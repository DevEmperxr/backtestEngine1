"""058 — Home-hours weakness (Breedon & Ranaldo 2011): short the base currency during its home session,
long it during the US session, every weekday.

Sessions (the paper's futures-hours definitions, in local time so daylight saving is handled):
    EUR / GBP base:  home = 07:00 London -> 08:00 New York (open to open, the sessions overlap)
    AUD base:        home = 10:00 -> 16:00 Sydney
    USD session:     08:00 -> 16:00 New York
The base currency comes from `currencies[0]` (run_experiment sets it from --pair).

Signals are levels on every session bar (entry at the session's first minute = the first signal bar's
close); at 08:00 NY a still-open EUR/GBP short is reversed into the long (exit_on_opposite + reverse).
Outside the sessions exit_signal closes any position. Standing ±1 h red-news blackout via
apply_news_blackout (re-entry when the blackout ends, if the session is still on). Protective stop =
1 x daily ATR(20) of the previous completed UTC days (min 5 days at the start of the data); target 10 x ATR (effectively off).

See research/runs/058_home_hours/summary.md.
"""

from __future__ import annotations

from datetime import time

import polars as pl

from lib.data import PIP
from lib.engine import Strategy
from research.regime.news import apply_news_blackout

NY, LONDON, SYDNEY = "America/New_York", "Europe/London", "Australia/Sydney"


def _clock(tz: str) -> pl.Expr:
    return pl.col("close_time").dt.convert_time_zone(tz).dt.time()


def _weekday(tz: str) -> pl.Expr:
    return pl.col("close_time").dt.convert_time_zone(tz).dt.weekday() <= 5


class HomeHours(Strategy):
    exit_on_opposite_signal = True
    reverse_on_opposite_signal = True
    marker_columns = ["long_signal", "short_signal"]
    region_columns = ["in_home", "in_usd"]

    def __init__(self, *, currencies: tuple[str, ...] = ("EUR", "USD"), blackout: bool = True,
                 blackout_min: int = 60, stop_atr: float = 1.0, target_atr: float = 10.0) -> None:
        super().__init__(10.0, 10.0, "1m")       # per-trade columns override these
        self.currencies = tuple(currencies)
        self.blackout, self.blackout_min = blackout, blackout_min
        self.stop_atr, self.target_atr = stop_atr, target_atr

    def _home_session(self) -> pl.Expr:
        base = self.currencies[0]
        if base in ("EUR", "GBP"):
            return (_clock(LONDON) >= time(7, 0)) & (_clock(NY) < time(8, 0)) & _weekday(NY)
        if base == "AUD":
            return (_clock(SYDNEY) >= time(10, 0)) & (_clock(SYDNEY) < time(16, 0)) & _weekday(SYDNEY)
        raise ValueError(f"no home session defined for base currency {base!r}")

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        if self.currencies[-1] != "USD":
            raise ValueError("058 is defined for XXX/USD pairs (USD session = 08:00-16:00 NY)")
        in_usd = (_clock(NY) >= time(8, 0)) & (_clock(NY) < time(16, 0)) & _weekday(NY)
        out = df.with_columns(in_home=self._home_session().fill_null(False), in_usd=in_usd.fill_null(False))

        # daily ATR(20) on mid prices, previous completed UTC days only
        mid = lambda f: (pl.col(f"bid_{f}") + pl.col(f"ask_{f}")) / 2
        day = pl.col("close_time").dt.date().alias("d")
        daily = (out.group_by(day).agg(h=mid("high").max(), l=mid("low").min(), c=mid("close").last()).sort("d")
                 # ATR(20); the first weeks of the data use the days available so far (min 5),
                 # so January isn't skipped for lack of history
                 .with_columns(atr_d=pl.max_horizontal(
                     pl.col("h") - pl.col("l"), (pl.col("h") - pl.col("c").shift(1)).abs(),
                     (pl.col("l") - pl.col("c").shift(1)).abs()).rolling_mean(20, min_samples=5))
                 .with_columns(atr_prev=pl.col("atr_d").shift(1)).select("d", "atr_prev"))
        out = out.with_columns(day).join(daily, on="d", how="left").drop("d")

        ok = pl.col("atr_prev").is_not_null()
        out = out.with_columns(
            short_signal=pl.col("in_home") & ok,
            long_signal=pl.col("in_usd") & ok,
        ).with_columns(
            exit_signal=~(pl.col("short_signal") | pl.col("long_signal")),
            sl_pips=pl.when(ok).then(self.stop_atr * pl.col("atr_prev") / PIP),
            tp_pips=pl.when(ok).then(self.target_atr * pl.col("atr_prev") / PIP),
        )
        if self.blackout:
            out = apply_news_blackout(out, list(self.currencies), self.blackout_min)
        return out


def make() -> HomeHours:
    return HomeHours()


def make_noblackout() -> HomeHours:
    """Reference only (news rule off), to measure what the blackout costs."""
    return HomeHours(blackout=False)
