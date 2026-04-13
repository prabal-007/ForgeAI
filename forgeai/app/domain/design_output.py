from __future__ import annotations

import re
from typing import Any


def validate_design_output(
    output: dict[str, Any],
    *,
    niche: str,
    target_user: str,
    core_problem: str,
) -> None:
    """
    Reject design concepts that are pure aesthetics without domain/audience signal.

    Complements the design prompt; keeps outputs tied to conversion + niche.
    """
    concepts = output.get("concepts")
    if not isinstance(concepts, list) or len(concepts) != 3:
        raise ValueError("Design output must include exactly 3 concepts.")

    blob = ""
    for i, c in enumerate(concepts):
        if not isinstance(c, dict):
            raise ValueError(f"Concept {i} must be an object")
        for key in ("style", "prompt", "layout_notes"):
            v = c.get(key)
            if not isinstance(v, str) or len(v.strip()) < 12:
                raise ValueError(f"Concept {i} '{key}' is missing or too short")
        p = str(c.get("prompt", ""))
        if len(p.strip()) < 55:
            raise ValueError(f"Concept {i} 'prompt' must be at least 55 characters (specific visual brief).")
        blob += " " + p.lower() + " " + str(c.get("layout_notes", "")).lower()

    # Tie visuals to niche: at least one significant token from niche appears in prompts
    niche_tokens = [w for w in re.findall(r"[a-z0-9]+", niche.lower()) if len(w) >= 4][:8]
    if niche_tokens:
        if not any(t in blob for t in niche_tokens):
            raise ValueError(
                "Cover design prompts must include concrete terms from the niche (not generic abstract-only art)."
            )

    # Audience / problem hints should surface in at least one prompt when provided
    hint_blob = f"{target_user.lower()} {core_problem.lower()}"
    hint_words = [w for w in re.findall(r"[a-z0-9]+", hint_blob) if len(w) >= 5][:10]
    for w in hint_words:
        if w in blob:
            break
    else:
        if len(hint_words) >= 2:
            raise ValueError(
                "Cover design prompts should reflect target_user / problem context (add domain cues, props, or setting)."
            )

