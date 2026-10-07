# 077 — Asia-session trades: gold long in an uptrend, and AUDUSD with the daily trend, 2023 + 2024 (in-sample)

**Date:** 2026-10-07 · strategy: research/strategies/077_asia_session.py · analysis: research/regime/asia_077.py
**Status:** pre-registered. User: "try that and also try it for audusd". **In-sample by construction**: the idea comes from
076, which looked at these same years (gold rose mostly in Asian hours in 2023–24).

## Template
0. **Who loses / who we ride:** gold: price-insensitive physical and central-bank buying in Asian hours (China, India).
   AUDUSD: no buyer story; trade the Asian session with the daily trend.
1–2. **Context / bias:** previous completed FX day's close vs its 50-day SMA (data/derived/<pair>_daily_2023_2024.parquet).
3. **POI (time):** signal on the 1m bar closing at **19:00 New York** (after the 17:00 reopen spread settles), FX days
   Mon–Fri (Sunday evening = Monday).
4. **Confirmation:** none (time-based).
5. **Execution:** enter at 19:00; **exit at 03:00 New York** (never crosses the 17:00 rollover); protective stop = 0.5 ×
   the previous FX day's ATR(14); no target (10 × stop); FTMO ±2 min news (pair's currencies; no re-entry the same night);
   prop mode (gold 0.0007%/side commission; AUDUSD $5/lot).

## Variants (fixed now)
- **gold_trend:** XAUUSD long only, on days whose daily trend is up (the idea).
- **gold_always:** XAUUSD long every day (reference: pure Asian-session drift).
- **aud_trend:** AUDUSD long in an uptrend, short in a downtrend (the idea, translated).
- **aud_always:** AUDUSD long every day (reference). Declared after seeing 076-style session totals for AUDUSD (Asia +567
  pips over 2023–24), so it's descriptive only.

## Bar
An idea (gold_trend, aud_trend) is a **candidate** if, after all FTMO costs: R per trade > 0 in both years, pooled
≥ +0.05R, and `ftmo_1step_scorecard` beats its zero-edge twin. Reported next to its "always" reference. Even a pass only
shows the trade's shape under FTMO costs in a gold bull market; it needs a year the user names (e.g. gold 2021–22,
flat to falling) to count as evidence.

## Results
_(filled after the run)_
