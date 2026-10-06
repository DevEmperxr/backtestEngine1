# 035 — Replication on 2024: Idea 1 fades in the first 2 h after the London open, 1h sideways

**Date:** 2026-10-06
**Files:** research/strategies/034_idea1_lon_ny.py (unchanged); results in research/runs/034_idea1_lon_ny/ (2024 run)
**Status:** direction holds (not a full replication); live lead

## Hypothesis (from 034, registered before the 2024 run)
In 2023, Idea 1 (023A rules, window 08:00 London → 16:00 NY) fades **entered 03:00–04:59 New York
(the first two hours after the London open) with the 1h sideways** made **+320.5 pips on 207
trades**. Found post hoc among 39 hour × context slices. When the 1h is going nowhere, the
London-open push overshoots, sweeps a level, and comes back.

## Test (fixed now)
- Run the 034 strategy **unchanged** on **EURUSD 2024** (2024 has never been run with this wider window).
- Take exactly the same slice: entry hour (New York) ∈ {03, 04} and 1h context = sideways. Same
  sequencing and management as in 2023 (one position at a time over the whole window; flat
  16:00 NY).
- **Single pre-specified test on unseen data:** "replicates" if the slice's net pips > 0 **and**
  its per-trade 95% bootstrap CI excludes 0. "Direction holds" if net > 0 but the CI includes 0.
  "Fails" if net ≤ 0.
- Report the 2023 + 2024 combined figures and charts too (equity + monthly for the slice).

## Results
EURUSD; 2024 audit passed (1,747 trades, 0 failures). Charts: [2024 slice](slice_2024.png),
[2023 + 2024](slice_2023_2024.png).

| slice: entries 03:00–04:59 NY, 1h sideways | trades | net | per trade | 95% CI | win | gross |
|---|---|---|---|---|---|---|
| 2023 (discovery) | 207 | +320.5 | +1.55 | [+0.22, +2.90] | 50.7% | +382.6 |
| **2024 (test)** | **225** | **+140.0** | **+0.62** | **[−0.39, +1.64]** | 47.1% | +189.9 |
| both (descriptive) | 432 | +460.4 | +1.07 | [+0.23, +1.90] | 48.8% | +572.5 |

2024 by hour: 03 NY +129.3 (121 trades), 04 NY +10.6 (104). The whole 2024 wider-window run: trending
+100.9, against −230.6, sideways +347.0, all +217.3 (2023: −819.3).

## Interpretation
**Direction holds; not a full replication.** On unseen 2024 the slice made money again (+140 pips on
225 trades, positive before costs too), but the per-trade CI includes zero, so by the registered rule
this is "direction holds", not "replicates". The edge per trade fell from +1.55 (discovery) to +0.62
(test): the usual shrinkage of a pattern found by slicing. Whatever is real is probably well under
1 pip/trade. The first hour after the London open (03:00 NY) carried most of it in both years.

Caution: the whole wider-window run swung from −819 (2023) to +217 (2024), and its sideways
part from −407 to +347. Year-to-year swings of that size mean single-year results for this family
are noisy.

## Decision
**Keep as a live lead ("London-open sideways fade"), not confirmed.** Next fair checks without
touching reserved data: other pairs' 2023 + 2024 as they download (needs JPY support for the yen
crosses). EURGBP 2023/2024 were used for Idea 1 before, but never with this window and slice, so
they are a usable check too. Rules must stay exactly as here.
