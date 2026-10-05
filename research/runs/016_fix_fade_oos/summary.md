# 016 — Out-of-sample test of the London-fix fade (007) on 2023 and 2025

**Date:** 2026-10-05
**File:** research/strategies/016_fix_fade_oos.py (A = 007 rules unchanged; B = big-move filter)
**Status:** discarded

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
| | trades | net pips | exp/trade | 95% CI | gross | H1 / H2 |
|---|---|---|---|---|---|---|
| A | 259 | **−423.6** | −1.64 | [−4.21, +0.92] | −352.3 | −282.0 / −141.6 |
| B | 110 | **−127.6** | −1.16 | [−5.01, +2.70] | −100.3 | +38.8 / −166.4 |

Data: 2023 (10.50 M 1s rows, checks PASSED; 10 gaps of 10–17 min, all 17:03–17:25 New
York = daily rollover, outside every test window), 2025 (9.42 M rows, checks PASSED,
0 unexplained gaps). All lookahead/independent audits passed on every run.

## Results — 2025
| | trades | net pips | exp/trade | 95% CI | gross | H1 / H2 |
|---|---|---|---|---|---|---|
| A | 259 | **−10.9** | −0.04 | [−2.81, +2.69] | +89.1 | −387.3 / +376.4 |
| B | 116 | **−276.8** | −2.39 | [−6.83, +1.95] | −231.2 | −345.2 / +68.4 |

## Pooled 2023 + 2025 and 2024 reference
| | n | net | exp | 97.5% CI (registered) | 99% CI (family) | 2023 | 2025 | 2024 ref |
|---|---|---|---|---|---|---|---|---|
| A | 518 | **−434.5** | −0.84 | [−2.99, +1.30] | [−3.34, +1.58] | −423.6 | −10.9 | +39.4 |
| B | 226 | **−404.4** | −1.79 | [−5.11, +1.51] | [−5.69, +2.09] | −127.6 | −276.8 | +71.6 |

## Visual check
Mechanics identical to 007 (A reproduces 007's 2024 trade log exactly); audits
recompute the 15:00→16:00 move and, for B, the past-only 20-day threshold from
1s-rebuilt bars: 0 violations in every year.

## Interpretation
**Not confirmed: both variants lost money in both test years.** The 2024 "big pre-fix move"
split (+217.7) was an artefact of using the full-year median; with a past-only threshold
it shrank to +71.6 on 2024 and turned negative out of sample.

This does not refute Krohn, Mueller & Whelan. Their unconditional effect is ~0.3
pips/day, invisible in two years. But fading the 15:00→16:00 London move at the fix is
**not a tradable rule on this data**. Part of that window is the 10:00 NY US-data
reaction (flagged before the test), which this rule fades indiscriminately.

## Decision
**discard (A and B).**
**Why:** pooled 2023+2025 −434.5 (A) / −404.4 (B); negative in both test years for both
variants; registered criterion (CI excludes 0 and both years positive) failed on every part.
