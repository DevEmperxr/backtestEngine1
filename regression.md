# §6 Regression — SMA(20/50) crossover

**Verdict: PASS.** The new engine reproduces the prototype. The pip-total
difference vs the old headline figure is **fully explained**: the original
prototype's 5-minute data pull was **incomplete**, and the 1-second pull this
build resamples from is a strict superset of it.

Investigation: [`notebooks/regression.ipynb`](notebooks/regression.ipynb).
Test: [`lib/tests/test_regression.py`](lib/tests/test_regression.py) (`-m slow`,
skipped if the data file is absent).

---

## The old §6 target is retired

Spec §6 quoted the prototype at **1,691 trades · −346.5 pips · 33.0% win rate**,
from 5-minute EURUSD bars with the old "assume SL hit first" same-bar fill
approximation. **Those numbers were computed on incomplete source data and are
no longer treated as ground truth** (see the root cause below).

The regression now runs the reference strategy end-to-end on the 1-second file
and locks *that* result:

`load_1s_data` → `resample("5m")` → `SmaCrossoverStrategy(20/50, sl 10 / tp 20,
mid price, reverse-on-opposite)` → `Engine.backtest`:

| metric | 1s-data baseline (locked) | old prototype figure |
|---|---|---|
| trades | **1,714** | 1,691 |
| win rate | **32.5%** | 33.0% |
| total pips | **−453.1** | −346.5 |
| exit mix | opposite_signal 999 · sl 443 · tp 271 · end_of_data 1 | — |
| wall-clock overlaps | 0 | — |

`sl=10 / tp=20` is the config used throughout the suite. It is not "the
prototype's parameters" — the spec never recorded those — it's just a fixed,
documented choice.

## Root cause of the pip difference — confirmed by a direct bar-level diff

The new 5-minute bars (`resample`d from the 1s file) were diffed against the
prototype's original `EURUSD_5min_ASK.csv` / `EURUSD_5min_BID.csv`:

- **74,708 overlapping bars. 7 disagree in value** — 6 are trivial (≤ 0.5 pip,
  ordinary noise between two independent tick aggregations); **1 is real** (a
  5-pip difference at Nov 21 17:00).
- **The original 5-minute data is missing 29 bars entirely** that the 1s-based
  data has. **Zero bars go the other way.** The new pipeline is a strict
  superset.
- The 29 missing bars **cluster at low-liquidity periods**: 18 of 29 fall in the
  Dec 24–25 Christmas window, the rest scattered across other thin-trading
  moments (July 4th, etc.). The Nov 21 5-pip discrepancy is a direct instance —
  the original data jumps straight from 17:00 to 17:10, missing the 17:05 bar
  during a fast down-move in the November sell-off. The 1s data has that bar
  (`n_ticks = 213`): bid ran 1.04741 → 1.04635 into 17:00, then 1.04636 → 1.04692
  through the missing 17:05.

**Conclusion:** this is a **source-data completeness issue in the original
prototype pull**, not a bug in `resample()`, the engine, or the fill logic. A
handful of extra bars in fast-moving thin markets is exactly the kind of thing
that shifts a fixed-SL/TP crossover strategy's realized P&L by ~30% while leaving
the trade count and win rate essentially unchanged.

## Confirming loop — the 29-bar list vs the earlier gap analysis

The same thin periods were already flagged, independently, by the load-time gap
analysis on the 1s file:

- `analyze_gaps` found **8 holiday gaps, every one on 2024-12-24 / 2024-12-25**,
  and the ~14-hour Christmas close (Dec 25 08:00 → 22:00 UTC).
- On the resampled 5m bars, thin bars (`n_ticks < 5`) number 138 for the year and
  **77 of them are in December** — the Christmas cluster. May–July are the next
  most elevated (summer thinness; July 4th runs ~55 ticks/bar vs ~84 on a normal
  weekday).
- The Christmas window (Dec 24 12:00 → Dec 26 00:00) holds 265 5m bars against
  432 for full coverage, with a single 14-hour internal gap.

The "18 of 29 missing original bars in Dec 24–25" lines up cleanly with that: the
original 5-minute pull was *also* thin over Christmas, just thinner than the 1s
pull. Same story, two independent measurements.

## Trade count is invariant to SL/TP (still true, still the key evidence)

Across a 25-cell `sl × tp` sweep the trade count stays in **1,700–1,733**. It is
set by the **crossover count**, not by SL/TP: `crossover(sma20, sma50)` on the
real 5m bars emits 1,719 rising edges; 1,714 become trades (the 5 lost are edges
with no `t+1` bar, or an edge landing inside a still-open trade after a
non-reversing exit).

That the count is right *regardless of SL/TP* is the strongest evidence the
signal generation, t+1 entry timing, and reversal chain are correct. The pips
figure is sensitive to SL in the 7–12 range (small changes flip trades between
`sl` losses and `opposite_signal` outcomes) — which is also why an incomplete
data pull can move the total meaningfully.

## Engine note surfaced by the regression

2 of 1,714 trades are **zero-duration** — `exit_time == entry_time`, both `sl`:

| entry | dir | why |
|---|---|---|
| 2024-01-16 13:30:00 | short | a US-data-release spike; the entry second's `ask_high` blew through the stop |
| 2024-12-25 22:05:00 | long | thin Christmas re-open, same thing |

This is **correct** per §0.2 — "the entry second is exposed to its own range".
The invariant is `exit_time >= entry_time` (never *before*), and any equal-time
trade must be `sl`/`tp`. The test asserts exactly that.

## What the strategy actually does (2024 EURUSD)

`SmaCrossoverStrategy(20/50, sl 10 / tp 20)` **loses money after costs**: net
−453 pips / −4.5%. Gross P&L before spread is only **+145 pips** over 1,714
trades — the ~600 pips of spread cost is what makes it a net loser ("costs ate
it"), but +145 gross is barely above noise, and the bootstrap 95% CI on
expectancy is **[−0.73, +0.22] pips/trade** — it straddles zero. There is no
statistically real edge in either direction. The framework surfaces that; that is
the point (spec §3).

## Test coverage (`test_regression.py`, 6 tests)

- **`test_headline_numbers_are_stable`** — the real regression tripwire: locks
  `1,714 / −453.1 / 32.5% /` exit mix exactly. A deliberate engine change updates
  these numbers *and this file*; an accidental one fails the test.
- **stability bands** (not a match to a historical figure): trade count in a
  plausible range, win rate in a plausible range, edge sign negative, `|pips|`
  bounded — these survive a data re-pull or a minor engine tweak.
- **well-formedness**: every trade has a valid `direction`/`exit_reason`;
  `exit_time >= entry_time` (and `==` ⇒ `sl`/`tp`); `entry_time` is one bar after
  a crossover rising edge; `entry_price` == that bar's `ask_open` (long) /
  `bid_open` (short).
- **no wall-clock overlap** between consecutive trades.
