# 039 — London-open sideways fade on EURGBP with a 3× ATR stop (2023 + 2024)

**Date:** 2026-10-06
**File:** research/strategies/039_idea1_lon_ny_wide_stop.py
**Status:** exploring

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
_(filled after the run)_

## Decision
_(filled after the run)_
