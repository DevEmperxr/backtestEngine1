# 065 — AUDUSD: fade a sweep of the Tokyo first-hour range during the second hour of Asia, 2023 + 2024

**Date:** 2026-10-07 · files: research/strategies/065_tokyo_sweep.py, research/regime/tokyo_sweep_065.py
**Status:** done. **FAIL** (AUDUSD loses at every layer)

## 0. Who loses, and why
At 09:55 Tokyo the Tokyo fix concentrates Japanese corporate dollar buying (a forced, price-insensitive flow;
see Ito & Yamada on the Tokyo fixing). The first Tokyo hour's range is shaped around it, and stops gather just
outside that range. In the second hour, traders who chase a break of the first hour's range, and those stopped
out at the extreme, are trapped when the break fails.

## 1–2. Context / bias
None (both directions). Not added in this run.

## 3. POI (fixed now)
First-hour range = high/low (mid) of 1m bars opening 09:00–09:59 Tokyo (00:00–00:59 UTC; Tokyo has no DST).
POI = price trades beyond that high or low during **10:00–11:00 Tokyo** (bars closing in (10:00, 11:00]), weekdays.

## 4. Confirmation (fixed now)
**Sweep:** a 1m bar whose mid high goes above the range high and whose mid close is back below it (sell); mirror
for the low (buy). Only the first sweep of the day (either side).

## 5. Execution (fixed now)
Entry at the next 1m open (bid/ask fills, Dukascopy spread). Stop = sweep bar's extreme + **0.5 × first-hour range**
(room beyond the wick; tight sweep stops failed in 048). Target = **first-hour range midpoint** (skip if the
signal close is already past the midpoint). Flat at **12:00 Tokyo**. One trade per day. Standing ±1 h red-news
blackout (AUD + USD; e.g. Australian data at 11:30 Sydney falls in or next to this window).

## Layer-by-layer measurement
- L3 POI only: first touch beyond the range in hour 2 -> race "back to the midpoint" vs "the same distance further";
  chance 50%.
- L4 + sweep: the same race from the sweep bar's close.
- L5 the full trade in the engine (R = pips / stop).
AUDUSD primary; EURUSD and GBPUSD reported as checks.

## Pass bar (stricter, lesson from 059)
AUDUSD strategy: total R > 0 in **both** 2023 and 2024, pooled **R per trade ≥ +0.10**, and the pooled 95% bootstrap
CI of R per trade **above 0**.

## Results
Engine runs: research/runs/065_tokyo_sweep/ (lookahead audit ok, all pairs/years). Analysis:
research/regime/tokyo_sweep_065.py -> results.json; charts equity_monthly_R_<PAIR>.png.

Races: "back to the first-hour midpoint" vs "the same distance further", chance 50%.

| | L3 POI only 2023 / 2024 | L4 + sweep 2023 / 2024 | L5 trade: R 2023 / 2024 | R per trade [CI], both years | net / gross pips |
|---|---|---|---|---|---|
| **AUDUSD** | 45.8% / 49.5% | 44.7% / 49.5% | −49.9 / −34.4 | **−0.22 [−0.30, −0.14]** | −638 / −228 |
| EURUSD | 47.8% / 54.2% | 46.8% / 51.3% | −15.4 / −4.9 | −0.05 [−0.13, +0.03] | −48 / +73 |
| GBPUSD | 53.1% / 56.9% | 53.4% / 56.4% | −27.0 / −18.2 | −0.11 [−0.19, −0.03] | −278 / +132 |

AUDUSD trades: 385, win 45.5%, median stop 6.6 / target 4.3 pips, spread 1.07 pips per trade (~0.16R).

**Verdict: FAIL.** On AUDUSD the first-hour range break in the second Tokyo hour **does not reverse**: price
goes back to the midpoint less often than chance at the POI layer (46–50%), the sweep confirmation doesn't change
that (45–50%), and the trade loses even before costs (gross −228 pips); after AUDUSD's ~1 pip spread on ~4-pip
targets it loses clearly (−84R). EURUSD is flat before costs. GBPUSD leaned toward reversal (53–57%, gross +132
pips) but its ~1 pip spread turns it negative (−45R); a hint only, not the primary.

