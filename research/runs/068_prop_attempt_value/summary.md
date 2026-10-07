# 068 — What is one €89 FTMO attempt worth? Challenge + a year funded, by risk setting and by edge

**Date:** 2026-10-07 · simulator: lib/prop.py `simulate_lifecycle` · analysis: research/regime/clean_check_067.py
(+ edge_needed.json from a fixed-edge sweep) · **Status:** done (descriptive / modelling)

## Model
FTMO 2-step $10k (+10%, +5%; −5% daily; −10% max; ≥ 4 trading days), then up to 260 trading days funded: payout
every 10 trading days if in profit (80% split, profit withdrawn, account back to $10k), fee refunded with the first
payout, account lost on a breach. Separate risk per trade in the challenge and when funded; optional own daily stop.
Trading days drawn with replacement from a real trade history (no regime streaks: optimistic for streaky losers).
Fee €89 treated as $89.

## Results (trade shape: the London fade, ~0.8 trades/day, ~6-pip stops)
| trades used | best setting (challenge / funded / own daily stop) | pass | **EV per attempt** | P(come out ahead) |
|---|---|---|---|---|
| in-sample 2023–24 (+0.10R/trade) | 1% / 1% / 2% | 74% | **+$1,409** | 69% |
| clean 2025 (−0.18R/trade) | 2% / 1% / none | 6% | **−$75** | 3% |
| zero-edge twin | 1% / 1% / 2% | 43% | **+$390** | 37% |

Edge sweep (same shape, every trade shifted to a fixed average R after costs; 1% challenge, 2% own daily stop):
| average R per trade after costs | pass | EV (funded 0.5%) | EV (funded 1%) |
|---|---|---|---|
| −0.15 | 8% | −$74 | −$60 |
| −0.10 | 15–16% | −$46 | **−$1** |
| −0.05 | 28% | +$28 | +$134 |
| 0.00 | 46% | +$173 | +$415 |
| +0.05 | 63–64% | +$428 | +$893 |
| +0.10 | 78% | +$788 | +$1,548 |

## Takeaways
- **Convexity is real and large:** a strategy with exactly zero edge after costs is worth about +$170 to +$400 per
  €89 attempt in this model; break-even is around **−0.05 to −0.10R per trade after costs**.
- **But costs are the trap:** for small-stop trades, FTMO costs are ~0.1R per trade, so "zero edge before costs" is
  about −0.1R after costs: break-even at best. The 2025 London fade (−0.18R) loses almost the whole fee.
- **Risk settings:** ~1% per trade in the challenge was best; a **2% own daily stop** raised pass rates (e.g. zero
  edge 28% -> 43%) by cutting bad days short. Funded risk: higher (1%) maximises average payout but most accounts
  breach within the year (46–75%); 0.5% keeps most accounts alive with lower payouts.
- **Caveats:** days are drawn independently (real losing streaks, like 2025, cluster); FTMO's exact payout/scaling
  terms, slippage, and prohibited-practice rules are not modelled; results depend on the trade shape used.
