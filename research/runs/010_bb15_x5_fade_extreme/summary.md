# 010 — 15m Bollinger stretch + 5m SMA 9/21 cross confirmation, stop beyond the setup extreme

**Date:** 2026-10-05
**File:** research/strategies/010_bb15_x5_fade_extreme.py
**Status:** discarded

## Hypothesis
*(written and committed before any code or backtest — pre-registration; 010 and 011 registered together)*

User's idea. A 15m close outside the 2σ Bollinger band marks an overstretched move.
Fading it straight away (009) caught falling knives. Waiting for a **5m SMA 9/21
cross back in the reversion direction** should confirm the short-term turn, so the
trade enters only once the stretch has started to unwind. The target is set "a bit
before" the 15m middle band, to exit ahead of the obvious level where other
participants' take-profits sit (Osler 2003).

**Prior:** sceptical. 009 (a 5m band fade) and 008 had no edge; mean-reversion
evidence for intraday FX outside the fix effect is weak. More rules mean more free
settings, and trials 10–11 on the same year.

## Rules (fixed in advance)
- signal frame: 5m bars (resampled from 1s), mid prices.
- **15m Bollinger** from closed 15m bars only (as-of on close_time, `higher_tf_join`):
  mid = SMA(20) of 15m closes, bands = mid ± 2 × SD(20).
- **setup (long):** a closed 15m bar's close < its lower band. Setup time = that bar's close_time.
  Short: close > upper band. A later qualifying 15m close refreshes the setup.
- setup **valid for 120 min** (amended from 60, see below) (5m rows with close_time ≤ setup time + 120m), and
  **cancelled** if any 5m bar since the setup reached the current 15m middle band
  (high ≥ mid for a long setup / low ≤ mid for a short) before the confirming cross.
- **confirmation:** 5m SMA(9) crosses above SMA(21) of 5m mid close (long) / below (short),
  on a 5m bar inside an active setup, with the close still on the far side of the 15m mid.
- entry at the next 5m open; window 07:00 NY → 16:00 London (entry time = signal bar
  close_time), Mon–Fri; force-flat 16:00 London; `exit_on_opposite_signal = False`.
- **TP** = 0.8 × |signal close − 15m middle band| (user: "a bit before the middle band").
- **SL (010):** beyond the setup extreme. Lowest 5m mid low (long) / highest high (short)
  from the start of the setup 15m bar through the signal bar, ± 2 pips buffer.

## Pre-registered evaluation plan
- full adversarial suite; H1/H2; spread-adjusted random-walk null.
- independent audit: 15m and 5m bars rebuilt from 1s with `lib.data.resample`, bands
  and SMAs recomputed with numpy; for every trade, confirm a qualifying 15m close
  ≤ 120 min before entry and a matching 5m cross on the signal bar.
- **raised bar (trial 10 on 2024):** CI excludes 0 AND both halves positive AND TP rate
  ≥ 2 SE above the spread-adjusted null.

## Amendment (2026-10-05, before any P&L was computed)
A signal count on the registered rules (no P&L looked at) gave only 56 signals in
2024: the verdict would be withheld by construction. The user chose to amend the
setup life from **60 to 120 minutes**. Nothing else changed. New signal count: 101
(both 010 and 011). Also seen, still pre-P&L: median TP 5.8 pips vs median SL 11.7
(010) / 9.2 (011). The confirmation arrives late, so the remaining distance to the
middle band is small. Break-even win rate is therefore ~65–70%.

## Headline result
- trades: **98** (101 signals; 3 fired mid-trade), win rate 62.2%, net **+12.8** pips
  (expectancy +0.13/trade)
- profit factor 1.04, avg win +5.2 / avg loss −8.2, max DD −0.64%, Sharpe 0.27
- exits: 51 TP / 23 SL / 24 force-flat
- verdict: **withheld: "inconclusive (98 trades, need ≥100)"**

## Adversarial checks
- gross vs net: gross +41.5, spread 28.7 (0.29/trade, ~5% of the median 5.8-pip target).
- bootstrap CI (expectancy): **[−1.46, +1.64]**; win rate CI [53.0, 71.4]%.
- MC drawdown: −0.64% vs median −0.75%, rank 72% → `fragile` flag; moot.
- ex-best-month: drop Mar (+43.1) → −30.2; ex best 1 trade → −4.4; ex top 5% → −58.5.
- **H1/H2:** H1 −14.6 (59 trades), H2 +27.4 (39).
- **random-walk null (spread-adjusted):** TP-first 68.9% vs **68.0%** null (z ≈ +0.2).
- **Raised bar:** no on all three counts; verdict also withheld for sample size.
- **lookahead audit: passed.** 98/98 entries verified; independent numpy recompute on
  1s-rebuilt 15m/5m bars: 0 trades without a qualifying 15m setup in the 120-min life,
  0 without a matching 5m cross on the signal bar; 0 SL mismatches; 0 force-flat violations.

## Visual check
[sample_trades.png](sample_trades.png) (4 random trades of 010; 011 has the same entries):
setup line (15m close outside the band) precedes each entry within 2 h; the 15m bands step
only when a 15m bar closes (no lookahead on the chart); entries at a 5m SMA 9/21 cross;
TP 80% of the way to the middle band. The 02-08 trade shows the structural issue below.
Interactive `strategy.visualize` not run (no notebook).

## Interpretation
Inconclusive, and nothing points to an edge. The high win rate is exactly what the
geometry predicts: targets are about half the stop (median TP/SL 0.43), so a random
entry would win ~68% of SL/TP-resolved trades, and this won 68.9%. Under 100
trades, the expectancy CI is ±1.5 pips/trade wide; H1 negative, H2 positive.

Structural issue (post hoc, a new trial if acted on): the 5m 9/21 cross arrives
late. By then price is usually most of the way back to the middle band: 81–82 of ~98
trades had TP < SL, and 15 had TP < 2 pips (e.g. 2024-02-08: TP 0.1 vs SL 22.9). The
confirmation filters out falling knives, but also most of the reversion it was
meant to capture.

## Decision
**discard** (inconclusive; no sign of an edge).
**Why:** verdict withheld (<100 trades); expectancy CI ≈ ±1.5 pips straddles zero; the
win rate matches the random-walk null for this TP/SL geometry; H1 negative. Under the
raised bar this fails on every count.


Raw numbers: [results.json](results.json) · plots: [equity](equity.png), [monthly](monthly.png), [MC drawdown](mc_drawdown.png)
