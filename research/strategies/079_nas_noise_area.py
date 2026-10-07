"""079 — NAS100 "noise area" intraday momentum (Zarattini, Aziz & Barbon 2024), FTMO rules. Pip-aware (1 point).

The noise table (day open, previous close, sigma per minute of session over the previous 14 sessions) is built from
NAS100 2023+2024 joined by build_noise_table() and cached in data/derived/nas100_noise_2023_2024.parquet.
See research/runs/079_nas100_noise_area/summary.md.
"""

from __future__ import annotations

from datetime import time
from pathlib import Path

import polars as pl

from lib.data import load_1s_data, pip_size, resample
from lib.engine import Strategy
from research.regime.news import apply_news_blackout

ROOT = Path(__file__).resolve().parents[2]
NY = "America/New_York"
TABLE = ROOT / "data" / "derived" / "nas100_noise_2023_2024.parquet"
SESSION_START, SESSION_END = time(9, 30), time(16, 0)


def build_noise_table(pair: str = "NAS100", years=(2023, 2024), lookback: int = 14) -> Path:
    """Per session day and minute-of-session: open, previous close, sigma (mean |price/open − 1| at that minute over the
    previous `lookback` sessions; the current day is never included)."""
    parts = []
    for y in years:
        b = resample(load_1s_data(str(ROOT / "data" / f"{pair}_1s_{y}.csv"), verbose=False), "1m")
        parts.append(b.select("timestamp", "close_time", mo=(pl.col("bid_open") + pl.col("ask_open")) / 2,
                              mc=(pl.col("bid_close") + pl.col("ask_close")) / 2))
    m = pl.concat(parts).sort("timestamp")
    t = pl.col("timestamp").dt.convert_time_zone(NY)
    m = m.with_columns(day=t.dt.date(), clock=t.dt.time(), wd=t.dt.weekday())
    s = m.filter((pl.col("clock") >= SESSION_START) & (pl.col("clock") < SESSION_END) & (pl.col("wd") <= 5))
    s = s.with_columns(minute=((pl.col("timestamp").dt.convert_time_zone(NY).dt.hour() * 60
                                + pl.col("timestamp").dt.convert_time_zone(NY).dt.minute()) - 570).cast(pl.Int32))
    day = (s.group_by("day").agg(open=pl.col("mo").first(), close=pl.col("mc").last(), n=pl.len()).sort("day")
           .filter(pl.col("n") >= 300).with_columns(prev_close=pl.col("close").shift(1)))
    s = s.join(day.select("day", "open"), on="day").with_columns(move=(pl.col("mc") / pl.col("open") - 1).abs())
    # sigma at the bar CLOSING at minute m+1 uses that bar's close; key by minute of the closing time
    s = s.with_columns(cmin=pl.col("minute") + 1)
    wide = s.select("day", "cmin", "move").sort("day")
    wide = wide.with_columns(sigma=pl.col("move").shift(1).rolling_mean(lookback, min_samples=lookback).over("cmin"))
    tab = wide.join(day.select("day", "open", "prev_close"), on="day").select("day", "cmin", "sigma", "open", "prev_close")
    TABLE.parent.mkdir(parents=True, exist_ok=True)
    tab.write_parquet(TABLE)
    return TABLE


class NoiseArea(Strategy):
    exit_on_opposite_signal = True
    reverse_on_opposite_signal = True
    pip_aware = True
    marker_columns = ["long_signal", "short_signal"]
    region_columns = ["in_window"]

    def __init__(self, *, stop_widths: float = 1.0, currencies: tuple[str, ...] = ("USD",)) -> None:
        super().__init__(100.0, 1000.0, "1m")
        self.stop_widths, self.currencies = stop_widths, tuple(currencies)
        self.pip = pip_size("NAS100")

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        if not TABLE.exists():
            build_noise_table()
        t = pl.col("close_time").dt.convert_time_zone(NY)
        out = df.with_columns(day=t.dt.date(), clock=t.dt.time(), wd=t.dt.weekday(),
                              cmin=(t.dt.hour() * 60 + t.dt.minute() - 570).cast(pl.Int32),
                              mc=(pl.col("bid_close") + pl.col("ask_close")) / 2)
        out = out.join(pl.read_parquet(TABLE), on=["day", "cmin"], how="left")
        up = pl.max_horizontal("open", "prev_close") * (1 + pl.col("sigma"))
        lo = pl.min_horizontal("open", "prev_close") * (1 - pl.col("sigma"))
        out = out.with_columns(upper=up, lower=lo)
        check = ((t.dt.minute().is_in([0, 30])) & (pl.col("clock") >= time(10, 0)) & (pl.col("clock") <= time(15, 30))
                 & (pl.col("wd") <= 5) & pl.col("sigma").is_not_null() & pl.col("prev_close").is_not_null())
        state = pl.when(pl.col("mc") > pl.col("upper")).then(1).when(pl.col("mc") < pl.col("lower")).then(-1).otherwise(0)
        out = out.with_columns(
            long_signal=(check & (state == 1)).fill_null(False),
            short_signal=(check & (state == -1)).fill_null(False),
            in_window=((pl.col("clock") > time(10, 0)) & (pl.col("clock") < time(15, 55)) & (pl.col("wd") <= 5)).fill_null(False),
        )
        sig = pl.col("long_signal") | pl.col("short_signal")
        width = self.stop_widths * pl.col("open") * pl.col("sigma") / self.pip
        out = out.with_columns(
            sl_pips=pl.when(sig).then(width), tp_pips=pl.when(sig).then(20 * width),
            exit_signal=((check & (state == 0)) | ~pl.col("in_window")).fill_null(True) & ~sig,
        )
        return apply_news_blackout(out, list(self.currencies))


def make():
    return NoiseArea()
