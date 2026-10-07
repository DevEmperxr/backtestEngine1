# 077 — Asia-session trades: gold long in an uptrend, and AUDUSD with the daily trend, 2023 + 2024 (in-sample)

**Date:** 2026-10-07 · strategy: research/strategies/077_asia_session.py · analysis: research/regime/asia_077.py
**Status:** done. No candidate; gold ≈ break-even after costs, AUDUSD negative. User: "try that and also try it for audusd". **In-sample by construction**: the idea comes from
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
All 8 runs: lookahead audit ok. Analysis: research/regime/asia_077.py -> results.json, asia_equity.png. From 2023-03-14.

| variant | 2023 R/trade | 2024 R/trade | both [CI] | gross / costs (pips) | stops hit | FTMO 1-step pass / $ (twin) |
|---|---|---|---|---|---|---|
| gold_trend (long in uptrend) | −0.012 | +0.022 | +0.009 [−0.05, +0.07] | +1,317 / 1,365 | 26 of 309 | 38% / +$242 (18% / +$17) |
| gold_always (reference) | −0.013 | +0.037 | +0.015 [−0.03, +0.06] | +2,421 / 2,031 | 31 of 459 | 60% / +$593 (27% / +$90) |
| aud_trend (with trend) | −0.122 | −0.080 | −0.098 [−0.15, −0.04] | −690 / 755 | 61 of 460 | 0.5% / −$88 (24% / +$63) |
| aud_always (reference) | +0.006 | −0.084 | −0.044 [−0.10, +0.01] | +206 / 755 | 55 of 460 | 10% / −$51 (30% / +$134) |

Where gold's Asian drift went (raw mid move, pips = $0.10):
| year | 18:01 -> 19:00 (skipped: reopen, wide spread) | 19:00 -> 03:00 (traded) |
|---|---|---|
| 2023 | +1,338 | +407 |
| 2024 | +614 | +2,034 |

**Verdict: no candidate.**
- **Gold:** in 2023 most of the Asian rise happened in the **first hour after the reopen** (18:00–19:00), which the
  strategy skips on purpose because the spread is wide then; the traded part (19:00–03:00) rose only +407 pips, less
  than the ~4.4 pips of costs per trade. In 2024 the traded part rose strongly (+2,034). After costs: ≈ 0 in 2023,
  small positive in 2024. The daily-trend filter didn't help (gold_trend ≤ gold_always).
- **The FTMO scorecard looks good for gold_always (60% pass, +$593 per attempt)** because its trades are small and
  steady (wide stop, time exit) with a slightly positive average: that's the convex payoff on a low-variance,
  barely-positive stream. It is in-sample, in a gold bull market, and not significant (CI includes 0).
- **AUDUSD:** with-trend Asian trades lose clearly (−0.10R, CI below 0), even before costs; "always long" is about flat
  before costs and negative after. AUDUSD's high costs (~0.055R per trade on ~30-pip stops) don't help.
- The honest test of "gold rises in Asian hours" is a non-bull year (gold 2021–22, flat to falling), only if the user
  names it.

