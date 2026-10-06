# 025 — Idea 2: after a stretch, wait for a confirmed 5m turn, ride the continuation (2023)

**Date:** 2026-10-06
**File:** research/strategies/025_turn_confirm_continuation.py (make_a / make_b / make_c = targets)
**Status:** not passed (too few trades); candidate for the multi-year test

## In plain words
The 1h is trending up. The 5m makes a high far above its 20 MA (an overshoot). Instead of
guessing the top (Idea 1), we wait until the 5m *proves* it has turned: price pulls back to a
low, bounces to a **lower high**, and then a 5m candle **closes below that pullback low**. We
sell and ride the move. Mirrored for 1h downtrends. The user's Idea 2; Idea 1 is separate (022–024).

## Hypothesis
*(registered before any 025 trade was simulated)*

After an overshoot in the 1h trend direction, a confirmed 5m structure break (lower high,
then a close below the last low) marks the start of a 1h pullback. The pullback should usually
carry further than the break point. Because the entry comes after confirmation, the stop
(above the lower high) is structural and wider than 1m noise, which was the 022 failure.

Prior: sceptical. 010/011 showed that late confirmation can leave too little room to the target.
That is why the targets here are on the 1h, not the 5m MA.

## Rules (fixed now)
Mid prices; bars from 1s via `resample`; higher timeframes from **closed bars only**.
- **Signal frame:** 5m bars. **1h context** exactly as 022/023 (ER20 ≥ 0.32 + slope of the 1h SMA20 →
  up / down / sideways).
- **Swings (5m):** a bar whose high (low) is the highest (lowest) of the 5 bars centred on it,
  usable only **2 bars later** (confirmation). (Amended from 7 bars / 3 later.)
- **Short setup:** (1) a confirmed 5m swing high **P** whose high ≥ that bar's SMA20 + 1.5·ATR14 (amended from 2·ATR)
  (stretched); (2) a later confirmed swing low **L1**; (3) a later confirmed swing high **H2 < P**
  (lower high); (4) the first 5m bar after H2 is confirmed whose **close < L1** → short at the
  next 5m open. A swing high ≥ P before H2 replaces P (if stretched) or cancels the setup. The
  break must come within **36 bars (3 h)** of P, else the setup is dropped. Long = mirror.
- **Stop:** 1 pip beyond H2 (the lower high), measured from the signal close.
- **Targets:**
  - **A:** the 1h SMA20 of the last closed 1h bar.
  - **B:** 2 × the stop distance.
  - **C:** the most recent confirmed **1h swing low** (5 1h bars centred, usable 2 h later) below
    the entry, for shorts (the last 1h higher low); mirror for longs.
  - In A and C: skip the trade if the target is not beyond the entry.
- **Window:** entries 07:00 New York → 16:00 London, Mon–Fri; flat at 16:00 London; one position at
  a time; `exit_on_opposite_signal = False`.
- **Primary context = "trending, stretch with the trend"** (stretch up + short in a 1h uptrend,
  stretch down + long in a downtrend). The other contexts are reported.

## Evaluation (fixed now)
- Full suite on the primary subset; H1/H2; spread-adjusted null; context table.
- **Pass (dev year):** primary 95% CI excludes 0 AND both halves positive AND TP-first ≥ 2 SE above
  the null. Three target variants → a pass on one is only a candidate for other years.
- Audit: independent plain-Python re-derivation on 1s-rebuilt 5m bars of the swing sequence
  P → L1 → H2 (with confirmation delays) and the break close for every trade; stop = H2 + 1 pip.

## Amendment (2026-10-06, before any P&L was computed)
A signal count on the registered rules (no P&L looked at) gave only 30–35 primary-context
setups in 2023 (90 / 226 / 170 in total for A / B / C). The user chose to loosen **both**:
stretch **1.5·ATR** (was 2·ATR) and 5m swings confirmed after **2 bars** (7-bar → **5-bar**
window). New counts: A 139 (49 primary), B 367 (55 primary), C 259 (52 primary). Still small
for one year; the multi-year test is where this idea can be judged. 1h swings unchanged (k=2).
A has fewer setups because the 1h SMA20 is often already behind price when the turn confirms.

## Results
2023 (amended rules). [a_2023](a_2023/) [b_2023](b_2023/) [c_2023](c_2023/).

**Audit note:** the first run's audit flagged 3 trades per variant as "structure not found".
Cause: the audit built 5m bars from 1m mids, while the strategy uses 5m bars resampled from
1s with mid per field. The highs/lows differ slightly, so exact level matches failed. Re-run
with the strategy's bar definition (still separate pattern-search code): **0 failures in A, B
and C**. The audit is fixed in `run_experiment.py`; the results.json files still show the
original flags.

| target | context | trades | net | exp/trade | 95% CI | win | TP-first vs null | exits (TP / SL / time) |
|---|---|---|---|---|---|---|---|---|
| **A 1h SMA20** | **trend_with** | 49 | **+51.7** | +1.06 | [−2.75, +4.99] | 49.0% | 37.0% vs 43.6% | 10 / 17 / 22 |
| A | sideways | 87 | −112.2 | −1.29 | [−3.27, +0.69] | 52.9% | 50.7% vs 59.8% | 38 / 37 / 12 |
| **B 2R** | **trend_with** | 46 | **+23.1** | +0.50 | [−4.00, +4.96] | 39.1% | 37.9% vs 32.2% | 11 / 18 / 17 |
| B | trend_against | 43 | +41.2 | +0.96 | [−4.22, +6.22] | 48.8% | 30.8% vs 32.2% | |
| B | sideways | 226 | **−584.3** | −2.59 | **[−4.48, −0.58]** | 34.1% | 21.1% vs 32.3% (z −2.9) | 31 / 116 / 79 |
| **C 1h swing** | **trend_with** | 51 | **+25.8** | +0.50 | [−3.87, +5.41] | 41.2% | 23.1% vs 30.4% | 6 / 20 / 25 |
| C | sideways | 173 | −231.9 | −1.34 | [−3.22, +0.58] | 45.1% | 39.7% vs 46.9% | |

Primary H1 / H2: A −4.8 / +56.5; B −6.1 / +29.1; C −50.9 / +76.7.

## Interpretation
**No pass, and too few trades to say much.** The with-trend case is mildly positive for all three
targets (+23 to +52 pips over ~50 trades), but every CI spans roughly ±4–5 pips/trade. None is
positive in both halves (all lose in H1), and targets are not hit more often than chance:
much of the result comes from the 16:00 time exit, not the targets.

The one consistent pattern, again: **sideways context loses clearly** (B −584, CI excludes 0,
TP-first 2.9 SE below the null). In a sideways 1h, a "confirmed 5m turn" after a stretch is
usually just noise, and the continuation doesn't come. That is the same message as 023:
the 1h context matters, mostly as a "don't trade sideways" filter.

Target A has fewest setups because the 1h SMA20 is often already behind price when the
5m turn confirms. Late confirmation eats the room, as in 010/011.

## Decision
**Not a pass on 2023; no target variant stands out.** ~50 primary trades per year is too few to
judge. Idea 2 can only be assessed on several years pooled. With Idea 1 (023A), it is a
candidate for the user's planned multi-year test, with-trend only and rules unchanged. Main
learning across both ideas: **sideways 1h context is reliably bad for both.**
