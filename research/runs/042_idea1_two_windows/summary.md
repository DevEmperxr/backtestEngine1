# 042 — Idea 1 with two entry windows only: London fade (sideways) + NY open (trending), 2023 + 2024

**Date:** 2026-10-06 · file: research/strategies/042_idea1_two_windows.py
**Status:** exploring (in-sample combination, user request)

## What
023A rules (1m sweep at a 2·ATR 5m stretch, stop 1.5 × 5m ATR, target the 5m SMA20), with entries
allowed only (entry hour in New York time):
- **03:00–04:59 and 1h sideways** (the London-open fade: 034/035)
- **08:00–09:59 and 1h trending, with the trend** (the NY-open window: 033)

One strategy, one position at a time, window 08:00 London → 16:00 NY, flat 16:00 NY. EURUSD 2023 + 2024.

**Caveat:** both windows were found on these years (the London fade on 2023 and tested on 2024; the NY
window on both). This shows how they work together, not evidence. (The NY window failed on EURGBP
in 037, but EURGBP has no USD; it needs a USD pair for a fair test.)

## Results
Lookahead audit clean both years (0 issues). Stats: research/regime/two_windows_042.py -> stats.json.

| | London fade | NY open | Combined |
|---|---|---|---|
| trades | 434 | 157 | 591 |
| net pips 2023 / 2024 | +322.2 / +140.0 | −24.5 / +157.5 | +297.7 / +297.5 |
| total | +462.2 | +133.0 | +595.3 |
| per trade (95% CI) | +1.07 [+0.25, +1.91] | +0.85 [−0.94, +2.72] | +1.01 [+0.21, +1.79] |
| win rate / payoff / PF | 48.8% / 1.37 / 1.31 | 45.9% / 1.40 / 1.18 | 48.1% / 1.37 / 1.27 |
| fair Sharpe (all days) | 1.75 | 0.64 | 1.77 |
| max DD (pips) / longest underwater | −147 / 283 d | −122 / 475 d | −126 / 237 d |
| months positive | 16/24 | 16/24 | 19/24 |
| without best 5 trades | +329.0 | −8.8 | +440.9 |

Monthly correlation between the two windows: −0.34 (they offset each other).

**NY window is fragile.** In 033 the same slice made +95.5 in 2023; here −24.5. With 07:00 and
sideways trades no longer taking the one position slot, ~15 extra NY trades per year get through:
−94.0 in 2023, +71.8 in 2024. The shared trades are positive both years (+69.5 / +85.7), but the
result depends on which trades happen to get through. Without its 5 best trades it is negative.

**Verdict:** the London fade carries this pair (CI above 0 on 2023+2024, but in-sample: found on 2023).
The NY window adds variety (negative correlation) but no reliable edge yet. Real check: a
pre-registered run on reserved years (2021/2022/2025), only with the user's go-ahead.
