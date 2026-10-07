# 084 — DAX-open reversal ideas (from 083), GER40 2023 in-sample, FTMO rules

**Date:** 2026-10-07 · strategy: research/strategies/084_dax_open_reversal.py
**Status:** pre-registered before running. User: "run a and b on 2023 and see if it changes the result, then I'll
decide if we test on 2024". **2023 is in-sample** (083 found the pattern in 2023); 2024 would be the test.

## Who loses
Opening-auction momentum traders and opening-range breakout traders: at the DAX open the first spike usually sets
one end of the day (083: 65% of days have the high or low in 09:00–10:00) and is given back over the following hours.

## Rules (Frankfurt time; EUR red news ±2 min; FTMO index costs; flat 17:25)
- **a — fade the first 30 min:** at the 1m bar closing 09:30, short if mid > the 09:00 open, long if below. Stop 5 pts
  beyond the 09:00–09:30 high (short) / low (long), at least 10 pts. No target; exit 17:25.
- **b — first-hour false break:** first-hour range = 09:00–10:00 high/low. From 10:00 to 12:00, the first 1m bar whose
  high exceeds the first-hour high and closes back below it -> short (mirror for the low -> long). Stop 5 pts beyond
  the highest high (lowest low) since 10:00, at least 10 pts. No target; exit 17:25. One trade a day.

## Bar for "worth testing on 2024"
After all FTMO costs on 2023: R per trade ≥ +0.05 and the FTMO 1-step scorecard beats its zero-edge twin.

## Results
GER40 2023, `--prop`, audits clean. Charts a_2023.png / b_2023.png; numbers results_2023.json.

| | trades | R/trade after costs | before costs | win % | avg win / loss | stopped out | FTMO EV vs twin |
|---|---|---|---|---|---|---|---|
| a fade first 30 min | 245 | **−0.113** | −0.016 | 16 | +4.4R / −1.0R | 82% | $48 vs $218 |
| b first-hour false break | 209 | **−0.053** | +0.051 | 20 | +3.9R / −1.0R | 80% | $102 vs $210 |

- Neither meets the bar (≥ +0.05R after costs and beats the twin), even in-sample. Not taken to 2024 unless the user asks.
- **a** made +974 points in total but loses in R: its stops (median 16 pts, ~3 minutes of normal open volatility)
  are hit on 82% of trades; the profit comes from a few wide-stop days. The structure (tight stop beyond the opening
  extreme + hold to 17:25) does not match a reversal that plays out over hours.
- **b** is roughly break-even before costs; costs (0.10R on a 13-pt stop) push it negative. Longs +0.07, shorts −0.15.
