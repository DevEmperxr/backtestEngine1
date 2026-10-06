# 054 — London fade vs market conditions, EURUSD by quarter 2021–2024 (descriptive)

**Date:** 2026-10-07 · script: research/regime/market_by_quarter_054.py -> results.json, by_quarter.parquet,
market_by_quarter.png · **Status:** descriptive, no rule change. User question: what was different in
the market before 2023?

## Findings
- **It didn't start winning in 2023.** 12 of 16 quarters were positive, starting 2021-Q3. The losing
  quarters: 2021-Q1 (−55), 2021-Q2 (−57), 2022-Q2 (−100), 2023-Q2 (−47). 2021 was flat because its first half lost.
- **The years differed a lot**, but not in ways that line up with the results:
  - volatility at the London open (5m ATR): 2021 4.5 pips, 2022 6.9, 2023 5.1, 2024 3.8. 2022, the most
    volatile, was positive; stops/targets scale with ATR. r = −0.09 with per-trade result.
  - spreads: 2022 highest (0.42 pips), 2024 lowest (0.23). r = +0.09.
  - EURUSD trend: down 871 pips in 2021, down 658 in 2022 (to parity), up 337 in 2023, down 691 in 2024.
    Quarterly move r = +0.48, but mixed (2022-Q3 fell 673 pips and the fade won).
  - choppiness: the 1h was "sideways" ~70% of window minutes in every year. Daily trendiness about the
    same every year (0.45–0.47).
  - 1m autocorrelation at the London open ~0 in every year (no year was clearly more mean-reverting).
- **The only clear link:** the strategy-free snap-back rate (share of 2xATR stretches in the window that
  reach the 5m SMA20 before running 1.5 ATR further), r = +0.48. The worst quarters had the lowest
  rates (2021-Q1 24%, 2023-Q2 27%). But that measures the edge itself, so it can't be known in advance.
- **Noise explains the pattern.** With +0.66 pips/trade, an SD of 10.2 pips/trade and ~53 trades a quarter,
  a quarter's average has an SD of ~1.4 pips, so ~32% of quarters should be negative from luck alone:
  **~5 of 16 expected, 4 observed.** No regime change is needed to explain 2021–2022 vs 2023–2024: a
  small, steady edge plus ordinary noise looks exactly like this. (The 2023 edge looked bigger partly
  because we picked the slice on 2023.)

## Implication
No market filter visible in advance (volatility, trend, spread, choppiness) separates the bad
quarters. Filtering on any of them now would be fitting to 4 bad quarters.
