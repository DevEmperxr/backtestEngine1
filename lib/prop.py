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
    pip_value_usd_per_lot: float = 10.0        # XXX/USD pairs
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


def apply_prop_costs(trades: pl.DataFrame, cfg: PropConfig) -> pl.DataFrame:
    c = cfg.commission_pips
    return trades.with_columns(commission_pips=pl.lit(c, dtype=pl.Float64), pips=pl.col("pips") - c)


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


def _phase(days, rng, target, risk, daily_lim, max_lim, min_days, max_days):
    """Run one phase. Returns ("pass"/"fail"/"timeout", trading days used)."""
    bal, traded_days = 0.0, 0                    # in % of the initial balance
    for n in range(1, max_days + 1):
        day = days[rng.integers(len(days))]
        start_bal = bal
        took = False
        for r in day:
            if (bal - start_bal) - risk < -daily_lim:      # its stop could breach the daily limit: skip
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
