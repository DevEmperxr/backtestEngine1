# §6 Regression — SMA(20/50) crossover

**Verdict: PASS, with one caveat** (the prototype's `sl_pips`/`tp_pips` aren't in
the spec, so they were fitted).

Investigation: [`notebooks/regression.ipynb`](notebooks/regression.ipynb).
Test: [`lib/tests/test_regression.py`](lib/tests/test_regression.py) (`-m slow`,
skipped if the data file is absent).

---

## Baseline (spec §6)

The 5-minute prototype, with the old "assume SL hit first" same-bar fill
approximation:

> **1,691 trades · −346.5 pips · 33.0% win rate**

Rebuilt here: `load_1s_data` → `resample("5m")` → `SmaCrossoverStrategy(20/50)`
(mid price for signals, reverse-on-opposite like the prototype) → `Engine.backtest`
(rising-edge entries, t+1 timing, spread-correct fills, SL/TP resolved on the
real 1-second path).

## Headline comparison

| metric | baseline | `sl=10/tp=20` (test config) | fitted `mid, sl=8/tp=15` | §6 tolerance |
|---|---|---|---|---|
| trades | 1,691 | 1,714 (**+1.4%**) | 1,708 (+1.0%) | ±5% ✓ |
| win rate | 33.0% | 32.5% (**−0.5 pt**) | 33.7% | ±3 pts ✓ |
| total pips | −346.5 | −453.1 (**1.31×**) | −342.1 (0.99×) | sign + 0.5×–2× ✓ |
| wall-clock overlaps | — | 0 | 0 | 0 ✓ |

`sl=10/tp=20` clears **every** §6 tolerance, so that's what the test asserts.

## Why the trade count matches (the important part)

Across the whole **25-cell `sl × tp` sweep** the trade count stays in
**1,700–1,733** — never more than ~2.5% off baseline. Trade count is set by the
**crossover count**, not by SL/TP. `crossover(sma20, sma50)` on the real 5m bars
emits 1,719 rising edges; 1,714 become trades (the 5 lost are edges with no `t+1`
bar, or an edge landing inside a still-open trade after a non-reversing exit).

That the count is right *regardless of SL/TP* is the strongest evidence the
signal generation, t+1 entry timing, and reversal chain reproduce the prototype.

## The pip gap at `sl=10/tp=20` (−453 vs −346) — chased, and benign

Three hypotheses tested in the notebook:

1. **Spread accounting.** Total spread paid at entries = 544.7 pips (mean 0.32
   pips/trade). The gap is only −106.6 pips, so it's *not* "the prototype charged
   no spread". Spread is charged correctly — long enters at `ask_open`, exits at
   `bid`; SL/TP levels are relative to the actual fill so an `sl` trade is exactly
   −10 and a `tp` exactly +20; the spread bite is on the `opposite_signal`
   round-trips only.

2. **Coarser fill resolution ("assume SL first" on 5m OHLC).** **Falsified.** Of
   the 271 `tp` trades, **0** would be re-classified as `sl` under the prototype's
   5m-bar "if the bar spanned both, SL wins" rule. Our 1s-path resolution is not
   producing systematically different SL/TP outcomes.

3. **Wrong parameters.** **This is it.** A fitted cell reproduces the baseline
   within ~1% on all three metrics:
   - `mid, sl≈8, tp≈15` → 1,708 / 33.7% / −342.1 (joint distance 0.026)
   - `bid, sl≈12, tp≈30` → 1,690 / 32.3% / −342.4 (0.024)
   - `ask, sl≈12, tp≈20` → 1,707 / 34.0% / −346.4 (0.031)

   The pips figure is genuinely sensitive to SL in the 7–12 range (small SL
   changes flip trades between `sl` losses and `opposite_signal` outcomes), which
   is why an arbitrary `10/20` lands 1.3× off while `8/15` lands on the nose.

**Most likely cause of the raw gap:** `sl=10/tp=20` is not the prototype's
config. The prototype's edge itself is slightly negative (the `opposite_signal`
reversal round-trips average −1.44 pips, 28.6% win) — the strategy loses money,
the prototype's reversal lost money the same way, and once SL/TP is fitted the
totals agree.

## Engine note surfaced by the regression

2 of 1,714 trades are **zero-duration** — `exit_time == entry_time`, both `sl`:

| entry | dir | why |
|---|---|---|
| 2024-01-16 13:30:00 | short | a US-data-release spike; the entry second's `ask_high` blew through the stop |
| 2024-12-25 22:05:00 | long | thin Christmas re-open, same thing |

This is **correct** per §0.2 — "the entry second is exposed to its own range".
The invariant is `exit_time >= entry_time` (never *before*), and any equal-time
trade must be `sl`/`tp`. The test asserts exactly that.

## Test coverage (`test_regression.py`, 6 tests)

- trade count within 5% of 1,691
- win rate within 3 pts of 33.0%
- total pips negative; `|pips|` in 0.5×–2× of 346.5
- every trade: valid `direction`/`exit_reason`; `exit_time >= entry_time` (and
  `==` ⇒ `sl`/`tp`); `entry_time` is one bar after a crossover rising edge;
  `entry_price` == that bar's `ask_open` (long) / `bid_open` (short)
- no wall-clock overlap between consecutive trades
- a headline-numbers lock (1,714 / −453.1 / 32.5% / exit mix) so an accidental
  engine change is caught — update these *and this file* on a deliberate change
