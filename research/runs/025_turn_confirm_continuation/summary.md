# 025 — Idea 2: after a stretch, wait for a confirmed 5m turn, ride the continuation (2023)

**Date:** 2026-10-06
**File:** research/strategies/025_turn_confirm_continuation.py (make_a / make_b / make_c = targets)
**Status:** exploring

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
_(filled after the run)_

## Interpretation
_(filled after the run)_

## Decision
_(filled after the run)_
