"""Data layer for the FX backtester (spec §1).

Loads the 1-second EURUSD bid/ask CSV, runs the sanity checks from spec §0.5 at
1s resolution as vectorized polars expressions, and hands back a cleaned frame.

The real file on disk is a *single* CSV with bid and ask OHLCV side by side
(`timestamp, bid_open, ..., bid_volume, ask_open, ..., ask_volume`), not the two
separate ask/bid files the spec originally assumed. `FxData` is built around the
actual schema.

Usage
-----
    from lib.data import FxData

    data = FxData("data/EURUSD_1s_2024.csv")   # raises if anything fails
    df = data.df                               # cleaned pl.DataFrame

or from the command line:

    python lib/data.py data/EURUSD_1s_2024.csv
"""

from __future__ import annotations

from datetime import date
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

# UTC calendar dates on which a multi-hour *weekday* gap in EURUSD data is
# expected rather than suspicious. 2024 FX holidays (Christmas / New Year /
# Good Friday). Extend/replace via the `holidays=` constructor arg for other
# years.
DEFAULT_HOLIDAYS = frozenset({
    date(2024, 1, 1),    # New Year's Day
    date(2024, 3, 29),   # Good Friday
    date(2024, 12, 24),  # Christmas Eve (half day)
    date(2024, 12, 25),  # Christmas Day
    date(2024, 12, 26),  # Boxing Day
    date(2024, 12, 31),  # New Year's Eve (half day)
})

DEFAULT_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S%z"  # e.g. "2024-01-01 22:00:12+00:00"


class DataQualityError(Exception):
    """Raised when loaded data fails a hard sanity check (spec §0.5)."""


# --------------------------------------------------------------------------- #
# check expressions (vectorized — no row-wise Python, spec §1)
# --------------------------------------------------------------------------- #

def _ohlc_violation_expr(side: str) -> pl.Expr:
    """True where a bar's OHLC is internally inconsistent for `side`.

    high must be >= max(open, close, low) and low <= min(open, close, high).
    Those two together also imply high >= low, so no separate check is needed.
    """
    o = pl.col(f"{side}_open")
    h = pl.col(f"{side}_high")
    l = pl.col(f"{side}_low")
    c = pl.col(f"{side}_close")
    return (h < pl.max_horizontal(o, c, l)) | (l > pl.min_horizontal(o, c, h))


def _negative_spread_expr() -> pl.Expr:
    """True where ask < bid on any of O/H/L/C.

    `ask(t) >= bid(t)` holds pointwise for an uncrossed book, so it must hold for
    every aggregate of the tick stream: open/close (same instant) trivially, and
    high/low because min/max of a pointwise-larger series stays larger.
    """
    return pl.any_horizontal(
        pl.col(f"ask_{f}") < pl.col(f"bid_{f}") for f in _OHLC
    )


# --------------------------------------------------------------------------- #
# main entry point
# --------------------------------------------------------------------------- #

class FxData:
    """Load + validate the 1s EURUSD bid/ask CSV.

    Constructing the object *is* the check: it raises `DataQualityError` on any
    hard failure (bad schema, unparseable timestamps, conflicting duplicate
    timestamps, nulls, NaNs, broken OHLC, negative spread). If it returns, the
    data is good.

    Gaps between consecutive bars are classified (weekend / holiday /
    unexplained). Unexplained gaps above `gap_report_threshold_s` are a warning
    by default; pass `strict_gaps=True` to make them raise instead.

    Attributes
    ----------
    df : pl.DataFrame
        Cleaned data, sorted by timestamp, `timestamp` as `Datetime[us, UTC]`.
    gaps : pl.DataFrame
        One row per reported gap: start, end, gap_s, gap_h, kind, start_dow.
    gap_summary : dict
        Headline gap/span stats.
    n_exact_duplicate_rows_dropped : int
        Fully-identical rows removed before validation (the month-boundary
        artifact from the download script — see the notebook).
    """

    def __init__(
        self,
        csv_path: str | Path,
        *,
        timestamp_format: str = DEFAULT_TIMESTAMP_FORMAT,
        holidays: Iterable[date] | None = None,
        gap_report_threshold_s: int = 600,
        strict_gaps: bool = False,
        verbose: bool = True,
    ) -> None:
        self.csv_path = str(csv_path)
        self.timestamp_format = timestamp_format
        self.holidays = frozenset(holidays) if holidays is not None else DEFAULT_HOLIDAYS
        self.gap_report_threshold_s = int(gap_report_threshold_s)

        if not Path(self.csv_path).is_file():
            raise FileNotFoundError(self.csv_path)

        lf = self._scan_and_parse()
        lf, self.n_exact_duplicate_rows_dropped = self._drop_exact_duplicates(lf)

        self._run_hard_checks(lf)

        self.df: pl.DataFrame = lf.sort("timestamp").collect()
        self.gap_summary, self.gaps = self._analyze_gaps()

        n_unexplained = self.gap_summary["n_unexplained_gaps"]
        if n_unexplained and strict_gaps:
            raise DataQualityError(
                f"{n_unexplained} unexplained gap(s) >= {self.gap_report_threshold_s}s "
                f"(strict_gaps=True):\n{self.unexplained_gaps}"
            )

        if verbose:
            self.print_report()

    # ------------------------------------------------------------------ #
    # loading
    # ------------------------------------------------------------------ #

    def _scan_and_parse(self) -> pl.LazyFrame:
        raw = pl.scan_csv(self.csv_path)

        names = raw.collect_schema().names()
        missing = [c for c in EXPECTED_COLUMNS if c not in names]
        if missing:
            raise DataQualityError(
                f"{self.csv_path}: missing expected column(s): {missing}\n"
                f"got: {names}"
            )

        return raw.with_columns(
            # explicit format (fast, and won't silently fall back to str on a
            # parse failure the way inference can). `%z` reads the +00:00 offset,
            # so the result is tz-aware UTC.
            pl.col("timestamp").str.to_datetime(self.timestamp_format)
        )

    def _drop_exact_duplicates(self, lf: pl.LazyFrame) -> tuple[pl.LazyFrame, int]:
        """Remove fully-identical rows (all 11 columns equal).

        The month-by-month download overlaps by one bar at each month boundary,
        so the 00:00:00 bar on the 1st appears twice, byte-for-byte. Those are
        safe to collapse. Rows that share only a *timestamp* but differ in the
        OHLCV values are NOT touched here — `_check_duplicate_timestamps` treats
        those as a hard error.
        """
        n_before = lf.select(pl.len()).collect().item()
        deduped = lf.unique(keep="first", maintain_order=True)
        n_after = deduped.select(pl.len()).collect().item()
        return deduped, n_before - n_after

    # ------------------------------------------------------------------ #
    # hard checks — single vectorized pass, spec §0.5 / §1
    # ------------------------------------------------------------------ #

    def _run_hard_checks(self, lf: pl.LazyFrame) -> None:
        try:
            agg = lf.select(
                n_rows=pl.len(),
                n_ts_unique=pl.col("timestamp").n_unique(),
                n_ts_null=pl.col("timestamp").null_count(),
                n_nulls=pl.sum_horizontal(pl.all().null_count()),
                n_nans=pl.sum_horizontal(pl.col(pl.Float64).is_nan().sum()),
                n_ohlc_bad=(
                    _ohlc_violation_expr("bid") | _ohlc_violation_expr("ask")
                ).sum(),
                n_spread_bad=_negative_spread_expr().sum(),
            ).collect()
        except pl.exceptions.ComputeError as e:  # e.g. timestamp parse failure
            raise DataQualityError(f"{self.csv_path}: failed to load/parse — {e}") from e

        row = agg.row(0, named=True)

        if row["n_rows"] == 0:
            raise DataQualityError(f"{self.csv_path}: no rows")

        if row["n_ts_null"]:
            raise DataQualityError(
                f"{row['n_ts_null']} timestamp(s) failed to parse with "
                f"format {self.timestamp_format!r}"
            )

        if row["n_ts_unique"] != row["n_rows"]:
            self._raise_duplicate_timestamps(lf, row["n_rows"] - row["n_ts_unique"])

        if row["n_nulls"]:
            raise DataQualityError(f"null values present: {self._null_breakdown(lf)}")

        if row["n_nans"]:
            raise DataQualityError(f"NaN values present: {self._nan_breakdown(lf)}")

        if row["n_ohlc_bad"]:
            raise DataQualityError(
                f"{row['n_ohlc_bad']} bar(s) violate OHLC consistency "
                f"(high < max(o,c,l) or low > min(o,c,h)). "
                f"First: {self._first_offenders(lf, _ohlc_violation_expr('bid') | _ohlc_violation_expr('ask'))}"
            )

        if row["n_spread_bad"]:
            raise DataQualityError(
                f"{row['n_spread_bad']} bar(s) have ask < bid (negative spread). "
                f"First: {self._first_offenders(lf, _negative_spread_expr())}"
            )

    # -- detailed error helpers (only run on the failure path) ---------- #

    def _raise_duplicate_timestamps(self, lf: pl.LazyFrame, n: int) -> None:
        dup = (
            lf.filter(pl.col("timestamp").is_duplicated())
              .select("timestamp")
              .unique()
              .sort("timestamp")
              .head(5)
              .collect()["timestamp"]
              .to_list()
        )
        raise DataQualityError(
            f"{n} row(s) share a timestamp with conflicting values "
            f"(exact-duplicate rows were already dropped). Affected: {dup}"
        )

    def _null_breakdown(self, lf: pl.LazyFrame) -> dict:
        nc = lf.null_count().collect()
        return {c: nc[c].item() for c in nc.columns if nc[c].item()}

    def _nan_breakdown(self, lf: pl.LazyFrame) -> dict:
        floats = [c for c, t in lf.collect_schema().items() if t == pl.Float64]
        counts = lf.select(pl.col(c).is_nan().sum().alias(c) for c in floats).collect()
        return {c: counts[c].item() for c in floats if counts[c].item()}

    def _first_offenders(self, lf: pl.LazyFrame, mask: pl.Expr, n: int = 3) -> list:
        return (
            lf.filter(mask).select("timestamp").head(n).collect()["timestamp"].to_list()
        )

    # ------------------------------------------------------------------ #
    # gap analysis — weekends expected, holidays expected, rest is a flag
    # ------------------------------------------------------------------ #

    def _analyze_gaps(self) -> tuple[dict, pl.DataFrame]:
        g = (
            self.df.lazy()
            .select(start=pl.col("timestamp").shift(1), end=pl.col("timestamp"))
            .drop_nulls()
            .with_columns(
                gap_s=(pl.col("end") - pl.col("start")).dt.total_seconds(),
                start_dow=pl.col("start").dt.weekday(),  # Mon=1 .. Sun=7
            )
            .collect()
        )

        hol = list(self.holidays)
        is_weekend = (pl.col("start_dow") == 5) & pl.col("end").dt.weekday().is_in([6, 7])
        is_holiday = (
            pl.col("start").dt.date().is_in(hol) | pl.col("end").dt.date().is_in(hol)
        )
        g = g.with_columns(
            kind=pl.when(is_weekend).then(pl.lit("weekend"))
                  .when(is_holiday).then(pl.lit("holiday"))
                  .otherwise(pl.lit("unexplained"))
        )

        thr = self.gap_report_threshold_s
        gaps = (
            g.filter((pl.col("gap_s") >= thr) | (pl.col("kind") == "weekend"))
             .with_columns(gap_h=(pl.col("gap_s") / 3600).round(2))
             .select("start", "end", "gap_s", "gap_h", "kind", "start_dow")
             .sort("gap_s", descending=True)
        )

        over_thr = pl.col("gap_s") >= thr
        summary = {
            "n_bars": self.df.height,
            "span_start": self.df["timestamp"].min(),
            "span_end": self.df["timestamp"].max(),
            "median_gap_s": g["gap_s"].median(),
            "p99_gap_s": g["gap_s"].quantile(0.99),
            "max_unexplained_gap_s": g.filter(pl.col("kind") == "unexplained")["gap_s"].max(),
            "n_weekend_gaps": int((g["kind"] == "weekend").sum()),
            "n_holiday_gaps": g.filter((pl.col("kind") == "holiday") & over_thr).height,
            "n_unexplained_gaps": g.filter((pl.col("kind") == "unexplained") & over_thr).height,
        }
        return summary, gaps

    # ------------------------------------------------------------------ #
    # convenience
    # ------------------------------------------------------------------ #

    @property
    def unexplained_gaps(self) -> pl.DataFrame:
        return self.gaps.filter(pl.col("kind") == "unexplained")

    def print_report(self) -> None:
        s = self.gap_summary
        span = f"{s['span_start']:%Y-%m-%d %H:%M} -> {s['span_end']:%Y-%m-%d %H:%M} UTC"
        print(f"FxData: {self.csv_path}")
        print(f"  bars ................. {s['n_bars']:,}")
        print(f"  span ................. {span}")
        if self.n_exact_duplicate_rows_dropped:
            print(f"  exact dup rows dropped {self.n_exact_duplicate_rows_dropped}")
        print(f"  inter-bar gap ........ median {s['median_gap_s']:.0f}s  p99 {s['p99_gap_s']:.0f}s")
        print(f"  weekend gaps ......... {s['n_weekend_gaps']}")
        print(f"  holiday gaps ......... {s['n_holiday_gaps']}")
        n_ux = s["n_unexplained_gaps"]
        if n_ux:
            print(f"  UNEXPLAINED gaps ..... {n_ux}  (>= {self.gap_report_threshold_s}s)  << review")
            with pl.Config(tbl_rows=20, tbl_width_chars=200):
                print(self.unexplained_gaps)
        else:
            print(f"  unexplained gaps ..... 0")
        print("  checks .............. PASSED")

    def __repr__(self) -> str:
        s = self.gap_summary
        return (
            f"<FxData {self.csv_path!r} | {s['n_bars']:,} bars | "
            f"{s['span_start']:%Y-%m-%d} -> {s['span_end']:%Y-%m-%d} | "
            f"{s['n_unexplained_gaps']} unexplained gaps>"
        )


def load_1s_data(csv_path: str | Path, **kwargs) -> pl.DataFrame:
    """Spec §1 `load_1s_data`, adapted to the single-file schema.

    Loads, sanity-checks, and returns the cleaned 1s bid/ask frame. Raises
    `DataQualityError` on duplicate timestamps, nulls, broken OHLC or negative
    spread. For the gap report and other metadata, use `FxData` directly.
    """
    return FxData(csv_path, **kwargs).df


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "data/EURUSD_1s_2024.csv"
    data = FxData(path)
    print()
    print(data)
