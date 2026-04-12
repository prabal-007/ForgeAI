from __future__ import annotations


def validate_listing_output(output: dict) -> None:
    """Ensure listing agent output is safe to persist and export."""
    required_keys = ("title", "subtitle", "description", "keywords")
    missing = [key for key in required_keys if key not in output]
    if missing:
        raise ValueError(f"Invalid listing output: missing required keys: {', '.join(missing)}")

    for field in ("title", "subtitle", "description"):
        if not isinstance(output[field], str):
            raise ValueError(f"Invalid listing output: '{field}' must be a string")

    keywords = output["keywords"]
    if not isinstance(keywords, list):
        raise ValueError("Invalid listing output: 'keywords' must be a list of strings")
    invalid_keyword_items = [item for item in keywords if not isinstance(item, str)]
    if invalid_keyword_items:
        raise ValueError("Invalid listing output: 'keywords' must contain only strings")
