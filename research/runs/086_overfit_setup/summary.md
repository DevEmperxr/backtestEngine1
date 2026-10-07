# 086 — DELIBERATE OVERFIT over the setup template (user-approved one-off learning exercise), GER40 2023

**Date:** 2026-10-07 · search: research/regime/setup_search_086.py · rules: research/strategies/086_overfit_setup.py
**Status:** the user asked to over-fit properly, using the setup template, on Jan–Jun 2023, respecting our rules, to
understand what happens; "then we will never do that again". **Nothing here is a candidate.** 2024 not touched.

## Menu searched (Frankfurt time; FTMO costs + EUR news ±2 min + flat 17:25 + one trade/day; no VWAP)
- Context (7): none · previous day narrow / wide vs ATR · gap big / small · volatility rising / falling
- Bias (7): both · with / against daily trend (SMA10) · with / against the gap · with / against the previous day
- POI (6) × window (4): previous-day H/L · pre-open range · first-hour range · pivot R1/S1 · 5m Bollinger(20,2) ·
  round 100s  ×  09–10 / 10–12 / 12–14:30 / 14:30–17
- Confirmation (4): rejection · pin-bar rejection · break · break-and-retest
- Execution: stop 0.1 / 0.2 / 0.35 × daily ATR; target 1R / 2R / 3R / hold to 17:25
- 16,128 setups had ≥ 30 trades in Jan–Jun. Ranked by total R in Jan–Jun.

## The winner (fast search and engine agree exactly; lookahead audit clean)
Rising volatility · bias against the previous day's candle · round 100 level · 10:00–12:00 · break-and-retest ·
stop 0.1 × daily ATR (~16 pts) · no target, hold to 17:25.

| | trades | R per trade | total R | win % | FTMO 1-step pass / EV (twin) |
|---|---|---|---|---|---|
| Jan–Jun (chosen here) | 30 | **+2.39** (CI +0.59 … +4.36) | +71.8 | 40 | **94.6% / +$11,281** (38.9% / $236) |
| Jul–Dec (same rules) | 36 | **+0.00** | +0.2 | 17 | 31.7% / $213 (31.1% / $210) |

- Half of its Jan–Jun profit was 3 trades on 24 Feb, 15 Mar and 17 Mar 2023 (the SVB / Credit Suisse panic).
- Across all 16,128 setups: Jan–Jun median −0.05R/trade, Jul–Dec −0.07R. Correlation of a setup's Jan–Jun result with
  its Jul–Dec result: **−0.09** (none). Top 50 on Jan–Jun averaged −0.08R/trade in Jul–Dec; top 1% −0.10R.
- What the top 50 "liked": round numbers and Bollinger bands, 10–12, break/retest, the tightest stop and no target
  (tight stop + no target = a lottery ticket that pays big on a few trend days).
