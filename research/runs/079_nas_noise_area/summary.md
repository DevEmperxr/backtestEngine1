# 079 — NAS 100 "noise area" intraday momentum (Zarattini, Aziz & Barbon 2024), FTMO rules, 2023 + 2024

**Date:** 2026-10-07 · strategy: research/strategies/079_nas_noise_area.py · analysis: research/regime/noise_079.py · window label fixed (10:00 check now inside in_window) before any analysis
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
2026-10-07, NAS100 2023 (from 2023-01-23, after the 14-session warm-up) + 2024, `--prop` (FTMO costs). Lookahead audit
clean both years (a window-label bug flagged the 10:00 check as "outside the window"; fixed, trades unchanged).

| | trades | R/trade after costs | 95% CI | win % | total R |
|---|---|---|---|---|---|
| 2023 | 198 | **+0.135** | −0.03 … +0.31 | 43 | +26.6 |
| 2024 | 212 | **+0.131** | −0.04 … +0.32 | 39 | +27.8 |
| both | 410 | **+0.133** | **+0.01 … +0.26** | 41 | +54.4 |
| long | 213 | +0.218 | +0.05 … +0.40 | 47 | +46.5 |
| short | 197 | +0.040 | −0.13 … +0.23 | 34 | +7.9 |

- Before costs +0.158R; costs only 0.025R per trade (median stop 65 points vs ~1.7-point spread).
- Exits: 318 by the boundary check, 92 by the stop. 1.46 trades per traded day, 281 days traded.
- Best day +8.4R = 15.5% of total profit (FTMO best-day limit 50%: fine).
- 14 of 24 months positive; worst month about −7R (Dec 2023).
- **FTMO 1-step scorecard** (best: 1% risk challenge and funded, own day stop 1.2%): pass **69.9%**, EV **+$1,434** per
  attempt, ~36 trades / 58 days to pass. Zero-edge twin: pass 38.2%, EV +$280. Beats the twin.

**Verdict: CANDIDATE**: passes every pre-registered condition (both years > 0, pooled +0.133 ≥ 0.05, beats the twin).

**Caveats (honest):**
- Each year alone has a CI that crosses 0; only the pooled CI is above 0.
- Momentum relies on a few big days: dropping the best 5% of trades turns 2024 negative.
- Longs carry most of it, in a 2023–24 Nasdaq bull market. Shorts are only +0.04R.
- Next checks: a long-only drift baseline (is it just "long Nasdaq"?), DAX/Nikkei 2023–24 with the same rules, and a
  reserved year only when the user names it.

