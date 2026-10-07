# 062 — POI study: round numbers (Osler 2003) and the Asian-session high/low, 2023 + 2024

**Date:** 2026-10-07 · script: research/regime/poi_round_asia_062.py · **Status:** pre-registered (descriptive)
Template layer: **3 — POI** (no context, bias, confirmation or strategy yet). EURUSD + GBPUSD primary, AUDUSD as a check.

## 0. Who loses, and why
- **Round numbers (Osler 2003, J. Finance; Osler 2005):** take-profit orders cluster exactly at round numbers,
  so trends tend to stall and reverse there; stop-loss orders cluster just beyond them, so after a round number
  is crossed, moves tend to accelerate. The losers are traders whose orders sit at predictable round levels
  (and those who run into them).
- **Asian high/low:** stops left overnight beyond the Asian range get run at the London open. Either the run
  fails (fake-out; the stopped-out traders paid the extreme) or it starts the day's move (the faders lose).

## 3. POIs (fixed now)
Common: 1m mid bars; previous completed FX days' ATR(20) as the distance unit; weekdays.
**A. Round numbers**, window **07:00 London -> 12:00 New York**. Two level types, tested separately:
"00" = every 0.0100 (e.g. 1.0800), "50" = the 0.0050 levels between them (e.g. 1.0850).
- **A1 reversal:** the first 1m bar in the window whose range reaches a round level not yet traded during this FX
  day, approaching from one side (previous 1m close on the other side). Expected: price turns back.
- **A2 continuation:** after such a touch, the first 1m close beyond that level (the same day, within the
  window). Expected: price keeps going in the crossing direction.
**B. Asian range:** high/low of bars opening 00:00–06:59 London (same London date).
- **B reversal (two-sided test):** the first touch of the Asian high (low) between 07:00 and 11:00 London, only
  if not already broken. One high and one low event per day at most.

## Outcome
From the event bar's close: race of X in the expected direction vs X the other way, within 4 hours.
X = **0.1 × ATR** (primary for A1/A2, ~8 pips) and **0.25 × ATR** (primary for B, ~20 pips); both reported for all.
Ties / unresolved excluded from the rate. Mean move after 30 / 60 / 120 min (pips, expected direction).

## Carry-forward rule
5 tests (A1-00, A1-50, A2-00, A2-50, B). Carried forward only if, for EUR+GBP pooled at the primary X, the success
rate is **≥ 55% in both 2023 and 2024** and the pooled two-sided binomial p < **0.01** (0.05 / 5). For B the
"expected" direction is reversal, but a significant **continuation** (≤ 45% both years, p < 0.01) also counts.

## Results
_(filled after the run)_
