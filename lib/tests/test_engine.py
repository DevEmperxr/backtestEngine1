"""Tests for lib/engine.py — the Strategy ABC (spec §2.2)."""

import polars as pl
import pytest

from lib.engine import Strategy


class _MiniStrategy(Strategy):
    """Smallest possible concrete strategy — just enough to exercise the ABC."""

    def __init__(self, sl_pips=10.0, tp_pips=20.0, timeframe="5m", fast_n=3):
        super().__init__(sl_pips, tp_pips, timeframe)
        self.fast_n = fast_n  # a subclass-specific param

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(
            long_signal=pl.col("bid_close") > pl.col("bid_open"),
            short_signal=pl.col("bid_close") < pl.col("bid_open"),
        )


class _SLTPOnlyStrategy(_MiniStrategy):
    exit_on_opposite_signal = False


def _frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "bid_open": [1.10, 1.11, 1.12],
            "bid_close": [1.11, 1.10, 1.12],
        }
    )


def test_strategy_is_abstract():
    with pytest.raises(TypeError):
        Strategy(sl_pips=10, tp_pips=20, timeframe="5m")


def test_concrete_subclass_stores_constructor_args():
    s = _MiniStrategy(sl_pips=12.5, tp_pips=30, timeframe="1h", fast_n=8)
    assert s.sl_pips == 12.5
    assert s.tp_pips == 30.0
    assert s.timeframe == "1h"
    assert s.fast_n == 8


def test_exit_on_opposite_signal_default_and_override():
    assert Strategy.exit_on_opposite_signal is True
    assert _MiniStrategy().exit_on_opposite_signal is True
    assert _SLTPOnlyStrategy().exit_on_opposite_signal is False


@pytest.mark.parametrize(
    "kwargs",
    [
        {"sl_pips": 0, "tp_pips": 20, "timeframe": "5m"},
        {"sl_pips": 10, "tp_pips": -5, "timeframe": "5m"},
        {"sl_pips": 10, "tp_pips": 20, "timeframe": ""},
        {"sl_pips": 10, "tp_pips": 20, "timeframe": 5},
    ],
)
def test_init_rejects_bad_args(kwargs):
    with pytest.raises(ValueError):
        _MiniStrategy(**kwargs)


def test_generate_signals_returns_boolean_columns():
    out = _MiniStrategy().generate_signals(_frame())
    assert out.schema["long_signal"] == pl.Boolean
    assert out.schema["short_signal"] == pl.Boolean


def test_generate_signals_does_not_mutate_input():
    df = _frame()
    before = df.clone()
    _MiniStrategy().generate_signals(df)
    assert df.equals(before)
    assert "long_signal" not in df.columns
