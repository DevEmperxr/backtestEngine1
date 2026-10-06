"""Run 045 — 042 (all days) vs 044 (skip red days) vs 045 (+-1 h red-news blackout), 2023+2024.
Also checks independently that no 045 trade is open inside any blackout."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import numpy as np
import polars as pl

from research.regime.chart_images import equity_and_monthly_png
from research.regime.compare_044 import row, tagged
from research.regime.news import red_news_times

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "runs" / "045_two_windows_news_blackout"


def blackout_check(t: pl.DataFrame) -> dict:
    times, days = red_news_times(["USD", "EUR"])
    ev = np.array([int(x.timestamp() * 1e9) for x in times], dtype=np.int64)
    h = int(timedelta(hours=1).total_seconds() * 1e9)
    a = t["entry_time"].dt.epoch("ns").to_numpy()
    b = t["exit_time"].dt.epoch("ns").to_numpy()
    # an event window [e - 1h, e + 1h] overlaps the open trade (a, b) if e - 1h < b and e + 1h > a
    i = np.searchsorted(ev, a - h, side="right")          # first event with e + 1h > a
    nxt = np.where(i < len(ev), ev[np.minimum(i, len(ev) - 1)], np.iinfo(np.int64).max)
    overlap = (nxt - h) < b
    d = t["entry_time"].dt.convert_time_zone("America/New_York").dt.date().is_in(sorted(days))
    return {"trades_overlapping_blackout": int(overlap.sum()), "trades_on_whole_day_blocks": int(d.sum())}


def main(scratch: Path) -> None:
    runs = {"042": tagged("042_idea1_two_windows", "042_idea1_two_windows", scratch),
            "044": tagged("044_two_windows_no_red_news", "044_two_windows_no_red_news", scratch),
            "045": tagged("045_two_windows_news_blackout", "045_two_windows_news_blackout", scratch)}
    res = {}
    for part, filt in (("London fade", pl.col("window_tag") == "london_sideways"),
                       ("NY open", pl.col("window_tag") == "ny_trend"), ("COMBINED", pl.lit(True))):
        for rn, t in runs.items():
            res[f"{part} {rn}"] = row(t.filter(filt))
    keys = list(next(iter(res.values())))
    print(f"{'':<22}" + "".join(f"{n:>16}" for n in res))
    for k in keys:
        print(f"{k:<22}" + "".join(f"{str(v[k]):>16}" for v in res.values()))
    res["blackout_check_045"] = blackout_check(runs["045"])
    print("blackout check:", res["blackout_check_045"])
    (OUT / "comparison.json").write_text(json.dumps(res, indent=2, default=str))
    runs["045"].write_parquet(OUT / "trades_tagged_2023_2024.parquet")
    print(equity_and_monthly_png(runs["045"], "045: two windows, +-1h red-news blackout, EURUSD 2023+2024", OUT / "equity_monthly_2023_2024.png"))


if __name__ == "__main__":
    import sys
    main(Path(sys.argv[1]))
