# 059 — London-open range breakout, after NR7 days (Crabel), EURUSD / GBPUSD / AUDUSD 2023 + 2024

**Date:** 2026-10-07 · file: research/strategies/059_london_orb_nr7.py · **Status:** pre-registered (user request)

## Who loses, and why
- **Traders caught against the opening move:** stops of those who faded the first half hour sit just beyond
  the opening range; when it breaks they become forced orders that push price further (stop clustering,
  Osler 2003).
- **NR7 (narrowest range of 7 days):** after a compressed day, stops cluster tightly and volatility tends to
  expand again (volatility clustering / mean reversion of range). That's when the breakout's losers get hit
  hardest (Crabel 1990).
- Always-winner: the spread (market makers). Here stops are range-sized and holds are hours, so costs are a
  small share of each trade.
Honest prior: our only FX breakout test (005, NY pre-news range on EURUSD 2024) failed, and EURUSD intraday has
leaned toward reversion in our work. The London open (FX's main open) and the NR7 filter are untested.

## Rules (fixed now)
- 1m bars, mid prices for the range and signals; fills at bid/ask by the engine.
- **Opening range (OR):** high/low of 08:00–08:30 London time, weekdays.
- **Entry:** the first 1m close above the OR high (long) or below the OR low (short) between 08:30 and 11:00
  London; entry at the next minute's open. **One trade per day** (only the first breakout).
- **Stop:** the opposite side of the OR (distance from the signal close). **Target:** none (10 × OR range,
  effectively off). **Exit:** 16:00 London (London close) if still open.
- **NR7 filter (the test):** trade only if the previous FX day (17:00–17:00 New York) had a range strictly
  narrower than each of the 6 FX days before it.
- **Control (reference):** the same breakout on every day (no filter).
- **News rule (standing):** ±1 h red-news blackout for the pair's currencies (breakout signals inside it are
  skipped; open trades closed 1 h before a release; no re-entry).
- Costs: Dukascopy bid/ask, no commission.
- Results reported in pips and in **R** (pips ÷ stop distance = equal risk per trade).

## Pass bar
Primary = **EURUSD + GBPUSD pooled** (the London-open currencies); AUDUSD secondary.
- **PASS:** NR7 version total R > 0 in **both** 2023 and 2024 (pooled EUR+GBP), AND its R per trade beats the
  every-day control's on 2023+2024.
- **STRONG:** PASS and the pooled 95% bootstrap CI of R per trade above 0.
NR7 gives ~35 trading days per pair per year, so the sample is small (~140 trades for the primary); judge the
CI honestly.

## Results
_(filled after the run)_
