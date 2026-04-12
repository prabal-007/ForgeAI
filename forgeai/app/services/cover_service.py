from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import urlopen
from uuid import UUID, uuid4

from openai import OpenAI

_client: OpenAI | None = None


def _openai_client() -> OpenAI:
    global _client
    if _client is None:
        key = os.getenv("OPENAI_API_KEY", "").strip()
        if not key:
            raise ValueError("OPENAI_API_KEY is required for real cover image generation")
        _client = OpenAI(api_key=key)
    return _client


def _pick_best_concept(best_design_concept: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize design-agent output into a single concept payload (prompt + style)."""
    if not isinstance(best_design_concept, dict):
        return {}

    concepts = best_design_concept.get("concepts")
    if isinstance(concepts, list):
        for concept in concepts:
            if isinstance(concept, dict):
                return dict(concept)

    if isinstance(best_design_concept.get("best_design_concept"), dict):
        return dict(best_design_concept["best_design_concept"])

    candidates = best_design_concept.get("design_concepts")
    if isinstance(candidates, list):
        for concept in candidates:
            if isinstance(concept, dict):
                return dict(concept)

    return dict(best_design_concept)


def _build_image_prompt(concept: dict[str, Any]) -> str:
    """Compose a single image prompt from the chosen design concept."""
    parts: list[str] = []
    prompt = concept.get("prompt")
    if isinstance(prompt, str) and prompt.strip():
        parts.append(prompt.strip())
    style = concept.get("style")
    if isinstance(style, str) and style.strip():
        parts.append(f"Visual style: {style.strip()}")
    layout = concept.get("layout_notes")
    if isinstance(layout, str) and layout.strip():
        parts.append(f"Layout: {layout.strip()}")
    if not parts:
        raise ValueError("Design concept has no usable prompt, style, or layout_notes for image generation")
    base = " ".join(parts)
    suffix = (
        " Professional KDP book cover, full bleed, high resolution, clean typography area, "
        "no copyrighted characters or logos, original artwork."
    )
    return f"{base}{suffix}"


def _generate_image_bytes(prompt: str) -> tuple[bytes, str | None]:
    """
    Call OpenAI Images API; return PNG/JPEG bytes and optional provider-revised prompt.
    """
    model = os.getenv("COVER_IMAGE_MODEL", "dall-e-3").strip()
    size = os.getenv("COVER_IMAGE_SIZE", "1024x1792").strip()
    client = _openai_client()

    response = client.images.generate(model=model, prompt=prompt, size=size, quality="standard", n=1)
    item = response.data[0]
    revised = getattr(item, "revised_prompt", None)

    b64 = getattr(item, "b64_json", None)
    if b64:
        raw = base64.b64decode(b64)
        return raw, revised if isinstance(revised, str) else None

    remote_url = getattr(item, "url", None)
    if not remote_url:
        raise RuntimeError("Image API returned no url or b64_json")

    with urlopen(remote_url) as resp:  # noqa: S310 — OpenAI-hosted URL from API
        raw = resp.read()
    return raw, revised if isinstance(revised, str) else None


def _store_locally(image_bytes: bytes, product_id: UUID | str) -> tuple[str, str]:
    storage_dir = Path(os.getenv("COVER_STORAGE_DIR", "./generated_covers")).resolve()
    storage_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{product_id}_{uuid4().hex}.png"
    file_path = storage_dir / filename
    file_path.write_bytes(image_bytes)
    return f"file://{file_path}", str(file_path)


def _upload_s3(image_bytes: bytes, bucket: str, key: str) -> str:
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("COVER_STORAGE_MODE=s3 requires the boto3 package") from exc

    region = os.getenv("COVER_S3_REGION", "").strip()
    if region:
        client = boto3.client("s3", region_name=region)
    else:
        client = boto3.client("s3")
    client.put_object(Bucket=bucket, Key=key, Body=image_bytes, ContentType="image/png")
    if region:
        return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
    return f"https://{bucket}.s3.amazonaws.com/{key}"


def generate_cover(best_design_concept: dict[str, Any], product_id: UUID | str) -> dict[str, Any]:
    """
    Generate a real cover image from the design concept via OpenAI Images API.

    Sets product.data['cover'] fields including image_url, prompt_used, and path (local) or S3 URL.
    """
    concept = _pick_best_concept(best_design_concept)
    concept_id = concept.get("id") or concept.get("concept_id")
    prompt_used = _build_image_prompt(concept)

    image_bytes, revised = _generate_image_bytes(prompt_used)
    if not image_bytes:
        raise RuntimeError("Image generation returned empty payload")

    # Normalize to PNG on disk for downstream export (OpenAI may return PNG bytes).
    storage_mode = os.getenv("COVER_STORAGE_MODE", "local").strip().lower()
    record_prompt = revised.strip() if isinstance(revised, str) and revised.strip() else prompt_used

    if storage_mode == "s3":
        bucket = os.getenv("COVER_S3_BUCKET", "").strip()
        if not bucket:
            raise ValueError("COVER_S3_BUCKET is required when COVER_STORAGE_MODE=s3")
        key = f"products/{product_id}/cover-{uuid4().hex}.png"
        image_url = _upload_s3(image_bytes=image_bytes, bucket=bucket, key=key)
        return {
            "image_url": image_url,
            "prompt_used": record_prompt,
            "storage": "s3",
            "path": key,
            "concept_id": concept_id,
            "bytes_length": len(image_bytes),
        }

    image_url, local_path = _store_locally(image_bytes=image_bytes, product_id=product_id)
    return {
        "image_url": image_url,
        "prompt_used": record_prompt,
        "storage": "local",
        "path": local_path,
        "concept_id": concept_id,
        "bytes_length": len(image_bytes),
    }


def local_path_from_cover(cover: dict[str, Any] | None) -> Path | None:
    """Resolve a local filesystem path for a cover dict, if available."""
    if not isinstance(cover, dict):
        return None
    path_str = cover.get("path")
    if isinstance(path_str, str) and path_str and cover.get("storage") == "local":
        p = Path(path_str)
        if p.is_file():
            return p
    url = cover.get("image_url")
    if isinstance(url, str) and url.startswith("file://"):
        parsed = urlparse(url)
        if parsed.path:
            p = Path(parsed.path)
            if p.is_file():
                return p
    return None
