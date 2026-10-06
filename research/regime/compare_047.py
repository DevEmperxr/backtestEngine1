"""Run 047 — London fade: sweep on 1m (046) vs sweep on 5m (047), EURUSD 2023."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import polars as pl

from lib.evaluate import bootstrap_ci, evaluate, sharpe_all_days
from research.regime.chart_images import equity_and_monthly_png

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "research" / "runs"
OUT = RUNS / "047_london_fade_5m_sweep"


def sheet(run: str) -> dict:
    t = pl.read_parquet(RUNS / run / "main_2023" / "trades.parquet").sort("exit_time")
    r = json.loads((RUNS / run / "main_2023" / "results.json").read_text())["random_walk_baseline"]
    s = evaluate(t)["summary"]
    ci = bootstrap_ci(t, seed=0)["expectancy_pips"]
    eq = t["pips"].cum_sum()
    m = t.group_by(pl.col("exit_time").dt.month()).agg(p=pl.col("pips").sum())
    return {
        "trades": t.height, "net_pips": round(s["total_pips"], 1), "per_trade": round(s["expectancy_pips"], 2),
        "per_trade_ci95": [round(ci["ci_low"], 2), round(ci["ci_high"], 2)],
        "win_rate_%": round(s["win_rate"], 1), "profit_factor": round(s["profit_factor"], 2),
        "target_first_%": r["actual_tp_rate_pct"], "chance_target_first_%": r["null_tp_rate_pct"],
        "median_stop": round(t["sl_pips"].median(), 1), "median_target": round(t["tp_pips"].median(), 1),
        "median_hold_min": round(((t["exit_time"] - t["entry_time"]).dt.total_seconds() / 60).median()),
        "max_dd_pips": round((eq - eq.cum_max().clip(lower_bound=0)).min(), 1),
        "months_positive": f"{int((m['p'] > 0).sum())}/12",
        "fair_sharpe": round(sharpe_all_days(t, date(2023, 1, 2), date(2023, 12, 29))["sharpe"], 2),
        "H1 / H2": [round(t.filter(pl.col("entry_time").dt.month() <= 6)["pips"].sum(), 1),
                    round(t.filter(pl.col("entry_time").dt.month() > 6)["pips"].sum(), 1)],
    }


def main() -> None:
    a, b = sheet("046_london_fade_standalone"), sheet("047_london_fade_5m_sweep")
    print(f"{'':<24}{'1m sweep (046)':>22}{'5m sweep (047)':>22}")
    for k in a:
        print(f"{k:<24}{str(a[k]):>22}{str(b[k]):>22}")
    # overlap: a 5m trade "matches" a 1m trade if they enter within 5 minutes in the same direction
    t1 = pl.read_parquet(RUNS / "046_london_fade_standalone" / "main_2023" / "trades.parquet")
    t5 = pl.read_parquet(RUNS / "047_london_fade_5m_sweep" / "main_2023" / "trades.parquet")
    j = t5.sort("entry_time").join_asof(t1.sort("entry_time").select("entry_time", "direction", pl.col("entry_time").alias("e1")),
                                        on="entry_time", by="direction", strategy="nearest", tolerance=timedelta(minutes=5))
    both = j.filter(pl.col("e1").is_not_null())
    only5 = j.filter(pl.col("e1").is_null())
    ov = {"5m trades with a 1m trade within 5 min": both.height, "their pips": round(both["pips"].sum(), 1),
          "5m-only trades": only5.height, "their pips (5m-only)": round(only5["pips"].sum(), 1)}
    print(ov)
    (OUT / "comparison.json").write_text(json.dumps({"1m_046": a, "5m_047": b, "overlap": ov}, indent=2, default=str))
    print(equity_and_monthly_png(t5, "047: London fade, sweep on 5m candles, EURUSD 2023", OUT / "equity_monthly_2023.png"))


if __name__ == "__main__":
    main()
