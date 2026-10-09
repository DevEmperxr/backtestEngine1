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

## Addendum (2026-10-09): has the edge decayed since publication?
User: "it seems like the edge disappeared or slowed in 2025 after being published". The paper (SSRN 4824172, SFI 24-97)
was first posted around May 2024 (a revision is dated Nov 2024).
- Before June 2024: 754 trades, +0.140R/trade. After: 331 trades, +0.077R/trade (about half). Difference 0.063R,
  standard error ~0.08 -> not distinguishable from noise either way. Half-years after posting: 2024-H2 +0.207 (best of
  all ten), 2025-H1 +0.101, 2025-H2 −0.007 (the only negative half). Earlier weak halves: 2021-H2 +0.033, 2024-H1 +0.055.
- Literature prior: published anomalies lose about half their return after publication on average (McLean & Pontiff
  2016), so planning for a smaller edge is prudent.
- FTMO 1-step value if the true edge is smaller (same trade shape, funded 1%, own stop 2%):
  | edge R/trade | challenge 0.5%: pass / EV | challenge 1%: pass / EV |
  |---|---|---|
  | +0.12 | 72% / $1,546 | 74% / $1,563 |
  | +0.09 | 61% / $1,009 | 67% / $1,088 |
  | +0.06 | 48% / $598 | 57% / $710 |
  | +0.03 | 34% / $314 | 48% / $453 |
  | 0.00 | 24% / $138 | 39% / $269 |
  The 1% challenge setting is better at every edge size, more so as the edge shrinks -> robust to decay.
