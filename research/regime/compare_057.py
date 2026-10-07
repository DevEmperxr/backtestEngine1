"""Run 057 — London fade (046) on GBPUSD 2023+2024 vs EURUSD (all four years), gross vs net."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from lib.evaluate import bootstrap_ci
from research.regime.chart_images import equity_and_monthly_png

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "research" / "runs" / "046_london_fade_standalone"
OUT = ROOT / "research" / "runs" / "057_london_fade_gbpusd"


def path(pair: str, y: int) -> Path:
    if pair == "EURUSD":
        return (RUN if y == 2024 else RUN / f"main_{y}") / "trades.parquet"
    return RUN / f"main_{pair}_{y}" / "trades.parquet"


def line(t: pl.DataFrame) -> dict:
    ci = bootstrap_ci(t, seed=0)["expectancy_pips"]
    eq = t.sort("exit_time")["pips"].cum_sum()
    return {"trades": t.height, "net": round(t["pips"].sum(), 1), "net_per_trade": round(t["pips"].mean(), 2),
            "gross_per_trade": round((t["pips"] + t["spread_pips_paid"]).mean(), 2),
            "spread_per_trade": round(t["spread_pips_paid"].mean(), 2),
            "net_ci95": [round(ci["ci_low"], 2), round(ci["ci_high"], 2)],
            "win_%": round(100 * (t["pips"] > 0).mean(), 1),
            "median_stop": round(t["sl_pips"].median(), 1), "median_target": round(t["tp_pips"].median(), 1),
            "max_dd": round((eq - eq.cum_max().clip(lower_bound=0)).min(), 1)}


def main() -> None:
    rows = {}
    for pair, years in (("GBPUSD", (2023, 2024)), ("EURUSD", (2021, 2022, 2023, 2024))):
        for y in years:
            rows[f"{pair} {y}"] = line(pl.read_parquet(path(pair, y)))
    g = pl.concat([pl.read_parquet(path("GBPUSD", y)) for y in (2023, 2024)])
    rows["GBPUSD 2023+2024"] = line(g)
    keys = list(next(iter(rows.values())))
    print(f"{'':<18}" + "".join(f"{k:>16}" for k in keys))
    for n, r in rows.items():
        print(f"{n:<18}" + "".join(f"{str(r[k]):>16}" for k in keys))
    (OUT / "comparison.json").write_text(json.dumps(rows, indent=2, default=str))
    print(equity_and_monthly_png(g, "057: London fade on GBPUSD 2023+2024 (rules unchanged)", OUT / "equity_monthly_2023_2024.png"))


if __name__ == "__main__":
    main()
