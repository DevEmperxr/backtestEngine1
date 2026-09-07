"""Data layer for the FX backtester (spec §1).

Loads the 1-second EURUSD bid/ask CSV, runs the sanity checks from spec §0.5 at
1s resolution as vectorized polars expressions, and hands back a cleaned frame.

The real file on disk is a *single* CSV with bid and ask OHLCV side by side
(`timestamp, bid_open, ..., bid_volume, ask_open, ..., ask_volume`), not the two
separate ask/bid files the spec originally assumed. Everything here is built
around the actual schema.

The pipeline is three separable steps so the engine can reuse the check step on
a frame it was handed (spec §2.1) without re-loading:

    read_1s_csv(path)   -> raw pl.DataFrame        (one full read, schema + parse)
    normalize_1s(df)    -> (clean df, n_dropped)   (drop exact-dup rows, sort)
    validate_1s(df)     -> None | raises           (the hard §0.5 checks)

`FxData` runs all three plus the gap report. `load_1s_data` is the spec's
one-call entry point.

Usage
-----
    from lib.data import FxData, load_1s_data

    data = FxData("data/EURUSD_1s_2024.csv")   # raises if anything fails
    df = data.df                               # cleaned pl.DataFrame

    df = load_1s_data("data/EURUSD_1s_2024.csv")   # just the frame

    # engine.py, on an already-loaded frame:
    from lib.data import validate_1s
    validate_1s(df)

or from the command line:

    python lib/data.py data/EURUSD_1s_2024.csv
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

import polars as pl

# --------------------------------------------------------------------------- #
# constants
# --------------------------------------------------------------------------- #

PIP = 0.0001  # EURUSD; hardcoded on purpose (spec §2.4 — no premature multi-pair)

_SIDES = ("bid", "ask")
_OHLC = ("open", "high", "low", "close")

EXPECTED_COLUMNS = (
    "timestamp",
    *(f"{s}_{f}" for s in _SIDES for f in (*_OHLC, "volume")),
)

DEFAULT_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S%z"  # e.g. "2024-01-01 22:00:12+00:00"

# A gap only counts as a "weekend" gap if it is also at least this long — the
# real FX weekend close is ~48h, so this rules out a tiny Friday-evening gap
# that happens to sit next to a stray Saturday tick being mislabelled.
WEEKEND_MIN_SECONDS = 12 * 3600


class DataQualityError(Exception):
    """Raised when 1s data fails a hard sanity check (spec §0.5)."""


# --------------------------------------------------------------------------- #
# check expressions — the single definition of "valid data" (spec §0.5).
# engine.py's construction-time re-check should import these, not re-implement.
# --------------------------------------------------------------------------- #

def ohlc_violation_expr(side: str) -> pl.Expr:
    """True where a bar's OHLC is internally inconsistent for `side`.

    high must be >= max(open, close, low) and low <= min(open, close, high).
    Those two together also imply high >= low, so no separate check is needed.
    """
    o = pl.col(f"{side}_open")
    h = pl.col(f"{side}_high")
    l = pl.col(f"{side}_low")
    c = pl.col(f"{side}_close")
    return (h < pl.max_horizontal(o, c, l)) | (l > pl.min_horizontal(o, c, h))


def negative_spread_expr() -> pl.Expr:
    """True where ask < bid on any of O/H/L/C.

    `ask(t) >= bid(t)` holds pointwise for an uncrossed book, so it must hold for
    every aggregate of the tick stream: open/close (same instant) trivially, and
    high/low because min/max of a pointwise-larger series stays larger.
    """
    return pl.any_horizontal(pl.col(f"ask_{f}") < pl.col(f"bid_{f}") for f in _OHLC)


# --------------------------------------------------------------------------- #
# holiday calendar — computed per year, not hardcoded
# --------------------------------------------------------------------------- #

def easter_sunday(year: int) -> date:
    """Gregorian Easter Sunday for `year` (anonymous computus). Good Friday is
    two days earlier."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    month = (h + m - 7 * n + 114) // 31
    day = ((h + m - 7 * n + 114) % 31) + 1
    return date(year, month, day)


def fx_holidays(years: int | Iterable[int]) -> frozenset[date]:
    """UTC calendar dates on which EURUSD tick data typically shows a multi-hour
    *weekday* gap: New Year's Day, Good Friday, and the Christmas / New Year's
    Eve stretch. Works for any year — Good Friday is derived from `easter_sunday`.

    The FX market is otherwise 24/5 and merely thins (rather than closing) for
    national holidays, so this list is intentionally short. Pass an explicit set
    to `analyze_gaps` / `FxData` to override.
    """
    if isinstance(years, int):
        years = (years,)
    out: set[date] = set()
    for y in years:
        out |= {
            date(y, 1, 1),                             # New Year's Day
            easter_sunday(y) - timedelta(days=2),      # Good Friday
            date(y, 12, 24),                           # Christmas Eve (early close)
            date(y, 12, 25),                           # Christmas Day
            date(y, 12, 26),                           # Boxing Day
            date(y, 12, 31),                           # New Year's Eve (early close)
        }
    return frozenset(out)


def _holidays_for_span(df: pl.DataFrame) -> frozenset[date]:
    years = df.select(
        lo=pl.col("timestamp").dt.year().min(),
        hi=pl.col("timestamp").dt.year().max(),
    ).row(0)
    return fx_holidays(range(int(years[0]), int(years[1]) + 1))


# --------------------------------------------------------------------------- #
# step 1 — load
# --------------------------------------------------------------------------- #

def _require_columns(names: Iterable[str], src: str) -> None:
    missing = [c for c in EXPECTED_COLUMNS if c not in set(names)]
    if missing:
        raise DataQualityError(f"{src}: missing expected column(s): {missing}")


def read_1s_csv(
    path: str | Path,
    *,
    timestamp_format: str = DEFAULT_TIMESTAMP_FORMAT,
) -> pl.DataFrame:
    """Scan the CSV, verify the schema, parse the timestamp. One full read.

    Returns the raw frame — NOT deduplicated or sorted (see `normalize_1s`).
    `%z` in the format reads the UTC offset, so `timestamp` lands tz-aware UTC.
    """
    src = str(path)
    lf = pl.scan_csv(src)
    _require_columns(lf.collect_schema().names(), src)
    try:
        return lf.with_columns(
            pl.col("timestamp").str.to_datetime(timestamp_format)
        ).collect()
    except pl.exceptions.PolarsError as e:  # parse failure, bad file, ...
        raise DataQualityError(f"{src}: failed to load/parse — {e}") from e


def _ensure_parsed_timestamp(
    df: pl.DataFrame,
    timestamp_format: str = DEFAULT_TIMESTAMP_FORMAT,
) -> pl.DataFrame:
    """Parse `timestamp` if it's still a string; leave it alone if already datetime."""
    if "timestamp" not in df.columns or df.schema["timestamp"] != pl.String:
        return df
    try:
        return df.with_columns(pl.col("timestamp").str.to_datetime(timestamp_format))
    except pl.exceptions.PolarsError as e:
        raise DataQualityError(f"failed to parse timestamp column — {e}") from e


# --------------------------------------------------------------------------- #
# step 2 — normalize
# --------------------------------------------------------------------------- #

def normalize_1s(df: pl.DataFrame) -> tuple[pl.DataFrame, int]:
    """Drop fully-identical rows, then sort by timestamp.

    The month-by-month download overlaps one bar at each month boundary, so the
    00:00:00 bar on the 1st can appear twice, byte-for-byte. Collapsing those is
    lossless. Rows that share only a *timestamp* but differ in value are left
    for `validate_1s` to reject.

    Returns (clean_df, n_exact_duplicate_rows_dropped).
    """
    n_before = df.height
    out = df.unique(keep="first", maintain_order=True).sort("timestamp")
    return out, n_before - out.height


# --------------------------------------------------------------------------- #
# step 3 — validate (hard checks, spec §0.5 — vectorized, single pass)
# --------------------------------------------------------------------------- #

def validate_1s(df: pl.DataFrame) -> None:
    """Hard sanity checks on an in-memory 1s bid/ask frame.

    Raises `DataQualityError` on: missing columns, null/unparsed timestamps,
    duplicate timestamps with conflicting values, nulls, NaNs, OHLC that isn't
    internally consistent (per side), or negative spread. Returns None if the
    data is good.

    This is the single source of truth for "is this a valid 1s frame" — the
    engine calls it at construction time (spec §2.1).
    """
    _require_columns(df.columns, "<frame>")

    float_cols = [c for c, t in df.schema.items() if t == pl.Float64]
    nan_expr = (
        pl.sum_horizontal(pl.col(c).is_nan().sum() for c in float_cols)
        if float_cols else pl.lit(0)
    )

    agg = df.select(
        n_rows=pl.len(),
        n_ts_unique=pl.col("timestamp").n_unique(),
        n_ts_null=pl.col("timestamp").null_count(),
        n_nulls=pl.sum_horizontal(pl.all().null_count()),
        n_nans=nan_expr,
        n_ohlc_bad=(ohlc_violation_expr("bid") | ohlc_violation_expr("ask")).sum(),
        n_spread_bad=negative_spread_expr().sum(),
    ).row(0, named=True)

    if agg["n_rows"] == 0:
        raise DataQualityError("frame has no rows")

    if agg["n_ts_null"]:
        raise DataQualityError(
            f"{agg['n_ts_null']} timestamp(s) are null / failed to parse"
        )

    if agg["n_ts_unique"] != agg["n_rows"]:
        _raise_duplicate_timestamps(df, agg["n_rows"] - agg["n_ts_unique"])

    if agg["n_nulls"]:
        raise DataQualityError(f"null values present: {_null_breakdown(df)}")

    if agg["n_nans"]:
        raise DataQualityError(f"NaN values present: {_nan_breakdown(df, float_cols)}")

    if agg["n_ohlc_bad"]:
        mask = ohlc_violation_expr("bid") | ohlc_violation_expr("ask")
        raise DataQualityError(
            f"{agg['n_ohlc_bad']} bar(s) violate OHLC consistency "
            f"(high < max(o,c,l) or low > min(o,c,h)). "
            f"First: {_first_offenders(df, mask)}"
        )

    if agg["n_spread_bad"]:
        raise DataQualityError(
            f"{agg['n_spread_bad']} bar(s) have ask < bid (negative spread). "
            f"First: {_first_offenders(df, negative_spread_expr())}"
        )


# -- detailed error helpers (only run on the failure path) ------------------- #

def _raise_duplicate_timestamps(df: pl.DataFrame, n: int) -> None:
    dup = (
        df.filter(pl.col("timestamp").is_duplicated())
          .select("timestamp").unique().sort("timestamp")
          .head(5)["timestamp"].to_list()
    )
    raise DataQualityError(
        f"{n} row(s) share a timestamp with conflicting values "
        f"(exact-duplicate rows are dropped first). Affected: {dup}"
    )


def _null_breakdown(df: pl.DataFrame) -> dict:
    nc = df.null_count()
    return {c: nc[c].item() for c in nc.columns if nc[c].item()}


def _nan_breakdown(df: pl.DataFrame, float_cols: list[str]) -> dict:
    if not float_cols:
        return {}
    counts = df.select(pl.col(c).is_nan().sum().alias(c) for c in float_cols)
    return {c: counts[c].item() for c in float_cols if counts[c].item()}


def _first_offenders(df: pl.DataFrame, mask: pl.Expr, n: int = 3) -> list:
    return df.filter(mask).select("timestamp").head(n)["timestamp"].to_list()


# --------------------------------------------------------------------------- #
# gap analysis — weekends expected, holidays expected, anything else is flagged
# --------------------------------------------------------------------------- #

def analyze_gaps(
    df: pl.DataFrame,
    *,
    holidays: Iterable[date] | None = None,
    report_threshold_s: int = 600,
    weekend_min_s: int = WEEKEND_MIN_SECONDS,
) -> tuple[dict, pl.DataFrame]:
    """Classify the gap between every pair of consecutive bars.

    kind:
      weekend      — starts Friday, ends Sat/Sun, and lasts > `weekend_min_s`
      holiday      — either endpoint falls on a `holidays` date
      unexplained  — anything else

    `holidays` defaults to `fx_holidays()` computed for every year the data spans.
    Pass an explicit iterable of `date` to override.

    Returns (summary, gaps). `gaps` holds every weekend gap plus every gap
    >= `report_threshold_s`, longest first. `summary` always reports the single
    largest *unexplained* gap and when it started — even if it's below the
    threshold — so a sub-threshold hole is never silently hidden behind a "0".

    Expects `df` already sorted by timestamp.
    """
    hol = list(holidays) if holidays is not None else list(_holidays_for_span(df))

    g = (
        df.select(start=pl.col("timestamp").shift(1), end=pl.col("timestamp"))
          .drop_nulls()
          .with_columns(
              gap_s=(pl.col("end") - pl.col("start")).dt.total_seconds(),
              start_dow=pl.col("start").dt.weekday(),  # Mon=1 .. Sun=7
          )
          .with_columns(
              kind=pl.when(
                       (pl.col("start_dow") == 5)
                       & pl.col("end").dt.weekday().is_in([6, 7])
                       & (pl.col("gap_s") > weekend_min_s)
                   ).then(pl.lit("weekend"))
                   .when(
                       pl.col("start").dt.date().is_in(hol)
                       | pl.col("end").dt.date().is_in(hol)
                   ).then(pl.lit("holiday"))
                   .otherwise(pl.lit("unexplained"))
          )
    )

    over_thr = pl.col("gap_s") >= report_threshold_s
    gaps = (
        g.filter(over_thr | (pl.col("kind") == "weekend"))
         .with_columns(gap_h=(pl.col("gap_s") / 3600).round(2))
         .select("start", "end", "gap_s", "gap_h", "kind", "start_dow")
         .sort("gap_s", descending=True)
    )

    ux = g.filter(pl.col("kind") == "unexplained").sort("gap_s", descending=True)
    max_ux = ux.row(0, named=True) if ux.height else None

    summary = {
        "n_bars": df.height,
        "span_start": df["timestamp"].min() if df.height else None,
        "span_end": df["timestamp"].max() if df.height else None,
        "median_gap_s": g["gap_s"].median() if g.height else None,
        "p99_gap_s": g["gap_s"].quantile(0.99) if g.height else None,
        "n_weekend_gaps": int((g["kind"] == "weekend").sum()),
        "n_holiday_gaps": int(g.filter((pl.col("kind") == "holiday") & over_thr).height),
        "n_unexplained_gaps": int(g.filter((pl.col("kind") == "unexplained") & over_thr).height),
        "max_unexplained_gap_s": max_ux["gap_s"] if max_ux else None,
        "max_unexplained_gap_start": max_ux["start"] if max_ux else None,
    }
    return summary, gaps


# --------------------------------------------------------------------------- #
# FxData — orchestrates load + normalize + validate + gap report
# --------------------------------------------------------------------------- #

class FxData:
    """Load + validate 1s EURUSD bid/ask data, from a CSV path or an in-memory frame.

    Constructing the object *is* the check: it raises `DataQualityError` on any
    hard failure. If it returns, the data is good.

    Gaps between consecutive bars are classified (weekend / holiday /
    unexplained). Unexplained gaps at or above `gap_report_threshold_s` are a
    warning by default; pass `strict_gaps=True` to make them raise. The report
    always states the single largest weekday gap regardless of threshold.

    Attributes
    ----------
    df : pl.DataFrame
        Cleaned data, sorted by timestamp (`timestamp` = `Datetime[us, UTC]`).
    gaps : pl.DataFrame
        One row per reported gap: start, end, gap_s, gap_h, kind, start_dow.
    unexplained_gaps : pl.DataFrame
        `.gaps` filtered to kind == "unexplained".
    gap_summary : dict
        Span, median/p99 inter-bar gap, gap counts by kind, largest weekday gap.
    n_exact_duplicate_rows_dropped : int
        Fully-identical rows removed before validation (month-boundary artifact).
    """

    def __init__(
        self,
        source: str | Path | pl.DataFrame | pl.LazyFrame,
        *,
        timestamp_format: str = DEFAULT_TIMESTAMP_FORMAT,
        holidays: Iterable[date] | None = None,
        gap_report_threshold_s: int = 600,
        strict_gaps: bool = False,
        verbose: bool = True,
    ) -> None:
        self.timestamp_format = timestamp_format
        self._holidays_override = frozenset(holidays) if holidays is not None else None
        self.gap_report_threshold_s = int(gap_report_threshold_s)

        if isinstance(source, (str, Path)):
            self.source = str(source)
            if not Path(source).is_file():
                raise FileNotFoundError(source)
            df = read_1s_csv(source, timestamp_format=timestamp_format)
        elif isinstance(source, pl.LazyFrame):
            self.source = "<LazyFrame>"
            df = _ensure_parsed_timestamp(source.collect(), timestamp_format)
        elif isinstance(source, pl.DataFrame):
            self.source = "<DataFrame>"
            df = _ensure_parsed_timestamp(source, timestamp_format)
        else:
            raise TypeError(
                f"source must be a path, pl.DataFrame or pl.LazyFrame, got {type(source)!r}"
            )

        df, self.n_exact_duplicate_rows_dropped = normalize_1s(df)
        validate_1s(df)
        self.df: pl.DataFrame = df

        self.holidays: frozenset[date] = (
            self._holidays_override
            if self._holidays_override is not None
            else _holidays_for_span(df)
        )
        self.gap_summary, self.gaps = analyze_gaps(
            df,
            holidays=self.holidays,
            report_threshold_s=self.gap_report_threshold_s,
        )

        n_ux = self.gap_summary["n_unexplained_gaps"]
        if n_ux and strict_gaps:
            raise DataQualityError(
                f"{n_ux} unexplained gap(s) >= {self.gap_report_threshold_s}s "
                f"(strict_gaps=True):\n{self.unexplained_gaps}"
            )

        if verbose:
            self.print_report()

    @property
    def unexplained_gaps(self) -> pl.DataFrame:
        return self.gaps.filter(pl.col("kind") == "unexplained")

    def print_report(self) -> None:
        s = self.gap_summary
        thr = self.gap_report_threshold_s
        span = (
            f"{s['span_start']:%Y-%m-%d %H:%M} -> {s['span_end']:%Y-%m-%d %H:%M} UTC"
            if s["span_start"] is not None else "(empty)"
        )
        print(f"FxData: {self.source}")
        print(f"  bars ................. {s['n_bars']:,}")
        print(f"  span ................. {span}")
        if self.n_exact_duplicate_rows_dropped:
            print(f"  exact dup rows dropped {self.n_exact_duplicate_rows_dropped}")
        if s["median_gap_s"] is not None:
            print(
                f"  inter-bar gap ........ median {s['median_gap_s']:.0f}s  "
                f"p99 {s['p99_gap_s']:.0f}s"
            )
        print(f"  weekend gaps ......... {s['n_weekend_gaps']}")
        print(f"  holiday gaps ......... {s['n_holiday_gaps']}")

        n_ux = s["n_unexplained_gaps"]
        if n_ux:
            print(f"  unexplained gaps .... {n_ux}  (>= {thr}s)   << review")
            with pl.Config(tbl_rows=20, tbl_width_chars=200):
                print(self.unexplained_gaps)
        else:
            print(f"  unexplained gaps .... 0  (>= {thr}s)")

        mx, mx_at = s["max_unexplained_gap_s"], s["max_unexplained_gap_start"]
        if mx is not None:
            print(
                f"  largest unexpl. gap . {mx:.0f}s ({mx / 60:.1f} min) "
                f"at {mx_at:%Y-%m-%d %H:%M} UTC"
            )

        print("  checks .............. PASSED")

    def __repr__(self) -> str:
        s = self.gap_summary
        span = (
            f"{s['span_start']:%Y-%m-%d} -> {s['span_end']:%Y-%m-%d}"
            if s["span_start"] is not None else "empty"
        )
        return (
            f"<FxData {self.source!r} | {s['n_bars']:,} bars | {span} | "
            f"{s['n_unexplained_gaps']} unexplained gaps>"
        )


def load_1s_data(
    source: str | Path | pl.DataFrame | pl.LazyFrame,
    **kwargs,
) -> pl.DataFrame:
    """Spec §1 entry point, adapted to the single-file schema.

    `source` is a CSV path, or an already-loaded `pl.DataFrame` / `pl.LazyFrame`.
    Returns the cleaned, validated 1s frame. Raises `DataQualityError` on
    duplicate timestamps, nulls, broken OHLC or negative spread. Use `FxData`
    directly when you also want the gap report.
    """
    return FxData(source, **kwargs).df


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "data/EURUSD_1s_2024.csv"
    data = FxData(path)
    print()
    print(data)
