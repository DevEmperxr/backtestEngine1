# 028 — Idea 2 (025, unchanged) on the second practice year, 2024

**Date:** 2026-10-06
**File:** research/strategies/025_turn_confirm_continuation.py; results in research/runs/025_turn_confirm_continuation/{a,b,c}_2024/
**Status:** done: direction repeats, still not significant

## Result (EURUSD; audits passed, 0 structure failures in 2024)

| target | context | 2023 | 2024 | both years: n | net | exp/trade | 95% CI | TP-first vs null |
|---|---|---|---|---|---|---|---|---|
| A 1h SMA20 | trend_with | +51.7 (49) | −1.2 (55) | 104 | +50.6 | +0.49 | [−1.69, +2.79] | 40.7% vs 44.6% |
| A | sideways | −112.2 | −105.1 | 188 | −217.3 | −1.16 | [−2.44, +0.12] | |
| **B 2R** | **trend_with** | **+23.1 (46)** | **+49.8 (53)** | 99 | **+72.9** | +0.74 | [−1.90, +3.43] | 37.7% vs 32.3% |
| B | sideways | −584.3 | −313.8 | 452 | **−898.1** | −1.99 | **[−3.25, −0.68]** | 21.9% vs 32.3% |
| **C 1h swing** | **trend_with** | **+25.8 (51)** | **+62.5 (58)** | 109 | **+88.3** | +0.81 | [−1.76, +3.57] | 32.8% vs 34.2% |
| C | sideways | −231.9 | −84.5 | 355 | −316.4 | −0.89 | [−2.11, +0.36] | |

## Interpretation
Unlike Idea 1 (026), **Idea 2's pattern repeats in the second practice year**. Targets B and C
are positive with the trend in **both** 2023 and 2024, and sideways is negative in both years for
all three targets (B clearly: CI excludes 0). It is still small (≈100 with-trend trades over two
years, CIs ≈ ±2.6 pips/trade), so it is not established. But it is the first idea in this
programme that held its direction across both practice years.

Target A (the 1h MA) does worst: far away, often already passed, and 2024 is flat. B (2× risk)
is the only one whose targets are hit more often than chance in the combined years.

## Decision
**Idea 2 stays alive** (B and C), with-trend only. More data is needed within the practice years
rather than new tuning: run it on EURGBP 2023 + 2024 (and other crosses as they arrive), same
rules, to grow the sample without touching the reserved years.
