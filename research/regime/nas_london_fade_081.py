"""Run 081 — London fade on NAS100 results after FTMO costs: per year, long vs short, before costs, exits, best-day
share, FTMO 1-step scorecard vs the zero-edge twin, equity + monthly chart. Pre-registered in
research/runs/081_nas_london_fade/summary.md."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import polars as pl

from lib.prop_firms import ftmo_1step_scorecard
from research.regime.chart_images import equity_and_monthly_png
from research.regime.trend_dip_073 import stats

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "research" / "runs" / "081_nas_london_fade"


def load(y: int) -> pl.DataFrame:
    return pl.read_parquet(RUN / f"main_NAS100_{y}" / "trades.parquet").with_columns(R=pl.col("pips") / pl.col("sl_pips"))


def main() -> None:
    t = {y: load(y) for y in (2023, 2024)}
    both = pl.concat([t[2023], t[2024]]).sort("entry_time")
    r = {str(y): stats(t[y]) for y in (2023, 2024)}
    r["both"] = stats(both)
    r["long"] = stats(both.filter(pl.col("direction") == "long"))
    r["short"] = stats(both.filter(pl.col("direction") == "short"))
    r["gross_R_per_trade"] = round(((both["pips"] + both["spread_pips_paid"] + both["commission_pips"]) / both["sl_pips"]).mean(), 3)
    r["exits"] = dict(both.group_by("exit_reason").len().iter_rows())
    days = both.with_columns(d=pl.col("entry_time").dt.date()).group_by("d").agg(R=pl.col("R").sum(), n=pl.len())
    r["days_traded"] = days.height
    r["trades_per_traded_day"] = round(both.height / days.height, 2)
    pos = days.filter(pl.col("R") > 0)
    r["best_day_share_of_profit_%"] = round(100 * pos["R"].max() / both["R"].sum(), 1)
    r["best_day_R"] = round(pos["R"].max(), 2)
    start = both["entry_time"].min().date()
    sc = ftmo_1step_scorecard(both, start, date(2024, 12, 31), n_sims=1500, seed=4)
    r["scorecard"] = {"strategy": sc["strategy"], "zero_edge_twin": sc["zero_edge_twin"], "beats_twin": sc["beats_twin"]}
    r["candidate"] = bool(r["2023"]["R_per_trade"] > 0 and r["2024"]["R_per_trade"] > 0 and r["both"]["R_per_trade"] >= 0.05
                          and sc["beats_twin"])
    for k in ("2023", "2024", "both", "long", "short"):
        print(f"{k:>6} {r[k]}")
    print("gross R/trade", r["gross_R_per_trade"], "| exits", r["exits"], "| days traded", r["days_traded"],
          "| trades/day", r["trades_per_traded_day"], "| best day", r["best_day_R"], "R =", r["best_day_share_of_profit_%"], "% of profit")
    print("FTMO strategy:", sc["strategy"])
    print("FTMO twin:    ", sc["zero_edge_twin"])
    print("candidate:", r["candidate"])
    png = equity_and_monthly_png(both.with_columns(pips=pl.col("R")), "081 London fade on NAS100, in R after FTMO costs (axis \"pips\" = R), 2023–24", RUN / "nas_london_fade_081.png")
    (RUN / "results.json").write_text(json.dumps(r, indent=2, default=str))
    print(png)


if __name__ == "__main__":
    main()
