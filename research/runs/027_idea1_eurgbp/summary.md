# 027 — Idea 1 (023A, unchanged) on a second market: EURGBP 2021–2024

**Date:** 2026-10-06
**File:** research/strategies/023_sweep_fade_rework.py (make_a); results in research/runs/023_sweep_fade_rework/a_EURGBP_<year>/
**Status:** done: does not replicate

## Why
User request. EURGBP has never been looked at in this project. Running Idea 1 with the **exact**
023A rules (including the 0.32 1h-ER trend threshold derived from EURUSD 2023, and the 2·ATR
stretch / 1.5·ATR stop, which scale with each pair's own volatility) is a clean replication on
unseen data. Registered before any EURGBP result was computed. 2025 is excluded (still
downloading).

## Question / criteria (fixed now)
Does Idea 1's with-trend case make money on EURGBP?
- Per year (2021, 2022, 2023, 2024): with-trend trades, net, expectancy, TP-first vs the
  spread-adjusted null; context table (with / against / sideways).
- **Pooled 2021–2024 with-trend:** "replicates" only if the expectancy 95% CI excludes 0 AND at
  least 3 of 4 years are positive. Also reported: whether sideways is worse than with-trend
  (the 2023-EURUSD pattern that 2024-EURUSD did not repeat).
- Audits as 023A (sweep/stretch re-derived on 1s-rebuilt bars; ATR stop checked).
- Caveat: EURGBP spreads relative to its moves may differ from EURUSD; gross vs net is reported.

## Results
Data: EURGBP 1s 2021–2024, all checks PASSED. Unexplained gaps were short rollover-time holes,
except a 1.4 h hole on 2024-12-17 (15:30–16:53 UTC) inside the window, where no trades occurred.
Audits passed every year (605 / 626 / 653 / 660 trades, 0 failures).

| context | 2021 | 2022 | 2023 | 2024 | pooled n | pooled net | exp/trade | 95% CI | gross | TP-first vs null |
|---|---|---|---|---|---|---|---|---|---|---|
| **trend_with** | −67.0 | −446.2 | −141.9 | −55.6 | 514 | **−710.7** | −1.38 | **[−1.96, −0.83]** | −243.8 | 30.0% vs 33.4% |
| trend_against | −44.6 | +40.7 | −57.7 | −2.1 | 251 | −63.8 | −0.25 | [−1.07, +0.61] | +165.0 | 35.9% vs 33.6% |
| sideways | −333.5 | −627.5 | −450.6 | −376.5 | 1,779 | −1,788.1 | −1.01 | [−1.31, −0.70] | −64.9 | 31.2% vs 32.8% |

- Spread paid ≈ 0.7–1.1 pips/trade vs median stops of 3.6–7.6 pips (≈ 15–20% of the risk),
  against ≈ 0.3 on EURUSD (~4%).

## Interpretation
**Does not replicate; with-trend loses every year**, and its pooled CI is entirely negative.
Two reasons:
1. **No edge before costs** in the with-trend case (gross −243.8; TP-first below chance).
   The reversion that 023A showed on EURUSD 2023 isn't there.
2. **Costs are much heavier on EURGBP.** The pair moves about half as much as EURUSD, but its spread
   isn't half, so it takes a much bigger bite out of each trade.

With EURUSD 2024 (026) this makes three of four checks negative for Idea 1 beyond its
discovery year. The "trend context" effect did not hold across years or markets.

## Decision
**Idea 1 does not replicate on EURGBP; with-trend pooled −710.7 pips, CI [−1.96, −0.83].** Together
with 026, Idea 1 (023A) has no edge outside EURUSD 2023. Recommend shelving Idea 1 rather than
tuning it further.
