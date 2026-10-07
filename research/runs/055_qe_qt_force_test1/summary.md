# 055 — "Q Tide": does the net QE/QT force of the Fed vs the ECB predict EUR/USD? (Test 1, daily 2009–2020)

**Date:** 2026-10-07 · **Status:** pre-registered (user idea; definitions agreed with the user)
Code: research/regime/qe_force.py (index), research/regime/qe_force_test1.py (test).

## Idea (user)
QE weakens a currency and QT strengthens it. Measure each central bank's balance-sheet force, net the
two for EUR/USD, and see if the leftover force predicts the pair's direction (negative = favours shorts).

## Data (user permission: daily data allowed for Test 1 only)
- Fed total assets: FRED **WALCL** (weekly, Wednesday level, millions USD). Usable from obs date + 2 days.
- ECB total assets: FRED **ECBASSETSW** (weekly, Friday level, millions EUR). Usable from obs date + 5 days.
- US nominal GDP: FRED **GDP** (quarterly, SAAR, billions USD). Euro area nominal GDP: FRED **EUNNGDP**
  (quarterly, millions EUR, x4 to annualise). A quarter is usable 90 days after it ends.
- EUR/USD: FRED **DEXUSEU** (daily noon New York rate, USD per EUR). Test dates 2009-01-01 to 2020-12-31,
  forward windows ending by 2020-12-31. Nothing from 2021 or later is used for EUR/USD.
- Robustness version (bond holdings only): Fed **WSHOSHO** (securities held outright) and ECB
  **ILM.W.U2.C.A070100.U2.EUR** (securities held for monetary policy purposes, ECB data portal; ISO week,
  usable from that week's Friday + 5 days).

## Index (fixed now)
For each day d, using only data usable by d:
- force_US = (Fed assets now − Fed assets 13 weeks earlier) / US annual nominal GDP × 100 (% of GDP)
- force_EA = same for the ECB with euro area GDP
- **net F = force_US − force_EA.** Positive (Fed expanding faster / shrinking slower) should push EUR/USD **up**;
  negative should push it **down** (favours shorts).
- **z = F / standard deviation of F over the previous 756 trading days (~3 years).**
- State: z > +1 "long tide", z < −1 "short tide", otherwise neutral.

## Test 1 (pass bar fixed now)
Outcome: EUR/USD log return over the next 20 trading days (primary) and 5 days (secondary), from day d's
rate to day d+h's rate.
PASS requires all four, on the 20-day horizon:
1. mean forward return in "long tide" days minus "short tide" days > 0;
2. regression fwd20 = a + b·z: b > 0 with Newey–West t > 2 (20 lags);
3. same with EUR/USD's own trailing 20-day return as a control: b > 0, t > 2;
4. b > 0 in both halves, 2009–2014 and 2015–2020.
Report the same for the 5-day horizon and for the bond-holdings version (secondary, not part of the bar).
Also report how often each state occurs and EUR/USD's move in each.

If Test 1 fails, the force is not used as a filter. If it passes, Test 2 (on 2023–24 intraday: do short
trades beat long trades when the force is negative?) gets its own pre-registration.

## Results
_(filled after the run)_
