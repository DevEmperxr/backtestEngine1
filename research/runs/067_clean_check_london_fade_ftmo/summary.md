# 067 — Clean check: the London fade under FTMO rules on unseen EURUSD 2025 (+ 2021–22 under the new rules)

**Date:** 2026-10-07 · strategy: research/strategies/066_ftmo_reruns.py `make_london_fade` (046 rules, ±2 min news)
· run with `run_experiment --prop` · analysis: research/regime/clean_check_067.py
**Status:** done. **FAIL** on unseen 2025. User asked for the clean check ("do 1 and 2").

## Data
- **EURUSD 2025 (primary, unseen by this strategy):** used before only by the fix-fade runs (016–019). The news
  calendar ends 2025-04-07, so the ±2 min window can only be applied until then; **Jan 1 – Apr 7 2025** is also
  reported on its own as the fully rule-correct part. (The fade trades 03:00–05:00 NY, where red releases are rare.)
- **EURUSD 2021 and 2022 (context, already seen in 051 under the old ±60 min rule, no commission):** rerun under
  the FTMO rules for comparison; not part of the bar.

## Unchanged rules
046 London fade: 1m sweep after a 2×ATR stretch from the 5m SMA20, entries 03:00–04:59 NY, 1h sideways (ER < 0.32),
stop 1.5 × 5m ATR, target the 5m SMA20, flat 16:00 NY; FTMO news ±2 min; prop mode ($5/lot, flat by 16:55 NY).

## Pass bar (fixed now)
On EURUSD 2025, after spread + commission:
- **PASS:** R per trade > 0 AND the FTMO 2-step pass probability at 1% risk beats the zero-edge twin's.
- **STRONG:** PASS and the bootstrap 95% CI of R per trade above 0.
- **FAIL:** R per trade ≤ 0.
Expectation (stated before running): roughly break-even, given 051 (+0.24 pips/trade before commission on 2021–22).

## Results
Engine runs: research/runs/066_ftmo_reruns/london_fade_<year>/ (audit ok). Analysis: research/regime/clean_check_067.py
-> results.json; chart equity_R_2025.png. All after spread + 0.5-pip commission.

| EURUSD | trades | net pips | gross pips | R / trade [95% CI] | win |
|---|---|---|---|---|---|
| **2025 (unseen)** | 213 | **−318.1** | −124.2 | **−0.181 [−0.34, −0.01]** | 35.7% |
| 2025 Jan 1 – Apr 7 (news filter complete) | 48 | −98.3 | −55.5 | −0.255 | 33.3% |
| 2025 Apr 8 – Dec 31 (no news data) | 165 | −219.9 | −68.7 | −0.160 | 36.4% |
| 2021 (seen in 051, context) | 237 | −85.4 | +99.0 | −0.059 | 42.2% |
| 2022 (seen in 051, context) | 213 | +83.3 | +279.1 | −0.028 | 40.4% |
| 2023 (in-sample) | 203 | +170.1 | +331.8 | +0.133 | 49.3% |
| 2024 (in-sample) | 221 | +45.5 | +203.0 | +0.063 | 47.5% |

FTMO 2-step on 2025 trades: pass 0.1% / 1.7% / 6.0% at 0.5 / 1 / 2% risk, vs its zero-edge twin 13% / 30% / 27%.

**Verdict: FAIL.** On unseen 2025 the London fade lost even before costs (gross −124 pips), and after FTMO costs
−0.18R per trade (CI entirely below 0). Under FTMO costs it is negative in 3 of the 4 non-discovery years
(2021, 2022, 2025). The 2023–24 result was largely the discovery sample. **The London fade is retired.**

