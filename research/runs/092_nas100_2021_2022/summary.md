# 092 — NAS100 noise-area momentum (079 rules, frozen) on 2021 + 2022: second out-of-sample test

**Date:** 2026-10-09 · strategy: research/strategies/089_noise_area_indices.py `make_nas100_2122` · analysis:
research/regime/nas2122_092.py
**Status:** pre-registered BEFORE any 2021/2022 price data is used. User: "do 2021 and 2022" (reserved years named
explicitly; first and only use for this idea). 2026 untouched.

## Rules
Exactly 079 / 091. Noise table from NAS100 2021+2022 joined (first 14 sessions of 2021 skipped: no earlier data).
News: ForexFactory USD red ±2 min (file covers both years). FTMO index costs. Note: 2022 was a bear market (Nasdaq
about −33%), 2021 a bull market.

## Pass (same bar as 079 / 091)
Pooled 2021+2022, after all FTMO costs: **R per trade ≥ +0.05** and the FTMO 1-step scorecard beats its zero-edge
twin. Reported: each year, long vs short, before costs, the always-long twin.

## Results (lookahead audits clean; charts nas100_2021_2022.png, nas100_five_years.png)
| | trades | R/trade after costs | 95% CI | win % | always-long twin |
|---|---|---|---|---|---|
| 2021 (bull) | 214 | **+0.144** | −0.02 … +0.33 | 41 | +0.100 |
| 2022 (bear) | 252 | **+0.143** | +0.01 … +0.29 | 41 | +0.018 |
| **2021+2022** | 466 | **+0.143** | **+0.04 … +0.26** | 41 | +0.056 |
- Before costs +0.166R; costs 0.022R. Long +0.237R, short +0.061R (2022: long +0.20, short +0.10).
- FTMO 1-step (2021–22 trades, 1% risk): pass 85%, EV +$2,589 per attempt (~53 days to pass) vs zero-edge twin 52% /
  +$510.
- **Verdict (pre-registered): PASS.** Both unseen years match the in-sample edge (+0.133).

### All five years, identical rules
| 2021 | 2022 | 2023 | 2024 | 2025 | all (1,085 trades) |
|---|---|---|---|---|---|
| +0.144 | +0.143 | +0.135 | +0.131 | +0.045 | **+0.120R/trade, CI +0.05 … +0.20, +130.7R** |
Three of the five years were never used to build or tune the rules (2021, 2022, 2025). 2025 is the weakest year
(narrow fail of its own test, 091); every other year is ~+0.14. The direction choice beat being long in 4 of 5
years (equal in 2023).
