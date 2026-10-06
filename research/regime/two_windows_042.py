"""Run 042 — per-window and combined stats for Idea 1 with two entry windows, EURUSD 2023+2024.

Trades come from run_experiment (042 strategy, one account). Each trade is tagged with the window
of its signal bar (london_sideways / ny_trend). Stats use playbook_stats.stats (fair Sharpe incl.
no-trade days); bootstrap CIs from lib.evaluate.
"""

from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path

import polars as pl

from lib.data import load_1s_data, resample
from lib.evaluate import bootstrap_ci
from research.regime.chart_images import equity_and_monthly_png
from research.regime.playbook_stats import stats

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "research" / "runs" / "042_idea1_two_windows"
NAMES = {"london_sideways": "London fade (03-05 NY, sideways)", "ny_trend": "NY open (08-10 NY, trending)"}


def load(scratch: Path) -> pl.DataFrame:
    st = import_module("research.strategies.042_idea1_two_windows").make()
    parts = []
    for y, f in ((2023, RUN / "main_2023" / "trades.parquet"), (2024, RUN / "trades.parquet")):
        bp = scratch / f"bars1m_{y}.parquet"
        b = pl.read_parquet(bp) if bp.exists() else resample(load_1s_data(str(ROOT / "data" / f"EURUSD_1s_{y}.csv"), verbose=False), "1m")
        tag = st.generate_signals(b).select(pl.col("close_time").alias("entry_time"), "window_tag")
        parts.append(pl.read_parquet(f).join(tag, on="entry_time", how="left"))
    t = pl.concat(parts).sort("exit_time")
    assert t["window_tag"].null_count() == 0
    return t.with_columns(r=pl.col("pips") / pl.col("sl_pips"),
                          hold_min=(pl.col("exit_time") - pl.col("entry_time")).dt.total_seconds() / 60)


def main(scratch: Path) -> None:
    t = load(scratch)
    table = {}
    for k, name in NAMES.items():
        table[name] = stats(t.filter(pl.col("window_tag") == k))
    table["COMBINED"] = stats(t)
    for name, x in [(n, t.filter(pl.col("window_tag") == k)) for k, n in NAMES.items()] + [("COMBINED", t)]:
        for y in (2023, 2024):
            xs = x.filter(pl.col("entry_time").dt.year() == y)
            table[name][f"pips_{y}"] = round(xs["pips"].sum(), 1)
        ci = bootstrap_ci(x, seed=0)["expectancy_pips"]
        table[name]["per_trade_ci95"] = [round(ci["ci_low"], 2), round(ci["ci_high"], 2)]
        top5 = x.sort("pips", descending=True)
        table[name]["pips_without_best_5"] = round(top5["pips"].sum() - top5["pips"].head(5).sum(), 1)
    keys = list(table["COMBINED"])
    print(f"{'':<24}" + "".join(f"{n[:30]:>34}" for n in table))
    for k in keys:
        print(f"{k:<24}" + "".join(f"{str(table[n][k]):>34}" for n in table))
    m = (t.with_columns(month=pl.col("exit_time").dt.strftime("%Y-%m"))
         .group_by("month").agg(*[pl.col("pips").filter(pl.col("window_tag") == k).sum().alias(k) for k in NAMES]))
    corr = m.select(pl.corr("london_sideways", "ny_trend"))[0, 0]
    table["monthly_correlation_between_windows"] = round(corr, 2)
    print("monthly correlation between windows:", round(corr, 2))
    (RUN / "stats.json").write_text(json.dumps(table, indent=2, default=str))
    t.write_parquet(RUN / "trades_tagged_2023_2024.parquet")
    print(equity_and_monthly_png(t, "042: Idea 1, two windows only (London fade + NY open), EURUSD 2023+2024", RUN / "equity_monthly_2023_2024.png"))


if __name__ == "__main__":
    import sys
    main(Path(sys.argv[1]))
