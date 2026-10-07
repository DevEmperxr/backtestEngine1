# 064 — Intraday momentum: does the morning move predict the NY afternoon? EURUSD / GBPUSD / AUDUSD 2023 + 2024

**Date:** 2026-10-07 · script: research/regime/intraday_momentum_064.py · **Status:** done. FAIL on both targets

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
results.json, days.parquet. Result = target move in the direction of the morning move (pips, mid, before costs).

| EUR+GBP, news-free days | 2023 | 2024 | both | hit rate |
|---|---|---|---|---|
| **T1 NY afternoon 12–16** | −1.27 (t −1.3, n 360) | −0.15 (t −0.2, n 345) | **−0.72 (t −1.1)** | 47.8% |
| **T2 last half hour 15:30–16** | +0.49 (t 1.9, n 387) | −0.02 (t −0.1, n 380) | **+0.23 (t 1.4)** | 54.2% |

All days (reference): T1 −0.33 pips (t −0.5); T2 +0.12 (t 0.7). By pair (news-free, T1): EUR −0.49, GBP −0.96,
AUD −0.48; (T2): EUR +0.24, GBP +0.23, AUD +0.15. Correlation morning move vs target: T1 −0.03, T2 +0.06.
Big vs small morning moves: no consistent difference.

**Verdict: FAIL on both.**
- **NY afternoon:** no momentum. If anything the afternoon leans slightly *against* the morning move
  (−0.7 pips, not significant).
- **Last half hour:** the right direction, and price moves with the morning 54% of the time, but the average is
  only **+0.2 pips**, below even EURUSD's spread, and it only showed in 2023. The literature's equity effect exists
  here in sign only, far too small to trade.

