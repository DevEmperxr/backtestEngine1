# 026 — Idea 1 (023A, unchanged) on the second practice year, 2024

**Date:** 2026-10-06
**File:** research/strategies/023_sweep_fade_rework.py (make_a), results in research/runs/023_sweep_fade_rework/a_2024/
**Status:** done: the 2023 pattern does not repeat

## Why
Under the new data split (research/DATA_SPLIT.md), an improvement must help in both practice
years. 023A had only been run on 2023, so it first needed a baseline on 2024. Rules
unchanged; 2024 had not been used for Idea 1 before.

## Result (2024; audit passed, 702 trades re-derived, 0 failures)

| context | trades | net | exp/trade | 95% CI | win | TP-first vs null | 2023 (for comparison) |
|---|---|---|---|---|---|---|---|
| trend_with | 131 | **−18.9** | −0.14 | [−1.55, +1.31] | 45.8% | **37.4% vs 37.3%** | +56.7 (142), TP-first 43.5% vs 37.2% |
| trend_against | 59 | −84.8 | −1.44 | [−3.25, +0.51] | 37.3% | 32.7% vs 41.6% | −57.1 (74) |
| sideways | 512 | **+18.4** | +0.04 | [−0.66, +0.73] | 42.2% | 37.3% vs 38.5% | −509.8 (481) |
| all | 702 | −85.3 | −0.12 | [−0.71, +0.48] | 42.5% | 36.9% vs 38.5% | −510.2 (697) |

## Interpretation
The two things 2023 suggested both fail to repeat in 2024:
- With-trend fades were not profitable (−18.9), and the targets were hit exactly as often as
  chance.
- Sideways fades did **not** lose (+18.4), so "avoid sideways" was not a stable filter either.

Across the two practice years, Idea 1 with-trend = +37.8 pips on 273 trades (≈ +0.14/trade),
essentially zero; the 2023 context split looks like one year's noise. Only trend_against is
negative in both years, but on small samples (74 and 59).

## Decision
Idea 1 (023A) shows **no edge across the two practice years**. Improvements (stronger trends,
news filter, ...) would now be tuning a near-zero baseline. Any one of them must clear
both practice years by a clear margin before a test-year check. Recorded so later
sessions don't rely on the 2023-only "trend context" conclusion.
