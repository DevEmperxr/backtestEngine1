"""005 — Opening-range breakout: 07:00-08:30 New York range, first 1m close
beyond it after 08:30 NY (until 16:00 London), SL at the opposite side, TP =
1.5 x range, flat at 16:00 London.

See research/runs/005_orb_ny_prenews/summary.md for the pre-registered
hypothesis and rules.
"""

from __future__ import annotations

from datetime import date, time

import polars as pl

from lib.data import PIP
from lib.engine import Strategy
from lib.signals import session_window

NY, LONDON = "America/New_York", "Europe/London"
RANGE_START, RANGE_END = time(7, 0), time(8, 30)   # NY
WINDOW_END = time(16, 0)                            # London

# BLS 2024 release dates, 08:30 ET (bls.gov/schedule/2024): reporting split only.
NFP_2024 = [date(2024, m, d) for m, d in [(1, 5), (2, 2), (3, 8), (4, 5), (5, 3), (6, 7),
                                           (7, 5), (8, 2), (9, 6), (10, 4), (11, 1), (12, 6)]]
CPI_2024 = [date(2024, m, d) for m, d in [(1, 11), (2, 13), (3, 12), (4, 10), (5, 15), (6, 12),
                                           (7, 11), (8, 14), (9, 11), (10, 10), (11, 13), (12, 11)]]
NEWS_DATES = sorted(NFP_2024 + CPI_2024)


class OrbStrategy(Strategy):
    line_columns = ["range_hi", "range_lo"]
    marker_columns = ["long_signal", "short_signal"]
    region_columns = ["in_window"]

    exit_on_opposite_signal = False
    reverse_on_opposite_signal = False

    def __init__(
        self, *, range_start: time = RANGE_START, range_end: time = RANGE_END,
        tp_range_mult: float = 1.5, timeframe: str = "1m", force_flat: bool = True,
    ) -> None:
        # sl/tp are per trade (columns); the ctor values are only chart fallbacks
        super().__init__(10.0, 15.0, timeframe)
        self.range_start, self.range_end = range_start, range_end
        self.tp_range_mult = tp_range_mult
        self.force_flat = force_flat
        self.range_bars = int((range_end.hour * 60 + range_end.minute)
                              - (range_start.hour * 60 + range_start.minute))

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        mid = lambda f: (pl.col(f"bid_{f}") + pl.col(f"ask_{f}")) / 2
        start_ny = pl.col("timestamp").dt.convert_time_zone(NY)
        close_ny = pl.col("close_time").dt.convert_time_zone(NY)
        out = df.with_columns(
            mid_close=mid("close"), mid_high=mid("high"), mid_low=mid("low"),
            ny_date=start_ny.dt.date(),
            in_range=(start_ny.dt.time() >= self.range_start) & (close_ny.dt.time() <= self.range_end)
                     & (close_ny.dt.date() == start_ny.dt.date()),
            # entry happens at close_time; strictly after the range has closed
            in_window=session_window(pl.col("close_time"), NY, self.range_end, LONDON, WINDOW_END)
                      & (close_ny.dt.time() > self.range_end)
                      & (close_ny.dt.weekday() <= 5),
        )
        rng = out.filter("in_range").group_by("ny_date").agg(
            range_hi_d=pl.col("mid_high").max(),
            range_lo_d=pl.col("mid_low").min(),
            n_range_bars=pl.len(),
        ).filter(pl.col("n_range_bars") >= self.range_bars)
        out = out.join(rng, on="ny_date", how="left").with_columns(
            # The range is only known once its last bar has closed: hide it on
            # every bar that isn't strictly after 08:30 NY (no lookahead, not even
            # on the chart).
            range_hi=pl.when(pl.col("in_window")).then(pl.col("range_hi_d")),
            range_lo=pl.when(pl.col("in_window")).then(pl.col("range_lo_d")),
        )
        out = out.with_columns(
            brk_up=(pl.col("mid_close") > pl.col("range_hi")).fill_null(False),
            brk_dn=(pl.col("mid_close") < pl.col("range_lo")).fill_null(False),
        ).with_columns(
            n_brk=(pl.col("brk_up") | pl.col("brk_dn")).cast(pl.Int32).cum_sum().over("ny_date"),
        ).with_columns(
            first=(pl.col("brk_up") | pl.col("brk_dn")) & (pl.col("n_brk") == 1),
        ).with_columns(
            long_signal=pl.col("first") & pl.col("brk_up"),
            short_signal=pl.col("first") & pl.col("brk_dn"),
        ).with_columns(
            sl_pips=pl.when(pl.col("long_signal"))
                     .then((pl.col("mid_close") - pl.col("range_lo")) / PIP)
                     .when(pl.col("short_signal"))
                     .then((pl.col("range_hi") - pl.col("mid_close")) / PIP),
            tp_pips=pl.when(pl.col("first"))
                     .then((pl.col("range_hi") - pl.col("range_lo")) / PIP * self.tp_range_mult),
        )
        if self.force_flat:
            out = out.with_columns(exit_signal=~pl.col("in_window"))
        return out

    @staticmethod
    def report_splits(trades: pl.DataFrame) -> dict[str, pl.DataFrame]:
        d = trades["entry_time"].dt.convert_time_zone(NY).dt.date()
        news = d.is_in(NEWS_DATES)
        return {"news_nfp_cpi": trades.filter(news), "non_news": trades.filter(~news)}


def make() -> OrbStrategy:
    return OrbStrategy(range_start=time(7, 0), range_end=time(8, 30), tp_range_mult=1.5)
