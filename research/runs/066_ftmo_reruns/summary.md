# 066 — Re-check of the most promising ideas under FTMO's real rules, EURUSD + GBPUSD 2023 + 2024

**Date:** 2026-10-07 · strategies: research/strategies/066_ftmo_reruns.py · analysis: research/regime/ftmo_reruns_066.py
**Status:** done. Only the London fade on EURUSD survives FTMO costs, in-sample. **In-sample re-check** (these years were used to build/judge the ideas), not a fresh test.

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
All 16 runs: lookahead audit ok. Analysis: research/regime/ftmo_reruns_066.py -> results.json; charts
equity_R_<idea>_EURUSD.png. Costs per trade = spread + 0.5 pip commission.

| idea, pair | trades | net pips (after all costs) | R / trade 2023 · 2024 | R / trade both [CI] | costs/trade |
|---|---|---|---|---|---|
| **London fade, EURUSD** | 424 | **+215.6** | **+0.133 · +0.063** | **+0.096 [−0.02, +0.21]** | 0.75 pips |
| London fade, GBPUSD | 442 | −349.0 | −0.080 · −0.134 | −0.107 | 1.30 |
| London fade 4R, EURUSD | 432 | +48.3 | +0.145 · −0.109 | +0.018 [−0.15, +0.20] | 0.76 |
| London fade 4R, GBPUSD | 517 | −523.3 | −0.211 · −0.168 | −0.190 | 1.31 |
| Home hours, EURUSD | 1547 | −353.6 | +0.001 · −0.013 | −0.006 [−0.02, +0.01] | 0.76 |
| Home hours, GBPUSD | 1528 | +160.3 | +0.016 · −0.023 | −0.003 | 1.38 |
| ORB NR7, EURUSD | 76 | +7.4 | +0.023 · −0.209 | −0.099 | 0.75 |
| ORB NR7, GBPUSD | 78 | +27.2 | −0.089 · +0.158 | +0.038 | 1.32 |

**FTMO 2-step challenge simulation** ($10k; pass = both phases), London fade EURUSD vs its zero-edge twin:

| risk per trade | pass | fail | median trading days to pass | zero-edge twin: pass / fail |
|---|---|---|---|---|
| 0.25% | 12.4% | 0.2% | 339 (most still running after 2 years) | 0.6% / 2.4% |
| 0.5% | 56.7% | 7.1% | 222 | 14.1% / 32.0% |
| **1%** | **65.3%** | 32.7% | **96** | 31.9% / 64.8% |
| 2% | 45.3% | 54.7% | 34 | 27.9% / 72.1% |

Zero-edge twins of every idea pass ~25–32% at 1–2% risk (the convex payoff of the challenge).

**Verdict (pre-registered reading):** the only candidate is the **London fade on EURUSD**: positive in both years
after spread + commission, and well above its zero-edge twin in the challenge simulation. Everything else is ~0 or
negative after FTMO costs. **Home-hours weakness does not come back**: with the 2-min news rule it takes ~770 trades
a year (re-entries after each blackout), and the 0.5-pip commission on ~1,550 trades (~775 pips) wipes out the drift.

**Big caveat:** EURUSD 2023–24 is where the London fade was found. On its unseen years 2021–22 (051) it made only
+0.24 pips/trade before commission, so with FTMO's commission it would be roughly −0.26 pips/trade there. The
65% pass rate is an in-sample, optimistic number; a realistic edge after FTMO costs is around zero.

