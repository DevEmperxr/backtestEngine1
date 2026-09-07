"""Tests for the data layer (spec §6 — sanity-check discipline).

Builds tiny synthetic polars frames in code and asserts each hard check fires,
that clean data passes, and that the gap classifier labels weekend / holiday /
unexplained correctly (including the size guard on the weekend rule and the
sub-threshold hole that must still surface in the report).
"""

from datetime import datetime, timezone

import polars as pl
import pytest

from lib.data import (
    DataQualityError,
    FxData,
    analyze_gaps,
    easter_sunday,
    fx_holidays,
    load_1s_data,
    normalize_1s,
    resample,
    validate_1s,
)

from datetime import date

UTC = timezone.utc


def T(y=2024, mo=6, d=3, h=12, mi=0, s=0) -> datetime:
    """A tz-aware UTC datetime. 2024-06-03 is a Monday (default)."""
    return datetime(y, mo, d, h, mi, s, tzinfo=UTC)


def bar(ts: datetime, bid: float = 1.1000, ask: float = 1.1002, **override) -> dict:
    """One internally-consistent bid/ask bar as a row dict."""
    row = dict(
        timestamp=ts,
        bid_open=bid, bid_high=bid, bid_low=bid, bid_close=bid, bid_volume=1.0,
        ask_open=ask, ask_high=ask, ask_low=ask, ask_close=ask, ask_volume=1.0,
    )
    row.update(override)
    return row


def frame(rows: list[dict]) -> pl.DataFrame:
    return pl.DataFrame(rows)


# --------------------------------------------------------------------------- #
# clean data passes
# --------------------------------------------------------------------------- #

def test_clean_frame_passes():
    df = frame([bar(T(s=0)), bar(T(s=1)), bar(T(s=2))])
    validate_1s(df)  # must not raise

    data = FxData(df, verbose=False)
    assert data.df.height == 3
    assert data.gap_summary["n_unexplained_gaps"] == 0
    assert isinstance(load_1s_data(df), pl.DataFrame)


def test_accepts_lazyframe():
    lf = frame([bar(T(s=0)), bar(T(s=1))]).lazy()
    assert FxData(lf, verbose=False).df.height == 2


def test_accepts_string_timestamps():
    df = frame([bar(T(s=0)), bar(T(s=1))]).with_columns(
        pl.col("timestamp").dt.strftime("%Y-%m-%d %H:%M:%S%z")
    )
    assert df.schema["timestamp"] == pl.String
    assert FxData(df, verbose=False).df.schema["timestamp"] != pl.String


# --------------------------------------------------------------------------- #
# hard checks each raise
# --------------------------------------------------------------------------- #

def test_conflicting_duplicate_timestamp_raises():
    dup = bar(T(s=0), bid=1.5)  # same timestamp, different values
    rows = [bar(T(s=0)), dup, bar(T(s=1))]
    with pytest.raises(DataQualityError, match="conflicting"):
        FxData(frame(rows), verbose=False)


def test_exact_duplicate_rows_dropped_not_raised():
    r = bar(T(s=0))
    data = FxData(frame([r, dict(r), bar(T(s=1))]), verbose=False)
    assert data.df.height == 2
    assert data.n_exact_duplicate_rows_dropped == 1


def test_high_below_open_raises():
    bad = bar(T(s=0))
    bad["bid_high"] = bad["bid_open"] - 0.01
    with pytest.raises(DataQualityError, match="OHLC"):
        FxData(frame([bad, bar(T(s=1))]), verbose=False)


def test_negative_spread_raises():
    bad = bar(T(s=0))
    for f in ("open", "high", "low", "close"):
        bad[f"ask_{f}"] = bad[f"bid_{f}"] - 0.001  # ask below bid, ask still consistent
    with pytest.raises(DataQualityError, match="spread"):
        FxData(frame([bad, bar(T(s=1))]), verbose=False)


def test_null_raises():
    bad = bar(T(s=0))
    bad["bid_close"] = None
    with pytest.raises(DataQualityError, match="null"):
        FxData(frame([bad, bar(T(s=1))]), verbose=False)


def test_nan_raises():
    bad = bar(T(s=0))
    bad["ask_high"] = float("nan")
    with pytest.raises(DataQualityError, match="NaN"):
        FxData(frame([bad, bar(T(s=1))]), verbose=False)


def test_missing_column_raises():
    df = frame([bar(T(s=0)), bar(T(s=1))]).drop("ask_volume")
    with pytest.raises(DataQualityError, match="column"):
        validate_1s(df)


def test_empty_frame_raises():
    df = frame([bar(T(s=0))]).clear()
    with pytest.raises(DataQualityError, match="no rows"):
        validate_1s(df)


# --------------------------------------------------------------------------- #
# gap classification
# --------------------------------------------------------------------------- #

def test_fabricated_midweek_hole_is_unexplained():
    rows = [
        bar(T(d=3, h=12, s=0)),
        bar(T(d=3, h=12, s=1)),
        bar(T(d=3, h=15, s=1)),   # 3-hour jump, still Monday
        bar(T(d=3, h=15, s=2)),
    ]
    summary, gaps = analyze_gaps(frame(rows).sort("timestamp"), report_threshold_s=600)
    ux = gaps.filter(pl.col("kind") == "unexplained")
    assert ux.height == 1
    assert ux["gap_s"][0] == pytest.approx(3 * 3600)
    assert summary["n_unexplained_gaps"] == 1


def test_real_weekend_gap_is_weekend():
    rows = [
        bar(T(d=7, h=20, s=0)),   # 2024-06-07 Friday
        bar(T(d=9, h=21, s=0)),   # 2024-06-09 Sunday  (~49h)
        bar(T(d=9, h=21, s=1)),
    ]
    summary, gaps = analyze_gaps(frame(rows).sort("timestamp"))
    assert summary["n_weekend_gaps"] == 1
    assert gaps.filter(pl.col("kind") == "weekend").height == 1
    assert summary["n_unexplained_gaps"] == 0


def test_small_friday_gap_not_labelled_weekend():
    # Fri 20:00 -> Fri 20:10: only 600s, must NOT be tagged weekend (size guard)
    rows = [
        bar(T(d=7, h=20, s=0)),
        bar(T(d=7, h=20, mi=10, s=0)),
        bar(T(d=7, h=20, mi=10, s=1)),
    ]
    summary, gaps = analyze_gaps(frame(rows).sort("timestamp"), report_threshold_s=300)
    assert summary["n_weekend_gaps"] == 0
    assert gaps.filter(pl.col("kind") == "unexplained").height == 1


def test_holiday_gap_is_holiday():
    rows = [
        bar(T(mo=12, d=24, h=22, s=0)),
        bar(T(mo=12, d=25, h=23, s=0)),   # ~25h across Christmas
        bar(T(mo=12, d=25, h=23, s=1)),
    ]
    summary, gaps = analyze_gaps(frame(rows).sort("timestamp"))
    assert summary["n_holiday_gaps"] >= 1
    assert gaps.filter(pl.col("kind") == "holiday").height >= 1


# --------------------------------------------------------------------------- #
# holiday calendar — computed per year, any year
# --------------------------------------------------------------------------- #

def test_easter_computus_known_years():
    assert easter_sunday(2024) == date(2024, 3, 31)
    assert easter_sunday(2025) == date(2025, 4, 20)
    assert easter_sunday(2030) == date(2030, 4, 21)


def test_fx_holidays_covers_good_friday_and_christmas_for_any_year():
    h = fx_holidays(2027)
    assert date(2027, 3, 26) in h    # Good Friday 2027 (Easter 3/28)
    assert date(2027, 12, 25) in h
    assert date(2027, 1, 1) in h
    assert len(fx_holidays(range(2023, 2026))) == 18   # 6 dates x 3 years


def test_holidays_auto_derived_from_data_span():
    # a 2026 Christmas gap must classify as holiday with NO explicit holidays arg
    rows = [
        bar(T(y=2026, mo=12, d=24, h=22, s=0)),
        bar(T(y=2026, mo=12, d=25, h=23, s=0)),
        bar(T(y=2026, mo=12, d=25, h=23, s=1)),
    ]
    data = FxData(frame(rows), verbose=False)
    assert date(2026, 12, 25) in data.holidays
    assert data.gap_summary["n_holiday_gaps"] >= 1
    assert data.gap_summary["n_unexplained_gaps"] == 0


# --------------------------------------------------------------------------- #
# reporting — a sub-threshold hole must not hide behind "0"
# --------------------------------------------------------------------------- #

def test_report_surfaces_subthreshold_gap(capsys):
    rows = [
        bar(T(d=3, h=12, s=0)),
        bar(T(d=3, h=12, mi=5, s=0)),   # 300s midweek gap, below the 600s threshold
        bar(T(d=3, h=12, mi=5, s=1)),
    ]
    FxData(frame(rows), gap_report_threshold_s=600, verbose=True)
    out = capsys.readouterr().out
    assert "unexplained gaps .... 0" in out
    assert "largest unexpl. gap" in out
    assert "300s" in out


def test_strict_gaps_raises_on_unexplained():
    rows = [
        bar(T(d=3, h=12, s=0)),
        bar(T(d=3, h=13, s=0)),   # 1h midweek gap
        bar(T(d=3, h=13, s=1)),
    ]
    with pytest.raises(DataQualityError, match="strict_gaps"):
        FxData(frame(rows), gap_report_threshold_s=600, strict_gaps=True, verbose=False)


# --------------------------------------------------------------------------- #
# normalize
# --------------------------------------------------------------------------- #

def test_normalize_sorts_and_counts_dupes():
    r = bar(T(s=5))
    df = frame([bar(T(s=2)), r, dict(r), bar(T(s=1))])
    out, n_dropped = normalize_1s(df)
    assert n_dropped == 1
    assert out["timestamp"].to_list() == sorted(out["timestamp"].to_list())


# --------------------------------------------------------------------------- #
# resample (spec §1 / §6)
# --------------------------------------------------------------------------- #

def ticks(specs: list[tuple]) -> pl.DataFrame:
    """specs: list of (datetime, bid, ask)."""
    return frame([bar(ts, bid=b, ask=a) for ts, b, a in specs]).sort("timestamp")


def test_resample_ohlc_bid_and_ask_correct():
    df = ticks([
        (T(h=12, mi=0, s=0),  1.10, 1.1002),
        (T(h=12, mi=0, s=30), 1.12, 1.1203),   # highs
        (T(h=12, mi=1, s=0),  1.09, 1.0902),   # lows
        (T(h=12, mi=4, s=59), 1.11, 1.1105),   # closes
        (T(h=12, mi=5, s=0),  1.20, 1.2002),   # 2nd bucket
        (T(h=12, mi=9, s=59), 1.21, 1.2103),
    ])
    b0 = resample(df, "5m").row(0, named=True)
    assert (b0["bid_open"], b0["bid_high"], b0["bid_low"], b0["bid_close"]) == (1.10, 1.12, 1.09, 1.11)
    assert (b0["ask_open"], b0["ask_high"], b0["ask_low"], b0["ask_close"]) == (1.1002, 1.1203, 1.0902, 1.1105)
    assert b0["bid_volume"] == 4.0 and b0["ask_volume"] == 4.0
    assert b0["n_ticks"] == 4


def test_resample_drops_trailing_partial_bucket():
    base = [(T(h=12, mi=0, s=0), 1.10, 1.1002), (T(h=12, mi=3, s=0), 1.11, 1.1102)]
    # data ends mid-bucket -> [12:00, 12:05) never finished -> dropped
    assert resample(ticks(base), "5m").height == 0
    # data ends exactly on the boundary (12:04:59 covers [59, 60) -> 12:05:00) -> kept
    out = resample(ticks(base + [(T(h=12, mi=4, s=59), 1.12, 1.1202)]), "5m")
    assert out.height == 1
    assert out.row(0, named=True)["timestamp"] == T(h=12, mi=0, s=0)


def test_resample_close_time_is_generalized_per_timeframe():
    specs = [(T(h=12), 1.10, 1.1002)]
    specs += [(T(h=12 + i // 60, mi=i % 60, s=0), 1.10, 1.1002) for i in range(1, 120)]
    specs += [(T(h=13, mi=59, s=59), 1.10, 1.1002)]
    df = ticks(specs)
    for tf, secs in (("5m", 300), ("1h", 3600)):
        out = resample(df, tf, fill_gaps=False)
        assert out.height > 0
        deltas = (out["close_time"] - out["timestamp"]).dt.total_seconds().unique().to_list()
        assert deltas == [secs]


def test_resample_fills_intrasession_gap_with_flat_candles():
    df = ticks([
        (T(h=12, mi=0, s=0),   1.10, 1.1002),
        (T(h=12, mi=30, s=0),  1.15, 1.1502),
        (T(h=12, mi=34, s=59), 1.16, 1.1602),
    ])
    out = resample(df, "5m")
    assert out["timestamp"].to_list() == [T(h=12, mi=m, s=0) for m in (0, 5, 10, 15, 20, 25, 30)]
    flat = out.filter(pl.col("n_ticks") == 0)
    assert flat.height == 5
    r = flat.row(0, named=True)
    assert r["bid_open"] == r["bid_high"] == r["bid_low"] == r["bid_close"] == 1.10
    assert r["ask_open"] == r["ask_high"] == r["ask_low"] == r["ask_close"] == 1.1002
    assert r["bid_volume"] == 0.0 and r["ask_volume"] == 0.0


def test_resample_does_not_fill_a_weekend_gap():
    df = ticks([
        (T(d=7, h=20, s=0),        1.10, 1.1002),   # Friday 2024-06-07
        (T(d=9, h=21, s=0),        1.11, 1.1102),   # Sunday 2024-06-09 (~49h later)
        (T(d=9, h=21, mi=4, s=59), 1.12, 1.1202),
    ])
    out = resample(df, "5m")
    assert out.height == 2
    assert out["n_ticks"].to_list() == [1, 2]


def test_resample_fill_gaps_false_returns_only_real_buckets():
    df = ticks([
        (T(h=12, mi=0, s=0),   1.10, 1.1002),
        (T(h=12, mi=30, s=0),  1.15, 1.1502),
        (T(h=12, mi=34, s=59), 1.16, 1.1602),
    ])
    out = resample(df, "5m", fill_gaps=False)
    assert out["timestamp"].to_list() == [T(h=12, s=0), T(h=12, mi=30, s=0)]
