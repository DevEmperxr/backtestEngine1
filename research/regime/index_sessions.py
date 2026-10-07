"""Where in the day did a stock index move (2023–24)? Descriptive, like 076 for gold.

    .venv/Scripts/python.exe -m research.regime.index_sessions NAS100

Sessions (New York time): overnight 18:00–04:00, pre-market 04:00–09:30, the open 09:30–10:00, morning 10:00–12:00,
midday 12:00–14:00, afternoon 14:00–16:00, after the close 16:00–17:00. Per FX day (17:00–17:00 NY) and session: mid
change from the session's first 1m open to its last 1m close, in index points and %, totals / t-stats / up days by year.
"""

from __future__ import annotations

import json
import math
import sys
from datetime import time, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import polars as pl  # noqa: E402

from lib.data import load_1s_data, resample  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
NY = "America/New_York"
SESSIONS = [("overnight 18-04", time(18, 0), time(4, 0)), ("pre-market 04-09:30", time(4, 0), time(9, 30)),
            ("open 09:30-10", time(9, 30), time(10, 0)), ("morning 10-12", time(10, 0), time(12, 0)),
            ("midday 12-14", time(12, 0), time(14, 0)), ("afternoon 14-16", time(14, 0), time(16, 0)),
            ("after close 16-17", time(16, 0), time(17, 0))]


def moves(pair: str) -> pl.DataFrame:
    parts = []
    for y in (2023, 2024):
        b = resample(load_1s_data(str(ROOT / "data" / f"{pair}_1s_{y}.csv"), verbose=False), "1m")
        parts.append(b.select("timestamp", mo=(pl.col("bid_open") + pl.col("ask_open")) / 2,
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
         .filter(pl.col("n") >= 10)
         .with_columns(move=pl.col("c") - pl.col("o"), pct=100 * (pl.col("c") / pl.col("o") - 1),
                       year=pl.col("fxday").dt.year()))
    return d.filter(pl.col("fxday").dt.weekday() <= 5)


def main(pair: str) -> None:
    out_dir = ROOT / "research" / "runs" / f"080_{pair.lower()}_sessions"
    out_dir.mkdir(parents=True, exist_ok=True)
    d = moves(pair)
    res = {}
    fig, ax = plt.subplots(figsize=(12, 5))
    for name, *_ in SESSIONS:
        x = d.filter(pl.col("session") == name)
        r = {}
        for label, part in (("2023", x.filter(pl.col("year") == 2023)), ("2024", x.filter(pl.col("year") == 2024)), ("both", x)):
            v, p = part["move"].to_numpy(), part["pct"].to_numpy()
            r[label] = {"days": len(v), "total_pts": round(float(v.sum()), 1), "total_%": round(float(p.sum()), 1),
                        "mean_pts": round(float(v.mean()), 2), "t": round(float(v.mean() / (v.std(ddof=1) / math.sqrt(len(v)))), 2),
                        "up_days_%": round(100 * float((v > 0).mean()), 1), "mean_abs_pts": round(float(abs(v).mean()), 1)}
        res[name] = r
        print(f"{pair} {name:<22} 2023 {r['2023']['total_pts']:>8} pts (t {r['2023']['t']:>5}) | 2024 {r['2024']['total_pts']:>8} "
              f"(t {r['2024']['t']:>5}) | both {r['both']['total_%']:>6}% | per day {r['both']['mean_pts']:>6} pts | "
              f"avg size {r['both']['mean_abs_pts']} pts | up days {r['both']['up_days_%']}%")
        xs = x.sort("fxday")
        ax.plot(xs["fxday"].to_list(), xs["pct"].cum_sum().to_list(), label=name, lw=1.4)
    ax.axhline(0, color="#555", lw=0.7)
    ax.set_title(f"{pair}: cumulative % move by session, 2023–24 (New York time)", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_dir / "session_moves.png", dpi=110)
    (out_dir / "results.json").write_text(json.dumps(res, indent=2, default=str))
    print(out_dir / "session_moves.png")


if __name__ == "__main__":
    main(sys.argv[1].upper())
