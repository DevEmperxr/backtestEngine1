"""fx_viz's pure-data logic (visualizer spec §2/§6/§8.4).

Deliberately NOT covered here: anything that needs a live browser (candle/
line/marker/region rendering, hot-reload, pane add/delete). Those were
verified by hand with a Playwright-driven headless Chromium against real
backtester data -- see the §1.1 spike methodology in
notebooks/viz_spike.ipynb. This file covers only what's testable without one:
the contiguous-run/gap-segmentation helper, the tz-strip-and-rename prep
step, and the trade-to-column projection used by Strategy.visualize().
"""

from datetime import datetime

import numpy as np
import pandas as pd
import polars as pl
import pytest

from fx_viz.chart import _contiguous_runs, _to_pandas
from lib.engine import _project_trades


class TestContiguousRuns:
    def test_all_valid_is_one_run(self):
        assert _contiguous_runs(np.array([True, True, True])) == [(0, 3)]

    def test_all_invalid_is_no_runs(self):
        assert _contiguous_runs(np.array([False, False])) == []

    def test_empty_is_no_runs(self):
        assert _contiguous_runs(np.array([], dtype=bool)) == []

    def test_bounded_run_in_the_middle(self):
        # the exact shape spec §6.1 needs for a bounded hline: null outside,
        # constant inside -> one run starting and stopping where the data does
        mask = np.array([False, False, True, True, True, False, False])
        assert _contiguous_runs(mask) == [(2, 5)]

    def test_leading_and_trailing_runs(self):
        mask = np.array([True, True, False, False, True, True])
        assert _contiguous_runs(mask) == [(0, 2), (4, 6)]

    def test_single_bar_runs(self):
        mask = np.array([False, True, False, True, False])
        assert _contiguous_runs(mask) == [(1, 2), (3, 4)]


class TestToPandas:
    def test_strips_tz_and_renames_time_column(self):
        df = pl.DataFrame(
            {
                "timestamp": pl.datetime_range(
                    pl.datetime(2024, 1, 1), pl.datetime(2024, 1, 1, 0, 2),
                    "1m", eager=True, time_zone="UTC",
                ),
                "close": [1.1, 1.2, 1.3],
            }
        )
        pdf = _to_pandas(df)
        assert "time" in pdf.columns and "timestamp" not in pdf.columns
        assert not isinstance(pdf["time"].dtype, pd.DatetimeTZDtype)

    def test_passes_through_tz_naive(self):
        df = pl.DataFrame(
            {
                "timestamp": pl.datetime_range(
                    pl.datetime(2024, 1, 1), pl.datetime(2024, 1, 1, 0, 2),
                    "1m", eager=True,
                ),
                "close": [1.1, 1.2, 1.3],
            }
        )
        pdf = _to_pandas(df)
        assert "time" in pdf.columns


class TestProjectTrades:
    @staticmethod
    def _signal_df(n=10):
        return pl.DataFrame(
            {
                "timestamp": pl.datetime_range(
                    pl.datetime(2024, 1, 1), pl.datetime(2024, 1, 1, 0, 9),
                    "1m", eager=True,
                ),
            }
        )

    @staticmethod
    def _trade(entry_min, exit_min, direction):
        return {
            "entry_time": datetime(2024, 1, 1, 0, entry_min),
            "entry_price": 1.1,
            "direction": direction,
            "exit_time": datetime(2024, 1, 1, 0, exit_min),
            "exit_price": 1.1,
            "pips": 0.0,
            "exit_reason": "tp",
            "spread_pips_paid": 0.1,
        }

    def test_marks_entry_bar_and_in_trade_window(self):
        df = self._signal_df()
        trades = pl.DataFrame([self._trade(2, 5, "long")])
        out = _project_trades(df, trades)

        assert out["trade_entry_long"].to_list() == [
            False, False, True, False, False, False, False, False, False, False
        ]
        # [entry_time, exit_time) -- bar 5 (the exit bar) is NOT inside the window
        assert out["trade_region_long"].to_list() == [
            False, False, True, True, True, False, False, False, False, False
        ]
        assert not out["trade_entry_short"].any()
        assert not out["trade_region_short"].any()

    def test_non_overlapping_long_and_short_trades(self):
        df = self._signal_df()
        trades = pl.DataFrame([self._trade(1, 3, "long"), self._trade(3, 6, "short")])
        out = _project_trades(df, trades)

        assert out["trade_region_long"].to_list() == [
            False, True, True, False, False, False, False, False, False, False
        ]
        assert out["trade_region_short"].to_list() == [
            False, False, False, True, True, True, False, False, False, False
        ]

    def test_no_trades_yields_all_false(self):
        df = self._signal_df()
        trades = pl.DataFrame(
            [], schema={
                "entry_time": df.schema["timestamp"], "entry_price": pl.Float64,
                "direction": pl.String, "exit_time": df.schema["timestamp"],
                "exit_price": pl.Float64, "pips": pl.Float64,
                "exit_reason": pl.String, "spread_pips_paid": pl.Float64,
            }
        )
        out = _project_trades(df, trades)
        for col in ("trade_entry_long", "trade_entry_short", "trade_region_long", "trade_region_short"):
            assert not out[col].any()
