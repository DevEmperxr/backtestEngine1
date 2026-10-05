# 017 — Engulfing mean reversion, entries only after the London fix (16:00 London → 16:00 NY), out of sample

**Date:** 2026-10-05
**File:** research/strategies/017_bb15_engulf5_postfix.py (make_a = setup-extreme stop, make_b = engulfing-candle stop)
**Status:** exploring

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
_(filled after the run)_

## Results — 2025
_(filled after the run)_

## Pooled 2023 + 2025 and 2024 reference
_(filled after the run)_

## Interpretation
_(filled after the run)_

## Decision
_(filled after the run)_
