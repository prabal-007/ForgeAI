"""
Programmatic KDP cover generator using Pillow.

Produces a 1600×2560 PNG (standard Kindle / KDP ebook ratio) with:
- Solid brand-colour background
- Large legible title (listing title — 100% reliable text rendering)
- Subtitle
- Brand name + tagline at the bottom

Zero AI image API calls, zero garbled text, zero tokens cost.
"""
from __future__ import annotations

import io
import math
import os
from pathlib import Path
from typing import Any

# ── KDP dimensions ─────────────────────────────────────────────────────────────
W, H = 1600, 2560   # standard Kindle ebook cover (px)

# ── Colour helpers ─────────────────────────────────────────────────────────────

def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"Bad hex: {hex_color!r}")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = (c / 255.0 for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _darken(rgb: tuple[int, int, int], factor: float = 0.55) -> tuple[int, int, int]:
    return tuple(max(0, int(c * factor)) for c in rgb)  # type: ignore[return-value]


def _lighten(rgb: tuple[int, int, int], factor: float = 1.35) -> tuple[int, int, int]:
    return tuple(min(255, int(c * factor)) for c in rgb)  # type: ignore[return-value]


def _blend(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))  # type: ignore[return-value]


def _readable_fg(bg: tuple[int, int, int]) -> tuple[int, int, int]:
    """Return white or near-black depending on background luminance."""
    return (248, 249, 252) if _luminance(bg) < 0.45 else (18, 20, 26)


def _parse_palette(color_palette: Any) -> list[tuple[int, int, int]]:
    """Extract usable RGB tuples from brand color_palette (list of hex strings)."""
    if not isinstance(color_palette, list):
        return []
    out: list[tuple[int, int, int]] = []
    for entry in color_palette:
        if isinstance(entry, str):
            try:
                out.append(_hex_to_rgb(entry))
            except ValueError:
                pass
    return out


def _choose_colors(
    palette: list[tuple[int, int, int]],
) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    """
    Pick (background, accent, text) from palette.
    Falls back to a professional deep-navy set if palette is empty or all-light.
    """
    default_bg     = (16, 28, 54)
    default_accent = (46, 79, 204)
    default_text   = (248, 249, 252)

    if not palette:
        return default_bg, default_accent, default_text

    # Prefer the darkest colour as bg (best contrast for white text on cover)
    sorted_pal = sorted(palette, key=lambda c: _luminance(c))
    bg = sorted_pal[0]
    if _luminance(bg) > 0.5:
        bg = _darken(bg, 0.4)

    # Accent = second colour, or a lightened version of bg
    accent = sorted_pal[1] if len(sorted_pal) >= 2 else _lighten(bg, 1.6)

    text = _readable_fg(bg)
    return bg, accent, text


# ── Font helpers ──────────────────────────────────────────────────────────────

def _find_font(bold: bool = True) -> str | None:
    candidates = (
        [
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\calibrib.ttf",
            r"C:\Windows\Fonts\segoeuib.ttf",
            r"C:\Windows\Fonts\trebucbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        ]
        if bold
        else [
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\calibri.ttf",
            r"C:\Windows\Fonts\segoeui.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        ]
    )
    for p in candidates:
        if Path(p).is_file():
            return p
    return None


def _load_font(path: str | None, size: int):
    from PIL import ImageFont
    if path:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _text_w(draw, text: str, font) -> int:
    try:
        bb = draw.textbbox((0, 0), text, font=font)
        return bb[2] - bb[0]
    except AttributeError:
        return int(draw.textlength(text, font=font))


def _wrap(draw, text: str, font, max_w: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = (cur + " " + w).strip()
        if _text_w(draw, trial, font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [text]


# ── Geometric decoration ──────────────────────────────────────────────────────

def _draw_gradient_bg(draw, bg: tuple[int, int, int], accent: tuple[int, int, int]) -> None:
    """Subtle vertical gradient from bg_dark at top to slightly lighter at bottom."""
    dark = _darken(bg, 0.75)
    for y in range(H):
        t = y / H
        color = _blend(dark, bg, t)
        draw.line([(0, y), (W, y)], fill=color)


def _draw_geometric_elements(draw, bg, accent, text_color) -> None:
    """Tasteful geometric accents — horizontal rules, corner marks, diagonal stripe."""
    a_muted = _blend(accent, bg, 0.55)     # softened accent

    # top accent bar
    draw.rectangle([(0, 0), (W, 18)], fill=accent)

    # thick horizontal divider at ~38% height (title zone separator)
    div_y = int(H * 0.38)
    draw.rectangle([(80, div_y), (W - 80, div_y + 6)], fill=accent)

    # thin rule above bottom zone
    bot_y = int(H * 0.84)
    draw.rectangle([(80, bot_y), (W - 80, bot_y + 2)], fill=a_muted)

    # corner notch — top-left
    notch = 40
    draw.polygon([(0, 18), (notch, 18), (0, 18 + notch)], fill=a_muted)

    # bottom accent bar
    draw.rectangle([(0, H - 16), (W, H)], fill=accent)


# ── Text drawing ──────────────────────────────────────────────────────────────

def _draw_centered_wrapped(
    draw,
    text: str,
    font,
    text_color: tuple[int, int, int],
    center_x: int,
    start_y: int,
    max_w: int,
    leading: int,
) -> int:
    """Draw centred wrapped text; return y after last line."""
    lines = _wrap(draw, text, font, max_w)
    y = start_y
    for ln in lines:
        tw = _text_w(draw, ln, font)
        draw.text((center_x - tw // 2, y), ln, font=font, fill=text_color)
        y += leading
    return y


# ── Main generator ────────────────────────────────────────────────────────────

def generate_programmatic_cover(
    *,
    title: str,
    subtitle: str = "",
    brand_name: str = "",
    tagline: str = "",
    color_palette: list[str] | None = None,
    niche: str = "",
) -> bytes:
    """
    Render a professional KDP cover PNG (1600×2560) and return bytes.

    All text is rendered via Pillow with system fonts → 100% legible, no AI artefacts.
    """
    from PIL import Image, ImageDraw

    palette = _parse_palette(color_palette or [])
    bg, accent, text_color = _choose_colors(palette)
    muted = _blend(text_color, bg, 0.5)

    img  = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    _draw_gradient_bg(draw, bg, accent)
    _draw_geometric_elements(draw, bg, accent, text_color)

    cx        = W // 2
    margin    = int(W * 0.08)
    max_tw    = W - 2 * margin

    bold_path = _find_font(bold=True)
    reg_path  = _find_font(bold=False)

    # ── Category / niche label (small caps above title) ──────────────────────
    cat_font = _load_font(reg_path, 42)
    niche_label = niche.upper()[:60] if niche else ""
    if niche_label:
        nw = _text_w(draw, niche_label, cat_font)
        draw.text((cx - nw // 2, int(H * 0.07)), niche_label, font=cat_font, fill=muted)

    # ── Title ─────────────────────────────────────────────────────────────────
    # Auto-size: start large, shrink until it wraps ≤ 3 lines
    title_size = 145
    while title_size > 60:
        tf = _load_font(bold_path, title_size)
        lines = _wrap(draw, title, tf, max_tw)
        if len(lines) <= 3:
            break
        title_size -= 8
    title_font    = _load_font(bold_path, title_size)
    title_leading = int(title_size * 1.22)
    title_top     = int(H * 0.115) if not niche_label else int(H * 0.14)
    after_title   = _draw_centered_wrapped(
        draw, title, title_font, text_color, cx, title_top, max_tw, title_leading
    )

    # ── Subtitle ──────────────────────────────────────────────────────────────
    if subtitle.strip():
        sub_font    = _load_font(reg_path, 58)
        sub_leading = 72
        sub_top     = after_title + int(H * 0.022)
        _draw_centered_wrapped(
            draw, subtitle, sub_font, muted, cx, sub_top, max_tw, sub_leading
        )

    # ── Mid-section decorative rule (already drawn in geometric elements) ─────

    # ── Bottom zone: brand name + tagline ─────────────────────────────────────
    brand_font   = _load_font(bold_path, 52)
    tag_font     = _load_font(reg_path, 40)
    brand_y      = int(H * 0.87)

    if brand_name.strip():
        bw = _text_w(draw, brand_name, brand_font)
        draw.text((cx - bw // 2, brand_y), brand_name, font=brand_font, fill=text_color)
        brand_y += 64

    if tagline.strip():
        tw2 = _text_w(draw, tagline[:90], tag_font)
        draw.text((cx - tw2 // 2, brand_y), tagline[:90], font=tag_font, fill=muted)

    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()


def cover_mode() -> str:
    """
    COVER_MODE env var:
      'programmatic' (default) — fast, reliable, zero API cost
      'ai'                     — DALL-E / image model (opt-in, costs tokens)
    """
    return os.getenv("COVER_MODE", "programmatic").strip().lower()
