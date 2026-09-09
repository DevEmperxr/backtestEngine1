"""Tests for lib/strategies.py — SmaCrossoverStrategy (spec §4, §6)."""

from datetime import datetime, timedelta, timezone

import polars as pl
import pytest

from lib.engine import Engine
from lib.signals import crossover, sma
from lib.strategies import SmaCrossoverStrategy

UTC = timezone.utc


def _bars(bid_close, ask_close, *, step_min=5, start=datetime(2024, 6, 3, 12, 0, tzinfo=UTC)):
    """A resample()-shaped signal frame from bid/ask close lists."""
    n = len(bid_close)
    ts = [start + timedelta(minutes=step_min * i) for i in range(n)]
    return pl.DataFrame({
        "timestamp": ts,
        "close_time": [t + timedelta(minutes=step_min) for t in ts],
        "bid_open": bid_close, "bid_high": [b + 0.001 for b in bid_close],
        "bid_low": [b - 0.001 for b in bid_close], "bid_close": bid_close,
        "bid_volume": [1.0] * n,
        "ask_open": ask_close, "ask_high": [a + 0.001 for a in ask_close],
        "ask_low": [a - 0.001 for a in ask_close], "ask_close": ask_close,
        "ask_volume": [1.0] * n,
    })


def _xover(series, fast_n, slow_n):
    """The crossover the strategy would compute over `series` as the mid price."""
    d = pl.DataFrame({"v": [float(x) for x in series]})
    cu, cd = crossover(sma(pl.col("v"), fast_n), sma(pl.col("v"), slow_n))
    o = d.select(u=cu, d=cd)
    return o["u"].to_list(), o["d"].to_list()


# --------------------------------------------------------------------------- #
# constructor
# --------------------------------------------------------------------------- #

def test_constructor_stores_params_including_super():
    s = SmaCrossoverStrategy(fast_n=10, slow_n=30, sl_pips=8, tp_pips=16, timeframe="1h")
    assert (s.fast_n, s.slow_n) == (10, 30)
    assert s.sl_pips == 8.0 and s.tp_pips == 16.0
    assert s.timeframe == "1h"
    assert s.exit_on_opposite_signal is True


def test_reverses_on_opposite_signal_like_the_prototype():
    assert SmaCrossoverStrategy.reverse_on_opposite_signal is True


@pytest.mark.parametrize("fast_n, slow_n", [(50, 20), (20, 20), (0, 10), (-1, 10)])
def test_constructor_rejects_bad_windows(fast_n, slow_n):
    with pytest.raises(ValueError):
        SmaCrossoverStrategy(fast_n=fast_n, slow_n=slow_n, sl_pips=10, tp_pips=20)


def test_constructor_still_validates_sl_tp_via_super():
    with pytest.raises(ValueError):
        SmaCrossoverStrategy(fast_n=2, slow_n=3, sl_pips=0, tp_pips=20)


# --------------------------------------------------------------------------- #
# generate_signals
# --------------------------------------------------------------------------- #

def test_generate_signals_output_shape_and_dtypes():
    df = _bars([1.10 + 0.001 * i for i in range(8)], [1.1002 + 0.001 * i for i in range(8)])
    out = SmaCrossoverStrategy(fast_n=2, slow_n=3, sl_pips=10, tp_pips=20).generate_signals(df)
    for c in ("mid_close", "sma_fast", "sma_slow", "long_signal", "short_signal"):
        assert c in out.columns
    assert out.schema["long_signal"] == pl.Boolean
    assert out.schema["short_signal"] == pl.Boolean
    assert out["long_signal"].null_count() == 0
    assert out["short_signal"].null_count() == 0


def test_generate_signals_is_pure():
    df = _bars([1.10] * 6, [1.1002] * 6)
    before = df.clone()
    SmaCrossoverStrategy(fast_n=2, slow_n=3, sl_pips=10, tp_pips=20).generate_signals(df)
    assert df.equals(before)


def test_signals_use_mid_not_bid_or_ask():
    # spread spikes at bar 6 -> the mid crosses where the bid alone does not
    bid = [1.0000, 1.0010, 1.0025, 1.0015, 1.0005, 1.0000, 1.0000, 1.0000]
    ask = [1.0002, 1.0012, 1.0027, 1.0017, 1.0007, 1.0002, 1.0060, 1.0002]
    mid = [(b + a) / 2 for b, a in zip(bid, ask)]

    strat = SmaCrossoverStrategy(fast_n=2, slow_n=3, sl_pips=10, tp_pips=20)
    out = strat.generate_signals(_bars(bid, ask))

    mid_up, mid_dn = _xover(mid, 2, 3)
    bid_up, bid_dn = _xover(bid, 2, 3)
    assert (mid_up, mid_dn) != (bid_up, bid_dn)            # the frame distinguishes them
    assert out["long_signal"].to_list() == mid_up
    assert out["short_signal"].to_list() == mid_dn


def test_no_signal_during_slow_warmup():
    df = _bars([1.10 + 0.002 * i for i in range(12)], [1.1002 + 0.002 * i for i in range(12)])
    strat = SmaCrossoverStrategy(fast_n=3, slow_n=6, sl_pips=10, tp_pips=20)
    out = strat.generate_signals(df)
    assert not any(out["long_signal"].to_list()[: strat.slow_n])
    assert not any(out["short_signal"].to_list()[: strat.slow_n])
    assert out["sma_slow"].to_list()[: strat.slow_n - 1] == [None] * (strat.slow_n - 1)


def test_one_known_crossover_lands_on_the_expected_bar():
    # constant spread -> mid tracks bid; fast(2) crosses slow(3) up at bar 4
    bid = [1.0000, 1.0000, 1.0000, 1.0000, 1.0010, 1.0020, 1.0030, 1.0030]
    ask = [b + 0.0004 for b in bid]
    out = SmaCrossoverStrategy(fast_n=2, slow_n=3, sl_pips=10, tp_pips=20).generate_signals(_bars(bid, ask))
    assert [i for i, v in enumerate(out["long_signal"].to_list()) if v] == [4]
    assert not any(out["short_signal"].to_list())


# --------------------------------------------------------------------------- #
# integration smoke through the engine
# --------------------------------------------------------------------------- #

def _base_1s(start, n, bid=1.1000, ask=1.1002):
    ts = [start + timedelta(seconds=i) for i in range(n)]
    return pl.DataFrame({
        "timestamp": ts,
        "bid_open": [bid] * n, "bid_high": [bid] * n, "bid_low": [bid] * n,
        "bid_close": [bid] * n, "bid_volume": [1.0] * n,
        "ask_open": [ask] * n, "ask_high": [ask] * n, "ask_low": [ask] * n,
        "ask_close": [ask] * n, "ask_volume": [1.0] * n,
    })


def test_engine_backtest_smoke():
    bid = [1.0000, 1.0000, 1.0000, 1.0000, 1.0010, 1.0025, 1.0015, 1.0005, 1.0000, 1.0000]
    ask = [b + 0.0004 for b in bid]
    sig = _bars(bid, ask, start=datetime(2024, 6, 3, 12, 0, tzinfo=UTC))
    base = _base_1s(datetime(2024, 6, 3, 12, 0, tzinfo=UTC), n=60 * 60)

    trades = Engine(sig, base).backtest(
        SmaCrossoverStrategy(fast_n=2, slow_n=3, sl_pips=10, tp_pips=20)
    )

    assert trades.columns == [
        "entry_time", "entry_price", "direction",
        "exit_time", "exit_price", "pips", "exit_reason", "spread_pips_paid",
    ]
    assert set(trades["direction"].to_list()) <= {"long", "short"}
    assert set(trades["exit_reason"].to_list()) <= {"sl", "tp", "opposite_signal", "end_of_data"}
    assert trades["entry_time"].null_count() == 0
