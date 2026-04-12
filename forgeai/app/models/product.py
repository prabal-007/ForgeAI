from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.pipeline import (
    PIPELINE_STAGE_ORDER,
    PipelineStage,
    PipelineStageStatus,
    is_valid_stage,
)

# API schema aliases preserved for compatibility.
Stage = PipelineStage
StageStatus = PipelineStageStatus


class ProductCreateRequest(BaseModel):
    brief: str = Field(..., min_length=10)


class ProductTransitionRequest(BaseModel):
    reason: str | None = None
    human_notes: str | None = Field(
        default=None,
        description="Optional operator notes; stored on product.data['feedback'] and fed into regeneration.",
    )


class ProductHistoryItem(BaseModel):
    from_stage: str | None
    to_stage: str
    action: str
    reason: str | None = None
    created_at: datetime


class ProductResponse(BaseModel):
    id: UUID
    stage: Stage
    status: StageStatus
    data: dict
    created_at: datetime
    history: list[ProductHistoryItem] = Field(default_factory=list)


class StageActionResponse(BaseModel):
    product: ProductResponse
    message: str
