# 024 — Idea 1 (023A) with three stop methods: swing + buffer, time stop, break-even (2023)

**Date:** 2026-10-06
**File:** research/strategies/024_sweep_fade_stops.py (make_a, make_b, make_c)
**Status:** discarded (023A remains the version)

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
2023, same entries as 023A. All audits passed (stops as specified; 0 trades held past 30
bars in B; every break-even exit at the entry price in C). [a_2023](a_2023/) [b_2023](b_2023/) [c_2023](c_2023/).

| version | context | trades | net | exp/trade | 95% CI | win | median stop | TP-first vs null |
|---|---|---|---|---|---|---|---|---|
| **023A (reference)** | trend_with | 142 | **+56.7** | +0.40 | [−1.34, +2.15] | 47.2% | 7.8 | 43.5% vs 37.2% (z +1.39) |
| 024A swing + buffer | trend_with | 191 | −92.6 | −0.48 | [−1.58, +0.66] | 29.3% | 4.6 | 24.6% vs 26.2% |
| 024B 30-min time stop | trend_with | 153 | −35.9 | −0.23 | [−1.51, +1.00] | 47.7% | 7.8 | 34.2% vs 39.1% |
| 024C break-even at 50% | trend_with | 147 | +26.2 | +0.18 | [−1.29, +1.68] | 35.4% | 7.6 | 40.9% vs 37.2% |
| 023A | sideways | 481 | −509.8 | −1.06 | [−1.94, −0.18] | | | |
| 024A / 024B / 024C | sideways | 578 / 506 / 496 | −285.4 / −390.6 / −419.8 | | | | | |

- 024B: 64 of 153 with-trend trades were closed by the 30-minute stop; TP hits fell from 50 to 25.
- 024C: 35 with-trend trades exited at break-even; TP hits fell from 50 to 38.
- 024A: the sweep distance plus half an ATR is smaller (median 4.6 pips) than 1.5 ATR (7.8),
  so it is stopped more often (129 SL vs 65).

## Interpretation
**All three stops are worse than 023A's plain 1.5 × ATR stop.** They fail for the same reason:
the snap-back to the 5m MA20 often takes time and comes after an adverse wiggle.
- A tighter, structure-based stop (024A) gets hit by those wiggles, like 022.
- Cutting trades after 30 minutes (024B) throws away trades that would have reached the
  target later: half of 023A's TP hits came after 30 minutes.
- Moving to break-even halfway (024C) closes trades that dip back to entry before
  going on to the target.

So the trade needs **room and time**, and 023A already gives it both. The context pattern
is the same in every version: with-trend is the best case, sideways clearly loses.

## Decision
**Discard 024A, 024B and 024C; keep 023A's 1.5 × ATR stop as Idea 1's version.**
**Why:** none beat 023A in the with-trend case (−92.6, −35.9, +26.2 vs +56.7). Six versions of
Idea 1 have now been tried on 2023, so 023A, the best of them, must be confirmed on other years
(unchanged, with-trend only) before it means anything.
