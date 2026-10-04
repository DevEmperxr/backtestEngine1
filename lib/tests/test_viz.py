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
from lib.engine import _project_trades, _windowed_signals
from lib.strategies import SmaCrossoverStrategy


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


class TestWindowedSignalsNoLookahead:
    """`_windowed_signals` backs the lazy-load/timeframe-switch paths in
    `Strategy.visualize()` (spec §4/§5). The property that matters most: a
    windowed-with-warmup computation must be IDENTICAL to what a full-dataset
    computation produces for the same rows -- not approximately close, not
    "close enough after warmup converges" -- exactly equal, bar for bar. If
    it weren't, that would mean either future data was leaking backward
    (wrong direction) or real history was being withheld that should have
    been there (the "seam" bug the spec explicitly calls out).
    """

    @staticmethod
    def _bars(n=1000, seed=0):
        rng = np.random.default_rng(seed)
        walk = 1.10 + np.cumsum(rng.normal(0, 0.0003, n))
        return pl.DataFrame(
            {
                "timestamp": pl.datetime_range(
                    datetime(2024, 1, 1), datetime(2024, 1, 1) + pd.Timedelta(minutes=5 * (n - 1)),
                    "5m", eager=True,
                ),
                "bid_close": walk,
                "ask_close": walk + 0.0001,
            }
        )

    @staticmethod
    def _strategy():
        return SmaCrossoverStrategy(fast_n=5, slow_n=20, sl_pips=10, tp_pips=20)

    def test_matches_full_dataset_computation_exactly(self):
        bars = self._bars()
        strat = self._strategy()
        full = strat.generate_signals(bars)

        start_idx, end_idx, warmup = 400, 700, 200
        windowed = _windowed_signals(strat, bars, start_idx, end_idx, warmup)
        expected = full.slice(start_idx, end_idx - start_idx)

        assert windowed.height == expected.height
        for col in ("sma_fast", "sma_slow", "long_signal", "short_signal"):
            assert windowed[col].to_list() == expected[col].to_list(), col

    def test_insufficient_warmup_degrades_safely_not_wrongly(self):
        # warmup_bars=5 is LESS than slow_n=20's own lookback requirement --
        # this is the one case where windowed and full-dataset DON'T match
        # bar-for-bar, and that's correct: with less history available,
        # sma()'s null-until-a-full-window design (lib/signals.py) means the
        # windowed version shows nulls for MORE leading rows than the
        # full-dataset version does. That's the system being honest about
        # insufficient data rather than fabricating a value -- the opposite
        # failure mode of lookahead. What must NEVER happen: a row where the
        # full dataset has a real value but the windowed version has a
        # DIFFERENT real value (that would mean genuine corruption), or a row
        # where windowed has a real value but the full dataset has null
        # (that would mean it used data it wasn't entitled to).
        bars = self._bars()
        strat = self._strategy()
        full = strat.generate_signals(bars)

        start_idx, end_idx, warmup = 10, 60, 5  # warmup_bars < slow_n=20
        windowed = _windowed_signals(strat, bars, start_idx, end_idx, warmup)
        expected = full.slice(start_idx, end_idx - start_idx)

        for col in ("sma_fast", "sma_slow"):
            w, e = windowed[col].to_numpy(), expected[col].to_numpy()
            # windowed may be null where expected is real (less history) ...
            assert not (np.isnan(e) & ~np.isnan(w)).any(), f"{col}: used data it shouldn't have"
            # ... but never the reverse, and never a differing real value
            both_real = ~np.isnan(w) & ~np.isnan(e)
            np.testing.assert_allclose(w[both_real], e[both_real], rtol=1e-9)
        for col in ("long_signal", "short_signal"):
            # a signal can only legitimately fire where BOTH SMAs are real in
            # both versions; outside that, windowed staying quiet (False)
            # while expected (with more history) might have fired is the
            # same safe degradation as above, never the other way around.
            w_fires = windowed[col].to_numpy()
            e_fires = expected[col].to_numpy()
            both_smas_real = (
                ~np.isnan(windowed["sma_slow"].to_numpy()) & ~np.isnan(expected["sma_slow"].to_numpy())
            )
            assert (w_fires[both_smas_real] == e_fires[both_smas_real]).all(), col
            assert not (w_fires & ~e_fires).any(), f"{col}: fired where full dataset didn't"

    def test_window_starting_at_zero_needs_no_warmup_clamp(self):
        bars = self._bars()
        strat = self._strategy()
        full = strat.generate_signals(bars)

        windowed = _windowed_signals(strat, bars, 0, 50, warmup_bars=200)
        expected = full.slice(0, 50)
        assert windowed["sma_slow"].to_list() == expected["sma_slow"].to_list()

    def test_never_reads_past_end_idx(self):
        # mutate every row from end_idx onward to an impossible sentinel value;
        # if the windowed computation's result changes, it read past the
        # window it was given -- i.e. a real lookahead bug.
        bars = self._bars()
        strat = self._strategy()
        start_idx, end_idx, warmup = 300, 500, 200

        windowed_before = _windowed_signals(strat, bars, start_idx, end_idx, warmup)

        poisoned = bars.with_columns(
            pl.when(pl.int_range(pl.len()) >= end_idx)
            .then(pl.lit(999.0))
            .otherwise(pl.col("bid_close"))
            .alias("bid_close"),
            pl.when(pl.int_range(pl.len()) >= end_idx)
            .then(pl.lit(999.0))
            .otherwise(pl.col("ask_close"))
            .alias("ask_close"),
        )
        windowed_after = _windowed_signals(strat, poisoned, start_idx, end_idx, warmup)

        for col in ("sma_fast", "sma_slow", "long_signal", "short_signal"):
            assert windowed_before[col].to_list() == windowed_after[col].to_list(), col

    def test_never_reads_before_compute_start(self):
        # symmetric check: poisoning data strictly BEFORE compute_start must
        # not change the result either (it's outside even the warmup window).
        bars = self._bars()
        strat = self._strategy()
        start_idx, end_idx, warmup = 300, 500, 200
        compute_start = start_idx - warmup  # == 100

        windowed_before = _windowed_signals(strat, bars, start_idx, end_idx, warmup)

        poisoned = bars.with_columns(
            pl.when(pl.int_range(pl.len()) < compute_start)
            .then(pl.lit(-999.0))
            .otherwise(pl.col("bid_close"))
            .alias("bid_close"),
            pl.when(pl.int_range(pl.len()) < compute_start)
            .then(pl.lit(-999.0))
            .otherwise(pl.col("ask_close"))
            .alias("ask_close"),
        )
        windowed_after = _windowed_signals(strat, poisoned, start_idx, end_idx, warmup)

        for col in ("sma_fast", "sma_slow", "long_signal", "short_signal"):
            assert windowed_before[col].to_list() == windowed_after[col].to_list(), col
