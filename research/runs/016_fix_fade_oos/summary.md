# 016 — Out-of-sample test of the London-fix fade (007) on 2023 and 2025

**Date:** 2026-10-05
**File:** research/strategies/016_fix_fade_oos.py (A = 007 rules unchanged; B = big-move filter)
**Status:** exploring

## Hypothesis
*(written and committed while the 2023 and 2025 data were still downloading: no
2023/2025 price data existed on disk when this was registered)*

Krohn, Mueller & Whelan (JF 2024): the USD rises into the 16:00 London (WM/R) fix and
reverses afterwards, and the last-hour move before a fix predicts the next window's
return with a negative sign. On 2024 (in-sample, and contaminated by 006), 007 made
+39.4 pips with a CI straddling zero. The pre-registered split was suggestive: big
pre-fix moves +217.7, small −178.3. Runs 014/015 (entries after 16:00 London) were
positive too. All of that is one year, looked at several times. **016 tests it on two
years nobody has looked at.**

## Variants (both fixed now; two tests → each judged at 97.5%, Bonferroni)
- **A — replication of 007 exactly:** at the 1m bar closing 16:00 Europe/London (Mon–Fri),
  r = mid close 16:00 − mid close 15:00 London; r < 0 → long, r > 0 → short; entry next 1m
  open; force-flat 16:00 New York; SL/TP 50/50 (disaster bracket).
- **B — big-move filter (from 007's 2024 split):** as A, but trade only when
  |r| > the **median of |r| over the previous 20 fix days** (strictly past days: today's
  |r| is excluded; no trade until 20 past fix days exist in the loaded data). 20 days,
  not 60, so less of each test year is lost to warmup. The threshold uses past data only.

## Test design (fixed now)
- **Test years: 2023 and 2025**, each run separately on its own file through the same
  engine and evaluation. 2024 results are shown only as an in-sample reference.
- **Confirmation criterion, per variant:** pooled 2023+2025 trades with a bootstrap 97.5%
  CI for expectancy that excludes 0, **AND** net pips positive in **both** 2023 and 2025
  separately. Anything less = "not confirmed".
- **Power, stated up front:** fix→16:00 NY moves have SD ≈ 18 pips (2024). Pooled A gives
  ≈ 520 trades → SE ≈ 0.8 pips/trade, so only an effect ≥ ~1.8 pips/trade can reach
  significance. B has ≈ 240 trades → SE ≈ 1.2, needing ≥ ~2.7 pips/trade. 2024's
  big-move half averaged +1.67 pips/trade. **Even if the effect is real at that size,
  two years will most likely *not* confirm it.** A "not confirmed" result is the
  expected outcome under both the null and a modest real effect; only the direction
  and consistency across years will be informative.
- Lookahead audit as in 007 (entry at the fix, direction = −sign(r) recomputed from
  1s-rebuilt bars), plus for B: the threshold at each trade is recomputed from strictly
  earlier fix days.
- Costs: the spread in each year's data (no other costs).

## Results — 2023
_(filled after the run)_

## Results — 2025
_(filled after the run)_

## Pooled 2023 + 2025 and 2024 reference
_(filled after the run)_

## Visual check
_(filled after the run)_

## Interpretation
_(filled after the run)_

## Decision
_(filled after the run)_
