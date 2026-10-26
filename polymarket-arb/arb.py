"""Arbitrage detectors for Polymarket order books. Pure functions, no I/O.

Every opportunity is a basket of legs (buy at the asks or sell at the bids)
plus a fixed cash flow per unit from Polymarket's position primitives:

  merge   1 YES + 1 NO of a market         -> $1        (instant)
  split   $1                                -> 1 YES + 1 NO (instant)
  convert (neg-risk) k NO shares, one in each of k markets of the event
          -> (k - 1) USDC + 1 YES in each of the other N - k markets (instant)
  resolve exactly one outcome of a neg-risk event pays $1 (wait for settlement)

The detectors walk each book level by level and keep adding units while the
marginal unit still clears `min_edge` after taker fees, so the reported size is
what the visible depth can actually absorb.
"""

import re
from dataclasses import dataclass, field

BUY, SELL = "buy", "sell"


@dataclass
class Leg:
    token: str
    side: str          # BUY takes asks, SELL hits bids
    levels: list       # [(price, size)], best first
    label: str = ""


@dataclass
class Opportunity:
    kind: str
    event: str
    legs: list
    size: float        # units of the basket
    cost: float        # cash paid for the buy legs including fees
    profit: float      # dollars, after fees and fixed costs
    edge: float        # profit per unit on the first (best) unit
    instant: bool      # True if it closes without waiting for resolution
    end_date: str = ""
    note: str = ""
    key: tuple = field(default=())


def taker_fee(price, size, rate):
    """Polymarket taker fee: shares x rate x p x (1 - p)."""
    return size * rate * price * (1 - price)


def sort_levels(levels, side):
    """Best price first. Polymarket returns bids ascending and asks descending."""
    lv = [(float(l["price"]), float(l["size"])) if isinstance(l, dict) else (float(l[0]), float(l[1]))
          for l in levels]
    lv = [l for l in lv if l[1] > 0]
    return sorted(lv, key=lambda l: -l[0] if side == SELL else l[0])


def walk(legs, cash_per_unit, fee_rate, min_edge=0.0, fixed_cost=0.0, max_units=None):
    """Fill the basket unit by unit across book levels while it stays profitable.

    cash_per_unit is the fixed cash each unit returns (+) or needs (-) from
    merge / split / convert / resolution. Returns (units, buy_cost, profit, first_edge).
    """
    if not legs or any(not leg.levels for leg in legs):
        return 0.0, 0.0, 0.0, 0.0
    idx = [0] * len(legs)
    left = [leg.levels[0][1] for leg in legs]
    units = cost = profit = 0.0
    first_edge = None
    while True:
        prices = [leg.levels[i][0] for leg, i in zip(legs, idx)]
        per_unit = cash_per_unit
        for leg, p in zip(legs, prices):
            fee = taker_fee(p, 1, fee_rate)
            per_unit += (p - fee) if leg.side == SELL else -(p + fee)
        if first_edge is None:
            first_edge = per_unit
        if per_unit <= min_edge:
            break
        chunk = min(left)
        if max_units is not None:
            chunk = min(chunk, max_units - units)
        units += chunk
        profit += per_unit * chunk
        cost += sum((p + taker_fee(p, 1, fee_rate)) * chunk
                    for leg, p in zip(legs, prices) if leg.side == BUY)
        if max_units is not None and units >= max_units:
            break
        exhausted = False
        for j in range(len(legs)):
            left[j] -= chunk
            if left[j] <= 1e-9:
                idx[j] += 1
                if idx[j] >= len(legs[j].levels):
                    exhausted = True
                else:
                    left[j] = legs[j].levels[idx[j]][1]
        if exhausted:
            break
    if units > 0:
        profit -= fixed_cost
    return units, cost, profit, first_edge or 0.0


# ------------------------------------------------------------ market model

@dataclass
class Market:
    question: str
    yes: str           # token ids
    no: str
    end_date: str = ""
    label: str = ""    # groupItemTitle, e.g. "↑ 120,000" or a candidate name
    active: bool = True


@dataclass
class Event:
    title: str
    slug: str
    markets: list
    neg_risk: bool = False
    augmented: bool = False


def _opp(kind, event, legs, cash, books_fee, instant, args, end_date="", note=""):
    units, cost, profit, edge = walk(legs, cash, books_fee, args["min_edge"], args["fixed_cost"],
                                     args.get("max_units"))
    if units <= 0 or profit < args["min_profit"]:
        return None
    return Opportunity(kind, event.title, legs, units, cost, profit, edge, instant, end_date, note,
                       key=(kind, event.slug) + tuple(l.token + l.side for l in legs))


def scan_event(event, books, fee_rate=0.0, min_edge=0.0, min_profit=0.0, fixed_cost=0.0,
               max_units=None):
    """All opportunities in one event. `books` maps token id -> {"bids": [...], "asks": [...]}."""
    args = dict(min_edge=min_edge, min_profit=min_profit, fixed_cost=fixed_cost, max_units=max_units)
    found = []

    def leg(token, side, label):
        book = books.get(token) or {}
        return Leg(token, side, sort_levels(book.get("asks" if side == BUY else "bids", []), side), label)

    live = [m for m in event.markets if m.active]

    # 1. Single binary market: YES + NO should cost exactly $1.
    for m in live:
        name = m.label or m.question
        found.append(_opp("buy YES+NO, merge", event,
                          [leg(m.yes, BUY, f"YES {name}"), leg(m.no, BUY, f"NO {name}")],
                          1.0, fee_rate, True, args))
        found.append(_opp("split, sell YES+NO", event,
                          [leg(m.yes, SELL, f"YES {name}"), leg(m.no, SELL, f"NO {name}")],
                          -1.0, fee_rate, True, args))

    # 2. Neg-risk events: exactly one outcome wins.
    if event.neg_risk and len(live) >= 2 and len(live) == len(event.markets):
        n = len(live)
        end = max(m.end_date for m in live)
        if not event.augmented:
            # Holding one YES of every outcome pays $1 at resolution. Unsafe on
            # augmented events, whose outcome list can still grow.
            found.append(_opp("buy every YES, hold", event,
                              [leg(m.yes, BUY, f"YES {m.label or m.question}") for m in live],
                              1.0, fee_rate, False, args, end,
                              "pays $1 only once the event resolves"))
        # Buy NO on every outcome and convert them all into N-1 USDC now.
        found.append(_opp("buy every NO, convert", event,
                          [leg(m.no, BUY, f"NO {m.label or m.question}") for m in live],
                          float(n - 1), fee_rate, True, args))
        # Split $1 in every market, sell every YES, convert the N NOs back to N-1 USDC.
        found.append(_opp("split all, sell every YES", event,
                          [leg(m.yes, SELL, f"YES {m.label or m.question}") for m in live],
                          -1.0, fee_rate, True, args))
        # Buy one NO, convert it into a YES in every other outcome, sell those.
        for i, m in enumerate(live):
            legs = [leg(m.no, BUY, f"NO {m.label or m.question}")]
            legs += [leg(o.yes, SELL, f"YES {o.label or o.question}") for j, o in enumerate(live) if j != i]
            found.append(_opp("buy one NO, convert, sell YES", event, legs, 0.0, fee_rate, True, args))

    # 3. Threshold ladders ("above $100k", "above $110k"): a higher bar can't be likelier.
    for a, b in ladder_pairs(live):
        if a.end_date != b.end_date:
            continue
        # YES on the easier bar + NO on the harder bar pays at least $1 in every outcome.
        found.append(_opp("ladder: YES easier + NO harder", event,
                          [leg(a.yes, BUY, f"YES {a.label or a.question}"),
                           leg(b.no, BUY, f"NO {b.label or b.question}")],
                          1.0, fee_rate, False, args, a.end_date,
                          "pays at least $1 at resolution; both legs must use the same price source"))
    return [o for o in found if o]


_NUM = r"\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*([kKmMbB])?"
_ABOVE = re.compile(r"(above|over|greater than|more than|at least|reach|hit|≥|>|↑)\s*" + _NUM, re.I)
_BELOW = re.compile(r"(below|under|less than|fewer than|dip to|drop to|≤|<|↓)\s*" + _NUM, re.I)


def threshold(text):
    """'Will BTC be above $120k on Dec 31?' -> ('above', 120000.0)."""
    for direction, rx in (("above", _ABOVE), ("below", _BELOW)):
        m = rx.search(text or "")
        if m:
            value = float(m.group(2).replace(",", ""))
            value *= {"k": 1e3, "m": 1e6, "b": 1e9}.get((m.group(3) or "").lower(), 1)
            return direction, value
    return None


def ladder_pairs(markets):
    """Pairs (easier, harder) of same-direction threshold markets in one event.
    For "above" the lower bar is easier; for "below" the higher bar is."""
    parsed = []
    for m in markets:
        t = threshold(m.label) or threshold(m.question)
        if t:
            parsed.append((t[0], t[1], m))
    pairs = []
    for direction in ("above", "below"):
        group = sorted(((v, m) for d, v, m in parsed if d == direction), key=lambda x: x[0])
        if direction == "below":
            group.reverse()  # for "below", a higher bar is the easier one
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                if group[i][0] != group[j][0]:
                    pairs.append((group[i][1], group[j][1]))
    return pairs
