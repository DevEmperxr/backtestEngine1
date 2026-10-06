# 024 — Idea 1 (023A) with three stop methods: swing + buffer, time stop, break-even (2023)

**Date:** 2026-10-06
**File:** research/strategies/024_sweep_fade_stops.py (make_a, make_b, make_c)
**Status:** exploring

## In plain words
023A (1m sweep fade to the 5m MA20 with a stop of 1.5 × the 5m ATR) was positive when the 1h
was trending. The user asked to test three other stop methods on the same trade:
- **A, swing + buffer:** stop above the sweep's high **plus half a 5m ATR**.
- **B, time stop:** 023A's stop, and **close after 30 minutes** if the target hasn't been hit.
- **C, break-even:** 023A's stop, but **once price has covered half the distance to the
  target, the stop moves to the entry price**.

## Hypothesis
*(registered before any 024 trade was simulated; trials 4–6 of Idea 1 on 2023)*
- A: a stop at a level that means "the sweep failed", with room for normal noise, should be
  at least as good as a pure volatility stop.
- B: a real snap-back to the MA happens quickly. Trades still open after 30 minutes are more
  likely failed overshoots, so cutting them should help.
- C: trades that move halfway to the target and then turn back are the costly ones; moving the
  stop to entry should cut those losses.
Each is judged against 023A on the same entries.

## Rules (fixed now; everything else identical to 023A)
Entries, 1h context, 5m stretch, target (5m SMA20), window and 16:00 London flat: as 023A.
- **A:** stop distance = (sweep bar's high − signal close) + 0.5 × ATR14(5m) for shorts
  (mirror for longs), measured from the signal close.
- **B:** stop = 1.5 × ATR14(5m) as 023A; **max hold 30 one-minute bars**: if still open, exit at
  the open of the 30th bar after entry (exit reason "max_hold").
- **C:** stop = 1.5 × ATR14(5m) as 023A; **break-even** once price (on the exit side, so bid
  for longs and ask for shorts) has moved ≥ 50% of the TP distance in favour; the stop then
  moves to the entry price for the rest of the trade.
- Primary = "trending, stretch with the trend", as 022/023.

## Engine changes (needed for B and C; optional, off by default)
- per-trade **`max_hold_bars`** column (read at the signal bar like sl/tp): exit at the open of
  bar entry_bar + max_hold_bars if nothing else fired first; exit_reason `max_hold`.
- per-trade **`be_trigger_pips`** column: once the favourable move reaches it on the 1s path,
  the stop becomes the entry price. Within a single 1s bar the old stop is checked before
  the move to break-even (conservative).
- Both have unit tests; existing strategies and the §6 regression are unaffected.

## Evaluation (fixed now)
- Same as 023: full suite, H1/H2, spread-adjusted null (for C the null is only indicative,
  since break-even changes the bracket mid-trade), context table.
- **Comparison with 023A primary** (+56.7, +0.40/trade, TP-first 43.5% vs 37.2%) on the same entries.
- Pass bar (dev year) as 022/023. With six variants of Idea 1 now tried on 2023, any "best
  version" must be confirmed on other years before being believed.
- Audits as 023A, plus: A stop = sweep distance + 0.5·ATR; B no trade held past 30 bars; C every
  break-even exit at the entry price.

## Results
_(filled after the run)_

## Interpretation
_(filled after the run)_

## Decision
_(filled after the run)_
