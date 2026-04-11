from pydantic import BaseModel, Field


class BrandCandidate(BaseModel):
    name: str = Field(..., min_length=3)
    tone: str
    visual_direction: str
    uniqueness_notes: list[str] = Field(default_factory=list)
