# Fellowship slides (TikTok, 1080x1920)

New slides with an "APPLY IF YOU'RE A CS STUDENT" header, in the same template as the original AI4ALL / Outreachy / LFX / GSoC / MLH slides.

- `output/` holds the finished slides.
- `programs.json` holds each slide's title, description, logo, and source link.
- `assets/background.png` is the original background with the logo and text removed;
  `assets/background-dark.png` is the dark version the slides now use (rebuild it with `python3 make_dark_background.py`).
- `output/00-cover.png` is a text-only cover ("still no internship? apply to these.") set in Nimbus Sans, a free Helvetica clone.
- Font: League Spartan Bold (the Canva default). Size and letter spacing were measured to match the originals.

## Swapping in a real logo

Save the logo as `logos/<slug>.png` (for example `logos/code2040-fellows.png`), then run:

    pip install pillow
    python3 make_slides.py code2040-fellows   # or no arguments to rebuild every slide

A file in `logos/` always replaces the white placeholder card.

## Logo status

Real logos: Explore Microsoft, Uber Career Prep, SEO Tech Developer, Code2040, KP Fellows, Neo Scholars,
Summer of Bitcoin, DAAD RISE, Jane Street INSIGHT, CodePath, ColorStack, Rewriting the Code.
Placeholder name cards that still need the official logo: Mitacs Globalink, CERN openlab, NSF REU.
