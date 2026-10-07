# 072 — When to take profits out of a funded FTMO 1-step account (modelling)

**Date:** 2026-10-07 · script: research/regime/payout_policy_072.py -> results.json, payout_policy.png · **Status:** done
User question: "when do I pull out profits on the funded phase?"

## FTMO facts used (public sources, 2026-10-07)
First reward after 14 days of trading, then on demand; 90% split; fee refunded with the first payout; from the first
payout on, **max 1% risk per trade idea**; best-day rule not applied when funded; 10% max loss **trailing the highest
end-of-day balance** (never moves down). **Unknown:** what a payout does to the trailing floor. Two cases modelled:
"reset" (floor restarts 10% below the balance left) and "stays" (floor stays where the peak put it, so a payout
eats the cushion).

## Setup
Funded year (260 trading days), London-fade trade shape, FTMO $5 commission, edge before commission 0 / +0.10 /
+0.20 R (after costs ≈ −0.09 / +0.01 / +0.11 R per trade), risk 0.5% or 1%, 1,500 simulated years each.

## Average $ paid out in the first funded year, 1% risk (reset | stays)
| policy | edge ≈ −0.09R after costs | ≈ +0.01R | ≈ +0.11R |
|---|---|---|---|
| **every 2 weeks, take all profit** | $373 \| $320 | $759 \| $495 | $1,571 \| $807 |
| **on demand, take all once profit ≥ 1%** | **$400 \| $353** | **$781 \| $532** | **$1,571 \| $897** |
| on demand, ≥ 2% | $374 \| $310 | $748 \| $539 | $1,539 \| $857 |
| on demand, ≥ 5% | $286 \| $236 | $623 \| $390 | $1,414 \| $638 |
| every 2 weeks, keep a 2% buffer | $276 \| $213 | $616 \| $387 | $1,408 \| $759 |

Chance of breaching within the year (1% risk): ~18% / ~9% / ~3–5% for the three edge levels, nearly the same across
policies. At 0.5% risk payouts are lower but breaches rarer (e.g. +0.01R: $595–610, 5–7% breach).

## Takeaways
- **Take profits early and often:** first payout as soon as allowed (14 days), then whenever there's ~1% or more.
  Waiting for a big pile (5%) or keeping a buffer in the account **pays less in every case**.
- **Why a buffer doesn't help:** the max loss trails your highest end-of-day balance, so profit left in the account
  doesn't widen your cushion; the floor rises with it. Money left in is just money that can still be lost.
- **The unknown rule matters a lot:** if the floor "stays" after a payout, yearly payouts with a good strategy are
  roughly halved ($1,571 -> $807). **Ask FTMO support** exactly how the 1-step trailing max loss is set after a reward.
- Not modelled: FTMO's scaling plan (+25% balance every 4 months with consistent profit); check whether frequent
  withdrawals affect it.

## Update (same day): FTMO confirmed the reset
The user got FTMO's answer: "On the 1-Step FTMO Account, when a reward is withdrawn, the Maximum Loss Limit fully
resets, returning the first-day limit back to 90% of the initial simulated capital." So the **"reset" column is the
real one** (e.g. ~$1,571 a year at 1% risk with ≈ +0.11R after costs); the "stays" case doesn't apply. After a reward
the limit restarts at $9,000 and trails up again from the next end-of-day balances, so a buffer left in the account
only adds cushion until the next end of day. Conclusion unchanged: withdraw early and often.
