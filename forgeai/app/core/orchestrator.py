from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.agents.brand_agent import brand_agent
from app.agents.compliance_agent import compliance_agent
from app.agents.content_agent import content_agent
from app.agents.design_agent import design_agent
from app.agents.trend_agent import trend_agent
from app.db.models import Product, ProductStage, ProductStatus
from app.models.product import ProductHistoryItem, ProductResponse, StageActionResponse
from app.services.db_service import (
    StateTransitionError,
    approve_current_stage,
    create_product,
    get_product,
    reject_current_stage,
    save_stage_output,
    set_stage,
)


def _regeneration_notes(product: Product) -> str | None:
    failure_reasons = (product.data or {}).get("failure_reasons", [])
    if not failure_reasons:
        return None
    return f"Avoid previous issues: {', '.join(failure_reasons)}"


def _to_response(product: Product) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        stage=product.stage,
        status=product.status,
        data=product.data or {},
        created_at=product.created_at,
        history=[
            ProductHistoryItem(
                from_stage=item.from_stage,
                to_stage=item.to_stage,
                action=item.action,
                reason=item.reason,
                created_at=item.created_at,
            )
            for item in product.history
        ],
    )


def _commit_and_refresh(db: Session, product: Product) -> Product:
    db.commit()
    db.refresh(product)
    return product


def create_pipeline_product(db: Session, brief: str) -> StageActionResponse:
    try:
        product = create_product(db, brief)
        product = _commit_and_refresh(db, product)
        return StageActionResponse(product=_to_response(product), message="Product created at IDEA stage.")
    except Exception:
        db.rollback()
        raise


def run_stage(db: Session, product_id: UUID) -> StageActionResponse:
    # Strict stage handling follows the persisted pipeline order in db models (conflict-safe).
    try:
        product = get_product(db, product_id)
        if product.status == ProductStatus.REJECTED.value and product.stage != ProductStage.COMPLIANCE.value:
            raise StateTransitionError("Rejected stage must be regenerated before running again")

        notes = _regeneration_notes(product)

        if product.stage == ProductStage.IDEA.value:
            brief = (product.data or {}).get("brief", "")
            output = trend_agent(brief=brief, regeneration_notes=notes)
            product = save_stage_output(db, product, ProductStage.IDEA.value, output)
        elif product.stage == ProductStage.BRAND.value:
            idea_output = (product.data or {}).get("idea_output", {})
            output = brand_agent(idea_json=idea_output, regeneration_notes=notes)
            product = save_stage_output(db, product, ProductStage.BRAND.value, output)
        elif product.stage == ProductStage.DESIGN.value:
            brand_output = (product.data or {}).get("brand_output", {})
            idea_output = (product.data or {}).get("idea_output", {})
            niche = idea_output.get("niche") if isinstance(idea_output, dict) else None
            if not niche:
                niche = (product.data or {}).get("brief", "general niche")
            output = design_agent(brand_identity=brand_output, niche=niche, regeneration_notes=notes)
            product = save_stage_output(db, product, ProductStage.DESIGN.value, output)
        elif product.stage == ProductStage.CONTENT.value:
            idea_output = (product.data or {}).get("idea_output", {})
            niche = idea_output.get("niche") if isinstance(idea_output, dict) else None
            if not niche:
                niche = (product.data or {}).get("brief", "general niche")

            brand_output = (product.data or {}).get("brand_output", {})
            brand_tone = brand_output.get("tone") if isinstance(brand_output, dict) else None
            if not brand_tone:
                brand_tone = "clear, practical, supportive"

            output = content_agent(niche=niche, brand_tone=brand_tone, regeneration_notes=notes)
            product = save_stage_output(db, product, ProductStage.CONTENT.value, output)
        elif product.stage == ProductStage.COMPLIANCE.value:
            payload = {
                "idea": (product.data or {}).get("idea_output", {}),
                "brand": (product.data or {}).get("brand_output", {}),
                "design": (product.data or {}).get("design", {}),
                "content": (product.data or {}).get("content", {}),
            }
            output = compliance_agent(payload)
            product = save_stage_output(db, product, ProductStage.COMPLIANCE.value, output)
            if output.get("decision") == "fail":
                issue_reasons = [item.get("reason", "") for item in output.get("issues", []) if isinstance(item, dict)]
                reason = "; ".join([r for r in issue_reasons if r]) or "Compliance failed"
                product = reject_current_stage(db, product, reason=reason)
                product = _commit_and_refresh(db, product)
                return StageActionResponse(product=_to_response(product), message="Compliance failed. Product rejected.")
        elif product.stage == ProductStage.READY.value:
            raise StateTransitionError("READY stage cannot be run")
        else:
            raise StateTransitionError(f"Unknown stage '{product.stage}'")

        product = _commit_and_refresh(db, product)
        return StageActionResponse(product=_to_response(product), message=f"Stage '{product.stage}' executed.")
    except Exception:
        db.rollback()
        raise


def approve_stage(db: Session, product_id: UUID) -> StageActionResponse:
    try:
        product = get_product(db, product_id)
        product = approve_current_stage(db, product)
        product = _commit_and_refresh(db, product)
        return StageActionResponse(product=_to_response(product), message=f"Advanced to '{product.stage}' stage.")
    except Exception:
        db.rollback()
        raise


def reject_stage(db: Session, product_id: UUID, reason: str | None = None) -> StageActionResponse:
    try:
        product = get_product(db, product_id)
        product = reject_current_stage(db, product, reason=reason)
        product = _commit_and_refresh(db, product)
        return StageActionResponse(product=_to_response(product), message=f"Stage '{product.stage}' rejected.")
    except Exception:
        db.rollback()
        raise


def regenerate_stage(db: Session, product_id: UUID) -> StageActionResponse:
    try:
        product = get_product(db, product_id)
        if product.status != ProductStatus.REJECTED.value:
            raise StateTransitionError("Only rejected products can be regenerated")

        # When compliance fails, iterate by regenerating content using failure reasons.
        if product.stage == ProductStage.COMPLIANCE.value:
            product = set_stage(
                db,
                product,
                new_stage=ProductStage.CONTENT.value,
                reason="Compliance failure triggered content regeneration",
                action="regenerate",
            )
        else:
            product = set_stage(
                db,
                product,
                new_stage=product.stage,
                reason="Manual regeneration",
                action="regenerate",
            )

        product = _commit_and_refresh(db, product)
        return run_stage(db, product.id)
    except Exception:
        db.rollback()
        raise
