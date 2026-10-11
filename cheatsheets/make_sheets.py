"""Render the cheat sheet series (1080x1920): 1-cover.png, 2-sheet.png, 3-sheet.png per topic.

Usage: python3 make_sheets.py [slug ...]
"""
import io
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont

from sheets import SHEETS

ROOT = Path(__file__).resolve().parent
A = ROOT / "assets"
W, H, S = 1080, 1920, 2
BG = (11, 11, 11)
FG = (240, 240, 240)
MUTED = (135, 135, 138)
EDGE = (44, 44, 46)
X0, TW = 70, 940

plt.rcParams["mathtext.fontset"] = "dejavusans"


def sans(weight, size):
    return ImageFont.truetype(str(A / f"NimbusSans-{weight.capitalize()}.otf"), round(size * S))


def mono(size):
    return ImageFont.truetype(str(A / "JetBrainsMono-Regular.ttf"), round(size * S),
                              layout_engine=ImageFont.Layout.BASIC)  # no ligatures


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


def para(d, x, y, text, f, fill, max_w, lh):
    for line in wrap(f, text, max_w):
        d.text((x * S, y * S), line, font=f, fill=fill)
        y += lh
    return y


def math_img(tex, px, color):
    """Render mathtext so that its font size is `px` (1x pixels)."""
    dpi = 200
    fig = plt.figure(figsize=(0.01, 0.01), dpi=dpi)
    fig.text(0, 0, tex, fontsize=px * S * 72 / dpi, color=[c / 255 for c in color])
    buf = io.BytesIO()
    fig.savefig(buf, dpi=dpi, transparent=True, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    buf.seek(0)
    im = Image.open(buf).convert("RGBA")
    return im.crop(im.getchannel("A").getbbox())


def draw_block(img, d, block, y, accent):
    kind = block[0]
    if kind == "h":
        y += 18
        d.text((X0 * S, y * S), block[1].upper(), font=sans("bold", 26), fill=accent)
        return y + 48
    if kind == "row":
        _, code, note = block
        f = mono(31)
        for line in code.split("\n"):
            if f.getlength(line) > TW * S:
                raise ValueError(f"code too wide: {line}")
            d.text((X0 * S, y * S), line, font=f, fill=FG)
            y += 42
        y = para(d, X0, y + 2, note, sans("regular", 28), MUTED, TW, 34)
        return y + 20
    if kind == "item":
        _, name, note = block
        d.text((X0 * S, y * S), name, font=sans("bold", 36), fill=FG)
        y = para(d, X0, y + 46, note, sans("regular", 29), MUTED, TW, 35)
        return y + 18
    if kind == "math":
        _, tex, note = block
        im = math_img(tex, 46, FG)
        img.alpha_composite(im, (X0 * S, round(y * S)))
        y += im.height / S + 10
        if note:
            y = para(d, X0, y, note, sans("regular", 28), MUTED, TW, 34)
        return y + 24
    if kind == "mathgrid":
        ims = [math_img(t, 40, FG) for t in block[1]]
        col_w = TW / 2
        for i in range(0, len(ims), 2):
            pair = ims[i:i + 2]
            row_h = max(im.height for im in pair) / S
            for j, im in enumerate(pair):
                if im.width / S > col_w - 20:
                    raise ValueError("math cell too wide")
                img.alpha_composite(im, (round((X0 + j * col_w) * S), round((y + (row_h - im.height / S) / 2) * S)))
            y += row_h + 30
        return y + 6
    if kind == "table":
        _, headers, rows, notes = block
        first_w = 300
        cw = (TW - first_w) / (len(headers) - 1)
        hf, nf, vf = sans("regular", 26), sans("regular", 31), mono(29)
        for j, h in enumerate(headers):
            x = X0 if j == 0 else X0 + first_w + (j - 1) * cw
            d.text((x * S, y * S), h, font=hf, fill=accent if j == 0 else MUTED)
        y += 46
        for r in rows:
            d.line((X0 * S, y * S, (X0 + TW) * S, y * S), fill=EDGE, width=2 * S)
            y += 18
            for j, v in enumerate(r):
                if j == 0:
                    d.text((X0 * S, y * S), v, font=nf, fill=FG)
                else:
                    if vf.getlength(v) > (cw - 8) * S:
                        raise ValueError(f"table cell too wide: {v}")
                    d.text(((X0 + first_w + (j - 1) * cw) * S, y * S), v, font=vf, fill=FG)
            y += 48
        d.line((X0 * S, y * S, (X0 + TW) * S, y * S), fill=EDGE, width=2 * S)
        y += 18
        for n in notes:
            y = para(d, X0, y, n, sans("regular", 25), MUTED, TW, 32)
        return y + 18
    if kind == "flow":
        f = mono(29)
        x, gap = X0, 14
        arrow = " → "
        for i, step in enumerate(block[1]):
            label = step + (arrow if i < len(block[1]) - 1 else "")
            w = f.getlength(label) / S
            if x + w > X0 + TW:
                x, y = X0, y + 46
            d.text((x * S, y * S), step, font=f, fill=FG)
            if i < len(block[1]) - 1:
                d.text(((x + f.getlength(step) / S) * S, y * S), arrow, font=f, fill=accent)
            x += w
        return y + 64
    raise ValueError(kind)


def render_sheet(n, sheet, idx, title, blocks):
    layer = Image.new("RGBA", (W * S, H * S * 2), BG + (255,))
    d = ImageDraw.Draw(layer)
    d.text((X0 * S, 0), f"cheat sheet · {n:02d} · {idx}/2", font=sans("regular", 28), fill=MUTED)
    y = 50
    d.text((X0 * S, y * S), title, font=sans("bold", 52), fill=FG)
    y += 90
    for b in blocks:
        y = draw_block(layer, d, b, y, sheet["accent"])
    d.text((X0 * S, (y + 10) * S), "save this for later.", font=sans("regular", 26), fill=MUTED)
    h = y + 50
    if h > 1640:
        raise ValueError(f"{sheet['slug']} slide {idx} too tall: {h}")
    top = max(130, round(880 - h / 2))
    img = Image.new("RGBA", (W * S, H * S), BG + (255,))
    img.alpha_composite(layer.crop((0, 0, W * S, round(h * S))), (0, top * S))
    return img


def render_cover(n, sheet):
    img = Image.new("RGBA", (W * S, H * S), BG + (255,))
    ImageDraw.Draw(img).text((W * S // 2, H * S // 2), sheet["mark"], font=mono(380),
                             fill=sheet["accent"] + (22,), anchor="mm")
    img = Image.alpha_composite(Image.new("RGBA", img.size, BG + (255,)), img)
    d = ImageDraw.Draw(img)
    d.text((W * S // 2, 300 * S), f"cheat sheet · {n:02d}", font=sans("regular", 30), fill=MUTED, anchor="mt")
    pitch = 69
    lines = sheet["cover"]
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


def save(img, n, slug, name):
    out = ROOT / "output" / f"{n:02d}-{slug}" / name
    out.parent.mkdir(parents=True, exist_ok=True)
    img.resize((W, H), Image.LANCZOS).convert("RGB").save(out, optimize=True)
    return out


def main():
    wanted = set(sys.argv[1:])
    for n, sheet in enumerate(SHEETS, 1):
        if wanted and sheet["slug"] not in wanted:
            continue
        print(save(render_cover(n, sheet), n, sheet["slug"], "1-cover.png").relative_to(ROOT))
        for i, (title, blocks) in enumerate(sheet["slides"], 1):
            print(save(render_sheet(n, sheet, i, title, blocks), n, sheet["slug"], f"{i + 1}-sheet.png").relative_to(ROOT))


if __name__ == "__main__":
    main()
