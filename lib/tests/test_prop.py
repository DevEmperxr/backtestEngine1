"""Prop-firm mode (lib/prop.py + Engine.backtest(prop=...)) and the FTMO challenge simulator."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import polars as pl
import pytest

from lib.engine import Engine
from lib.prop import PropConfig, simulate_challenge
from lib.tests.test_engine import F, Tr, _ColumnStrategy, _flat_path

UTC = timezone.utc


def _sig(start: datetime, n: int) -> pl.DataFrame:
    """n 1-minute signal bars from `start`, flat prices (bid 1.1000 / ask 1.1002)."""
    ts = [start + timedelta(minutes=i) for i in range(n)]
    return pl.DataFrame({
        "timestamp": ts, "close_time": [t + timedelta(minutes=1) for t in ts],
        "bid_open": [1.1000] * n, "bid_high": [1.1000] * n, "bid_low": [1.1000] * n, "bid_close": [1.1000] * n,
        "ask_open": [1.1002] * n, "ask_high": [1.1002] * n, "ask_low": [1.1002] * n, "ask_close": [1.1002] * n,
    })


# 2024-06-03 is a Monday; New York is UTC-4 (EDT): 20:45 UTC = 16:45 New York
START = datetime(2024, 6, 3, 20, 45, tzinfo=UTC)


def test_prop_forces_flat_before_rollover_and_charges_commission():
    sig = _sig(START, 30)                                   # 16:45 -> 17:15 New York
    base = _flat_path(40 * 60, start=START)
    longs = [F, Tr] + [F] * 28                              # signal on the bar closing 16:47 -> entry 16:47
    plain = Engine(sig, base).backtest(_ColumnStrategy(longs, [F] * 30)).row(0, named=True)
    assert plain["exit_reason"] == "end_of_data"
    t = Engine(sig, base).backtest(_ColumnStrategy(longs, [F] * 30), prop=PropConfig())
    row = t.row(0, named=True)
    assert row["exit_reason"] == "exit_signal"
    # flat bar = first bar closing at 16:55 New York (20:55 UTC); filled at its close
    assert row["exit_time"] == datetime(2024, 6, 3, 20, 55, tzinfo=UTC)
    assert row["commission_pips"] == pytest.approx(0.5)
    assert row["pips"] == pytest.approx(-2.0 - 0.5)        # 2-pip spread + 0.5-pip commission


def test_prop_blocks_entries_in_the_flat_window():
    sig = _sig(START, 30)
    base = _flat_path(40 * 60, start=START)
    longs = [F] * 11 + [Tr] + [F] * 18                      # signal bar closes 16:57 New York
    t = Engine(sig, base).backtest(_ColumnStrategy(longs, [F] * 30), prop=PropConfig())
    assert t.height == 0


def test_prop_commission_setting():
    assert PropConfig(commission_usd_per_lot=7.0).commission_pips == pytest.approx(0.7)


def _trades_from_days(days: list[list[float]], start: date) -> pl.DataFrame:
    rows, d, i = [], start, 0
    while i < len(days):
        if d.weekday() < 5:
            for k, r in enumerate(days[i]):
                t = datetime(d.year, d.month, d.day, 14, k, tzinfo=UTC)
                rows.append({"exit_time": t, "pips": r * 10.0, "sl_pips": 10.0})
            i += 1
        d += timedelta(days=1)
    return pl.DataFrame(rows, schema={"exit_time": pl.Datetime("ns", "UTC"), "pips": pl.Float64, "sl_pips": pl.Float64})


def test_simulator_always_winning_passes_after_target_days():
    start = date(2024, 1, 1)
    tr = _trades_from_days([[1.0]] * 20, start)
    s = simulate_challenge(tr, start, start + timedelta(days=27), risk_pct=1.0, n_sims=50)
    assert s["pass_%"] == 100.0
    assert s["median_days_to_pass"] == 15                    # 10 days to +10%, 5 days to +5%


def test_simulator_always_losing_fails():
    start = date(2024, 1, 1)
    tr = _trades_from_days([[-1.0]] * 20, start)
    s = simulate_challenge(tr, start, start + timedelta(days=27), risk_pct=1.0, n_sims=50)
    assert s["fail_%"] == 100.0


def test_simulator_daily_safety_skips_trades_that_could_breach():
    # each day: three -1R trades at 3% risk; the 2nd would risk -6% < -5% daily limit, so it is skipped
    start = date(2024, 1, 1)
    tr = _trades_from_days([[-1.0, -1.0, -1.0]] * 20, start)
    s = simulate_challenge(tr, start, start + timedelta(days=27), risk_pct=3.0, n_sims=20)
    assert s["fail_%"] == 100.0                               # fails on max loss (-12% after 4 days), never daily


def test_lifecycle_always_winning_collects_payouts_and_refund():
    from lib.prop import simulate_lifecycle
    start = date(2024, 1, 1)
    tr = _trades_from_days([[1.0]] * 40, start)
    s = simulate_lifecycle(tr, start, start + timedelta(days=55), risk_challenge=1.0, risk_funded=0.5,
                           funded_days=20, payout_every=10, n_sims=20)
    assert s["pass_%"] == 100.0
    # funded: +0.5% a day for 20 days -> two payouts of 5% x 10k x 0.8 = 400 each; + fee refund - fee
    assert s["funded_mean_payout"] == pytest.approx(800.0)
    assert s["EV_per_attempt"] == pytest.approx(800.0)


def test_lifecycle_always_losing_loses_the_fee():
    from lib.prop import simulate_lifecycle
    start = date(2024, 1, 1)
    tr = _trades_from_days([[-1.0]] * 40, start)
    s = simulate_lifecycle(tr, start, start + timedelta(days=55), n_sims=20, fee=89.0)
    assert s["pass_%"] == 0.0 and s["EV_per_attempt"] == pytest.approx(-89.0)


def test_own_daily_stop_limits_the_day():
    # three -1R trades a day at 1% risk with a 1.5% own daily stop: only one trade per day is taken
    start = date(2024, 1, 1)
    tr = _trades_from_days([[-1.0, -1.0, -1.0]] * 30, start)
    a = simulate_challenge(tr, start, start + timedelta(days=41), risk_pct=1.0, n_sims=20)
    from lib.prop import simulate_lifecycle
    b = simulate_lifecycle(tr, start, start + timedelta(days=41), risk_challenge=1.0, day_stop=1.5, n_sims=20)
    assert a["fail_%"] == 100.0 and b["pass_%"] == 0.0
