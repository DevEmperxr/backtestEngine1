"""Tests for lib/signals.py — sma + crossover (spec §4, and the §0.4 / §6 guard)."""

import polars as pl
import pytest

from datetime import datetime, time, timezone

from datetime import timedelta

from lib.signals import atr, crossover, higher_tf_join, rsi, session_window, sma


# --------------------------------------------------------------------------- #
# sma
# --------------------------------------------------------------------------- #

def test_sma_hand_checked_values_and_null_warmup():
    s = pl.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]})
    out = s.select(m=sma(pl.col("x"), 3))["m"].to_list()
    # first n-1 entries are null (NOT a partial mean like 1.0 or 1.5)
    assert out[:2] == [None, None]
    assert out[2:] == [2.0, 3.0, 4.0, 5.0]


def test_sma_returns_expr_and_rejects_bad_n():
    assert isinstance(sma(pl.col("x"), 5), pl.Expr)
    with pytest.raises(ValueError):
        sma(pl.col("x"), 0)


def test_sma_does_not_mutate_input_frame():
    df = pl.DataFrame({"x": [1.0, 2.0, 3.0]})
    before = df.clone()
    df.select(sma(pl.col("x"), 2))
    assert df.equals(before)


# --------------------------------------------------------------------------- #
# crossover
# --------------------------------------------------------------------------- #

def _cross(fast, slow):
    df = pl.DataFrame({"fast": fast, "slow": slow})
    cu, cd = crossover(pl.col("fast"), pl.col("slow"))
    return df.select(cross_up=cu, cross_down=cd)


def test_crossover_zigzag_known_crossings():
    # fast dips below slow once, pops above twice -> 2 up, 1 down
    fast = [1.0, 3.0, 5.0, 3.0, 1.0, 3.0, 5.0]
    slow = [2.0] * 7
    out = _cross(fast, slow)
    up = [i for i, v in enumerate(out["cross_up"].to_list()) if v]
    down = [i for i, v in enumerate(out["cross_down"].to_list()) if v]
    assert up == [1, 5]
    assert down == [4]


def test_crossover_output_is_boolean_with_no_nulls():
    out = _cross([1.0, 3.0, 5.0, 3.0, 1.0], [2.0] * 5)
    for col in ("cross_up", "cross_down"):
        assert out.schema[col] == pl.Boolean
        assert out[col].null_count() == 0


def test_crossover_no_signal_at_the_warmup_boundary():
    # fast = SMA(2), slow = SMA(4): both first valid at index 3. The series dips
    # then rises, so the real cross-up is at index 6 — index 3 must stay False.
    df = pl.DataFrame({"x": [5.0, 4.0, 3.0, 2.0, 1.0, 2.0, 4.0, 6.0, 8.0]})
    cu, cd = crossover(sma(pl.col("x"), 2), sma(pl.col("x"), 4))
    out = df.select(cross_up=cu, cross_down=cd)
    up = out["cross_up"].to_list()
    assert up[3] is False                       # warmup boundary — no spurious cross
    assert [i for i, v in enumerate(up) if v] == [6]
    assert out["cross_up"].null_count() == 0


def test_crossover_is_pure():
    df = pl.DataFrame({"fast": [1.0, 3.0, 2.0], "slow": [2.0, 2.0, 2.0]})
    before = df.clone()
    cu, cd = crossover(pl.col("fast"), pl.col("slow"))
    df.select(cross_up=cu, cross_down=cd)
    assert df.equals(before)


# --------------------------------------------------------------------------- #
# spec §0.4 / §6 regression — the result must be a REAL bool, not object-dtype
# --------------------------------------------------------------------------- #

def test_crossover_boolean_dtype_regression():
    """§0.4: the prototype got a 44x-inflated signal count when a crossover
    column became object-dtype (Python bools) and a later `~` did a *bitwise*
    invert (`~True == -2`, `~False == -1` — both truthy). Guard: the result is
    genuine pl.Boolean, and `~` behaves as logical not (so `sum(~x) + sum(x)`
    equals the row count), and the count is the small hand-known value."""
    fast = [1.0, 3.0, 5.0, 3.0, 1.0, 3.0, 5.0]
    slow = [2.0] * 7
    df = pl.DataFrame({"fast": fast, "slow": slow})
    cu, cd = crossover(pl.col("fast"), pl.col("slow"))
    out = df.select(cross_up=cu, cross_down=cd)

    up = out["cross_up"]
    assert up.dtype == pl.Boolean
    assert up.sum() == 2                                    # sane, not inflated
    assert (~up).sum() == up.len() - up.sum()               # logical not, not bitwise

    # the exact downstream move the engine/strategy makes
    acted = df.select(
        a=(cu).shift(1, fill_value=False) & ~(cd).shift(1, fill_value=False)
    )["a"]
    assert acted.dtype == pl.Boolean
    assert acted.null_count() == 0


# --------------------------------------------------------------------------- #
# atr
# --------------------------------------------------------------------------- #

def test_atr_hand_checked_with_gap_and_null_warmup():
    df = pl.DataFrame({
        "h": [1.0, 2.0, 5.0, 4.0],
        "l": [0.0, 1.0, 4.0, 3.0],
        "c": [0.5, 1.5, 4.5, 3.5],
    })
    out = df.select(a=atr(pl.col("h"), pl.col("l"), pl.col("c"), 2))["a"].to_list()
    # TR: [1 (no prev), max(1,1.5,0.5)=1.5, max(1,3.5,2.5)=3.5, max(1,0.5,1.5)=1.5]
    assert out[0] is None
    assert out[1:] == pytest.approx([1.25, 2.5, 2.5])


def test_atr_row_t_ignores_later_bars():
    base = pl.DataFrame({"h": [1.0, 2.0, 3.0], "l": [0.0, 1.0, 2.0], "c": [0.5, 1.5, 2.5]})
    later = pl.concat([base, pl.DataFrame({"h": [99.0], "l": [-99.0], "c": [0.0]})])
    f = lambda d: d.select(a=atr(pl.col("h"), pl.col("l"), pl.col("c"), 2))["a"].to_list()
    assert f(later)[:3] == f(base)


def test_atr_rejects_bad_n():
    with pytest.raises(ValueError):
        atr(pl.col("h"), pl.col("l"), pl.col("c"), 0)


# --------------------------------------------------------------------------- #
# session_window — 07:00 New York -> 16:00 London
# --------------------------------------------------------------------------- #

UTC = timezone.utc


def _in_ny_london(*stamps):
    df = pl.DataFrame({"ts": list(stamps)}, schema={"ts": pl.Datetime("us", "UTC")})
    expr = session_window(pl.col("ts"), "America/New_York", time(7), "Europe/London", time(16))
    out = df.select(w=expr)
    assert out.schema["w"] == pl.Boolean
    return out["w"].to_list()


def test_session_window_winter_is_12_to_16_utc():
    d = lambda h, m=0: datetime(2024, 1, 10, h, m, tzinfo=UTC)
    assert _in_ny_london(d(11, 55), d(12), d(15, 55), d(16)) == [False, True, True, False]


def test_session_window_summer_is_11_to_15_utc():
    d = lambda h, m=0: datetime(2024, 7, 10, h, m, tzinfo=UTC)
    assert _in_ny_london(d(10, 55), d(11), d(14, 55), d(15)) == [False, True, True, False]


def test_session_window_dst_mismatch_week_is_5h():
    # 2024-03-20: US already on EDT (07:00 NY = 11:00 UTC), UK still GMT (16:00 = 16:00 UTC)
    d = lambda h, m=0: datetime(2024, 3, 20, h, m, tzinfo=UTC)
    assert _in_ny_london(d(10, 55), d(11), d(15, 55), d(16)) == [False, True, True, False]


def test_session_window_late_evening_and_early_morning_are_out():
    # the bug this guards: 01:00 London is "before 16:00 London" and its NY time
    # (20:00 the previous day) is "after 07:00 NY" -- naive hour checks say IN
    assert _in_ny_london(
        datetime(2024, 1, 11, 1, 0, tzinfo=UTC),
        datetime(2024, 1, 10, 23, 0, tzinfo=UTC),
        datetime(2024, 1, 10, 5, 0, tzinfo=UTC),
    ) == [False, False, False]


# --------------------------------------------------------------------------- #
# higher_tf_join — 5m/15m features on 1m rows, no peeking at a forming bar
# --------------------------------------------------------------------------- #

def _one_min(closes, start=datetime(2024, 6, 3, 12, 0, tzinfo=UTC)):
    ts = [start + timedelta(minutes=i) for i in range(len(closes))]
    return pl.DataFrame({"timestamp": ts, "close_time": [t + timedelta(minutes=1) for t in ts],
                         "c": closes})


def _join5(df):
    return higher_tf_join(df, "5m", "c", {"htf_close": pl.col("close")})


def test_higher_tf_join_only_sees_closed_buckets():
    df = _one_min([float(i) for i in range(12)])           # 12:00..12:11
    out = _join5(df)["htf_close"].to_list()
    # rows 12:00-12:03 close before the first 5m bar closes (12:05) -> null
    assert out[:4] == [None] * 4
    # row 12:04 closes at 12:05 == first bucket's close -> sees its close (row 4's c)
    assert out[4:9] == [4.0] * 5
    assert out[9:] == [9.0] * 3                            # second bucket closes 12:10


def test_higher_tf_join_future_bars_never_change_earlier_rows():
    a = [float(i) for i in range(15)]
    b = a[:7] + [999.0] * 8                                # change everything after 12:06
    out_a, out_b = _join5(_one_min(a))["htf_close"], _join5(_one_min(b))["htf_close"]
    # rows up to 12:06 (closing <= 12:07) must be identical, including the ones
    # whose 5m bucket (12:05-12:10) is still forming
    assert out_a[:7].to_list() == out_b[:7].to_list()


def test_higher_tf_join_features_and_nesting_check():
    df = _one_min([1.0, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    out = higher_tf_join(df, "5m", "c", {"up": pl.col("close") > pl.col("close").shift(1)})
    assert out["up"].to_list()[9] is True                  # bucket 2 close 10 > bucket 1 close 5
    bad = df.with_columns(close_time=pl.col("timestamp") + timedelta(minutes=7))
    with pytest.raises(ValueError, match="nest"):
        _join5(bad)


# --------------------------------------------------------------------------- #
# rsi
# --------------------------------------------------------------------------- #

def _rsi(xs, n):
    return pl.DataFrame({"x": xs}).select(r=rsi(pl.col("x"), n))["r"].to_list()


def test_rsi_warmup_and_extremes():
    up = _rsi([1.0, 2, 3, 4, 5], 2)
    assert up[:2] == [None, None] and up[2:] == [100.0, 100.0, 100.0]
    down = _rsi([5.0, 4, 3, 2, 1], 2)
    assert down[2:] == pytest.approx([0.0, 0.0, 0.0])


def test_rsi_hand_checked_wilder():
    # diffs: +1, -1, +2 ; n=2, alpha=1/2, adjust=False, ewm seeded at first diff
    # gain ewm: 1, 0.5, 1.25 ; loss ewm: 0, 0.5, 0.25 ; rsi[3] = 100-100/(1+5) = 83.33
    out = _rsi([1.0, 2, 1, 3], 2)
    assert out[3] == pytest.approx(100 - 100 / 6)


def test_rsi_row_t_ignores_later_bars():
    a = [1.0, 2, 1.5, 3, 2.5, 2]
    assert _rsi(a + [100.0], 3)[:6] == _rsi(a, 3)



# --------------------------------------------------------------------------- #
# trend detectors (research 020)
# --------------------------------------------------------------------------- #

from lib.signals import adx, choppiness, efficiency_ratio, return_autocorr, rolling_r2, variance_ratio


def _col(expr, **cols):
    return pl.DataFrame(cols).select(o=expr)["o"].to_list()


def test_efficiency_ratio_line_chop_and_hand_value():
    line = [float(i) for i in range(10)]
    assert _col(efficiency_ratio(pl.col("x"), 3), x=line)[3:] == pytest.approx([1.0] * 7)
    chop = [0.0, 1.0] * 5
    assert _col(efficiency_ratio(pl.col("x"), 4), x=chop)[4:] == pytest.approx([0.0] * 6)
    # 1,2,4,3: net |3-1| = 2, path 1+2+1 = 4 -> 0.5
    assert _col(efficiency_ratio(pl.col("x"), 3), x=[1.0, 2, 4, 3])[3] == pytest.approx(0.5)
    assert _col(efficiency_ratio(pl.col("x"), 3), x=[1.0] * 5)[4] is None   # flat: no path


def test_rolling_r2_line_is_one_and_noise_is_low():
    assert _col(rolling_r2(pl.col("x"), 5), x=[2.0 * i for i in range(8)])[4:] == pytest.approx([1.0] * 4)
    assert _col(rolling_r2(pl.col("x"), 4), x=[0.0, 1, 0, 1, 0, 1])[5] < 0.3


def test_variance_ratio_trend_vs_alternating():
    trend = [float(i) + (0.1 if i % 3 == 0 else 0) for i in range(40)]
    alt = [0.0, 1.0] * 20
    assert _col(variance_ratio(pl.col("x"), 2, 20), x=alt)[-1] < 0.2      # perfect reversal
    assert _col(variance_ratio(pl.col("x"), 2, 20), x=trend)[-1] > 0.5


def test_return_autocorr_signs():
    alt = [0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0]
    assert _col(return_autocorr(pl.col("x"), 5), x=alt)[-1] == pytest.approx(-1.0)


def test_adx_and_chop_trend_vs_range():
    n = 60
    up = [float(i) for i in range(n)]
    rng = [0.0, 1.0] * (n // 2)
    hi = lambda c: [v + 0.5 for v in c]
    lo = lambda c: [v - 0.5 for v in c]
    adx_up = _col(adx(pl.col("h"), pl.col("l"), pl.col("c"), 14), h=hi(up), l=lo(up), c=up)[-1]
    adx_rng = _col(adx(pl.col("h"), pl.col("l"), pl.col("c"), 14), h=hi(rng), l=lo(rng), c=rng)[-1]
    assert adx_up > 90 and adx_rng < 30
    ch_up = _col(choppiness(pl.col("h"), pl.col("l"), pl.col("c"), 14), h=hi(up), l=lo(up), c=up)[-1]
    ch_rng = _col(choppiness(pl.col("h"), pl.col("l"), pl.col("c"), 14), h=hi(rng), l=lo(rng), c=rng)[-1]
    assert ch_up < 30 and ch_rng > 80


@pytest.mark.parametrize("make", [
    lambda: efficiency_ratio(pl.col("c"), 5), lambda: rolling_r2(pl.col("c"), 5),
    lambda: variance_ratio(pl.col("c"), 2, 6), lambda: return_autocorr(pl.col("c"), 5),
    lambda: adx(pl.col("h"), pl.col("l"), pl.col("c"), 5),
    lambda: choppiness(pl.col("h"), pl.col("l"), pl.col("c"), 5),
])
def test_detectors_row_t_ignores_later_bars(make):
    import random
    rnd = random.Random(0)
    c = [100.0 + sum(rnd.uniform(-1, 1) for _ in range(i)) for i in range(30)]
    later = c[:20] + [999.0] * 10
    f = lambda cc: _col(make(), c=cc, h=[v + 0.5 for v in cc], l=[v - 0.5 for v in cc])[:20]
    a, b = f(c), f(later)
    assert all((x is None and y is None) or x == pytest.approx(y) for x, y in zip(a, b))
