# 071 — How to pass FTMO 1-step faster (modelling)

**Date:** 2026-10-07 · simulator: lib/prop_firms.py (FTMO_1STEP, $5 commission) · results.json, speed_vs_risk.png
**Status:** done. User question: "it takes way too much time to pass an account, what can we do to make it faster?"

## Method
London-fade trade shape (2023–24, ~6-pip stops), average edge before commission 0 or +0.05R (after FTMO's $5 commission
≈ −0.08 / −0.03R per trade). Risk per trade 0.5–2%; trades per day 1× / 2× / 3× (≈ running 1–3 independent
strategies: each simulated day = k random real days back to back). No own daily stop (only FTMO's 3%, never a trade
that could breach it). 600 attempts each; 260-day cap per phase.

## Results (1× ≈ 0.8 trades a day)
| risk | edge 0: pass / days to pass / days to money > fee / $ per attempt | edge +0.05R: same |
|---|---|---|
| 0.5% | 35% / 146 / 177 / +$146 | 41% / 148 / 175 / +$263 |
| 1.0% | 36% / 48 / 69 / +$224 | 40% / 53 / 80 / +$296 |
| 1.5% | 42% / 30 / 52 / +$307 | 43% / 30 / 52 / +$285 |
| **2.0%** | **43% / 17 / 40 / +$302** | **46% / 19 / 38 / +$340** |

More trades per day (2× / 3×) cut the calendar days, but **lowered** pass rates and $ per attempt at these edges
(e.g. edge 0, 1% risk: 36% -> 11% -> 8%), because after commission the average trade is slightly negative: more
trades just let the small loss pile up faster (accounts drift down to the loss floor and stall).

## Takeaways
1. **Risk per trade is the main speed lever.** Going from 1% to 2% cut the median time to pass from ~50 to ~18
   trading days, and money in hand from ~70–80 to ~40 days, **without lowering the pass rate** (it rose).
   When the edge after costs is ~zero or slightly negative, bigger bets are better ("bold play"): fewer trades means
   less time for costs to grind the account down.
2. **The 3% daily limit is the ceiling:** at 2% risk only one losing trade fits in a day; above that, one loss
   could breach it.
3. **More trades per day only helps with a real positive edge after costs.** Otherwise it speeds up the losses.
4. **Once funded, lower the risk** (e.g. 0.5–1%): the account then has to survive to keep paying.
5. If a strategy has a real edge after costs, lower risk becomes better for the pass rate (but slower): re-run this
   with the actual strategy's trades before choosing the risk.
