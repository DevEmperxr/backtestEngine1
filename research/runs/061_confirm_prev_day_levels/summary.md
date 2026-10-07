# 061 — Confirmation layer at the previous day's high / low: rejection vs acceptance, 2023 + 2024

**Date:** 2026-10-07 · script: research/regime/confirm_prev_day_061.py · **Status:** pre-registered (descriptive)
Template layer: **4 — Confirmation** on the 060 POI (first touch of the previous FX day's high/low in the London
morning 07–11 London and the NY morning 08–11 NY). Same events, same data (EURUSD, GBPUSD; AUDUSD as a check).

## 0. Who loses (refined)
- **Rejection:** the stops beyond the level were absorbed and price came back inside: the breakout buyers
  (and those stopped out at the extreme) are trapped; price should turn back.
- **Acceptance:** price stays beyond the level: the stops cascaded and the faders are trapped; price should
  continue.

## 4. Confirmation (fixed now)
Decision point = the touch bar's close + **D minutes**, D = **5** (fast) or **15** (slower).
- **Rejection:** the 1m mid close at the decision point is back inside the previous day's range
  (below the previous high / above the previous low). Expected: reversal.
- **Acceptance:** the close at the decision point is still beyond the level. Expected: continuation.
Every event gets exactly one label per D.

## Outcome (fixed now)
From the decision point's close: race of X = **0.25 × daily ATR(20)** in the expected direction vs X the other
way, within 4 hours (primary); X = 0.5 × ATR reported. Ties and unresolved races are excluded from the rate.
Also the mean move after 60 / 240 minutes in the expected direction (pips, mid, before costs).

## Carry-forward rule
8 combinations (2 windows × 2 labels × 2 speeds). A combination is carried forward to the next layer only if,
for **EURUSD + GBPUSD pooled**, the success rate (expected direction first) at X = 0.25 ATR is **≥ 55% in both
2023 and 2024** and the pooled two-sided binomial p < **0.006** (0.05 / 8).

## Results
_(filled after the run)_
