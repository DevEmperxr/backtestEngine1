# 064 — Intraday momentum: does the morning move predict the NY afternoon? EURUSD / GBPUSD / AUDUSD 2023 + 2024

**Date:** 2026-10-07 · script: research/regime/intraday_momentum_064.py · **Status:** pre-registered (descriptive, POI layer)

## Literature
Gao, Han, Li & Zhou (2018, JFE): on US stock indices the first half-hour return (previous close -> 10:00 ET)
predicts the last half-hour (15:30–16:00). Elaut, Frömmel & Lampaert (2018): the same in RUB/USD. FX majors trade 24h,
so "the day" is defined here as the FX day (17:00 New York -> 17:00 New York).

## 0. Who loses, and why
Traders who must trade late in the day **in the direction of the day's move, whatever the price**: hedgers
rebalancing exposure that moved during the day, funds catching up with the day's move, dealers squaring positions
before the close (Gao et al.'s infrequent rebalancers / late-informed traders). Being in front of that predictable
late flow is the edge.

## 3. POI / predictor (fixed now)
**Morning move** = mid price change from the FX-day open (17:00 New York the previous evening) to **09:30 New York**.
Direction = its sign. Weekdays only.

## Targets (fixed now)
- **T1 (primary): NY afternoon 12:00 -> 16:00 New York** (mid change).
- **T2: last half hour 15:30 -> 16:00 New York** (the literature's analogue).
Trade direction = sign of the morning move; result = target change in that direction (pips, mid, before costs).

## News rule
**Primary sample:** days with no red release of the pair's currencies between 1 h before the target window starts
and its end (tradable under the standing ±1 h rule). All days reported as a reference.

## Tests and pass bar
For each target, EUR+GBP pooled, primary sample:
- mean signed result > 0 in **both** 2023 and 2024;
- pooled t-statistic > **2.24** (two targets: 0.05/2, two-sided);
- pooled mean result larger than the pair's typical spread (EURUSD ~0.3, GBPUSD ~0.8 pips per round trip).
Also reported: correlation of morning move and target move, results by morning-move size (top vs bottom half), and
AUDUSD as a check. A target that passes goes to the next layers (confirmation, context, execution with costs).

## Results
_(filled after the run)_
