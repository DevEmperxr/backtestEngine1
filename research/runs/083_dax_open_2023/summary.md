# 083 — How the DAX (GER40) behaves at the 09:00 Frankfurt cash open, 2023 (descriptive)

**Date:** 2026-10-07 · script: research/regime/dax_open_083.py · chart dax_open_2023.png · numbers results.json
**Status:** descriptive only (user: "look at the DAX on 2023, what is its behaviour at the open"). Not a strategy test.

## Findings (255 cash days, mid prices, before costs)
- **The open is the most violent time of day:** avg |1m move| 6.2 pts at 09:00–09:15, vs ~2.5 at midday and ~4 at the
  US open (15:30). Spread drops from 2.6 (08:00–09:00) to 1.44 at 09:00 exactly.
- **The first hour sets the day's extremes:** the day's high or low is set in 09:00–10:00 on 65% of days (25.5% of
  all highs/lows in the first 30 minutes alone). Second cluster: 17:00–17:30 (12.5%) and 14:30 (US data).
- **The first move does NOT continue; it leans slightly to reversal:** first 30 min vs the rest of the day corr −0.11;
  trading with the first 30 min to 17:30 = −10.9 pts/day (t −1.75); with the first 60 min −6.8 (t −1.2).
- **15-min opening-range breakouts fail slightly:** median range 43 pts, break at ~09:19, only 47% close beyond the
  break level, −7.5 pts per day (t −1.2).
- **Overnight gap** (09:00 vs previous 17:30): median 44 pts; fills the same day 58%, by 10:00 37%. The first 30 min
  is a coin flip vs the gap direction (51%); fading the gap 09:00 -> 09:30 is negative.

## Reading
The DAX open is a high-volatility "two-way" auction: the first hour usually prints one end of the day, and early
moves tend to be given back rather than extended (weak; one year). Consistent with 081 (fading stretches inside the
first two hours lost) and 082 (going with them only ~break-even): what tends to happen is a spike that sets an
extreme then a reversal over HOURS, not minutes. Hypotheses for later (need pre-registration, 2023 dev / 2024 test):
fade the first-30-min move with a target later in the day; or trade the return from the first-hour extreme.
