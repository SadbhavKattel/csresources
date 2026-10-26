"""Scan open Polymarket events for arbitrage against live order books.

Reads use Polymarket's public, unauthenticated endpoints (Gamma for events,
CLOB for order books). Nothing is traded.

Usage:
    python3 scan.py                         # one pass over every open event
    python3 scan.py --watch 15 --minutes 60 # rescan every 15 s, log how long each lasts
    python3 scan.py --fee-rate 0.04 --min-profit 1
"""

import argparse
import csv
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

from arb import Event, Market, scan_event

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"


def http(url, body=None, retries=4):
    data = json.dumps(body).encode() if body is not None else None
    delay = 1.0
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, headers={
            "User-Agent": "polymarket-arb-scanner/1.0", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == retries - 1:
                raise
        except urllib.error.URLError:
            if attempt == retries - 1:
                raise
        time.sleep(delay)
        delay *= 2


def _list(v):
    return json.loads(v) if isinstance(v, str) else (v or [])


def parse_event(e):
    markets = []
    for m in e.get("markets", []):
        tokens, outcomes = _list(m.get("clobTokenIds")), _list(m.get("outcomes"))
        if len(tokens) != 2:
            continue
        # Any two-outcome market can be split and merged; the first token plays "YES".
        label = m.get("groupItemTitle") or ""
        if outcomes and [o.lower() for o in outcomes] != ["yes", "no"]:
            label = label or f"{m.get('question', '')} [{outcomes[0]}]"
        markets.append(Market(
            question=m.get("question", ""), yes=tokens[0], no=tokens[1],
            end_date=(m.get("endDate") or e.get("endDate") or "")[:10],
            label=label,
            active=bool(m.get("active")) and not m.get("closed") and m.get("enableOrderBook", True)
                   and m.get("acceptingOrders", True)))
    return Event(title=e.get("title", ""), slug=e.get("slug", ""), markets=markets,
                 neg_risk=bool(e.get("negRisk") or e.get("enableNegRisk")),
                 augmented=bool(e.get("negRiskAugmented")))


def fetch_events(limit=None, min_liquidity=0.0):
    events, offset = [], 0
    while True:
        page = http(f"{GAMMA}/events?closed=false&active=true&limit=500&offset={offset}")
        if not page:
            break
        for e in page:
            if float(e.get("liquidity") or 0) >= min_liquidity:
                events.append(parse_event(e))
        offset += len(page)
        if len(page) < 500 or (limit and len(events) >= limit):
            break
    return events[:limit] if limit else events


def fetch_books(token_ids):
    books = {}
    ids = list(dict.fromkeys(token_ids))
    for i in range(0, len(ids), 100):
        for b in http(f"{CLOB}/books", [{"token_id": t} for t in ids[i:i + 100]]) or []:
            books[b["asset_id"]] = b
    return books


def describe(o):
    legs = ", ".join(f"{l.side} {l.label} @ {l.levels[0][0]:.3f}" for l in o.legs)
    when = "instant" if o.instant else f"hold to {o.end_date or '?'}"
    return (f"${o.profit:8.2f}  size {o.size:9.1f}  edge {o.edge * 100:5.2f}c/unit  {when:18} "
            f"{o.kind:31} | {o.event[:60]} | {legs[:200]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fee-rate", type=float, default=0.05,
                    help="taker fee coefficient (fee = shares x rate x p x (1-p)); check the market's rate")
    ap.add_argument("--min-edge", type=float, default=0.0, help="minimum profit per unit, dollars")
    ap.add_argument("--min-profit", type=float, default=0.50, help="minimum total profit, dollars")
    ap.add_argument("--fixed-cost", type=float, default=0.02, help="gas/relayer cost per opportunity")
    ap.add_argument("--min-liquidity", type=float, default=0.0, help="skip events below this Gamma liquidity")
    ap.add_argument("--limit", type=int, default=None, help="scan at most this many events")
    ap.add_argument("--watch", type=float, default=0, help="rescan every N seconds")
    ap.add_argument("--minutes", type=float, default=30, help="how long --watch runs")
    ap.add_argument("--log", default="opportunities.csv")
    args = ap.parse_args()

    events = fetch_events(args.limit, args.min_liquidity)
    print(f"{len(events)} open events, {sum(len(e.markets) for e in events)} binary markets")
    seen = {}  # key -> first/last seen, best profit
    stop = time.time() + args.minutes * 60
    new_log = not os.path.exists(args.log)
    with open(args.log, "a", newline="") as f:
        w = csv.writer(f)
        if new_log:
            w.writerow(["seen_at", "kind", "event", "profit", "size", "edge", "instant", "end_date", "legs"])
        while True:
            t0 = time.time()
            books = fetch_books([t for e in events for m in e.markets if m.active for t in (m.yes, m.no)])
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            opps = []
            for e in events:
                opps += scan_event(e, books, args.fee_rate, args.min_edge, args.min_profit, args.fixed_cost)
            opps.sort(key=lambda o: -o.profit)
            for o in opps:
                rec = seen.setdefault(o.key, {"first": t0, "best": 0.0, "o": o})
                rec["last"], rec["best"] = t0, max(rec["best"], o.profit)
                w.writerow([now, o.kind, o.event, f"{o.profit:.2f}", f"{o.size:.1f}", f"{o.edge:.4f}",
                            o.instant, o.end_date, " ; ".join(f"{l.side} {l.label} @ {l.levels[0][0]}"
                                                               for l in o.legs)])
            f.flush()
            print(f"\n[{now}] {len(books)} books in {time.time() - t0:.1f}s, {len(opps)} opportunities")
            for o in opps[:25]:
                print("  " + describe(o))
            if not args.watch or time.time() >= stop:
                break
            time.sleep(max(0, args.watch - (time.time() - t0)))

    if args.watch and seen:
        print("\nPersistence (an opportunity counts as alive between first and last scan it appeared in):")
        for rec in sorted(seen.values(), key=lambda r: -r["best"])[:25]:
            print(f"  alive ~{rec['last'] - rec['first']:6.0f}s  best ${rec['best']:8.2f}  "
                  f"{rec['o'].kind} | {rec['o'].event[:60]}")
    print(f"\nlogged to {args.log}")


if __name__ == "__main__":
    main()
