"""Pull settled Kalshi NBA game-winner markets and their pre-game prices.

Kalshi lists each game as an event (e.g. KXNBAGAME-25OCT21HOUOKC) with one
market per team (...-HOU, ...-OKC). A market settles "yes" if that team won.
The pre-game price is the last hourly candle at or before a cutoff on game day
(default 12:00 ET, before any NBA tip-off), using the YES ask (what a buyer
pays) when available and the last trade price otherwise.

Usage:
    python3 fetch_kalshi.py --start 2025-10-01 --end 2026-10-26 --out games_kalshi.csv
"""

import argparse
import re
from datetime import date, datetime, time as dtime, timezone

from common import ET, get_json, parse_date, season_of, write_games

BASE = "https://api.elections.kalshi.com/trade-api/v2"
SERIES = "KXNBAGAME"
MONTHS = {m: i for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], 1)}


def list_markets(cache):
    """All settled markets in the series. Kalshi moves old markets behind a
    /historical prefix, so query both and de-duplicate by ticker."""
    seen = {}
    for prefix in ("", "/historical"):
        cursor = None
        while True:
            params = {"series_ticker": SERIES, "status": "settled", "limit": 1000}
            if prefix:
                params.pop("status")
            if cursor:
                params["cursor"] = cursor
            data = get_json(f"{BASE}{prefix}/markets", params, cache)
            if not data:
                break
            for m in data.get("markets", []):
                seen.setdefault(m["ticker"], m)
            cursor = data.get("cursor")
            if not cursor:
                break
    return list(seen.values())


def event_date(event_ticker):
    """KXNBAGAME-25OCT21HOUOKC -> (date(2025, 10, 21), 'HOUOKC')."""
    m = re.match(rf"{SERIES}-(\d\d)([A-Z]{{3}})(\d\d)([A-Z]+)$", event_ticker)
    if not m:
        return None, None
    yy, mon, dd, teams = m.groups()
    return date(2000 + int(yy), MONTHS[mon], int(dd)), teams


def cents(obj, key="close"):
    """Read a candle price field in either the integer-cents or *_dollars form."""
    if not obj:
        return None
    if obj.get(key) is not None:
        return obj[key] / 100
    if obj.get(f"{key}_dollars") is not None:
        return float(obj[f"{key}_dollars"])
    return None


def pregame_price(market, cutoff_ts, cache):
    params = {"start_ts": cutoff_ts - 3 * 86400, "end_ts": cutoff_ts, "period_interval": 60}
    data = None
    for path in (f"/series/{SERIES}/markets/{market['ticker']}/candlesticks",
                 f"/historical/markets/{market['ticker']}/candlesticks"):
        data = get_json(f"{BASE}{path}", params, cache)
        if data and data.get("candlesticks"):
            break
    candles = [c for c in (data or {}).get("candlesticks", []) if c["end_period_ts"] <= cutoff_ts]
    for c in reversed(candles):
        price = cents(c.get("yes_ask")) or cents(c.get("price")) or cents(c.get("price"), "previous")
        if price and 0 < price < 1:
            return price
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", default="2025-10-01")
    ap.add_argument("--end", default=date.today().isoformat())
    ap.add_argument("--cutoff-et", default="12:00", help="pre-game snapshot time, ET (HH:MM)")
    ap.add_argument("--out", default="games_kalshi.csv")
    ap.add_argument("--cache", default=".cache/kalshi")
    args = ap.parse_args()

    start, end = parse_date(args.start), parse_date(args.end)
    hh, mm = map(int, args.cutoff_et.split(":"))

    events = {}
    for m in list_markets(args.cache):
        d, teams = event_date(m["event_ticker"])
        if d and start <= d <= end:
            events.setdefault(m["event_ticker"], (d, teams, []))[2].append(m)

    rows = []
    for i, (ev, (d, teams, markets)) in enumerate(sorted(events.items()), 1):
        if len(markets) != 2:
            continue
        # Tickers list the away team first: HOUOKC = Houston at Oklahoma City.
        codes = {m["ticker"].rsplit("-", 1)[1]: m for m in markets}
        away = next((c for c in codes if teams.startswith(c)), None)
        home = next((c for c in codes if c != away), None)
        if not away or not home:
            continue
        cutoff = datetime.combine(d, dtime(hh, mm), ET).astimezone(timezone.utc)
        ts = int(cutoff.timestamp())
        hp = pregame_price(codes[home], ts, args.cache)
        apr = pregame_price(codes[away], ts, args.cache)
        result = {c: m.get("result") for c, m in codes.items()}
        winner = home if result[home] == "yes" else away if result[away] == "yes" else ""
        rows.append({"date": d.isoformat(), "season": season_of(d), "game_id": ev,
                     "home": home, "away": away,
                     "home_prob": f"{hp:.4f}" if hp else "", "away_prob": f"{apr:.4f}" if apr else "",
                     "winner": winner, "source": "kalshi"})
        if i % 50 == 0:
            print(f"  {i}/{len(events)} events priced")
    write_games(args.out, rows)


if __name__ == "__main__":
    main()
