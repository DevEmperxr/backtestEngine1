# 038 — Test on EURGBP: London-open sideways fade (Idea 1, 034 rules), 2023 + 2024

**Date:** 2026-10-06
**Files:** research/strategies/034_idea1_lon_ny.py (unchanged); results in research/runs/034_idea1_lon_ny/main_EURGBP_<year>/
**Status:** fails after costs; positive before costs in both years

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
Audits passed (2023: 1,716 trades, 2024: 1,694; 0 failures). Chart: [eurgbp_london_sideways.png](eurgbp_london_sideways.png).

| EURGBP, entries 03:00–04:59 NY, 1h sideways | trades | net | per trade | 95% CI | win | gross (before costs) | spread/trade |
|---|---|---|---|---|---|---|---|
| 2023 | 217 | −103.0 | −0.47 | [−1.37, +0.45] | 35.9% | **+97.3** | 0.92 |
| 2024 | 219 | −88.2 | −0.40 | [−1.02, +0.24] | 34.2% | **+81.1** | 0.77 |
| both | 436 | **−191.2** | −0.44 | [−0.99, +0.12] | 35.1% | **+178.3** | 0.85 |

By hour: 2023 03 NY −5.0 (118), 04 NY −98.0 (99); 2024 03 NY −123.2 (124), 04 NY +34.9 (95).

## Decision
**Fails by the registered rule** (net −191, negative both years). Like 037, it is **positive before
costs in both years** (+0.41 pips/trade) but EURGBP's spread (~0.85 pips per trade against
small stops) turns it negative. EURGBP is too expensive for these small-stop trades. The
hour pattern also differs from EURUSD (03:00 NY was the strong hour on EURUSD; on EURGBP it lost in
both years). Not confirmed. The next fair test needs a pair with EURUSD-like costs, e.g. the USD
majors (GBPUSD, USDCHF, USDJPY), which are not in the current minor-cross download.
