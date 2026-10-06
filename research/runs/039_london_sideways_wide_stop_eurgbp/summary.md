# 039 — London-open sideways fade on EURGBP with a 3× ATR stop (2023 + 2024)

**Date:** 2026-10-06
**File:** research/strategies/039_idea1_lon_ny_wide_stop.py
**Status:** fails: the wider stop doesn't help

## Why (user's choice: "bigger trades")
In 038 the slice was positive before costs (+178 pips, +0.41/trade) but EURGBP's spread (~0.85 pips
per trade vs ~5-pip stops, ≈17% of the risk) made it negative. Doubling the stop to **3 × 5m ATR**
halves the spread's share of the risk and lets fewer trades be knocked out by noise. Target
unchanged (the 5m SMA20, the snap-back point). One pre-chosen change; not a parameter sweep.

## Rules (fixed now)
034 rules (023A entries, window 08:00 London → 16:00 NY, flat 16:00 NY) with **stop_atr_mult = 3.0**
instead of 1.5. Same slice: entries 03:00–04:59 NY, 1h sideways. EURGBP 2023 and 2024.

## Test (fixed now)
"Works" if pooled net > 0 AND positive in both years; "strong" if the pooled per-trade 95% CI also
excludes 0. Otherwise "fails". Caveat stated now: EURGBP 2023/2024 were used in 038 for this slice,
so a pass here still needs another pair before it means anything.

## Results
Run outputs are in research/runs/039_idea1_lon_ny_wide_stop/main_EURGBP_<year>/ (named after the
strategy file). Audits passed (1,150 / 1,124 trades, 0 failures). Chart: [eurgbp_wide_stop.png](eurgbp_wide_stop.png).

| EURGBP slice (03:00–04:59 NY, sideways) | trades | net | per trade | 95% CI | win | gross | median stop / target |
|---|---|---|---|---|---|---|---|
| 1.5× ATR stop (038), 2023 | 217 | −103.0 | −0.47 | [−1.37, +0.45] | 35.9% | +97.3 | 4.9 / 7.4 |
| 1.5× ATR stop (038), 2024 | 219 | −88.2 | −0.40 | [−1.02, +0.24] | 34.2% | +81.1 | 3.4 / 5.1 |
| **3× ATR stop, 2023** | 178 | **−142.3** | −0.80 | [−2.20, +0.63] | 53.4% | +17.2 | 9.7 / 7.3 |
| **3× ATR stop, 2024** | 173 | **−61.2** | −0.35 | [−1.40, +0.66] | 53.8% | +78.6 | 6.9 / 5.2 |
| **3× ATR stop, both** | 351 | **−203.5** | −0.58 | [−1.45, +0.30] | 53.6% | +95.7 | 8.4 / 6.4 |

## Decision
**Fails** (negative in both years; −203.5 vs −191.2 with the 1.5× stop). The wider stop lifted the win
rate (35% → 54%) as expected, but losses got bigger and the before-costs result shrank (+178 → +96),
so costs still win. Because the target (the 5m MA) didn't grow, the trade now risks more than it
can make (8.4 vs 6.4 pips). As with the stop tests on EURUSD (022–024), changing the stop
reshapes the trade without adding an edge. Making the London-open fade pay on EURGBP would need
cheaper execution (e.g. limit entries) or a stronger entry, not a different stop.
