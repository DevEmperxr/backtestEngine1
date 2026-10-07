"""Run 058 — results for home-hours weakness: per pair / year / leg trade stats (with and without the news
blackout) and the raw session drift (mid price, no costs, no blackout) that tests the effect itself.
Pre-registration: research/runs/058_home_hours/summary.md.
"""

from __future__ import annotations

import json
from datetime import time
from importlib import import_module
from pathlib import Path

import numpy as np
import polars as pl

from lib.data import PIP, load_1s_data, resample
from lib.evaluate import bootstrap_ci
from research.regime.chart_images import equity_and_monthly_png

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "research" / "runs" / "058_home_hours"
PAIRS, YEARS = ("EURUSD", "GBPUSD", "AUDUSD"), (2023, 2024)
NY = "America/New_York"


def trades_path(variant: str, pair: str, y: int) -> Path:
    if pair == "EURUSD":
        if variant == "main":
            return (RUN if y == 2024 else RUN / f"main_{y}") / "trades.parquet"
        return RUN / f"{variant}_{y}" / "trades.parquet"
    return RUN / f"{variant}_{pair}_{y}" / "trades.parquet"


def leg_stats(t: pl.DataFrame) -> dict:
    if t.height == 0:
        return {"trades": 0}
    ci = bootstrap_ci(t, seed=0)["expectancy_pips"]
    return {"trades": t.height, "net": round(t["pips"].sum(), 1),
            "gross": round((t["pips"] + t["spread_pips_paid"]).sum(), 1),
            "net_per_trade": round(t["pips"].mean(), 2), "ci95": [round(ci["ci_low"], 2), round(ci["ci_high"], 2)],
            "spread_per_trade": round(t["spread_pips_paid"].mean(), 2),
            "stop_hits": int((t["exit_reason"] == "sl").sum())}


def session_drift(pair: str, y: int) -> dict:
    """Mid-price move over each full session (no costs, no blackout), one value per weekday, in pips."""
    b = resample(load_1s_data(str(ROOT / "data" / f"{pair}_1s_{y}.csv"), verbose=False), "1m")
    st = import_module("research.strategies.058_home_hours").HomeHours(
        currencies=(pair[:3], pair[3:]), blackout=False)
    s = st.generate_signals(b).with_columns(mid=(pl.col("bid_close") + pl.col("ask_close")) / 2)
    out = {}
    for leg, col in (("home_session", "in_home"), ("usd_session", "in_usd")):
        x = s.filter(pl.col(col)).with_columns(
            day=pl.col("close_time").dt.convert_time_zone(NY if leg == "usd_session" or pair[:3] != "AUD"
                                                          else "Australia/Sydney").dt.date())
        # entry at the first session bar's open ~ previous bar's close: use first bar's open mid
        first_open = ((pl.col("bid_open") + pl.col("ask_open")) / 2).first()
        d = x.group_by("day").agg(o=first_open, c=pl.col("mid").last()).with_columns(move=(pl.col("c") - pl.col("o")) / PIP)
        m = d["move"].to_numpy()
        out[leg] = {"days": len(m), "mean_pips": round(float(m.mean()), 2),
                    "t": round(float(m.mean() / (m.std(ddof=1) / np.sqrt(len(m)))), 2),
                    "share_down_%": round(100 * float((m < 0).mean()), 1)}
    return out


def main() -> None:
    res: dict = {}
    for pair in PAIRS:
        res[pair] = {}
        for y in YEARS:
            r = {}
            for variant in ("main", "noblackout"):
                t = pl.read_parquet(trades_path(variant, pair, y))
                r[variant] = {"all": leg_stats(t), "home_short": leg_stats(t.filter(pl.col("direction") == "short")),
                              "usd_long": leg_stats(t.filter(pl.col("direction") == "long"))}
            r["drift"] = session_drift(pair, y)
            res[pair][str(y)] = r
            print(f"\n== {pair} {y}")
            print("  drift (mid, no costs):", r["drift"])
            for variant in ("main", "noblackout"):
                print(f"  {variant:<11} all {r[variant]['all']}")
                print(f"  {'':<11} home short {r[variant]['home_short']}")
                print(f"  {'':<11} usd long   {r[variant]['usd_long']}")
        both = pl.concat([pl.read_parquet(trades_path("main", pair, y)) for y in YEARS])
        res[pair]["2023+2024 main"] = leg_stats(both)
        print(f"  {pair} 2023+2024 with blackout: {res[pair]['2023+2024 main']}")
        equity_and_monthly_png(both, f"058 home-hours weakness, {pair} 2023+2024 (news rule on)",
                               RUN / f"equity_monthly_{pair}_2023_2024.png")
    (RUN / "results.json").write_text(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()
