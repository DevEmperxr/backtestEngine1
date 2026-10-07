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
_(filled after the run)_
