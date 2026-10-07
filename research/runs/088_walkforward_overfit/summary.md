# 088 — Walk-forward test of "over-fit month by month" (user's method), GER40 2023 only

**Date:** 2026-10-07 · script: research/regime/walkforward_088.py
**Status:** pre-registered before running. User: "overfit month by month and then compare... will this method work
or is it a fallacy?" -> "yes run it but only on 2023".

## Method (fixed now)
- Same setup menu as 087 (Context × Bias × POI level/side/window × Confirmation × stop; 3R target; one trade a day;
  exit 17:25; FTMO costs). News: **EUR + USD** red news ±2 min (087 lesson).
- Each month m: rank every setup by its number of 3R wins over the previous L months (tie-break total R; needs
  ≥ 10 trades per lookback month), pick #1, trade it UNCHANGED in month m. Only information before month m is used.
- Two versions, both reported: **L = 1** (Feb–Dec traded) and **L = 3** (Apr–Dec traded).
- Judge only the stitched next-month trades. Baseline: the average next-month result of all eligible setups (= a random
  pick). Also: where the pick ranks in its next month (percentile; 50 = no better than random).

## Reading (fixed now)
**The method shows something** if, for both L: stitched R per trade after costs > 0, 3R hit rate > 25%, the pick's
average next-month percentile > 60, and the FTMO 1-step scorecard beats its zero-edge twin. Otherwise: over-fitting
month by month does not carry forward (the fallacy).

## Results (~100k setups re-ranked every month; chart walkforward.png; picks in results.json)
| | months | trades | R/trade when chosen | **R/trade next month (traded)** | 3R hit | random pick | pick's next-month percentile | FTMO 1-step (twin) |
|---|---|---|---|---|---|---|---|---|
| L = 1 month | 11 | 196 | +1.10 | **−0.135** | 19.9% | −0.10 | 44.9 | 18% / −$19 (35% / $204) |
| L = 3 months | 9 | 177 | +0.61 | **+0.011** | 23.2% | −0.10 | 55.4 | 40% / $239 (34% / $191) |

**Verdict (pre-registered): the method does not work.** The pick looked like +0.6…+1.1R per trade on the months it
was chosen on and made −0.14 (1-month lookback) or ~0 (3-month lookback) the next month. With a 1-month lookback the
pick did WORSE than a random setup (percentile 45). The 3-month lookback is about break-even (above the −0.10
average setup, which is the cost drag), not an edge. The month-to-month "best setup" kept changing (11 different
picks); explaining each change would have been explaining noise.
