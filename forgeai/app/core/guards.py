from __future__ import annotations

import re
from typing import Iterable

BLACKLIST = {
    "ironman",
    "avengers",
    "naruto",
    "batman",
    "spiderman",
    "superman",
    "captain america",
}

BANNED_PATTERNS = (
    re.compile(r"\binspired\s+by\b", re.IGNORECASE),
    re.compile(r"\blike\s+[\w\s-]{1,40}\b", re.IGNORECASE),
)

VISUAL_RISK_KEYWORDS = {
    "armor suit",
    "glowing eyes",
    "superhero",
    "cape",
    "mask",
}


def _collect_hits(text: str, dictionary: Iterable[str]) -> list[str]:
    lowered = text.lower()
    return [item for item in dictionary if item in lowered]


def run_guardrails(text: str) -> dict:
    """Hard-gate compliance checks before LLM analysis."""
    issues: list[str] = []

    blacklist_hits = _collect_hits(text, BLACKLIST)
    if blacklist_hits:
        issues.extend([f"Blacklisted keyword: {hit}" for hit in blacklist_hits])

    for pattern in BANNED_PATTERNS:
        if pattern.search(text):
            issues.append(f"Banned phrase pattern: {pattern.pattern}")

    visual_hits = _collect_hits(text, VISUAL_RISK_KEYWORDS)
    if visual_hits:
        issues.extend([f"Visual IP risk cue: {hit}" for hit in visual_hits])

    if issues:
        return {
            "decision": "fail",
            "risk": "high",
            "issues": issues,
        }

    return {
        "decision": "pass",
        "risk": "low",
        "issues": [],
    }
