from __future__ import annotations

from pathlib import Path

from app.services.llm_service import run_prompt

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "trend.txt"


def trend_agent(brief: str) -> dict:
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    return run_prompt(f"{prompt}\n\nUser brief:\n{brief}")
