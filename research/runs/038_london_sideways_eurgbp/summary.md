# 038 — Test on EURGBP: London-open sideways fade (Idea 1, 034 rules), 2023 + 2024

**Date:** 2026-10-06
**Files:** research/strategies/034_idea1_lon_ny.py (unchanged); results in research/runs/034_idea1_lon_ny/main_EURGBP_<year>/
**Status:** exploring

## Hypothesis (from 034/035, registered before running on EURGBP)
On EURUSD, Idea 1 fades entered in the first two hours after the London open (03:00–04:59 New
York) with the 1h **sideways** made +320.5 (2023, discovery) and +140.0 (2024, test). EURGBP is two
European currencies, so the London open is central to it, which makes it a fair second market.
(The user noted the 08:00–10:00 NY pattern should be tested on USD pairs instead.)

## Test (fixed now)
- Run the 034 strategy **unchanged** on **EURGBP 2023 and 2024** (never run with this window).
- Same slice: entry hour (New York) ∈ {03, 04} and 1h context = sideways.
- "Replicates" if pooled net > 0 AND the per-trade 95% CI excludes 0. "Direction holds" if net > 0 in
  both years. "Fails" otherwise. Gross (before costs) is reported, since EURGBP costs are high (027, 037).

## Results
_(filled after the run)_

## Decision
_(filled after the run)_
