# 066 — Re-check of the most promising ideas under FTMO's real rules, EURUSD + GBPUSD 2023 + 2024

**Date:** 2026-10-07 · strategies: research/strategies/066_ftmo_reruns.py · analysis: research/regime/ftmo_reruns_066.py
**Status:** pre-registered. **In-sample re-check** (these years were used to build/judge the ideas), not a fresh test.

## What changed vs the original runs (nothing else)
- News: FTMO's ±2 min window instead of ±60 min (user decision, 2026-10-07).
- Prop-firm mode (`run_experiment --prop`): $5/lot round-trip commission (0.5 pip), flat by 16:55 New York, no
  entries 16:55–17:00 (no overnight, weekend or rollover holding; all four ideas already close earlier).

## Ideas
| spec | idea | original result (±60 min, no commission) |
|---|---|---|
| 066:london_fade | 046 London-open sideways fade | EURUSD +455 pips 2023+24 |
| 066:london_fade_4r | 049 sweep+3 stop, BE at 2R, target 4R | EURUSD 2023 +233 |
| 066:home_hours | 058 home-hours weakness | EURUSD −144 (no-news-rule reference +1,040) |
| 066:orb_nr7 | 059 London-open breakout after NR7 | EUR+GBP +0.04R/trade |

## Reported
Per idea and pair: trades, net pips (after spread AND commission), R per trade with bootstrap CI, each year.
FTMO 2-step challenge simulation (lib.prop.simulate_challenge; $10k; +10% then +5%; −5% daily; −10% max; ≥ 4
trading days; days drawn from 2023–24) at risk 0.25 / 0.5 / 1 / 2% per trade, next to the **zero-edge twin**
(same trades with the average R removed).

## How to read it
An idea is a **candidate** only if R per trade > 0 in both years after costs AND its pass probability beats its
zero-edge twin at the same risk. Because the data is in-sample, a candidate still needs a clean check on unused
data (EURUSD/GBPUSD 2021–22 for the ideas that never saw them; EURUSD 2025 Jan–Apr).

## Results
_(filled after the run)_
