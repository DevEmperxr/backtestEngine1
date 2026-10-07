# 061 — Confirmation layer at the previous day's high / low: rejection vs acceptance, 2023 + 2024

**Date:** 2026-10-07 · script: research/regime/confirm_prev_day_061.py · **Status:** done. Nothing carried forward; the previous-day-level POI is dropped
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
results.json. Success = price moved ~0.25 × daily ATR (~20 pips) in the expected direction first (chance 50%).

| EUR+GBP | 2023 | 2024 | both (p) | move after 60 / 240 min (pips, expected dir.) |
|---|---|---|---|---|
| London, 5 min, rejection | 52.3% | 41.9% | 47.1% (0.59) | +0.3 / +0.4 |
| London, 5 min, acceptance | 47.3% | 43.8% | 45.6% (0.38) | −2.3 / −1.6 |
| London, 15 min, rejection | 51.0% | 56.9% | 54.0% (0.42) | −0.1 / +1.7 |
| London, 15 min, acceptance | 50.9% | 50.0% | 50.6% (0.92) | −0.7 / +1.5 |
| NY, 5 min, rejection | 49.0% | 45.0% | 47.2% (0.60) | −2.9 / −2.9 |
| NY, 5 min, acceptance | 26.0% | 63.6% | 43.6% (0.22) | +1.6 / −1.1 |
| NY, 15 min, rejection | 43.4% | 41.2% | 42.5% (0.16) | −5.7 / −3.1 |
| NY, 15 min, acceptance | 46.7% | 41.3% | 44.0% (0.25) | 0.0 / −0.2 |

About 40–55 resolved cases per cell per year, so differences of a few points are noise.

**Verdict:** none of the 8 combinations comes close to the bar (≥ 55% both years, p < 0.006). Neither a
failed sweep (rejection) nor a held break (acceptance) tells us where price goes next, in London or New York,
on 1m closes after 5 or 15 minutes. With 060, the previous day's high/low **as a POI is dropped**: the stops
there get hit, but what happens afterwards is a coin flip.
(Small, not significant: NY rejections tended to fail, i.e. price went on through the level anyway, 42–47%.)

