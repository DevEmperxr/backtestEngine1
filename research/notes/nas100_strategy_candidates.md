# NAS 100 strategy candidates (literature review, 2026-10-07)

For FTMO 1-step: intraday, flat by 16:55 New York, ~1 trade a day, FTMO US100.cash costs ≈ 1.7-point spread and no
commission (user-confirmed). Test only on NAS100 2023 + 2024 (user rule), template layer by layer.

## 1. Intraday momentum, "noise area" breakout (Zarattini, Aziz & Barbon 2024, SPY)
- Rule (as published): for each time of day, sigma = average over the last 14 days of |price / day's open − 1| at that
  time; upper boundary = max(open, previous close) × (1 + sigma), lower = min(open, previous close) × (1 − sigma).
  Checked every 30 minutes (HH:00, HH:30); go long above the upper / short below the lower boundary; trailing stop;
  flat at the close. Paper: SPY 2007–2024, 19.6% a year, Sharpe 1.33 **net of costs**; Quantpedia Awards 2025 (4th).
- Who loses: liquidity providers / mean-reversion traders fading a day with a real demand-supply imbalance; late
  trend-followers and dealers hedging (gamma) push it further.
- Our adaptation: the paper's trailing stop uses VWAP, which the user excluded -> trail on the boundary only.
- FTMO fit: ≤ 1–2 trades a day; trend-day profits are lumpy (watch the 50% best-day rule in the challenge).

## 2. 5-minute opening-range breakout (Zarattini & Aziz 2023, QQQ)
- Rule: direction of the first 5-minute candle after 09:30 NY; enter at 09:35; stop at the other side of that candle;
  target 10R or the close. Paper: 24% hit rate, +0.13R per trade on QQQ (2016–2023).
- **Independent replication (2015–2026, 5 indices): gross reproduced (NQ +0.131R), net ≈ 0 (NQ +0.002R) with
  2.5 points of cost on NQ.** FTMO's ~1.7-point spread and no commission would leave roughly +0.04R: thin.
- FTMO fit: poor-ish. 24% win rate and 10R targets = long losing streaks and lumpy best days.
- Our own FX result (059): breakouts lost at the London open; indices are where ORB was found, so worth one test.

## 3. Market intraday momentum (Gao, Han, Li & Zhou 2018, SPY 1993–2013)
- First half-hour return (from the previous close to 10:00 NY) predicts the last half-hour (15:30–16:00); stronger on
  volatile, high-volume and macro-news days; also in other ETFs. In FX (064) it was in the right direction but tiny.
- FTMO fit: one 30-minute trade a day, small moves vs a 1.7-point spread; likely thin.

## 4. Pre-FOMC drift (Lucca & Moench 2015)
- US stocks rise ahead of FOMC announcements. Intraday version: long the morning of FOMC day, out by 13:58 NY (before
  the ±2 min news window at 14:00). Only ~8 trades a year: an add-on, not a strategy.

## Excluded by the user's rules
- Overnight drift (equity returns earned mostly overnight: Cliff, Cooper & Gulen 2008; Lou, Polk & Skouras 2019) and
  turn-of-the-month effects need overnight holds.
- Anything VWAP-based.

## Suggested order once NAS100 2023–24 is downloaded
0. Descriptive first (template POI = time): where in the day NAS100 moved in 2023–24 (as 076 did for gold).
1. Noise-area intraday momentum (strongest evidence, net of costs in the paper).
2. 5-minute ORB (gross edge documented; test whether FTMO's lower cost leaves something).
Needs first: index support in the engine (points, contract size, FTMO spread top-up ≈ +0.2 points, US news filter,
session hours).
