# 060 — POI study: first touch of the previous day's high / low (London and NY mornings), 2023 + 2024

**Date:** 2026-10-07 · script: research/regime/poi_prev_day_060.py · **Status:** pre-registered (descriptive, POI layer only)
Template layer: **3 — POI** (no context, bias, confirmation or strategy yet).

## 0. Who loses, and why
Stop-loss orders cluster just beyond obvious extremes such as the previous day's high and low (Osler 2003, 2005:
stops cluster near such levels and can trigger cascades). When price reaches them, those stops are forced
orders. Either they **cascade** (price runs on; the people on the other side of the move lose) or they are
**absorbed** by larger players and price **reverses** (the stopped-out traders paid the extreme). This study
measures which happens more often, by session.

## 3. POI (fixed now)
- Levels: previous **FX day** (17:00–17:00 New York) high and low, mid prices.
- Event: the **first 1m bar** in the window whose mid high reaches the previous high (or mid low the previous low),
  only if today hadn't already traded beyond that level before the window opened. At most one high event and one
  low event per day per window.
- Windows: **London morning 07:00–11:00 London**; **NY morning 08:00–11:00 New York**.
- Measured from the event bar's close (nothing before it is used after it; no lookahead).

## Measurements
For distances X = 0.25 and 0.5 × daily ATR(20) (previous completed FX days):
- **Reversal race:** does price first move X back (away from the level, toward the day's range) or X further
  beyond the level, within 4 hours? Chance = 50% (same distance both ways). Ties within one 1m bar and
  unresolved races are reported separately and excluded from the rate.
- Also: forward mid return at 30 / 60 / 120 / 240 minutes, signed so that + = continuation beyond the level.

## Pairs / years
EURUSD, GBPUSD, AUDUSD; 2023 and 2024 (practice years).

## What counts as an interesting POI (for the next layer)
A window/level type is carried forward only if, for EURUSD + GBPUSD pooled, the reversal (or continuation) rate
at X = 0.5 ATR differs from 50% by **at least 5 points in both years**, in the same direction, with a two-sided
binomial p < 0.05 on the pooled sample. AUDUSD is reported as a check.

## Results
_(filled after the run)_
