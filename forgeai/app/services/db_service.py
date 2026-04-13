from __future__ import annotations

import uuid

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.db.models import Product, ProductHistory, ProductStage, ProductStatus, is_valid_stage
from app.domain.listing_output import validate_listing_output

NEXT_STAGE = {
    ProductStage.IDEA.value: ProductStage.BRAND.value,
    ProductStage.BRAND.value: ProductStage.DESIGN.value,
    ProductStage.DESIGN.value: ProductStage.CONTENT.value,
    ProductStage.CONTENT.value: ProductStage.COMPLIANCE.value,
    ProductStage.COMPLIANCE.value: ProductStage.EVALUATION.value,
    ProductStage.EVALUATION.value: ProductStage.LISTING.value,
    ProductStage.LISTING.value: ProductStage.ASSETS_GENERATION.value,
    ProductStage.ASSETS_GENERATION.value: ProductStage.READY.value,
}

STAGE_DATA_KEY = {
    ProductStage.IDEA.value: "idea_output",
    ProductStage.BRAND.value: "brand_output",
    ProductStage.DESIGN.value: "design",
    ProductStage.CONTENT.value: "content",
    ProductStage.COMPLIANCE.value: "compliance_output",
    ProductStage.EVALUATION.value: "evaluation",
    ProductStage.LISTING.value: "listing",
    ProductStage.ASSETS_GENERATION.value: "assets_generation",
}


class StateTransitionError(ValueError):
    pass


def _record_history(
    db: Session,
    product: Product,
    action: str,
    from_stage: str | None,
    to_stage: str,
    reason: str | None = None,
) -> None:
    db.add(
        ProductHistory(
            product_id=product.id,
            from_stage=from_stage,
            to_stage=to_stage,
            action=action,
            reason=reason,
        )
    )


def create_product(db: Session, brief: str) -> Product:
    product = Product(
        stage=ProductStage.IDEA.value,
        status=ProductStatus.PENDING.value,
        data={"brief": brief},
    )
    db.add(product)
    db.flush()
    _record_history(db, product, action="create", from_stage=None, to_stage=product.stage)
    db.flush()
    return product


def get_product(db: Session, product_id: uuid.UUID) -> Product:
    product = db.get(Product, product_id)
    if not product:
        raise StateTransitionError(f"Product {product_id} not found")
    return product


def save_stage_output(db: Session, product: Product, stage: str, output: dict) -> Product:
    data = dict(product.data or {})
    data_key = STAGE_DATA_KEY.get(stage, f"{stage}_output")
    data[data_key] = output
    product.data = data
    flag_modified(product, "data")
    _record_history(db, product, action="run_stage", from_stage=stage, to_stage=stage)
    db.flush()
    return product


def approve_current_stage(db: Session, product: Product) -> Product:
    current_stage = product.stage
    if current_stage == ProductStage.READY.value:
        raise StateTransitionError("READY stage cannot be approved further")

    if current_stage == ProductStage.DESIGN.value:
        design = (product.data or {}).get("design")
        cover  = (product.data or {}).get("cover")
        if not isinstance(design, dict):
            raise StateTransitionError(
                "Design stage has not been run yet — POST /pipeline/{product_id}/run first to generate concepts and cover."
            )
        if not isinstance(cover, dict) or not str(cover.get("image_url", "")).strip():
            raise StateTransitionError(
                "Design stage ran but no cover was generated — POST /pipeline/{product_id}/run again, or POST /products/{product_id}/regenerate-cover."
            )
    if current_stage == ProductStage.COMPLIANCE.value:
        decision = (product.data or {}).get("compliance_output", {}).get("decision")
        if decision != "pass":
            raise StateTransitionError("Cannot approve compliance stage without a pass decision")
    if current_stage == ProductStage.LISTING.value:
        listing = (product.data or {}).get("listing")
        if not isinstance(listing, dict):
            raise StateTransitionError(
                "Cannot approve listing without agent output: POST /pipeline/{product_id}/run first, then approve."
            )
        try:
            validate_listing_output(listing)
        except ValueError as exc:
            raise StateTransitionError(str(exc)) from exc
    if current_stage == ProductStage.ASSETS_GENERATION.value:
        data = product.data or {}
        cover = data.get("cover", {})
        interior_pdf = data.get("interior_pdf") or (data.get("assets_generation") or {}).get("interior_pdf")
        if not isinstance(cover, dict) or not str(cover.get("image_url", "")).strip():
            raise StateTransitionError("Cannot advance to READY without a valid cover.image_url")
        if not isinstance(interior_pdf, str) or not interior_pdf.strip():
            raise StateTransitionError("Cannot advance to READY without a generated interior_pdf")

    next_stage = NEXT_STAGE.get(current_stage)
    if not next_stage:
        raise StateTransitionError(f"No valid transition from stage '{current_stage}'")

    product.status = ProductStatus.APPROVED.value if next_stage == ProductStage.READY.value else ProductStatus.PENDING.value
    product.stage = next_stage

    _record_history(db, product, action="approve", from_stage=current_stage, to_stage=next_stage)
    db.flush()
    return product


def reject_current_stage(db: Session, product: Product, reason: str | None = None, human_notes: str | None = None) -> Product:
    product.status = ProductStatus.REJECTED.value
    data = dict(product.data or {})
    if reason:
        failure_reasons = list(data.get("failure_reasons", []))
        failure_reasons.append(reason)
        data["failure_reasons"] = failure_reasons

    feedback_entry = {
        "rejected_reason": reason or "",
        "human_notes": (human_notes or "").strip(),
        "stage": product.stage,
    }
    data["feedback"] = feedback_entry
    history = list(data.get("feedback_history", []))
    history.append(feedback_entry)
    data["feedback_history"] = history
    product.data = data
    flag_modified(product, "data")

    _record_history(db, product, action="reject", from_stage=product.stage, to_stage=product.stage, reason=reason)
    db.flush()
    return product


def set_stage(db: Session, product: Product, new_stage: str, reason: str | None = None, action: str = "transition") -> Product:
    if not is_valid_stage(new_stage):
        raise StateTransitionError(f"Invalid target stage '{new_stage}'")

    old_stage = product.stage
    if old_stage == ProductStage.READY.value and new_stage != ProductStage.READY.value:
        raise StateTransitionError("READY product cannot transition backward")

    product.stage = new_stage
    product.status = ProductStatus.PENDING.value
    _record_history(db, product, action=action, from_stage=old_stage, to_stage=new_stage, reason=reason)
    db.flush()
    return product
