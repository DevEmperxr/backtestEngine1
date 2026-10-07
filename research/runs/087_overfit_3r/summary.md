# 087 — DELIBERATE OVERFIT #2: most 3R winners, one trade a day, built from the setup elements (GER40 Jan–Jun 2023)

**Date:** 2026-10-07 · search: research/regime/search_3r_087.py · rules: research/strategies/087_overfit_3r.py
**Status:** user-requested over-fit (second one; user: "maximize the number of 3R trades... 1 trade a day... the
importance of the elements of trading setups"). Selection on Jan–Jun 2023 only; Jul–Dec shown after. 2024 untouched.

## Menu (each element as the user defined it)
- **Context** (where are we: up / down / range): SMA20 + slope · efficiency ratio · swing structure (HH/HL vs LH/LL);
  on daily / 1h / 15m (9 readers)
- **Bias** (expect up or down): with the context · against it · in a range: mean-revert to the 20-bar midpoint ·
  in a range: lean with the side of the midpoint price is on ("range breakout")
- **POI** (level + time): previous-day H/L · pre-open range · first-hour range · round 100s · 5m Bollinger(20,2) ·
  last 1h swing H/L · day open · previous close; as pullback (support for longs) or breakout level; windows 09–10,
  10–12, 12–14:30, 14:30–17, 09–17
- **Confirmation** (within 15 min of the POI): none · rejection · engulfing · micro break of structure (5 bars) ·
  3 closes holding · RSI(14) turn
- **Execution:** target 3R; stop beyond the swing since the touch, or 0.1 / 0.2 × daily ATR; exit 17:25; EUR news ±2
  min; FTMO costs; first signal of the day only. 29,043 setups had ≥ 20 trades in Jan–Jun. Ranked by 3R wins Jan–Jun.

## Results (engine; fast search matches exactly; lookahead audits clean)
| | Jan–Jun trades / 3R wins / R per trade | Jul–Dec trades / 3R wins / R per trade |
|---|---|---|
| **#1 winner**: 15m SMA context, with-trend bias, 5m Bollinger breakout, engulfing, stop 0.1 ATR | 121 / **39** (32%) / +0.32 | 124 / 27 (22%) / **−0.10** |
| **#2 runner-up**: 15m SMA "range", lean with the side of the 20-bar midpoint, pullback to the day open, no confirmation, stop 0.1 ATR | 111 / **38** (34%) / +0.49 | 116 / 39 (34%) / **+0.38** |
| All 29,043 setups (average) | 17% hit / −0.06 | 17% hit / −0.10 |
| Top 50 on Jan–Jun (average) | 29% hit / +0.20 | 23% hit / −0.07 |

- 3R hit rate needed to break even ≈ 25% (+ costs ~0.1R).
- **Hidden news effect:** both had their best trades at US data releases (14:30 Frankfurt = 08:30 New York; e.g. 12 Jan
  2023 CPI, 3R in 5 seconds). The DAX news filter only blocked EUR news. With a tight stop and a 3R target, a big
  release pays +3R half the time and −1R the other half, so the news trades looked great. That is news trading (not
  allowed at FTMO).
- **Re-run with EUR + USD news blocked:** winner +0.29 -> −0.11; runner-up **+0.36 (Jan–Jun) and +0.28 (Jul–Dec)**,
  3R hit 28% in both halves, 225 trades.

## Reading
The winner on the searched half fell apart on the second half, like 086. The runner-up held up in both halves, but
it was singled out partly BECAUSE its Jul–Dec looked good, so Jul–Dec is no longer a clean test for it. If it is
taken further it must be frozen exactly as is (EUR + USD news) and tested once on GER40 2024 (user's decision).
Lesson kept: the DAX news filter for future work should include USD.

---

## Test (pre-registered 2026-10-07 before running): runner-up FROZEN on GER40 Jan–Jun 2024
User: "look at the first half of 2024". Config exactly as in winner.json["runner_up"], EUR + USD red news ±2 min, FTMO
costs. Data loaded from 2023-12-01 (warm-up only) to 2024-06-30 (Jul–Dec 2024 not loaded); only 2024 trades count.
**Pass:** R per trade after costs > 0 with 3R hit rate > 25%, and the FTMO 1-step scorecard beats its zero-edge twin.
A pass means "worth one more out-of-sample check", not a strategy; a fail ends it.

### Result: FAIL
108 trades, **−0.19R per trade** after costs (CI −0.45 … +0.10), 3R hit **15.7%** (needs > 25%; was 28% in 2023),
longs −0.35, shorts −0.04. Only January positive (+3.8R); March −13.2R. FTMO 1-step: pass 12%, EV −$53 vs zero-edge
twin 34% / +$197. **The 2023 consistency did not carry into 2024. Dropped.** Chart runner_up_2024H1.png.
