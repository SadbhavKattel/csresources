"""Render TikTok fellowship slides (1080x1920) matching the original template.

Usage: python3 make_slides.py [slug ...]

A real logo dropped into logos/<slug>.png (or .jpg/.webp) always overrides
the logo spec in programs.json.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
FONT_PATH = ROOT / "assets" / "LeagueSpartan-Variable.ttf"
BACKGROUND = ROOT / "assets" / "background.png"

# Measured from the original Canva slides.
CENTER_X = 540
TITLE_TOP = 856          # cap-height top of the title line
TITLE_SIZE, TITLE_TRACK = 51, -3.0
DESC_TOP = 966           # cap-height top of the first description line
DESC_SIZE, DESC_TRACK = 51, -1.5
DESC_LINE_PITCH = 55.5
DESC_MAX_WIDTH = 760
MAX_DESC_LINES = 6
LOGO_BOX = (660, 380)    # max logo width/height
LOGO_CENTER_Y = 620
CARD_SIZE = (656, 194)   # white card, same size as the GSoC slide
CARD_TEXT_COLOR = (32, 33, 36)


def font(size):
    f = ImageFont.truetype(str(FONT_PATH), size)
    f.set_variation_by_name("Bold")
    return f


def line_width(f, text, track):
    return f.getlength(text) + track * (len(text) - 1)


def draw_line(draw, f, text, top, track):
    cap_offset = f.getbbox("H")[1]
    x0 = CENTER_X - line_width(f, text, track) / 2
    y = top - cap_offset
    for i, ch in enumerate(text):
        draw.text((x0 + f.getlength(text[:i]) + track * i, y), ch, font=f, fill=(0, 0, 0))


def wrap(f, text, max_width, track):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if line_width(f, trial, track) <= max_width:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    lines.append(cur)
    return lines


def fit(img, max_w, max_h):
    scale = min(max_w / img.width, max_h / img.height)
    return img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)


def make_card(spec):
    card = Image.new("RGBA", CARD_SIZE, (255, 255, 255, 255))
    parts = []
    if "mark" in spec:
        mark = Image.open(ROOT / spec["mark"]).convert("RGBA")
        mark = mark.crop(mark.getchannel("A").getbbox())
        parts.append(fit(mark, CARD_SIZE[0] - 80, spec.get("mark_height", 100)))
    if "text" in spec:
        room = CARD_SIZE[0] - 80 - sum(p.width + 24 for p in parts)
        size = 68
        while size > 30 and font(size).getlength(spec["text"]) > room:
            size -= 2
        f = font(size)
        l, t, r, b = f.getbbox(spec["text"])
        txt = Image.new("RGBA", (r - l, b - t), (0, 0, 0, 0))
        ImageDraw.Draw(txt).text((-l, -t), spec["text"], font=f, fill=CARD_TEXT_COLOR)
        parts.append(txt)
    total = sum(p.width for p in parts) + 24 * (len(parts) - 1)
    x = (CARD_SIZE[0] - total) // 2
    for p in parts:
        card.alpha_composite(p, (x, (CARD_SIZE[1] - p.height) // 2))
        x += p.width + 24
    return card


def load_logo(program):
    for ext in ("png", "jpg", "jpeg", "webp"):
        override = ROOT / "logos" / f"{program['slug']}.{ext}"
        if override.exists() and program["logo"].get("file") != f"logos/{override.name}":
            return fit(Image.open(override).convert("RGBA"), *LOGO_BOX)
    spec = program["logo"]
    if spec["type"] == "image":
        img = Image.open(ROOT / spec["file"]).convert("RGBA")
        return fit(img, LOGO_BOX[0], min(LOGO_BOX[1], spec.get("max_height", LOGO_BOX[1])))
    return make_card(spec)


def render(program, index):
    slide = Image.open(BACKGROUND).convert("RGBA")
    logo = load_logo(program)
    slide.alpha_composite(logo, (CENTER_X - logo.width // 2, LOGO_CENTER_Y - logo.height // 2))

    draw = ImageDraw.Draw(slide)
    title_font = font(TITLE_SIZE)
    if line_width(title_font, program["title"], TITLE_TRACK) > DESC_MAX_WIDTH:
        raise ValueError(f"title too long for one line: {program['title']}")
    draw_line(draw, title_font, program["title"], TITLE_TOP, TITLE_TRACK)

    desc_font = font(DESC_SIZE)
    lines = wrap(desc_font, program["description"], DESC_MAX_WIDTH, DESC_TRACK)
    if len(lines) > MAX_DESC_LINES:
        raise ValueError(f"description is {len(lines)} lines (max {MAX_DESC_LINES}): {program['slug']}")
    for i, line in enumerate(lines):
        draw_line(draw, desc_font, line, DESC_TOP + i * DESC_LINE_PITCH, DESC_TRACK)

    out = ROOT / "output" / f"{index:02d}-{program['slug']}.png"
    slide.convert("RGB").save(out, optimize=True)
    return out, len(lines)


def main():
    programs = json.loads((ROOT / "programs.json").read_text())
    wanted = set(sys.argv[1:])
    for i, program in enumerate(programs, 1):
        if wanted and program["slug"] not in wanted:
            continue
        out, n = render(program, i)
        print(f"{out.relative_to(ROOT)}  ({n} lines)")


if __name__ == "__main__":
    main()
