# 023 — Idea 1 reworked: (A) 1m sweep with a 5m-noise-sized stop, (B) sweep on the 5m (2023)

**Date:** 2026-10-06
**File:** research/strategies/023_sweep_fade_rework.py (make_a, make_b)
**Status:** A carried forward (not passed); B discarded

## In plain words
022 failed because the stop just above a 1m sweep (≈2.8 pips) sits inside normal 1m noise:
most trades were stopped within minutes. Two fixes, tested as separate trials:
- **A:** same 1m sweep entry, but stop = **1.5 × the 5m ATR** from the entry (about one normal
  5m candle).
- **B:** the sweep is on **5m candles**: a stretched 5m candle pokes above (below) the latest
  confirmed 5m swing high (low) and closes back inside; enter at the next 5m open; stop 1 pip
  beyond that 5m candle.

## Hypothesis
*(registered before any 023 trade was simulated; data-informed by 022's result, so these
are trials 2 and 3 of Idea 1 on 2023)*

If the 022 idea was right but its stop was too tight, giving the trade room for normal 5m
noise (A), or reading the sweep on the 5m where its stop is naturally wider (B), should
turn the primary context positive and lift the TP-first rate above the random null.

## Rules (fixed now; everything not listed is identical to 022)
- 1h context (ER20 ≥ 0.32 and slope of the 1h SMA20), 5m SMA20 and ATR14, stretch 2·ATR, target
  = 5m SMA20, window 07:00 NY → 16:00 London, flat 16:00 London: **as 022**.
- **A:** signal frame 1m; 1m sweep of the latest confirmed 1m swing (3 bars each side), exactly as
  022. **Stop = 1.5 × ATR14 of the last closed 5m bar**, from the signal close.
- **B:** signal frame **5m**. Stretch: the 5m bar's high ≥ its SMA20 + 2·ATR14 (low ≤ SMA20 −
  2·ATR14), using that bar's own SMA/ATR (known at its close). Swing: highest (lowest) of
  7 5m bars centred on it, usable only 3 bars later and only from the next bar on. Sweep:
  high > latest confirmed 5m swing high and close < it (mirror for longs). Entry next 5m open.
  **Stop = 1 pip beyond the 5m sweep bar's extreme.** Target = the 5m SMA20 at the signal bar;
  skip if price is already beyond it.
- Primary = "trending, stretch with the trend"; trend_against and sideways reported too.

## Evaluation (fixed now; as 022)
- Full suite; H1/H2; spread-adjusted null; context table.
- **Pass (dev year):** primary 95% CI excludes 0 AND both halves positive AND TP-first ≥ 2 SE
  above the null. A pass means "confirm on other years", nothing more.
- Comparison with 022's primary (−0.30 pips/trade, TP-first 16.4% vs 18.0%).
- Audits as 022 (sweep and stretch re-derived in plain Python on 1s-rebuilt bars, swings with
  their confirmation delay, on the signal timeframe); A: stop = 1.5 × 5m ATR checked.

## Results
2023. All audits passed (A 697, B 336 trades: 0 not a sweep of a confirmed swing, 0 not at the
stretch, 0 ATR-stop mismatches). [a_2023](a_2023/), [b_2023](b_2023/).

| | context | trades | net | exp/trade | 95% CI | win | gross | H1 / H2 | TP-first vs null |
|---|---|---|---|---|---|---|---|---|---|
| **A** | **trend_with (primary)** | 142 | **+56.7** | +0.40 | [−1.34, +2.15] | 47.2% | +99.3 | +26.2 / +30.5 | 43.5% vs 37.2% (z +1.39) |
| A | trend_against | 74 | −57.1 | −0.77 | [−2.86, +1.37] | 40.5% | −33.4 | −27.1 / −30.0 | 36.9% vs 41.9% |
| A | sideways | 481 | **−509.8** | −1.06 | **[−1.94, −0.18]** | 38.7% | −359.4 | −303.1 / −206.7 | 34.6% vs 38.0% |
| A | all | 697 | −510.2 | −0.73 | [−1.48, +0.02] | 40.6% | −293.5 | | 36.6% vs 38.3% |
| **B** | **trend_with (primary)** | 76 | **−83.2** | −1.09 | [−2.39, +0.24] | 34.2% | −60.6 | −68.2 / −15.0 | 30.6% vs 34.7% |
| B | trend_against | 35 | +5.8 | +0.17 | [−1.72, +2.14] | 48.6% | +15.2 | | 46.9% vs 42.9% |
| B | sideways | 225 | −129.7 | −0.58 | [−1.46, +0.33] | 40.4% | −58.2 | | 39.4% vs 42.9% |

- A primary exits: 50 TP, 65 SL, 27 time. Median stop 7.9 pips (022: 2.8), target 12.1.
- A, with-trend minus sideways (descriptive, not registered): +1.46 pips/trade, 95% CI
  [−0.41, +3.35].
- vs 022 primary (−0.30/trade, TP-first 16.4% vs 18.0%): A moves to +0.40/trade and
  6 points above the null; B is worse (−1.09).

## Interpretation
**Neither passes.** But A is the first version of Idea 1 where things move the way the idea
says they should:
1. **Wider stop helps** (022 → A): giving the trade room for normal 5m noise turned the primary
   case from −0.30 to +0.40 pips/trade. The TP-first rate is now 6 points above chance (43.5%
   vs 37.2%), positive in both halves. The sample trades show it directly: entries 022 lost in
   two minutes now reach the target.
2. **Context starts to matter:** in A, with-trend fades are positive while **sideways fades
   lose clearly** (−509.8 pips, CI excludes 0). That fits the user's idea: a stretch is an
   "overshoot" worth fading only when there is a trend for it to overshoot. In a sideways
   market the stretch is more often a breakout that keeps going.
3. **5m sweep (B) is worse:** rarer signals, tighter structure, below the null. Reading the
   sweep on the 5m doesn't help.

Caveats: 142 trades; CI [−1.34, +2.15] includes 0; z = 1.39 < 2; the context difference CI
includes 0; and this is the third trial of Idea 1 on 2023. Promising direction, not a finding.

## Decision
**A: not a pass, but the lead for Idea 1. Carry forward. B: discard.**
**Why:** A primary +56.7 pips, positive in both halves, TP-first +6 points vs null, but the CI
includes 0 and z < 2. Sideways fades are clearly negative. That suggests the 1h context, used
as a filter, does real work.
Next, if pursued: test **A restricted to with-trend context**, unchanged, **on other years**
(2021, 2022, 2024, 2025) as a pre-registered confirmation. Trend-restricted is the
registered primary already, so no new tuning is needed.
