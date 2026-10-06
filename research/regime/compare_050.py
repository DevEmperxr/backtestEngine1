"""Run 050 — London fade exits: A (046, all out at the middle band) vs B (BE at middle band, run to the
opposite band, out by 08:00 NY) vs C (half off at the middle band + B on the rest). EURUSD 2023."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from lib.evaluate import bootstrap_ci, evaluate, sharpe_all_days
from research.regime.chart_images import equity_and_monthly_png
from research.regime.playbook_stats import streak

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "research" / "runs"
OUT = RUNS / "050_london_fade_runner"
FILES = {"A all out at MA": RUNS / "046_london_fade_standalone" / "main_2023" / "trades.parquet",
         "B runner (BE)": OUT / "b_2023" / "trades.parquet",
         "C half + runner": OUT / "c_2023" / "trades.parquet"}


def sheet(t: pl.DataFrame) -> dict:
    from datetime import date
    t = t.sort("exit_time")
    s = evaluate(t)["summary"]
    ci = bootstrap_ci(t, seed=0)["expectancy_pips"]
    eq = t["pips"].cum_sum()
    m = t.group_by(pl.col("exit_time").dt.month()).agg(p=pl.col("pips").sum())
    p = t.sort("pips", descending=True)["pips"]
    er = dict(t.group_by("exit_reason").len().iter_rows())
    return {
        "trades": t.height, "net_pips": round(s["total_pips"], 1), "per_trade": round(s["expectancy_pips"], 2),
        "per_trade_ci95": [round(ci["ci_low"], 2), round(ci["ci_high"], 2)],
        "win_rate_%": round(s["win_rate"], 1), "profit_factor": round(s["profit_factor"], 2),
        "max_dd_pips": round((eq - eq.cum_max().clip(lower_bound=0)).min(), 1),
        "max_losing_streak": streak(t["pips"].to_list()),
        "months_positive": f"{int((m['p'] > 0).sum())}/12",
        "fair_sharpe": round(sharpe_all_days(t, date(2023, 1, 2), date(2023, 12, 29))["sharpe"], 2),
        "H1 / H2": [round(t.filter(pl.col("entry_time").dt.month() <= 6)["pips"].sum(), 1),
                    round(t.filter(pl.col("entry_time").dt.month() > 6)["pips"].sum(), 1)],
        "without best 10": round(p.sum() - p.head(10).sum(), 1),
        "median_hold_min": round(((t["exit_time"] - t["entry_time"]).dt.total_seconds() / 60).median()),
        "exits tp/be/sl/time": [er.get("tp", 0), er.get("breakeven", 0), er.get("sl", 0), er.get("exit_signal", 0)],
    }


def main() -> None:
    ts = {k: pl.read_parquet(f) for k, f in FILES.items()}
    sh = {k: sheet(t) for k, t in ts.items()}
    print(f"{'':<22}" + "".join(f"{k:>22}" for k in sh))
    for row in next(iter(sh.values())):
        print(f"{row:<22}" + "".join(f"{str(v[row]):>22}" for v in sh.values()))
    # paired with A: what happened to trades that reached the middle band
    a, b = ts["A all out at MA"], ts["B runner (BE)"]
    j = a.join(b, on="entry_time", suffix="_b")
    reached = j.filter(pl.col("exit_reason") == "tp")              # A's winners = price reached the middle band
    after = {
        "same entries A & B": j.height,
        "A winners (reached the middle band)": reached.height,
        "  of those, B went on to the opposite band": int((reached["exit_reason_b"] == "tp").sum()),
        "  of those, B came back to break-even": int((reached["exit_reason_b"] == "breakeven").sum()),
        "  of those, B closed at 08:00 NY": int((reached["exit_reason_b"] == "exit_signal").sum()),
        "  A pips on them / B pips on them": [round(reached["pips"].sum(), 1), round(reached["pips_b"].sum(), 1)],
    }
    for k, v in after.items():
        print(f"{k:<46}{v}")
    (OUT / "comparison.json").write_text(json.dumps({"sheets": sh, "after_middle_band": after}, indent=2, default=str))
    print(equity_and_monthly_png(ts["C half + runner"], "050 C: London fade, half off at the middle band + runner, EURUSD 2023", OUT / "equity_monthly_c_2023.png"))
    print(equity_and_monthly_png(ts["B runner (BE)"], "050 B: London fade, BE at the middle band + runner, EURUSD 2023", OUT / "equity_monthly_b_2023.png"))


if __name__ == "__main__":
    main()
