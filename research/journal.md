# Strategy Research Journal

Index of every strategy experiment run in this repo, in order. See
[`strategy_research_protocol.md`](../strategy_research_protocol.md) for the
process this follows and the entry format. **Append-only** — a new result
gets a new numbered entry, never an edit to an old one.

Format: `- **00N** \`name\` (date) — hypothesis → decision + why. [details](runs/00N_name/summary.md)`

---

- **001** `sma_nywin_flat1600` (2026-10-05) — 5m SMA20/50 cross, 07:00 NY→16:00 London, SL10/TP15, flat 16:00 → **discarded**: +26.8 pips but expectancy CI [−1.20,+1.42] straddles 0, TP rate 40.9% vs 40% random-walk null, H1/H2 signs flip, ex-Nov −46.7. [details](runs/001_sma_nywin_flat1600/summary.md)
- **002** `sma_nywin_letrun` (2026-10-05) — as 001 but no time exit (let trades run) → **discarded**: win rate 40.23% vs 40.0% null (pure noise), CI [−1.45,+1.56], ex-Nov −120; the 16:00 flat changes ~12 pips over 68 trades. [details](runs/002_sma_nywin_letrun/summary.md)
- **003** `sma_nywin_atr` (2026-10-05) — as 001 with SL=2.5×ATR14, TP=1.5×SL → **discarded**: gross −102.7 (no edge before costs), CI [−1.92,+0.75], both halves negative; vol-scaled exits can't rescue an uninformative entry. [details](runs/003_sma_nywin_atr/summary.md)
- **004** `sma_mtf_align_1m` (2026-10-05) — 1m SMA20/50 cross only when 5m+15m SMA trends agree, SL4/TP6, flat 16:00 → **discarded**: −180.7 pips, gross −87.8, CI [−0.91,+0.02], negative both halves, TP 34.9% vs 37.6% spread-adjusted null. Also: null formula corrected to (SL−spread)/(SL+TP); errata appended to 001–003, conclusions unchanged. [details](runs/004_sma_mtf_align_1m/summary.md)
- **005** `orb_ny_prenews` (2026-10-05) — ORB: 07:00–08:30 NY range, first 1m close beyond it after 08:30, SL opposite side, TP 1.5×range, flat 16:00 → **discarded**: −165.4 pips, gross −104.3, CI [−2.55,+1.25], H1 +16 / H2 −181, TP 40.9% vs 45.5% null, NFP/CPI days no different (n=24). 46% of trades time-exited. [details](runs/005_orb_ny_prenews/summary.md)
- **006** `orb_ny_prenews_nyclose` (2026-10-05) — 005 with window/force-flat at 16:00 NY instead of 16:00 London (data-informed variant, trial 6) → **discarded**: −510.6 pips, gross −446.9, CI [−4.18,+0.16], both halves negative. The 118 trades open at London close were +153.5 then, −215.2 by NY close: breakouts reverse after London close. [details](runs/006_orb_ny_prenews_nyclose/summary.md)
- **007** `fix_fade_london` (2026-10-05) — Krohn/Mueller/Whelan: fade the 15:00→16:00 London move at the 16:00 fix, hold to 16:00 NY → **discarded on 2024, re-test on other years**: +39.4 pips but CI [−1.96,+2.29], H1 −11 / H2 +51. Pre-registered split: big pre-fix moves +217.7 vs small −178.3 (both CIs include 0; 2024 contaminated by 006). [details](runs/007_fix_fade_london/summary.md)
- **008** `round_number_fade` (2026-10-05) — Osler: fade 1m touch-and-reject of 50-pip levels, SL 4 beyond, TP 1.5R → **discarded**: −181.7, gross −91.8, CI [−1.14,+0.19], both halves negative; 00 levels worst (−142.5), the opposite of the TP-clustering prediction. [details](runs/008_round_number_fade/summary.md)
- **009** `band_rsi_fade` (2026-10-05) — Bollinger(20,2)+RSI(14) 30/70 fade on 5m, TP mid-band, SL 2.5×ATR → **discarded**: −190.1, gross −123.7, CI [−2.04,+0.65], H1 −202 / H2 +12. [details](runs/009_band_rsi_fade/summary.md)
- **010** `bb15_x5_fade_extreme` (2026-10-05) — user idea: 15m Bollinger(20,2) close outside band, confirmed by 5m SMA 9/21 cross back within 2h (amended from 1h pre-P&L: only 56 signals), TP 80% to mid-band, SL beyond setup extreme +2 → **discarded (inconclusive)**: 98 trades, +12.8 pips, CI [−1.46,+1.64], TP-first 68.9% vs 68.0% null; confirmation arrives late (TP < SL on 81/98). [details](runs/010_bb15_x5_fade_extreme/summary.md)
- **011** `bb15_x5_fade_atr` (2026-10-05) — as 010 with SL 2.5×ATR(5m) → **discarded (inconclusive)**: 99 trades, +6.3 pips, CI [−1.42,+1.49], TP-first 66.2% vs 63.6% null. [details](runs/011_bb15_x5_fade_atr/summary.md)
- **012** `bb15_engulf5_extreme` (2026-10-05) — 010 with a 5m "outside" engulfing confirm (close beyond prior high/low) instead of SMA 9/21; SL beyond setup extreme → **discarded**: 415 trades, −157.8, gross −61.2, CI [−1.29,+0.53], TP-first 42.7% vs 47.6% null (z −1.75). Earlier entries, but reversals did not follow through. [details](runs/012_bb15_engulf5_extreme/summary.md)
- **013** `bb15_engulf5_candlestop` (2026-10-05) — as 012, SL 2 pips beyond the engulfing candle → **discarded**: 476 trades, −149.3, gross −36.7, CI [−1.03,+0.44], TP-first 35.1% vs 39.0% null. [details](runs/013_bb15_engulf5_candlestop/summary.md)
- **014** `bb15_engulf5_extreme_lonny` (2026-10-05) — 012 with window 08:00 London → 16:00 NY → **discarded**: 1,057 trades, −15.9 pips, gross +0.21/trade < spread, CI [−0.60,+0.57], TP-first at null. Split: entries after 16:00 London +46.2 (n=193), before −62.1. [details](runs/014_bb15_engulf5_extreme_lonny/summary.md)
- **015** `bb15_engulf5_candlestop_lonny` (2026-10-05) — 013 with window 08:00 London → 16:00 NY → **discarded**: 1,229 trades, −153.2, CI [−0.58,+0.35], both halves negative. Split: after 16:00 London +94.3 (n=236), before −247.5. Third post-fix-positive hint on 2024 (see 006/007). [details](runs/015_bb15_engulf5_candlestop_lonny/summary.md)
- **016** `fix_fade_oos` (2026-10-05) — OUT OF SAMPLE (2023, 2025; registered before data existed): fade 15:00→16:00 London move at the fix (A = 007; B = past-only big-move filter) → **discarded**: A −423.6 / −10.9, B −127.6 / −276.8; negative in both test years. [details](runs/016_fix_fade_oos/summary.md)
- **017** `bb15_engulf5_postfix` (2026-10-05) — OUT OF SAMPLE: 014/015 engulfing fade, entries 16:00 London → 16:00 NY only → **discarded**: A −47.1 / −99.3, B −51.6 / −218.3; the 2024 post-fix advantage was noise. [details](runs/017_bb15_engulf5_postfix/summary.md)
- **018** `orb_fix_fade` (2026-10-05) — OUT OF SAMPLE: fade the day's still-open 005 breakout at the 16:00 London fix, flat 16:00 NY → **not confirmed, open lead**: 2023 +95.9 (n=97), 2025 +58.2 (n=126), positive in all three years incl. 2024 discovery (+330.2); pooled 2023+2025 99% CI [−2.47,+3.77] includes 0; edge decayed +2.80 → +0.99 → +0.46/trade. [details](runs/018_orb_fix_fade/summary.md)
- **019** `orb_fix_fade_exits` (2026-10-06) — OUT OF SAMPLE (2021, 2022; registered before data opened): 018's fade with designed exits A time-exit / B 1.5×ATR bracket / C back-to-range, + 018 control → **019A/B/C discarded** (A 2022 −92.7, B 2022 −231.0, C 2021 −15.3); **018 not confirmed**: 2021 +150.2, 2022 +24.8, pooled 98.75% CI [−2.40,+3.90]. 018 now positive in all 5 years; unseen-only (2021/22/23/25) 481 trades +329.1, +0.68/trade, 95% CI [−1.02,+2.39]. [details](runs/019_orb_fix_fade_exits/summary.md)
- **020** `trend_detector_scorecard` (2026-10-06) — REGIME BRICK 1 (2023, measurement): do 7 past-only trend detectors (ER, ADX, MA slope, R², choppiness, variance ratio, autocorr) predict the next 20 bars' efficiency on 5m/15m/1h? → **no**: all ρ ≈ 0 (|ρ| ≤ 0.04 on 5m/15m, inside the sign-randomised nulls). Hint only: 1h R²/ER ρ −0.15/−0.11 (a clean 20h trend is followed by chop), 95% CI excludes 0, 99.8% doesn't. [details](runs/020_trend_detector_scorecard/summary.md)
- **021** `fib_stretch_1h` (2026-10-06) — REGIME BRICK 1b (2023, measurement): how far does price stretch from the 1h MA20 in σ before returning; do Fibonacci bands matter? → in-window, 31% of excursions reach 1σ, 21.5% 1.618σ, 14% 2.618σ; **the turning probability falls as stretch grows** (≈9% → 2–3% per 0.1σ); **Fibonacci levels not special** (fib − control 95% CI includes 0). [details](runs/021_fib_stretch_1h/summary.md)
- **022** `sweep_fade_to_ma` (2026-10-06) — IDEA 1 (2023): 1h context + 5m stretched 2·ATR from MA20 + 1m sweep of a confirmed swing → fade to the 5m MA20, stop 1 pip beyond the sweep; no-sweep control → **discarded**: primary (trending, stretch with trend) 236 trades −71.6, gross −1.5, CI [−1.05,+0.51], TP-first 16.4% vs 18.0% null; the sweep = control; stops (~2.8 pips) sit inside 1m noise. [details](runs/022_sweep_fade_to_ma/summary.md)
- **023** `sweep_fade_rework` (2026-10-06) — IDEA 1 rework (2023): A = 1m sweep with stop 1.5× 5m ATR; B = 5m sweep → **A carried forward, not passed**: primary (trending, with trend) 142 trades +56.7, +0.40/trade, CI [−1.34,+2.15], both halves +, TP-first 43.5% vs 37.2% null (z +1.39); sideways fades −509.8 (CI excludes 0): context matters. **B discarded** (primary −83.2). [details](runs/023_sweep_fade_rework/summary.md)
- **024** `sweep_fade_stops` (2026-10-06) — IDEA 1, 023A with other stops (2023): A sweep + 0.5 ATR, B 30-min time stop, C break-even at 50% → **all discarded**: with-trend −92.6 / −35.9 / +26.2 vs 023A +56.7. The snap-back needs room and time; 023A's 1.5× ATR stop stays. Engine gained optional per-trade max_hold_bars and break-even. [details](runs/024_sweep_fade_stops/summary.md)
- **025** `turn_confirm_continuation` (2026-10-06) — IDEA 2 (2023): 1h context + 5m stretch (1.5 ATR, amended pre-P&L) → confirmed 5m turn (lower high, close below the pullback low) → ride; targets A 1h SMA20 / B 2R / C last 1h swing → **not passed, too few trades**: with-trend +51.7 / +23.1 / +25.8 on ~50 trades each, CIs ±4–5 pips/trade, H1 negative in all; sideways loses clearly (B −584.3, CI excludes 0). [details](runs/025_turn_confirm_continuation/summary.md)

> **Data split from run 026 on** ([DATA_SPLIT.md](DATA_SPLIT.md)): practice years **2023 + 2024** (keep a change only if it helps in both), test years **2021, 2022, 2025** (touched once per finished version), **2026** emergency holdout (untouched).
- **026** `idea1_baseline_2024` (2026-10-06) — Idea 1 (023A, unchanged) on practice year 2024 → **2023 pattern does not repeat**: with-trend −18.9 (131 trades, TP-first 37.4% vs 37.3% null), sideways +18.4. Two practice years: with-trend ≈ +0.14 pips/trade, i.e. no edge; "avoid sideways" not stable. [details](runs/026_idea1_baseline_2024/summary.md)
- **027** `idea1_eurgbp` (2026-10-06) — Idea 1 (023A unchanged) on EURGBP 2021–2024 (never looked at) → **does not replicate**: with-trend −67 / −446 / −142 / −56 by year, pooled 514 trades −710.7, CI [−1.96,−0.83], gross −243.8; spread ≈ 15–20% of risk on EURGBP. With 026, Idea 1 has no edge outside EURUSD 2023. [details](runs/027_idea1_eurgbp/summary.md)

> **Standing rule (user, 2026-10-06):** every idea, every pair, uses **2023 + 2024 only**; 2021/2022/2025 kept for final checks on request. See [DATA_SPLIT.md](DATA_SPLIT.md).
- **028** `idea2_baseline_2024` (2026-10-06) — Idea 2 (025 unchanged) on practice year 2024 → **direction repeats**: with-trend B +23.1 / +49.8 and C +25.8 / +62.5 in 2023 / 2024 (≈100 trades total each, CIs include 0); sideways negative both years (B −898, CI excludes 0). Target A flat in 2024. First idea in this programme to hold across both practice years. [details](runs/028_idea2_baseline_2024/summary.md)
- **029** `idea2_no_red_news` (2026-10-06) — Idea 2 (B, C) with no trading on ForexFactory red-news days for USD/EUR (~2/3 of days) → **filter hurts, not adopted**: B 99 → 36 trades, +72.9 → +23.2; C 109 → 43, +88.3 → +4.3; the removed red-day trades made +49.7 / +84.0, and the remaining quiet-day trades are negative in 2024. [details](runs/029_idea2_no_red_news/summary.md)
- **030** `idea1_no_red_news` (2026-10-06) — Idea 1 (023A) with no trading on red-news days (USD/EUR) → **no effect**: with-trend 273 → 112 trades, +0.14 → +0.12 pips/trade; removed red-day trades +0.15/trade; still ~zero, negative in 2024. Idea 1 stays shelved. [details](runs/030_idea1_no_red_news/summary.md)
- **031** `idea1_vs_daily_trend` (2026-10-06) — descriptive: does Idea 1 (023A) lose when the daily trend changes? → **no consistent link**: "with daily trend" +96 (2023) / −106 (2024), "against" −39 / +87, flipping each year; monthly P&L vs EURUSD monthly move r = −0.14 (24 months, noise). [details](runs/031_idea1_vs_daily_trend/summary.md)
- **032** `idea1_mfe` (2026-10-06) — descriptive (EURUSD 2023): how far price goes in our favour after Idea 1 entries before the stop → **at chance at every distance** (trending: 0.5R 69% vs 64% chance, 1R 44% vs 48%, 2R 29% vs 32%). No target choice can add an edge; the entry lacks direction. [details](runs/032_idea1_mfe/summary.md)
- **033** `idea1_time_of_day` (2026-10-06) — descriptive (EURUSD 2023+2024): Idea 1 by entry hour → trending trades entered **08:00–10:00 NY positive in both years** (131 trades, +161.6: +95.5 / +66.1); 07:00 and 10:00 negative in both; all-trades negative every hour. Post hoc → hypothesis only; needs unseen data (other pairs / reserved years). [details](runs/033_idea1_time_of_day/summary.md)
- **034** `idea1_lon_ny` (2026-10-06) — Idea 1 (023A) with window 08:00 London → 16:00 NY, EURUSD 2023, by hour → **worse overall** (−819 pips, all contexts negative; trending −177 vs +57 in the old window). Stand-out: fades in the first 2 h after the London open with the 1h **sideways** +320 (207 trades), post hoc. Per-hour picture fragile (09:00 NY flipped vs 033). [details](runs/034_idea1_lon_ny/summary.md)
- **035** `london_open_sideways_2024` (2026-10-06) — TEST on unseen 2024 of 034's post hoc slice (Idea 1 fades entered 03:00–04:59 NY, 1h sideways) → **direction holds, not replicated**: 225 trades +140.0, +0.62/trade, CI [−0.39,+1.64] (2023 discovery +1.55/trade). 03:00 NY carried most of it in both years. Live lead; next: EURGBP / other pairs 2023+2024, same rules. [details](runs/035_london_open_sideways_2024/summary.md)
- **036** `lookahead_check_london_sideways` (2026-10-06) — lookahead checks on the 034/035 slice → **no lookahead**: code review OK; future-scramble = 0 differences before the cut-off (2023 & 2024); 1-minute-late entry still positive (2023 +305, 2024 +249). Real caveat: 2024's +140 is +32.9 without its 5 best trades. [details](runs/036_lookahead_check_london_sideways/summary.md)
- **037** `idea1_us_window_eurgbp` (2026-10-06) — TEST of 033's pattern (Idea 1, trending, entries 08:00–10:00 NY) on EURGBP 2023+2024 (027 trade logs, never sliced by hour) → **fails**: 117 trades −17.1 (−8.0 / −9.1), though +85.7 before costs; the hour pattern doesn't repeat cleanly. [details](runs/037_idea1_us_window_eurgbp/summary.md)
- **038** `london_sideways_eurgbp` (2026-10-06) — TEST of the London-open sideways fade on EURGBP 2023+2024 (034 rules unchanged) → **fails after costs**: 436 trades −191.2 (−103 / −88), though +178.3 before costs (+97 / +81). The EURGBP spread (~0.85/trade) is too high for small-stop trades; the hour pattern differs from EURUSD. Needs a low-cost pair (USD majors) next. [details](runs/038_london_sideways_eurgbp/summary.md)
- **039** `london_sideways_wide_stop_eurgbp` (2026-10-06) — London-open sideways fade on EURGBP with a 3× ATR stop (user: "bigger trades") → **fails**: 351 trades −203.5 (−142 / −61) vs −191 with the 1.5× stop; win rate 35% → 54% but gross fell +178 → +96. A stop change doesn't beat costs. [details](runs/039_london_sideways_wide_stop_eurgbp/summary.md)
- **040** `eurusd_playbook` (2026-10-06) — the three EURUSD leads combined on one account, 2023+2024 (IN-SAMPLE pieces; descriptive): Idea 2 trend 2R +72.9, London-open sideways fade +460.4, fix fade +426.1 → **combined +959.4 on 746 trades** (+439 / +520), 18/24 months positive, monthly correlations ≈ 0 (−0.24 to +0.01), max 2 positions open. A real check needs the reserved years (user's call). [details](runs/040_eurusd_playbook/summary.md)
- **041** `playbook_trade_shapes` (2026-10-06) — trade-shape stats for the 040 playbook (in-sample) + a fair Sharpe counting all weekdays (`lib.evaluate.sharpe_all_days`, new): fair Sharpe Idea 2 0.37, London fade 1.74, fix fade 1.39, **combined 2.24** (framework's traded-days version: 0.89 / 2.34 / 2.18 / 2.53). Combined: 50% win, payoff 1.29, PF 1.31, max DD −196 pips, longest underwater 135 days. [details](runs/041_playbook_trade_shapes/summary.md)

## 042 — Idea 1, two entry windows only (London-open sideways + NY-open trending), EURUSD 2023+2024 — 2026-10-06
User request: keep only the two time filters. One strategy (023A rules), one position at a time.
Combined +595.3 on 591 trades (+297.7 / +297.5), per trade +1.01 [CI +0.21, +1.79], fair Sharpe 1.77,
19/24 months positive, max DD −126 pips. London fade +462 (both years +); NY open +133 (2023 −24.5,
2024 +157.5). In 033 the NY slice made +95.5 in 2023; ~15 extra trades a year that are no longer blocked
flip it, so it is fragile. In-sample; the reserved years are the real test. See runs/042_idea1_two_windows/summary.md.

## 043 — NY-window diagnostics (descriptive) — 2026-10-06
Splits of the 157 NY-window trades of 042. Positive in both years: 08:30–09:00 entries, days the London
window already traded, 2nd+ NY trade, target >= 2x stop. ~27 groups checked, so this is consistent
with chance; hypotheses only. Fair fresh test for NY ideas = a USD pair (GBPUSD 2023+2024).

## 044 — 042 with no red-news days (USD/EUR), EURUSD 2023+2024 — 2026-10-06
User request. Combined +595 -> +104 (216 trades, CI includes 0). London fade collapses (+462 -> +27):
its edge lives on news days. NY open +133 -> +77 on 66 trades, positive both years (+30 / +48) and
slightly better per trade, but wide CI. Not adopted. Third time (029, 030, 044) news days carry the profit.

## 045 — 042 with a +-1 h red-news blackout (no entries, close open trades 1 h before), 2023+2024 — 2026-10-06
User request. New: news.red_news_times() recovers the missing release times (usual time per event, with the
file's clock fixed for Iran's 2022 DST change; official times for NFP/Unemployment/Retail Sales/ECI/German flash
services PMI/German prelim CPI). Combined +469 on 506 trades (042: +595). London fade unchanged (+455 vs +462).
NY window +133 -> +14: its best trades are right after the 08:30/10:00 releases. Not adopted. Hypothesis for later:
the NY window may really be a "fade the post-release overshoot" trade; test on a fresh USD pair.

### Standing rule (2026-10-06): red-news blackout always on
The user will trade in a prop firm that bans news trading. From now on every strategy applies
research/regime/news.py apply_news_blackout(sig, currencies, 60): no entries from 1 h before to 1 h after
each red release for the pair's currencies, open trades closed 1 h before, unknown-time red days skipped.
New baseline for the two-window strategy = 045 (+469 on 2023+2024). Note: the calendar ends 2025-04-07.

## 046 — London-open sideways fade standalone (news blackout on), EURUSD 2023+2024 — 2026-10-06
+455.1 on 409 trades (+263.5 / +191.6), +1.11/trade [CI +0.29, +1.92], fair Sharpe 1.81, PF 1.33, max DD −131,
7/8 quarters positive, target-first 49% vs 39% chance both years, +351 with doubled costs, +240 without best 10.
Same as its part of 045. Best EURUSD lead; in-sample. Next: final check on 2021/2022/2025 (to 2025-04-07) if the user agrees.

## 047 — London fade with the sweep on 5m candles, EURUSD 2023 — 2026-10-06
User request (2023 only). 99 trades +19.2 (vs 1m sweep: 199, +263.5), target-first 52.5% vs 49.3% chance (1m: 49% vs 39%).
Waiting for the 5m close uses up the snap-back: target shrinks to ~6.6 pips against the same ~6.8 stop. Discarded.
Audit fix: sweep022 audit in 5m mode now builds 5m candles from 1s like the strategy (was a 0.23-pip false flag).

## 048 — London fade, stop at sweep candle + 3 pips, EURUSD 2023 — 2026-10-06
User request after the viewer. +119.1 on 222 trades vs +263.5 (ATR stop). Median stop 4.7 vs 7.0 pips. Of 193 shared
entries, 24 winners became stop-outs (+266.7 -> −115.8), 1 loser saved. Price retests past the sweep wick before
reverting. Discarded; third time (022/024/048) a stop tied to the sweep candle loses to the 1.5x ATR stop.

## 049 — London fade, sweep+3 stop, BE at +2R, TP 4R, EURUSD 2023 — 2026-10-06
User request ("let winners win"). +232.7 on 212 trades (046: +263.5; 048: +119.1). Win rate 23%, PF 1.36, max DD −86.8
(046: −130.6), 8/12 months positive, halves +110 / +122. But CI includes 0 and it's negative without its best 10
trades. Same total as 046, smoother, more reliant on big winners. Next fair step: both 046 and 049 unchanged on 2024.

## 050 — London fade runner past the middle band (B: BE + run to opposite band, C: half off + runner), 2023 — 2026-10-06
User chose B and C. New engine feature: partial take-profit (partial_tp_pips + partial_frac, one row per trade, size-weighted
pips; 8 tests). A +263.5 / B +205.4 / C +210.7. Of 91 trades that reached the middle band, running them made +922 vs +948
for taking profit: no edge past the average (random-walk expectation). Keep A: take profit at the middle band.

## 051 — FINAL CHECK: London fade A (046) + runner exits B/C (050) on test years 2021+2022 — 2026-10-06
User request, pre-registered pass bar. A: 2021 −3.0, 2022 +107.5 -> pooled +104.5 on 434 trades, +0.24/trade [CI −0.81, +1.35],
target-first above chance both years (40.7 vs 38.5, 39.8 vs 37.4) -> PASS (not strong). Edge ~80% smaller than on
practice years (+1.11), drawdown −234. B −276, C −74.5 on the test years -> FAIL; A stays. All 4 years A: +559.6 on 843
trades, +0.66/trade [−0.03, +1.35]. EURUSD 2021/2022 now used for the London fade.

## 052 — London fade, one trade per NY day, EURUSD 2021–2024 — 2026-10-06
User request. Practice years better (2023 +266.5 at +1.96/tr, DD −60; 2024 +162.5, DD −47), but test years worse (2021 −40.5,
2022 −24.8; first trade of the day at chance there, later trades +170). All 4 years: same +0.66/trade, 549 vs 843 trades,
Sharpe 0.78 vs 0.95. Not adopted (fails the 3-of-4-years rule). 2021/22 were already seen (051), so not a clean test.

## 053 — London fade one timeframe up (4h context / 15m setup / 5m sweep), EURUSD 2023 — 2026-10-06
User request (2023 only). 90 trades −37.8, target-first 41.5% vs 43.4% chance. Target barely above the stop (10.9 vs 8.9)
because the 5m close uses up the snap-back (as in 047). Discarded. New strategy settings setup_min/ctx_min
(defaults unchanged; 046/047 rechecked). The sweep022 audit now builds setup candles at setup_min.

## 054 — London fade vs market conditions by quarter, EURUSD 2021–2024 (descriptive) — 2026-10-07
User asked what was different before 2023. 12/16 quarters positive (from 2021-Q3); losses 2021-Q1/Q2, 2022-Q2, 2023-Q2.
Volatility, spread, trend, choppiness, 1m autocorrelation don't line up with results (|r| <= 0.3, except quarterly move
+0.48, mixed). Only the strategy-free snap-back rate tracks results (r +0.48), but that is the edge itself. With +0.66/trade
and SD 10.2, ~5 of 16 quarters should lose by luck alone; 4 did. Steady small edge plus noise; no regime filter justified.

## 055 — "Q Tide": net Fed vs ECB QE/QT force -> EUR/USD? Test 1, daily 2009–2020 — 2026-10-07
User idea. Net force = 13-week balance-sheet change as % of GDP (Fed − ECB), z-scored over 3 years; states at ±1.
Daily DEXUSEU 2009–2020 only (user allowed daily data for Test 1 only). FAIL: long−short tide +0.17% over 20 days but
slope t 0.49, t 0.48 with momentum control, halves +0.21 / −0.001; bond-holdings version also fails. Markets price QE on
announcement (EUR/USD fell 1.39 -> 1.05 in 2014 before ECB buying began). Test 2 not run. Code: research/regime/qe_force.py.

## 056 — Monetary tide: 2y rate-gap change + QE/QT combined, and Wu–Xia shadow-rate gap -> EUR/USD, daily 2009–2020 — 2026-10-07
User request (option 3 + shadow rate; allowed re-use of 2009–2020 daily). Pass bar t > 2.5. Combined: t −0.11; shadow: t 0.15;
rate part alone t −0.41. All FAIL. Rate-gap change vs EUR/USD: r −0.39 over the same 20 days, +0.03 over the next 20,
so it is priced as it happens. With 055: central bank tides don't predict EUR/USD; dropped. New dependency in .venv: xlrd
(old .xls shadow-rate files).

## 057 — London fade (046 unchanged) on GBPUSD 2023+2024 — 2026-10-07
FAIL after costs: −48.9 / −18.1 (420 trades, −0.16/trade). Gross +0.64/trade both years and target-first 2–3 pts above
chance, same as unseen EURUSD 2021–22 and EURGBP gross (038). Spread ~0.8 pips/trade eats it. The effect looks real but
small (~0.3–1 pip gross per trade); not viable at prop-firm costs (commission ~0.5–0.7 pip). GBPUSD 2023/24 now used.

## 058 — Home-hours weakness (Breedon & Ranaldo 2011) on EURUSD/GBPUSD/AUDUSD, 2023+2024 — 2026-10-07
Who loses: banks/funds selling their own currency in local hours (paper's BNP + TIC data; not corporates). Short base in home
session (EUR/GBP 07:00 London -> 08:00 NY; AUD 10–16 Sydney), long 08–16 NY, 1x daily-ATR stop, news rule on.
FAIL on all three: EURUSD −144 (+61 / −205), GBPUSD +100 (+720 / −621), AUDUSD −2213. Raw drift: EUR/GBP home session still
down in all 4 pair-years (−0.7 to −2.8 pips/day, |t| <= 1.5); USD session inconsistent. Effect much weaker than 1997–2007.
Reference without the news rule: EURUSD +897 / +142 (the 1h blackout costs ~1,180 pips on EURUSD). news.py: AUD tz + times.

## 059 — London-open range breakout (08:00–08:30 London) after NR7 days (Crabel), EURUSD/GBPUSD/AUDUSD 2023+2024 — 2026-10-07
Primary EUR+GBP NR7: 149 trades, +5.5R (+2.2 / +3.3), +0.037R/trade [CI −0.19, +0.28]: PASS by the letter (bar too loose), no
real edge; pair-years flip sign; AUDUSD NR7 −20R. Every-day breakouts lose in 5/6 pair-years (EUR+GBP −42R, all three −160R).
At the London open breakout traders are the losers; fading isn't free either (spread). Not adopted. Lesson: future pass bars
need a minimum R/trade or a CI condition, not just "positive both years".

## 060 — POI study: first touch of the previous FX day's high/low, London (07–11 London) and NY (08–11 NY) mornings — 2026-10-07
First setup built with the user's template (layer 3: POI only). Race "X back vs X further" after the touch: London EUR+GBP
52.4% reversal @0.25 ATR (p 0.51), NY 49.2%; mean move after 60 min ~1 pip. Coin flip; not carried forward. (0.5 ATR races
mostly unresolved in 4h.) EURUSD London leaned to reversal (~58% both years), not significant.

## 061 — Confirmation layer at the previous day's high/low: rejection vs acceptance after 5 / 15 min — 2026-10-07
Layer 4 on the 060 POI. All 8 combinations ~42–54% success at 0.25 ATR (chance 50%), none near the bar (>= 55% both years,
p < 0.006). Previous-day high/low dropped as a POI: confirmation doesn't separate what happens after the touch.

## 062 — POI study: round numbers (Osler 2003) and the Asian high/low in the London morning, 2023+2024 — 2026-10-07
Round 00/50 levels: reversal at first touch 50.8% / 52.9% (~8 pips), continuation after a cross 50.4% / 45.5%. Asian high/low
first touched 07–11 London: 52.5% reversal (~20 pips; 55.1% in 2023, 49.6% in 2024). Nothing passes (>= 55% both years,
p < 0.01). Three level-type POIs (060 prev-day H/L, round numbers, Asia H/L) are all coin flips at 8–20 pip scales.

## 063 — POI only: 2xATR stretch from the SMA20 at 5m / 15m / 1h, 08:00–10:00 London, 2023+2024 — 2026-10-07
User request (rebuild the London fade layer by layer at bigger scales). EUR+GBP symmetric race: 5m 51.6%, 15m 49.7%, 1h 53.1%
(p 0.09); trade shape vs chance: 5m +2.2 pts, 15m 0, 1h +0.5. Nothing passes. The snap-back is a short-scale (1m–5m) effect
and fades with scale; 046's larger EURUSD 2023–24 edge came from the confirmation + context layers plus luck.

## 064 — Intraday momentum (Gao et al. 2018 adapted): FX-day open -> 09:30 NY move predicts NY afternoon / last half hour? — 2026-10-07
EUR+GBP news-free: NY afternoon 12–16 −0.72 pips in the morning's direction (t −1.1); last half hour 15:30–16 +0.23 pips
(t 1.4, hit 54%, only 2023). FAIL: no momentum in the afternoon; last-half-hour effect right sign but far below the spread.

## 065 — AUDUSD: fade a sweep of the Tokyo first-hour range during 10:00–11:00 Tokyo, 2023+2024 — 2026-10-07
User idea (user chose Tokyo 2nd hour + sweep of the first-hour range). AUDUSD: POI 46/50% back to midpoint, + sweep 45/50%,
trade −84R (−0.22R/trade, CI below 0), gross −228 pips. FAIL. Targets ~4 pips vs ~1 pip spread. GBPUSD leaned to reversal
(53–57%, gross +132) but costs make it −45R; hint only.

## 066 — Promising ideas re-checked under FTMO rules (±2 min news, prop mode: $5/lot, flat 16:55 NY), EURUSD+GBPUSD 2023+2024 — 2026-10-07
New: lib/prop.py (PropConfig, Engine.backtest(prop=), FTMO 2-step challenge simulator); run_experiment --prop; news rule ±2 min.
Only the London fade on EURUSD survives: +215.6 pips after all costs, +0.096R/trade [−0.02, +0.21], both years positive;
FTMO sim at 1% risk: 65% pass (96 trading days) vs 32% for its zero-edge twin. In-sample: on 2021–22 its edge minus
commission is ~−0.26 pips/trade. Home hours, ORB NR7, the 4R variant, all GBPUSD versions: ~0 or negative after costs.
Zero-edge twins pass ~25–32% at 1–2% risk (convex challenge payoff).

## 067 — Clean check: London fade under FTMO rules on unseen EURUSD 2025 — 2026-10-07
FAIL: 213 trades −318 pips (gross −124), −0.18R/trade [CI −0.34, −0.01]; FTMO pass 1.7% at 1% risk vs 30% zero-edge twin.
Under FTMO costs it is negative in 2021, 2022 and 2025; only the discovery years 2023–24 are positive. London fade retired.

## 068 — Value of one €89 FTMO attempt (challenge + a year funded), lib.prop.simulate_lifecycle — 2026-10-07
Zero-edge twin: +$390 EV per attempt (1% challenge, 1% funded, 2% own daily stop), 43% pass. Edge sweep: break-even at
about −0.05 to −0.10R/trade after costs; +0.05R -> +$430–890; +0.10R -> +$790–1,550. FTMO costs ≈ 0.1R/trade on 6-pip stops,
so a zero-gross-edge small-stop strategy is about break-even. A 2% own daily stop raised pass rates.

## 069 — Which prop firm has the most lenient payoff shape? (modelling, lib/prop_firms.py) — 2026-10-07
9 programs (FTMO 2-step/1-step, FundedNext Stellar 2-step, The5ers High Stakes, FundingPips 2-step/Pro, Alpha Pro 10%/8%, E8),
same trade shape (2023–24 London-fade trades, edge set to 0 / −0.05 / −0.10R). FTMO 1-step best at every edge (+$553 / +$241
/ +$89 per attempt net of fee, 51% / 39% / 26% pass), then FundedNext Stellar 2-step; tight programs (FundingPips Pro, E8,
Alpha 8%) least lenient. Rules from secondary sources (2026-10-07); firm-specific costs not modelled.

## 070 — Prop-firm shapes in USD with each firm's commission and trades to pass / to profit — 2026-10-07
User request. Edge before commission 0 / +0.05 / +0.10R; commissions FTMO $3, Alpha $2.5, The5ers $4, FundedNext/FundingPips/E8 $5.
FTMO 1-step first at every edge (+$311 / +$616 / +$1,108 per attempt; 42/53/68% pass; ~38–40 trades to pass, ~50–56 to profit).
Alpha Pro 10% second; FundedNext drops to mid-table on its $5 commission. Tight programs (E8, FundingPips Pro) near zero at zero edge.

## 071 — Passing FTMO 1-step faster (modelling) — 2026-10-07
User asked how to pass faster. Risk per trade is the lever: 1% -> 2% cut median days to pass ~50 -> ~18 (money in hand ~75 -> ~40)
and the pass rate rose (36 -> 43% at zero edge before commission): with ~zero/negative edge after costs, bolder bets win.
3% daily limit caps risk at ~2%. More trades/day lowered pass rates at these edges (costs pile up faster). Lower risk once funded.

## 072 — When to take profits out of a funded FTMO 1-step account (modelling) — 2026-10-07
User question. Best: first payout as soon as allowed (14 days), then on demand whenever profit >= ~1%. Waiting for 5% or keeping a
2% buffer pays less at every edge level (the trailing floor rises with profit, so a buffer isn't a cushion). Unknown FTMO rule:
if the trailing floor stays where the peak put it after a payout, yearly payouts with a good strategy roughly halve. Ask FTMO.

## 073 — "Buy the dip in the trend": 1h RSI(2) pullback, layer by layer for FTMO 1-step, EURUSD 2023+2024 — 2026-10-07
User asked for an indicator-based strategy in the setup template. Bias (daily close vs SMA50) KEPT (better both years), context
(daily ATR > 100d median) DROPPED, 15m confirmation DROPPED. Final B: 2023 +0.099R, 2024 −0.061R; 277 trades, +0.009R/trade after
costs. FTMO 1-step scorecard: 36% pass vs 31.5% twin, +$194 vs +$146 per attempt. Not a candidate (negative 2024). Daily-trend bias
is the first bias layer to help in both years. Daily indicators from 2023+2024 joined (data/derived/eurusd_daily_2023_2024.parquet).

## 074 — Daily-trend bias + three POIs (SMA20 pullback, 20-hour breakout, previous-day break), EURUSD 2023+2024 — 2026-10-07
User: keep the bias, try other POIs/entries. All negative in both years after FTMO costs (−0.07 / −0.11 / −0.09R per trade) and
below their zero-edge twins on the FTMO scorecard. Breakouts with the trend lose (as 059). The RSI(2) sharp dip (073-B, ≈0) stays
the best of the trend-bias family. No candidate.

## 075 — Gold (XAUUSD) with the daily-trend bias: RSI(2) dip, 20-hour breakout, drift check, 2023+2024 — 2026-10-07
New: gold support (Engine(pip=), lib.data.pip_size, FTMO_GOLD 0.0007%/side commission). Rules unchanged from 073-B / 074-P2.
G1 dip −0.18R/trade (−0.11 before costs: dips keep going in gold); G2 breakout −0.08R (flat before costs, no better than drift);
drift check −0.09R. Shorts lose clearly (bull market). Gold's rise didn't appear in the 08:00 London–16:00 NY window. No candidate.

## 076 — Where in the day did gold move in 2023–24? (descriptive) — 2026-10-07
Gold: Asia 18:00–03:00 NY +$454 (both years positive, t 1.6–2.0, 56% up days), London +$195, NY morning −$297 (both years
negative), NY afternoon +$372 (both years positive). Explains 075's flat drift check (window on London + NY morning).
EURUSD: London −742 pips, NY afternoon +706 (home-hours pattern again). Asia gold trade wouldn't cross the rollover.

## 077 — Asian-session trades 19:00 -> 03:00 NY: gold long (uptrend / always), AUDUSD with trend / always long, 2023+2024 — 2026-10-07
In-sample (idea from 076). Gold_trend +0.009R/trade (2023 −0.012, 2024 +0.022), gold_always +0.015R (CI incl. 0); costs ≈ gross
(~4.4 pips/trade). 2023's Asian rise was mostly 18:00–19:00 (skipped, wide reopen spread). FTMO scorecard for gold_always 60% pass /
+$593 (low-variance, barely positive, bull market). AUDUSD with trend −0.10R (CI below 0); always long −0.04R. No candidate.

## 2026-10-07 — 079 NAS100 noise-area momentum (Zarattini/Aziz/Barbon, no VWAP) + 080 NAS100 sessions
- 080 sessions 2023–24: gains came overnight (mostly 2024) and in the 10:00–14:00 cash hours; 14:00–16:00 fell in 2024.
- 079: **first CANDIDATE after FTMO costs**. +0.133R/trade (2023 +0.135, 2024 +0.131), pooled CI +0.01…+0.26, 410 trades,
  costs only 0.025R. FTMO 1-step: pass 70% / EV +$1,434 vs twin 38% / +$280. Caveats: longs carry it (+0.22R vs +0.04R),
  depends on fat-tail days; next check a long-only drift baseline, then DAX/Nikkei.

## 2026-10-07 — 081 London fade (066 rules) on NAS100
- Not a candidate: −0.24R/trade after costs (both years negative, CI below 0); +0.045R before costs. The 03:00–05:00 NY
  NAS spread (~3.6 pts) is 27% of the 13-point ATR stop. Fixed the run_experiment ATR-stop audit to use the strategy's pip.
- 081 on GER40 2023 (user request, 2023 only): −0.19R/trade after costs, −0.12R even BEFORE costs (cheap 1.5-pt spread at
  the DAX open). The fade loses at the DAX cash open; not run on 2024.

## 2026-10-07 — 083 DAX open (descriptive) + 084 DAX-open reversal a/b (2023 in-sample)
- 083: the first hour sets the day high or low on 65% of days; opening moves lean to reversal (weak, t −1.75).
- 084 a (fade first 30 min) −0.11R, b (first-hour false break) −0.05R after costs; both stopped out ~80% of the time
  with tight stops (13–16 pts). Not candidates; 2024 not run.

## 2026-10-07 — 085 DELIBERATE OVERFIT lesson (user-approved one-off, GER40 2023 only; not evidence)
- 084a stops (16 pts) inside open noise: 82% stopped, 41% of those right by the close; raw lean +9 pts/trade (t 1.45).
  084b: nothing there (t 0.03).
- Best of 968 configs on Jan–Jun (+0.85R) -> −0.06R Jul–Dec; its profit was 2 crisis days (17/20 Mar 2023). Never again.
- 086 (same day): user asked for a proper over-fit over the setup template. 16,128 GER40 setups on Jan–Jun 2023; winner
  +2.39R/trade (FTMO pass 95%) -> 0.00R/trade Jul–Dec. H1-vs-H2 correlation across setups −0.09. Never again.
- 087 (same day, user-requested over-fit #2): most 3R wins over the setup elements, GER40 Jan–Jun 2023, 29k setups.
  #1 +0.32 -> −0.10R Jul–Dec. #2 (15m range context, lean with the side of the midpoint, pullback to the day open,
  no confirmation, 0.1 ATR stop, 3R) +0.36 / +0.28 with EUR+USD news blocked. Found: DAX trades must block USD news too
  (US releases were the best 3R trades). #2 only meaningful if frozen and tested once on 2024.
- 087 runner-up frozen on GER40 Jan–Jun 2024 (pre-registered): −0.19R/trade, 3R hit 15.7% (vs 28% in 2023). FAIL, dropped.
  Over-fit lesson confirmed even for the setup that held both 2023 halves.

## 2026-10-07 — 088 walk-forward of month-by-month over-fitting (GER40 2023, user's question "will this method work?")
- Re-pick the most-3R-wins setup each month from the previous 1 or 3 months, trade it the next month: L1 −0.135R/trade
  (worse than a random setup), L3 +0.01R (~0, 3R hit 23%). Chosen-on months looked +0.6…+1.1R. Method fails as
  pre-registered. Longer lookback = less noise but still no edge.

## 2026-10-07 — 089 noise-area: NAS100 drift check + DAX / Nikkei (rules frozen from 079)
- Index news rule now includes USD for GER40/JPN225 (user-approved).
- NAS100 beats its always-long twin by +0.063R/trade pooled (2023: 0.000, 2024: +0.122); shorts' long-twin −0.09.
- GER40 −0.085R/trade (negative before costs too), JPN225 −0.038R. Not candidates. Noise-area = Nasdaq-specific.

## 2026-10-09 — 091 NAS100 noise-area on 2025 (out-of-sample, user named 2025)
- News after 2025-04-07 rebuilt from official schedules (validated 99/99 vs ForexFactory); sensitivities negligible.
- 2025: +0.045R/trade (209 trades, CI −0.11…+0.22), H1 +0.10, H2 −0.01; +0.085R better than always-long; FTMO EV $286 vs
  twin $110. Pre-registered bar ≥ +0.05: FAIL narrowly. Edge ~1/3 of in-sample; weak / possibly decaying.

## 2026-10-09 — 092 NAS100 noise-area on 2021 + 2022 (out-of-sample, user named the years)
- 2021 +0.144R, 2022 +0.143R (bear year), pooled +0.143 (CI +0.04…+0.26); FTMO pass 85% / EV $2,589 vs twin 52% / $510.
  PASS. Five years 2021–25: 1,085 trades, +0.120R/trade (CI +0.05…+0.20). 2025 the weak year (+0.045).
  The NAS100 noise-area rule is the programme's first strategy confirmed on unseen data.
- 093 addendum: post-publication (from Jun 2024) +0.077R/trade vs +0.140 before; not significant (SE ~0.08) but in line
  with the usual ~50% post-publication decay. 1% challenge risk beats 0.5% at every assumed edge (+0.12 … 0).
