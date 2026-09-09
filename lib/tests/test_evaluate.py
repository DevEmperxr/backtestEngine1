"""Tests for lib/evaluate.py — §3.1 normal metrics and §3.2 deterministic adversarial."""

from datetime import datetime, timedelta, timezone
from math import sqrt

import polars as pl
import pytest

import numpy as np

from lib.evaluate import adversarial, bootstrap_ci, evaluate, mc_drawdown

UTC = timezone.utc
T0 = datetime(2024, 1, 1, 12, tzinfo=UTC)


def at(days: float, hours: float = 0.0) -> datetime:
    return T0 + timedelta(days=days, hours=hours)


def trades(pips, exit_times, *, entry_times=None, directions=None, spread=0.5) -> pl.DataFrame:
    n = len(pips)
    entry_times = entry_times or [t - timedelta(minutes=30) for t in exit_times]
    directions = directions or ["long"] * n
    spread = spread if isinstance(spread, (list, tuple)) else [spread] * n
    return pl.DataFrame({
        "entry_time": entry_times,
        "entry_price": [1.10] * n,
        "direction": directions,
        "exit_time": list(exit_times),
        "exit_price": [1.10] * n,
        "pips": [float(p) for p in pips],
        "exit_reason": ["tp" if p > 0 else "sl" for p in pips],
        "spread_pips_paid": [float(s) for s in spread],
    })


# --------------------------------------------------------------------------- #
# core scalars
# --------------------------------------------------------------------------- #

def test_win_rate_expectancy_profit_factor_avgs():
    pips = [20, 20, 20, 20, -10, -10, -10, -10, -10, -10]
    s = evaluate(trades(pips, [at(i) for i in range(10)]))["summary"]
    assert s["n_trades"] == 10
    assert s["win_rate"] == 40.0
    assert s["expectancy_pips"] == 2.0
    assert s["profit_factor"] == pytest.approx(80 / 60)
    assert s["avg_win_pips"] == 20.0
    assert s["avg_loss_pips"] == -10.0
    assert s["total_pips"] == 20.0                           # 4*20 - 6*10
    assert s["total_return_pct"] == pytest.approx(20.0 / 10_000 * 100)


def test_pip_value_scales_dollar_metrics_not_pip_metrics():
    pips = [20, 20, 20, 20, -10, -10, -10, -10, -10, -10]
    f = trades(pips, [at(i) for i in range(10)])
    s = evaluate(f, starting_balance=10_000, pip_value=10.0)["summary"]
    assert s["expectancy_pips"] == 2.0                       # unchanged
    assert s["total_pips"] == 20.0                           # unchanged
    assert s["total_return_pct"] == pytest.approx(20.0 * 10 / 10_000 * 100)


# --------------------------------------------------------------------------- #
# drawdown — exact peak -> trough
# --------------------------------------------------------------------------- #

def test_max_drawdown_exact_pct_and_date():
    # equity: 10000 -> 12500 (peak) -> 10000 (trough, -20%) -> 10500
    ex = [at(0), at(1), at(2)]
    s = evaluate(trades([2500, -2500, 500], ex), starting_balance=10_000, pip_value=1.0)["summary"]
    assert s["max_drawdown_pct"] == pytest.approx(-20.0)
    assert s["max_drawdown_date"] == ex[1]


def test_no_drawdown_gives_zero_and_no_date():
    s = evaluate(trades([10, 20, 30], [at(0), at(1), at(2)]))["summary"]
    assert s["max_drawdown_pct"] == 0.0
    assert s["max_drawdown_date"] is None


def test_equity_curve_shape():
    f = trades([10, -5, 8], [at(0), at(1), at(2)])
    ec = evaluate(f, starting_balance=10_000, pip_value=1.0)["equity_curve"]
    assert ec.columns == ["exit_time", "cum_pips", "equity", "drawdown_pct"]
    assert ec.height == 3
    assert ec["cum_pips"].to_list() == [10.0, 5.0, 13.0]
    assert ec["equity"].to_list() == [10_010.0, 10_005.0, 10_013.0]
    assert (ec["drawdown_pct"] <= 0).all()


# --------------------------------------------------------------------------- #
# monthly
# --------------------------------------------------------------------------- #

def test_monthly_breakdown_three_months():
    jan, feb, mar = datetime(2024, 1, 10, tzinfo=UTC), datetime(2024, 2, 5, tzinfo=UTC), datetime(2024, 3, 20, tzinfo=UTC)
    f = trades(
        [10, -5, 20, -10, -10, 30],
        [jan, jan + timedelta(days=3), feb, mar, mar + timedelta(hours=1), mar + timedelta(hours=2)],
    )
    m = evaluate(f, pip_value=2.0)["monthly"]
    assert m["month"].to_list() == [datetime(2024, 1, 1).date(),
                                    datetime(2024, 2, 1).date(),
                                    datetime(2024, 3, 1).date()]
    assert m["pips"].to_list() == [5.0, 20.0, 10.0]
    assert m["pnl"].to_list() == [10.0, 40.0, 20.0]           # * pip_value
    assert m["n_trades"].to_list() == [2, 1, 3]
    assert m["win_rate"].to_list() == pytest.approx([50.0, 100.0, 100 / 3])


# --------------------------------------------------------------------------- #
# Sharpe / Sortino
# --------------------------------------------------------------------------- #

def test_sharpe_matches_hand_computation():
    daily_pips = [30, -10, 20, -5, 15]                        # one trade per day
    f = trades(daily_pips, [at(i) for i in range(5)])
    s = evaluate(f, starting_balance=10_000, pip_value=1.0)["summary"]

    dr = pl.Series([p / 10_000 for p in daily_pips])
    expected = dr.mean() / dr.std() * sqrt(252)               # ddof=1, rf=0
    assert s["sharpe"] == pytest.approx(expected)

    downside = dr.filter(dr < 0)
    expected_sortino = dr.mean() / downside.std() * sqrt(252)
    assert s["sortino"] == pytest.approx(expected_sortino)


def test_single_trading_day_sharpe_is_none_not_error():
    # three trades, all exiting the same calendar day -> one daily return -> std undefined
    day = datetime(2024, 6, 3, tzinfo=UTC)
    f = trades([10, -20, 5], [day + timedelta(hours=h) for h in (1, 2, 3)])
    s = evaluate(f)["summary"]
    assert s["sharpe"] is None
    assert s["sortino"] is None


# --------------------------------------------------------------------------- #
# edge cases
# --------------------------------------------------------------------------- #

def test_empty_frame_no_crash():
    r = evaluate(pl.DataFrame())
    s = r["summary"]
    assert s["n_trades"] == 0
    assert s["total_pips"] == 0.0 and s["total_return_pct"] == 0.0
    assert s["max_drawdown_pct"] == 0.0
    assert s["win_rate"] is None and s["sharpe"] is None and s["mar"] is None
    assert r["equity_curve"].height == 0
    assert r["monthly"].height == 0
    assert r["equity_curve"].columns == ["exit_time", "cum_pips", "equity", "drawdown_pct"]


def test_all_winning_frame_profit_factor_is_inf():
    s = evaluate(trades([10, 20, 30, 15], [at(i) for i in range(4)]))["summary"]
    assert s["profit_factor"] == float("inf")
    assert s["avg_loss_pips"] is None
    assert s["win_rate"] == 100.0


def test_all_losing_frame():
    s = evaluate(trades([-10, -20, -5], [at(i) for i in range(3)]))["summary"]
    assert s["profit_factor"] == 0.0                          # gross_win 0, gross_loss != 0
    assert s["avg_win_pips"] is None
    assert s["win_rate"] == 0.0


def test_breakeven_trade_counts_as_neither_win_nor_loss():
    s = evaluate(trades([10, 0, -10], [at(0), at(1), at(2)]))["summary"]
    assert s["n_trades"] == 3
    assert s["win_rate"] == pytest.approx(100 / 3)            # 1 win of 3
    assert s["avg_win_pips"] == 10.0
    assert s["avg_loss_pips"] == -10.0                        # the 0 excluded


def test_mar_is_cagr_over_abs_drawdown_fraction():
    # 2 years, ends up +21% ($10k -> $12.1k), one -20% drawdown along the way
    f = trades([2500, -2500, 2100], [at(0), at(365.25), at(2 * 365.25)],
               entry_times=[at(-1), at(365.25) - timedelta(hours=1), at(2 * 365.25) - timedelta(hours=1)])
    s = evaluate(f, starting_balance=10_000, pip_value=1.0)["summary"]
    span_years = (f["exit_time"].max() - f["entry_time"].min()).total_seconds() / 86_400 / 365.25
    cagr = (12_100 / 10_000) ** (1 / span_years) - 1
    assert s["mar"] == pytest.approx(cagr / abs(s["max_drawdown_pct"] / 100))


# --------------------------------------------------------------------------- #
# adversarial — deterministic subset (spec §3.2)
# --------------------------------------------------------------------------- #

def _many(pips, spread=0.5):
    """Trade frame with `len(pips)` trades, one per day."""
    return trades(pips, [at(i) for i in range(len(pips))], spread=spread)


def test_gross_vs_net_costs_ate_the_edge():
    # net = -2, spread paid = 12  ->  gross = +10  ->  the edge was real
    f = trades([-5, -5, 8], [at(0), at(1), at(2)], spread=[4, 4, 4])
    g = adversarial(f, min_trades=1)["gross_vs_net"]
    assert g["net_pips"] == pytest.approx(-2.0)
    assert g["spread_paid_pips"] == pytest.approx(12.0)
    assert g["gross_pips"] == pytest.approx(10.0)
    assert "costs ate it" in g["edge_assessment"]


def test_gross_vs_net_no_edge():
    # net = -15, spread paid = 3  ->  gross = -12  ->  there was never an edge
    f = trades([-5, -5, -5], [at(0), at(1), at(2)], spread=[1, 1, 1])
    g = adversarial(f, min_trades=1)["gross_vs_net"]
    assert g["gross_pips"] == pytest.approx(-12.0)
    assert "no edge" in g["edge_assessment"]


def test_gross_equals_net_plus_spread_always():
    f = _many([3, -7, 12, -4, -1, 9], spread=[0.4, 0.6, 0.3, 0.5, 0.2, 0.7])
    g = adversarial(f, min_trades=1)["gross_vs_net"]
    assert g["gross_pips"] == pytest.approx(g["net_pips"] + g["spread_paid_pips"])


def test_adversarial_requires_spread_column():
    f = trades([1, 2, 3], [at(0), at(1), at(2)]).drop("spread_pips_paid")
    with pytest.raises(ValueError, match="spread_pips_paid"):
        adversarial(f, min_trades=1)


def test_exclude_best_month():
    jan = datetime(2024, 1, 10, tzinfo=UTC)
    feb = datetime(2024, 2, 10, tzinfo=UTC)
    mar = datetime(2024, 3, 10, tzinfo=UTC)
    f = trades(
        [10, -5, 50, -10, -10],
        [jan, jan + timedelta(days=1), feb, mar, mar + timedelta(hours=1)],
    )
    ebm = adversarial(f, min_trades=1)["ex_best_month"]
    assert ebm["dropped_month"] == datetime(2024, 2, 1).date()   # the middle month, clearly best
    assert ebm["dropped_month_pips"] == pytest.approx(50.0)
    assert ebm["full_pips"] == pytest.approx(35.0)
    assert ebm["pips"] == pytest.approx(35.0 - 50.0)             # exactly Feb removed


def test_exclude_best_n_trades_removes_the_outlier():
    f = _many([100] + [1] * 9)                                  # one huge winner, nine +1s
    r = adversarial(f, exclude_best_pct=[0.1], min_trades=1)["ex_best_trades"]
    assert len(r) == 1
    assert r[0]["pct"] == 0.1
    assert r[0]["n_dropped"] == 1                               # ceil(10 * 0.1)
    assert r[0]["pips"] == pytest.approx(9.0)                    # the 100 removed


def test_exclude_best_n_trades_default_two_pcts_and_ceil():
    f = _many([5.0] * 40)                                       # n = 40
    r = adversarial(f, min_trades=1)["ex_best_trades"]
    assert [e["pct"] for e in r] == [0.01, 0.05]
    assert [e["n_dropped"] for e in r] == [1, 2]                # ceil(40*.01)=1, ceil(40*.05)=2


def test_sample_size_gate_below_threshold_withholds_verdict():
    f = _many([2.0] * 50)                                       # net positive, but only 50 trades
    a = adversarial(f, min_trades=100)
    assert a["sample_size"]["low_sample"] is True
    assert a["sample_size"]["warning"] is not None
    assert a["verdict"].startswith("inconclusive")
    assert "50 trades" in a["verdict"]
    assert "profitable" not in a["verdict"]


def test_sample_size_ok_above_threshold_gives_a_real_verdict():
    up = adversarial(_many([1.0] * 150), min_trades=100)
    down = adversarial(_many([-1.0] * 150), min_trades=100)
    assert up["sample_size"]["low_sample"] is False
    assert up["verdict"] == "profitable"
    assert down["verdict"] == "unprofitable"


def test_adversarial_empty_frame_no_crash():
    a = adversarial(pl.DataFrame())
    assert a["sample_size"]["low_sample"] is True
    assert a["verdict"].startswith("inconclusive")
    assert a["gross_vs_net"]["gross_pips"] == 0.0
    assert a["ex_best_month"]["dropped_month"] is None
    assert [e["pct"] for e in a["ex_best_trades"]] == [0.01, 0.05]


# --------------------------------------------------------------------------- #
# bootstrap CI (spec §3.2)
# --------------------------------------------------------------------------- #

def test_bootstrap_is_deterministic_given_seed():
    f = _many([5, -3, 8, -2, -1, 4, 7, -6, 2, -4])
    a = bootstrap_ci(f, n_resamples=2_000, seed=7)
    b = bootstrap_ci(f, n_resamples=2_000, seed=7)
    c = bootstrap_ci(f, n_resamples=2_000, seed=8)
    assert a["win_rate"] == b["win_rate"] and a["expectancy_pips"] == b["expectancy_pips"]
    assert a["expectancy_pips"] != c["expectancy_pips"]


def test_bootstrap_ci_brackets_the_observed_value():
    f = _many([20, -10] * 20 + [30, -5] * 10)             # skewed-ish
    r = bootstrap_ci(f, n_resamples=5_000, seed=1)
    for k in ("win_rate", "expectancy_pips"):
        s = r[k]
        assert s["ci_low"] <= s["observed"] <= s["ci_high"]
        assert s["ci_low"] <= s["mean"] <= s["ci_high"]


def test_bootstrap_degenerate_all_equal_pips_collapses_to_the_point():
    f = _many([7.0] * 30)
    r = bootstrap_ci(f, n_resamples=1_000, seed=0)
    for k, pt in (("win_rate", 100.0), ("expectancy_pips", 7.0)):
        s = r[k]
        assert s["observed"] == pt
        assert s["ci_low"] == pytest.approx(pt) and s["ci_high"] == pytest.approx(pt)


def test_bootstrap_matches_a_direct_numpy_computation():
    pips = [3.0, -1.0, 5.0, -2.0, 4.0, -1.0, 2.0]
    f = _many(pips)
    r = bootstrap_ci(f, n_resamples=3_000, confidence=0.90, seed=123)

    arr = np.asarray(pips)
    rng = np.random.default_rng(123)
    idx = rng.integers(0, arr.size, size=(3_000, arr.size))
    samples = arr[idx]
    exp = samples.mean(axis=1)
    assert r["expectancy_pips"]["mean"] == pytest.approx(float(exp.mean()))
    assert r["expectancy_pips"]["ci_low"] == pytest.approx(float(np.percentile(exp, 5)))
    assert r["expectancy_pips"]["ci_high"] == pytest.approx(float(np.percentile(exp, 95)))


def test_bootstrap_empty_frame_no_crash():
    r = bootstrap_ci(pl.DataFrame())
    assert r["win_rate"]["observed"] is None
    assert r["expectancy_pips"]["ci_low"] is None


# --------------------------------------------------------------------------- #
# Monte-Carlo trade-order shuffle (spec §3.2)
# --------------------------------------------------------------------------- #

def test_mc_is_deterministic_given_seed():
    f = _many([5, -3, 8, -2, -1, 4, 7, -6, 2, -4])
    a = mc_drawdown(f, n_shuffles=2_000, seed=3)
    b = mc_drawdown(f, n_shuffles=2_000, seed=3)
    assert a["worst"] == b["worst"] and a["median"] == b["median"]
    assert a["observed_max_drawdown_pct"] == b["observed_max_drawdown_pct"]


def test_mc_distribution_depends_only_on_the_multiset_not_input_order():
    pips = [5, -3, 8, -2, -1, 4, 7, -6, 2, -4]
    forward = _many(pips)
    reversed_ = _many(list(reversed(pips)))
    a = mc_drawdown(forward, n_shuffles=3_000, seed=11)
    b = mc_drawdown(reversed_, n_shuffles=3_000, seed=11)
    # the shuffle distribution is identical (total P&L is shuffle-invariant) ...
    assert (a["median"], a["p95"], a["worst"]) == (b["median"], b["p95"], b["worst"])
    # ... only the real-ordering drawdown differs
    assert a["observed_max_drawdown_pct"] != b["observed_max_drawdown_pct"]


def test_mc_real_order_all_losses_first_is_near_worst_not_fragile():
    losses_first = _many([-10] * 5 + [30] * 5)
    r = mc_drawdown(losses_first, n_shuffles=5_000, seed=2)
    assert r["fragile"] is False
    assert r["observed_max_drawdown_pct"] == pytest.approx(r["worst"], abs=1e-9)
    assert r["percentile_rank"] < 5.0                      # almost nothing is worse


def test_mc_real_order_interleaved_with_clustering_risk_is_fragile():
    interleaved = _many([30, -10, 30, -10, 30, -10, 30, -10, 30, -10])
    r = mc_drawdown(interleaved, n_shuffles=5_000, seed=2)
    assert r["fragile"] is True
    assert r["observed_max_drawdown_pct"] > r["median"]    # milder than a typical reorder
    assert r["percentile_rank"] > 50.0                     # most reorderings are worse


def test_mc_small_n_no_crash():
    r = mc_drawdown(_many([2, -5, 3, -1, 4]), n_shuffles=500, seed=0)
    assert r["observed_max_drawdown_pct"] <= 0.0
    assert "sequence risk" in r["note"]


def test_mc_empty_frame_no_crash():
    r = mc_drawdown(pl.DataFrame())
    assert r["observed_max_drawdown_pct"] == 0.0
    assert r["fragile"] is False and r["median"] is None


# --------------------------------------------------------------------------- #
# Engine.evaluate — orchestration (spec §2.1) + plots
# --------------------------------------------------------------------------- #

def _mini_engine_run():
    from lib.engine import Engine, Strategy

    class _FixedSignals(Strategy):
        def __init__(self, longs, shorts):
            super().__init__(10.0, 20.0, "5m")
            self._l, self._s = longs, shorts

        def generate_signals(self, df):
            return df.with_columns(
                long_signal=pl.Series(self._l, dtype=pl.Boolean),
                short_signal=pl.Series(self._s, dtype=pl.Boolean),
            )

    t0 = datetime(2024, 6, 3, 12, tzinfo=UTC)
    n = 12
    sig = pl.DataFrame({
        "timestamp": [t0 + timedelta(minutes=5 * i) for i in range(n)],
        "close_time": [t0 + timedelta(minutes=5 * (i + 1)) for i in range(n)],
        "bid_open": [1.1000] * n, "bid_high": [1.1006] * n,
        "bid_low": [1.0994] * n, "bid_close": [1.1000] * n,
        "ask_open": [1.1002] * n, "ask_high": [1.1008] * n,
        "ask_low": [1.0996] * n, "ask_close": [1.1002] * n,
    })
    bn = 90 * 60
    base = pl.DataFrame({
        "timestamp": [t0 + timedelta(seconds=i) for i in range(bn)],
        "bid_open": [1.1000] * bn, "bid_high": [1.1000] * bn, "bid_low": [1.1000] * bn,
        "bid_close": [1.1000] * bn, "bid_volume": [1.0] * bn,
        "ask_open": [1.1002] * bn, "ask_high": [1.1002] * bn, "ask_low": [1.1002] * bn,
        "ask_close": [1.1002] * bn, "ask_volume": [1.0] * bn,
    })
    F, Tr = False, True
    longs = [F, Tr, F, F, F, Tr, F, F, F, Tr, F, F]
    shorts = [F, F, F, Tr, F, F, F, Tr, F, F, F, F]
    eng = Engine(sig, base)
    trades = eng.backtest(_FixedSignals(longs, shorts))
    assert trades.height >= 2
    return eng, trades


def test_engine_evaluate_merges_all_sections():
    eng, trades = _mini_engine_run()
    r = eng.evaluate(trades, seed=5, n_resamples=300, n_shuffles=300)

    assert set(r) == {"summary", "equity_curve", "monthly", "adversarial", "verdict"}
    assert set(r["adversarial"]) == {
        "gross_vs_net", "ex_best_month", "ex_best_trades",
        "sample_size", "bootstrap_ci", "mc_drawdown",
    }
    assert isinstance(r["equity_curve"], pl.DataFrame)
    assert r["verdict"] in ("profitable", "unprofitable") or r["verdict"].startswith("inconclusive")
    # sample-size gate: this run is small
    assert r["adversarial"]["sample_size"]["low_sample"] is True
    assert r["verdict"].startswith("inconclusive")


def test_engine_evaluate_is_reproducible_with_seed():
    eng, trades = _mini_engine_run()
    a = eng.evaluate(trades, seed=99, n_resamples=300, n_shuffles=300)
    b = eng.evaluate(trades, seed=99, n_resamples=300, n_shuffles=300)
    c = eng.evaluate(trades, seed=100, n_resamples=300, n_shuffles=300)
    assert a["adversarial"]["bootstrap_ci"]["win_rate"] == b["adversarial"]["bootstrap_ci"]["win_rate"]
    assert a["adversarial"]["mc_drawdown"]["worst"] == b["adversarial"]["mc_drawdown"]["worst"]
    assert a["adversarial"]["bootstrap_ci"] != c["adversarial"]["bootstrap_ci"]


def _agg_pyplot():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def test_plots_return_matplotlib_figures():
    plt = _agg_pyplot()
    from matplotlib.figure import Figure
    from lib.evaluate import plot_equity, plot_monthly, plot_mc_drawdown

    eng, trades = _mini_engine_run()
    r = eng.evaluate(trades, seed=1, n_resamples=200, n_shuffles=200)

    for fig in (
        plot_equity(r),
        plot_monthly(r),
        plot_mc_drawdown(r["adversarial"]["mc_drawdown"]),
    ):
        assert isinstance(fig, Figure)
        plt.close(fig)


def test_plots_do_not_crash_on_empty_result():
    plt = _agg_pyplot()
    from lib.evaluate import mc_drawdown, plot_equity, plot_mc_drawdown, plot_monthly

    empty = evaluate(pl.DataFrame())
    plt.close(plot_equity(empty))
    plt.close(plot_monthly(empty))
    plt.close(plot_mc_drawdown(mc_drawdown(pl.DataFrame())))
