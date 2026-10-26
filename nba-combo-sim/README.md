# NBA daily combo backtest

Simulates one strategy on real NBA prices: every game day, back the market
favourite in every game, put all of that day's picks into a single combo
(parlay), and buy it the way you would on Kalshi. It covers the 2025-26 season
(including playoffs) and the 2026-27 season up to today.

Needs only Python 3.9+ (stdlib). No API keys.

## Run it

```bash
cd nba-combo-sim

# 1. Real prediction-market prices (Kalshi KXNBAGAME markets)
python3 fetch_kalshi.py --start 2025-10-01 --out games_kalshi.csv

# 1b. or, closing sportsbook moneylines with the vig removed (ESPN)
python3 fetch_espn.py --start 2025-10-01 --out games_espn.csv

# 2. Simulate and write report/report.html + report/daily_log.csv
python3 simulate.py games_kalshi.csv --stake 10 --bankroll 1000
```

Both fetchers cache every response under `.cache/`, so a run that gets cut off
picks up where it stopped. The Kalshi fetch makes about two requests per game
(roughly 2,800 for both seasons), so it takes a few minutes.

## How a combo is priced

| Step | Rule |
|---|---|
| Pick | In each game, the side with the higher pre-game price |
| Pre-game price | Kalshi: last hourly YES ask at or before 12:00 ET on game day (`--cutoff-et`). ESPN: closing moneyline, de-vigged |
| Combo price | `P = product of leg prices × (1 + markup)`, capped at 0.99 |
| Contracts | `floor(stake / (P + fee))`. Each pays $1 if every leg wins |
| Fee | Kalshi taker fee: `ceil(0.07 × contracts × P × (1 − P))` cents, charged on entry |

Example: three favourites at 0.75, 0.70 and 0.65 make a combo priced at 0.341.
A $10 stake buys 27 contracts: $9.21 plus $0.43 in fees. If all three win, you get $27 back.

## Options

| Flag | Default | Meaning |
|---|---|---|
| `--stake` | 10 | Dollars per daily combo. The run stops betting once the bankroll falls below it |
| `--bankroll` | 1000 | Starting bankroll |
| `--max-legs N` | all | Keep only the N most confident favourites each day |
| `--min-prob` | 0 | Drop favourites priced below this, e.g. 0.65 |
| `--markup` | 0 | Extra the combo maker charges over the fair product, e.g. 0.05 for 5% |
| `--fee-rate` | 0.07 | Kalshi taker fee coefficient. Use 0 to switch fees off |

## What the report shows

- Bankroll curve for each season: the daily combo against the same picks bet
  as straight singles with the same daily stake
- Combos hit compared with the number a fairly priced market expects (the sum of combo prices)
- A sweep over combo sizes: top 1, 2, ... 6 legs, and every game
- Hit rate by number of legs
- Calibration: how often favourites at each price actually won
- The full day-by-day log: picks, losing legs, price, cost and payout

## What to expect before you run it

- **A full-slate combo almost never hits.** An NBA night usually has 5–12
  games, and favourites typically trade around 0.65–0.70. Ten legs at 0.68
  price at about 0.02, so it should hit roughly 1 night in 50. Over a season
  of about 160 game days that means 2–4 hits. Whether you finish up or down
  depends mostly on which of those nights land.
- **Fair odds still mean no edge.** If prices are calibrated, a combo's
  expected value is zero before costs. Parlaying doesn't create value. It
  only multiplies your exposure to whatever edge or error the prices already
  contain.
- **Costs grow with the number of legs.** The fee is `0.07 × (1 − P)` of what
  you pay. That is about 2% of stake on a single 0.68 favourite, but nearly
  7% on a long-shot combo. Any maker markup on combos comes on top. With
  `--markup 0` the simulation is optimistic.
- **The singles row is the control.** If the combo beats the singles, check
  how many hits produced the gap. One or two lucky nights are not evidence of
  a strategy.

## Caveats

- Kalshi may serve older settled markets from `/historical/...` endpoints, so
  the fetcher tries both the normal and historical paths. It was written
  without live access to the API. If the Kalshi fetch comes back empty, use the ESPN
  fetcher, or open an issue with the error.
- The noon-ET snapshot comes before almost every tip-off. It misses late
  injury news, which can move a price by several cents.
- Games without a pre-game price or a final result (postponed games, very
  thin markets) are skipped.
- Both fetchers default to 2025-10-01 through today. Pass `--start`/`--end` for other ranges.

## Tests

```bash
python3 -m unittest discover -s tests -v
```
