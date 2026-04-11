from __future__ import annotations

from pathlib import Path

from app.services.llm_service import run_prompt

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "brand.txt"


def brand_agent(idea_json: dict) -> dict:
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    return run_prompt(f"{prompt}\n\nIdea:\n{idea_json}")
