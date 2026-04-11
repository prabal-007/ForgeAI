from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import Path

from app.core.guards import run_guardrails
from app.services.llm_service import run_prompt

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "compliance.txt"

KNOWN_IP_NAMES = {
    "ironman",
    "avengers",
    "naruto",
    "batman",
    "spiderman",
    "superman",
    "captain america",
}

DESIGN_BANNED_CUES = {
    "superhero",
    "hero",
    "cape",
    "mask",
    "armor",
    "glowing eyes",
    "cinematic",
    "vigilante",
    "epic battle",
}

CONTENT_BANNED_CUES = {
    "character arc",
    "hero journey",
    "movie scene",
    "cinematic",
    "franchise",
    "lined pages",
    "blank lined",
}


def _is_similar_to_known_ip(brand_name: str) -> str | None:
    normalized = brand_name.lower().strip()
    if not normalized:
        return None

    for ip_name in KNOWN_IP_NAMES:
        ratio = SequenceMatcher(None, normalized, ip_name).ratio()
        if ip_name in normalized or ratio >= 0.82:
            return ip_name
    return None


def _collect_design_issues(design_payload: dict) -> list[dict]:
    issues: list[dict] = []
    concepts = design_payload.get("concepts", []) if isinstance(design_payload, dict) else []
    for index, concept in enumerate(concepts, start=1):
        merged = " ".join(
            [
                str(concept.get("style", "")),
                str(concept.get("prompt", "")),
                str(concept.get("layout_notes", "")),
            ]
        ).lower()
        for cue in DESIGN_BANNED_CUES:
            if re.search(rf"\b{re.escape(cue)}\b", merged):
                issues.append(
                    {
                        "type": "design",
                        "reason": f"Concept {index} contains restricted visual/cinematic cue: '{cue}'.",
                    }
                )
                break
    return issues


def _collect_content_issues(content_payload: dict) -> list[dict]:
    issues: list[dict] = []
    sections = content_payload.get("sections", []) if isinstance(content_payload, dict) else []
    for index, section in enumerate(sections, start=1):
        merged = " ".join(
            [
                str(section.get("name", "")),
                str(section.get("pages", "")),
                str(section.get("purpose", "")),
            ]
        ).lower()
        for cue in CONTENT_BANNED_CUES:
            if re.search(rf"\b{re.escape(cue)}\b", merged):
                issues.append(
                    {
                        "type": "content",
                        "reason": f"Section {index} includes restricted or low-value pattern: '{cue}'.",
                    }
                )
                break
    return issues


def _classify_guardrail_issue(issue: str) -> dict:
    lowered = issue.lower()
    issue_type = "design"
    if "blacklisted" in lowered:
        issue_type = "brand"
    elif "visual" in lowered:
        issue_type = "design"
    elif "pattern" in lowered:
        issue_type = "content"
    return {"type": issue_type, "reason": issue}




def _result(issues: list[dict]) -> dict:
    decision = "fail" if issues else "pass"
    risk = "high" if issues else "low"
    return {"risk": risk, "issues": issues, "decision": decision}


def compliance_agent(payload: dict) -> dict:
    brand_payload = payload.get("brand", {}) if isinstance(payload, dict) else {}
    design_payload = payload.get("design", {}) if isinstance(payload, dict) else {}
    content_payload = payload.get("content", {}) if isinstance(payload, dict) else {}

    issues: list[dict] = []

    brand_name = str(brand_payload.get("name", "")) if isinstance(brand_payload, dict) else ""
    matched_ip = _is_similar_to_known_ip(brand_name)
    if matched_ip:
        issues.append(
            {
                "type": "brand",
                "reason": f"Brand name '{brand_name}' appears similar to known IP '{matched_ip}'.",
            }
        )

    issues.extend(_collect_design_issues(design_payload))
    issues.extend(_collect_content_issues(content_payload))

    payload_text = json.dumps(payload, ensure_ascii=False)
    guardrail_result = run_guardrails(payload_text)
    if guardrail_result["decision"] == "fail":
        issues.extend([_classify_guardrail_issue(item) for item in guardrail_result.get("issues", [])])

    # Optional secondary review for additional semantic risks.
    if not issues:
        prompt = PROMPT_PATH.read_text(encoding="utf-8")
        llm_result = run_prompt(f"{prompt}\n\nPayload JSON:\n{payload_text}")
        llm_issues = llm_result.get("issues", []) if isinstance(llm_result, dict) else []
        for item in llm_issues:
            if isinstance(item, dict) and {"type", "reason"}.issubset(item):
                issues.append({"type": item["type"], "reason": item["reason"]})

    return _result(issues)
