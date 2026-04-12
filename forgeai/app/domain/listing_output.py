from __future__ import annotations

# Phrases that signal generic LLM listing fluff (case-insensitive).
_BANNED_SUBSTRINGS = (
    "unlock your potential",
    "elevate your",
    "transform your life",
    "game-changer",
    "game changer",
    "harness the full potential",
    "enhance creativity",
)


def validate_listing_output(output: dict) -> None:
    """Ensure listing agent output is safe to persist and export."""
    required_keys = (
        "target_user",
        "core_problem",
        "unique_value",
        "title",
        "subtitle",
        "description",
        "keywords",
    )
    missing = [key for key in required_keys if key not in output]
    if missing:
        raise ValueError(f"Invalid listing output: missing required keys: {', '.join(missing)}")

    for field in ("target_user", "core_problem", "unique_value", "title", "subtitle", "description"):
        val = output[field]
        if not isinstance(val, str) or not val.strip():
            raise ValueError(f"Invalid listing output: '{field}' must be a non-empty string")
        if len(val.strip()) < 12:
            raise ValueError(f"Invalid listing output: '{field}' is too vague (min 12 characters).")

    keywords = output["keywords"]
    if not isinstance(keywords, list):
        raise ValueError("Invalid listing output: 'keywords' must be a list of strings")
    invalid_keyword_items = [item for item in keywords if not isinstance(item, str)]
    if invalid_keyword_items:
        raise ValueError("Invalid listing output: 'keywords' must contain only strings")
    if len(keywords) < 3:
        raise ValueError("Invalid listing output: provide at least 3 keywords")

    combined = " ".join(
        [
            output["title"],
            output["subtitle"],
            output["description"],
        ]
    ).lower()
    for banned in _BANNED_SUBSTRINGS:
        if banned in combined:
            raise ValueError(f"Invalid listing output: remove generic phrase / cliché: {banned!r}")
