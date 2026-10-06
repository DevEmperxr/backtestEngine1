# 040 — EURUSD playbook: three leads combined (2023 + 2024, in-sample)

**Date:** 2026-10-06 · chart: [playbook_2023_2024.png](playbook_2023_2024.png) · trades: playbook_trades_2023_2024.parquet
**Status:** done (descriptive portfolio view of in-sample pieces; NOT a test)

## What
The user asked to run the three EURUSD leads together, on one account, each managed by its own rules
(existing audited trade logs, no new backtests):
1. **Idea 2, 1h trending only, target 2R** (025 B). B rather than C because it was the only target
   hit above chance across both years.
2. **London-open sideways fade** (034 strategy; entries 03:00–04:59 NY; 1h sideways).
3. **Fix fade** (018, original mirrored exits).

**Caveat:** each piece was chosen because it looked good on these years (2024 is 018's discovery
year; the London-open slice was found on 2023). The combined result is in-sample by construction. It
shows how the pieces fit together, not whether they work.

## Results
| piece | trades | net | per trade | 95% CI | 2023 | 2024 | max DD | Sharpe |
|---|---|---|---|---|---|---|---|---|
| Idea 2 (trend, 2R) | 99 | +72.9 | +0.74 | [−1.90, +3.43] | +23.1 | +49.8 | −0.95% | 0.89 |
| London-open sideways fade | 432 | +460.4 | +1.07 | [+0.23, +1.90] | +320.5 | +140.0 | −1.45% | 2.34 |
| Fix fade (018) | 215 | +426.1 | +1.98 | [+0.12, +3.93] | +95.9 | +330.2 | −1.89% | 2.18 |
| **combined** | **746** | **+959.4** | +1.29 | [+0.47, +2.09] | **+439.4** | **+520.0** | −1.78% | 2.53 |

- Monthly P&L correlations between pieces: −0.08, +0.01, −0.24, so they make and lose money in
  different months.
- Months positive: combined 18/24 (pieces 14, 16, 16). Max positions open at once: 2.

## Interpretation
The pieces fit together well: almost no correlation, so the combined curve is steadier than any
single piece (Sharpe 2.53, positive in both years and in 18 of 24 months). But every number here is
in-sample. The real question is how the combination does on data none of its pieces was chosen
on.

## Next (if the user wants it)
A pre-registered final check on the reserved EURUSD years (2021, 2022, 2025), only with the user's
go-ahead (standing rule). Note: the fix fade (018) already saw those years in runs 018/019 (positive
in each); Idea 2 and the London-open fade have never run on them.
