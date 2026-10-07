# 059 — London-open range breakout, after NR7 days (Crabel), EURUSD / GBPUSD / AUDUSD 2023 + 2024

**Date:** 2026-10-07 · file: research/strategies/059_london_orb_nr7.py · **Status:** done. PASS by the letter of the bar, but no real edge (+0.04R/trade, CI includes 0)

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
All runs: lookahead audit ok. Script: research/regime/london_orb_059.py -> results.json; charts
equity_monthly_R_nr7.png, equity_monthly_R_all.png (EURUSD+GBPUSD, in R).

| | NR7 days (test) | every day (control) |
|---|---|---|
| EURUSD 2023 | 36 tr, +112 pips, **+4.6R** | 239 tr, +130 pips, −4.5R |
| EURUSD 2024 | 40 tr, +5 pips, **−2.1R** | 241 tr, +117 pips, +9.8R |
| GBPUSD 2023 | 35 tr, −40 pips, **−2.4R** | 233 tr, −384 pips, −13.2R |
| GBPUSD 2024 | 38 tr, +60 pips, **+5.4R** | 231 tr, −477 pips, −34.5R |
| AUDUSD 2023 | 38 tr, −151 pips, −14.2R | 252 tr, −799 pips, −69.6R |
| AUDUSD 2024 | 37 tr, −69 pips, −5.8R | 251 tr, −416 pips, −47.6R |

| pooled | trades | R total | R / trade [95% CI] | win | max DD (R) |
|---|---|---|---|---|---|
| **Primary EUR+GBP, NR7** | 149 | **+5.5** (2023 +2.2, 2024 +3.3) | **+0.037 [−0.19, +0.28]** | 35.6% | −12.4 |
| EUR+GBP, every day | 944 | −42.4 | −0.045 [−0.13, +0.04] | 37.5% | −54.7 |
| AUDUSD, NR7 | 75 | −20.1 | −0.27 | 28.0% | |
| All three, NR7 | 224 | −14.5 | −0.07 [−0.25, +0.12] | 33.0% | |

Spread is small here (≈0.04R per trade on EUR/GBP), as intended.

**Verdict:** by the pre-registered bar it **passes** (EUR+GBP NR7 positive in both years and better than the
control). Honestly, the bar was too loose: +0.04R per trade with a CI from −0.19 to +0.28 is no edge, each
pair flips sign between years, and AUDUSD's NR7 version loses. "Beats the control" mostly means "loses less
than breakouts on every day", which **lose in 5 of 6 pair-years**.

**What it does show (who loses):** at the London open, **breakout traders are the losers**, not the
winners: plain breakouts lose on all three pairs, the same tendency to snap back that made the London fade
work a little. Fading the breakout instead isn't automatically profitable either: the every-day breakouts lose
mostly through spread (EUR+GBP gross −114 pips vs net −614), so the opposite trade would pay the same costs.

Not adopted. NR7 makes breakouts less bad but doesn't create an edge.

