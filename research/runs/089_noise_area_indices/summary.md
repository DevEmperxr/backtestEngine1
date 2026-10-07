# 089 — Noise-area momentum (079 rules): (1) is NAS100 just "long Nasdaq"? (2) same rules on DAX and Nikkei, 2023 + 2024

**Date:** 2026-10-07 · strategy: research/strategies/089_noise_area_indices.py · analysis: research/regime/noise_089.py
**Status:** pre-registered before running. User: "go" (after: drift check, then DAX and Nikkei).

## (1) NAS100 drift check, from the existing 079 trades (no new data)
For every 079 trade, the **always-long twin**: same entry and exit times, but long. Points = actual for longs; for
shorts −(gross move) − spread. Same stop as R unit.
**Reading:** the noise-area direction adds value if the strategy's R per trade beats the always-long twin by
≥ +0.05R pooled, with the shorts' twin (long during the short trades) negative.

## (2) Same rules on GER40 and JPN225 (rules frozen from 079; only session clock and news change)
| | session (local) | checks | flat | news ±2 min |
|---|---|---|---|---|
| GER40 | 09:00–17:30 Frankfurt | :00/:30 from 09:30 to 17:00 | 17:25 | EUR + USD |
| JPN225 | 09:00–15:00 Tokyo | :00/:30 from 09:30 to 14:30 | 14:55 | JPY + USD |
- Day open = mid at the session open; previous close = previous session's last 1m close; sigma per minute of session
  = 14-session average |price/open − 1| (2023+2024 joined; first 14 sessions of 2023 skipped).
- Upper = max(open, prev close) × (1+sigma); Lower = min(...) × (1−sigma). Long above / short below / flat inside at
  each check; flips reverse. Stop = one noise width; no target. FTMO index costs (GER40 +0.15, JPN225 +2.9 points).
- JPN225: the Tokyo cash close moved to 15:30 on 5 Nov 2024; the rule keeps 15:00 throughout (fixed now).
**Candidate (each index separately):** after costs R per trade > 0 in both years, pooled ≥ +0.05, and the FTMO 1-step
scorecard beats its zero-edge twin.

## Results
_(filled after the run)_
