# 058 — Home-hours weakness (Breedon & Ranaldo 2011) on EURUSD, GBPUSD, AUDUSD, 2023 + 2024

**Date:** 2026-10-07 · file: research/strategies/058_home_hours.py · paper: research/papers/breedon_ranaldo_2011_intraday_fx.pdf
**Status:** pre-registered (user request)

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
  UTC days (mid prices); no profit target (set to 10 × ATR, i.e. effectively off). Stop hits reported.
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
_(filled after the run)_
