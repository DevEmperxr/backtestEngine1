"""089 — the 079 noise-area momentum rules on any index, with its own cash-session clock. Pip-aware (1 point).

    make_ger40()   09:00–17:30 Frankfurt, checks 09:30–17:00, flat 17:25
    make_jpn225()  09:00–15:00 Tokyo, checks 09:30–14:30, flat 14:55

Noise table per pair (open, previous close, sigma per minute of session over the previous 14 sessions) from 2023+2024
joined, cached in data/derived/<pair>_noise_2023_2024.parquet. News currencies come from run_experiment
(pair_currencies: GER40 EUR+USD, JPN225 JPY+USD). See research/runs/089_noise_area_indices/summary.md.
"""

from __future__ import annotations

from datetime import time
from pathlib import Path

import polars as pl

from lib.data import load_1s_data, resample
from lib.engine import Strategy
from research.regime.news import apply_news_blackout, pair_currencies

ROOT = Path(__file__).resolve().parents[2]
# pair -> (time zone, session open minute, session close minute, flat minute)
SESSIONS = {"NAS100": ("America/New_York", 570, 960, 955), "GER40": ("Europe/Berlin", 540, 1050, 1045),
            "JPN225": ("Asia/Tokyo", 540, 900, 895)}


def table_path(pair: str) -> Path:
    return ROOT / "data" / "derived" / f"{pair.lower()}_noise_2023_2024.parquet"


def build_noise_table(pair: str, years=(2023, 2024), lookback: int = 14) -> Path:
    tz, o, c, _ = SESSIONS[pair]
    parts = []
    for y in years:
        b = resample(load_1s_data(str(ROOT / "data" / f"{pair}_1s_{y}.csv"), verbose=False), "1m")
        parts.append(b.select("timestamp", mo=(pl.col("bid_open") + pl.col("ask_open")) / 2,
                              mc=(pl.col("bid_close") + pl.col("ask_close")) / 2))
    m = pl.concat(parts).sort("timestamp")
    t = pl.col("timestamp").dt.convert_time_zone(tz)
    m = m.with_columns(day=t.dt.date(), wd=t.dt.weekday(),
                       smin=t.dt.hour().cast(pl.Int32) * 60 + t.dt.minute().cast(pl.Int32))
    s = m.filter((pl.col("smin") >= o) & (pl.col("smin") < c) & (pl.col("wd") <= 5))
    day = (s.group_by("day").agg(open=pl.col("mo").first(), close=pl.col("mc").last(), n=pl.len(),
                                 first=pl.col("smin").min())
           .filter((pl.col("n") >= 0.75 * (c - o)) & (pl.col("first") == o)).sort("day")
           .with_columns(prev_close=pl.col("close").shift(1)))
    s = s.join(day.select("day", "open"), on="day").with_columns(
        move=(pl.col("mc") / pl.col("open") - 1).abs(), cmin=pl.col("smin") - o + 1)   # keyed by the bar's CLOSE minute
    w = s.select("day", "cmin", "move").sort("day").with_columns(
        sigma=pl.col("move").shift(1).rolling_mean(lookback, min_samples=lookback).over("cmin"))
    tab = w.join(day.select("day", "open", "prev_close"), on="day").select("day", "cmin", "sigma", "open", "prev_close")
    p = table_path(pair)
    p.parent.mkdir(parents=True, exist_ok=True)
    tab.write_parquet(p)
    return p


class NoiseAreaIndex(Strategy):
    exit_on_opposite_signal = True
    reverse_on_opposite_signal = True
    pip_aware = True
    marker_columns = ["long_signal", "short_signal"]
    region_columns = ["in_window"]

    def __init__(self, pair: str, *, stop_widths: float = 1.0) -> None:
        super().__init__(100.0, 1000.0, "1m")
        self.pair, self.stop_widths = pair, stop_widths
        self.currencies = tuple(pair_currencies(pair))
        self.pip = 1.0

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        tz, o, c, flat = SESSIONS[self.pair]
        if not table_path(self.pair).exists():
            build_noise_table(self.pair)
        t = pl.col("close_time").dt.convert_time_zone(tz)
        cm = t.dt.hour().cast(pl.Int32) * 60 + t.dt.minute().cast(pl.Int32)
        out = df.with_columns(day=t.dt.date(), wd=t.dt.weekday(), clock_min=cm, cmin=cm - o,
                              mc=(pl.col("bid_close") + pl.col("ask_close")) / 2)
        out = out.join(pl.read_parquet(table_path(self.pair)), on=["day", "cmin"], how="left")
        up = pl.max_horizontal("open", "prev_close") * (1 + pl.col("sigma"))
        lo = pl.min_horizontal("open", "prev_close") * (1 - pl.col("sigma"))
        out = out.with_columns(upper=up, lower=lo)
        check = ((pl.col("clock_min") % 30 == 0) & (pl.col("clock_min") >= o + 30) & (pl.col("clock_min") <= c - 30)
                 & (pl.col("wd") <= 5) & pl.col("sigma").is_not_null() & pl.col("prev_close").is_not_null())
        state = pl.when(pl.col("mc") > pl.col("upper")).then(1).when(pl.col("mc") < pl.col("lower")).then(-1).otherwise(0)
        out = out.with_columns(
            long_signal=(check & (state == 1)).fill_null(False),
            short_signal=(check & (state == -1)).fill_null(False),
            in_window=((pl.col("clock_min") >= o + 30) & (pl.col("clock_min") < flat) & (pl.col("wd") <= 5)).fill_null(False),
        )
        sig = pl.col("long_signal") | pl.col("short_signal")
        width = self.stop_widths * pl.col("open") * pl.col("sigma") / self.pip
        out = out.with_columns(
            sl_pips=pl.when(sig).then(width), tp_pips=pl.when(sig).then(20 * width),
            exit_signal=((check & (state == 0)) | ~pl.col("in_window")).fill_null(True) & ~sig,
        )
        return apply_news_blackout(out, list(self.currencies))


def make_ger40():
    return NoiseAreaIndex("GER40")


def make_jpn225():
    return NoiseAreaIndex("JPN225")


def make_nas100():      # replication check of 079 through the general code
    return NoiseAreaIndex("NAS100")
