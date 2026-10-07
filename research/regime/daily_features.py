"""Daily features (FX day 17:00–17:00 New York) from the 1s data of the given years joined, saved to
data/derived/<pair>_daily_<years>.parquet: high/low/close, SMA50, ATR14, its 100-day median, and the previous
completed day's trend (close vs SMA50) and "active" flag (ATR14 > 100-day median). Used by 073/074/075.

    .venv/Scripts/python.exe -m research.regime.daily_features XAUUSD 2023 2024
"""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

import polars as pl

from lib.data import load_1s_data, resample
from lib.signals import atr, sma

ROOT = Path(__file__).resolve().parents[2]
NY = "America/New_York"


def build(pair: str, years: list[int]) -> Path:
    parts = []
    for y in years:
        b = resample(load_1s_data(str(ROOT / "data" / f"{pair}_1s_{y}.csv"), verbose=False), "1m")
        parts.append(b.select("timestamp", mh=(pl.col("bid_high") + pl.col("ask_high")) / 2,
                              ml=(pl.col("bid_low") + pl.col("ask_low")) / 2, mc=(pl.col("bid_close") + pl.col("ask_close")) / 2))
    m = pl.concat(parts).sort("timestamp").with_columns(
        fxday=(pl.col("timestamp").dt.convert_time_zone(NY) + timedelta(hours=7)).dt.date())
    d = (m.group_by("fxday").agg(dh=pl.col("mh").max(), dl=pl.col("ml").min(), dc=pl.col("mc").last(), n=pl.len())
         .sort("fxday").filter(pl.col("n") >= 600)
         .with_columns(sma50=sma(pl.col("dc"), 50), datr=atr(pl.col("dh"), pl.col("dl"), pl.col("dc"), 14))
         .with_columns(datr_med=pl.col("datr").rolling_median(100, min_samples=60))
         .with_columns(trend=pl.when(pl.col("dc") > pl.col("sma50")).then(1).when(pl.col("dc") < pl.col("sma50")).then(-1),
                       active=pl.col("datr") > pl.col("datr_med"))
         .with_columns(trend_prev=pl.col("trend").shift(1), active_prev=pl.col("active").shift(1)))
    out = ROOT / "data" / "derived" / f"{pair.lower()}_daily_{'_'.join(map(str, years))}.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    d.write_parquet(out)
    return out


if __name__ == "__main__":
    pair, years = sys.argv[1], [int(y) for y in sys.argv[2:]]
    path = build(pair, years)
    d = pl.read_parquet(path)
    print(path, d.height, "days; bias from", d.filter(pl.col("trend_prev").is_not_null())["fxday"][0],
          "| up-trend days", int((d["trend_prev"] == 1).sum()), "down-trend days", int((d["trend_prev"] == -1).sum()))
