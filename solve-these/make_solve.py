"""Render the "solve these" TikTok series (1080x1920).

For each company: a minimal cover (dark + light, faint logo behind the text)
and a problem-list page styled like a dark-mode coding-practice app.

Usage: python3 make_solve.py [company ...]
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
FONTS = {
    "regular": ROOT / "assets" / "NimbusSans-Regular.otf",
    "bold": ROOT / "assets" / "NimbusSans-Bold.otf",
}
W, H = 1080, 1920
S = 2  # supersample factor for smooth edges

COVERS = {
    "google": [("you'll never get into google", "bold"), ("if you can't solve these.", "regular")],
    "amazon": [("you won't get into amazon", "bold"), ("if you don't know these yet.", "regular")],
    "microsoft": [("solve these if you want", "bold"), ("to get into microsoft.", "regular")],
}
NAMES = {"google": "Google", "amazon": "Amazon", "microsoft": "Microsoft"}
THEMES = {
    "dark": {"bg": (11, 11, 11), "fg": (255, 255, 255), "muted": (130, 130, 130), "mark": 0.07},
    "light": {"bg": (245, 244, 240), "fg": (14, 14, 14), "muted": (120, 120, 120), "mark": 0.05},
}

# Dark list palette.
LIST_BG = (26, 26, 26)
ROW_ALT = (40, 40, 40)
CHIP = (44, 44, 44)
TEXT = (238, 238, 238)
MUTED = (138, 138, 138)
TRACK = (62, 62, 62)
BAR = (255, 161, 22)
DIFF = {"Easy": ("Easy", (0, 184, 163)), "Medium": ("Med.", (255, 192, 30)), "Hard": ("Hard", (255, 55, 95))}


def font(weight, size):
    return ImageFont.truetype(str(FONTS[weight]), round(size * S))


def mark(company, height, color, opacity):
    m = Image.open(ROOT / "assets" / f"{company}-mark.png").convert("RGBA")
    m = m.resize((round(m.width * height * S / m.height), round(height * S)), Image.LANCZOS)
    tinted = Image.new("RGBA", m.size, color + (0,))
    tinted.putalpha(m.getchannel("A").point(lambda a: round(a * opacity)))
    return tinted


def finish(img, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    img.resize((W, H), Image.LANCZOS).convert("RGB").save(out, optimize=True)
    return out


def render_cover(company, theme):
    t = THEMES[theme]
    img = Image.new("RGBA", (W * S, H * S), t["bg"] + (255,))
    m = mark(company, 760, t["fg"], t["mark"])
    img.alpha_composite(m, ((W * S - m.width) // 2, (H * S - m.height) // 2))
    d = ImageDraw.Draw(img)

    d.text((W * S // 2, 300 * S), "solve these", font=font("regular", 30), fill=t["muted"], anchor="mt")
    lines = COVERS[company]
    pitch = 69
    y = H / 2 - pitch * len(lines) / 2
    for text, weight in lines:
        f = font(weight, 60)
        if f.getlength(text) > 940 * S:
            raise ValueError(f"cover line too wide: {text}")
        d.text((W * S // 2, round(y * S)), text, font=f, fill=t["fg"], anchor="mt")
        y += pitch
    return finish(img, ROOT / "output" / company / f"1-cover-{theme}.png")


def truncate(f, text, max_w):
    if f.getlength(text) <= max_w:
        return text
    while text and f.getlength(text + "…") > max_w:
        text = text[:-1]
    return text.rstrip() + "…"


def status_bar(d):
    d.text((80 * S, 44 * S), "9:41", font=font("bold", 32), fill=TEXT)
    x = 868
    for i, h in enumerate((10, 15, 20, 25)):  # signal bars
        d.rounded_rectangle(((x + i * 12) * S, (72 - h) * S, (x + i * 12 + 8) * S, 72 * S), 2 * S, fill=TEXT)
    d.rounded_rectangle((936 * S, 48 * S, 990 * S, 74 * S), 7 * S, outline=TEXT, width=2 * S)
    d.rounded_rectangle((940 * S, 52 * S, 978 * S, 70 * S), 4 * S, fill=TEXT)
    d.rounded_rectangle((992 * S, 56 * S, 996 * S, 66 * S), 2 * S, fill=TEXT)


def chip(d, x, y, label):
    f = font("regular", 30)
    w = f.getlength(label) / S + 52
    d.rounded_rectangle((x * S, y * S, (x + w) * S, (y + 64) * S), 32 * S, fill=CHIP)
    d.text(((x + w / 2) * S, (y + 32) * S), label, font=f, fill=TEXT, anchor="mm")
    return x + w + 16


def render_list(company, problems):
    img = Image.new("RGBA", (W * S, H * S), LIST_BG + (255,))
    d = ImageDraw.Draw(img)
    status_bar(d)

    # back chevron
    d.line([(78 * S, 168 * S), (60 * S, 186 * S), (78 * S, 204 * S)], fill=TEXT, width=5 * S, joint="curve")
    logo = mark(company, 56, TEXT, 1.0)
    img.alpha_composite(logo, (112 * S, round((186 - 28) * S)))
    d.text(((112 + logo.width / S + 22) * S, 186 * S), NAMES[company], font=font("bold", 52), fill=TEXT, anchor="lm")
    hard = sum(p["difficulty"] == "Hard" for p in problems)
    sub = f"{len(problems)} problems · {len(problems) - hard} medium · {hard} hard"
    d.text((60 * S, 252 * S), sub, font=font("regular", 32), fill=MUTED)

    x = 60
    for label in ("Last 6 months", "Medium + Hard", "Sort: Frequency"):
        x = chip(d, x, 324, label)

    small = font("regular", 28)
    d.text((70 * S, 440 * S), "Title", font=small, fill=MUTED)
    d.text((1010 * S, 440 * S), "Frequency", font=small, fill=MUTED, anchor="ra")

    title_f, meta_f = font("regular", 38), font("regular", 30)
    y0, row_h = 494, 128
    for i, p in enumerate(problems):
        top = y0 + i * row_h
        if i % 2 == 0:
            d.rounded_rectangle((40 * S, top * S, 1040 * S, (top + row_h) * S), 18 * S, fill=ROW_ALT)
        title = truncate(title_f, f"{p['id']}. {p['title']}", 690 * S)
        d.text((70 * S, (top + 26) * S), title, font=title_f, fill=TEXT)
        label, color = DIFF[p["difficulty"]]
        d.text((70 * S, (top + 78) * S), label, font=meta_f, fill=color)
        d.text((70 * S + meta_f.getlength(label + "  "), (top + 78) * S), "·  " + p["topic"], font=meta_f, fill=MUTED)
        cy = top + row_h / 2
        bx0, bx1 = 830, 1010
        d.rounded_rectangle((bx0 * S, (cy - 6) * S, bx1 * S, (cy + 6) * S), 6 * S, fill=TRACK)
        fill_to = bx0 + (bx1 - bx0) * max(p["frequency"], 6) / 100
        d.rounded_rectangle((bx0 * S, (cy - 6) * S, fill_to * S, (cy + 6) * S), 6 * S, fill=BAR)

    note_y = y0 + len(problems) * row_h + 40
    d.text((70 * S, note_y * S), "bar = how often it came up in interviews, last 6 months",
           font=font("regular", 26), fill=MUTED)
    return finish(img, ROOT / "output" / company / "2-problems.png")


def main():
    data = json.loads((ROOT / "problems.json").read_text())
    wanted = sys.argv[1:] or list(data)
    for company in wanted:
        for theme in THEMES:
            print(render_cover(company, theme).relative_to(ROOT))
        print(render_list(company, data[company]).relative_to(ROOT))


if __name__ == "__main__":
    main()
