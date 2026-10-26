"""Back-test "bet the favourite in every game, parlay the whole day" on NBA games.

Each day: pick the side with the higher pre-game price in every game, combine
them into one combo, and buy YES contracts on it with a fixed stake. A combo is
priced the way prediction markets quote them, as the product of the leg prices
(plus an optional maker markup), and Kalshi's taker fee is charged on entry:

    combo price P = min(0.99, prod(p_i) * (1 + markup))
    contracts C   = floor(stake / (P + fee_rate * P * (1 - P)))
    fee           = ceil_to_cent(fee_rate * C * P * (1 - P))
    payout        = C * $1 if every leg wins, else 0

The same favourites bet as straight singles (stake split evenly) are tracked
as a baseline so you can see what the parlay itself adds or costs.

Usage:
    python3 simulate.py games_kalshi.csv --stake 10 --bankroll 1000 --out report
"""

import argparse
import csv
import html
import math
import os
from collections import defaultdict
from math import prod

from common import read_games


def kalshi_fee(contracts, price, rate):
    return math.ceil(round(rate * contracts * price * (1 - price) * 100, 6)) / 100


def buy(stake, price, rate):
    """Spend up to `stake` on YES contracts at `price`. Returns (contracts, cost)."""
    contracts = math.floor(stake / (price + rate * price * (1 - price)))
    # The fee rounds up to the cent, which can tip the total just over the stake.
    while contracts > 0 and contracts * price + kalshi_fee(contracts, price, rate) > stake + 1e-9:
        contracts -= 1
    if contracts <= 0:
        return 0, 0.0
    return contracts, contracts * price + kalshi_fee(contracts, price, rate)


def favourite(g):
    """(team, price, won) for the side the market favours. Ties go to the home team."""
    if g["home_prob"] >= g["away_prob"]:
        return g["home"], g["home_prob"], g["winner"] == g["home"]
    return g["away"], g["away_prob"], g["winner"] == g["away"]


def by_day(games):
    days = defaultdict(list)
    for g in games:
        days[g["date"]].append(g)
    return dict(sorted(days.items()))


def simulate(games, stake=10.0, bankroll=1000.0, max_legs=None, min_prob=0.0,
             markup=0.0, fee_rate=0.07):
    """Run the strategy day by day. Returns a list of per-day records."""
    log = []
    bank = single_bank = bankroll
    for day, day_games in by_day(games).items():
        legs = sorted((favourite(g) + (g,) for g in day_games), key=lambda x: -x[1])
        legs = [l for l in legs if l[1] >= min_prob]
        if max_legs:
            legs = legs[:max_legs]
        if not legs:
            continue

        price = min(0.99, prod(l[1] for l in legs) * (1 + markup))
        hit = all(l[2] for l in legs)
        contracts, cost = buy(stake, price, fee_rate) if bank >= stake else (0, 0.0)
        payout = contracts * 1.0 if hit else 0.0
        bank += payout - cost

        s_cost = s_payout = 0.0
        if single_bank >= stake:
            for _, p, won, _ in legs:
                c, k = buy(stake / len(legs), p, fee_rate)
                s_cost += k
                s_payout += c if won else 0
        single_bank += s_payout - s_cost

        log.append({
            "date": day, "season": legs[0][3]["season"], "legs": len(legs),
            "picks": " ".join(f"{t}@{p:.2f}{'' if w else 'x'}" for t, p, w, _ in legs),
            "legs_won": sum(l[2] for l in legs), "combo_price": price, "hit": hit,
            "contracts": contracts, "cost": cost, "payout": payout,
            "pnl": payout - cost, "bankroll": bank,
            "singles_cost": s_cost, "singles_pnl": s_payout - s_cost,
            "singles_bankroll": single_bank, "leg_price_sum": sum(l[1] for l in legs),
        })
    return log


def summarise(log, singles=False, start=1000.0):
    """Totals for the combo, or (singles=True) for the same picks bet one by one.
    For singles, hits count winning legs and a losing day is one with negative P&L."""
    p = "singles_" if singles else ""
    bets = [r for r in log if r[p + "cost"] > 0]
    staked = sum(r[p + "cost"] for r in bets)
    pnl = sum(r[p + "pnl"] for r in bets)
    peak, dd = start, 0.0
    for r in log:
        peak = max(peak, r[p + "bankroll"])
        dd = max(dd, peak - r[p + "bankroll"])
    streak = longest = 0
    for r in bets:
        lost = r["pnl"] < 0 if not singles else r["singles_pnl"] < 0
        streak = streak + 1 if lost else 0
        longest = max(longest, streak)
    if singles:
        tries, hits = sum(r["legs"] for r in bets), sum(r["legs_won"] for r in bets)
        expected = sum(r["leg_price_sum"] for r in bets)
    else:
        tries, hits = len(bets), sum(r["hit"] for r in bets)
        expected = sum(r["combo_price"] for r in bets)
    return {
        "days": len(bets), "tries": tries, "hits": hits,
        "hit_rate": hits / tries if tries else 0, "expected_hits": expected,
        "avg_legs": sum(r["legs"] for r in bets) / len(bets) if bets else 0,
        "staked": staked, "pnl": pnl, "roi": pnl / staked if staked else 0,
        "max_drawdown": dd, "longest_losing": longest,
        "end_bankroll": log[-1][p + "bankroll"] if log else start,
    }


def calibration(games):
    buckets = defaultdict(lambda: [0, 0.0, 0])
    for g in games:
        _, p, won, = favourite(g)
        b = min(int(p * 10), 9)
        buckets[b][0] += 1
        buckets[b][1] += p
        buckets[b][2] += won
    return [(f"{b * 10}-{b * 10 + 10}%", n, s / n, w / n)
            for b, (n, s, w) in sorted(buckets.items())]


# ---------------------------------------------------------------- reporting

def money(x):
    return f"-${-x:,.2f}" if x < 0 else f"${x:,.2f}"


def svg_curve(log, start, width=760, height=240):
    if not log:
        return ""
    series = [("combo", [start] + [r["bankroll"] for r in log], "var(--c1)"),
              ("singles", [start] + [r["singles_bankroll"] for r in log], "var(--c2)")]
    lo = min(min(s) for _, s, _ in series)
    hi = max(max(s) for _, s, _ in series)
    lo, hi = min(lo, start), max(hi, start)
    pad = (hi - lo) * 0.05 or 1
    lo, hi = lo - pad, hi + pad
    n = len(log)
    x = lambda i: 48 + i * (width - 60) / max(n, 1)
    y = lambda v: 10 + (hi - v) * (height - 40) / (hi - lo)
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Bankroll over time">']
    for frac in (0, 0.5, 1):
        v = lo + (hi - lo) * frac
        parts.append(f'<line x1="48" x2="{width - 12}" y1="{y(v):.1f}" y2="{y(v):.1f}" class="grid"/>'
                     f'<text x="44" y="{y(v) + 4:.1f}" class="axis" text-anchor="end">${v:,.0f}</text>')
    parts.append(f'<line x1="48" x2="{width - 12}" y1="{y(start):.1f}" y2="{y(start):.1f}" class="base"/>')
    for name, s, color in series:
        pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(s))
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2"/>')
    parts.append(f'<text x="48" y="{height - 8}" class="axis">{html.escape(log[0]["date"])}</text>'
                 f'<text x="{width - 12}" y="{height - 8}" class="axis" text-anchor="end">'
                 f'{html.escape(log[-1]["date"])}</text></svg>')
    return "".join(parts)


def summary_row(label, s):
    cls = "neg" if s["pnl"] < 0 else "pos"
    return (f"<tr><td>{html.escape(str(label))}</td><td>{s['days']}</td>"
            f"<td>{s['hits']}/{s['tries']} ({s['hit_rate']:.1%})</td><td>{s['expected_hits']:.1f}</td>"
            f"<td>{s['avg_legs']:.1f}</td><td>{money(s['staked'])}</td>"
            f"<td class='{cls}'>{money(s['pnl'])}</td><td class='{cls}'>{s['roi']:+.1%}</td>"
            f"<td>{money(s['max_drawdown'])}</td><td>{s['longest_losing']}</td></tr>")


HEAD = ("<tr><th>Run</th><th>Days bet</th><th>Bets won</th><th>Fair-market expectation</th>"
        "<th>Avg legs</th><th>Staked</th><th>P&amp;L</th><th>ROI</th>"
        "<th>Max drawdown</th><th>Longest losing run</th></tr>")


def write_report(path, games, log, sweep, args):
    seasons = sorted({r["season"] for r in log})
    blocks = []
    for season in seasons + ["All"]:
        sl = log if season == "All" else [r for r in log if r["season"] == season]
        c = summarise(sl, start=args.bankroll)
        s = summarise(sl, singles=True, start=args.bankroll)
        blocks.append((season, sl, c, s))

    legs_table = defaultdict(lambda: [0, 0, 0.0])
    for r in log:
        legs_table[r["legs"]][0] += 1
        legs_table[r["legs"]][1] += r["hit"]
        legs_table[r["legs"]][2] += r["combo_price"]

    allc = blocks[-1][2]
    source = sorted({g["source"] for g in games})
    out = [f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NBA Combo Backtest</title>
<style>
:root{{--bg:#fbfaf7;--fg:#1d1d1b;--muted:#6b6a66;--line:#e3e1da;--card:#fff;--c1:#2f6fdb;--c2:#c2410c;--pos:#15803d;--neg:#b91c1c}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#161615;--fg:#ecebe6;--muted:#9b9a94;--line:#2e2d2a;--card:#1f1f1d;--c1:#7aa7ff;--c2:#fb923c;--pos:#4ade80;--neg:#f87171}}}}
:root[data-theme="dark"]{{--bg:#161615;--fg:#ecebe6;--muted:#9b9a94;--line:#2e2d2a;--card:#1f1f1d;--c1:#7aa7ff;--c2:#fb923c;--pos:#4ade80;--neg:#f87171}}
body{{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif;margin:0;padding:24px 16px}}
main{{max-width:980px;margin:0 auto}} h1{{font-size:26px;margin:0 0 4px}} h2{{font-size:18px;margin:32px 0 8px}}
.muted{{color:var(--muted)}} .cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:20px 0}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}}
.card b{{display:block;font-size:22px;font-variant-numeric:tabular-nums}} .card span{{color:var(--muted);font-size:13px}}
.wrap{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;font-size:14px}}
th,td{{text-align:right;padding:6px 8px;border-bottom:1px solid var(--line);white-space:nowrap}} th:first-child,td:first-child{{text-align:left}}
th{{color:var(--muted);font-weight:600}} .pos{{color:var(--pos)}} .neg{{color:var(--neg)}}
svg{{width:100%;height:auto;background:var(--card);border:1px solid var(--line);border-radius:10px}}
svg .grid{{stroke:var(--line)}} svg .base{{stroke:var(--muted);stroke-dasharray:4 4}} svg .axis{{fill:var(--muted);font-size:11px}}
.key{{display:flex;gap:16px;font-size:13px;color:var(--muted);margin:6px 0}} .key i{{display:inline-block;width:14px;height:3px;vertical-align:middle;margin-right:6px}}
td.picks{{text-align:left;font-family:ui-monospace,monospace;font-size:12px;white-space:normal}}
</style></head><body><main>
<h1>NBA daily combo backtest</h1>
<p class="muted">Bet the market favourite in every game and combine the day's picks into one combo.
Stake {money(args.stake)}/day, bankroll {money(args.bankroll)}, combo markup {args.markup:.0%},
fee rate {args.fee_rate}, max legs {args.max_legs or 'all'}, min leg price {args.min_prob:.2f}.
Prices: {html.escape(', '.join(source))}. {len(games)} games, {log[0]['date'] if log else '-'} to {log[-1]['date'] if log else '-'}.</p>
<div class="cards">
<div class="card"><span>Combo P&amp;L</span><b class="{'neg' if allc['pnl'] < 0 else 'pos'}">{money(allc['pnl'])}</b></div>
<div class="card"><span>ROI on stakes</span><b>{allc['roi']:+.1%}</b></div>
<div class="card"><span>Combos hit</span><b>{allc['hits']} / {allc['days']}</b></div>
<div class="card"><span>Hits a fair market expects</span><b>{allc['expected_hits']:.1f}</b></div>
<div class="card"><span>Avg legs per combo</span><b>{allc['avg_legs']:.1f}</b></div>
</div>"""]

    for season, sl, c, s in blocks:
        out.append(f"<h2>{html.escape(season)}</h2>")
        if season != "All":
            out.append('<div class="key"><span><i style="background:var(--c1)"></i>Daily combo</span>'
                       '<span><i style="background:var(--c2)"></i>Same picks as singles</span></div>')
            out.append(svg_curve(sl, args.bankroll))
        out.append(f'<div class="wrap"><table>{HEAD}{summary_row("Daily combo", c)}'
                   f'{summary_row("Same picks as singles", s)}</table></div>')

    out.append("<h2>What if the combo is capped at N legs?</h2>"
               "<p class='muted'>Each row keeps only the N most confident favourites each day.</p>"
               f'<div class="wrap"><table>{HEAD}')
    for label, s in sweep:
        out.append(summary_row(label, s))
    out.append("</table></div>")

    out.append("<h2>Hit rate by number of legs</h2><div class='wrap'><table>"
               "<tr><th>Legs</th><th>Days</th><th>Hit</th><th>Hit rate</th><th>Market-implied</th></tr>")
    for n, (d, h, p) in sorted(legs_table.items()):
        out.append(f"<tr><td>{n}</td><td>{d}</td><td>{h}</td><td>{h / d:.1%}</td><td>{p / d:.1%}</td></tr>")
    out.append("</table></div>")

    out.append("<h2>Are the favourites priced right?</h2><div class='wrap'><table>"
               "<tr><th>Favourite price</th><th>Games</th><th>Avg price</th><th>Actually won</th></tr>")
    for label, n, avg, won in calibration(games):
        out.append(f"<tr><td>{label}</td><td>{n}</td><td>{avg:.1%}</td><td>{won:.1%}</td></tr>")
    out.append("</table></div>")

    out.append("<h2>Every day</h2><p class='muted'>x marks a losing leg.</p><div class='wrap'><table>"
               "<tr><th>Date</th><th>Picks</th><th>Price</th><th>Cost</th><th>Payout</th><th>Bankroll</th></tr>")
    for r in reversed(log):
        out.append(f"<tr><td>{r['date']}</td><td class='picks'>{html.escape(r['picks'])}</td>"
                   f"<td>{r['combo_price']:.3f}</td><td>{money(r['cost'])}</td>"
                   f"<td class='{'pos' if r['hit'] else ''}'>{money(r['payout'])}</td><td>{money(r['bankroll'])}</td></tr>")
    out.append("</table></div></main></body></html>")
    with open(path, "w") as f:
        f.write("\n".join(out))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("games", help="CSV from fetch_kalshi.py or fetch_espn.py")
    ap.add_argument("--stake", type=float, default=10.0, help="dollars per daily combo")
    ap.add_argument("--bankroll", type=float, default=1000.0)
    ap.add_argument("--max-legs", type=int, default=None, help="cap legs per combo (most confident first)")
    ap.add_argument("--min-prob", type=float, default=0.0, help="skip favourites priced below this")
    ap.add_argument("--markup", type=float, default=0.0,
                    help="extra the combo maker charges over the product of leg prices, e.g. 0.05")
    ap.add_argument("--fee-rate", type=float, default=0.07, help="Kalshi taker fee coefficient; 0 for none")
    ap.add_argument("--out", default="report", help="output directory")
    args = ap.parse_args()

    games = read_games(args.games)
    if not games:
        raise SystemExit(f"no priced, finished games in {args.games}")
    kw = dict(stake=args.stake, bankroll=args.bankroll, min_prob=args.min_prob,
              markup=args.markup, fee_rate=args.fee_rate)
    log = simulate(games, max_legs=args.max_legs, **kw)
    sweep = [(f"Top {n}" if n else "All games", summarise(simulate(games, max_legs=n, **kw), start=args.bankroll))
             for n in (1, 2, 3, 4, 5, 6, None)]

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "daily_log.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(log[0]))
        w.writeheader()
        w.writerows(log)
    write_report(os.path.join(args.out, "report.html"), games, log, sweep, args)

    for season in sorted({r["season"] for r in log}) + ["All"]:
        sl = log if season == "All" else [r for r in log if r["season"] == season]
        c = summarise(sl, start=args.bankroll)
        s = summarise(sl, singles=True, start=args.bankroll)
        print(f"{season:8} combo: {c['hits']}/{c['days']} hit (fair market expects {c['expected_hits']:.1f}), "
              f"P&L {money(c['pnl'])}, ROI {c['roi']:+.1%} | singles P&L {money(s['pnl'])}, ROI {s['roi']:+.1%}")
    print("legs cap sweep:")
    for label, s in sweep:
        print(f"  {label:10} {s['hits']:3}/{s['days']:3} hit, P&L {money(s['pnl']):>12}, ROI {s['roi']:+.1%}")
    print(f"report: {os.path.join(args.out, 'report.html')}")


if __name__ == "__main__":
    main()
