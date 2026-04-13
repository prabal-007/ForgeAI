from __future__ import annotations

from typing import Any

from app.domain.idea_output import niche_from_idea_output


def design_context_from_idea(data: dict[str, Any]) -> tuple[str, str]:
    """
    Derive positioning hints for the design agent from idea + brief (design runs before content).

    Returns (target_user_hint, core_problem_hint) — best-effort from niche list + brief.
    """
    idea = data.get("idea_output") or {}
    brief = str(data.get("brief") or "").strip()
    niche_label = niche_from_idea_output(idea, brief or "general niche")

    audience = ""
    reason = ""
    niches = idea.get("niches")
    if isinstance(niches, list) and niches:
        first = niches[0]
        if isinstance(first, dict):
            audience = str(first.get("audience") or "").strip()
            reason = str(first.get("reason") or "").strip()

    target_user = audience or niche_label
    core_problem = reason or brief
    if len(core_problem) < 30:
        core_problem = f"{brief} {niche_label}".strip()[:600] if brief else niche_label

    return target_user.strip() or niche_label, core_problem.strip() or brief or niche_label
