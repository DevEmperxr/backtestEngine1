"""Prop-firm mode: FTMO-style costs, no overnight / weekend / rollover holding, and a challenge simulator.

    cfg = PropConfig()                                    # $5 / lot round trip, flat by 16:55 New York
    trades = engine.backtest(strategy, prop=cfg)          # commission_pips column, pips net of commission
    sim = simulate_challenge(trades, start, end, risk_pct=0.5)   # pass / fail probabilities (Monte Carlo)

Engine side (see Engine.backtest): with `prop`, every 1m bar closing at or after `flat_time_ny` and before the
17:00 New York rollover gets exit_signal=True and cannot open a trade, so nothing is ever held through the
rollover, overnight or over a weekend. Commission is charged per round trip in pips:
commission_usd_per_lot / pip_value_usd_per_lot (0.5 pips for $5 on a USD-quoted pair).

Challenge simulator (FTMO 2-step, defaults for the $10k account; all limits relative to the initial balance):
    phase 1: reach +10%, phase 2: reach +5%; at least 4 trading days per phase;
    fail if equity falls 5% below the day's starting balance (max daily loss) or 10% below the initial
    balance (max loss). Each trade risks `risk_pct` of the initial balance (lots = risk / stop), so a trade's
    money result = R x risk. Daily-loss safety: a trader never opens a trade whose full stop would breach the
    daily limit (the realistic way to trade the rule; floating loss within a trade can't exceed its stop because
    nothing is held through gaps). Days are drawn with replacement from the real calendar of trading days
    (including days without trades), so time-to-pass is realistic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time, timedelta

import numpy as np
import polars as pl

NY = "America/New_York"


@dataclass(frozen=True)
class PropConfig:
    commission_usd_per_lot: float = 5.0        # round trip
    pip_value_usd_per_lot: float = 10.0        # XXX/USD pairs (and gold at pip 0.1 with 100 oz lots)
    commission_pct_per_side: float | None = None   # metals/CFDs: % of notional per side (FTMO gold 0.0007% = 7e-6)
    extra_spread_pips: float = 0.0                 # per round trip: FTMO's spread minus our data's (index CFDs)
    flat_time_ny: time = time(16, 55)          # flat before the 17:00 New York rollover
    rollover_ny: time = time(17, 0)

    @property
    def commission_pips(self) -> float:
        return self.commission_usd_per_lot / self.pip_value_usd_per_lot


def flat_mask(close_time: pl.Expr, cfg: PropConfig) -> pl.Expr:
    """True on bars that close in [flat_time, rollover) New York: force flat, no entries."""
    t = close_time.dt.convert_time_zone(NY).dt.time()
    return (t >= cfg.flat_time_ny) & (t < cfg.rollover_ny)


def apply_prop_signals(sig: pl.DataFrame, cfg: PropConfig) -> pl.DataFrame:
    flat = flat_mask(pl.col("close_time"), cfg)
    ex = pl.col("exit_signal") if "exit_signal" in sig.columns else pl.lit(False)
    out = sig.with_columns(_prop_flat=flat.fill_null(False))
    return out.with_columns(
        long_signal=pl.col("long_signal") & ~pl.col("_prop_flat"),
        short_signal=pl.col("short_signal") & ~pl.col("_prop_flat"),
        exit_signal=(ex.fill_null(False) | pl.col("_prop_flat")),
    ).drop("_prop_flat")


def apply_prop_costs(trades: pl.DataFrame, cfg: PropConfig, pip: float = 0.0001) -> pl.DataFrame:
    if cfg.commission_pct_per_side is not None:
        # % of notional per side, both sides: price x pct x 2, in price units per unit -> pips
        c = pl.col("entry_price") * cfg.commission_pct_per_side * 2 / pip
    else:
        c = pl.lit(cfg.commission_pips, dtype=pl.Float64)
    # extra spread (FTMO wider than our data) is counted with the spread actually paid
    return trades.with_columns(commission_pips=c.cast(pl.Float64)).with_columns(
        pips=pl.col("pips") - pl.col("commission_pips") - cfg.extra_spread_pips,
        spread_pips_paid=pl.col("spread_pips_paid") + cfg.extra_spread_pips)


# FTMO gold (XAUUSD): $0 per lot, 0.0007% of notional per side (FTMO commission notice, 2026)
FTMO_GOLD = PropConfig(commission_usd_per_lot=0.0, commission_pct_per_side=7e-6)

# FTMO index CFDs: commission-free (user-confirmed 2026-10-07); spread top-up = FTMO typical spread minus our Dukascopy
# main-session median (US100 1.66 vs 1.46, GER40 1.58 vs ~1.44, JP225 10 vs 7.1 points)
FTMO_INDEX = {
    "NAS100": PropConfig(commission_usd_per_lot=0.0, extra_spread_pips=0.2),
    "GER40": PropConfig(commission_usd_per_lot=0.0, extra_spread_pips=0.15),
    "JPN225": PropConfig(commission_usd_per_lot=0.0, extra_spread_pips=2.9),
}


def prop_config_for(pair: str) -> PropConfig:
    """FTMO prop-mode settings for an instrument (FX default $5/lot; gold; index CFDs)."""
    pair = pair.upper()
    if pair.startswith("XAU"):
        return FTMO_GOLD
    return FTMO_INDEX.get(pair, PropConfig())


# --------------------------------------------------------------------------- #
# FTMO challenge simulator
# --------------------------------------------------------------------------- #

def daily_R(trades: pl.DataFrame, start: date, end: date) -> list[list[float]]:
    """One list of trade results in R (pips / stop, in exit order) per weekday (New York date) in [start, end]."""
    t = trades.sort("exit_time").with_columns(
        R=pl.col("pips") / pl.col("sl_pips"),
        d=pl.col("exit_time").dt.convert_time_zone(NY).dt.date())
    by_day: dict = {}
    for d, r in zip(t["d"].to_list(), t["R"].to_list()):
        by_day.setdefault(d, []).append(float(r))
    days, d = [], start
    while d <= end:
        if d.weekday() < 5:
            days.append(by_day.get(d, []))
        d += timedelta(days=1)
    return days


def _phase(days, rng, target, risk, daily_lim, max_lim, min_days, max_days, day_stop=None):
    """Run one phase. Returns ("pass"/"fail"/"timeout", trading days used). `day_stop` = the trader's own
    daily stop in % (stop trading for the day once a new trade's full stop could take the day below it)."""
    bal, traded_days = 0.0, 0                    # in % of the initial balance
    stop_at = min(daily_lim, day_stop) if day_stop else daily_lim
    for n in range(1, max_days + 1):
        day = days[rng.integers(len(days))]
        start_bal = bal
        took = False
        for r in day:
            if (bal - start_bal) - risk < -stop_at:        # its stop could breach the daily limit: skip
                break
            bal += r * risk
            took = True
            if bal <= -max_lim or (bal - start_bal) <= -daily_lim:
                return "fail", n
        traded_days += took
        if bal >= target and traded_days >= min_days:
            return "pass", n
    return "timeout", max_days


def simulate_challenge(trades: pl.DataFrame, start: date, end: date, *, risk_pct: float = 0.5,
                       targets: tuple[float, ...] = (10.0, 5.0), daily_loss_pct: float = 5.0,
                       max_loss_pct: float = 10.0, min_trading_days: int = 4, max_days_per_phase: int = 260,
                       n_sims: int = 5000, seed: int = 0, demean: bool = False) -> dict:
    """Monte Carlo pass probability of an FTMO-style multi-phase challenge for this trade history.
    `demean=True` subtracts the average R from every trade: a zero-edge twin with the same shape."""
    days = daily_R(trades, start, end)
    if demean:
        allr = [r for d in days for r in d]
        mu = float(np.mean(allr)) if allr else 0.0
        days = [[r - mu for r in d] for d in days]
    rng = np.random.default_rng(seed)
    outcomes, used = [], []
    for _ in range(n_sims):
        total, res = 0, "pass"
        for tgt in targets:
            res, n = _phase(days, rng, tgt, risk_pct, daily_loss_pct, max_loss_pct, min_trading_days, max_days_per_phase)
            total += n
            if res != "pass":
                break
        outcomes.append(res)
        used.append(total)
    o, u = np.array(outcomes), np.array(used)
    passed = o == "pass"
    return {"risk_pct": risk_pct, "pass_%": round(100 * passed.mean(), 1), "fail_%": round(100 * (o == "fail").mean(), 1),
            "timeout_%": round(100 * (o == "timeout").mean(), 1),
            "median_days_to_pass": int(np.median(u[passed])) if passed.any() else None,
            "trades_per_day": round(sum(len(d) for d in days) / len(days), 2), "n_days": len(days)}


def _funded(days, rng, risk, daily_lim, max_lim, n_days, payout_every, split, account, day_stop=None):
    """Funded stage: trade day by day; every `payout_every` trading days withdraw profit (trader keeps `split`)
    and reset to the initial balance. Ends on a breach or after `n_days`. Returns (payout $, days survived,
    number of payouts, breached)."""
    bal, paid, n_pay = 0.0, 0.0, 0
    stop_at = min(daily_lim, day_stop) if day_stop else daily_lim
    for n in range(1, n_days + 1):
        day = days[rng.integers(len(days))]
        start_bal = bal
        for r in day:
            if (bal - start_bal) - risk < -stop_at:
                break
            bal += r * risk
            if bal <= -max_lim or (bal - start_bal) <= -daily_lim:
                return paid, n, n_pay, True
        if n % payout_every == 0 and bal > 0:
            paid += bal / 100 * account * split
            n_pay += 1
            bal = 0.0
    if bal > 0:
        paid += bal / 100 * account * split
        n_pay += 1
    return paid, n_days, n_pay, False


def simulate_lifecycle(trades: pl.DataFrame, start: date, end: date, *, risk_challenge: float = 1.0,
                       risk_funded: float = 0.5, day_stop: float | None = None, fee: float = 89.0,
                       account: float = 10_000.0, split: float = 0.8, payout_every: int = 10,
                       funded_days: int = 260, targets: tuple[float, ...] = (10.0, 5.0),
                       daily_loss_pct: float = 5.0, max_loss_pct: float = 10.0, min_trading_days: int = 4,
                       max_days_per_phase: int = 260, n_sims: int = 3000, seed: int = 0,
                       demean: bool = False) -> dict:
    """Value of one paid attempt: challenge (FTMO 2-step) then up to `funded_days` trading days funded, with a
    payout every `payout_every` trading days (~2 weeks), profit split `split`, and the fee refunded with the
    first payout. `day_stop` = the trader's own daily stop (% of the account). Money in account currency."""
    days = daily_R(trades, start, end)
    if demean:
        allr = [r for d in days for r in d]
        mu = float(np.mean(allr)) if allr else 0.0
        days = [[r - mu for r in d] for d in days]
    rng = np.random.default_rng(seed)
    net, passed, payouts, surv, breached = [], 0, [], [], 0
    for _ in range(n_sims):
        ok = True
        for tgt in targets:
            res, _n = _phase(days, rng, tgt, risk_challenge, daily_loss_pct, max_loss_pct, min_trading_days,
                             max_days_per_phase, day_stop)
            if res != "pass":
                ok = False
                break
        if not ok:
            net.append(-fee)
            continue
        passed += 1
        paid, n, n_pay, br = _funded(days, rng, risk_funded, daily_loss_pct, max_loss_pct, funded_days,
                                     payout_every, split, account, day_stop)
        refund = fee if n_pay > 0 else 0.0
        net.append(paid + refund - fee)
        payouts.append(paid)
        surv.append(n)
        breached += br
    net_a = np.array(net)
    return {"risk_challenge": risk_challenge, "risk_funded": risk_funded, "day_stop": day_stop,
            "pass_%": round(100 * passed / n_sims, 1),
            "EV_per_attempt": round(float(net_a.mean()), 1),
            "P(net > 0)_%": round(100 * float((net_a > 0).mean()), 1),
            "funded_mean_payout": round(float(np.mean(payouts)), 1) if payouts else None,
            "funded_median_days_survived": int(np.median(surv)) if surv else None,
            "funded_breach_%": round(100 * breached / passed, 1) if passed else None}
