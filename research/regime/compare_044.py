"""Run 044 — 042 (two windows) vs 044 (same, no red-news days): per window and combined, 2023+2024."""

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
RUNS = ROOT / "research" / "runs"
OUT = RUNS / "044_two_windows_no_red_news"
SHOW = ["trades", "win_rate_%", "expectancy_pips", "profit_factor", "max_drawdown_pips",
        "longest_drawdown_days", "months_positive", "sharpe_all_days", "total_pips"]


def tagged(run: str, strat: str, scratch: Path) -> pl.DataFrame:
    st = import_module(f"research.strategies.{strat}").make()
    parts = []
    for y, f in ((2023, RUNS / run / "main_2023" / "trades.parquet"), (2024, RUNS / run / "trades.parquet")):
        bp = scratch / f"bars1m_{y}.parquet"
        b = pl.read_parquet(bp) if bp.exists() else resample(load_1s_data(str(ROOT / "data" / f"EURUSD_1s_{y}.csv"), verbose=False), "1m")
        tag = st.generate_signals(b).select(pl.col("close_time").alias("entry_time"), "window_tag")
        parts.append(pl.read_parquet(f).join(tag, on="entry_time", how="left"))
    t = pl.concat(parts).sort("exit_time")
    assert t["window_tag"].null_count() == 0
    return t.with_columns(r=pl.col("pips") / pl.col("sl_pips"),
                          hold_min=(pl.col("exit_time") - pl.col("entry_time")).dt.total_seconds() / 60)


def row(x: pl.DataFrame) -> dict:
    s = stats(x)
    d = {k: s[k] for k in SHOW}
    for y in (2023, 2024):
        d[f"pips_{y}"] = round(x.filter(pl.col("entry_time").dt.year() == y)["pips"].sum(), 1)
    ci = bootstrap_ci(x, seed=0)["expectancy_pips"]
    d["per_trade_ci95"] = [round(ci["ci_low"], 2), round(ci["ci_high"], 2)]
    return d


def main(scratch: Path) -> None:
    runs = {"042 all days": tagged("042_idea1_two_windows", "042_idea1_two_windows", scratch),
            "044 no red-news days": tagged("044_two_windows_no_red_news", "044_two_windows_no_red_news", scratch)}
    res = {}
    for part, filt in (("London fade", pl.col("window_tag") == "london_sideways"),
                       ("NY open", pl.col("window_tag") == "ny_trend"), ("COMBINED", pl.lit(True))):
        for rn, t in runs.items():
            res[f"{part} | {rn}"] = row(t.filter(filt))
    keys = list(next(iter(res.values())))
    print(f"{'':<24}" + "".join(f"{n.split(' | ')[0][:12] + (' 042' if '042' in n else ' 044'):>18}" for n in res))
    for k in keys:
        print(f"{k:<24}" + "".join(f"{str(v[k]):>18}" for v in res.values()))
    (OUT / "comparison.json").write_text(json.dumps(res, indent=2, default=str))
    t = runs["044 no red-news days"]
    t.write_parquet(OUT / "trades_tagged_2023_2024.parquet")
    print(equity_and_monthly_png(t, "044: two windows, no red-news days (USD/EUR), EURUSD 2023+2024", OUT / "equity_monthly_2023_2024.png"))


if __name__ == "__main__":
    import sys
    main(Path(sys.argv[1]))
