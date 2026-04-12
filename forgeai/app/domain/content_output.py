from __future__ import annotations

from typing import Any


def validate_content_output(output: dict[str, Any]) -> None:
    """
    Reject thin 'lined notebook' style outputs.

    Expects structured systems with explicit usage and repeatability per section.
    """
    sections = output.get("sections")
    if not isinstance(sections, list) or len(sections) < 3:
        raise ValueError("Content must include at least 3 sections (core frameworks / systems).")

    text_keys = ("name", "purpose", "framework_usage", "repeatable_cycle")
    for i, raw in enumerate(sections):
        if not isinstance(raw, dict):
            raise ValueError(f"Section {i} must be an object")
        for key in text_keys:
            val = raw.get(key)
            if not isinstance(val, str) or not val.strip():
                raise ValueError(f"Section {i} missing or empty '{key}'")
        pages_raw = raw.get("pages")
        pages_ok = False
        if isinstance(pages_raw, (int, float)) and pages_raw >= 1:
            pages_ok = True
        elif isinstance(pages_raw, str) and pages_raw.strip():
            pages_ok = True
        if not pages_ok:
            raise ValueError(f"Section {i} missing or invalid 'pages'")

        purpose = raw["purpose"].strip()
        if len(purpose) < 40:
            raise ValueError(f"Section {i} 'purpose' must be at least 40 characters (specific, actionable).")

        fu = raw["framework_usage"].strip()
        if len(fu) < 25:
            raise ValueError(f"Section {i} 'framework_usage' must explain how to use the framework (min 25 chars).")

        name_lower = raw["name"].strip().lower()
        vague = ("lined", "blank", "notes page", "journal page", "empty page")
        if any(v in name_lower for v in vague):
            raise ValueError(f"Section {i} name looks like filler pages, not a system: {raw['name']!r}")
