"""084 — DAX-open reversal ideas from 083 (GER40, Frankfurt time), FTMO rules. Pip-aware (points).

    make_a()  fade the first 30 minutes: at 09:30 trade against 09:00->09:30; stop 5 pts beyond that half hour's
              extreme (min 10 pts); exit 17:25
    make_b()  first-hour false break: 10:00-12:00, first 1m bar that trades beyond the 09:00-10:00 high (low) and
              closes back inside -> short (long); stop 5 pts beyond the extreme since 10:00; one trade a day; exit 17:25

See research/runs/084_dax_open_reversal/summary.md.
"""

from __future__ import annotations

from datetime import time

import polars as pl

from lib.engine import Strategy
from research.regime.news import apply_news_blackout

FRA = "Europe/Berlin"
BUF, MIN_STOP, NO_TP = 5.0, 10.0, 5000.0
EXIT = time(17, 25)


class DaxOpenReversal(Strategy):
    exit_on_opposite_signal = False
    reverse_on_opposite_signal = False
    pip_aware = True
    marker_columns = ["long_signal", "short_signal"]
    region_columns = ["in_window"]

    def __init__(self, variant: str, *, currencies: tuple[str, ...] = ("EUR",)) -> None:
        super().__init__(100.0, NO_TP, "1m")
        if variant not in ("a", "b"):
            raise ValueError(variant)
        self.variant, self.currencies = variant, tuple(currencies)

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        mid = lambda f: (pl.col(f"bid_{f}") + pl.col(f"ask_{f}")) / 2
        st = pl.col("timestamp").dt.convert_time_zone(FRA).dt.time()      # bar START (Frankfurt)
        ct = pl.col("close_time").dt.convert_time_zone(FRA)
        out = df.with_columns(mo=mid("open"), mh=mid("high"), ml=mid("low"), mc=mid("close"),
                              day=ct.dt.date(), clock=ct.dt.time(), start=st, wd=ct.dt.weekday())
        wk = pl.col("wd") <= 5
        if self.variant == "a":
            first = out.filter((pl.col("start") >= time(9, 0)) & (pl.col("start") < time(9, 30)))
            agg = first.group_by("day").agg(o930=pl.col("mo").first(), hi=pl.col("mh").max(), lo=pl.col("ml").min(),
                                            n=pl.len(), s0=pl.col("start").min())
            agg = agg.filter((pl.col("n") >= 25) & (pl.col("s0") == time(9, 0)))
            out = out.join(agg.select("day", "o930", "hi", "lo"), on="day", how="left")
            at = (pl.col("clock") == time(9, 30)) & wk & pl.col("o930").is_not_null()
            short = at & (pl.col("mc") > pl.col("o930"))
            long_ = at & (pl.col("mc") < pl.col("o930"))
            sl_s = pl.max_horizontal(pl.col("hi") - pl.col("mc") + BUF, pl.lit(MIN_STOP))
            sl_l = pl.max_horizontal(pl.col("mc") - pl.col("lo") + BUF, pl.lit(MIN_STOP))
            win_start = time(9, 30)
        else:
            first = out.filter((pl.col("start") >= time(9, 0)) & (pl.col("start") < time(10, 0)))
            agg = first.group_by("day").agg(hi=pl.col("mh").max(), lo=pl.col("ml").min(), n=pl.len(),
                                            s0=pl.col("start").min())
            agg = agg.filter((pl.col("n") >= 50) & (pl.col("s0") == time(9, 0)))
            out = out.join(agg.select("day", "hi", "lo"), on="day", how="left")
            after = (pl.col("start") >= time(10, 0)) & (pl.col("clock") <= time(12, 0)) & wk & pl.col("hi").is_not_null()
            runhi = pl.when(after).then(pl.col("mh")).cum_max().over("day")
            runlo = pl.when(after).then(pl.col("ml")).cum_min().over("day")
            out = out.with_columns(runhi=runhi, runlo=runlo)
            short = after & (pl.col("mh") > pl.col("hi")) & (pl.col("mc") < pl.col("hi"))
            long_ = after & (pl.col("ml") < pl.col("lo")) & (pl.col("mc") > pl.col("lo"))
            sl_s = pl.max_horizontal(pl.col("runhi") - pl.col("mc") + BUF, pl.lit(MIN_STOP))
            sl_l = pl.max_horizontal(pl.col("mc") - pl.col("runlo") + BUF, pl.lit(MIN_STOP))
            win_start = time(10, 1)
        out = out.with_columns(short=(short & ~long_).fill_null(False), long=(long_ & ~short).fill_null(False))
        first_sig = (pl.col("short") | pl.col("long")).cast(pl.Int32).cum_sum().over("day") == 1
        out = out.with_columns(short_signal=pl.col("short") & first_sig, long_signal=pl.col("long") & first_sig)
        sig = pl.col("short_signal") | pl.col("long_signal")
        out = out.with_columns(
            sl_pips=pl.when(pl.col("short_signal")).then(sl_s).when(pl.col("long_signal")).then(sl_l),
            tp_pips=pl.when(sig).then(pl.lit(NO_TP)),
            in_window=((pl.col("clock") >= win_start) & (pl.col("clock") < EXIT) & wk).fill_null(False),
        ).with_columns(exit_signal=~pl.col("in_window") & ~sig)
        return apply_news_blackout(out.drop("short", "long"), list(self.currencies))


def make_a():
    return DaxOpenReversal("a")


def make_b():
    return DaxOpenReversal("b")
