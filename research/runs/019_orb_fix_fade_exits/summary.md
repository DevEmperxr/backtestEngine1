# 019 — Fade the breakout at the London fix: three redesigned exits (+ 018 unchanged), tested on 2021 and 2022

**Date:** 2026-10-05
**File:** research/strategies/019_orb_fix_fade_exits.py (make_a / make_b / make_c); 018 unchanged via research/strategies/018_orb_fix_fade.py
**Status:** 019A/B/C discarded; 018 not confirmed (open lead)

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
Data: 2021 (7.67 M 1s rows, checks PASSED; 4 gaps of 10–16 min at 17:13–17:55 NY rollover),
2022 (12.12 M rows, checks PASSED; December re-fetched after a DNS failure and appended:
one identical boundary row dropped; 1 gap at the Sunday 21:00 UTC reopen). Both outside
every test window. All lookahead/independent audits passed on every run.

| design | 2021 | 2022 | pooled n | pooled net | exp/trade | 98.75% CI (registered) | both years > 0 | verdict |
|---|---|---|---|---|---|---|---|---|
| 018 mirrored (control) | **+150.2** | **+24.8** | 258 | +175.1 | +0.68 | [−2.40, +3.90] | **yes** | not confirmed (CI ∋ 0) |
| 019A time exit | +320.5 | **−92.7** | 258 | +227.8 | +0.88 | [−2.75, +4.57] | no | fails |
| 019B ATR bracket | +73.9 | **−231.0** | 258 | −157.1 | −0.61 | [−3.93, +2.57] | no | fails |
| 019C back to range | **−15.3** | +65.2 | 156 | +49.9 | +0.32 | [−3.15, +3.71] | no | fails |

Per-year detail (95% CI): 018 2021 [−1.30, +3.72], H1 +138.9 / H2 +11.3; 2022 [−3.91, +4.18],
H1 +130.6 / H2 −105.8. 019A 2022 H1 −32.1 / H2 −60.6.

## Results — 2023–2025 (descriptive)
*(Run at the user's request while the test years were still downloading; the rules above
were already committed, so these numbers could not influence the confirmatory test. 2024
is the discovery year of the entry; none of this is evidence.)*

| exit design | 2023 | 2024 | 2025 | 3-yr total (n) | exp/trade | 95% CI |
|---|---|---|---|---|---|---|
| 018 mirrored (control) | +95.9 | +330.2 | +58.2 | +484.3 (341) | +1.42 | [−0.31, +3.21] |
| 019A time exit | +244.0 | +229.4 | +36.3 | +509.7 (341) | +1.49 | [−0.63, +3.62] |
| 019B ATR bracket | +78.5 | +272.9 | +8.2 | +359.6 (341) | +1.05 | [−0.68, +2.79] |
| 019C back to range | +108.9 | +139.3 | −65.7 | +182.5 (224) | +0.81 | [−0.89, +2.50] |

- A: 327/341 trades closed at the 16:00 NY time exit; only 14 hit the 3×ATR disaster stop.
- C: highest win rate (64.6–70.6%) but negative in 2025.
- All four in the same +0.8 to +1.5 pips/trade band: the entry carries the result, not the exits.
- 2025 is the weakest year for every design. All audits passed.

## Interpretation
**Nothing is confirmed.** No design's pooled 98.75% CI excludes zero, as the power section
predicted.

**The redesigned exits did not hold up.** The time exit (019A), best on 2023–2025 and
on 2021, lost in 2022. The ATR bracket lost badly in 2022. Back-to-range lost in 2021. On
2023–2025 all four designs looked alike. On fresh years they diverged, in no consistent
order, so the "best exit" was noise.

**The original 018 rule is now positive in every year available:** 2021 +150.2, 2022 +24.8,
2023 +95.9, 2024 +330.2 (discovery), 2025 +58.2. Across the four years that were unseen
when tested (2021, 2022, 2023, 2025): 481 trades, **+329.1 pips, +0.68/trade, 95% CI
[−1.02, +2.39]**, Sharpe 0.57; per-year expectancy +1.21 / +0.19 / +0.99 / +0.46. Four
positive unseen years out of four would happen about 1 time in 16 by chance if the true edge
were zero and each year a coin flip. That is suggestive, not significant, and the CI still
includes zero. The effect, if real, is about +0.5–1 pip/trade (≈ 1.5–3% of the per-trade
SD of 19 pips), far too small for these sample sizes to prove.

Note: 018 was positive in 2022, but its exits were never designed. That the
designed exits did no better suggests the mirrored levels are not hiding a better edge.
The entry carries whatever is there.

## Decision
**019A, 019B, 019C: discard** (each lost money in one of the two test years). **018 (control):
not confirmed, still the only open lead.** It met the "positive in both test years" part
again, but its pooled CI includes zero.
**Why:** registered criterion (98.75% CI excludes 0 AND both years positive) failed by
every design. 018 is now 4/4 positive on unseen years (+329 pips, +0.68/trade, 95% CI
[−1.02, +2.39]), but with an effect this small relative to per-trade noise, more history
alone won't settle it. 2026 remains the untouched holdout.
