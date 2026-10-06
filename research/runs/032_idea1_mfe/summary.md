# 032 — Idea 1: how far does price move in our favour before the stop? (EURUSD 2023, descriptive)

**Date:** 2026-10-06
**Script:** research/regime/idea1_mfe.py · chart: [mfe_vs_chance_2023.png](mfe_vs_chance_2023.png)
**Status:** done (measurement for choosing a target; no new trades)

## Why
Target design for Idea 1 (023A). The user chose: measure first on 2023, pick a target, check it on
2024. VWAP excluded at the user's request.

## Method
For each 023A trade (same entries), walk the 1s path from entry until the 1.5 × 5m-ATR stop is
touched (exit side; the stop second excluded) or 16:00 London. Record the maximum favourable
excursion (MFE) in pips, in multiples of the stop distance (R), and as a fraction of the distance
to the 5m SMA20 (the current target). Chance reference: a random walk reaches +x·R before −1·R with
probability ≈ (1 − spread/stop)/(1 + x).

## Results (2023)
1h-trending trades (main case, n = 142): stop hit before 16:00 in 57%; median MFE 7.6 pips =
0.89 R = 0.53 of the distance to the MA (median stop 7.8, median distance to the MA 12.3).

| reached in our favour before the stop | 0.25 R | 0.5 R | 0.75 R | 1 R | 1.5 R | 2 R | 3 R |
|---|---|---|---|---|---|---|---|
| Idea 1, 1h trending | 81% | 69% | 56% | 44% | 32% | 29% | 23% |
| pure chance | 77% | 64% | 55% | 48% | 38% | 32% | 24% |
| Idea 1, all trades (697) | 78% | 63% | 53% | 44% | 32% | 25% | 16% |

As a fraction of the way to the MA (trending): 25% of the way 73%, 50% 53%, 75% 42%, 100% 35%.

## Interpretation
**The excursion curve sits on the chance curve.** At every distance, price reaches it before the
stop about as often as random price would (largest gap +5 points at 0.5 R, within the ±4-point
noise for 142 trades). A target can only change the shape of the trade: many small wins or a few
big ones. It cannot add an edge the entry doesn't have. For any target, expected profit ≈ chance
odds × reward − (1 − odds) × risk − spread, which is about −spread.

## Decision
**Changing the target alone won't make Idea 1 profitable**: no distance is reached more often than
chance. Step 2 (pick a target) is therefore moot. The entry (trigger and context) is what lacks
direction. Next work on Idea 1, if continued, should target the entry. Checking on 2024 is not needed
for this conclusion (it was already ~chance there: 026).
