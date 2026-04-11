from __future__ import annotations

import json
import os

from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


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
    return json.loads(content)
