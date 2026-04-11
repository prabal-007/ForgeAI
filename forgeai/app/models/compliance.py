from pydantic import BaseModel, Field


class ComplianceResult(BaseModel):
    decision: str
    risk: str
    issues: list[str] = Field(default_factory=list)
    notes: str | None = None
