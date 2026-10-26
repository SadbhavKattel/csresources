"""Shared helpers: the games CSV schema, HTTP with retries, odds conversions."""

import csv
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

# One row per game. home_prob / away_prob are the pre-game prices (0-1) you
# would pay for each side; on Kalshi they can sum to slightly more than 1.
FIELDS = ["date", "season", "game_id", "home", "away",
          "home_prob", "away_prob", "winner", "source"]


def season_of(d: date) -> str:
    """NBA season label for a game date: 2025-11-03 -> '2025-26'."""
    start = d.year if d.month >= 8 else d.year - 1
    return f"{start}-{str(start + 1)[2:]}"


def daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def get_json(url, params=None, cache_dir=None, retries=5):
    """GET a JSON document, retrying on 429/5xx. Responses are cached on disk
    so an interrupted fetch can resume without re-downloading."""
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    cache_path = None
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        safe = urllib.parse.quote(url, safe="")[-200:]
        cache_path = os.path.join(cache_dir, safe + ".json")
        if os.path.exists(cache_path):
            with open(cache_path) as f:
                return json.load(f)
    delay = 1.0
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"User-Agent": "nba-combo-sim/1.0",
                                                   "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.load(resp)
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code not in (429, 500, 502, 503, 504) or attempt == retries - 1:
                raise
        except urllib.error.URLError:
            if attempt == retries - 1:
                raise
        time.sleep(delay)
        delay *= 2
    if cache_path:
        with open(cache_path, "w") as f:
            json.dump(data, f)
    return data


def american_to_prob(ml) -> float:
    """-150 -> 0.6, +130 -> 0.4348 (includes the bookmaker's vig)."""
    ml = float(str(ml).replace("+", ""))
    return -ml / (-ml + 100) if ml < 0 else 100 / (ml + 100)


def devig(p_home: float, p_away: float):
    """Remove the bookmaker margin by normalising the two implied probabilities."""
    total = p_home + p_away
    return p_home / total, p_away / total


def write_games(path, rows):
    rows = sorted(rows, key=lambda r: (r["date"], r["game_id"]))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})
    print(f"wrote {len(rows)} games to {path}")


def read_games(path):
    games = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            if not r.get("winner") or not r.get("home_prob") or not r.get("away_prob"):
                continue  # postponed, unfinished, or no pre-game price
            r["home_prob"] = float(r["home_prob"])
            r["away_prob"] = float(r["away_prob"])
            r["season"] = r.get("season") or season_of(parse_date(r["date"]))
            games.append(r)
    return games
