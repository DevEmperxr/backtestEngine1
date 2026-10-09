# Strategy card — NAS100 "noise area" intraday momentum (milestone, 2026-10-09)

**Status:** the first strategy in this programme confirmed on data it was never built on. Lead candidate for the
FTMO 1-step $10k account. Rules FROZEN — do not tweak without a new pre-registered run.

Code: `research/strategies/089_noise_area_indices.py` (`NoiseAreaIndex("NAS100")`; `make_nas100`,
`make_nas100_2122`, `make_nas100_2025`). Original: `079_nas_noise_area.py`. Source: Zarattini, Aziz & Barbon,
"Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)", SSRN 4824172 (first posted ~May
2024), adapted without VWAP (user rule).

## 0. Who loses
Traders who fade a day with a real buy/sell imbalance. On unusually large moves, US-specific flows (option dealers'
hedging, leveraged-ETF rebalancing) push in the same direction, and the faders get run over.

## Rules (New York time, US cash session 09:30–16:00)
1. **Day open** = price at 09:30. **Previous close** = last price before 16:00 the day before.
2. **Noise width** for each minute of the session = the average distance of price from the open at that minute over
   the previous 14 sessions (as a % of the open).
3. **Upper boundary** = max(open, previous close) × (1 + noise %). **Lower** = min(open, previous close) × (1 − noise %).
4. **Checks** at 10:00, 10:30, … 15:30 (on the 1-minute close at that time):
   above upper -> be long · below lower -> be short · inside -> be flat. A flip reverses the position.
5. **Stop:** one noise width (open × noise %) from the entry. No target.
6. **Flat** at 15:55. Never overnight.
7. **News:** no trading ±2 min around red USD news (FTMO); open trades closed 2 min before.

## Results (after FTMO costs: no commission, spread + 0.2-point top-up), R = profit / amount risked
| year | 2021 | 2022 | 2023 | 2024 | 2025 | all 5 years |
|---|---|---|---|---|---|---|
| role | unseen | unseen | built here | built here | unseen | |
| trades | 214 | 252 | 198 | 212 | 209 | 1,085 |
| R per trade | +0.144 | +0.143 | +0.135 | +0.131 | +0.045 | **+0.120** (95% CI +0.05 … +0.20) |
- Beats "always long at the same times" in 4 of 5 years (equal in 2023); works in the 2022 bear market.
- Fails on the DAX (−0.085) and Nikkei (−0.038): Nasdaq-specific.
- **Possible decay after publication:** before June 2024 +0.140 R/trade (754 trades), after +0.077 (331 trades).
  Not statistically significant, but plan for a smaller edge (published edges typically lose ~half).

## FTMO 1-step settings (run 093)
- **Recommended:** challenge **1%** risk per trade · funded **1%** (FTMO max) · own daily stop **2%** ·
  withdraw every ~2 weeks.
- Simulated (2021–25 trades): pass ~74%, ~60 trading days to pass, ~+$1,570 expected per $89 attempt.
  If the edge has halved (+0.06): pass ~57%, ~+$710. If it is gone: pass ~39%, ~+$270 (FTMO's structure only).
- Size: lots = $ risk / (stop in points × $ per point per lot) — check US100.cash contract value in the platform.

## Before going live
1. Demo / paper trade it to check fills and spreads vs the backtest.
2. Agree a stop rule in advance (suggested: re-evaluate if the average after 200 live trades is below 0).
3. Data note: all NAS100 years 2021–2025 are now seen; 2026 is the only unseen data (emergency holdout).

## Run trail
079 (built, 2023–24) · 089 (vs always-long; DAX / Nikkei) · 090 (why: intraday character) · 091 (2025, narrow fail
+0.045 vs +0.05 bar) · 092 (2021–22, pass) · 093 (FTMO risk settings + decay check).
News after 2025-04-07: rebuilt from official schedules (`research/regime/news_rebuild.py`, validated 99/99).
