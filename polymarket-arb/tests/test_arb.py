import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from arb import BUY, SELL, Event, Leg, Market, ladder_pairs, scan_event, sort_levels, threshold, walk  # noqa: E402
from scan import parse_event  # noqa: E402


def book(bids=(), asks=()):
    return {"bids": [{"price": str(p), "size": str(s)} for p, s in bids],
            "asks": [{"price": str(p), "size": str(s)} for p, s in asks]}


def kinds(opps, kind):
    return [o for o in opps if o.kind == kind]


class Walk(unittest.TestCase):
    def test_sort_levels(self):
        raw = [{"price": "0.40", "size": "5"}, {"price": "0.45", "size": "0"}, {"price": "0.42", "size": "3"}]
        self.assertEqual(sort_levels(raw, SELL), [(0.42, 3.0), (0.40, 5.0)])
        self.assertEqual(sort_levels(raw, BUY), [(0.40, 5.0), (0.42, 3.0)])

    def test_merge_walks_depth(self):
        yes = Leg("y", BUY, [(0.45, 100)])
        no = Leg("n", BUY, [(0.50, 50), (0.53, 100)])
        units, cost, profit, edge = walk([yes, no], 1.0, 0.0)
        # 50 units at 0.95 (+0.05 each) then 50 at 0.98 (+0.02 each); YES depth runs out
        self.assertAlmostEqual(units, 100)
        self.assertAlmostEqual(profit, 50 * 0.05 + 50 * 0.02)
        self.assertAlmostEqual(cost, 50 * 0.95 + 50 * 0.98)
        self.assertAlmostEqual(edge, 0.05)

    def test_fees_cut_depth(self):
        yes = Leg("y", BUY, [(0.45, 100)])
        no = Leg("n", BUY, [(0.50, 50), (0.53, 100)])
        units, _, profit, _ = walk([yes, no], 1.0, 0.05)
        fee1 = 0.05 * 0.45 * 0.55 + 0.05 * 0.5 * 0.5
        self.assertAlmostEqual(units, 50)  # second level no longer clears its fee
        self.assertAlmostEqual(profit, 50 * (0.05 - fee1))

    def test_no_edge(self):
        units, _, profit, edge = walk([Leg("y", BUY, [(0.5, 10)]), Leg("n", BUY, [(0.51, 10)])], 1.0, 0.0)
        self.assertEqual((units, profit), (0, 0))
        self.assertAlmostEqual(edge, -0.01)

    def test_fixed_cost_and_max_units(self):
        legs = [Leg("y", BUY, [(0.45, 100)]), Leg("n", BUY, [(0.50, 100)])]
        units, _, profit, _ = walk(legs, 1.0, 0.0, fixed_cost=0.5, max_units=10)
        self.assertAlmostEqual(units, 10)
        self.assertAlmostEqual(profit, 10 * 0.05 - 0.5)

    def test_empty_book(self):
        self.assertEqual(walk([Leg("y", BUY, []), Leg("n", BUY, [(0.4, 1)])], 1.0, 0.0)[0], 0)


class Detectors(unittest.TestCase):
    def three_way(self, books, augmented=False):
        ms = [Market(f"Will {c} win?", f"{c}y", f"{c}n", "2026-11-03", c) for c in "ABC"]
        return scan_event(Event("Who wins?", "who-wins", ms, neg_risk=True, augmented=augmented), books)

    def test_binary_merge_and_split(self):
        m = Market("Will it rain?", "y", "n", "2026-11-01")
        ev = Event("Rain", "rain", [m])
        opps = scan_event(ev, {"y": book(asks=[(0.45, 10)]), "n": book(asks=[(0.5, 10)])})
        self.assertAlmostEqual(kinds(opps, "buy YES+NO, merge")[0].profit, 0.5)
        opps = scan_event(ev, {"y": book(bids=[(0.55, 10)]), "n": book(bids=[(0.5, 10)])})
        self.assertAlmostEqual(kinds(opps, "split, sell YES+NO")[0].profit, 0.5)

    def test_fair_binary_finds_nothing(self):
        m = Market("Will it rain?", "y", "n")
        books = {"y": book([(0.49, 100)], [(0.51, 100)]), "n": book([(0.49, 100)], [(0.51, 100)])}
        self.assertEqual(scan_event(Event("Rain", "rain", [m]), books), [])

    def test_buy_every_no_convert(self):
        books = {f"{c}n": book(asks=[(p, 20)]) for c, p in zip("ABC", (0.60, 0.65, 0.70))}
        o = kinds(self.three_way(books), "buy every NO, convert")[0]
        self.assertAlmostEqual(o.profit, 20 * (2 - 1.95))  # 3 NOs convert into $2
        self.assertTrue(o.instant)

    def test_split_all_sell_every_yes(self):
        books = {f"{c}y": book(bids=[(p, 20)]) for c, p in zip("ABC", (0.40, 0.35, 0.30))}
        self.assertAlmostEqual(kinds(self.three_way(books), "split all, sell every YES")[0].profit, 20 * 0.05)

    def test_buy_one_no_convert_sell_yes(self):
        books = {"An": book(asks=[(0.55, 10)]), "By": book(bids=[(0.30, 10)]), "Cy": book(bids=[(0.30, 10)])}
        o = kinds(self.three_way(books), "buy one NO, convert, sell YES")
        self.assertEqual(len(o), 1)
        self.assertAlmostEqual(o[0].profit, 10 * 0.05)

    def test_buy_every_yes_only_when_not_augmented(self):
        books = {f"{c}y": book(asks=[(p, 10)]) for c, p in zip("ABC", (0.30, 0.30, 0.35))}
        o = kinds(self.three_way(books), "buy every YES, hold")
        self.assertAlmostEqual(o[0].profit, 10 * 0.05)
        self.assertFalse(o[0].instant)
        self.assertEqual(kinds(self.three_way(books, augmented=True), "buy every YES, hold"), [])

    def test_neg_risk_skipped_if_a_market_is_closed(self):
        ms = [Market("A?", "Ay", "An", label="A"), Market("B?", "By", "Bn", label="B", active=False)]
        books = {"Ay": book(asks=[(0.3, 10)]), "By": book(asks=[(0.3, 10)])}
        self.assertEqual(kinds(scan_event(Event("x", "x", ms, neg_risk=True), books), "buy every YES, hold"), [])

    def test_ladder_above(self):
        ms = [Market("Will BTC be above $100k on Dec 31?", "Ly", "Ln", "2026-12-31"),
              Market("Will BTC be above $110k on Dec 31?", "Hy", "Hn", "2026-12-31")]
        books = {"Ly": book(asks=[(0.60, 10)]), "Hn": book(asks=[(0.35, 10)])}
        o = kinds(scan_event(Event("BTC", "btc", ms), books), "ladder: YES easier + NO harder")
        self.assertEqual([l.token for l in o[0].legs], ["Ly", "Hn"])
        self.assertAlmostEqual(o[0].profit, 0.5)

    def test_ladder_below_picks_higher_bar_as_easier(self):
        ms = [Market("BTC dip to $80k?", "Ly", "Ln"), Market("BTC dip to $90k?", "Hy", "Hn")]
        pairs = ladder_pairs(ms)
        self.assertEqual([(a.yes, b.yes) for a, b in pairs], [("Hy", "Ly")])

    def test_ladder_needs_same_end_date(self):
        ms = [Market("above $100k", "Ly", "Ln", "2026-12-31"), Market("above $110k", "Hy", "Hn", "2027-01-31")]
        books = {"Ly": book(asks=[(0.60, 10)]), "Hn": book(asks=[(0.35, 10)])}
        self.assertEqual(kinds(scan_event(Event("BTC", "btc", ms), books), "ladder: YES easier + NO harder"), [])


class Parsing(unittest.TestCase):
    def test_threshold(self):
        self.assertEqual(threshold("Will BTC be above $120k?"), ("above", 120000.0))
        self.assertEqual(threshold("↑ 120,000"), ("above", 120000.0))
        self.assertEqual(threshold("Will ETH dip to $2,500 in October?"), ("below", 2500.0))
        self.assertEqual(threshold("More than $1.5M raised?"), ("above", 1500000.0))
        self.assertIsNone(threshold("Who will win the election?"))

    def test_parse_gamma_event(self):
        e = {"title": "Who wins?", "slug": "w", "negRisk": True, "negRiskAugmented": False, "markets": [
            {"question": "A?", "clobTokenIds": '["1","2"]', "outcomes": '["Yes","No"]', "active": True,
             "closed": False, "endDate": "2026-11-03T00:00:00Z", "groupItemTitle": "A"},
            {"question": "Up or down?", "clobTokenIds": '["3","4"]', "outcomes": '["Up","Down"]', "active": True}]}
        ev = parse_event(e)
        self.assertTrue(ev.neg_risk)
        self.assertEqual([(m.yes, m.no, m.end_date, m.label) for m in ev.markets],
                         [("1", "2", "2026-11-03", "A"), ("3", "4", "", "Up or down? [Up]")])


if __name__ == "__main__":
    unittest.main()
