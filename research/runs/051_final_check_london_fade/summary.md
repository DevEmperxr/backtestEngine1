# 051 — Final check: London fade (046) and the runner exits (050 B, C) on 2021 + 2022

**Date:** 2026-10-06 · **Status:** done. A = PASS by the letter of the bar, but the edge shrank a lot; B and C FAIL. User asked: "test the origin idea, A, B and C on the
previous years to see if it breaks".

## Data
EURUSD **2021 and 2022**, test years (research/DATA_SPLIT.md). Never seen by the London fade or any
Idea 1 run on EURUSD (previously used only by the fix-fade runs 016–019). The news calendar covers
both years (Iran-DST clock handled up to 2022). 2025 and 2026 not touched. B and C also run on
practice year 2024 (A's 2024 is known: 210 trades, +191.6).

## Versions (files unchanged, as committed)
- **A** = research/strategies/046_london_fade_standalone.py (the original London fade)
- **B** = research/strategies/050_london_fade_runner.py make_b (break-even at the middle band, run to the
  opposite stretch band, out by 08:00 NY)
- **C** = 050 make_c (half off at the middle band + B on the rest)
Same costs/fills/news blackout as before. No parameter is changed after seeing these years.

## Pass bar (fixed now)
For A, on the two test years pooled:
- **PASS:** net pips > 0 after costs, AND target hit first more often than the spread-adjusted
  random-walk chance rate in BOTH years.
- **STRONG PASS:** PASS and the pooled 95% bootstrap CI of per-trade pips is above 0.
- **FAIL:** pooled net pips <= 0, or target-first at/below chance in either year.
Each year is reported separately as well. B and C: adopted over A only if they beat A on the pooled test
years AND on 2023+2024 combined; otherwise A stays.

## Results
All runs: lookahead audit ok. Script: research/regime/final_check_051.py -> results.json; charts
equity_monthly_A_2021_2022.png, equity_monthly_A_2021_2024.png.

| net pips (trades) | 2021 (test) | 2022 (test) | 2023 (practice) | 2024 (practice) |
|---|---|---|---|---|
| **A** original | **−3.0** (229) | **+107.5** (205) | +263.5 (199) | +191.6 (210) |
| B runner | −94.9 (226) | −181.1 (203) | +205.4 (191) | +118.0 (202) |
| C half + runner | −41.7 (226) | −32.8 (203) | +210.7 (191) | +161.0 (202) |

| A | test 2021+2022 | practice 2023+2024 | all 4 years |
|---|---|---|---|
| trades | 434 | 409 | 843 |
| net pips | +104.5 | +455.1 | +559.6 |
| per trade (95% CI) | **+0.24 [−0.81, +1.35]** | +1.11 [+0.29, +1.92] | +0.66 [−0.03, +1.35] |
| win rate | 40.3% | 48.9% | 44.5% |
| max drawdown | −233.9 | −130.6 | −233.9 |
| target first vs chance | 40.7% vs 38.5% (2021), 39.8% vs 37.4% (2022) | 49% vs 39% | |

A by quarter on the test years: 2021 −55.5, −57.2, +31.4, +78.3; 2022 +41.3, −99.9, +62.0, +104.2.

**Verdict (pre-registered bar):**
- **A: PASS, not strong.** Pooled net > 0 and target-first above chance in both years, but the CI includes 0.
  Honest reading: the edge **shrank by about 80%** on unseen data (+0.24 vs +1.11 pips per trade;
  target-first edge +2 points vs +10). 2021 was flat, 2022 positive, and the drawdown nearly doubled.
  Part of the practice result was selection luck (the slice was found on 2023). What's left looks like a
  small real effect, thin against ~0.25 pip costs.
- **B, C: FAIL** (negative on both test years); A stays the exit.

2021 and 2022 are now used for the London fade. Remaining clean data: EURUSD 2025 (to 2025-04-07 for the
news filter) and 2026 (holdout), plus other pairs.

