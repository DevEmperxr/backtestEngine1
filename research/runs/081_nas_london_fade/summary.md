# 081 — London fade on NAS100, 2023 + 2024, FTMO rules

**Date:** 2026-10-07 · strategy: research/strategies/081_nas_london_fade.py · analysis: research/regime/nas_london_fade_081.py
**Status:** pre-registered. User: "can you now run the london fade strat on Nasdaq".

## Rules: unchanged from 066:london_fade (046 rules, FTMO ±2 min news)
- Entries only 03:00–04:59 New York (London open hours) while the 1h context is **sideways** (ER20 < 0.32).
- Short when a 1m bar pokes above the 5m SMA20 + 2×ATR14 band AND sweeps the last confirmed 1m swing high, then closes
  back below it (mirror for longs).
- Stop 1.5 × 5m ATR14; target the 5m SMA20; flat at 16:00 New York. One position at a time.
- Only changes: points instead of EURUSD pips (wrapper), news currency USD only, FTMO index costs (`--prop`:
  no commission, +0.2-point spread top-up, flat by 16:55 NY).

## Who loses
Early-Europe breakout traders whose stops sit above/below the overnight swing; the sweep runs them, and price returns
to the mean in a sideways hour. On NAS100 these hours are thin pre-market futures trading, with a wider spread
(~3.5 points vs ~1.5 in the cash session), so costs may matter more than on EURUSD.

## Bar (same as 079)
**Candidate** if, after all FTMO costs: R per trade > 0 in **both** years, pooled R per trade ≥ +0.05, and
`ftmo_1step_scorecard` beats its zero-edge twin.

## Results
2026-10-07, NAS100 2023 + 2024, `--prop`. Lookahead audit clean both years (after fixing the audit's ATR-stop check,
which was recomputing stops in EURUSD pips; it now uses the strategy's own pip; EURUSD 066 still audits clean).

| | trades | R/trade after costs | 95% CI | win % |
|---|---|---|---|---|
| 2023 | 250 | **−0.254** | −0.40 … −0.11 | 31 |
| 2024 | 189 | **−0.221** | −0.39 … −0.04 | 31 |
| both | 439 | **−0.240** | −0.35 … −0.13 | 31 |

- Before costs only +0.045R per trade. **Costs eat 0.285R per trade**: the median stop is 13 points, but the
  03:00–05:00 NY spread is ~3.6 points (27% of the stop). On EURUSD the same rules paid ~0.75 pip on a larger stop.
- Long and short both negative. FTMO 1-step: pass 2%, EV −$85 per attempt vs zero-edge twin 23% / +$47.

**Verdict: NOT a candidate.** The EURUSD edge does not carry over; the pre-market hours are too thin and expensive
on NAS100, and even before costs the fade is barely positive.


---

## Addendum (pre-registered 2026-10-07, before running): same rules on GER40 (DAX), **2023 only** (user request)
- Identical code (`081 --pair GER40 --prop`): 03:00–04:59 New York entries = **09:00–10:59 Frankfurt, the DAX cash
  open**, which suits a London-open fade much better than NAS pre-market. News: EUR red news ±2 min (pair_currencies).
  FTMO index costs: no commission, +0.15-point spread top-up.
- Who loses: the same early-breakout stop-runs, here at the real DAX opening auction / first hour.
- Bar for "worth checking 2024": R per trade after costs ≥ +0.05 in 2023 and the FTMO 1-step scorecard beats its
  zero-edge twin. 2024 then decides.

### GER40 2023 result
_(filled after the run)_
