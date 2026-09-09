"""Tests for lib/engine.py — the Strategy ABC (§2.2) and Engine entry timing (§2.1, pass 5a)."""

from datetime import datetime, timedelta, timezone

import polars as pl
import pytest

import numpy as np

from lib.data import PIP, DataQualityError
from lib.engine import (
    Engine,
    Strategy,
    _resolve_exit,
    _sl_tp_levels,
)

UTC = timezone.utc


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


# --------------------------------------------------------------------------- #
# Engine — construction + entry timing (spec §2.1) and the SL/TP 1s walk (§2.3)
# --------------------------------------------------------------------------- #

def _base_1s(n: int = 5) -> pl.DataFrame:
    """A minimal valid 1s bid/ask frame — just enough for validate_1s to pass."""
    t0 = datetime(2024, 6, 3, 12, tzinfo=UTC)
    rows = []
    for i in range(n):
        b, a = 1.1000, 1.1002
        rows.append(dict(
            timestamp=t0 + timedelta(seconds=i),
            bid_open=b, bid_high=b, bid_low=b, bid_close=b, bid_volume=1.0,
            ask_open=a, ask_high=a, ask_low=a, ask_close=a, ask_volume=1.0,
        ))
    return pl.DataFrame(rows)


def _path_base(bid_hl, ask_hl, start=datetime(2024, 6, 3, 12, 0, 0, tzinfo=UTC)):
    """A hand-built 1s path: `bid_hl` / `ask_hl` are lists of (high, low) per
    second. open = close = each side's midpoint. Starts 2024-06-03 12:00:00."""
    rows = []
    for i, ((bh, bl), (ah, al)) in enumerate(zip(bid_hl, ask_hl)):
        bm, am = (bh + bl) / 2, (ah + al) / 2
        rows.append(dict(
            timestamp=start + timedelta(seconds=i),
            bid_open=bm, bid_high=bh, bid_low=bl, bid_close=bm, bid_volume=1.0,
            ask_open=am, ask_high=ah, ask_low=al, ask_close=am, ask_volume=1.0,
        ))
    return pl.DataFrame(rows)


def _shift_hl(hl, delta):
    return [(h + delta, l + delta) for h, l in hl]


def _sig_at_noon(n: int, step_min: int = 5) -> pl.DataFrame:
    """`n` signal bars `step_min` apart; bar index 2 is exactly
    2024-06-03 12:00:00, so a rising edge on bar index 1 enters into
    `_path_base`'s first second. Flat prices — ask_open 1.1002, bid_open 1.1000
    (a 2-pip spread)."""
    t0 = datetime(2024, 6, 3, 12, 0, 0, tzinfo=UTC) - timedelta(minutes=2 * step_min)
    ts = [t0 + timedelta(minutes=step_min * i) for i in range(n)]
    return pl.DataFrame({
        "timestamp": ts,
        "close_time": [t + timedelta(minutes=step_min) for t in ts],
        "bid_open": [1.1000] * n, "bid_high": [1.1006] * n,
        "bid_low": [1.0994] * n, "bid_close": [1.1000] * n,
        "ask_open": [1.1002] * n, "ask_high": [1.1008] * n,
        "ask_low": [1.0996] * n, "ask_close": [1.1002] * n,
    })


def _flat_path(n: int, start=datetime(2024, 6, 3, 12, 0, 0, tzinfo=UTC)) -> pl.DataFrame:
    """`n` seconds of a motionless 1s path — bid 1.1000, ask 1.1002."""
    return _path_base([(1.1000, 1.1000)] * n, [(1.1002, 1.1002)] * n, start=start)


def _signal_df(n: int = 8) -> pl.DataFrame:
    """n 5-minute bars with a distinct ask_open / bid_open per bar (so fills are
    identifiable), starting 2024-06-03 12:00 UTC."""
    t0 = datetime(2024, 6, 3, 12, tzinfo=UTC)
    ts = [t0 + timedelta(minutes=5 * i) for i in range(n)]
    ask_open = [round(1.1000 + 0.0010 * i, 5) for i in range(n)]
    bid_open = [round(1.0998 + 0.0010 * i, 5) for i in range(n)]
    return pl.DataFrame({
        "timestamp": ts,
        "close_time": [t + timedelta(minutes=5) for t in ts],
        "bid_open": bid_open,
        "bid_high": [round(b + 0.0005, 5) for b in bid_open],
        "bid_low": [round(b - 0.0005, 5) for b in bid_open],
        "bid_close": bid_open,
        "ask_open": ask_open,
        "ask_high": [round(a + 0.0005, 5) for a in ask_open],
        "ask_low": [round(a - 0.0005, 5) for a in ask_open],
        "ask_close": ask_open,
    })


class _ManualStrategy(Strategy):
    """Attaches signal columns supplied verbatim by the test."""

    def __init__(self, longs, shorts, timeframe="5m"):
        super().__init__(10.0, 20.0, timeframe)
        self._longs, self._shorts = longs, shorts

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(
            long_signal=pl.Series(self._longs, dtype=pl.Boolean),
            short_signal=pl.Series(self._shorts, dtype=pl.Boolean),
        )


F, Tr = False, True


def test_engine_init_validates_base_1s():
    dirty = _base_1s().with_columns(pl.col("bid_close") + 1.0)  # breaks OHLC / spread
    with pytest.raises(DataQualityError):
        Engine(_signal_df(), dirty)


def test_engine_init_rejects_signal_df_missing_columns():
    with pytest.raises(ValueError, match="missing column"):
        Engine(_signal_df().drop("close_time"), _base_1s())


def test_engine_init_rejects_unsorted_signal_df():
    unsorted = _signal_df().reverse()
    with pytest.raises(ValueError, match="sorted"):
        Engine(unsorted, _base_1s())


def test_backtest_rejects_non_boolean_signals():
    class _BadStrategy(Strategy):
        def __init__(self):
            super().__init__(10, 20, "5m")

        def generate_signals(self, df):
            return df.with_columns(long_signal=pl.lit(1), short_signal=pl.lit(0))

    with pytest.raises(ValueError, match="Boolean"):
        Engine(_signal_df(), _base_1s()).backtest(_BadStrategy())


def test_long_signal_enters_at_next_bar_ask_open():
    sd = _signal_df(8)
    longs = [F, Tr, F, F, F, F, F, F]          # signal on bar index 1
    trades = Engine(sd, _base_1s()).backtest(_ManualStrategy(longs, [F] * 8))
    assert trades.height == 1
    row = trades.row(0, named=True)
    assert row["direction"] == "long"
    assert row["entry_time"] == sd["timestamp"][2]          # bar t+1
    assert row["entry_price"] == sd["ask_open"][2]          # buy fills at ask


def test_short_signal_enters_at_next_bar_bid_open():
    sd = _signal_df(8)
    shorts = [F, F, Tr, F, F, F, F, F]         # signal on bar index 2
    trades = Engine(sd, _base_1s()).backtest(_ManualStrategy([F] * 8, shorts))
    row = trades.row(0, named=True)
    assert row["direction"] == "short"
    assert row["entry_time"] == sd["timestamp"][3]
    assert row["entry_price"] == sd["bid_open"][3]          # sell fills at bid


def test_signal_on_last_bar_produces_no_entry():
    sd = _signal_df(6)
    longs = [F, F, F, F, F, Tr]                # nothing after it to act on
    trades = Engine(sd, _base_1s()).backtest(_ManualStrategy(longs, [F] * 6))
    assert trades.height == 0


def test_entry_timestamp_is_strictly_after_the_signal_bar():
    sd = _signal_df(8)
    signal_bar = 4
    longs = [F] * 8
    longs[signal_bar] = Tr
    trades = Engine(sd, _base_1s()).backtest(_ManualStrategy(longs, [F] * 8))
    assert trades.row(0, named=True)["entry_time"] > sd["timestamp"][signal_bar]
    assert trades.row(0, named=True)["entry_time"] == sd["timestamp"][signal_bar + 1]


def test_ambiguous_bar_both_signals_true_raises():
    sd = _signal_df(6)
    with pytest.raises(ValueError, match="ambiguous"):
        Engine(sd, _base_1s()).backtest(_ManualStrategy([F, Tr, F, F, F, F],
                                                        [F, Tr, F, F, F, F]))


# --------------------------------------------------------------------------- #
# Engine — SL / TP / end-of-data exits over the 1s path (spec §2.3 / §2.4)
# --------------------------------------------------------------------------- #

# _sig_at_noon + _ManualStrategy(sl=10, tp=20). A LONG enters at ask_open 1.1002
# -> sl_level 1.0992, tp_level 1.1022.  A SHORT enters at bid_open 1.1000
# -> sl_level 1.1010, tp_level 1.0980.

FLAT_BID = [(1.1000, 1.1000)] * 12
FLAT_ASK = [(1.1002, 1.1002)] * 12


def test_long_take_profit_on_the_1s_bid_path():
    bid = [(1.1005, 1.0998)] * 3 + [(1.1030, 1.1020)] + [(1.1005, 1.0998)] * 6
    ask = _shift_hl(bid, 0.0002)
    base = _path_base(bid, ask)
    sig = _sig_at_noon(6)
    trades = Engine(sig, base).backtest(_ManualStrategy([F, Tr, F, F, F, F], [F] * 6))

    row = trades.row(0, named=True)
    assert row["direction"] == "long"
    assert row["entry_time"] == sig["timestamp"][2]        # t+1
    assert row["exit_reason"] == "tp"
    assert row["exit_time"] == base["timestamp"][3]        # the 1s bar of the touch
    assert row["pips"] == pytest.approx(20.0)              # exit at tp_level, exactly +tp_pips


def test_long_stop_loss_on_the_1s_bid_path():
    bid = [(1.1005, 1.0998)] * 4 + [(1.0995, 1.0985)] + [(1.1005, 1.0998)] * 5
    ask = _shift_hl(bid, 0.0002)
    base = _path_base(bid, ask)
    sig = _sig_at_noon(6)
    trades = Engine(sig, base).backtest(_ManualStrategy([F, Tr, F, F, F, F], [F] * 6))

    row = trades.row(0, named=True)
    assert row["exit_reason"] == "sl"
    assert row["exit_time"] == base["timestamp"][4]
    assert row["pips"] == pytest.approx(-10.0)


def test_short_take_profit_exits_against_the_ask():
    # short exits by buying -> the walk uses the ASK arrays
    ask = [(1.1002, 1.0999)] * 5 + [(1.0985, 1.0970)] + [(1.1002, 1.0999)] * 6
    bid = _shift_hl(ask, -0.0002)
    base = _path_base(bid, ask)
    sig = _sig_at_noon(6)
    trades = Engine(sig, base).backtest(_ManualStrategy([F] * 6, [F, Tr, F, F, F, F]))

    row = trades.row(0, named=True)
    assert row["direction"] == "short"
    assert row["exit_reason"] == "tp"
    assert row["exit_time"] == base["timestamp"][5]
    assert row["pips"] == pytest.approx(20.0)


def test_short_stop_loss_exits_against_the_ask():
    ask = [(1.1004, 1.0999)] * 2 + [(1.1015, 1.1005)] + [(1.1004, 1.0999)] * 9
    bid = _shift_hl(ask, -0.0002)
    base = _path_base(bid, ask)
    sig = _sig_at_noon(6)
    trades = Engine(sig, base).backtest(_ManualStrategy([F] * 6, [F, Tr, F, F, F, F]))

    row = trades.row(0, named=True)
    assert row["exit_reason"] == "sl"
    assert row["exit_time"] == base["timestamp"][2]
    assert row["pips"] == pytest.approx(-10.0)


def test_no_touch_forces_close_at_end_of_data_last_bid_close():
    base = _path_base(FLAT_BID, FLAT_ASK)                  # never moves
    sig = _sig_at_noon(6)
    trades = Engine(sig, base).backtest(_ManualStrategy([F, Tr, F, F, F, F], [F] * 6))

    row = trades.row(0, named=True)
    assert row["exit_reason"] == "end_of_data"
    assert row["exit_time"] == base["timestamp"][base.height - 1]
    assert row["exit_price"] == base["bid_close"][base.height - 1]   # long closes at bid
    assert row["pips"] == pytest.approx(-2.0)              # the 2-pip spread, paid on the round trip


def test_rising_edge_dedup_state_signal_true_for_many_bars_is_one_trade():
    base = _path_base(FLAT_BID, FLAT_ASK)
    sig = _sig_at_noon(6)
    longs = [F, Tr, Tr, Tr, Tr, Tr]                        # one False->True edge, then held
    trades = Engine(sig, base).backtest(_ManualStrategy(longs, [F] * 6))
    assert trades.height == 1
    assert trades.row(0, named=True)["entry_time"] == sig["timestamp"][2]


# --------------------------------------------------------------------------- #
# Engine — opposite-signal exit raced against SL/TP (spec §2.2 / §0.2)
# --------------------------------------------------------------------------- #

class _ManualStrategyNoOppExit(_ManualStrategy):
    exit_on_opposite_signal = False


def test_opposite_signal_exit_when_path_never_touches_sl_tp():
    base = _flat_path(12)
    sig = _sig_at_noon(8)
    longs = [F, Tr, F, F, F, F, F, F]                      # long enters at bar 2
    shorts = [F, F, F, F, Tr, F, F, F]                     # opposite edge at k=4
    trades = Engine(sig, base).backtest(_ManualStrategy(longs, shorts))

    row = trades.row(0, named=True)
    assert row["direction"] == "long"
    assert row["exit_reason"] == "opposite_signal"
    assert row["exit_time"] == sig["timestamp"][5]         # acted on at k+1's open
    assert row["exit_price"] == sig["bid_open"][5]         # closing a long -> bid


def test_sl_preempts_opposite_signal_when_it_was_first():
    # SL touched at 12:00:03, well before bar k+1's open (12:15) -> SL wins
    bid = [(1.1005, 1.0998)] * 3 + [(1.0990, 1.0980)] + [(1.1005, 1.0998)] * 6
    base = _path_base(bid, _shift_hl(bid, 0.0002))
    sig = _sig_at_noon(8)
    longs = [F, Tr, F, F, F, F, F, F]
    shorts = [F, F, F, F, Tr, F, F, F]                     # opposite edge at k=4 -> k+1=5 (12:15)
    trades = Engine(sig, base).backtest(_ManualStrategy(longs, shorts))

    row = trades.row(0, named=True)
    assert row["exit_reason"] == "sl"
    assert row["exit_time"] == base["timestamp"][3]


def test_sl_on_the_signal_exit_bar_itself_does_not_count():
    # §0.2: on bar k+1 the signal exit fills at the open, BEFORE the range; the
    # SL that only prints at/after that open must not steal the exit.
    k1_open = datetime(2024, 6, 3, 12, 15, 0, tzinfo=UTC)
    bid = [(1.1000, 1.1000)] * 5 + [(1.1000, 1.0980)] + [(1.1000, 1.1000)] * 14   # SL dip at 12:15:00
    base = _path_base(bid, _shift_hl(bid, 0.0002),
                      start=k1_open - timedelta(seconds=5))
    sig = _sig_at_noon(8)
    longs = [F, Tr, F, F, F, F, F, F]
    shorts = [F, F, F, F, Tr, F, F, F]                     # k=4 -> exit acted at bar 5 = 12:15:00
    trades = Engine(sig, base).backtest(_ManualStrategy(longs, shorts))

    row = trades.row(0, named=True)
    assert row["exit_reason"] == "opposite_signal"
    assert row["exit_time"] == sig["timestamp"][5]


def test_opposite_edge_on_last_signal_bar_falls_through_to_end_of_data():
    base = _flat_path(12)
    sig = _sig_at_noon(6)
    longs = [F, Tr, F, F, F, F]
    shorts = [F, F, F, F, F, Tr]                           # edge on the last bar -> no k+1
    trades = Engine(sig, base).backtest(_ManualStrategy(longs, shorts))
    assert trades.row(0, named=True)["exit_reason"] == "end_of_data"


def test_exit_on_opposite_signal_false_ignores_the_opposite_edge():
    base = _flat_path(12)
    sig = _sig_at_noon(8)
    longs = [F, Tr, F, F, F, F, F, F]
    shorts = [F, F, F, F, Tr, F, F, F]

    on = Engine(sig, base).backtest(_ManualStrategy(longs, shorts))
    off = Engine(sig, base).backtest(_ManualStrategyNoOppExit(longs, shorts))
    assert on.row(0, named=True)["exit_reason"] == "opposite_signal"
    assert off.row(0, named=True)["exit_reason"] == "end_of_data"


def test_resume_a_recross_during_a_hold_opens_no_second_trade():
    base = _flat_path(2100)                                # hold runs past every signal bar
    sig = _sig_at_noon(8)
    longs = [F, Tr, F, Tr, F, Tr, F, F]                    # rising edges at 1, 3, 5
    trades = Engine(sig, base).backtest(_ManualStrategy(longs, [F] * 8))
    assert trades.height == 1


def test_resume_next_entry_is_never_before_the_previous_exit():
    # 1-minute bars so a quick TP frees the engine before the next edge
    sig = _sig_at_noon(8, step_min=1)                      # bars 11:58 .. 12:05
    bid = [(1.1005, 1.0998)] * 3 + [(1.1030, 1.1020)] + [(1.1000, 1.1000)] * 400
    base = _path_base(bid, _shift_hl(bid, 0.0002))
    longs = [F, Tr, F, F, F, F, Tr, F]                     # edges at 1 and 6
    trades = Engine(sig, base).backtest(_ManualStrategy(longs, [F] * 8))

    assert trades.height == 2
    assert trades["entry_time"][1] >= trades["exit_time"][0]
    assert trades["exit_reason"].to_list() == ["tp", "end_of_data"]


# --------------------------------------------------------------------------- #
# Engine — reverse_on_opposite_signal (always-in-the-market, spec §6)
# --------------------------------------------------------------------------- #

class _ReversingStrategy(_ManualStrategy):
    reverse_on_opposite_signal = True


class _ReverseButNoExit(_ManualStrategy):
    exit_on_opposite_signal = False
    reverse_on_opposite_signal = True


def test_reverse_requires_exit_on_opposite_signal():
    with pytest.raises(ValueError, match="reverse_on_opposite_signal requires"):
        _ReverseButNoExit([F, F], [F, F])


def test_reversal_opens_the_opposite_at_the_same_open():
    base = _flat_path(1200)                                # never touches SL/TP
    sig = _sig_at_noon(8)
    longs = [F, Tr, F, F, F, F, F, F]
    shorts = [F, F, F, F, Tr, F, F, F]                     # opposite edge at k=4 -> bar 5
    trades = Engine(sig, base).backtest(_ReversingStrategy(longs, shorts))

    assert trades.height == 2
    a, b = trades.row(0, named=True), trades.row(1, named=True)
    assert a["direction"] == "long" and a["exit_reason"] == "opposite_signal"
    assert a["exit_time"] == sig["timestamp"][5]
    assert a["exit_price"] == sig["bid_open"][5]           # close long -> bid
    assert b["direction"] == "short"
    assert b["entry_time"] == a["exit_time"]               # same instant
    assert b["entry_price"] == a["exit_price"]             # same open, one spread crossing


def test_reversal_chains_while_opposite_edges_keep_firing():
    base = _flat_path(2000)                                # 12:00:00 .. 12:33:19
    sig = _sig_at_noon(10)                                 # bars 11:50 .. 12:35
    longs = [F, Tr, F, F, F, F, Tr, F, F, F]               # long edges at 1, 6
    shorts = [F, F, F, Tr, F, F, F, F, F, F]               # short edge at 3
    trades = Engine(sig, base).backtest(_ReversingStrategy(longs, shorts))

    assert trades["direction"].to_list() == ["long", "short", "long"]
    assert trades["exit_reason"].to_list() == ["opposite_signal", "opposite_signal", "end_of_data"]
    assert trades["entry_time"][1] == trades["exit_time"][0]
    assert trades["entry_time"][2] == trades["exit_time"][1]


def test_reversal_chain_stops_when_a_trade_hits_sl():
    k1 = datetime(2024, 6, 3, 12, 15, 0, tzinfo=UTC)
    # flat until 12:15, then the ASK spikes -> the reversed SHORT stops out
    ask = [(1.1002, 1.1002)] * 10 + [(1.1015, 1.1002)] + [(1.1002, 1.1002)] * 19
    bid = _shift_hl(ask, -0.0002)
    base = _path_base(bid, ask, start=k1 - timedelta(seconds=5))
    sig = _sig_at_noon(8)
    longs = [F, Tr, F, F, F, F, F, F]
    shorts = [F, F, F, F, Tr, F, F, F]                     # opposite edge at k=4 -> bar 5 (12:15)
    trades = Engine(sig, base).backtest(_ReversingStrategy(longs, shorts))

    assert trades.height == 2
    assert trades["direction"].to_list() == ["long", "short"]
    assert trades["exit_reason"].to_list() == ["opposite_signal", "sl"]


def test_reverse_off_is_unchanged_one_trade_then_jump():
    base = _flat_path(1200)
    sig = _sig_at_noon(8)
    longs = [F, Tr, F, F, F, F, F, F]
    shorts = [F, F, F, F, Tr, F, F, F]
    trades = Engine(sig, base).backtest(_ManualStrategy(longs, shorts))  # reverse defaults False
    assert trades.height == 1
    assert trades.row(0, named=True)["exit_reason"] == "opposite_signal"


# --------------------------------------------------------------------------- #
# spread_pips_paid — round-trip cost recorded per trade (spec §3.2 step 0)
# --------------------------------------------------------------------------- #

def test_spread_pips_paid_flat_market_is_full_spread_and_equals_minus_pips():
    # _sig_at_noon: entry spread 2 pips -> half 1.0.  _flat_path close spread 2
    # pips -> exit half 1.0.  end_of_data exit.
    base = _flat_path(1200)
    sig = _sig_at_noon(8)
    row = Engine(sig, base).backtest(
        _ManualStrategy([F, Tr, F, F, F, F, F, F], [F] * 8)
    ).row(0, named=True)
    assert row["exit_reason"] == "end_of_data"
    assert row["spread_pips_paid"] == pytest.approx(2.0)        # 1.0 in + 1.0 out
    assert row["pips"] == pytest.approx(-2.0)                   # flat market -> lost exactly the spread
    assert row["pips"] + row["spread_pips_paid"] == pytest.approx(0.0)  # gross == 0


def test_spread_pips_paid_uses_the_spread_at_the_exit_second():
    # entry half-spread 1.0 (sig).  The 1s bar the TP hits on has a 4-pip close
    # spread -> exit half-spread 2.0 -> spread_pips_paid == 3.0.
    bid = [(1.1005, 1.0998)] * 3 + [(1.1035, 1.1025)] + [(1.1005, 1.0998)] * 6
    ask = _shift_hl(bid, 0.0002)
    ask[3] = (1.1039, 1.1029)                                  # widen only the TP-hit second
    base = _path_base(bid, ask)
    sig = _sig_at_noon(6)
    row = Engine(sig, base).backtest(
        _ManualStrategy([F, Tr, F, F, F, F], [F] * 6)
    ).row(0, named=True)
    assert row["exit_reason"] == "tp"
    assert row["spread_pips_paid"] == pytest.approx(3.0)


# --------------------------------------------------------------------------- #
# _resolve_exit — numba 1s-path SL/TP walk (spec §2.3, pass 5b part 1)
# --------------------------------------------------------------------------- #

# Levels for a LONG entered at 1.1000 with sl=10 / tp=20 pips.
SL_L, TP_L = 1.0990, 1.1020
# Levels for a SHORT entered at 1.1000 with sl=10 / tp=20 pips.
SL_S, TP_S = 1.1010, 1.0980


def _arr(vals):
    return np.asarray(vals, dtype=np.float64)


def _walk(high, low, direction, sl, tp, start=0):
    high, low = _arr(high), _arr(low)
    k, price, reason = _resolve_exit(high, low, start, len(high), direction, sl, tp)
    return int(k), float(price), int(reason)


def test_resolve_exit_is_njit_compiled():
    assert hasattr(_resolve_exit, "py_func")          # numba dispatcher
    # first real call forces JIT compilation
    assert _walk([1.0] * 3, [1.0] * 3, 1, 0.5, 2.0) == (3, 0.0, 0)


def test_long_hits_stop_loss():
    highs = [1.1000] * 6                              # TP (1.1020) never reached
    lows = [1.0996, 1.0995, 1.0994, SL_L, 1.0993, 1.0992]   # SL touched at k=3
    assert _walk(highs, lows, 1, SL_L, TP_L) == (3, SL_L, 1)


def test_long_hits_take_profit():
    highs = [1.1005, 1.1010, TP_L, 1.1015, 1.1012, 1.1011]  # TP touched at k=2
    lows = [1.0995] * 6                               # SL (1.0990) never reached
    assert _walk(highs, lows, 1, SL_L, TP_L) == (2, TP_L, 2)


def test_long_no_touch_returns_end_idx():
    highs = [1.1000, 1.1005, 1.1010, 1.1015, 1.1018, 1.1019]
    lows = [1.0995, 1.0994, 1.0993, 1.0992, 1.0991, 1.0991]
    assert _walk(highs, lows, 1, SL_L, TP_L) == (6, 0.0, 0)


def test_same_bar_straddles_both_levels_stop_loss_wins():
    highs = [1.1000, 1.1030, 1.1000]                  # k=1 high >= TP ...
    lows = [1.0995, 1.0980, 1.0995]                   # ... and k=1 low <= SL
    assert _walk(highs, lows, 1, SL_L, TP_L) == (1, SL_L, 1)


def test_short_hits_stop_loss_on_ask_high():
    # short exits by buying -> caller passes the ASK arrays
    ask_high = [1.1004, 1.1008, SL_S, 1.1012, 1.1011, 1.1009]   # SL touched at k=2
    ask_low = [1.0999] * 6                            # TP (1.0980) never reached
    assert _walk(ask_high, ask_low, -1, SL_S, TP_S) == (2, SL_S, 1)


def test_short_hits_take_profit_on_ask_low():
    ask_high = [1.1005] * 6                           # SL (1.1010) never reached
    ask_low = [1.0995, 1.0988, TP_S, 1.0975, 1.0979, 1.0982]    # TP touched at k=2
    assert _walk(ask_high, ask_low, -1, SL_S, TP_S) == (2, TP_S, 2)


def test_start_idx_skips_earlier_touches():
    highs = [1.1000] * 6
    lows = [SL_L, SL_L, 1.0995, 1.0996, 1.0997, 1.0998]   # SL touches at k=0 and k=1
    # from k=0 the touch is found immediately
    assert _walk(highs, lows, 1, SL_L, TP_L, start=0) == (0, SL_L, 1)
    # from k=2 those earlier touches are invisible -> nothing in [2, 6)
    assert _walk(highs, lows, 1, SL_L, TP_L, start=2) == (6, 0.0, 0)


# --------------------------------------------------------------------------- #
# _sl_tp_levels
# --------------------------------------------------------------------------- #

def test_sl_tp_levels_long():
    sl, tp = _sl_tp_levels(1, 1.1000, 10, 20)
    assert sl == pytest.approx(1.0990)               # SL below entry
    assert tp == pytest.approx(1.1020)               # TP above entry


def test_sl_tp_levels_short():
    sl, tp = _sl_tp_levels(-1, 1.1000, 10, 20)
    assert sl == pytest.approx(1.1010)               # SL above entry
    assert tp == pytest.approx(1.0980)               # TP below entry


def test_sl_tp_levels_uses_pip_constant():
    sl, tp = _sl_tp_levels(1, 1.2000, 5, 5)
    assert sl == pytest.approx(1.2000 - 5 * PIP)
    assert tp == pytest.approx(1.2000 + 5 * PIP)
