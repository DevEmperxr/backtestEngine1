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

## Results
_(filled after the run)_
