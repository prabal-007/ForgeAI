from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.db.models import PIPELINE_STAGE_ORDER, Product, ProductHistory, ProductStage, ProductStatus

NEXT_STAGE = {
    ProductStage.IDEA.value: ProductStage.BRAND.value,
    ProductStage.BRAND.value: ProductStage.DESIGN.value,
    ProductStage.DESIGN.value: ProductStage.CONTENT.value,
    ProductStage.CONTENT.value: ProductStage.COMPLIANCE.value,
    ProductStage.COMPLIANCE.value: ProductStage.READY.value,
}

STAGE_DATA_KEY = {
    ProductStage.IDEA.value: "idea_output",
    ProductStage.BRAND.value: "brand_output",
    ProductStage.DESIGN.value: "design",
    ProductStage.CONTENT.value: "content",
    ProductStage.COMPLIANCE.value: "compliance_output",
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
    db.commit()
    db.refresh(product)
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
    _record_history(db, product, action="run_stage", from_stage=stage, to_stage=stage)
    db.commit()
    db.refresh(product)
    return product


def approve_current_stage(db: Session, product: Product) -> Product:
    current_stage = product.stage
    if current_stage == ProductStage.READY.value:
        raise StateTransitionError("READY stage cannot be approved further")

    if current_stage == ProductStage.COMPLIANCE.value:
        decision = (product.data or {}).get("compliance_output", {}).get("decision")
        if decision != "pass":
            raise StateTransitionError("Cannot approve compliance stage without a pass decision")

    next_stage = NEXT_STAGE.get(current_stage)
    if not next_stage:
        raise StateTransitionError(f"No valid transition from stage '{current_stage}'")

    product.status = ProductStatus.APPROVED.value if next_stage == ProductStage.READY.value else ProductStatus.PENDING.value
    product.stage = next_stage

    _record_history(db, product, action="approve", from_stage=current_stage, to_stage=next_stage)
    db.commit()
    db.refresh(product)
    return product


def reject_current_stage(db: Session, product: Product, reason: str | None = None) -> Product:
    product.status = ProductStatus.REJECTED.value
    data = dict(product.data or {})
    if reason:
        failure_reasons = list(data.get("failure_reasons", []))
        failure_reasons.append(reason)
        data["failure_reasons"] = failure_reasons
        product.data = data

    _record_history(db, product, action="reject", from_stage=product.stage, to_stage=product.stage, reason=reason)
    db.commit()
    db.refresh(product)
    return product


def set_stage(db: Session, product: Product, new_stage: str, reason: str | None = None, action: str = "transition") -> Product:
    if new_stage not in PIPELINE_STAGE_ORDER:
        raise StateTransitionError(f"Invalid target stage '{new_stage}'")

    old_stage = product.stage
    if old_stage == ProductStage.READY.value and new_stage != ProductStage.READY.value:
        raise StateTransitionError("READY product cannot transition backward")

    product.stage = new_stage
    product.status = ProductStatus.PENDING.value
    _record_history(db, product, action=action, from_stage=old_stage, to_stage=new_stage, reason=reason)
    db.commit()
    db.refresh(product)
    return product
