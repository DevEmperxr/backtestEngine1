# 063 — POI study: the stretch from the mean at three scales (5m / 15m / 1h), London open, 2023 + 2024

**Date:** 2026-10-07 · script: research/regime/poi_stretch_063.py · **Status:** pre-registered (descriptive)
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
_(filled after the run)_
