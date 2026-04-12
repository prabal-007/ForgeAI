from __future__ import annotations

import io
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def _find_system_font() -> str | None:
    candidates = [
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for p in candidates:
        if Path(p).is_file():
            return p
    return None


def apply_cover_title_overlay(image_bytes: bytes, title: str, subtitle: str) -> bytes:
    """
    Draw a readable title + optional subtitle on the upper portion of the cover.

    Keeps the generated artwork but adds buyer-facing text (niche / brand clarity).
    """
    from PIL import Image, ImageDraw, ImageFont

    title = (title or "Journal").strip()[:72]
    subtitle = (subtitle or "").strip()[:140]

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h = img.size
    draw = ImageDraw.Draw(img)

    font_path = _find_system_font()
    title_size = max(22, int(h * 0.038))
    sub_size = max(14, int(h * 0.022))
    try:
        if font_path:
            title_font = ImageFont.truetype(font_path, title_size)
            sub_font = ImageFont.truetype(font_path, max(12, sub_size - 2))
        else:
            title_font = ImageFont.load_default()
            sub_font = title_font
    except OSError:
        title_font = ImageFont.load_default()
        sub_font = title_font

    bar_top = int(h * 0.02)
    bar_bottom = int(h * 0.19)
    draw.rectangle((0, bar_top, w, bar_bottom), fill=(18, 22, 30))

    margin = int(w * 0.045)
    y = int(h * 0.055)
    draw.text((margin, y), title, font=title_font, fill=(248, 248, 252))
    try:
        bbox = draw.textbbox((margin, y), title, font=title_font)
        y = bbox[3] + int(h * 0.018)
    except AttributeError:
        y += title_size + max(8, int(h * 0.01))
    if subtitle:
        draw.text((margin, y), subtitle, font=sub_font, fill=(210, 215, 225))

    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()


def overlay_enabled() -> bool:
    return os.getenv("COVER_TEXT_OVERLAY", "true").strip().lower() in ("1", "true", "yes")
