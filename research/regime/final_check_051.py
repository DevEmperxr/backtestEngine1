"""Run 051 — final check of the London fade A (046) and runner exits B/C (050) on test years 2021+2022,
plus all four years side by side. Pass bar pre-registered in research/runs/051_final_check_london_fade."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from lib.evaluate import bootstrap_ci
from research.regime.chart_images import equity_and_monthly_png

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "research" / "runs"
OUT = RUNS / "051_final_check_london_fade"


def path(ver: str, year: int) -> Path:
    if ver == "A":
        d = RUNS / "046_london_fade_standalone"
        return (d if year == 2024 else d / f"main_{year}") / "trades.parquet"
    return RUNS / "050_london_fade_runner" / f"{ver.lower()}_{year}" / "trades.parquet"


def results_json(ver: str, year: int) -> dict:
    p = path(ver, year).with_name("results.json")
    return json.loads(p.read_text())


def line(t: pl.DataFrame) -> dict:
    ci = bootstrap_ci(t, seed=0)["expectancy_pips"]
    eq = t.sort("exit_time")["pips"].cum_sum()
    return {"trades": t.height, "net": round(t["pips"].sum(), 1), "per_trade": round(t["pips"].mean(), 2),
            "ci95": [round(ci["ci_low"], 2), round(ci["ci_high"], 2)],
            "win_%": round(100 * (t["pips"] > 0).mean(), 1),
            "max_dd": round((eq - eq.cum_max().clip(lower_bound=0)).min(), 1)}


def main() -> None:
    years = (2021, 2022, 2023, 2024)
    T = {(v, y): pl.read_parquet(path(v, y)) for v in "ABC" for y in years}
    res: dict = {}
    print(f"{'':<16}" + "".join(f"{y:>34}" for y in years))
    for v in "ABC":
        res[v] = {str(y): line(T[(v, y)]) for y in years}
        res[v]["test 2021+2022"] = line(pl.concat([T[(v, 2021)], T[(v, 2022)]]))
        res[v]["practice 2023+2024"] = line(pl.concat([T[(v, 2023)], T[(v, 2024)]]))
        res[v]["all 4 years"] = line(pl.concat([T[(v, y)] for y in years]))
        print(f"{v:<16}" + "".join(f"{str(res[v][str(y)]['net']) + ' pips, ' + str(res[v][str(y)]['trades']) + ' tr':>34}" for y in years))
    print()
    for v in "ABC":
        for k in ("test 2021+2022", "practice 2023+2024", "all 4 years"):
            print(f"{v} {k:<20} {res[v][k]}")
    # pass bar for A: target-first vs chance in each test year
    tf = {}
    for y in (2021, 2022):
        r = results_json("A", y)["random_walk_baseline"]
        tf[str(y)] = {"target_first_%": r["actual_tp_rate_pct"], "chance_%": r["null_tp_rate_pct"]}
    pooled = res["A"]["test 2021+2022"]
    passed = pooled["net"] > 0 and all(v["target_first_%"] > v["chance_%"] for v in tf.values())
    strong = passed and pooled["ci95"][0] > 0
    verdict = "STRONG PASS" if strong else ("PASS" if passed else "FAIL")
    res["A_target_first_test_years"] = tf
    res["A_verdict"] = verdict
    print("\nA target-first vs chance:", tf, "->", verdict)
    # quarters for A on test years
    a = pl.concat([T[("A", 2021)], T[("A", 2022)]])
    q = (a.with_columns(q=pl.col("entry_time").dt.year().cast(pl.Utf8) + "-Q" + pl.col("entry_time").dt.quarter().cast(pl.Utf8))
         .group_by("q").agg(n=pl.len(), pips=pl.col("pips").sum().round(1)).sort("q"))
    res["A_quarters_test"] = q.to_dicts()
    print(q.to_dicts())
    (OUT / "results.json").write_text(json.dumps(res, indent=2, default=str))
    print(equity_and_monthly_png(a, "051: London fade (A) on unseen test years 2021+2022, EURUSD", OUT / "equity_monthly_A_2021_2022.png"))
    allA = pl.concat([T[("A", y)] for y in years])
    print(equity_and_monthly_png(allA, "London fade (A), EURUSD 2021-2024 (2021-22 unseen test years)", OUT / "equity_monthly_A_2021_2024.png"))


if __name__ == "__main__":
    main()
