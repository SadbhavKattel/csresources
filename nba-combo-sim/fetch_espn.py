"""Pull NBA results and closing sportsbook moneylines from ESPN's public API.

Use this when Kalshi history is unavailable. Moneylines are converted to
implied probabilities and de-vigged, which approximates the price a liquid
prediction market would quote before tip-off.

Usage:
    python3 fetch_espn.py --start 2025-10-01 --end 2026-10-26 --out games_espn.csv
"""

import argparse
from datetime import date, datetime

from common import ET, american_to_prob, daterange, devig, get_json, parse_date, season_of, write_games

SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary"
GAME_TYPES = {2, 3, 5}  # regular season, playoffs, play-in; skips preseason and All-Star


def moneylines(odds):
    """Return (home_ml, away_ml) from an ESPN odds entry, whichever format it uses."""
    if not odds:
        return None, None
    h, a = odds.get("homeTeamOdds", {}), odds.get("awayTeamOdds", {})
    if h.get("moneyLine") is not None and a.get("moneyLine") is not None:
        return h["moneyLine"], a["moneyLine"]
    ml = odds.get("moneyline") or {}
    for when in ("close", "current", "open"):
        hv = (ml.get("home") or {}).get(when, {}).get("odds")
        av = (ml.get("away") or {}).get(when, {}).get("odds")
        if hv not in (None, "OFF", "EVEN") and av not in (None, "OFF", "EVEN"):
            return hv, av
    return None, None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", default="2025-10-01")
    ap.add_argument("--end", default=date.today().isoformat())
    ap.add_argument("--out", default="games_espn.csv")
    ap.add_argument("--cache", default=".cache/espn")
    args = ap.parse_args()

    rows = []
    for d in daterange(parse_date(args.start), parse_date(args.end)):
        board = get_json(SCOREBOARD, {"dates": d.strftime("%Y%m%d"), "limit": 100}, args.cache)
        for ev in (board or {}).get("events", []):
            if ev.get("season", {}).get("type") not in GAME_TYPES:
                continue
            comp = ev["competitions"][0]
            if not comp.get("status", ev.get("status", {})).get("type", {}).get("completed"):
                continue
            teams = {c["homeAway"]: c for c in comp["competitors"]}
            home, away = teams["home"], teams["away"]
            hml, aml = moneylines((comp.get("odds") or [None])[0])
            if hml is None:
                summ = get_json(SUMMARY, {"event": ev["id"]}, args.cache) or {}
                hml, aml = moneylines((summ.get("pickcenter") or [None])[0])
            hp = ap_ = None
            if hml is not None:
                hp, ap_ = devig(american_to_prob(hml), american_to_prob(aml))
            winner = home if home.get("winner") else away if away.get("winner") else None
            tip = datetime.fromisoformat(ev["date"].replace("Z", "+00:00")).astimezone(ET).date()
            rows.append({"date": tip.isoformat(), "season": season_of(tip), "game_id": ev["id"],
                         "home": home["team"]["abbreviation"], "away": away["team"]["abbreviation"],
                         "home_prob": f"{hp:.4f}" if hp else "", "away_prob": f"{ap_:.4f}" if ap_ else "",
                         "winner": winner["team"]["abbreviation"] if winner else "",
                         "source": "espn-moneyline-devig"})
        if d.day == 1:
            print(f"  through {d}: {len(rows)} games")
    # The scoreboard for one date can repeat a game listed under the neighbouring date.
    write_games(args.out, list({r["game_id"]: r for r in rows}.values()))


if __name__ == "__main__":
    main()
