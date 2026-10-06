# 033 — Idea 1 (023A) by entry hour (EURUSD 2023 + 2024, descriptive)

**Date:** 2026-10-06 · chart: [idea1_by_hour.png](idea1_by_hour.png)
**Status:** done (descriptive; post hoc, so a hypothesis only)

## Question (user)
Is there a significant pattern in Idea 1's results by time of the trade?

## Results (entry hour in New York time; entries allowed 07:00 NY → 16:00 London)
| hour | all: n | all: per trade | trending: n | trending: per trade | trending 2023 | trending 2024 |
|---|---|---|---|---|---|---|
| 07:00 | 321 | −0.51 | 63 | −0.87 | −29.8 | −25.1 |
| **08:00** | 446 | −0.37 | 64 | **+1.13** | **+52.5** | **+19.5** |
| **09:00** | 310 | −0.52 | 67 | **+1.34** | **+43.0** | **+46.6** |
| 10:00 | 299 | −0.31 | 73 | −1.04 | −20.7 | −55.4 |
| 11:00 | 23 | −0.56 | 6 | +1.18 | +11.7 | −4.6 |

- 1h-trending trades entered **08:00–09:59 NY**: 131 trades, **+161.6 pips (2023 +95.5 / 2024 +66.1)**,
  ≈ +1.2 pips/trade; trending trades at 07:00 and 10:00 are negative in both years.
- Every single-hour 95% CI includes 0. All-trades results are negative in every hour.

## Interpretation
The one consistent pattern: with the 1h trending, Idea 1 fades taken **08:00–10:00 New York** were
positive in **both** practice years, while 07:00 and 10:00 were negative in both. 08:30 NY is the main US
data release time, which fits 029 (Idea 2 also did better on news days): big stretches and sweeps
around the US open/data may be real overshoots that revert.

**Caveat: this was found by slicing** (5 hours × 2 groups, both practice years looked at), so it's a
hypothesis, not a result. Per-hour CIs all include 0.

## Decision
Carry forward one hypothesis: **"Idea 1, 1h trending, entries 08:00–10:00 NY only"**. It can't be
confirmed on 2023/2024 (it was found there). A fair test needs data where Idea 1 hasn't been sliced
by hour: another pair's 2023 + 2024 (EURGBP 2023/2024 were already used for Idea 1 in 027; other
crosses as they download, which need JPY support for the yen crosses), or a final check on the
reserved years when the user asks.
