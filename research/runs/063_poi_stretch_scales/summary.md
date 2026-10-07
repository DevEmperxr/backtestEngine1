# 063 — POI study: the stretch from the mean at three scales (5m / 15m / 1h), London open, 2023 + 2024

**Date:** 2026-10-07 · script: research/regime/poi_stretch_063.py · **Status:** done. No scale passes the POI layer
Template layer: **3 — POI only.** Rebuilding the London fade (046) layer by layer at bigger scales; 046's
context (1h sideways) and confirmation (1m sweep) are switched OFF here.

## 0. Who loses, and why
Traders who chase a fast move away from the short-term average at the London open (late breakout buyers/sellers
and stop-runs that overshoot) get caught when price returns toward fair value as liquidity refills: the
stretch-and-snap-back that 046 found (target hit first 49% vs 39% chance on EURUSD 2023–24; smaller on other
years/pairs). Question: does the snap-back exist at bigger scales, where trades are large enough for prop-firm costs?

## 3. POI (fixed now)
- Scales TF ∈ {**5m, 15m, 1h**}: SMA20 and ATR14 of mid prices on TF bars (built from 1m mids), taken from the
  **last closed** TF bar.
- Bands: SMA20 ± **2 × ATR14** (as 046).
- Event: the first 1m bar in the window whose mid high reaches the upper band (or low reaches the lower band);
  at most one up-stretch and one down-stretch event per day per scale.
- Window: **08:00–10:00 London** (the 046 London-open window), weekdays.
- Measured from the event bar's close. Expected direction = back toward the SMA.

## Outcomes
1. **Symmetric race (primary):** 1 × ATR(TF) toward the mean vs 1 × ATR(TF) away; chance 50%. Horizon: 5m 2 h,
   15m 4 h, 1h 8 h. Ties/unresolved excluded.
2. **Trade-shape bracket:** target = distance to the SMA at the event; stop = 1.5 × ATR(TF) beyond the event
   close. Success rate vs the random-walk chance rate stop / (stop + target) (computed per event, averaged).
Also reported: median target size in pips, mean move after 30 / 60 / 120 min toward the mean.

## Carry-forward rule
3 tests (one per scale). A scale goes to the next layer if, for **EURUSD + GBPUSD pooled**, the symmetric race is
**≥ 55% in both 2023 and 2024** and the pooled two-sided binomial p < **0.017** (0.05 / 3). AUDUSD reported as a check.

## Next layers (only for scales that pass)
4 confirmation (sweep on the next-lower timeframe) -> 1 context (higher-TF sideways) -> 2 bias -> 5 execution with
prop-firm costs. Each kept only if it improves both practice years.

## Results
results.json, events.parquet.

| EUR+GBP | symmetric race 2023 | 2024 | both (p) | trade-shape: reach the mean before 1.5 ATR stop vs chance | typical ATR / target | move toward mean after 60 min |
|---|---|---|---|---|---|---|
| **5m** | 52.3% (n 681) | 51.0% (n 698) | 51.6% (0.23) | **44.1% vs 41.9%** (+2.2 pts) | 4.4 / 9.3 pips | +0.4 pips |
| **15m** | 47.8% (n 527) | 51.6% (n 535) | 49.7% (0.85) | 40.6% vs 40.5% | 5.4 / 11.8 pips | +0.3 pips |
| **1h** | 54.2% (n 378) | 51.9% (n 372) | 53.1% (0.09) | 41.0% vs 40.5% | 9.2 / 20.3 pips | +0.9 pips |

AUDUSD symmetric race: 5m 50.0%, 15m 55.1%, 1h 51.4%.

**Verdict:** none of the three scales passes (≥ 55% both years, p < 0.017). The stretch **on its own** is close
to a coin flip at every scale:
- **5m:** a small snap-back remains in the trade shape (+2 points over chance), the same size as 046 showed on
  unseen years. In 046 (EURUSD 2023–24) the gap was +10 points, so most of that came from the other two
  layers (the 1m sweep confirmation and the 1h-sideways context) plus luck.
- **15m:** no snap-back at all. 053 (15m stretch + 5m sweep + 4h context) was also below chance, so adding
  layers didn't rescue this scale either.
- **1h:** the strongest of the three on the symmetric race (53%, both years above 50%), but not significant,
  and the trade shape is exactly at chance.

**Where it breaks:** the snap-back is a **short-scale effect** (the 1m–5m reaction at the London open). It
fades as the scale grows, so it can't simply be scaled up to 20+ pip targets.

