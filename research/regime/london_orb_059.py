"""Run 059 — results for the London-open breakout: NR7 days vs every day (control), per pair / year, in pips
and in R (pips / stop = equal risk per trade). Primary = EURUSD + GBPUSD pooled.
Pre-registration: research/runs/059_london_orb_nr7/summary.md.
"""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from lib.evaluate import bootstrap_ci
from research.regime.chart_images import equity_and_monthly_png

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "research" / "runs" / "059_london_orb_nr7"
PAIRS, YEARS, VARIANTS = ("EURUSD", "GBPUSD", "AUDUSD"), (2023, 2024), ("main", "all")


def path(variant: str, pair: str, y: int) -> Path:
    if pair == "EURUSD":
        if variant == "main":
            return (RUN if y == 2024 else RUN / f"main_{y}") / "trades.parquet"
        return RUN / f"{variant}_{y}" / "trades.parquet"
    return RUN / f"{variant}_{pair}_{y}" / "trades.parquet"


def load(variant: str, pair: str, y: int) -> pl.DataFrame:
    return pl.read_parquet(path(variant, pair, y)).with_columns(
        R=pl.col("pips") / pl.col("sl_pips"), pair=pl.lit(pair), year=pl.lit(y))


def stats(t: pl.DataFrame) -> dict:
    if t.height == 0:
        return {"trades": 0}
    ci = bootstrap_ci(t.with_columns(pips=pl.col("R")), seed=0)["expectancy_pips"]
    er = dict(t.group_by("exit_reason").len().iter_rows())
    eqR = t.sort("exit_time")["R"].cum_sum()
    return {"trades": t.height, "net_pips": round(t["pips"].sum(), 1),
            "gross_pips": round((t["pips"] + t["spread_pips_paid"]).sum(), 1),
            "R_total": round(t["R"].sum(), 2), "R_per_trade": round(t["R"].mean(), 3),
            "R_ci95": [round(ci["ci_low"], 3), round(ci["ci_high"], 3)],
            "win_%": round(100 * (t["pips"] > 0).mean(), 1), "median_stop": round(t["sl_pips"].median(), 1),
            "spread_in_R": round((t["spread_pips_paid"] / t["sl_pips"]).mean(), 3),
            "max_dd_R": round((eqR - eqR.cum_max().clip(lower_bound=0)).min(), 2),
            "exits sl/time/news/tp": [er.get("sl", 0), er.get("exit_signal", 0) - 0, 0, er.get("tp", 0)]}


def main() -> None:
    T = {(v, p, y): load(v, p, y) for v in VARIANTS for p in PAIRS for y in YEARS}
    res: dict = {}
    print(f"{'':<28}{'NR7 (test)':>70}{'every day (control)':>70}")
    for p in PAIRS:
        for y in YEARS:
            a, c = stats(T[("main", p, y)]), stats(T[("all", p, y)])
            res[f"{p} {y}"] = {"NR7": a, "all": c}
            f = lambda d: f"{d['trades']} tr, {d['net_pips']:+.0f} pips, R {d['R_total']:+.1f} ({d['R_per_trade']:+.3f}/tr), win {d['win_%']}%"
            print(f"{p + ' ' + str(y):<28}{f(a):>70}{f(c):>70}")
    for label, pairs in (("PRIMARY EURUSD+GBPUSD", ("EURUSD", "GBPUSD")), ("AUDUSD", ("AUDUSD",)),
                         ("ALL THREE", PAIRS)):
        for v, name in (("main", "NR7"), ("all", "all")):
            by_year = {str(y): stats(pl.concat([T[(v, p, y)] for p in pairs])) for y in YEARS}
            both = stats(pl.concat([T[(v, p, y)] for p in pairs for y in YEARS]))
            res[f"{label} {name}"] = {"by_year": by_year, "2023+2024": both}
            print(f"\n{label} {name}: 2023 R {by_year['2023']['R_total']:+.2f} | 2024 R {by_year['2024']['R_total']:+.2f} | both {both}")
    prim = res["PRIMARY EURUSD+GBPUSD NR7"]
    ctrl = res["PRIMARY EURUSD+GBPUSD all"]
    passed = (prim["by_year"]["2023"]["R_total"] > 0 and prim["by_year"]["2024"]["R_total"] > 0
              and prim["2023+2024"]["R_per_trade"] > ctrl["2023+2024"]["R_per_trade"])
    strong = passed and prim["2023+2024"]["R_ci95"][0] > 0
    res["VERDICT"] = "STRONG PASS" if strong else ("PASS" if passed else "FAIL")
    print("\nVERDICT:", res["VERDICT"])
    (RUN / "results.json").write_text(json.dumps(res, indent=2, default=str))
    for v, name in (("main", "NR7 days"), ("all", "every day")):
        t = pl.concat([T[(v, p, y)] for p in ("EURUSD", "GBPUSD") for y in YEARS]).with_columns(pips=pl.col("R"))
        print(equity_and_monthly_png(t, f"059 London-open breakout, {name}, EURUSD+GBPUSD 2023+2024 (in R = equal risk)",
                                     RUN / f"equity_monthly_R_{'nr7' if v == 'main' else 'all'}.png"))


if __name__ == "__main__":
    main()
