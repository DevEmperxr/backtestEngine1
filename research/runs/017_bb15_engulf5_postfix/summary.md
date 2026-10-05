# 017 — Engulfing mean reversion, entries only after the London fix (16:00 London → 16:00 NY), out of sample

**Date:** 2026-10-05
**File:** research/strategies/017_bb15_engulf5_postfix.py (make_a = setup-extreme stop, make_b = engulfing-candle stop)
**Status:** discarded

## Hypothesis
*(registered before the 2023/2025 files were read: the downloads were still running,
~6 weeks of each year partially written to disk, unopened)*

On 2024, the 15m-Bollinger + 5m outside-engulfing fade (014/015) lost money overall,
but entries **after 16:00 London** made +46.2 (n=193) and +94.3 (n=236), while earlier
entries lost. That matches the post-fix reversal documented by Krohn, Mueller & Whelan
(JF 2024) and Evans (JBF 2018). If the reversal is real, restricting this mean-reversion
setup to the post-fix period should be profitable **in years it was not discovered in**.

2024 is the discovery sample (post hoc split, many looks). It is reported only as reference.

## Rules (fixed now; identical to 014/015 except the window)
- 5m bars from 1s, mid; 15m Bollinger(20, 2) from closed 15m bars only.
- setup: closed 15m close outside the band; valid 120 min; cancelled if price reached the
  current 15m middle band since the setup.
- confirmation: 5m outside-engulfing (green & close > previous high / red & close < previous low).
- **window: entry time in [16:00 Europe/London, 16:00 America/New_York)**, Mon–Fri;
  force-flat 16:00 New York.
- TP = 0.8 × |signal close − 15m middle band|.
- **A:** SL = setup extreme ± 2 pips (as 014). **B:** SL = engulfing candle ± 2 pips (as 015).

## Test design (fixed now)
- Test years **2023 and 2025**, run separately with the same pipeline; 2024 = reference.
- **Per-variant criterion:** pooled 2023+2025 expectancy CI excludes 0 **and** net positive
  in both 2023 and 2025.
- **Family of fix tests: 016A, 016B, 017A, 017B, 018 (5 tests).** Family-level
  confirmation uses **99% CIs** (Bonferroni 0.05/5). A single pass at a looser level is
  reported as such, not as confirmation.
- Power: ~200 trades/year → ~400 pooled, SE ≈ 0.5–0.6 pips/trade. 2024's post-fix effect
  (+0.24 / +0.40 per trade) is far below what can be confirmed. Expected outcome even if
  real: "not confirmed". Direction and consistency across years are the informative parts.
- Audits: setup + engulfing re-derived from 1s-rebuilt bars; force-flat at 16:00 NY.

## Results — 2023
| | trades | net pips | exp/trade | 95% CI | gross | H1 / H2 |
|---|---|---|---|---|---|---|
| A | 255 | **−47.1** | −0.18 | [−1.57, +1.23] | +23.2 | −6.0 / −41.1 |
| B | 303 | **−51.6** | −0.17 | [−1.20, +0.89] | +35.6 | +9.1 / −60.7 |

Data: 2023 (10.50 M 1s rows, checks PASSED; 10 gaps of 10–17 min, all 17:03–17:25 New
York = daily rollover, outside every test window), 2025 (9.42 M rows, checks PASSED,
0 unexplained gaps). All lookahead/independent audits passed on every run.

## Results — 2025
| | trades | net pips | exp/trade | 95% CI | gross | H1 / H2 |
|---|---|---|---|---|---|---|
| A | 310 | **−99.3** | −0.32 | [−1.77, +1.15] | +28.4 | −162.3 / +63.0 |
| B | 384 | **−218.3** | −0.57 | [−1.54, +0.45] | −53.0 | −177.7 / −40.5 |

## Pooled 2023 + 2025 and 2024 reference
| | n | net | exp | 95% CI | 99% CI (family) | 2023 | 2025 | 2024 ref |
|---|---|---|---|---|---|---|---|---|
| A | 565 | **−146.5** | −0.26 | [−1.25, +0.76] | [−1.56, +1.08] | −47.1 | −99.3 | +74.5 |
| B | 687 | **−269.8** | −0.39 | [−1.11, +0.34] | [−1.31, +0.58] | −51.6 | −218.3 | +34.4 |

## Interpretation
**Not confirmed: both variants lost in both test years.** The post-fix advantage seen in
014/015 on 2024 was noise from slicing one year. Gross P&L is near zero (+23 to +36 in 2023,
−53 to +28 in 2025): a random-like entry minus spread, like every other mean-reversion
rule in this project.

## Decision
**discard (A and B).**
**Why:** pooled −146.5 (A) / −269.8 (B); negative in both 2023 and 2025; criterion failed.
