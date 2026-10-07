# 056 — Monetary tide: rates + QE/QT combined, and the shadow-rate gap -> EUR/USD? (daily 2009–2020)

**Date:** 2026-10-07 · **Status:** done. **Both FAIL**; central bank tides dropped as a filter.
(User chose option 3 + the shadow-rate shortcut and allowed re-use of daily EUR/USD 2009–2020.)
Code: research/regime/monetary_tide.py (indices + test).

## Data (each value used only from the day it was usable)
- US 2-year Treasury yield: FRED **DGS2** (daily close). Usable next day.
- Euro-area 2-year: ECB **YC B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y** (AAA government curve, 2-year spot, daily). Usable next day.
- QE/QT force: run 055 index, total assets (research/regime/qe_force.py), unchanged.
- Shadow rates: Wu & Xia (2016), US and euro area, monthly (Cynthia Wu's site, files cached in data/macro/).
  Usable 30 days after the month ends. **Caveat:** these are model estimates fitted over the full
  sample, not real-time numbers, so they carry some hindsight; a pass would be weaker evidence.
- EUR/USD: FRED DEXUSEU daily, 2009–2020 as in 055; nothing after 2020.

## Indices (fixed now; z = value / std over the previous 756 trading days)
- **Rate component:** R = change over 20 trading days in (US 2y − EA 2y). US yields rising relative to euro
  should push EUR/USD **down**, so its EUR/USD-signed score is **−z(R)**.
- **QE component:** z(F) from 055 (Fed − ECB balance-sheet force; positive pushes EUR/USD up).
- **Combined monetary tide (primary A):** C = (−z(R) + z(F)) / 2, then zC = z(C); states at ±1.
- **Shadow-rate tide (primary B):** S = US shadow rate − EA shadow rate (monthly); ΔS = change over the last
  3 months; score −z(ΔS) (US rising relative to euro pushes EUR/USD down); states at ±1.
- Rate component alone (−z(R)): reported, not judged.

## Test and pass bar (stricter than 055: this is a second round on the same data, two primaries)
Outcome: EUR/USD log return over the next 20 trading days (primary) and 5 days (reported).
Each primary PASSES only if, on the 20-day horizon:
1. mean forward return on "long" days minus "short" days > 0;
2. slope on the score > 0 with Newey–West t > **2.5** (20 lags);
3. same with EUR/USD's own trailing 20-day return as a control: t > **2.5**;
4. slope > 0 in both halves, 2009–2014 and 2015–2020.

If neither passes, central bank tides are dropped as a filter. If one passes, a Test 2 on 2023–24
intraday trades gets its own pre-registration.

## Results
results.json, chart monetary_tide_2009_2020.png. The combined score starts 2010-10 (it needs 3 years of
history for its own scaling).

| 20-day horizon | long − short | slope t | t with momentum | halves (t) | verdict |
|---|---|---|---|---|---|
| **A combined (rates + QE/QT)** | +0.004% | −0.11 | −0.07 | +0.90 / −0.28 | **FAIL** |
| **B shadow-rate gap** | −0.27% | 0.15 | 0.15 | −0.07 / +0.62 | **FAIL** |
| rate component alone (reported) | +0.24% | −0.41 | −0.47 | −0.01 / −0.67 | (fail) |

5-day horizon: all |t| < 0.8. The rate and QE parts are only weakly related (r = 0.19), so combining them
added two kinds of noise, not signal.

**The key fact:** the 2-year rate-gap change and EUR/USD move strongly **together** over the same 20 days
(r = −0.39, right sign: US yields up relative to euro, EUR/USD down), but the gap says **nothing about
the next 20 days** (r = +0.03). Rate expectations are priced into EUR/USD as they change, so by the time
a "tide" is measurable, the move has already happened. Same lesson as 055 for QE.

**Conclusion (055 + 056):** none of the slow central bank measures (balance sheets, 2-year rate gap, shadow
rates, or the combination) predicts EUR/USD's next 1–4 weeks on 2009–2020. They describe the move as it
happens; they don't anticipate it. Dropped as filters.

