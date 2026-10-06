# 037 — Test on EURGBP: Idea 1, 1h trending, entries 08:00–10:00 New York only

**Date:** 2026-10-06
**Data:** existing run-027 trade logs (023A rules on EURGBP), 2023 and 2024 only (user's rule)
**Status:** fails (net ≤ 0); positive before costs

## Hypothesis (from 033, registered before looking at EURGBP by hour)
On EURUSD 2023 + 2024, Idea 1 (023A) trades with the 1h trending, entered **08:00–09:59 New York**,
made +161.6 pips on 131 trades, positive in both years (found by slicing by hour).

## Test (fixed now)
- Take the 027 EURGBP trade logs for **2023 and 2024** (023A rules, unchanged; never examined by
  hour). Select: context = trending with the trend AND entry hour (New York) ∈ {08, 09}.
- "Replicates" if pooled net > 0 AND the per-trade 95% CI excludes 0. "Direction holds" if net > 0 in
  both years. "Fails" otherwise.
- Caveat stated now: Idea 1 lost heavily on EURGBP overall (027: spread ≈ 15–20% of risk), so this is
  a hard test.

## Results
Chart: [eurgbp_us_window.png](eurgbp_us_window.png).

| EURGBP, trending, entries 08:00–09:59 NY | trades | net | per trade | 95% CI | win | gross (before costs) |
|---|---|---|---|---|---|---|
| 2023 | 58 | −8.0 | −0.14 | [−1.86, +1.72] | 39.7% | **+44.8** |
| 2024 | 59 | −9.1 | −0.15 | [−1.37, +1.12] | 39.0% | **+40.8** |
| both | 117 | **−17.1** | −0.15 | [−1.21, +0.97] | 39.3% | **+85.7** |

EURGBP trending trades by hour (both years): 07 +2.5 (53), 08 −57.0 (74), 09 +39.9 (43), 10 −176.6 (72).

## Decision
**Fails by the registered rule** (net −17.1, slightly negative in both years). Before costs, the
slice was positive in both years (+0.73 pips/trade), but EURGBP's spread (about 0.8–1.1 pips per trade,
against stops of 4–7 pips) wipes it out. The hour pattern itself also doesn't repeat cleanly
(08:00 negative, 09:00 positive on EURGBP; both positive on EURUSD). Verdict: the 08:00–10:00 NY
pattern is not confirmed. If it is real, it is too small to survive EURGBP costs. A fairer
second check would be a pair with EURUSD-like costs.
