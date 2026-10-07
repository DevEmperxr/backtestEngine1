# 079 — NAS 100 "noise area" intraday momentum (Zarattini, Aziz & Barbon 2024), FTMO rules, 2023 + 2024

**Date:** 2026-10-07 · strategy: research/strategies/079_nas_noise_area.py · analysis: research/regime/noise_079.py
**Status:** pre-registered. User: "try those on nasdaq first". The published rules were built on SPY (2007–early 2024);
NAS100 2023–24 is new ground for them (closer to a fresh test than our usual in-sample work).

## Template
0. **Who loses:** traders fading a day that has a real demand/supply imbalance; dealers' hedging and late
   trend-followers extend the move.
3. **POI:** price outside the "noise area" at a 30-minute check.
4. **Confirmation:** none beyond the check (as published).
5. **Execution** (below). 1–2 (context/bias): none (as published).

## Rules (fixed now; from the paper, one change marked)
- Cash session 09:30–16:00 New York. Day open = mid at 09:30 (first 1m open); previous close = mid at the previous
  session's 16:00 (last 1m close before 16:00).
- For minute-of-session m: move_m = |price_m / open − 1|; **sigma_m = average of move_m over the previous 14 sessions**
  (computed from NAS100 2023+2024 joined, so 2024 is warmed up by 2023; the first 14 sessions of 2023 are skipped).
- Upper = max(open, prev close) × (1 + sigma_m); Lower = min(open, prev close) × (1 − sigma_m).
- Checks at **10:00, 10:30, … 15:30** (1m bar closing at that time): close > Upper -> long; close < Lower -> short;
  inside the area -> flat. A flip at a check reverses the position.
- **Change vs paper:** the paper trails with max(Upper, VWAP); VWAP is excluded by the user, so the exit is the
  boundary itself (flat when back inside the area at a check).
- Protective stop: one noise width (open × sigma_m at entry) from the entry; no target; flat 15:55 NY.
- FTMO: ±2 min USD news (blocks a check at e.g. 10:00 on data days); prop mode (no commission, +0.2-point spread top-up,
  flat by 16:55 NY).

## Bar
**Candidate** if, after all FTMO costs: R per trade > 0 in **both** years, pooled R per trade ≥ +0.05, and
`ftmo_1step_scorecard` beats its zero-edge twin. Also reported: before-cost result, long vs short, trades per day,
exits, best-day share (FTMO 50% rule).

## Results
_(filled after the run)_
