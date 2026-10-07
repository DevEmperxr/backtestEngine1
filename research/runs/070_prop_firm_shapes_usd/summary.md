# 070 — Prop-firm payoff shapes in USD, with each firm's commission and trades / days to pass and to profit

**Date:** 2026-10-07 · simulator: lib/prop_firms.py (firm_days, simulate_firm) · script:
research/regime/firm_shapes_070.py -> results.json, output.txt, firm_shapes_usd.png · **Status:** done (modelling)

## Changes vs 069 (user request)
- Everything in **USD**: FTMO's euro prices converted at EUR/USD 1.126 (FRED DEXUSEU, 2026-10-02).
- **Each firm's commission** (round trip per lot, public sources 2026-10-07): FTMO $3, Alpha Capital $2.50 (RAW
  account; its standard account is $0 commission with wider spreads, which can't be modelled here), The5ers $4,
  FundedNext $5, FundingPips $5 (sources say $3–5; the higher is used), E8 $5. Spreads: the same raw Dukascopy spread
  for all (firm-specific spreads not available).
- Edge measured **before commission** (spread included): 0 / +0.05 / +0.10 R per trade; each firm then charges its
  own commission (0.25–0.5 pip on ~6-pip stops = 0.04–0.08R per trade).
- New: median **trades (and trading days) to pass**, to the **first payout**, and until the **money received
  exceeds the fee** ("to profit"), over the attempts where that happens.

## Results: average $ per attempt after the fee (pass rate), best risk setting per firm
| program | fee | comm | edge 0 | edge +0.05R | edge +0.10R |
|---|---|---|---|---|---|
| **FTMO 1-step** | $89 | $3 | **+$311 (42%)** | **+$616 (53%)** | **+$1,108 (68%)** |
| Alpha Capital Pro 10% | $80* | $2.5 | +$195 (32%) | +$472 (46%) | +$871 (59%) |
| FTMO 2-step | $100 | $3 | +$130 (31%) | +$386 (42%) | +$794 (60%) |
| Alpha Capital Pro 8% | $80* | $2.5 | +$175 (35%) | +$335 (41%) | +$646 (54%) |
| FundedNext Stellar 2-step | $90 | $5 | +$153 (28%) | +$316 (35%) | +$654 (53%) |
| The5ers High Stakes | $75 | $4 | +$97 (24%) | +$293 (39%) | +$676 (56%) |
| FundingPips 2-step (8/5) | $60 | $5 | +$86 (26%) | +$211 (36%) | +$550 (53%) |
| E8 2-phase | $80* | $5 | +$23 (23%) | +$166 (34%) | +$368 (43%) |
| FundingPips 2-step Pro | $55 | $5 | +$19 (17%) | +$98 (28%) | +$241 (39%) |
\* fee not verified.

## Trades (trading days) at +0.05R edge before commission, best risk setting
| program | to pass | to first payout | until money received > fee |
|---|---|---|---|
| FTMO 1-step | 38 (59 d) | 52 (78 d) | 53 (80 d) |
| Alpha Capital Pro 10% | 77 (120 d) | 95 (145 d) | 98 (149 d) |
| FTMO 2-step | 79 (119 d) | 90 (140 d) | 94 (141 d) |
| Alpha Capital Pro 8% | 58 (87 d) | 74 (111 d) | 75 (115 d) |
| FundedNext Stellar 2-step (2% challenge risk) | 24 (36 d) | 37 (54 d) | 38 (58 d) |
| The5ers High Stakes | 75 (117 d) | 92 (141 d) | 97 (149 d) |
| FundingPips 2-step (8/5) | 73 (113 d) | 91 (137 d) | 97 (152 d) |
| E8 2-phase | 63 (96 d) | 77 (117 d) | 84 (126 d) |
| FundingPips 2-step Pro | 47 (69 d) | 57 (89 d) | 63 (97 d) |
Counts depend on the chosen risk: at 2% per trade the targets come ~twice as fast (fewer trades) but fewer attempts pass.

## Takeaways
- **FTMO 1-step stays first** at every edge, now also thanks to a low $3 commission. One 10% hurdle, 90% split.
  Passing typically takes ~40 trades (~2–3 months at this trade rate), money in hand ~50–55 trades.
- **Costs reshuffle the rest:** low-commission Alpha Capital moves up to second; FundedNext ($5) drops from second
  to the middle. On ~6-pip stops each extra $1/lot of commission costs ~0.017R per trade.
- **Even at zero edge before commission**, every program is positive on average in this model (the convex payoff),
  but the tight ones (E8, FundingPips Pro) are close to zero.
- If FTMO's commission is really $5 (not $3), its edge drops ~0.03R per trade: still first in this table.

## Caveats
Same as 069 (secondary-source rules and prices, funded accounts with the evaluation's rules, independent days,
one trade shape), plus: firm-specific spreads not modelled; Alpha's standard account (no commission, wider spreads)
not modelled; three fees unverified.

## Update (same day): FTMO's confirmed commission is $5 per round trip
The user shared FTMO's commission notice: forex **$2.50 per lot per side** ($5 round trip; previously $1.50/side).
FTMO rows re-simulated at $5 (ftmo_at_5usd.json):

| program | edge 0 | edge +0.05R | edge +0.10R | trades to pass / to profit (+0.05R) |
|---|---|---|---|---|
| FTMO 1-step ($5) | +$131 (31%) | +$377 (44%) | +$760 (59%) | 39 / 54 |
| FTMO 2-step ($5) | +$38 (24%) | +$187 (35%) | +$491 (46%) | 77 / 100 |

With the real commission, **FTMO 1-step falls from 1st to about 2nd** at +0.05R and +0.10R (behind Alpha Capital Pro 10%
at $2.50 RAW commission: +$472 / +$871), and to about 4th at zero edge. Alpha's fee and RAW-account terms are unverified.
FTMO 1-step remains well ahead of FTMO 2-step.
