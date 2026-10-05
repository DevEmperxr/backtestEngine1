# 018 — Fade the day's opening-range breakout at the 16:00 London fix, out of sample

**Date:** 2026-10-05
**File:** research/strategies/018_orb_fix_fade.py
**Status:** not confirmed (open lead)

## Hypothesis
*(registered before the 2023/2025 files were read: downloads still running, partial
files unopened)*

On 2024, 005's ORB trades still open at 16:00 London went on to lose −368.7 pips
(118 trades, −3.12/trade) by their exit (≤ 16:00 NY). Fading that leg would have made
+368.7 before ~25 pips of extra spread: 95% CI [+0.81, +5.50] pips/trade, positive in both
halves. This is the only 2024 result whose CI excludes zero. **It was found by looking**
(post hoc, after ~15 trials), so 2024 proves nothing. The mechanism is published: the
day's move tends to reverse after the London fix (Krohn, Mueller & Whelan 2024; Evans
2018). If real, it must show up in 2023 and 2025.

## Rules (fixed now)
- Run the **005 breakout unchanged** each day (07:00–08:30 NY range; first 1m mid close
  beyond it after 08:30 NY; entry next 1m open; SL at the opposite side from the signal
  close; TP = 1.5 × range).
- Determine, from 1m bid/ask highs and lows up to the bar closing 16:00 London, whether that
  breakout trade has touched its SL or TP. (A 1m bar's high/low contains every second's,
  so "touched before 16:00" is exact.)
- **If still open:** signal on the bar closing 16:00 Europe/London, Mon–Fri, in the
  **opposite** direction; entry at the next 1m open (16:00:00 London).
- Exits: **TP at the breakout's SL level, SL at the breakout's TP level** (distances measured
  from the signal-bar mid close; skip the day if either distance is ≤ 0), and force-flat at
  **16:00 New York**. This mirrors the leg measured in 2024.
- One trade per day max.

## Test design (fixed now)
- Test years **2023 and 2025**; 2024 = discovery reference only.
- **Criterion:** pooled 2023+2025 expectancy CI excludes 0 **and** net positive in both
  years. **Family:** 016A, 016B, 017A, 017B, 018. Family-level confirmation at **99%**
  (Bonferroni 0.05/5).
- Power: ~120 trades/year → ~240 pooled; SD ≈ 13 pips/trade (2024 leg) → SE ≈ 0.85.
  2024's +3.1/trade would be clearly visible if it persisted at even half that size;
  an effect ≤ ~1.5/trade would likely not confirm.
- **Independent audit:** run the 005 strategy through `Engine` on the same data (separate
  code path). Every 018 trade must sit on a day where 005's trade exited `exit_signal` at
  16:00 London, with the opposite direction, entry_time = that exit time, and the fade's
  TP/SL levels equal to the breakout's SL/TP levels (within distance-measurement rounding).

## Results — 2023
- trades **97**, net **+95.9** pips, exp +0.99/trade, 95% CI [−2.11, +4.13], win 53.6%,
  gross +122.3, H1 **+155.8** / H2 **−59.8**

Data: 2023 (10.50 M 1s rows, checks PASSED; 10 gaps of 10–17 min, all 17:03–17:25 New
York = daily rollover, outside every test window), 2025 (9.42 M rows, checks PASSED,
0 unexplained gaps). All lookahead/independent audits passed on every run.

## Results — 2025
- trades **126**, net **+58.2** pips, exp +0.46/trade, 95% CI [−2.84, +3.87], win 57.1%,
  gross +104.0, H1 +7.7 / H2 +50.5
- sample trades: [main_2025/sample_trades.png](main_2025/sample_trades.png). Fade at 16:00
  London, opposite to the day's breakout, TP = breakout SL (far side of the range), SL =
  breakout TP, exit by 16:00 NY: mechanics correct. Geometry note: when price has already
  drifted back toward the range by the fix, TP is small and SL large (e.g. 06-10: TP 6.1 /
  SL 51.8), so the profile is many small wins and rare large losses.

## Pooled 2023 + 2025 and 2024 reference
| | n | net | exp | 95% CI | 97.5% CI | **99% CI (family)** | Sharpe | max DD |
|---|---|---|---|---|---|---|---|---|
| pooled 2023+2025 | 223 | **+154.1** | +0.69 | [−1.69, +3.03] | [−2.05, +3.36] | **[−2.47, +3.77]** | 0.61 | −2.25% |
| 2024 (discovery) | 118 | +330.2 | +2.80 | [+0.50, +5.18] | | | | |
| all three (descriptive) | 341 | +484.3 | +1.42 | [−0.31, +3.21] | | | | |

Registered criterion: CI excludes 0 → **no** (at every level); positive in both test
years → **yes** (+95.9, +58.2).

## Interpretation
**Not confirmed, but it is the only idea in the project that held its direction out of
sample.** It was positive in 2024 (discovery), 2023 and 2025, and positive before costs in all
three. The per-trade edge shrank sharply from discovery to test: +2.80 → +0.99 → +0.46.
That is the textbook winner's-curse pattern: the 2024 number was mostly selection luck,
and whatever is real is probably well under +1 pip/trade. At ~110 trades/year, an edge of
+0.5 pips/trade with SD ≈ 17 would need roughly **4,500 trades (~40 years)** to confirm
at 95%. More years of this rule cannot settle it quickly.

Consistent with the published post-fix reversal (Krohn, Mueller & Whelan; Evans), but
not evidence for it on its own. 2023's H2 was negative, so it is not steady within years.

## Decision
**not confirmed; keep as the project's only open lead, not promoted.**
**Why:** positive in all three years (the registered "both test years positive" part
passed), but the pooled 99% CI [−2.47, +3.77] includes zero and the edge decayed
from +2.8 to ~+0.5–1.0 pips/trade. Not tradable with confidence. Next steps, if pursued:
pre-register on further unseen data (2021–2022 or 2026 YTD), and/or a version with a
better-shaped bracket (the current TP/SL asymmetry is inherited from 005, not designed).
