"""Generic prop-firm rule sets and a simulator to compare the payoff "shape" of firms (run 069).

A FirmRules describes one program on a $10k account (all limits in % of the initial balance). simulate_firm()
plays one paid attempt many times: the evaluation phase(s), then up to `funded_days` trading days funded with a
payout every `payout_every` trading days (profit withdrawn, account reset), fee refund after the n-th payout,
optional share of challenge profits. Trading days are drawn with replacement from a real trade history
(lib.prop.daily_R); `edge_shift` replaces every trade's R with (R - mean R + edge_shift) to give the same trade
shape a chosen average edge after costs (0 = zero-edge twin).

Simplifications (stated in the run summary): funded accounts keep the evaluation's daily/max-loss rules;
consistency/best-day rules apply to the evaluation only; trailing max-loss floors trail end-of-day balances;
a trader never opens a trade whose full stop could breach the daily limit, the own daily stop or the floor.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import polars as pl

from lib.prop import daily_R


@dataclass(frozen=True)
class FirmRules:
    name: str
    targets: tuple[float, ...]            # profit target per phase (%)
    daily_loss: float                     # max daily loss from the day's starting balance (%)
    max_loss: float                       # max overall loss (%)
    trailing_eod: bool = False            # max-loss floor trails the highest end-of-day balance
    trail_lock_at_initial: bool = False   # trailing floor stops once it reaches the initial balance
    min_days: int = 0                     # minimum trading days per phase
    min_profitable_days: int = 0          # days with P&L >= profitable_day_pct (e.g. The5ers)
    profitable_day_pct: float = 0.5
    best_day_frac: float | None = None    # best day <= frac x sum of positive days (consistency rule)
    split: float = 0.8                    # trader's share when funded
    refund_after_payouts: int | None = 1  # fee refunded with the n-th payout (None = never)
    challenge_profit_share: float = 0.0   # share of evaluation profits paid when funded (FundedNext 15%)
    fee: float = 89.0                     # indicative price for $10k (promos vary)


def _trail(firm: FirmRules, bal: float, peak: float, floor: float) -> tuple[float, float]:
    if firm.trailing_eod and bal > peak:
        peak = bal
        floor = peak - firm.max_loss
        if firm.trail_lock_at_initial:
            floor = min(floor, 0.0)
    return peak, floor


def run_phase(days, rng, firm: FirmRules, target: float, risk: float, day_stop: float | None, max_days: int):
    """One evaluation phase. Returns (result, trading days used, final balance %)."""
    bal, peak, floor = 0.0, 0.0, -firm.max_loss
    n_traded, n_prof, day_profits = 0, 0, []
    stop_at = min(firm.daily_loss, day_stop) if day_stop else firm.daily_loss
    for n in range(1, max_days + 1):
        day = days[rng.integers(len(days))]
        start, took = bal, False
        for r in day:
            if (bal - start) - risk < -stop_at or bal - risk <= floor:
                break
            bal += r * risk
            took = True
            if bal <= floor or (bal - start) <= -firm.daily_loss:
                return "fail", n, bal
        pnl = bal - start
        n_traded += took
        n_prof += pnl >= firm.profitable_day_pct
        if took:
            day_profits.append(pnl)
        peak, floor = _trail(firm, bal, peak, floor)
        if bal >= target and n_traded >= firm.min_days and n_prof >= firm.min_profitable_days:
            if firm.best_day_frac is not None:
                pos = sum(p for p in day_profits if p > 0)
                if pos <= 0 or max(day_profits) > firm.best_day_frac * pos:
                    continue
            return "pass", n, bal
    return "timeout", max_days, bal


def run_funded(days, rng, firm: FirmRules, risk: float, day_stop: float | None, n_days: int,
               payout_every: int, account: float):
    """Funded stage. Returns (payouts $, number of payouts, breached)."""
    bal, peak, floor, paid, n_pay = 0.0, 0.0, -firm.max_loss, 0.0, 0
    stop_at = min(firm.daily_loss, day_stop) if day_stop else firm.daily_loss
    for n in range(1, n_days + 1):
        day = days[rng.integers(len(days))]
        start = bal
        for r in day:
            if (bal - start) - risk < -stop_at or bal - risk <= floor:
                break
            bal += r * risk
            if bal <= floor or (bal - start) <= -firm.daily_loss:
                return paid, n_pay, True
        peak, floor = _trail(firm, bal, peak, floor)
        if n % payout_every == 0 and bal > 0:
            paid += bal / 100 * account * firm.split
            n_pay += 1
            bal, peak, floor = 0.0, 0.0, -firm.max_loss            # withdrawal resets the account
    if bal > 0:
        paid += bal / 100 * account * firm.split
        n_pay += 1
    return paid, n_pay, False


def simulate_firm(trades: pl.DataFrame, start: date, end: date, firm: FirmRules, *, risk_challenge: float = 1.0,
                  risk_funded: float = 0.5, day_stop: float | None = None, edge_shift: float | None = None,
                  account: float = 10_000.0, payout_every: int = 10, funded_days: int = 260,
                  max_days_per_phase: int = 260, n_sims: int = 2000, seed: int = 0) -> dict:
    days = daily_R(trades, start, end)
    if edge_shift is not None:
        allr = [r for d in days for r in d]
        mu = float(np.mean(allr)) if allr else 0.0
        days = [[r - mu + edge_shift for r in d] for d in days]
    rng = np.random.default_rng(seed)
    gross, passed = [], 0
    for _ in range(n_sims):
        ok, ch_profit = True, 0.0
        for tgt in firm.targets:
            res, _n, bal = run_phase(days, rng, firm, tgt, risk_challenge, day_stop, max_days_per_phase)
            if res != "pass":
                ok = False
                break
            ch_profit += max(bal, 0.0)
        if not ok:
            gross.append(0.0)
            continue
        passed += 1
        paid, n_pay, _ = run_funded(days, rng, firm, risk_funded, day_stop, funded_days, payout_every, account)
        refund = firm.fee if (firm.refund_after_payouts is not None and n_pay >= firm.refund_after_payouts) else 0.0
        share = firm.challenge_profit_share * ch_profit / 100 * account
        gross.append(paid + refund + share)
    g = np.array(gross)
    return {"firm": firm.name, "risk_challenge": risk_challenge, "risk_funded": risk_funded, "day_stop": day_stop,
            "pass_%": round(100 * passed / n_sims, 1), "expected_gross": round(float(g.mean()), 1),
            "EV_net": round(float(g.mean()) - firm.fee, 1), "value_per_fee": round(float(g.mean()) / firm.fee, 2),
            "P(net>0)_%": round(100 * float((g > firm.fee).mean()), 1)}
