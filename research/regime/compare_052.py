"""Run 052 — London fade 046 (all trades) vs 052 (one trade per NY day), EURUSD 2021–2024."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import polars as pl

from lib.evaluate import bootstrap_ci, sharpe_all_days
from research.regime.chart_images import equity_and_monthly_png

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "research" / "runs"
OUT = RUNS / "052_london_fade_one_a_day"
YEARS = (2021, 2022, 2023, 2024)


def load(run: str, y: int) -> pl.DataFrame:
    d = RUNS / run
    return pl.read_parquet((d if y == 2024 else d / f"main_{y}") / "trades.parquet").sort("exit_time")


def line(t: pl.DataFrame, y0: int, y1: int) -> dict:
    ci = bootstrap_ci(t, seed=0)["expectancy_pips"]
    eq = t.sort("exit_time")["pips"].cum_sum()
    return {"trades": t.height, "net": round(t["pips"].sum(), 1), "per_trade": round(t["pips"].mean(), 2),
            "ci95": [round(ci["ci_low"], 2), round(ci["ci_high"], 2)], "win_%": round(100 * (t["pips"] > 0).mean(), 1),
            "max_dd": round((eq - eq.cum_max().clip(lower_bound=0)).min(), 1),
            "fair_sharpe": round(sharpe_all_days(t, date(y0, 1, 1), date(y1, 12, 31))["sharpe"], 2)}


def main() -> None:
    res = {}
    rows = []
    for y in YEARS:
        a, o = load("046_london_fade_standalone", y), load("052_london_fade_one_a_day", y)
        day = pl.col("entry_time").dt.convert_time_zone("America/New_York").dt.date()
        nth = a.sort("entry_time").with_columns(n=pl.col("entry_time").rank("ordinal").over(day))
        later = nth.filter(pl.col("n") > 1)
        res[str(y)] = {"all trades (046)": line(a, y, y), "one a day (052)": line(o, y, y),
                       "046 2nd+ trades of the day": {"trades": later.height, "net": round(later["pips"].sum(), 1)}}
        r = res[str(y)]
        rows.append((y, r["all trades (046)"], r["one a day (052)"], r["046 2nd+ trades of the day"]))
    A = pl.concat([load("046_london_fade_standalone", y) for y in YEARS])
    O = pl.concat([load("052_london_fade_one_a_day", y) for y in YEARS])
    res["all 4 years"] = {"all trades (046)": line(A, 2021, 2024), "one a day (052)": line(O, 2021, 2024)}
    print(f"{'year':<6}{'046 all trades':>46}{'052 one a day':>46}{'046 2nd+ of day':>22}")
    for y, a, o, l in rows:
        f = lambda d: f"{d['trades']} tr, {d['net']:+.1f}, {d['per_trade']:+.2f}/tr, dd {d['max_dd']}, S {d['fair_sharpe']}"
        print(f"{y:<6}{f(a):>46}{f(o):>46}{str(l['trades']) + ' tr, ' + format(l['net'], '+.1f'):>22}")
    for k, v in res["all 4 years"].items():
        print(f"all 4 years {k:<20}{v}")
    (OUT / "comparison.json").write_text(json.dumps(res, indent=2, default=str))
    print(equity_and_monthly_png(O, "052: London fade, one trade per day, EURUSD 2021-2024", OUT / "equity_monthly_2021_2024.png"))


if __name__ == "__main__":
    main()
