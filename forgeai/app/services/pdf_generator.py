from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen.canvas import Canvas

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "generated_assets" / "interiors"

# ── Layout constants ─────────────────────────────────────────────────────────
LM = 54.0                          # left margin  (tighter than before)
RM = LETTER[0] - 54.0              # right margin
TW = RM - LM                       # printable text width
TOP = LETTER[1] - 52.0             # top baseline for header row

# ── Palette ───────────────────────────────────────────────────────────────────
INK       = HexColor("#18191C")    # near-black body text
INK_GREY  = HexColor("#5A5F6B")    # secondary / instructions text
RULE      = HexColor("#C8CAD0")    # light horizontal rules
BOX_BG    = HexColor("#F5F6F8")    # field group background
BOX_EDGE  = HexColor("#D0D3DA")    # field group border
BADGE_BG  = HexColor("#E8EAF0")    # section-type pill background
ACCENT    = HexColor("#2E4FCC")    # accent stripe on title page
WHITE     = HexColor("#FFFFFF")

_SECTION_TYPES = frozenset({"framework", "log", "template"})


# ── Text helpers ──────────────────────────────────────────────────────────────

def _wrap(c: Canvas, text: str, font: str, size: float, max_w: float) -> list[str]:
    text = " ".join(text.split())
    if not text:
        return []

    def sw(parts: list[str]) -> float:
        return c.stringWidth(" ".join(parts), font, size) if parts else 0.0

    def break_word(w: str) -> list[str]:
        if sw([w]) <= max_w:
            return [w]
        chunks, buf = [], ""
        for ch in w:
            if c.stringWidth(buf + ch, font, size) <= max_w:
                buf += ch
            else:
                if buf:
                    chunks.append(buf)
                buf = ch
        if buf:
            chunks.append(buf)
        return chunks

    words: list[str] = []
    for w in text.split():
        words.extend(break_word(w))

    lines, cur = [], []
    for w in words:
        trial = cur + [w]
        if sw(trial) <= max_w:
            cur.append(w)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines


def _text_block(
    c: Canvas,
    text: str,
    font: str,
    size: float,
    color: Color,
    x: float,
    y: float,
    max_w: float,
    leading: float,
) -> float:
    """Draw wrapped text, return y after last line."""
    c.setFont(font, size)
    c.setFillColor(color)
    for ln in _wrap(c, text, font, size, max_w):
        c.drawString(x, y, ln)
        y -= leading
    return y


def _hrule(c: Canvas, y: float, x0: float = LM, x1: float = RM,
           color: Color = RULE, width: float = 0.5) -> None:
    c.setStrokeColor(color)
    c.setLineWidth(width)
    c.line(x0, y, x1, y)


def _box(c: Canvas, x: float, y: float, w: float, h: float,
         bg: Color = BOX_BG, edge: Color = BOX_EDGE, radius: float = 4.0) -> None:
    c.setFillColor(bg)
    c.setStrokeColor(edge)
    c.setLineWidth(0.6)
    c.roundRect(x, y, w, h, radius, fill=1, stroke=1)


def _page_header(c: Canvas, label: str, page_number: int) -> None:
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(INK_GREY)
    c.drawString(LM, TOP + 4, label)
    c.drawRightString(RM, TOP + 4, f"{page_number}")
    _hrule(c, TOP - 2, color=RULE, width=0.4)


# ── Page-count helpers ────────────────────────────────────────────────────────

def _coerce_pages(raw: Any, default: int = 1) -> int:
    if isinstance(raw, int):
        return max(1, min(raw, 40))
    if isinstance(raw, str):
        digits = "".join(ch for ch in raw if ch.isdigit())
        if digits:
            return max(1, min(int(digits), 40))
    return default


def _is_legacy(s: dict[str, Any]) -> bool:
    t = s.get("type")
    if isinstance(t, str) and t.strip().lower() in _SECTION_TYPES:
        return False
    return bool(s.get("framework_usage"))


def _n_pages(s: dict[str, Any]) -> int:
    if _is_legacy(s):
        return _coerce_pages(s.get("pages"), 1)
    raw = s.get("pages")
    if isinstance(raw, (int, float)) and raw >= 1:
        return max(1, min(int(raw), 40))
    if isinstance(raw, str) and any(ch.isdigit() for ch in raw):
        return _coerce_pages(raw, 3)
    t = str(s.get("type") or "template").lower()
    return {"framework": 4, "log": 5}.get(t, 3)


def _field_labels(s: dict[str, Any]) -> list[str]:
    collected: list[str] = []
    seen: set[str] = set()
    for block in (str(s.get("instructions") or ""), str(s.get("example_entry") or "")):
        for ln in block.splitlines():
            t = ln.strip().lstrip("-•\t ").strip()
            if 4 <= len(t) <= 52 and t.lower() not in seen:
                collected.append(t[:50])
                seen.add(t.lower())
            if len(collected) >= 6:
                break
        if len(collected) >= 6:
            break
    defaults = [
        "Primary input", "Context / constraints", "Expected output",
        "What happened", "Change next time", "Rating (1–5)",
    ]
    for d in defaults:
        if len(collected) >= 6:
            break
        if d.lower() not in seen:
            collected.append(d)
            seen.add(d.lower())
    return collected[:6]


# ── Practice-page renderers ───────────────────────────────────────────────────

def _draw_lined_page(c: Canvas, name: str, pg: int) -> None:
    """Legacy lined template — name in header, ruled lines."""
    _page_header(c, name, pg)
    y = TOP - 20
    while y > 72:
        _hrule(c, y, width=0.5)
        y -= 22


def _draw_framework_page(c: Canvas, section: dict[str, Any], pg: int) -> None:
    """Labelled field boxes grouped inside a rounded container."""
    height = LETTER[1]
    _page_header(c, f"{section.get('name', 'Framework')} — practice", pg)

    labels = _field_labels(section)
    field_h = 48.0
    gap     = 8.0
    pad_v   = 10.0
    pad_h   = 14.0
    inner_w = TW - 2 * pad_h
    total_h = len(labels) * (field_h + gap) - gap + 2 * pad_v

    box_y = TOP - 28 - total_h
    _box(c, LM, box_y, TW, total_h)

    y = box_y + total_h - pad_v - field_h
    for label in labels:
        # label text
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(INK)
        c.drawString(LM + pad_h, y + field_h - 14, label)
        # light rule at bottom of each field
        _hrule(c, y + 8, x0=LM + pad_h, x1=LM + pad_h + inner_w,
               color=BOX_EDGE, width=0.6)
        y -= field_h + gap


def _draw_log_page(c: Canvas, section: dict[str, Any], pg: int) -> None:
    """Structured log table with header row."""
    _page_header(c, f"{section.get('name', 'Log')} — log", pg)

    col_x  = [LM, LM + 110, LM + 268]
    col_w  = [110, 158, RM - (LM + 268)]
    hdr    = ("Date / ref", "Entry / event", "Outcome / notes")
    row_h  = 32.0
    pad    = 5.0

    # header row
    hdr_y = TOP - 24
    _box(c, LM, hdr_y - 4, TW, 20, bg=BADGE_BG, edge=BOX_EDGE, radius=3)
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(INK)
    for i, h in enumerate(hdr):
        c.drawString(col_x[i] + pad, hdr_y + 4, h)

    # column dividers in header
    c.setStrokeColor(BOX_EDGE)
    c.setLineWidth(0.5)
    for cx in col_x[1:]:
        c.line(cx, hdr_y - 4, cx, hdr_y + 16)

    y = hdr_y - 4 - row_h
    while y > 64:
        _hrule(c, y, width=0.45)
        # column dividers
        c.setStrokeColor(RULE)
        c.setLineWidth(0.35)
        for cx in col_x[1:]:
            c.line(cx, y, cx, y + row_h)
        y -= row_h


# ── Section intro pages ───────────────────────────────────────────────────────

def _draw_section_intro_v2(c: Canvas, section: dict[str, Any]) -> None:
    """Polished v2 intro: name, type badge, purpose, instructions, example."""
    height = LETTER[1]
    name = str(section.get("name") or "Section")
    st   = str(section.get("type") or "template").lower()
    rep  = section.get("repeatable", False)

    y = height - 58

    # accent left stripe
    c.setFillColor(ACCENT)
    c.rect(LM - 8, y - 6, 4, 24, fill=1, stroke=0)

    # section name
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(INK)
    c.drawString(LM + 2, y, name)
    y -= 26

    # type + repeatable badge
    badge = f"  {st.upper()}  ·  {'REPEATABLE' if rep else 'ONCE'}"
    bw = c.stringWidth(badge, "Helvetica-Bold", 8) + 8
    _box(c, LM, y - 2, bw, 14, bg=BADGE_BG, edge=BOX_EDGE, radius=3)
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(INK_GREY)
    c.drawString(LM + 4, y + 1, badge.strip())
    y -= 22

    _hrule(c, y, width=0.5)
    y -= 14

    # purpose
    purpose = str(section.get("purpose") or "").strip()
    if purpose:
        y = _text_block(c, purpose, "Helvetica-Bold", 11, INK, LM, y, TW, 15)
        y -= 10

    # instructions block in a box
    instructions = str(section.get("instructions") or "").strip()
    if instructions:
        lines = _wrap(c, f"Instructions: {instructions}", "Helvetica", 10, TW - 20)
        box_h = len(lines) * 14 + 14
        _box(c, LM, y - box_h + 4, TW, box_h, bg=BOX_BG, edge=BOX_EDGE)
        inner_y = y - 6
        c.setFont("Helvetica", 10)
        c.setFillColor(INK_GREY)
        for ln in lines:
            c.drawString(LM + 10, inner_y, ln)
            inner_y -= 14
        y = inner_y - 8

    # example entry
    example = str(section.get("example_entry") or "").strip()
    if example and y > 120:
        y = _text_block(c, f"Example: {example}", "Helvetica", 9, INK_GREY, LM, y, TW, 13)


def _draw_section_intro_legacy(c: Canvas, section: dict[str, Any]) -> None:
    height = LETTER[1]
    name  = str(section.get("name") or "Section")
    purp  = str(section.get("purpose") or "")
    fw    = str(section.get("framework_usage") or "")
    cycle = str(section.get("repeatable_cycle") or "")

    y = height - 68

    c.setFillColor(ACCENT)
    c.rect(LM - 8, y - 4, 4, 24, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(INK)
    c.drawString(LM + 2, y, name)
    y -= 28

    _hrule(c, y, width=0.5)
    y -= 14

    if purp:
        y = _text_block(c, f"Purpose: {purp}", "Helvetica-Bold", 11, INK, LM, y, TW, 15)
        y -= 8
    if fw:
        y = _text_block(c, f"How to use: {fw}", "Helvetica", 10, INK_GREY, LM, y, TW, 14)
        y -= 6
    if cycle:
        _text_block(c, f"Repeat: {cycle}", "Helvetica", 10, INK_GREY, LM, y, TW, 14)


# ── Title / system identity page ─────────────────────────────────────────────

def _draw_title_page(c: Canvas, content: dict[str, Any]) -> None:
    width, height = LETTER
    sn = str(content.get("system_name") or "").strip() or "Journal Interior"
    tu = str(content.get("target_user") or "").strip()
    cp = str(content.get("core_problem") or "").strip()
    uf = str(content.get("usage_frequency") or "").strip()
    sections = content.get("sections") or []

    # full-width accent bar at top
    c.setFillColor(ACCENT)
    c.rect(0, height - 64, width, 64, fill=1, stroke=0)

    # system name on accent
    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(WHITE)
    c.drawString(LM, height - 42, sn)

    y = height - 90

    # WHO and PROBLEM meta
    if tu:
        y = _text_block(c, tu, "Helvetica-Bold", 11, INK, LM, y, TW, 15)
        y -= 4
    if cp:
        y = _text_block(c, f"Core problem: {cp}", "Helvetica", 10, INK_GREY, LM, y, TW, 14)
        y -= 4
    if uf:
        y = _text_block(c, f"Cadence: {uf}", "Helvetica", 10, INK_GREY, LM, y, TW, 13)
        y -= 16

    _hrule(c, y, width=0.6)
    y -= 20

    # "How to use this system" — 3 steps derived from first 3 section names
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(INK)
    c.drawString(LM, y, "How to use this system")
    y -= 18

    step_names = [str(s.get("name") or "") for s in sections if isinstance(s, dict)][:3]
    default_steps = [
        "Complete each section in order on your chosen cadence.",
        "Review your entries weekly to spot patterns and progress.",
        "Adjust your approach based on what the data tells you.",
    ]
    steps = step_names if len(step_names) >= 3 else default_steps

    for i, step in enumerate(steps[:3], 1):
        # numbered circle
        cx, cy = LM + 8, y + 4
        c.setFillColor(ACCENT)
        c.circle(cx, cy, 8, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(WHITE)
        c.drawCentredString(cx, cy - 3, str(i))
        # step text
        c.setFont("Helvetica", 10)
        c.setFillColor(INK)
        c.drawString(LM + 22, y, step[:90])
        y -= 22

    y -= 8
    _hrule(c, y, width=0.4)

    # sections overview
    y -= 14
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(INK)
    c.drawString(LM, y, "What's inside")
    y -= 14
    for s in sections:
        if not isinstance(s, dict):
            continue
        name = str(s.get("name") or "")
        stype = str(s.get("type") or "section").lower()
        badge = f"[{stype}]"
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(INK_GREY)
        bw = c.stringWidth(badge + "  ", "Helvetica-Bold", 9)
        c.drawString(LM, y, badge)
        c.setFont("Helvetica", 9)
        c.setFillColor(INK)
        c.drawString(LM + bw, y, name)
        y -= 14
        if y < 72:
            break

    # footer
    c.setFont("Helvetica", 8)
    c.setFillColor(INK_GREY)
    c.drawCentredString(width / 2, 36, "Generated by ForgeAI")


def _draw_title_page_legacy(c: Canvas) -> None:
    width, height = LETTER
    c.setFillColor(ACCENT)
    c.rect(0, height - 64, width, 64, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 24)
    c.setFillColor(WHITE)
    c.drawCentredString(width / 2, height - 40, "Journal Interior")
    c.setFont("Helvetica", 9)
    c.setFillColor(INK_GREY)
    c.drawCentredString(width / 2, 36, "Generated by ForgeAI")


# ── Public entry point ────────────────────────────────────────────────────────

def generate_interior_pdf(*, content: dict[str, Any], output_name: str) -> str:
    """
    Build interior PDF from full content object.
    v2 sections (type / instructions / example_entry) → polished practice pages.
    Legacy v1 sections (framework_usage) → classic lined template.
    """
    sections = content.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ValueError("Cannot generate interior PDF without content.sections")

    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DEFAULT_OUTPUT_DIR / f"{output_name}.pdf"

    c = Canvas(str(output_path), pagesize=LETTER)

    # ── Title / identity page ─────────────────────────────────────────────────
    has_v2 = bool(
        str(content.get("system_name") or "").strip()
        or str(content.get("target_user") or "").strip()
    )
    if has_v2:
        _draw_title_page(c, content)
    else:
        _draw_title_page_legacy(c)
    c.showPage()

    pg = 1
    for section in sections:
        if not isinstance(section, dict):
            continue

        legacy = _is_legacy(section)
        n_pgs  = _n_pages(section)
        sname  = str(section.get("name") or "Section")
        stype  = str(section.get("type") or "template").lower()

        # intro page
        if legacy:
            _draw_section_intro_legacy(c, section)
        else:
            _draw_section_intro_v2(c, section)
        c.showPage()
        pg += 1

        # practice pages
        for _ in range(n_pgs):
            if legacy or stype == "template":
                _draw_lined_page(c, sname, pg)
            elif stype == "framework":
                _draw_framework_page(c, section, pg)
            elif stype == "log":
                _draw_log_page(c, section, pg)
            else:
                _draw_lined_page(c, sname, pg)
            c.showPage()
            pg += 1

    c.save()
    return str(output_path)
