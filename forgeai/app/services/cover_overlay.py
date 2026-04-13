from __future__ import annotations

import io
import os
from pathlib import Path


def _find_bold_font() -> str | None:
    candidates = [
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibrib.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for p in candidates:
        if Path(p).is_file():
            return p
    return None


def _find_regular_font() -> str | None:
    candidates = [
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for p in candidates:
        if Path(p).is_file():
            return p
    return None


def _wrap_text(draw_ref, text: str, font, max_width: int) -> list[str]:
    """Word-wrap text to fit max_width pixels."""
    from PIL import ImageFont
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = (current + " " + word).strip()
        try:
            bb = draw_ref.textbbox((0, 0), trial, font=font)
            w = bb[2] - bb[0]
        except AttributeError:
            w = draw_ref.textlength(trial, font=font)
        if w <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def apply_cover_title_overlay(
    image_bytes: bytes,
    title: str,
    subtitle: str = "",
    *,
    dark_band: bool = True,
) -> bytes:
    """
    Composite a branded title + subtitle band on the TOP of the cover image.

    Keeps original artwork visible below the band.
    title    → large bold white text (should be the KDP listing title)
    subtitle → smaller grey text (tagline or subtitle from listing)
    """
    from PIL import Image, ImageDraw, ImageFont

    title    = (title or "Journal").strip()[:120]
    subtitle = (subtitle or "").strip()[:160]

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h = img.size

    bold_path = _find_bold_font()
    reg_path  = _find_regular_font() or bold_path

    # responsive font sizes relative to image height
    title_sz = max(24, int(h * 0.042))
    sub_sz   = max(15, int(h * 0.024))
    margin   = int(w * 0.05)
    inner_w  = w - 2 * margin

    try:
        title_font = ImageFont.truetype(bold_path, title_sz)  if bold_path else ImageFont.load_default()
        sub_font   = ImageFont.truetype(reg_path,  sub_sz)    if reg_path  else title_font
    except OSError:
        title_font = ImageFont.load_default()
        sub_font   = title_font

    # measure wrapped lines
    probe = ImageDraw.Draw(img)
    title_lines = _wrap_text(probe, title, title_font, inner_w)
    sub_lines   = _wrap_text(probe, subtitle, sub_font, inner_w) if subtitle else []

    line_gap_t  = int(title_sz * 1.25)
    line_gap_s  = int(sub_sz   * 1.30)
    pad_v       = int(h * 0.022)
    gap_between = int(h * 0.012) if sub_lines else 0

    band_h = (
        pad_v
        + len(title_lines) * line_gap_t
        + gap_between
        + len(sub_lines)   * line_gap_s
        + pad_v
    )
    band_h = max(band_h, int(h * 0.14))

    # draw band
    overlay = Image.new("RGBA", (w, band_h), (14, 18, 30, 230))  # deep navy, semi-opaque
    img_rgba = img.convert("RGBA")
    img_rgba.paste(overlay, (0, 0), overlay)
    img = img_rgba.convert("RGB")

    draw = ImageDraw.Draw(img)

    # accent stripe at bottom of band
    draw.rectangle((0, band_h - 3, w, band_h), fill=(46, 79, 204))

    # title lines
    y = pad_v
    for ln in title_lines:
        draw.text((margin, y), ln, font=title_font, fill=(248, 250, 255))
        y += line_gap_t

    # subtitle lines
    y += gap_between
    for ln in sub_lines:
        draw.text((margin, y), ln, font=sub_font, fill=(185, 195, 215))
        y += line_gap_s

    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()


def reapply_overlay_from_listing(
    image_path: str,
    listing_title: str,
    listing_subtitle: str = "",
) -> bytes:
    """
    Load an existing cover PNG and re-composite with the final listing title.
    Returns new PNG bytes (caller must save).
    """
    raw = Path(image_path).read_bytes()
    return apply_cover_title_overlay(raw, listing_title, listing_subtitle)


def overlay_enabled() -> bool:
    return os.getenv("COVER_TEXT_OVERLAY", "true").strip().lower() in ("1", "true", "yes")
