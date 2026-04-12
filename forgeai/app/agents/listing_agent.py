from __future__ import annotations

from pathlib import Path

from app.services.llm_service import run_prompt

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "listing.txt"
PROMPT = PROMPT_PATH.read_text(encoding="utf-8")


def listing_agent(
    niche: str,
    brand: str,
    evaluation_positioning: dict,
    regeneration_notes: str | None = None,
) -> dict:
    guidance = f"\n\nRegeneration notes:\n{regeneration_notes}" if regeneration_notes else ""
    return run_prompt(
        f"{PROMPT}\n\nNiche:\n{niche}\n\nBrand:\n{brand}\n\nEvaluation positioning:\n{evaluation_positioning}{guidance}"
    )
