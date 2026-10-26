import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common import american_to_prob, devig, season_of  # noqa: E402
from fetch_espn import moneylines  # noqa: E402
from fetch_kalshi import cents, event_date  # noqa: E402
from simulate import buy, kalshi_fee, simulate, summarise, write_report  # noqa: E402


def game(d, home, away, hp, ap, winner, gid=None):
    return {"date": d, "season": season_of(date.fromisoformat(d)), "game_id": gid or f"{d}{home}",
            "home": home, "away": away, "home_prob": hp, "away_prob": ap,
            "winner": winner, "source": "test"}


class Odds(unittest.TestCase):
    def test_american(self):
        self.assertAlmostEqual(american_to_prob(-150), 0.6)
        self.assertAlmostEqual(american_to_prob("+150"), 0.4)

    def test_devig(self):
        h, a = devig(american_to_prob(-110), american_to_prob(-110))
        self.assertAlmostEqual(h, 0.5)
        self.assertAlmostEqual(h + a, 1.0)

    def test_espn_formats(self):
        self.assertEqual(moneylines({"homeTeamOdds": {"moneyLine": -200}, "awayTeamOdds": {"moneyLine": 170}}),
                         (-200, 170))
        new = {"moneyline": {"home": {"close": {"odds": "-200"}}, "away": {"close": {"odds": "+170"}}}}
        self.assertEqual(moneylines(new), ("-200", "+170"))
        self.assertEqual(moneylines(None), (None, None))

    def test_season(self):
        self.assertEqual(season_of(date(2025, 10, 21)), "2025-26")
        self.assertEqual(season_of(date(2026, 6, 10)), "2025-26")
        self.assertEqual(season_of(date(2026, 10, 25)), "2026-27")


class Kalshi(unittest.TestCase):
    def test_ticker(self):
        self.assertEqual(event_date("KXNBAGAME-25OCT21HOUOKC"), (date(2025, 10, 21), "HOUOKC"))
        self.assertEqual(event_date("garbage"), (None, None))

    def test_price_fields(self):
        self.assertEqual(cents({"close": 65}), 0.65)
        self.assertEqual(cents({"close_dollars": "0.6500"}), 0.65)
        self.assertIsNone(cents({}))

    def test_fee(self):
        # Kalshi's worked example: 100 contracts at 50c -> 0.07*100*0.25 = $1.75
        self.assertEqual(kalshi_fee(100, 0.5, 0.07), 1.75)
        # rounds up to the next cent: 0.07*1*0.5*0.5 = 0.0175 -> $0.02
        self.assertEqual(kalshi_fee(1, 0.5, 0.07), 0.02)

    def test_buy_stays_within_stake(self):
        c, cost = buy(10, 0.2, 0.07)
        self.assertEqual(c, 47)  # 10 / (0.2 + 0.0112) = 47.3
        self.assertLessEqual(cost, 10)

    def test_buy_fee_rounding_never_exceeds_stake(self):
        # 28 contracts at 0.34125 would cost $9.555 + $0.45 fee = $10.005
        c, cost = buy(10, 0.75 * 0.70 * 0.65, 0.07)
        self.assertEqual(c, 27)
        self.assertLessEqual(cost, 10)


class Simulation(unittest.TestCase):
    def setUp(self):
        self.games = [
            # day 1: both favourites win -> combo hits
            game("2025-11-01", "BOS", "NYK", 0.6, 0.4, "BOS"),
            game("2025-11-01", "LAL", "DEN", 0.2, 0.8, "DEN"),
            # day 2: one favourite loses -> combo misses
            game("2025-11-02", "OKC", "UTA", 0.9, 0.1, "OKC"),
            game("2025-11-02", "MIA", "ORL", 0.55, 0.45, "ORL"),
        ]

    def test_no_fee_arithmetic(self):
        log = simulate(self.games, stake=10, bankroll=100, fee_rate=0)
        d1, d2 = log
        self.assertEqual(d1["picks"], "DEN@0.80 BOS@0.60")
        self.assertAlmostEqual(d1["combo_price"], 0.48)
        self.assertEqual(d1["contracts"], 20)  # floor(10 / 0.48)
        self.assertTrue(d1["hit"])
        self.assertAlmostEqual(d1["pnl"], 20 - 20 * 0.48)
        self.assertFalse(d2["hit"])
        self.assertEqual(d2["legs_won"], 1)
        self.assertAlmostEqual(d2["pnl"], -d2["cost"])
        self.assertAlmostEqual(d2["bankroll"], 100 + d1["pnl"] + d2["pnl"])

    def test_max_legs_keeps_most_confident(self):
        log = simulate(self.games, max_legs=1, fee_rate=0)
        self.assertEqual([r["picks"] for r in log], ["DEN@0.80", "OKC@0.90"])
        self.assertTrue(all(r["hit"] for r in log))

    def test_markup_raises_price(self):
        log = simulate(self.games[:2], markup=0.1, fee_rate=0)
        self.assertAlmostEqual(log[0]["combo_price"], 0.528)

    def test_singles_baseline(self):
        log = simulate(self.games, stake=10, bankroll=100, fee_rate=0)
        s = summarise(log, singles=True, start=100)
        self.assertEqual((s["hits"], s["tries"]), (3, 4))
        # day 1 singles: $5 on DEN@0.8 (6 contracts) and $5 on BOS@0.6 (8 contracts)
        self.assertAlmostEqual(log[0]["singles_pnl"], (6 - 4.8) + (8 - 4.8))

    def test_stops_when_bust(self):
        loser = [game(f"2025-11-{d:02d}", "BOS", "NYK", 0.6, 0.4, "NYK") for d in range(1, 8)]
        log = simulate(loser, stake=10, bankroll=25, fee_rate=0)
        self.assertEqual(sum(r["cost"] > 0 for r in log), 2)
        self.assertGreaterEqual(log[-1]["bankroll"], 0)

    def test_report_renders(self):
        log = simulate(self.games)
        sweep = [("All games", summarise(log))]

        class A:
            stake, bankroll, markup, fee_rate, max_legs, min_prob = 10, 1000, 0, 0.07, None, 0

        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "r.html")
            write_report(path, self.games, log, sweep, A)
            with open(path) as f:
                self.assertIn("<svg", f.read())


if __name__ == "__main__":
    unittest.main()
