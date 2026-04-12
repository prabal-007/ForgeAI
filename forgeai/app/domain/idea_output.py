from __future__ import annotations

from typing import Any


def niche_from_idea_output(idea_output: Any, brief_fallback: str) -> str:
    """
    Resolve a single niche string for design/content/listing.

    Supports:
    - Top-level string field \"niche\" (preferred)
    - trend_agent shape: { \"niches\": [ { \"niche\": \"...\" }, ... ] }
    """
    if not isinstance(idea_output, dict):
        return brief_fallback

    direct = idea_output.get("niche")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    niches = idea_output.get("niches")
    if isinstance(niches, list):
        for item in niches:
            if isinstance(item, dict):
                label = item.get("niche")
                if isinstance(label, str) and label.strip():
                    return label.strip()

    return brief_fallback
