from __future__ import annotations

from app.agents.brand_agent import brand_agent
from app.agents.compliance_agent import compliance_agent
from app.agents.trend_agent import trend_agent
from app.models.product import PipelineRunRequest, PipelineRunResponse, ProductState, Stage, StageStatus


def run_pipeline(request: PipelineRunRequest) -> PipelineRunResponse:
    state = ProductState(stage=Stage.IDEA, status=StageStatus.PENDING)

    idea = trend_agent(request.brief)
    state.data[Stage.IDEA.value] = idea

    if not request.approve_idea:
        return PipelineRunResponse(state=state, next_action="Approve IDEA stage to continue.")

    state.stage = Stage.BRAND
    state.status = StageStatus.PENDING
    brand = brand_agent(idea)
    state.data[Stage.BRAND.value] = brand

    if not request.approve_brand:
        return PipelineRunResponse(state=state, next_action="Approve BRAND stage to run compliance.")

    state.stage = Stage.COMPLIANCE
    compliance = compliance_agent({"idea": idea, "brand": brand})
    state.data[Stage.COMPLIANCE.value] = compliance

    if compliance.get("decision") == "fail":
        state.status = StageStatus.REJECTED
        return PipelineRunResponse(state=state, next_action="Pipeline failed compliance checks.")

    state.stage = Stage.READY
    state.status = StageStatus.APPROVED
    return PipelineRunResponse(state=state, next_action="Product is READY for listing metadata generation.")
