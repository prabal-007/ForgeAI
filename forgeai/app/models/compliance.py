from pydantic import BaseModel, Field


class ComplianceIssue(BaseModel):
    type: str
    reason: str


class ComplianceResult(BaseModel):
    decision: str
    risk: str
    issues: list[ComplianceIssue] = Field(default_factory=list)
    notes: str | None = None
