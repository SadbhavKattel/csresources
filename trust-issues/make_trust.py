"""Render the "trust issues" TikTok series (1080x1920).

Each post: 1-cover, 2-question (the AI-written code), 3-answer (what's wrong + the fix).
Usage: python3 make_trust.py [slug ...]
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pygments import lex
from pygments.lexers import get_lexer_by_name
from pygments.token import Comment, Keyword, Name, Number, Operator, String, Token

from posts import POSTS

ROOT = Path(__file__).resolve().parent
A = ROOT / "assets"
W, H, S = 1080, 1920, 2
SERIES = "trust issues"

BG = (11, 11, 11)
FG = (245, 245, 245)
MUTED = (125, 125, 125)
CARD = (21, 21, 22)
CARD_EDGE = (40, 40, 42)
GUTTER = (78, 78, 82)
RED_BG, RED = (63, 24, 24), (255, 123, 114)
GREEN_BG, GREEN = (20, 52, 30), (86, 211, 100)

# GitHub-dark-like syntax palette
SYNTAX = [
    (Comment, (139, 148, 158)),
    (String, (165, 214, 255)),
    (Number, (121, 192, 255)),
    (Keyword.Constant, (121, 192, 255)),
    (Keyword, (255, 123, 114)),
    (Operator.Word, (255, 123, 114)),
    (Name.Builtin, (255, 166, 87)),
    (Name.Function, (210, 168, 255)),
    (Name.Class, (255, 166, 87)),
    (Name.Tag, (126, 231, 135)),
    (Name.Attribute, (121, 192, 255)),
]
CODE_FG = (230, 237, 243)


def sans(weight, size):
    return ImageFont.truetype(str(A / f"NimbusSans-{weight.capitalize()}.otf"), round(size * S))


def mono(size, bold=False):
    # BASIC layout = no ligatures, so == != => render as typed
    return ImageFont.truetype(str(A / f"JetBrainsMono-{'Bold' if bold else 'Regular'}.ttf"), round(size * S),
                              layout_engine=ImageFont.Layout.BASIC)


def color_for(tok):
    for t, c in SYNTAX:
        if tok in t:
            return c
    return CODE_FG


def tokens(line, lang):
    out = []
    for tok, val in lex(line, get_lexer_by_name(lang)):
        val = val.rstrip("\n")
        if val:
            out.append((val, color_for(tok)))
    return out


def wrap(f, text, max_w):
    lines, cur = [], ""
    for word in text.split(" "):
        trial = f"{cur} {word}".strip()
        if f.getlength(trial) <= max_w * S:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    lines.append(cur)
    return lines


def canvas():
    img = Image.new("RGB", (W * S, H * S), BG)
    return img, ImageDraw.Draw(img)


def centered(layer, content_bottom):
    """Paste a content layer drawn from y=0 so the block sits centred above TikTok's caption area."""
    img = Image.new("RGB", (W * S, H * S), BG)
    h = content_bottom - 200
    top = max(170, round(860 - h / 2)) - 200
    img.paste(layer, (0, top * S))
    return img


def finish(img, slug, name):
    out = ROOT / "output" / slug / name
    out.parent.mkdir(parents=True, exist_ok=True)
    img.resize((W, H), Image.LANCZOS).save(out, optimize=True)
    return out


def tag(d, n, suffix=""):
    d.text((70 * S, 200 * S), f"{SERIES} · {n:02d}{suffix}", font=sans("regular", 30), fill=MUTED)


def paragraph(d, text, y, size=40, weight="regular", fill=FG, max_w=940, gap=1.3):
    f = sans(weight, size)
    for line in wrap(f, text, max_w):
        d.text((70 * S, y * S), line, font=f, fill=fill)
        y += size * gap
    return y


def fit_code_size(lines, max_w, start=32, floor=22):
    size = start
    while size > floor and max(mono(size).getlength(l) for l in lines) > max_w * S:
        size -= 1
    return size


def code_card(d, y, title, rows, lang, numbered=True):
    """rows: list of (sign, text). sign None = plain, '-'/'+'/' ' = diff."""
    x0, x1, pad = 50, 1030, 36
    gutter_w = 64 if numbered else 44
    size = fit_code_size([t for _, t in rows], x1 - x0 - 2 * pad - gutter_w)
    lh = round(size * 1.55)
    head = 76
    h = head + 24 + lh * len(rows) + 28
    d.rounded_rectangle((x0 * S, y * S, x1 * S, (y + h) * S), 26 * S, fill=CARD, outline=CARD_EDGE, width=2 * S)
    d.text(((x0 + pad) * S, (y + head / 2) * S), title, font=sans("regular", 28), fill=MUTED, anchor="lm")
    d.line(((x0 + 2) * S, (y + head) * S, (x1 - 2) * S, (y + head) * S), fill=CARD_EDGE, width=2 * S)

    f, fb = mono(size), mono(size, bold=True)
    ly = y + head + 24
    for i, (sign, text) in enumerate(rows, 1):
        if sign in ("-", "+"):
            bg = RED_BG if sign == "-" else GREEN_BG
            d.rectangle(((x0 + 2) * S, ly * S, (x1 - 2) * S, (ly + lh) * S), fill=bg)
        mid = ly + lh / 2
        gx = x0 + pad
        if numbered:
            d.text(((gx + gutter_w - 28) * S, mid * S), str(i), font=f, fill=GUTTER, anchor="rm")
        elif sign in ("-", "+"):
            d.text((gx * S, mid * S), sign, font=fb, fill=RED if sign == "-" else GREEN, anchor="lm")
        x = (gx + gutter_w) * S
        for val, col in tokens(text, lang):
            d.text((x, mid * S), val, font=f, fill=col, anchor="lm")
            x += f.getlength(val)
        ly += lh
    return y + h


def render_cover(n, post):
    img, d = canvas()
    glyph = mono(560)
    layer = Image.new("L", img.size, 0)
    ImageDraw.Draw(layer).text((W * S // 2, H * S // 2), "{ }", font=glyph, fill=255, anchor="mm")
    img.paste(Image.new("RGB", img.size, FG), mask=layer.point(lambda a: round(a * 0.045)))
    d = ImageDraw.Draw(img)
    d.text((W * S // 2, 300 * S), f"{SERIES} · {n:02d}", font=sans("regular", 30), fill=MUTED, anchor="mt")
    pitch = 69
    lines = post["cover"]
    height = sum(pitch if l else pitch / 2 for l in lines)
    y = H / 2 - height / 2
    for line in lines:
        if line is None:
            y += pitch / 2
            continue
        text, weight = line
        f = sans(weight, 60)
        if f.getlength(text) > 960 * S:
            raise ValueError(f"cover line too wide: {text}")
        d.text((W * S // 2, round(y * S)), text, font=f, fill=FG, anchor="mt")
        y += pitch
    return finish(img, post["slug"], "1-cover.png")


def render_question(n, post):
    img, d = canvas()
    tag(d, n)
    y = paragraph(d, post["question"], 270, size=56, weight="bold")
    if post.get("hint"):
        y = paragraph(d, post["hint"], y + 6, size=34, fill=MUTED)
    rows = [(None, l) for l in post["code"].split("\n")]
    y = code_card(d, y + 40, post["filename"], rows, post["lang"])
    d.text((70 * S, (y + 48) * S), "comment your answer, then swipe →", font=sans("regular", 32), fill=MUTED)
    return finish(centered(img, y + 90), post["slug"], "2-question.png")


def render_answer(n, post):
    img, d = canvas()
    tag(d, n, " · answer")
    y = paragraph(d, post["answer"], 270, size=56, weight="bold")
    y += 26
    for para in post["explain"]:
        if para.startswith("$ "):
            f = mono(36)
            d.text((70 * S, y * S), para[2:], font=f, fill=RED)
            y += 36 * 1.3 + 22
        else:
            y = paragraph(d, para, y, size=40) + 22
    y = paragraph(d, post["fix_note"], y + 20, size=34, fill=MUTED)
    y = code_card(d, y + 22, post["filename"], post["diff"], post["lang"], numbered=False)
    return finish(centered(img, y), post["slug"], "3-answer.png")


def main():
    wanted = set(sys.argv[1:])
    for n, post in enumerate(POSTS, 1):
        if wanted and post["slug"] not in wanted:
            continue
        for fn in (render_cover, render_question, render_answer):
            print(fn(n, post).relative_to(ROOT))


if __name__ == "__main__":
    main()
