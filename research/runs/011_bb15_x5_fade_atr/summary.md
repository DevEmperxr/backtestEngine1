# 011 — 15m Bollinger stretch + 5m SMA 9/21 cross confirmation, stop 2.5 × 5m ATR

**Date:** 2026-10-05
**File:** research/strategies/011_bb15_x5_fade_atr.py
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
- **SL (011):** 2.5 × ATR(14) of 5m mid bars at the signal bar (same rule as 003/009). Identical to 010 otherwise.

## Pre-registered evaluation plan
- full adversarial suite; H1/H2; spread-adjusted random-walk null.
- independent audit: 15m and 5m bars rebuilt from 1s with `lib.data.resample`, bands
  and SMAs recomputed with numpy; for every trade, confirm a qualifying 15m close
  ≤ 120 min before entry and a matching 5m cross on the signal bar.
- **raised bar (trial 11 on 2024):** CI excludes 0 AND both halves positive AND TP rate
  ≥ 2 SE above the spread-adjusted null.

## Amendment (2026-10-05, before any P&L was computed)
A signal count on the registered rules (no P&L looked at) gave only 56 signals in
2024: the verdict would be withheld by construction. The user chose to amend the
setup life from **60 to 120 minutes**. Nothing else changed. New signal count: 101
(both 010 and 011). Also seen, still pre-P&L: median TP 5.8 pips vs median SL 11.7
(010) / 9.2 (011). The confirmation arrives late, so the remaining distance to the
middle band is small. Break-even win rate is therefore ~65–70%.

## Headline result
- trades: **99**, win rate 58.6%, net **+6.3** pips (expectancy +0.06/trade)
- profit factor 1.02, avg win +5.2 / avg loss −7.3, max DD −0.57%, Sharpe 0.14
- exits: 47 TP / 24 SL / 28 force-flat
- verdict: **withheld: "inconclusive (99 trades, need ≥100)"**

## Adversarial checks
- gross vs net: gross +37.9, spread 31.7.
- bootstrap CI (expectancy): **[−1.42, +1.49]**; win rate CI [48.5, 67.7]%.
- MC drawdown: −0.57% vs median −0.73%, rank 82% → `fragile` flag; moot.
- ex-best-month: drop Mar (+50.5) → −44.2; ex best 1 trade → −10.9; ex top 5% → −65.1.
- **H1/H2:** H1 −16.7 (60), H2 +23.0 (39).
- **random-walk null (spread-adjusted):** TP-first 66.2% vs **63.6%** null (z ≈ +0.45).
- **010 vs 011 (stop choice):** same entries; extreme-stop +12.8 vs ATR-stop +6.3.
  Indistinguishable at n ≈ 98.
- **Raised bar:** no on all three counts; verdict withheld for sample size.
- **lookahead audit: passed** (same checks as 010, all 0).

## Visual check
[sample_trades.png](sample_trades_entries_shared_with_010.png) (4 random trades of 010; 011 has the same entries):
setup line (15m close outside the band) precedes each entry within 2 h; the 15m bands step
only when a 15m bar closes (no lookahead on the chart); entries at a 5m SMA 9/21 cross;
TP 80% of the way to the middle band. The 02-08 trade shows the structural issue below.
Interactive `strategy.visualize` not run (no notebook).

## Interpretation
Inconclusive, and nothing points to an edge. The high win rate is exactly what the
geometry predicts: targets are about half the stop (median TP/SL 0.55), so a random
entry would win ~64% of SL/TP-resolved trades, and this won 66.2%. Under 100
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
