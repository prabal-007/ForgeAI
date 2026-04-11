from __future__ import annotations

import json
from pathlib import Path

from app.core.guards import run_guardrails
from app.services.llm_service import run_prompt

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "compliance.txt"


def compliance_agent(payload: dict) -> dict:
    payload_text = json.dumps(payload, ensure_ascii=False)
    guardrail_result = run_guardrails(payload_text)
    if guardrail_result["decision"] == "fail":
        return guardrail_result

    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    llm_result = run_prompt(f"{prompt}\n\nPayload JSON:\n{payload_text}")
    llm_result.setdefault("decision", "pass")
    llm_result.setdefault("risk", "low")
    llm_result.setdefault("issues", [])
    return llm_result
