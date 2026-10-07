# 067 — Clean check: the London fade under FTMO rules on unseen EURUSD 2025 (+ 2021–22 under the new rules)

**Date:** 2026-10-07 · strategy: research/strategies/066_ftmo_reruns.py `make_london_fade` (046 rules, ±2 min news)
· run with `run_experiment --prop` · analysis: research/regime/clean_check_067.py
**Status:** pre-registered. User asked for the clean check ("do 1 and 2").

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
_(filled after the run)_
