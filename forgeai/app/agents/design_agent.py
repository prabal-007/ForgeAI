from __future__ import annotations

from pathlib import Path

from app.services.llm_service import run_prompt

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "design.txt"
PROMPT = PROMPT_PATH.read_text(encoding="utf-8")


def design_agent(
    brand_identity: dict,
    niche: str,
    regeneration_notes: str | None = None,
    target_user: str | None = None,
    core_problem: str | None = None,
) -> dict:
    guidance = f"\n\nRegeneration notes:\n{regeneration_notes}" if regeneration_notes else ""
    pos = ""
    tu = (target_user or "").strip()
    cp = (core_problem or "").strip()
    if tu or cp:
        pos = f"\n\nTarget user:\n{tu or '(derive from niche)'}\n\nCore problem this product addresses:\n{cp or '(derive from niche)'}"

    return run_prompt(
        f"{PROMPT}\n\nBrand identity:\n{brand_identity}\n\nNiche:\n{niche}{pos}{guidance}"
    )
