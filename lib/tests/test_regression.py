"""Formal §6 regression — SMA(20/50) crossover, end to end on the real 1s file.

Baseline (spec §6, from the 5-min prototype with the old "assume SL first"
same-bar fill approximation):

    1,691 trades · −346.5 pips · 33.0% win rate

`sl_pips`/`tp_pips` were never recorded in the spec. This test runs `10/20` (the
config used throughout the rest of the suite) because it already clears every §6
tolerance; `notebooks/regression.ipynb` fits the parameters (`mid, sl≈8/tp≈15`
reproduces the baseline within ~1%) and chases the pip gap. See `regression.md`.

Marked `slow` and skipped when the data file is absent.
"""

from pathlib import Path

import polars as pl
import pytest

from lib.data import load_1s_data, resample
from lib.engine import Engine
from lib.strategies import SmaCrossoverStrategy

_DATA = Path(__file__).resolve().parents[2] / "data" / "EURUSD_1s_2024.csv"

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not _DATA.exists(), reason=f"{_DATA} not present"),
]

BASE_TRADES, BASE_PIPS, BASE_WIN = 1691, -346.5, 33.0
FAST_N, SLOW_N, SL_PIPS, TP_PIPS = 20, 50, 10, 20
VALID_EXIT_REASONS = {"sl", "tp", "opposite_signal", "end_of_data"}


@pytest.fixture(scope="module")
def run():
    base = load_1s_data(str(_DATA), verbose=False)
    bars = resample(base, "5m")
    trades = Engine(bars, base).backtest(
        SmaCrossoverStrategy(fast_n=FAST_N, slow_n=SLOW_N, sl_pips=SL_PIPS, tp_pips=TP_PIPS)
    )
    return bars, trades


def test_trade_count_within_5pct_of_baseline(run):
    _, trades = run
    assert abs(trades.height - BASE_TRADES) / BASE_TRADES < 0.05, trades.height


def test_win_rate_within_3_points_of_baseline(run):
    _, trades = run
    win = trades.filter(pl.col("pips") > 0).height / trades.height * 100
    assert abs(win - BASE_WIN) < 3.0, round(win, 2)


def test_edge_sign_holds_and_pip_magnitude_is_sane(run):
    _, trades = run
    total = trades["pips"].sum()
    assert total < 0, total                                  # the small negative edge
    assert 0.5 <= abs(total) / abs(BASE_PIPS) <= 2.0, round(total, 1)


def test_every_trade_is_well_formed(run):
    bars, trades = run

    # the bars whose t+1 open is a legal entry instant: one bar after a crossover
    # rising edge (a fresh entry, or the opposite edge that drives a reversal)
    sig = SmaCrossoverStrategy(
        fast_n=FAST_N, slow_n=SLOW_N, sl_pips=SL_PIPS, tp_pips=TP_PIPS
    ).generate_signals(bars)
    sig = sig.with_columns(
        edge=(
            (pl.col("long_signal") & ~pl.col("long_signal").shift(1, fill_value=False))
            | (pl.col("short_signal") & ~pl.col("short_signal").shift(1, fill_value=False))
        )
    )
    ts = sig["timestamp"].to_list()
    edge = sig["edge"].to_list()
    legal_entry_times = {
        ts[i + 1] for i in range(len(ts) - 1) if edge[i]
    }
    entry_open = {
        (row["timestamp"], "long"): row["ask_open"] for row in bars.iter_rows(named=True)
    }
    entry_open.update(
        {(row["timestamp"], "short"): row["bid_open"] for row in bars.iter_rows(named=True)}
    )

    for tr in trades.iter_rows(named=True):
        assert tr["direction"] in ("long", "short")
        assert tr["exit_reason"] in VALID_EXIT_REASONS
        # exit never *precedes* entry. `==` is legal: a stop/target that the
        # entry second's own 1s range already spans fires immediately (§0.2 —
        # the entry second is exposed to its own range).
        assert tr["exit_time"] >= tr["entry_time"]
        if tr["exit_time"] == tr["entry_time"]:
            assert tr["exit_reason"] in ("sl", "tp")
        assert tr["entry_time"] in legal_entry_times          # t+1 after a crossover edge
        want = entry_open[(tr["entry_time"], tr["direction"])]
        assert abs(tr["entry_price"] - want) < 1e-9           # ask (long) / bid (short) open


def test_no_wall_clock_overlap_between_consecutive_trades(run):
    _, trades = run
    prev_exit = trades["exit_time"].shift(1)
    # a reversal re-opens exactly at the previous exit instant, so >= not >
    bad = trades.filter(pl.col("entry_time") < prev_exit)
    assert bad.height == 0, bad.head()


def test_headline_numbers_are_stable(run):
    """Locks the current output so an accidental engine change is caught. If a
    deliberate change moves these, update the numbers *and* regression.md."""
    _, trades = run
    win = trades.filter(pl.col("pips") > 0).height / trades.height * 100
    assert trades.height == 1714
    assert round(trades["pips"].sum(), 1) == -453.1
    assert round(win, 1) == 32.5
    assert dict(trades.group_by("exit_reason").agg(pl.len()).iter_rows()) == {
        "opposite_signal": 999, "sl": 443, "tp": 271, "end_of_data": 1
    }
