# 019 — Fade the breakout at the London fix: three redesigned exits (+ 018 unchanged), tested on 2021 and 2022

**Date:** 2026-10-05
**File:** research/strategies/019_orb_fix_fade_exits.py (make_a / make_b / make_c); 018 unchanged via research/strategies/018_orb_fix_fade.py
**Status:** exploring

## Hypothesis
*(registered while the 2021 and 2022 downloads were still running: neither file had
been opened. 2026 is the user's untouched emergency holdout and is not used.)*

018's **entry** (at 16:00 London, fade the day's 005 breakout if it is still open) was
positive in 2024 (discovery), 2023 and 2025, but its **exits** were inherited from the
morning breakout. TP = the breakout's SL and SL = the breakout's TP give a random shape
(stop/target ratio 0.3–4.4; 60 of 341 trades risked over 3× their target; 63% of trades
hit neither level and closed at 16:00 NY). If the post-fix reversal is real, exits
designed for it should express it at least as well. **The designs below were chosen
by reasoning about the trade, not by comparing them on 2023–2025** (no A/B/C result on
any year existed when this was written).

## Common rules (all four tests)
- Entry exactly as 018: run 005 unchanged; if that day's breakout trade has not touched
  its SL/TP by the 1m bar closing 16:00 Europe/London (Mon–Fri), signal the opposite
  direction there; entry at the next 1m open; force-flat 16:00 America/New_York.
- **ATR** = ATR(14) of **1h mid bars** built from the 1m bars, taken from the **last 1h
  bar closed at or before the signal bar's close** (as-of backward on close_time). Simple
  mean of true range, as `lib.signals.atr`.

## The four exit designs
- **018 (control, unchanged):** TP at the breakout's SL level, SL at the breakout's TP level.
- **019A — time exit:** hold to 16:00 NY. **Disaster SL = 3 × ATR**; TP = 10 × ATR
  (effectively none; the engine needs a TP). The reversal is a drift over the afternoon,
  so let the clock close it.
- **019B — volatility bracket:** **SL = 1.5 × ATR, TP = 1.5 × ATR** (symmetric, 1:1), plus
  the 16:00 NY exit. Same risk shape every day.
- **019C — back to the range:** TP = distance from the signal-bar mid close back to the
  **edge of the 07:00–08:30 NY range that the breakout broke** (range high for a long
  breakout, low for a short). **SL = 1.5 × ATR.** If price is already back inside the range
  at the fix (TP distance ≤ 0), **no trade** that day. "The breakout failed" as the target.

## Test design (fixed now)
- **Test years: 2021 and 2022** (unseen). Each test: pooled 2021+2022 expectancy CI at
  **98.75%** (Bonferroni 0.05/4) excludes 0 **and** net positive in both 2021 and 2022.
- **Secondary, descriptive only:** all four on 2023–2025 (those years have been seen for
  018's entry, so they cannot confirm anything), and a five-year pooled view.
- Power: ~110–120 trades/year; per-trade SD ≈ 18 pips for 018 (A probably similar,
  B/C smaller). Pooled 2 years ≈ 230 trades → SE ≈ 1.2 (018/A), so only edges above
  ~3 pips/trade could confirm. Given 018's decay to ~+0.5–1.0, **"not confirmed" is the
  expected result even if the effect is real.** Consistent direction across years is
  the informative part.
- Audits: entry re-derived by running 005 through `Engine` (as 018); ATR recomputed from
  1h bars rebuilt from 1s via `lib.data.resample`; TP/SL distances checked per design;
  0 force-flat violations.

## Results — 2021 and 2022 (confirmatory)
_(filled after the run)_

## Results — 2023–2025 (descriptive)
_(filled after the run)_

## Interpretation
_(filled after the run)_

## Decision
_(filled after the run)_
