# 069 — Which prop firm has the most lenient (convex) payoff shape? (modelling)

**Date:** 2026-10-07 · simulator: lib/prop_firms.py · script: research/regime/firm_shapes_069.py -> results.json,
output.txt, firm_shapes.png · **Status:** done (descriptive modelling; uses only 2023–24 trades for the shape)

## Method
Same trade shape for every firm: EURUSD London-fade trades 2023–24 under FTMO costs (~0.8 trades/day, ~6-pip
stops), with the average result replaced by **0, −0.05 or −0.10 R per trade** (realistic for "no real edge after
costs"). One attempt = evaluation phase(s), then up to a year funded with a payout every ~2 weeks. Best of a small
risk grid per firm (challenge 1% or 2%, funded 0.5% or 1%), own daily stop at 40% of the firm's daily limit.
Ranked by **expected money out per attempt** (payouts + refund + challenge profit share), and net of an indicative
$10k fee.

## Rules used (public sources, 2026-10-07; check the firm's site before buying)
| program | targets | daily / max loss | other | split | refund | indicative fee |
|---|---|---|---|---|---|---|
| FTMO 2-step | 10% / 5% | 5% / 10% static | 4 min days | 80% | 1st payout | €89 promo (€155 std) |
| FTMO 1-step | 10% | 3% / 10% trailing (end of day) | best day ≤ 50% | 90% | 1st payout | ~€79 |
| FundedNext Stellar 2-step | 8% / 5% | 5% / 10% static | 5 min days; 15% of challenge profits paid | 80% | 1st payout | ~$90 |
| The5ers High Stakes | 10% / 5% | 5% / 10% | 3 profitable days (≥ 0.5%) | 80% | yes | ~$75 |
| FundingPips 2-step (8/5) | 8% / 5% | 5% / 10% static | 3 min days | 80% | after 4th payout | ~$60 |
| FundingPips 2-step Pro | 6% / 6% | 3% / 6% | 45% consistency | 80% | after 4th payout | ~$55 |
| Alpha Capital Pro 10% | 10% / 5% | 5% / 10% static | 3 min days | 80% | yes | ~$80 (unverified) |
| Alpha Capital Pro 8% | 8% / 5% | 4% / 8% static | 3 min days | 80% | yes | ~$80 (unverified) |
| E8 2-phase | 8% / 5% | 4% / 8% | 35% best day | 80% | none | ~$80 (unverified) |

## Results (net of the indicative fee; pass rate in brackets)
| firm | edge 0 | edge −0.05R | edge −0.10R |
|---|---|---|---|
| **FTMO 1-step** | **+$553 (51%)** | **+$241 (39%)** | **+$89 (26%)** |
| FundedNext Stellar 2-step | +$508 (46%) | +$209 (28%) | +$70 (21%) |
| FundingPips 2-step (8/5) | +$409 (45%) | +$170 (30%) | +$46 (24%) |
| FTMO 2-step | +$331 (41%) | +$115 (26%) | +$20 (20%) |
| The5ers High Stakes | +$326 (40%) | +$140 (26%) | +$39 (22%) |
| Alpha Capital Pro 10% | +$323 (40%) | +$131 (26%) | +$31 (20%) |
| Alpha Capital Pro 8% | +$260 (40%) | +$97 (25%) | +$1 (19%) |
| E8 2-phase | +$228 (41%) | +$92 (27%) | −$9 (18%) |
| FundingPips 2-step Pro | +$168 (36%) | +$45 (24%) | +$0 (16%) |

## Takeaways
- **Most lenient shape in this model: FTMO 1-step**, first at every edge level. One phase instead of two (no second
  hurdle), a 90% split, and a 10% loss cushion equal to the target outweigh its 3% daily limit, trailing floor and
  50% best-day rule for this trade shape (~1 trade a day, 1% risk, which never gets near 3% in a day).
- **FundedNext Stellar 2-step** is second: 8% first target, plus 15% of challenge profits paid when funded.
- **FundingPips (8/5)** is cheap per dollar of fee, but its fee only comes back after the 4th payout.
- **Tighter programs** (6–8% max loss, 3–4% daily, strict consistency rules: FundingPips Pro, E8, Alpha 8%) are the
  least lenient: cheaper targets don't make up for the smaller cushion.
- The ranking is about **rules only**. Each firm's **costs** (commission, spreads) shift the edge itself: a firm with
  0.3 pip higher costs moves a 6-pip-stop strategy ~0.05R down, about one column in the table.

## Caveats
Rules and prices come from secondary sources and change often; funded accounts are modelled with the evaluation's
loss rules; consistency rules only in the evaluation; days drawn independently (no losing streaks); one trade shape.
For strategies with several trades a day or bigger daily swings, the 3% daily limit of FTMO 1-step would bite more.
