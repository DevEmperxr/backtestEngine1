# 076 — Where in the day did gold (and EURUSD) move in 2023–24? (descriptive)

**Date:** 2026-10-07 · script: research/regime/gold_sessions_076.py -> results.json, session_moves.png
**Status:** done (descriptive, POI layer: time of day). User: "go check". EURUSD/XAUUSD 2023–24 only.

Each FX day (17:00–17:00 New York) split into Asia 18:00–03:00, London 03:00–08:00, NY morning 08:00–12:00,
NY afternoon 12:00–17:00 (New York time); mid price change per session, summed / averaged over weekdays.

## Gold (XAUUSD), $ per oz
| session | 2023 total (t) | 2024 total (t) | both: total, % | per day | up days |
|---|---|---|---|---|---|
| **Asia 18–03** | **+$193.7 (1.99)** | **+$260.0 (1.64)** | **+$453.7, +21.1%** | +$0.88 | **56.0%** |
| London 03–08 | +$35.1 (0.39) | +$159.4 (1.16) | +$194.5, +8.5% | +$0.38 | 53.7% |
| **NY morning 08–12** | **−$147.0 (−0.80)** | **−$150.1 (−0.68)** | **−$297.1, −12.4%** | −$0.58 | 47.1% |
| NY afternoon 12–17 | +$132.7 (1.27) | +$238.9 (1.70) | +$371.5, +17.2% | +$0.72 | 52.7% |

## EURUSD, pips (comparison)
| session | 2023 | 2024 | both | up days |
|---|---|---|---|---|
| Asia 18–03 | +151.9 | −447.9 | −296.0 | 50.1% |
| London 03–08 | −490.5 | −251.9 | −742.3 | 50.1% |
| NY morning 08–12 | +39.3 | −383.8 | −344.6 | 49.9% |
| NY afternoon 12–17 | +416.3 | +289.2 | +705.5 | 53.8% |

Gold spread by hour (2024 median): ~$0.37–0.39 most hours, $0.71 at the 17:00 reopen, $0.43 at 18:00, $0.41 at 19:00.

## Takeaways
- **Gold's 2023–24 rise happened mostly in the Asian session** (+$454, positive both years, t ≈ 1.6–2.0, up 56% of
  days) and the **NY afternoon** (+$372, positive both years). The **NY morning fell in both years** (−$297).
  Our 075 window (entries 03:00–12:00 NY) sat on London (+) and NY morning (−), which cancel: that's why even the
  with-trend drift check was flat.
- Plausible "who loses" for Asia: price-insensitive physical and central-bank buying during Asian hours (China, India)
  in a bull market. Caveat: this is 2023–24, a strong gold bull market; an Asia-session drift could be just where
  the bull market's buying happened, and may not hold in a flat or falling market.
- EURUSD shows the home-hours pattern again: EUR weak in London hours (−742), USD weak in the NY afternoon (+706 for
  EUR/USD), both years (as in 058's raw drift).
- An Asian-session gold trade would not cross the 17:00 NY rollover (18:00 -> 03:00 NY), so it fits the user's
  no-overnight / no-rollover rule; enter after 18:00 to avoid the wide reopen spread.
