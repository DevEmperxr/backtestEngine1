# 034 — Idea 1 (023A) from London open to New York close, by entry hour (EURUSD 2023)

**Date:** 2026-10-06
**File:** research/strategies/034_idea1_lon_ny.py
**Status:** done (descriptive)

## What
023A rules unchanged, except the entry window: **08:00 London → 16:00 New York**, everything flat
at 16:00 New York. 2023 only (user). Then results by entry hour (New York time), split by 1h context,
to see where in the wider day Idea 1 makes or loses money. Descriptive. Any hour-based rule
found here is a hypothesis for unseen data (033 already sliced 2023 + 2024 by hour inside the old
window).

## Results
EURUSD 2023; audit passed (1,699 trades, 0 failures). Charts: [by hour](idea1_by_hour_2023.png),
[equity, trending only](idea1_lon_ny_trend_2023.png).

| 1h context | trades | net | per trade |
|---|---|---|---|
| trending, with trend | 351 | −177.4 | −0.51 |
| trending, against trend | 213 | −234.9 | −1.10 |
| sideways | 1,135 | −406.9 | −0.36 |
| all | 1,699 | **−819.3** | −0.48 |

(Old window, 07:00 NY → 16:00 London, 2023: trending +56.7 on 142 trades.)

By entry hour (New York time; London ≈ NY + 5 h):

| hour NY (London) | trending: n / net | sideways: n / net | all: net |
|---|---|---|---|
| 03 (08 London open) | 35 / −85.7 | 125 / **+238.3** | +99.9 |
| 04 (09) | 28 / −36.5 | 82 / **+82.2** | +19.2 |
| 05 (10) | 18 / −18.9 | 72 / −123.8 | −113.4 |
| 06 (11) | 22 / **+107.9** (95% [+0.31, +9.83]/trade) | 80 / −120.7 | −43.4 |
| 07 (12) | 29 / −47.2 | 92 / −20.6 | −31.5 |
| 08 (13) | 29 / +52.5 | 166 / −95.7 | −121.2 |
| 09 (14) | 35 / −8.3 | 100 / −177.5 | −185.0 |
| 10 (15) | 39 / −81.6 | 95 / −75.3 | −181.1 |
| 11 (16) | 21 / +45.0 | 64 / −110.1 | −98.3 |
| 12 (17) | 29 / +7.6 | 59 / +17.5 | +31.8 |
| 13 (18) | 28 / −55.0 | 60 / −1.4 | −104.0 |
| 14 (19) | 19 / −35.3 | 78 / −51.7 | −81.4 |
| 15 (20) | 19 / −22.0 | 62 / +31.9 | −10.8 |

## What it shows
1. **The wider day is worse overall:** −819 pips, every context negative. Most extra hours lose,
   especially the US afternoon (13:00–15:00 NY) and late morning (09:00–10:00 NY).
2. **The London open stands out, but for sideways days:** fades entered in the first two hours after
   the London open (03:00–05:00 NY) with the 1h *sideways* made +320 pips on 207 trades. That's the
   opposite context from the original idea.
3. Trending trades are positive only in scattered hours (06, 08, 11 NY), with no clean block.
   Compared with 033 (old window), the 09:00 NY hour flipped from +43 to −8, because with more
   trades earlier in the day, one-at-a-time sequencing changes which later signals get taken.
   So the per-hour picture is fragile.
4. **Caution:** 13 hours × 3 contexts = 39 slices. At the 95% level, about 2 would look "significant"
   by luck alone. Nothing here is evidence; the London-open sideways block is a hypothesis
   worth testing on unseen data (and on 2024, which hasn't been used for the wider window).
