# solve these (TikTok series, 1080x1920)

Per company, in `output/<company>/`:
- `1-cover-dark.png` / `1-cover-light.png`: minimal cover with the company mark at low opacity. Post one per video.
- `2-problems.png`: the problem list, styled like a dark-mode coding-practice app (no LeetCode branding).

Edit `problems.json` or the `COVERS` text in `make_solve.py`, then run `python3 make_solve.py [company ...]`.

## Data

Problems were picked from the community dataset
[liquidslr/interview-company-wise-problems](https://github.com/liquidslr/interview-company-wise-problems)
("Six Months" lists), favouring problems each company asks more often than the other two so the posts don't repeat.
The list shows no frequency numbers because they can't be verified. Each problem gets one topic tag
(BFS, DFS, Two Pointers, Dynamic Programming, ...), chosen from that problem's own LeetCode tags.
Problem numbers come from [krishnadey30/LeetCode-Questions-CompanyWise](https://github.com/krishnadey30/LeetCode-Questions-CompanyWise).

Logos: Font Awesome Free brand icons (`@iconify-json/fa6-brands`). Font: Nimbus Sans (Helvetica clone).
