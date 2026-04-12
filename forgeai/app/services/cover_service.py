from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4


def _pick_best_concept(best_design_concept: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize possible design-agent output shapes into a single concept payload."""
    if not isinstance(best_design_concept, dict):
        return {}

    if isinstance(best_design_concept.get("best_design_concept"), dict):
        return dict(best_design_concept["best_design_concept"])

    candidates = best_design_concept.get("design_concepts")
    if isinstance(candidates, list):
        for concept in candidates:
            if isinstance(concept, dict):
                return dict(concept)

    return dict(best_design_concept)


def _render_image_stub(concept: dict[str, Any], product_id: UUID | str) -> bytes:
    """
    Placeholder image generation call.

    Replace this function with a concrete provider integration (e.g. image model API,
    Figma hand-off export, or internal renderer) when available.
    """
    return json.dumps({"product_id": str(product_id), "concept": concept}, indent=2).encode("utf-8")


def _store_locally(image_bytes: bytes, product_id: UUID | str) -> tuple[str, str]:
    storage_dir = Path(os.getenv("COVER_STORAGE_DIR", "./generated_covers")).resolve()
    storage_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{product_id}_{uuid4().hex}.png"
    file_path = storage_dir / filename
    file_path.write_bytes(image_bytes)
    return f"file://{file_path}", str(file_path)


def generate_cover(best_design_concept: dict[str, Any], product_id: UUID | str) -> dict[str, Any]:
    """
    Turn the selected design concept into a storable cover artifact and return an image URL.

    Storage mode:
    - local (default): writes a generated placeholder image payload to disk.
    - s3: returns a placeholder S3 URL/path for future uploader integration.
    """
    concept = _pick_best_concept(best_design_concept)
    concept_id = concept.get("id") or concept.get("concept_id")
    image_bytes = _render_image_stub(concept=concept, product_id=product_id)

    storage_mode = os.getenv("COVER_STORAGE_MODE", "local").strip().lower()
    if storage_mode == "s3":
        bucket = os.getenv("COVER_S3_BUCKET", "forgeai-cover-artifacts")
        key = f"products/{product_id}/cover-{uuid4().hex}.png"
        # Placeholder branch for future S3 upload adapter integration.
        return {
            "image_url": f"https://{bucket}.s3.amazonaws.com/{key}",
            "storage": "s3",
            "path": key,
            "concept_id": concept_id,
            "bytes_length": len(image_bytes),
        }

    image_url, local_path = _store_locally(image_bytes=image_bytes, product_id=product_id)
    return {
        "image_url": image_url,
        "storage": "local",
        "path": local_path,
        "concept_id": concept_id,
    }
