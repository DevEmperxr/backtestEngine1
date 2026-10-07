"""Run 076 — where in the day did gold (and EURUSD, for comparison) move in 2023–24? Descriptive.

Each FX day (17:00–17:00 New York) is split into Asia 18:00–03:00, London 03:00–08:00, NY morning 08:00–12:00 and
NY afternoon 12:00–17:00 (New York time). Per day and session: mid price change from the session's first 1m open to
its last 1m close (gold in $, EURUSD in pips) and in %; then totals, mean per day, t-stat and share of up days, by year.
"""

from __future__ import annotations

import json
import math
from datetime import time, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402

from lib.data import load_1s_data, pip_size, resample  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "runs" / "076_gold_sessions"
NY = "America/New_York"
SESSIONS = [("Asia 18-03", time(18, 0), time(3, 0)), ("London 03-08", time(3, 0), time(8, 0)),
            ("NY morning 08-12", time(8, 0), time(12, 0)), ("NY afternoon 12-17", time(12, 0), time(17, 0))]


def session_moves(pair: str) -> pl.DataFrame:
    parts = []
    for y in (2023, 2024):
        b = resample(load_1s_data(str(ROOT / "data" / f"{pair}_1s_{y}.csv"), verbose=False), "1m")
        parts.append(b.select("timestamp", "close_time", mo=(pl.col("bid_open") + pl.col("ask_open")) / 2,
                              mc=(pl.col("bid_close") + pl.col("ask_close")) / 2))
    m = pl.concat(parts).sort("timestamp")
    t = pl.col("timestamp").dt.convert_time_zone(NY)
    m = m.with_columns(fxday=(t + timedelta(hours=7)).dt.date(), clock=t.dt.time())
    sess = pl.lit(None, dtype=pl.Utf8)
    for name, a, b in SESSIONS:
        cond = ((pl.col("clock") >= a) | (pl.col("clock") < b)) if a > b else ((pl.col("clock") >= a) & (pl.col("clock") < b))
        sess = pl.when(cond).then(pl.lit(name)).otherwise(sess)
    m = m.with_columns(session=sess).filter(pl.col("session").is_not_null())
    d = (m.group_by("fxday", "session").agg(o=pl.col("mo").first(), c=pl.col("mc").last(), n=pl.len())
         .filter(pl.col("n") >= 30)
         .with_columns(move=(pl.col("c") - pl.col("o")) / pip_size(pair), pct=100 * (pl.col("c") / pl.col("o") - 1),
                       year=pl.col("fxday").dt.year()))
    return d.filter(pl.col("fxday").dt.weekday() <= 5)


def summarise(d: pl.DataFrame, unit: float) -> dict:
    out = {}
    for name, *_ in SESSIONS:
        x = d.filter(pl.col("session") == name)
        r = {}
        for label, part in (("2023", x.filter(pl.col("year") == 2023)), ("2024", x.filter(pl.col("year") == 2024)), ("both", x)):
            v = part["move"].to_numpy()
            p = part["pct"].to_numpy()
            r[label] = {"days": len(v), "total": round(float(v.sum()) * unit, 1), "mean_per_day": round(float(v.mean()) * unit, 3),
                        "t": round(float(v.mean() / (v.std(ddof=1) / math.sqrt(len(v)))), 2), "up_days_%": round(100 * float((v > 0).mean()), 1),
                        "total_%": round(float(p.sum()), 1)}
        out[name] = r
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    res = {}
    fig, axes = plt.subplots(1, 2, figsize=(15, 5))
    for ax, (pair, unit, lab) in zip(axes, (("XAUUSD", 0.1, "$ per oz"), ("EURUSD", 1.0, "pips"))):
        d = session_moves(pair)
        res[pair] = summarise(d, unit)
        print(f"\n===== {pair} (moves in {lab}) =====")
        for name, r in res[pair].items():
            print(f"  {name:<20} 2023 total {r['2023']['total']:>8} (t {r['2023']['t']:>5}) | 2024 total {r['2024']['total']:>8} "
                  f"(t {r['2024']['t']:>5}) | both: total {r['both']['total']:>8} = {r['both']['total_%']:>6}% , per day "
                  f"{r['both']['mean_per_day']:>7}, up days {r['both']['up_days_%']}%")
        for name, *_ in SESSIONS:
            x = d.filter(pl.col("session") == name).sort("fxday")
            ax.plot(x["fxday"].to_list(), (x["move"].cum_sum() * unit).to_list(), label=name, lw=1.5)
        ax.axhline(0, color="#555", lw=0.7)
        ax.set_title(f"{pair}: cumulative move by session, 2023–24 ({lab})", fontsize=10)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT / "session_moves.png", dpi=110)
    (OUT / "results.json").write_text(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()
