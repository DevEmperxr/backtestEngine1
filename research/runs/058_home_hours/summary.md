# 058 — Home-hours weakness (Breedon & Ranaldo 2011) on EURUSD, GBPUSD, AUDUSD, 2023 + 2024

**Date:** 2026-10-07 · file: research/strategies/058_home_hours.py · paper: research/papers/breedon_ranaldo_2011_intraday_fx.pdf
**Status:** done. **FAIL** on all three pairs with the news rule; effect weak in 2023–24

## Who loses, and why
Banks and investment funds tend to be **net sellers of their own currency during their own trading hours**
(BNP Paribas customer data and US TIC equity-flow data in the paper; corporates did NOT show it). Growing
funds keep converting fresh local money into foreign assets, and they trade when their desks are open, not
when the price is good. That predictable, price-insensitive selling pushes each currency down in its own
hours (Cornett et al. 1995, Ranaldo 2009, Breedon & Ranaldo 2011). We take the other side for a few hours.
Costs (spread) go to market makers on every trade; the holds are hours long, so the edge per trade can be pips.

## Paper facts used (not tuned)
- Sessions (futures hours): Europe 07:00–15:00 London; US 08:00–16:00 New York; Australia 10:00–16:00 Sydney.
- EUR/USD and GBP/USD sessions overlap, so (as in the paper) home session = **07:00 London -> 08:00 NY**
  (open to open) and USD session = **08:00 -> 16:00 NY**. AUD/USD (no overlap): AUD session = **10:00 -> 16:00
  Sydney**, USD session 08:00 -> 16:00 NY.
- Strategy: **short the base currency in its home session, long it in the USD session.** In 1997–2007 EBS data:
  EUR/USD profitable after costs (Sharpe 1.3 morning short, 0.9 afternoon long); GBP/USD and AUD/USD
  not profitable after (interdealer) costs. EUR/USD effect stable year by year 1999–2007.

## Rules (fixed now)
- 1m bars; positions held through the session (signal on every session bar; entry at the session's first
  minute; at 08:00 NY the short is closed and the long opened at the same price for EUR/GBP: reversal).
- Close at session end (EUR/GBP: long closed 16:00 NY; AUD: short closed 16:00 Sydney, long 16:00 NY).
- **News rule (standing):** ±1 h red-news blackout for the pair's currencies: an open position is closed 1 h
  before a release; **re-entry** in the same direction when the blackout ends if the session is still on
  (the flow doesn't stop for news); days with an unknown-time red event skipped.
- Protective stop (prop-firm requirement; the paper had none): **1 × daily ATR(20)** of the previous completed
  UTC days (mid prices; at the start of each year's data, the days available so far, minimum 5 —
  implementation note added before any result); no profit target (set to 10 × ATR, i.e. effectively off). Stop hits reported.
- Costs: Dukascopy bid/ask (no commission, as in all runs so far).

## Tests (fixed now)
- Primary: **EURUSD**, 2023 and 2024. Secondary: GBPUSD and AUDUSD (expected to fail on costs, per the paper).
- Report per pair, per year, per leg (home-session short, USD-session long): trades, net and gross pips,
  per-trade with bootstrap CI, stop hits, and the session's mid-price drift (no costs, no blackout) to see if
  the effect itself still exists in 2023–24.
- Reference only (not the result, per the news rule): same strategy without the blackout, to measure what
  the rule costs.

**PASS (EURUSD):** pooled 2023+2024 net > 0 AND net > 0 in each year AND both legs' mid-price drift has the
predicted sign in both years. **STRONG:** pooled per-trade CI above 0. GBPUSD / AUDUSD judged by the same
bar, reported separately.

## Results
All runs: generic lookahead audit ok. Script: research/regime/home_hours_058.py -> results.json;
charts equity_monthly_<PAIR>_2023_2024.png. Pre-run fixes (before any result): `in_window` column for the
audit; AUD home time zone and official AUD release times added to research/regime/news.py.

### 1. Is the effect still there? Raw session drift (mid price, no costs, no news rule), pips per day
| | home session (predicted down) | USD session (predicted up) |
|---|---|---|
| EURUSD 2023 | **−2.08** (t −1.2) ✓ | +1.53 (t 0.6) ✓ |
| EURUSD 2024 | **−1.95** (t −1.5) ✓ | −0.87 (t −0.5) ✗ |
| GBPUSD 2023 | −2.83 (t −1.2) ✓ | +4.66 (t 1.5) ✓ |
| GBPUSD 2024 | −0.69 (t −0.4) ✓ | −0.09 (t −0.0) ✗ |
| AUDUSD 2023 | +2.71 (t 1.9) ✗ | +1.14 (t 0.6) ✓ |
| AUDUSD 2024 | −0.36 (t −0.3) ✓ | −1.39 (t −0.9) ✗ |

The European home-session weakness still points the right way in all 4 EUR/GBP pair-years (about −1 to −3
pips a day) but is weak (no |t| above 1.5). The USD-session strength is inconsistent. Much smaller and
noisier than in 1997–2007.

### 2. The strategy (news rule on = the result)
| net pips (trades) | 2023 | 2024 | 2023+24 | per trade [CI] | spread/trade |
|---|---|---|---|---|---|
| **EURUSD** | +61.0 (583) | −205.3 (579) | **−144.3** | −0.12 [−1.34, +1.15] | 0.26 |
| GBPUSD | +720.4 (598) | −620.6 (590) | +99.9 | +0.08 [−1.48, +1.64] | 0.87 |
| AUDUSD | −1402.8 (627) | −809.9 (612) | −2212.7 | −1.79 [−2.75, −0.84] | 1.17 |

### 3. Reference only: no news rule (not allowed under the user's rule)
| net pips | 2023 | 2024 |
|---|---|---|
| EURUSD | +897.5 | +142.4 |
| GBPUSD | +1402.5 | −371.6 |
| AUDUSD | −797.0 | −650.3 |

On EURUSD the 1-hour news rule costs about 1,180 pips over two years: the sessions are full of red
releases (European data in the European morning, 08:30/10:00 US data), and being flat around them misses a
large part of the session drift. Re-entry spreads explain only ~40 pips of that.

**Verdict (pre-registered bar): FAIL on all three pairs.** EURUSD net < 0 with the news rule and its USD leg
had the wrong sign in 2024; GBPUSD lost in 2024; AUDUSD lost clearly (as the paper found for AUD after
costs). The effect seems to have weakened a lot since 2007; the European home-session leg is the only
part still pointing the right way, and it is not significant.

Note for the user (not tested, post-hoc): the no-news-rule EURUSD reference was positive in both years. A
shorter blackout (e.g. FTMO's actual few-minute rule) would sit between the two, but choosing it now,
after seeing these results, would be fitting to them; it would need fresh data (EURUSD 2025 Jan–Apr is the
only clean EURUSD left).

