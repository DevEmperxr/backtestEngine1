"""Generic prop-firm rule sets and a simulator to compare the payoff "shape" of firms (runs 069–070).

A FirmRules describes one program on a $10k account (all limits in % of the initial balance). simulate_firm()
plays one paid attempt many times: the evaluation phase(s), then up to `funded_days` trading days funded with a
payout every `payout_every` trading days (profit withdrawn, account reset), fee refund after the n-th payout,
optional share of evaluation profits (paid when funded). Trading days are drawn with replacement from a list of
days of trade results in R (lib.prop.daily_R or prepared by the caller).

Also tracked (median over the attempts where it happens): trades and trading days to pass; trades and days until
the first payout; trades and days until the money received (payouts + refund + profit share) exceeds the fee.

Simplifications (stated in the run summaries): funded accounts keep the evaluation's daily/max-loss rules;
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
    fee: float = 89.0                     # $10k price in USD (promos vary)
    commission_usd: float = 5.0           # round trip per standard lot (forex)


def _trail(firm: FirmRules, bal: float, peak: float, floor: float) -> tuple[float, float]:
    if firm.trailing_eod and bal > peak:
        peak = bal
        floor = peak - firm.max_loss
        if firm.trail_lock_at_initial:
            floor = min(floor, 0.0)
    return peak, floor


def run_phase(days, rng, firm: FirmRules, target: float, risk: float, day_stop: float | None, max_days: int):
    """One evaluation phase. Returns (result, trading days used, final balance %, trades taken)."""
    bal, peak, floor = 0.0, 0.0, -firm.max_loss
    n_traded, n_prof, day_profits, n_trades = 0, 0, [], 0
    stop_at = min(firm.daily_loss, day_stop) if day_stop else firm.daily_loss
    for n in range(1, max_days + 1):
        day = days[rng.integers(len(days))]
        start, took = bal, False
        for r in day:
            if (bal - start) - risk < -stop_at or bal - risk <= floor:
                break
            bal += r * risk
            took = True
            n_trades += 1
            if bal <= floor or (bal - start) <= -firm.daily_loss:
                return "fail", n, bal, n_trades
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
            return "pass", n, bal, n_trades
    return "timeout", max_days, bal, n_trades


def run_funded(days, rng, firm: FirmRules, risk: float, day_stop: float | None, n_days: int,
               payout_every: int, account: float):
    """Funded stage. Returns (list of payouts as (day, trades so far, $ amount), breached)."""
    bal, peak, floor, n_trades = 0.0, 0.0, -firm.max_loss, 0
    events = []
    stop_at = min(firm.daily_loss, day_stop) if day_stop else firm.daily_loss
    for n in range(1, n_days + 1):
        day = days[rng.integers(len(days))]
        start = bal
        for r in day:
            if (bal - start) - risk < -stop_at or bal - risk <= floor:
                break
            bal += r * risk
            n_trades += 1
            if bal <= floor or (bal - start) <= -firm.daily_loss:
                return events, True
        peak, floor = _trail(firm, bal, peak, floor)
        if n % payout_every == 0 and bal > 0:
            events.append((n, n_trades, bal / 100 * account * firm.split))
            bal, peak, floor = 0.0, 0.0, -firm.max_loss            # withdrawal resets the account
    if bal > 0:
        events.append((n_days, n_trades, bal / 100 * account * firm.split))
    return events, False


def firm_days(trades: pl.DataFrame, start: date, end: date, firm: FirmRules, edge_before_commission: float) -> list[list[float]]:
    """Days of trade results in R for this firm: the trade shape of `trades` with its average R (before
    commission) replaced by `edge_before_commission`, then this firm's commission charged on every trade.
    `trades` must carry pips net of a commission given in `commission_pips` (added back here)."""
    t = trades.with_columns(R0=(pl.col("pips") + pl.col("commission_pips")) / pl.col("sl_pips"))
    mu = float(t["R0"].mean())
    comm_pips = firm.commission_usd / 10.0                      # $10 per pip per lot on XXX/USD
    t = t.with_columns(pips=(pl.col("R0") - mu + edge_before_commission) * pl.col("sl_pips") - comm_pips)
    return daily_R(t, start, end)


def simulate_firm(days: list[list[float]], firm: FirmRules, *, risk_challenge: float = 1.0, risk_funded: float = 0.5,
                  day_stop: float | None = None, account: float = 10_000.0, payout_every: int = 10,
                  funded_days: int = 260, max_days_per_phase: int = 260, n_sims: int = 2000, seed: int = 0) -> dict:
    """Value of one attempt at `firm`, given days of trade results in R (see firm_days)."""
    rng = np.random.default_rng(seed)
    gross, passed = [], 0
    to_pass_t, to_pass_d, to_pay_t, to_pay_d, to_profit_t, to_profit_d = [], [], [], [], [], []
    for _ in range(n_sims):
        ok, ch_profit, tr_used, d_used = True, 0.0, 0, 0
        for tgt in firm.targets:
            res, n, bal, nt = run_phase(days, rng, firm, tgt, risk_challenge, day_stop, max_days_per_phase)
            tr_used += nt
            d_used += n
            if res != "pass":
                ok = False
                break
            ch_profit += max(bal, 0.0)
        if not ok:
            gross.append(0.0)
            continue
        passed += 1
        to_pass_t.append(tr_used)
        to_pass_d.append(d_used)
        events, _ = run_funded(days, rng, firm, risk_funded, day_stop, funded_days, payout_every, account)
        money = firm.challenge_profit_share * ch_profit / 100 * account
        total = money
        for k, (day_n, trades_n, amount) in enumerate(events, start=1):
            total += amount + (firm.fee if firm.refund_after_payouts == k else 0.0)
            if k == 1:
                to_pay_t.append(tr_used + trades_n)
                to_pay_d.append(d_used + day_n)
            if total > firm.fee and (len(to_profit_t) < passed):
                to_profit_t.append(tr_used + trades_n)
                to_profit_d.append(d_used + day_n)
        gross.append(total)
    g = np.array(gross)
    med = lambda x: int(np.median(x)) if x else None
    return {"firm": firm.name, "risk_challenge": risk_challenge, "risk_funded": risk_funded, "day_stop": day_stop,
            "fee": firm.fee, "commission_usd": firm.commission_usd,
            "pass_%": round(100 * passed / n_sims, 1), "expected_gross": round(float(g.mean()), 1),
            "EV_net": round(float(g.mean()) - firm.fee, 1), "value_per_fee": round(float(g.mean()) / firm.fee, 2),
            "P(net>0)_%": round(100 * float((g > firm.fee).mean()), 1),
            "trades_to_pass": med(to_pass_t), "days_to_pass": med(to_pass_d),
            "trades_to_first_payout": med(to_pay_t), "days_to_first_payout": med(to_pay_d),
            "trades_to_profit": med(to_profit_t), "days_to_profit": med(to_profit_d)}
