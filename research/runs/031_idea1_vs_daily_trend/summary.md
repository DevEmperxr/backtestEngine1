# 031 — Does Idea 1 lose when the daily trend changes? (EURUSD 2023 + 2024, descriptive)

**Date:** 2026-10-06
**Script:** research/regime/daily_trend_vs_idea1.py · chart: [idea1_vs_daily_trend.png](idea1_vs_daily_trend.png)
**Status:** done (descriptive analysis, no new trades)

## Question (user)
Compare Idea 1's (023A) equity and monthly P&L with the daily EURUSD chart: are we losing
money because the bigger (daily) trend changes?

## Method
- Daily mid closes; daily trend = close above / below its 50-day MA, taken from the last daily
  bar closed before each trade's entry (no lookahead). Late-2022 prices only warm up the MA.
- Idea 1 1h-trend trades (273, 2023 + 2024) split into "with" vs "against" the daily trend.
- Monthly correlation of Idea 1 P&L with EURUSD's monthly move, its size and its range.

## Results
| trades vs daily trend | 2023 | 2024 | both: n | net | exp/trade | 95% CI |
|---|---|---|---|---|---|---|
| with daily trend | +96.0 (56) | −105.6 (66) | 122 | −9.5 | −0.08 | [−1.72, +1.63] |
| against daily trend | −39.3 (86) | +86.7 (65) | 151 | +47.3 | +0.31 | [−1.20, +1.84] |

Monthly correlations (24 months): with EURUSD monthly move −0.14; with size of move +0.26;
with monthly range −0.01. With 24 months, anything inside about ±0.4 is noise.

## Interpretation
**No consistent link with the daily trend.** "With the daily trend" made money in 2023 and lost in
2024; "against" did the opposite. The groups swap every year, which is what noise looks like.
Monthly P&L doesn't follow EURUSD's monthly direction or the size of its moves either.
Individual bad months do coincide with sharp daily moves (Jul 2023 spike and reversal; Sep 2023 slide
from 1.10 to 1.05), but so do good months (Aug and Dec 2023), so the daily chart doesn't explain the
losses.

## Decision
The daily trend is not a usable filter for Idea 1 on these two years. Idea 1's results look like
noise around zero rather than a strategy that works in one daily regime and fails in another.
