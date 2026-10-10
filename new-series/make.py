"""Render the three series (1080x1920): each post = 1-cover.png + 2-details.png.

Usage: python3 make.py [series-key ...]   (closing-soon, paid-to-attend, edu-perks)
A real logo saved as logos/<key>.png overrides assets/logos/<key>.png and the name-tile fallback.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from data import SERIES

ROOT = Path(__file__).resolve().parent
W, H, S = 1080, 1920, 2
BG = (11, 11, 11)
FG = (245, 245, 245)
MUTED = (128, 128, 128)
CARD = (22, 22, 23)
EDGE = (42, 42, 44)
X0 = 70
TEXT_W = 940


def sans(weight, size):
    return ImageFont.truetype(str(ROOT / "assets" / f"NimbusSans-{weight.capitalize()}.otf"), round(size * S))


def wrap(f, text, max_w):
    lines, cur = [], ""
    for word in text.split(" "):
        trial = f"{cur} {word}".strip()
        if f.getlength(trial) <= max_w * S or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    lines.append(cur)
    return lines


def text_block(d, x, y, text, size, weight="regular", fill=FG, max_w=TEXT_W, gap=1.28):
    f = sans(weight, size)
    for line in wrap(f, text, max_w):
        d.text((x * S, y * S), line, font=f, fill=fill)
        y += size * gap
    return y


def logo_image(key):
    for p in (ROOT / "logos" / f"{key}.png", ROOT / "assets" / "logos" / f"{key}.png"):
        if p.exists():
            im = Image.open(p).convert("RGBA")
            bbox = im.getchannel("A").getbbox()
            return im.crop(bbox) if bbox else im
    return None


def tile(key, fallback, height):
    """White rounded tile with the logo; wide logos get a wide tile; missing logos get a name tile."""
    h = round(height * S)
    pad = round(h * 0.18)
    im = logo_image(key)
    if im is None:
        f = sans("bold", height * 0.30)
        tw = f.getlength(fallback)
        w = max(h, round(tw + 2 * pad))
        t = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        dd = ImageDraw.Draw(t)
        dd.rounded_rectangle((0, 0, w - 1, h - 1), round(h * 0.22), fill=(255, 255, 255))
        dd.text((w / 2, h / 2), fallback, font=f, fill=(20, 20, 20), anchor="mm")
        return t
    inner_h = h - 2 * pad
    scale = inner_h / im.height
    lw = round(im.width * scale)
    if lw > inner_h * 1.25:  # wide logo: cap width, widen tile
        lw = min(lw, round(h * 3.2))
        scale = lw / im.width
    im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS)
    w = max(h, im.width + 2 * pad)
    t = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(t).rounded_rectangle((0, 0, w - 1, h - 1), round(h * 0.22), fill=(255, 255, 255))
    t.alpha_composite(im, ((w - im.width) // 2, (h - im.height) // 2))
    return t


def canvas():
    img = Image.new("RGBA", (W * S, H * S), BG + (255,))
    return img, ImageDraw.Draw(img)


def save(img, series_key, n, slug, name):
    out = ROOT / "output" / series_key / f"{n:02d}-{slug}" / name
    out.parent.mkdir(parents=True, exist_ok=True)
    img.resize((W, H), Image.LANCZOS).convert("RGB").save(out, optimize=True)
    return out


def centered(layer, bottom):
    """Shift content drawn from y=170 so the block is centred above TikTok's caption area."""
    img = Image.new("RGBA", (W * S, H * S), BG + (255,))
    h = bottom - 170
    top = max(150, round(870 - h / 2))
    img.alpha_composite(layer, (0, (top - 170) * S))
    return img


def tag(d, series, n, y=170):
    d.text((X0 * S, y * S), f"{series} · {n:02d}", font=sans("regular", 30), fill=MUTED)


# ---------- covers ----------

def watermark(img, key, text):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    im = logo_image(key) if key else None
    if im is not None and im.getchannel("A").getextrema()[0] == 255:
        im = None  # opaque logo (e.g. on a white box) would show as a grey rectangle
        text = None
    if im is not None:
        im = im.convert("L").point(lambda v: 255)  # flat silhouette from alpha
        alpha = Image.open(next(p for p in (ROOT / "logos" / f"{key}.png", ROOT / "assets" / "logos" / f"{key}.png")
                                if p.exists())).convert("RGBA").getchannel("A")
        alpha = alpha.crop(alpha.getbbox())
        size = 720 * S
        scale = min(size / alpha.width, size / alpha.height)
        alpha = alpha.resize((round(alpha.width * scale), round(alpha.height * scale)), Image.LANCZOS)
        mark = Image.new("RGBA", alpha.size, FG + (0,))
        mark.putalpha(alpha.point(lambda a: round(a * 0.06)))
        layer.alpha_composite(mark, ((W * S - mark.width) // 2, (H * S - mark.height) // 2))
    elif text:
        ImageDraw.Draw(layer).text((W * S // 2, H * S // 2), text, font=sans("bold", 330),
                                   fill=FG + (16,), anchor="mm")
    img.alpha_composite(layer)


def render_cover(series, n, post, key, text_mark=None):
    img, _ = canvas()
    watermark(img, key, text_mark)
    d = ImageDraw.Draw(img)
    d.text((W * S // 2, 300 * S), f"{series['series']} · {n:02d}", font=sans("regular", 30), fill=MUTED, anchor="mt")
    pitch = 69
    lines = post["cover"]
    y = H / 2 - sum(pitch if l else pitch / 2 for l in lines) / 2
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
    return img


# ---------- detail slides ----------

def header(img, d, post, y, name, sub):
    t = tile(post["logo"], post["logo_text"], 120)
    img.alpha_composite(t, (X0 * S, round(y * S)))
    tw = t.width / S
    if tw <= 160:
        x = X0 + tw + 30
        yy = text_block(d, x, y + 8, name, 40, "bold", max_w=TEXT_W - tw - 30, gap=1.18)
        yy = text_block(d, x, yy + 2, sub, 32, fill=MUTED, max_w=TEXT_W - tw - 30, gap=1.2)
        return max(y + 120, yy)
    yy = text_block(d, X0, y + 150, name, 40, "bold", gap=1.18)
    return text_block(d, X0, yy + 2, sub, 32, fill=MUTED, gap=1.2)


def rows_block(d, rows, y, accent_label=None):
    for label, value in rows:
        d.text((X0 * S, y * S), label, font=sans("regular", 28), fill=accent_label or MUTED)
        y = text_block(d, X0, y + 40, value, 38, gap=1.25) + 30
    return y


def footer(d, link, y):
    d.text((X0 * S, y * S), f"apply → {link}", font=sans("bold", 32), fill=FG)
    d.text((X0 * S, (y + 48) * S), "double-check the details on the official site.", font=sans("regular", 26), fill=MUTED)
    return y + 90


def render_closing(series, n, post):
    img, d = canvas()
    tag(d, series["series"], n)
    y = header(img, d, post, 240, post["org"], post["program"]) + 50
    d.text((X0 * S, y * S), "deadline", font=sans("regular", 30), fill=MUTED)
    big = sans("bold", 150)
    d.text((X0 * S - 6 * S, (y + 46) * S), post["deadline"], font=big, fill=series["accent"])
    yr_x = X0 + big.getlength(post["deadline"]) / S + 18
    d.text((yr_x * S, (y + 128) * S), post["year"], font=sans("regular", 44), fill=series["accent"])
    y = text_block(d, X0, y + 216, post["deadline_note"], 30, fill=MUTED) + 44
    y = rows_block(d, post["rows"], y)
    y = footer(d, post["link"], y + 10)
    return centered(img, y)


def chip(d, x, y, label, accent):
    f = sans("regular", 32)
    w = f.getlength(label) / S + 44
    if x + w > X0 + TEXT_W:
        return None
    d.rounded_rectangle((x * S, y * S, (x + w) * S, (y + 66) * S), 33 * S,
                        fill=tuple(round(c * 0.18) for c in accent), outline=accent, width=2 * S)
    d.text(((x + w / 2) * S, (y + 33) * S), label, font=f, fill=accent, anchor="mm")
    return x + w + 14


def render_paid(series, n, post):
    img, d = canvas()
    tag(d, series["series"], n)
    y = header(img, d, post, 240, post["event"], post.get("sub", "student scholarships & travel funding")) + 54
    y = text_block(d, X0, y, post["where"], 76, "bold", gap=1.12)
    y = text_block(d, X0, y + 4, post["when"], 40, fill=MUTED) + 40
    d.text((X0 * S, y * S), "what they cover", font=sans("regular", 28), fill=MUTED)
    x, cy = X0, y + 44
    for c in post["covers"]:
        nx = chip(d, x, cy, c, series["accent"])
        if nx is None:
            x, cy = X0, cy + 80
            nx = chip(d, x, cy, c, series["accent"])
        x = nx
    y = cy + 66 + 50
    y = rows_block(d, post["rows"], y)
    y = footer(d, post["link"], y + 10)
    return centered(img, y)


def render_perks(series, n, post):
    img, d = canvas()
    tag(d, series["series"], n)
    y = text_block(d, X0, 225, post["title"], 56, "bold") + 30
    for key, name, headline, detail, link in post["perks"]:
        top = y
        t = tile(key, name, 104)
        inner_x = X0 + 30
        text_x = inner_x + t.width / S + 28
        tw = X0 + TEXT_W - 30 - text_x
        yy = text_block(d, text_x, top + 34, name, 32, fill=MUTED, max_w=tw, gap=1.2)
        yy = text_block(d, text_x, yy + 2, headline, 46, "bold", fill=series["accent"], max_w=tw, gap=1.15)
        yy = text_block(d, text_x, yy + 6, detail, 30, max_w=tw, gap=1.3)
        yy = text_block(d, text_x, yy + 8, link, 26, fill=MUTED, max_w=tw)
        bottom = max(yy + 20, top + 34 + 104 + 34)
        d.rounded_rectangle((X0 * S, top * S, (X0 + TEXT_W) * S, bottom * S), 26 * S, fill=CARD, outline=EDGE, width=2 * S)
        # redraw contents above the card fill
        img.alpha_composite(t, (round(inner_x * S), round((top + 34) * S)))
        yy = text_block(d, text_x, top + 34, name, 32, fill=MUTED, max_w=tw, gap=1.2)
        yy = text_block(d, text_x, yy + 2, headline, 46, "bold", fill=series["accent"], max_w=tw, gap=1.15)
        yy = text_block(d, text_x, yy + 6, detail, 30, max_w=tw, gap=1.3)
        text_block(d, text_x, yy + 8, link, 26, fill=MUTED, max_w=tw)
        y = bottom + 24
    d.text((X0 * S, (y + 16) * S), "offers change. double-check before you sign up.", font=sans("regular", 26), fill=MUTED)
    return centered(img, y + 60)


def main():
    wanted = sys.argv[1:] or list(SERIES)
    for key in wanted:
        series = SERIES[key]
        for n, post in enumerate(series["posts"], 1):
            if key == "edu-perks":
                cover = render_cover(series, n, post, None, ".edu")
                detail = render_perks(series, n, post)
            else:
                cover = render_cover(series, n, post, post["logo"])
                detail = render_closing(series, n, post) if key == "closing-soon" else render_paid(series, n, post)
            print(save(cover, key, n, post["slug"], "1-cover.png").relative_to(ROOT))
            print(save(detail, key, n, post["slug"], "2-details.png").relative_to(ROOT))


if __name__ == "__main__":
    main()
