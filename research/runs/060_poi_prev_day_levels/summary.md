# 060 — POI study: first touch of the previous day's high / low (London and NY mornings), 2023 + 2024

**Date:** 2026-10-07 · script: research/regime/poi_prev_day_060.py · **Status:** done. Not carried forward: a coin flip at both sessions
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
results.json, events.parquet (one row per touch).

| EUR+GBP pooled | events | reversal first @ 0.25 ATR (~20 pips) | @ 0.5 ATR (~40 pips) | resolved @ 0.5 | mean move after 60 / 240 min (+ = continues) |
|---|---|---|---|---|---|
| London 2023 | 139 | 53.5% | 51.4% | 35 | −1.2 / +0.9 pips |
| London 2024 | 122 | 51.1% | 57.1% | 28 | −0.8 / −2.9 |
| **London both** | 261 | **52.4% (p 0.51)** | 54.0% (p 0.53) | 63 | −1.0 / −0.9 |
| NY 2023 | 109 | 55.6% | 50.0% | 48 | −0.1 / −0.6 |
| NY 2024 | 110 | 42.2% | 38.2% | 34 | +2.6 / +1.7 |
| **NY both** | 219 | **49.2% (p 0.83)** | 45.1% (p 0.38) | 82 | +1.3 / +0.6 |

By pair (London, 0.25 ATR): EURUSD 59.5% / 57.5% reversal, GBPUSD 49.1% / 46.0%, AUDUSD 47.1% / 53.8%.
Highs vs lows (London, both years): highs 54.9% reversal, lows 50.0%.

**Verdict:** neither window meets the carry-forward rule. After the first touch of yesterday's high or low,
price is about as likely to run on as to turn back, and the average move afterwards is ~1 pip. **On its
own this POI has no edge** in either session.
Measurement note: at 0.5 × daily ATR most races (~70%) were still unresolved after 4 hours, so that test had
few cases; the 0.25 ATR race (most resolved) gives the same answer.
Small hint, not significant: EURUSD in London leaned toward reversal in both years (~58%); GBPUSD and AUDUSD didn't.

