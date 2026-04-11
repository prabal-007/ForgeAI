from __future__ import annotations

from pathlib import Path

from app.services.llm_service import run_prompt

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "brand.txt"


def brand_agent(idea_json: dict, regeneration_notes: str | None = None) -> dict:
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    guidance = f"\n\nRegeneration notes:\n{regeneration_notes}" if regeneration_notes else ""
    return run_prompt(f"{prompt}\n\nIdea:\n{idea_json}{guidance}")
