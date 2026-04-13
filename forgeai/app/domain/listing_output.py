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

_VAGUE_AUDIENCE_PHRASES = (
    "everyone",
    "anybody",
    "all users",
    "general audience",
    "people everywhere",
    "for anyone",
    "for everybody",
    "all kinds of people",
    "all walks of life",
    "people of all",
)

_GENERIC_PROBLEM_PHRASES = (
    "stay productive",
    "be organized",
    "get more done",
    "be more productive",
    "stay on track",
    "manage your time",
    "improve productivity",
    "be more organized",
    "helps you organize",
    "helps you stay productive",
    "just be more productive",
)

# Title must signal WHO (audience) + WHAT — e.g. contain " for " or a concrete role/domain token.
_TITLE_AUDIENCE_TOKENS = (
    "developer",
    "engineer",
    "engineering",
    "founder",
    "founders",
    "startup",
    "startups",
    "writer",
    "writers",
    "teacher",
    "teachers",
    "nurse",
    "nurses",
    "parent",
    "parents",
    "student",
    "students",
    "manager",
    "managers",
    "marketer",
    "marketers",
    "designer",
    "designers",
    "freelancer",
    "freelancers",
    "entrepreneur",
    "entrepreneurs",
    "solopreneur",
    "remote",
    "software",
    "technical",
    "product manager",
    "consultant",
    "consultants",
    "analyst",
    "analysts",
    "creator",
    "creators",
    "content creator",
    "professional",
    "professionals",
    "team",
    "executive",
    "executives",
    "nursing",
    "educator",
    "educators",
)


def _validate_listing_specificity(output: dict) -> None:
    """Specificity enforcement: reject safe-but-vague positioning (next.md FIX 1)."""
    tu = output["target_user"].strip().lower()
    if len(output["target_user"].strip()) < 22:
        raise ValueError("target_user must be at least 22 characters with a concrete audience (not a single vague label).")

    for phrase in _VAGUE_AUDIENCE_PHRASES:
        if phrase in tu:
            raise ValueError(f"target_user is too vague (remove phrases like {phrase!r}; name a specific role or situation).")

    if len(tu.split()) <= 2 and tu in {"creators", "people", "users", "everyone", "founders"}:
        raise ValueError("target_user must describe WHO in context (not a one-word bucket).")

    cp = output["core_problem"].strip().lower()
    if len(output["core_problem"].strip()) < 28:
        raise ValueError("core_problem must be at least 28 characters and state a specific pain or job-to-be-done.")

    for phrase in _GENERIC_PROBLEM_PHRASES:
        if phrase in cp:
            raise ValueError(f"core_problem is too generic (avoid empty phrases like {phrase!r}; name the real friction).")

    title = output["title"].strip()
    tl = title.lower()
    words = title.split()
    if len(words) < 4:
        raise ValueError(
            "title must follow WHO + WHAT + context (min 4 words), e.g. "
            "'AI Prompt Engineering Logbook for Developers'."
        )
    if len(title) < 18:
        raise ValueError("title is too short to carry niche specificity.")

    if " for " not in tl and not any(tok in tl for tok in _TITLE_AUDIENCE_TOKENS):
        raise ValueError(
            "title must include a clear audience or domain (e.g. 'for Developers', 'for Startup Founders') "
            "or role tokens such as engineer, founder, nurse."
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

    for field in ("unique_value", "subtitle", "description"):
        val = output[field]
        if not isinstance(val, str) or not val.strip():
            raise ValueError(f"Invalid listing output: '{field}' must be a non-empty string")
        if len(val.strip()) < 12:
            raise ValueError(f"Invalid listing output: '{field}' is too vague (min 12 characters).")

    for field, min_len in (("target_user", 22), ("core_problem", 28)):
        val = output[field]
        if not isinstance(val, str) or not val.strip():
            raise ValueError(f"Invalid listing output: '{field}' must be a non-empty string")
        if len(val.strip()) < min_len:
            raise ValueError(f"Invalid listing output: '{field}' is too vague (min {min_len} characters).")

    tit = output["title"]
    if not isinstance(tit, str) or not tit.strip():
        raise ValueError("Invalid listing output: 'title' must be a non-empty string")
    if len(tit.strip()) < 18:
        raise ValueError("Invalid listing output: 'title' is too short for niche-specific positioning.")

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

    _validate_listing_specificity(output)
