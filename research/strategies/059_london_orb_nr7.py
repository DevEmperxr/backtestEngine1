"""059 — London-open range breakout after NR7 days (Crabel 1990).

Opening range = 08:00–08:30 London (mid high/low). First 1m close beyond it between 08:30 and 11:00 London ->
enter at the next open in that direction; stop at the opposite side of the range; no target (10 x range);
flat at 16:00 London. One trade per day. NR7: trade only if the previous FX day (17:00–17:00 New York) had a
range strictly narrower than each of the 6 FX days before it. Standing ±1 h red-news blackout.

    make()     NR7 days only (the test)
    make_all() every day (control)

See research/runs/059_london_orb_nr7/summary.md.
"""

from __future__ import annotations

from datetime import time, timedelta

import polars as pl

from lib.data import PIP
from lib.engine import Strategy
from research.regime.news import apply_news_blackout

LONDON, NY = "Europe/London", "America/New_York"


class LondonORB(Strategy):
    exit_on_opposite_signal = False
    reverse_on_opposite_signal = False
    line_columns = ["or_high", "or_low"]
    marker_columns = ["long_signal", "short_signal"]
    region_columns = ["in_window"]

    def __init__(self, *, nr7: bool = True, currencies: tuple[str, ...] = ("EUR", "USD"),
                 blackout_min: int = 60) -> None:
        super().__init__(10.0, 10.0, "1m")       # per-trade columns override these
        self.nr7, self.currencies, self.blackout_min = nr7, tuple(currencies), blackout_min

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        mid = lambda f: (pl.col(f"bid_{f}") + pl.col(f"ask_{f}")) / 2
        lon = pl.col("close_time").dt.convert_time_zone(LONDON)
        start = pl.col("timestamp").dt.convert_time_zone(LONDON)        # bar open time
        out = df.with_columns(
            mh=mid("high"), ml=mid("low"), mc=mid("close"),
            lday=lon.dt.date(), lclock=lon.dt.time(), sclock=start.dt.time(),
            wkday=lon.dt.weekday() <= 5,
            # FX day: 17:00 New York -> 17:00 New York, labelled by the day it ends
            fxday=(pl.col("timestamp").dt.convert_time_zone(NY) + timedelta(hours=7)).dt.date(),
        )
        # opening range: bars that OPEN in [08:00, 08:30) London
        in_or = (pl.col("sclock") >= time(8, 0)) & (pl.col("sclock") < time(8, 30)) & pl.col("wkday")
        orng = (out.filter(in_or).group_by("lday")
                .agg(or_high=pl.col("mh").max(), or_low=pl.col("ml").min(), or_bars=pl.len()))
        out = out.join(orng, on="lday", how="left")

        # NR7 on the previous completed FX day
        fx = (out.group_by("fxday").agg(rng=pl.col("mh").max() - pl.col("ml").min(), n=pl.len()).sort("fxday")
              .filter(pl.col("n") >= 600))                                # drop stub days (e.g. holidays)
        prev6_min = pl.min_horizontal([pl.col("rng").shift(k) for k in range(1, 7)])
        fx = fx.with_columns(nr7=(pl.col("rng") < prev6_min)).with_columns(prev_nr7=pl.col("nr7").shift(1))
        out = out.join(fx.select("fxday", "prev_nr7"), on="fxday", how="left")

        window = (pl.col("lclock") > time(8, 30)) & (pl.col("lclock") <= time(11, 0)) & pl.col("wkday")
        ok = window & pl.col("or_high").is_not_null() & (pl.col("or_bars") >= 25)
        if self.nr7:
            ok = ok & pl.col("prev_nr7").fill_null(False)
        up = ok & (pl.col("mc") > pl.col("or_high"))
        dn = ok & (pl.col("mc") < pl.col("or_low"))
        brk = up | dn
        first = brk & (brk.cast(pl.Int32).cum_sum().over("lday") == 1)   # causal: first breakout today
        out = out.with_columns(
            long_signal=(first & up).fill_null(False),
            short_signal=(first & dn).fill_null(False),
            in_window=((pl.col("lclock") > time(8, 0)) & (pl.col("lclock") <= time(16, 0)) & pl.col("wkday")).fill_null(False),
        )
        out = out.with_columns(
            exit_signal=~pl.col("in_window") | (pl.col("lclock") >= time(16, 0)),
            sl_pips=pl.when(pl.col("long_signal")).then((pl.col("mc") - pl.col("or_low")) / PIP)
                      .when(pl.col("short_signal")).then((pl.col("or_high") - pl.col("mc")) / PIP),
            tp_pips=pl.when(pl.col("long_signal") | pl.col("short_signal"))
                      .then(10 * (pl.col("or_high") - pl.col("or_low")) / PIP),
        ).with_columns(
            # a signal bar can't also be an exit bar
            exit_signal=pl.col("exit_signal") & ~(pl.col("long_signal") | pl.col("short_signal")),
        )
        return apply_news_blackout(out, list(self.currencies), self.blackout_min)


def make() -> LondonORB:
    return LondonORB(nr7=True)


def make_all() -> LondonORB:
    return LondonORB(nr7=False)
