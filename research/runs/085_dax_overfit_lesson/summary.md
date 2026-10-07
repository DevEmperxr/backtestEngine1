# 085 — DELIBERATE OVERFIT (learning exercise): why 084 a/b failed on GER40 2023

**Date:** 2026-10-07 · script: research/regime/overfit_085.py · charts grid_a.png, grid_b.png, overfit_lesson.png
**Status:** user-approved ONE-OFF over-fit on GER40 2023 "just so that I can understand what is going on, and then we
will never do that again". **Nothing here is evidence; no config from here may be carried to 2024 as a candidate.**
2024 not touched. Re-simulation of 084 exits matches the engine (a −0.09 vs −0.11R, b −0.052 vs −0.053R).

## Why it failed
- **a (fade first 30 min):** with no stop, held 09:30 -> 17:25: +9.3 pts/trade, 50% wins, t 1.45 — a weak lean, not
  an edge. The 16-pt stops were hit on 201/245 trades; **41% of those would have been right by 17:25.** The stop sat
  inside the open's normal noise (~6 pts per minute).
- **b (first-hour false break):** no stop, hold to 17:25: +0.2 pts/trade (t 0.03). There is simply nothing there;
  every stop/exit cell is ~0.

## What over-fitting found (a, full 2023)
- Stop × exit grid: the best cell (stop 20, exit 17:25) gives +0.21R; 10 pts gives −0.03R, 15 pts +0.11R, 150 pts
  +0.05R. Results jump around between neighbouring cells — a sign of noise.
- Filters "explain" the winners: large first-30 moves +0.11R vs small 0.01; longs +0.12 vs shorts −0.01 (2023 rose:
  fading a down-open = buying a dip in a bull year); Wednesday −0.15R vs other days +0.04…+0.15 (meaningless).

## The lesson: choose on Jan–Jun, check Jul–Dec (968 configs)
- Best on H1: stop 20, exit 17:25, "first-30 move large": **+0.85R per trade in H1 -> −0.06R in H2.**
- Its H1 profit was mostly 2 days: **17 and 20 March 2023 (Credit Suisse / SVB banking stress), +18R each.** Without
  its top 3 days, H1 was −19.7R.
- Top 10 configs on H1 average +0.07R in H2; all configs −0.01R; H1-vs-H2 correlation across configs 0.22.
  Selection inflated the edge ~8-10x; what survives is close to nothing.
