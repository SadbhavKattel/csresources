# Polymarket arbitrage scanner

Scans every open Polymarket event against live order books and reports
baskets that lock in a profit after taker fees, sized to the visible depth.
It also logs how long each one survives. It reads public endpoints only and
never trades.

```bash
cd polymarket-arb
python3 scan.py                           # one pass
python3 scan.py --watch 15 --minutes 120  # rescan every 15 s for 2 h, log persistence
python3 -m unittest discover -s tests -v
```

Python 3.9+, stdlib only, no keys. Output goes to `opportunities.csv`.

## What it looks for

| Kind | Trade | Pays | Closes |
|---|---|---|---|
| buy YES+NO, merge | YES ask + NO ask < $1 | merge into $1 | instant |
| split, sell YES+NO | YES bid + NO bid > $1 | split $1 into both, sell both | instant |
| buy every NO, convert | N-outcome event: sum of NO asks < N − 1 | Neg Risk Adapter converts N NOs into N − 1 USDC | instant |
| split all, sell every YES | sum of YES bids > $1 | split in every market, sell YES, convert the NOs back | instant |
| buy one NO, convert, sell YES | NO ask on one outcome < sum of YES bids on all the others | convert that NO into a YES on every other outcome, sell them | instant |
| buy every YES, hold | sum of YES asks < $1 | exactly one outcome pays $1 | at resolution |
| ladder | YES on "above $100k" + NO on "above $110k" < $1 | at least $1 in every outcome | at resolution |

Each detector walks the order book level by level and stops at the first
unit that no longer clears fees. `--fee-rate` is the taker coefficient in
`shares × rate × p × (1 − p)`. The default 0.05 matches most categories;
check the market you would trade. Makers pay no fee.

The scanner skips these on purpose:
- **Buy every YES on augmented neg-risk events:** new outcomes can still be
  added, and the "Other" outcome's definition shifts as that happens.
- **Neg-risk baskets where any market is closed or not accepting orders.**
- **Ladders whose two markets end on different dates.**

## What the research says, before you spend money

Arbitrage like this does exist on Polymarket, but you are unlikely to profit
from it with a script like this one.

- **About $40M was taken, mostly by bots.** The largest study of Polymarket
  arbitrage ([Saguillo et al., AFT 2025](https://arxiv.org/abs/2508.03474))
  estimates about $40M of realised arbitrage profit from April 2024 to April
  2025, across more than 7,000 mispriced markets. That figure is the total
  over a year of whoever was fastest, not a per-person yield.
- **Most of that couldn't actually be traded before settlement.** A 2026
  follow-up ([arXiv 2608.00666](https://arxiv.org/html/2608.00666v1)) checks
  which mispricings the contracts actually let you exploit before settlement.
  It puts executable profit at about **$1.12M**: $1.086M through NO→YES
  conversion, and $32K from buying full baskets and holding them to
  settlement. The YES-side violations you see most often have no conversion
  path, so they're mostly not exploitable before settlement.
- **When it appears, it lasts seconds and is small.** On 75M+ order-book
  snapshots across 173 NBA games
  ([Cheng, Yang & Zou, 2026](https://arxiv.org/abs/2605.00864)):
  - **Single-market:** only 7 executable episodes, with a median life of
    **3.6 seconds**.
  - **Cross-market (combinatorial):** 290 episodes, with a median return of
    1.01%. 76.9% of them were capped at about **15 shares**.

  A reviewer notes that even those counts may be too high, because the
  snapshots don't model latency.
- **Fees ate the rest.** An independent run found that 125 snapshots which
  looked like locked profit
  [all turned negative after fees and conversion rules](https://howprosbet.com/prediction-market-sportsbook-arbitrage/).

What that means for you:

1. **Instant arbs** (merge, split, convert) are the only riskless kinds, and
   they're a latency race. A 15-second polling scanner sees them after the
   bots have closed them. To compete you need a websocket feed, co-located
   execution and pre-funded positions, and you would still be racing
   professional shops for about $15 trades.
2. **Hold-to-resolution arbs** (buy every YES, ladders) last longer because
   they tie up capital. A 1¢ edge on a 99¢ basket held two months is about
   6% a year, roughly a money-market rate. You also carry resolution risk:
   UMA disputes, ambiguous wording, or two "related" markets resolving on
   different sources.
3. **Kalshi vs Polymarket** "arbs" are the most-advertised kind and the
   riskiest. The two venues resolve under different rules: Polymarket uses
   UMA's oracle and Kalshi its own rulebook. Mismatched wording can make
   both legs lose. The scanner leaves this out on purpose. A hedge that can
   lose on both sides isn't arbitrage.

"Less risk, more reward" doesn't exist here. Real arbitrage is low risk *and*
low reward, and the reward goes to the fastest. Anything with a large payout
carries risk that hasn't been priced, whether in resolution, liquidity, or
one leg filling without the other.

## How to use it honestly

Run `--watch 15 --minutes 240` for a few days and read the persistence summary.
- **If opportunities live under a minute:** a polling bot will lose that race.
- **If they live for hours at a few cents:** check whether the depth and the
  annualised return beat simply holding cash.

Trust the logged results over any blog post, this README included.

## Limits

- Reads the top 100 levels that the `/books` endpoint returns. Doesn't model
  latency or other traders' cancellations, so it shows the best case.
- Assumes merge, split and convert cost only `--fixed-cost` in gas (default
  $0.02). Through Polymarket's relayer they are usually gasless.
- Ladder detection parses thresholds from market titles, such as "above
  $120k", "↑ 120,000" or "dip to $80k". Read both markets' rules before
  trusting a ladder hit.
- Written and tested without access to the live API. The tests use
  hand-built order books that follow the documented formats. Expect small
  field-name fixes on the first live run.
