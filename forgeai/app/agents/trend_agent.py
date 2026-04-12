from __future__ import annotations

from pathlib import Path

from app.services.llm_service import run_prompt

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "trend.txt"
PROMPT = PROMPT_PATH.read_text(encoding="utf-8")


def trend_agent(brief: str, regeneration_notes: str | None = None) -> dict:
    guidance = f"\n\nRegeneration notes:\n{regeneration_notes}" if regeneration_notes else ""
    return run_prompt(f"{PROMPT}\n\nUser brief:\n{brief}{guidance}")
