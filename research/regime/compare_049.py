"""Run 049 — London fade: 046 (ATR stop, MA target) vs 048 (sweep+3, MA target) vs 049 (sweep+3, BE 2R, TP 4R), 2023."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from research.regime.chart_images import equity_and_monthly_png
from research.regime.compare_047 import sheet

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "research" / "runs"
OUT = RUNS / "049_london_fade_be2r_tp4r"
RUNS3 = {"046 ATR/MA": "046_london_fade_standalone", "048 sweep+3/MA": "048_london_fade_sweep_stop",
         "049 sweep+3/BE2R/4R": "049_london_fade_be2r_tp4r"}


def main() -> None:
    sh = {k: sheet(v) for k, v in RUNS3.items()}
    for k in sh.values():
        k.pop("target_first_%"), k.pop("chance_target_first_%")   # simple bracket null doesn't apply with BE
    ts = {k: pl.read_parquet(RUNS / v / "main_2023" / "trades.parquet") for k, v in RUNS3.items()}
    for k, t in ts.items():
        p = t.sort("pips", descending=True)["pips"]
        sh[k]["without best 5"] = round(p.sum() - p.head(5).sum(), 1)
        sh[k]["without best 10"] = round(p.sum() - p.head(10).sum(), 1)
        er = dict(t.group_by("exit_reason").len().iter_rows())
        sh[k]["exits tp/be/sl/time"] = [er.get("tp", 0), er.get("breakeven", 0), er.get("sl", 0), er.get("exit_signal", 0)]
        sh[k]["avg R"] = round((t["pips"] / t["sl_pips"]).mean(), 2)
    print(f"{'':<24}" + "".join(f"{k:>24}" for k in sh))
    for row in next(iter(sh.values())):
        print(f"{row:<24}" + "".join(f"{str(v[row]):>24}" for v in sh.values()))
    t9 = ts["049 sweep+3/BE2R/4R"]
    r = (t9["pips"] / t9["sl_pips"])
    dist = {"R <= -1 (full stop)": int((r <= -0.9).sum()), "around 0 (BE / small time exit)": int(((r > -0.9) & (r < 0.5)).sum()),
            "0.5R .. 3.5R (time exit in profit)": int(((r >= 0.5) & (r < 3.5)).sum()), ">= 3.5R (target)": int((r >= 3.5).sum())}
    print("049 R buckets:", dist)
    # same entries as 048: what did BE + 4R do to them
    t8 = ts["048 sweep+3/MA"]
    j = t8.join(t9, on="entry_time", suffix="_9")
    print(f"same entries 048 & 049: {j.height}, 048 {j['pips'].sum():+.1f} -> 049 {j['pips_9'].sum():+.1f}")
    (OUT / "comparison.json").write_text(json.dumps({"sheets": sh, "r_buckets_049": dist}, indent=2, default=str))
    print(equity_and_monthly_png(t9, "049: London fade, sweep+3 stop, BE at 2R, TP 4R, EURUSD 2023", OUT / "equity_monthly_2023.png"))


if __name__ == "__main__":
    main()
