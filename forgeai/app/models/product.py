from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class Stage(str, Enum):
    IDEA = "idea"
    BRAND = "brand"
    DESIGN = "design"
    CONTENT = "content"
    COMPLIANCE = "compliance"
    READY = "ready"


class StageStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


PIPELINE_STAGE_ORDER = (
    Stage.IDEA.value,
    Stage.BRAND.value,
    Stage.DESIGN.value,
    Stage.CONTENT.value,
    Stage.COMPLIANCE.value,
    Stage.READY.value,
)


def is_valid_stage(stage: str) -> bool:
    return stage in PIPELINE_STAGE_ORDER


class ProductCreateRequest(BaseModel):
    brief: str = Field(..., min_length=10)


class ProductTransitionRequest(BaseModel):
    reason: str | None = None


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
