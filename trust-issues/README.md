# trust issues (TikTok series, 1080x1920)

"don't blindly trust AI code." Each post is 3 slides in `output/<slug>/`:
1. `1-cover.png`: the hook
2. `2-question.png`: the AI-written code plus a question ("what does this print?")
3. `3-answer.png`: what's wrong, why, and the fix as a red/green diff

Posts live in `posts.py`. Add one there and run `python3 make_trust.py [slug ...]`.
Every bug and fix in `posts.py` was executed to confirm it (Python 3, Node 22), except the
API-key post, which is an architecture issue.

Fonts: Nimbus Sans (Helvetica clone) and JetBrains Mono (ligatures off). Syntax colours: GitHub-dark-like.
