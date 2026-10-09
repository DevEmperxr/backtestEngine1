# 093 — FTMO 1-step risk settings for the NAS100 noise-area strategy

**Date:** 2026-10-09 · script: research/regime/risk_settings_093.py
**Status:** decision rule fixed before running. User: "Pick the risk settings". Uses the 1,085 trades of the frozen
rules over 2021–2025 (089/091/092). This chooses position size, not strategy rules.

## Options (small, fixed grid)
- Challenge risk per trade: 0.5 / 0.75 / 1 / 1.5 / 2 %
- Funded risk per trade: 0.25 / 0.5 / 0.75 / 1 % (FTMO: max 1% after the first payout)
- Own daily stop: 1.2% / 2% / none (FTMO's 3% daily limit always applies)
- Payout every 10 trading days in the funded stage (withdrawal resets the max-loss floor, FTMO-confirmed); one year
  funded; fee $89; FTMO 1-step rules (+10%, 3% daily, 10% trailing EOD, best day ≤ 50%).

## Decision rule
1. Simulate every option on the five years pooled (days resampled), 2,000 attempts each.
2. Keep options whose expected $ per attempt is > 0 in **every single year** (each year's days resampled alone),
   2025 included.
3. Pick the highest pooled EV among those; if within 5% of each other, take the lower risk.
Also reported: pass rate, days to pass, chance of ending ahead of the fee, and the zero-edge twin.

## Results (grid.csv, results.json, risk_settings.png)
- 60 options; the 8 with challenge risk 1.5–2% and a 1.2% own daily stop can never open a trade (one stop > the daily
  stop), so 52 valid. **All 52 have positive expected $ in every single year**, so step 2 removes nothing else.
- Funded risk: 1% (the FTMO maximum) is best in every row. Challenge risk 0.5–1% gives the highest EV
  (~$1,400–1,630); 1.5–2% passes faster (22–33 trading days) but the pass rate falls to 50–62% and EV to $600–1,300.
- Own daily stop: small effect.

| challenge | funded | own day stop | pass | EV per attempt | ahead of fee | trading days to pass | to 1st payout | EV in 2025 |
|---|---|---|---|---|---|---|---|---|
| 0.75% | 1% | 1.2% | 79% | **$1,632** (top) | 74% | 91 | 114 | $299 |
| 1% | 1% | 2% | 74% | $1,573 | 69% | **60** | 79 | $290 |
| **0.5%** | **1%** | **2%** | 72% | $1,557 | 67% | 131 | 153 | $293 |
| 1.5% | 1% | 2% | 62% | $1,298 | 57% | 33 | 52 | $243 |
| 2% | 1% | 2% | 50% | $964 | 46% | 23 | 41 | $197 |
Zero-edge twin at the pick: pass 25%, EV $106.

**Pick by the pre-registered rule** (within 5% of the top -> lowest risk): **challenge 0.5%, funded 1%, own daily stop
2%.** The three options within 5% (0.5 / 0.75 / 1% challenge) are equal within simulation noise; they differ mainly in
speed: 131 vs 91 vs 60 trading days to pass. The tie-break chose the slowest. Given the user's earlier priority
("it takes way too much time to pass"), the 1% / 1% / 2% option is the same value and twice as fast -> offered to the
user as the alternative; the user decides.
