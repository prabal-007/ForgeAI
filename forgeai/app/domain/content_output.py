from __future__ import annotations

from typing import Any

_SECTION_TYPES = frozenset({"framework", "log", "template"})
_GENERIC_NAMES = frozenset(
    {
        "notes",
        "thoughts",
        "reflections",
        "daily reflections",
        "gratitude",
        "journal",
    }
)


def _is_legacy_section(section: dict[str, Any]) -> bool:
    """v1 sections used framework_usage + repeatable_cycle without type."""
    return "type" not in section and bool(section.get("framework_usage"))


def _is_legacy_content(output: dict[str, Any]) -> bool:
    sections = output.get("sections")
    if not isinstance(sections, list) or not sections:
        return False
    first = sections[0]
    return isinstance(first, dict) and _is_legacy_section(first)


def validate_content_output(output: dict[str, Any]) -> None:
    """
    Reject low-value notebook outputs.

    Accepts:
    - **v2** (preferred): system_name, target_user, core_problem, usage_frequency, typed sections
    - **v1 (legacy)**: sections with framework_usage / repeatable_cycle (for older DB rows)
    """
    if _is_legacy_content(output):
        _validate_legacy_content(output)
    else:
        _validate_v2_content(output)


def _validate_legacy_content(output: dict[str, Any]) -> None:
    sections = output.get("sections")
    if not isinstance(sections, list) or len(sections) < 3:
        raise ValueError("Content must include at least 3 sections (core frameworks / systems).")

    text_keys = ("name", "purpose", "framework_usage", "repeatable_cycle")
    for i, raw in enumerate(sections):
        if not isinstance(raw, dict):
            raise ValueError(f"Section {i} must be an object")
        if not _is_legacy_section(raw):
            raise ValueError(
                "Legacy content detected on first section but section "
                f"{i} is missing v1 fields (framework_usage). Regenerate with one consistent schema."
            )
        for key in text_keys:
            val = raw.get(key)
            if not isinstance(val, str) or not val.strip():
                raise ValueError(f"Section {i} missing or empty '{key}'")
        pages_raw = raw.get("pages")
        pages_ok = isinstance(pages_raw, (int, float)) and pages_raw >= 1 or (
            isinstance(pages_raw, str) and pages_raw.strip()
        )
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


def _validate_v2_content(output: dict[str, Any]) -> None:
    for key in ("system_name", "target_user", "core_problem", "usage_frequency"):
        val = output.get(key)
        if not isinstance(val, str) or not val.strip():
            raise ValueError(f"Content must include non-empty '{key}'")
        if len(val.strip()) < 8 and key != "usage_frequency":
            raise ValueError(f"Content '{key}' is too vague (min 8 characters).")

    uf = output["usage_frequency"].strip().lower()
    if "daily" not in uf and "weekly" not in uf:
        raise ValueError("Content 'usage_frequency' must indicate daily or weekly primary use.")

    sections = output.get("sections")
    if not isinstance(sections, list) or len(sections) < 3:
        raise ValueError("Content must include at least 3 typed sections.")

    for i, raw in enumerate(sections):
        if not isinstance(raw, dict):
            raise ValueError(f"Section {i} must be an object")
        if _is_legacy_section(raw):
            raise ValueError(
                f"Section {i} looks like v1 legacy (framework_usage without typed 'type'). "
                "Use v2 schema with type, instructions, and example_entry."
            )

        name = raw.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Section {i} missing 'name'")
        nkey = name.strip().lower()
        if nkey in _GENERIC_NAMES:
            raise ValueError(f"Section {i} name is too generic for a paid tool: {name!r}")

        st = raw.get("type")
        if not isinstance(st, str) or st.strip().lower() not in _SECTION_TYPES:
            raise ValueError(f"Section {i} 'type' must be one of: framework, log, template")

        for field, min_len in (("purpose", 30), ("instructions", 40), ("example_entry", 20)):
            val = raw.get(field)
            if not isinstance(val, str) or len(val.strip()) < min_len:
                raise ValueError(f"Section {i} '{field}' must be at least {min_len} characters.")

        if not isinstance(raw.get("repeatable"), bool):
            raise ValueError(f"Section {i} 'repeatable' must be a boolean")

        pages_raw = raw.get("pages")
        pages_ok = isinstance(pages_raw, (int, float)) and pages_raw >= 1 or (
            isinstance(pages_raw, str) and str(pages_raw).strip() and any(c.isdigit() for c in str(pages_raw))
        )
        if not pages_ok:
            raise ValueError(f"Section {i} 'pages' must be a positive integer (how many practice pages).")
