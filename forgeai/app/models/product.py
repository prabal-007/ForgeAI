from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Stage(str, Enum):
    IDEA = "idea"
    VALIDATION = "validation"
    BRAND = "brand"
    DESIGN = "design"
    CONTENT = "content"
    COMPLIANCE = "compliance"
    READY = "ready"


class StageStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ProductState(BaseModel):
    stage: Stage = Stage.IDEA
    status: StageStatus = StageStatus.PENDING
    data: dict[str, Any] = Field(default_factory=dict)


class PipelineRunRequest(BaseModel):
    brief: str = Field(..., min_length=10, description="Product idea brief.")
    approve_idea: bool = False
    approve_brand: bool = False


class PipelineRunResponse(BaseModel):
    state: ProductState
    next_action: str
