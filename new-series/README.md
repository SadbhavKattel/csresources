# New series (TikTok, 1080x1920)

Three series, five posts each. Every post is `1-cover.png` + `2-details.png` in
`output/<series>/<NN-slug>/`.

| series | folder | what it is |
|---|---|---|
| closing soon | `closing-soon/` | one opportunity per post: deadline, pay, location, eligibility, link |
| they'll pay you to show up | `paid-to-attend/` | conferences that fund students: city, dates, what's covered, how to apply |
| your .edu unlocks | `edu-perks/` | three verified student perks per post |

Content and sources live in `data.py`. Run `python3 make.py [closing-soon|paid-to-attend|edu-perks]`.

## Logos
Brand logos come from simple-icons and Iconify's `logos` set (npm). DAAD RISE is the file supplied earlier.
These are still name tiles because no logo was reachable: **nsf, hertz, soros, doe, tapia, frontendmasters**.
Save the real logo as `logos/<key>.png` (transparent PNG is best) and re-run; it's picked up automatically.

## Accuracy
Facts were checked on 2026-10-10. Deadlines, amounts and offers change, so re-check the official link
on each slide before posting. Left out on purpose because current terms couldn't be confirmed:
GitHub Copilot for students (plan changed March 2026), Cursor's student year (ended June 2026),
AWS Educate credits.
