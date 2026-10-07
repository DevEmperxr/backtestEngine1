# 082 — DAX-open sweep continuation (mirror of the 081 fade), GER40, FTMO rules

**Date:** 2026-10-07 · strategy: research/strategies/082_dax_open_sweep_continuation.py
**Status:** pre-registered BEFORE running. User: "can't we fix this and test it on 2024?" after 081 showed the fade
loses on GER40 2023 even before costs (−0.12R gross).

## Honesty note
The idea comes FROM GER40 2023 (the fade lost there). So **2023 is in-sample** for this mirror: it is expected to be
positive before costs by construction and proves nothing. **GER40 2024 is the test.**

## Who loses
Traders who fade the first stretch at the DAX cash open (exactly the 081 rules): the sweep of a recent high/low at
the open marks real order flow, and the faders' stops above/below feed the continuation.

## Rules (fixed)
- Same signal bar as 081 (09:00–10:59 Frankfurt, 1h sideways, 1m bar beyond 5m SMA20 ± 2×ATR14 sweeping the last
  confirmed 1m swing and closing back inside it), but trade WITH the sweep: fade-short signal -> long, fade-long -> short.
- Target = 1.5 × 5m ATR14 (the fade's stop); stop = distance back to the 5m SMA20 (the fade's target).
- Skip signals whose stop is < 5 points (cost guard). Flat 16:00 New York. EUR red news ±2 min; FTMO index costs.

## Bar (decided on 2024 only)
**Candidate** if GER40 2024, after all FTMO costs: R per trade ≥ +0.05, and the FTMO 1-step scorecard (2024 trades)
beats its zero-edge twin. 2023 is reported only as an in-sample sanity check.

## Results
**2023 (in-sample, user asked to see it before 2024):** 231 trades, audit ok. −0.016R/trade after costs (CI −0.13 …
+0.09), +0.04R before costs, win 58%; median stop 32 pts vs target 21 pts, so the fade's −0.12R does not mirror into
+0.12R. Break-even, below the +0.05 bar even in-sample.

**2024 note:** 2024 was run in the same command before the user's "before running on 2024" message arrived; only its
headline total (+420 pts, 212 trades) was seen; not scored yet, pending the user's decision.
