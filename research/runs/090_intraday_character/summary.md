# 090 — Do the indices trend or mean-revert inside the cash session? (descriptive, 2023 + 2024)

**Date:** 2026-10-07 · script: research/regime/intraday_character_090.py · numbers results.json
**Why:** user asked why the 079 noise-area rule worked on NAS100 but not GER40 / JPN225 (089).

| | days | variance ratio (30-min, in session) | 30-min autocorr | move so far vs rest of day | gap share of |move| |
|---|---|---|---|---|---|
| NAS100 | 511 | 1.09 (mild trending) | +0.011 | +0.003 | 41% |
| GER40 | 515 | **1.01 (random)** | +0.007 | −0.005 | 40% |
| JPN225 | 514 | **1.21 (most trending)** | +0.050 | +0.049 | **54%** |

Reading (sampling error of the VR roughly ±0.1):
- GER40 has no intraday trend to catch; the momentum rule mostly whipsaws (725 trades, negative before costs).
- JPN225 does trend (+0.056R before costs in 089) but the spread (~0.1R per trade) eats it, and more than half of its
  movement happens overnight (gap), leaving less inside the cash session.
- NAS100 trends only mildly on average; the noise-area rule wins on the large-move days where it is in the market,
  consistent with US-specific flows (option-dealer hedging, leveraged-ETF rebalancing) that push with big moves.
