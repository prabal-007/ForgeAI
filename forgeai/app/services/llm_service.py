from __future__ import annotations

import json
import logging
import os

from openai import OpenAI

logger = logging.getLogger(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class LLMResponseError(ValueError):
    pass


def run_prompt(prompt: str) -> dict:
    """Run prompt and force JSON object output."""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "Return only valid JSON."},
            {"role": "user", "content": prompt},
        ],
    )
    content = response.choices[0].message.content or "{}"
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON from LLM response: %s", content)
        raise LLMResponseError("LLM returned invalid JSON") from exc
