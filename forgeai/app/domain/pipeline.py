from __future__ import annotations

from enum import Enum


class PipelineStage(str, Enum):
    IDEA = "idea"
    BRAND = "brand"
    DESIGN = "design"
    CONTENT = "content"
    COMPLIANCE = "compliance"
    EVALUATION = "evaluation"
    LISTING = "listing"
    ASSETS_GENERATION = "assets_generation"
    READY = "ready"


class PipelineStageStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


PIPELINE_STAGE_ORDER = (
    PipelineStage.IDEA.value,
    PipelineStage.BRAND.value,
    PipelineStage.DESIGN.value,
    PipelineStage.CONTENT.value,
    PipelineStage.COMPLIANCE.value,
    PipelineStage.EVALUATION.value,
    PipelineStage.LISTING.value,
    PipelineStage.ASSETS_GENERATION.value,
    PipelineStage.READY.value,
)


def is_valid_stage(stage: str) -> bool:
    return stage in PIPELINE_STAGE_ORDER
