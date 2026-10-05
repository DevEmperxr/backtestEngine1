"""Tests for lib/signals.py — sma + crossover (spec §4, and the §0.4 / §6 guard)."""

import polars as pl
import pytest

from datetime import datetime, time, timezone

from lib.signals import atr, crossover, session_window, sma


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
