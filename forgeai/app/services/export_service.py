from __future__ import annotations

import json
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.agents.listing_agent import listing_agent
from app.db.models import Product
from app.domain.idea_output import niche_from_idea_output
from app.domain.listing_output import validate_listing_output
from app.services.cover_service import local_path_from_cover
from app.services.pdf_generator import DEFAULT_OUTPUT_DIR

EXPORT_ROOT = Path(__file__).resolve().parents[2] / "generated_exports"


def _cover_image_bytes(cover: dict[str, Any]) -> bytes:
    local = local_path_from_cover(cover)
    if local is not None:
        return local.read_bytes()
    if cover.get("storage") == "s3":
        bucket = os.getenv("COVER_S3_BUCKET", "").strip() or None
        key = cover.get("path")
        if bucket and isinstance(key, str) and key.strip():
            try:
                import boto3
            except ImportError as exc:
                raise ValueError("S3 cover export requires boto3 installed") from exc
            region = os.getenv("COVER_S3_REGION", "").strip()
            client = boto3.client("s3", region_name=region) if region else boto3.client("s3")
            obj = client.get_object(Bucket=bucket, Key=key)
            return obj["Body"].read()
    raise ValueError("Export requires a readable cover (local path or S3 key)")


def _interior_pdf_path(data: dict[str, Any]) -> str | None:
    top = data.get("interior_pdf")
    if isinstance(top, str) and top.strip():
        return top.strip()
    nested = data.get("assets_generation")
    if isinstance(nested, dict):
        inner = nested.get("interior_pdf")
        if isinstance(inner, str) and inner.strip():
            return inner.strip()
    return None


def _generate_missing_listing(data: dict[str, Any]) -> dict[str, Any]:
    """Backfill listing via listing_agent (e.g. listing was approved without POST .../run)."""
    idea_output = data.get("idea_output") or {}
    niche = niche_from_idea_output(idea_output, str(data.get("brief") or "general niche"))
    brand_output = data.get("brand_output") or {}
    brand = brand_output.get("name") or "Original brand"
    evaluation_output = data.get("evaluation") or data.get("evaluation_output") or {}
    if not isinstance(evaluation_output, dict):
        evaluation_output = {}
    evaluation_positioning = {
        "why_it_will_sell": evaluation_output.get("why_it_will_sell", ""),
        "target_customer": evaluation_output.get("target_customer", ""),
        "use_case": evaluation_output.get("use_case", ""),
    }
    output = listing_agent(
        niche=niche,
        brand=brand,
        evaluation_positioning=evaluation_positioning,
        regeneration_notes=None,
    )
    validate_listing_output(output)
    return output


def _listing_payload(listing: Any) -> dict[str, Any]:
    if not isinstance(listing, dict):
        raise ValueError("Product has no listing data to export")
    out = {
        "target_user": listing.get("target_user"),
        "core_problem": listing.get("core_problem"),
        "unique_value": listing.get("unique_value"),
        "title": listing.get("title"),
        "subtitle": listing.get("subtitle"),
        "description": listing.get("description"),
        "keywords": listing.get("keywords"),
    }
    required_export = ("title", "subtitle", "description", "keywords")
    missing = [k for k in required_export if out.get(k) is None]
    if missing:
        raise ValueError(f"Listing export missing required fields: {', '.join(missing)}")
    if not isinstance(out["keywords"], list) or not all(isinstance(x, str) for x in out["keywords"]):
        raise ValueError("listing.keywords must be a list of strings")
    return out


def export_product(db: Session, product_id: UUID) -> dict[str, Any]:
    """
    Zip cover.png, interior.pdf, and listing.json for KDP/manual upload.

    Persists product.data['export'] with zip_path and metadata.
    """
    product = db.get(Product, product_id)
    if not product:
        raise ValueError(f"Product {product_id} not found")

    data = dict(product.data or {})
    cover = data.get("cover")
    if not isinstance(cover, dict):
        raise ValueError("Product has no cover data to export")
    cover_bytes = _cover_image_bytes(cover)

    interior = _interior_pdf_path(data)
    used_disk_fallback = False
    if not interior:
        fallback_pdf = DEFAULT_OUTPUT_DIR / f"product-{product_id}.pdf"
        if fallback_pdf.is_file():
            interior = str(fallback_pdf.resolve())
            used_disk_fallback = True
    if not interior:
        raise ValueError(
            "Export requires interior_pdf path in product data (or assets_generation.interior_pdf). "
            "Re-run POST /pipeline/{id}/run on assets_generation after upgrading, or ensure the interior PDF exists."
        )
    interior_path = Path(interior)
    if not interior_path.is_file():
        raise ValueError(f"Interior PDF not found at {interior_path}")

    listing_raw = data.get("listing")
    try:
        listing_payload = _listing_payload(listing_raw)
    except ValueError:
        generated = _generate_missing_listing(data)
        data["listing"] = generated
        listing_payload = _listing_payload(generated)

    EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
    product_dir = EXPORT_ROOT / str(product_id)
    product_dir.mkdir(parents=True, exist_ok=True)
    zip_path = product_dir / "product_export.zip"

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("cover.png", cover_bytes)
        zf.write(interior_path, arcname="interior.pdf")
        listing_bytes = json.dumps(listing_payload, indent=2, ensure_ascii=False).encode("utf-8")
        zf.writestr("listing.json", listing_bytes)

    export_record = {
        "zip_path": str(zip_path.resolve()),
        "files": ["cover.png", "interior.pdf", "listing.json"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if used_disk_fallback:
        data["interior_pdf"] = interior
    data["export"] = export_record
    product.data = data
    flag_modified(product, "data")
    db.add(product)
    db.commit()
    db.refresh(product)
    return export_record
