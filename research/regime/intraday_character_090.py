"""Run 090 — does each index trend or mean-revert inside its cash session? (descriptive, 2023 + 2024; why 089 worked on
NAS100 but not GER40 / JPN225)

    .venv/Scripts/python.exe -m research.regime.intraday_character_090

Per index and cash session (089 clocks), from 30-minute mid returns:
- variance ratio VR = var(sum of 30-min returns over the session) / (k * var(one 30-min return)); > 1 trending, < 1
  mean-reverting, inside the day
- autocorrelation of consecutive 30-min returns
- "move so far -> rest of day": corr of (open -> each check) with (check -> close), averaged over checks
- share of the cash-session move already in the opening gap (overnight vs day)
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl

from lib.data import load_1s_data, resample

ROOT = Path(__file__).resolve().parents[2]
SESSIONS = {"NAS100": ("America/New_York", 570, 960), "GER40": ("Europe/Berlin", 540, 1050), "JPN225": ("Asia/Tokyo", 540, 900)}


def main() -> None:
    res = {}
    for pair, (tz, o, c) in SESSIONS.items():
        parts = []
        for y in (2023, 2024):
            b = resample(load_1s_data(str(ROOT / "data" / f"{pair}_1s_{y}.csv"), verbose=False), "1m")
            parts.append(b.select("timestamp", mc=(pl.col("bid_close") + pl.col("ask_close")) / 2,
                                  mo=(pl.col("bid_open") + pl.col("ask_open")) / 2))
        m = pl.concat(parts).sort("timestamp")
        t = pl.col("timestamp").dt.convert_time_zone(tz)
        m = m.with_columns(day=t.dt.date(), wd=t.dt.weekday(), smin=t.dt.hour().cast(pl.Int32) * 60 + t.dt.minute().cast(pl.Int32))
        s = m.filter((pl.col("smin") >= o) & (pl.col("smin") < c) & (pl.col("wd") <= 5))
        # price at each 30-min mark (open of the bar starting there), plus the close
        marks = list(range(o, c, 30))
        px = s.filter(pl.col("smin").is_in(marks)).pivot(on="smin", index="day", values="mo")
        cl = s.group_by("day").agg(close=pl.col("mc").last(), n=pl.len())
        d = px.join(cl, on="day").filter(pl.col("n") >= 0.75 * (c - o)).drop_nulls().sort("day")
        P = np.column_stack([d[str(k)].to_numpy() for k in marks] + [d["close"].to_numpy()])
        lr = np.diff(np.log(P), axis=1)                       # 30-min log returns, k per day
        k = lr.shape[1]
        vr = float(np.var(lr.sum(1)) / (k * np.var(lr)))
        ac = float(np.corrcoef(lr[:, :-1].ravel(), lr[:, 1:].ravel())[0, 1])
        so_far = []
        for j in range(1, k):
            a, b2 = np.log(P[:, j] / P[:, 0]), np.log(P[:, -1] / P[:, j])
            so_far.append(np.corrcoef(a, b2)[0, 1])
        prev_close = np.r_[np.nan, P[:-1, -1]]
        gap = np.abs(np.log(P[1:, 0] / prev_close[1:]))
        day_move = np.abs(np.log(P[1:, -1] / P[1:, 0]))
        res[pair] = {"days": int(len(P)), "variance_ratio": round(vr, 3), "autocorr_30m": round(ac, 3),
                     "corr_move_so_far_vs_rest": round(float(np.mean(so_far)), 3),
                     "corr_by_check": [round(float(x), 3) for x in so_far],
                     "gap_share_of_abs_move_%": round(100 * float(gap.mean() / (gap.mean() + day_move.mean())), 1)}
        print(pair, {k2: v for k2, v in res[pair].items() if k2 != "corr_by_check"})
    out = ROOT / "research" / "runs" / "090_intraday_character"
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
