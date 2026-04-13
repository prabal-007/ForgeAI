from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

logger = logging.getLogger(__name__)

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.agents.brand_agent import brand_agent
from app.agents.compliance_agent import compliance_agent
from app.agents.content_agent import content_agent
from app.agents.design_agent import design_agent
from app.agents.listing_agent import listing_agent
from app.agents.trend_agent import trend_agent
from app.db.models import Product, ProductStage, ProductStatus
from app.domain.content_output import validate_content_output
from app.domain.design_output import validate_design_output
from app.domain.design_positioning import design_context_from_idea
from app.domain.idea_output import niche_from_idea_output
from app.domain.listing_output import validate_listing_output
from app.models.product import ProductHistoryItem, ProductResponse, StageActionResponse
from app.services.cover_overlay import overlay_enabled, reapply_overlay_from_listing
from app.services.cover_service import generate_cover
from app.services.db_service import (
    StateTransitionError,
    approve_current_stage,
    create_product,
    get_product,
    reject_current_stage,
    save_stage_output,
    set_stage,
)
from app.services.pdf_generator import generate_interior_pdf


def _regeneration_notes(product: Product) -> str | None:
    data = product.data or {}
    failure_reasons = data.get("failure_reasons", [])
    parts: list[str] = []
    if isinstance(failure_reasons, list) and failure_reasons:
        parts.append(f"Avoid previous issues: {', '.join(str(x) for x in failure_reasons if x)}")
    fb = data.get("feedback")
    if isinstance(fb, dict):
        notes = (fb.get("human_notes") or "").strip()
        if notes:
            parts.append(f"Operator notes: {notes}")
        rej = (fb.get("rejected_reason") or "").strip()
        if rej:
            parts.append(f"Rejection context: {rej}")
    if not parts:
        return None
    return "\n".join(parts)


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
        if product.status == ProductStatus.REJECTED.value:
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
            data_brief = (product.data or {}).get("brief", "general niche")
            niche = niche_from_idea_output(idea_output, str(data_brief))
            pos_user, pos_problem = design_context_from_idea(product.data or {})
            output = design_agent(
                brand_identity=brand_output,
                niche=niche,
                regeneration_notes=notes,
                target_user=pos_user,
                core_problem=pos_problem,
            )
            try:
                validate_design_output(
                    output,
                    niche=niche,
                    target_user=pos_user,
                    core_problem=pos_problem,
                )
            except ValueError as exc:
                raise StateTransitionError(str(exc)) from exc
            product = save_stage_output(db, product, ProductStage.DESIGN.value, output)

            data = dict(product.data or {})
            bn      = brand_output.get("name")        if isinstance(brand_output, dict) else None
            bt      = brand_output.get("tagline")     if isinstance(brand_output, dict) else None
            cp_raw  = brand_output.get("color_palette") if isinstance(brand_output, dict) else None
            palette = [str(c) for c in cp_raw if isinstance(c, str)] if isinstance(cp_raw, list) else []
            cover_artifact = generate_cover(
                best_design_concept=output,
                product_id=product.id,
                niche=niche,
                brand_name=bn if isinstance(bn, str) else None,
                brand_tagline=bt if isinstance(bt, str) else None,
                color_palette=palette or None,
            )
            data["cover"] = cover_artifact
            product.data = data
            flag_modified(product, "data")
            db.flush()
        elif product.stage == ProductStage.CONTENT.value:
            idea_output = (product.data or {}).get("idea_output", {})
            data_brief = (product.data or {}).get("brief", "general niche")
            niche = niche_from_idea_output(idea_output, str(data_brief))

            brand_output = (product.data or {}).get("brand_output", {})
            brand_tone = brand_output.get("tone") if isinstance(brand_output, dict) else None
            if not brand_tone:
                brand_tone = "clear, practical, supportive"

            output = content_agent(niche=niche, brand_tone=brand_tone, regeneration_notes=notes)
            try:
                validate_content_output(output)
            except ValueError as exc:
                raise StateTransitionError(str(exc)) from exc
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
        elif product.stage == ProductStage.EVALUATION.value:
            raise StateTransitionError("EVALUATION stage is review-only; approve or reject it without running")
        elif product.stage == ProductStage.LISTING.value:
            data = dict(product.data or {})
            evaluation_output = data.get("evaluation") or data.get("evaluation_output")
            if not isinstance(evaluation_output, dict):
                evaluation_output = {}

            idea_output = data.get("idea_output") or {}
            niche = niche_from_idea_output(idea_output, str(data.get("brief") or "general niche"))

            brand_output = data.get("brand_output") or {}
            brand = brand_output.get("name") or "Original brand"

            evaluation_positioning = {
                "why_it_will_sell": evaluation_output.get("why_it_will_sell", ""),
                "target_customer": evaluation_output.get("target_customer", ""),
                "use_case": evaluation_output.get("use_case", ""),
            }

            output = listing_agent(
                niche=niche,
                brand=brand,
                evaluation_positioning=evaluation_positioning,
                regeneration_notes=notes,
            )
            try:
                validate_listing_output(output)
            except ValueError as exc:
                raise StateTransitionError(str(exc)) from exc
            product = save_stage_output(db, product, ProductStage.LISTING.value, output)
        elif product.stage == ProductStage.ASSETS_GENERATION.value:
            data = dict(product.data or {})
            content = data.get("content", {})
            sections = content.get("sections", []) if isinstance(content, dict) else []
            if not isinstance(sections, list) or not sections:
                raise StateTransitionError("Cannot generate assets without content.sections")
            if not isinstance(content, dict):
                content = {"sections": sections}

            interior_pdf = generate_interior_pdf(content=content, output_name=f"product-{product.id}")
            if not Path(interior_pdf).is_file() or Path(interior_pdf).stat().st_size <= 0:
                raise StateTransitionError("Interior PDF generation failed")

            # Refresh cover with final listing title (programmatic: regenerate; AI: re-overlay)
            listing = data.get("listing") or {}
            listing_title    = str(listing.get("title") or "").strip()
            listing_subtitle = str(listing.get("subtitle") or "").strip()
            cover = data.get("cover") or {}
            cover_path = str(cover.get("path") or "")
            if listing_title and cover_path and Path(cover_path).is_file():
                try:
                    from app.services.cover_generator import cover_mode, generate_programmatic_cover
                    if cover_mode() == "programmatic":
                        brand_output_a = data.get("brand_output") or {}
                        idea_output_a  = data.get("idea_output") or {}
                        niche_a        = niche_from_idea_output(idea_output_a, str(data.get("brief") or ""))
                        cp_raw_a       = brand_output_a.get("color_palette") if isinstance(brand_output_a, dict) else None
                        palette_a      = [str(c) for c in cp_raw_a if isinstance(c, str)] if isinstance(cp_raw_a, list) else []
                        new_bytes = generate_programmatic_cover(
                            title=listing_title,
                            subtitle=listing_subtitle,
                            brand_name=str(brand_output_a.get("name") or ""),
                            tagline=str(brand_output_a.get("tagline") or ""),
                            color_palette=palette_a,
                            niche=niche_a,
                        )
                    else:
                        new_bytes = reapply_overlay_from_listing(cover_path, listing_title, listing_subtitle)
                    Path(cover_path).write_bytes(new_bytes)
                    data["cover"] = {**cover, "overlay_title": listing_title, "cover_updated": True}
                except Exception as _cover_err:
                    logger.warning("Cover title refresh skipped at assets stage: %s", _cover_err)

            data["interior_pdf"] = interior_pdf
            data["assets_generation"] = {
                "status": "completed",
                "interior_pdf": interior_pdf,
                "source_sections": len(sections),
            }
            product.data = data
            flag_modified(product, "data")
            product = save_stage_output(db, product, ProductStage.ASSETS_GENERATION.value, data["assets_generation"])
        elif product.stage == ProductStage.READY.value:
            raise StateTransitionError("READY stage cannot be run")
        else:
            raise StateTransitionError(f"Unknown stage '{product.stage}'")

        product = _commit_and_refresh(db, product)
        return StageActionResponse(product=_to_response(product), message=f"Stage '{product.stage}' executed.")
    except Exception:
        db.rollback()
        raise


def regenerate_cover(db: Session, product_id: UUID) -> StageActionResponse:
    """
    Generate (or re-generate) cover for any product that already has brand + idea data.

    Safe to call at any stage — does not change stage or status.
    Use when design was approved without running, or when the cover needs refreshing.
    """
    try:
        product = get_product(db, product_id)
        data = dict(product.data or {})

        brand_output = data.get("brand_output") or {}
        idea_output  = data.get("idea_output") or {}
        data_brief   = str(data.get("brief") or "general niche")
        niche        = niche_from_idea_output(idea_output, data_brief)
        pos_user, pos_problem = design_context_from_idea(data)

        design_output = data.get("design")
        if not isinstance(design_output, dict) or not design_output.get("concepts"):
            # Design concepts never generated — run design agent first
            notes = _regeneration_notes(product)
            design_output = design_agent(
                brand_identity=brand_output,
                niche=niche,
                regeneration_notes=notes,
                target_user=pos_user,
                core_problem=pos_problem,
            )
            try:
                validate_design_output(
                    design_output,
                    niche=niche,
                    target_user=pos_user,
                    core_problem=pos_problem,
                )
            except ValueError as exc:
                raise StateTransitionError(str(exc)) from exc
            data["design"] = design_output

        bn      = brand_output.get("name")        if isinstance(brand_output, dict) else None
        bt      = brand_output.get("tagline")     if isinstance(brand_output, dict) else None
        cp_raw  = brand_output.get("color_palette") if isinstance(brand_output, dict) else None
        palette = [str(c) for c in cp_raw if isinstance(c, str)] if isinstance(cp_raw, list) else []
        listing = data.get("listing") or {}
        lt      = str(listing.get("title") or "").strip() or None
        ls      = str(listing.get("subtitle") or "").strip() or None
        cover_artifact = generate_cover(
            best_design_concept=design_output,
            product_id=product.id,
            niche=niche,
            brand_name=bn if isinstance(bn, str) else None,
            brand_tagline=bt if isinstance(bt, str) else None,
            color_palette=palette or None,
            listing_title=lt,
            listing_subtitle=ls,
        )
        data["cover"] = cover_artifact
        product.data = data
        flag_modified(product, "data")
        product = _commit_and_refresh(db, product)
        return StageActionResponse(
            product=_to_response(product),
            message=f"Cover regenerated ({cover_artifact.get('method', 'programmatic')}). image_url: {cover_artifact.get('image_url')}",
        )
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


def reject_stage(db: Session, product_id: UUID, reason: str | None = None, human_notes: str | None = None) -> StageActionResponse:
    try:
        product = get_product(db, product_id)
        product = reject_current_stage(db, product, reason=reason, human_notes=human_notes)
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
