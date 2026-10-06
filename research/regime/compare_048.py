"""Run 048 — London fade: 1.5 x ATR stop (046) vs sweep candle + 3 pips (048), EURUSD 2023."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from research.regime.chart_images import equity_and_monthly_png
from research.regime.compare_047 import sheet

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "research" / "runs"
OUT = RUNS / "048_london_fade_sweep_stop"


def main() -> None:
    a, b = sheet("046_london_fade_standalone"), sheet("048_london_fade_sweep_stop")
    print(f"{'':<24}{'ATR stop (046)':>22}{'sweep+3 stop (048)':>22}")
    for k in a:
        print(f"{k:<24}{str(a[k]):>22}{str(b[k]):>22}")
    t6 = pl.read_parquet(RUNS / "046_london_fade_standalone" / "main_2023" / "trades.parquet")
    t8 = pl.read_parquet(RUNS / "048_london_fade_sweep_stop" / "main_2023" / "trades.parquet")
    both = t6.join(t8, on="entry_time", suffix="_8")
    tighter = both.filter(pl.col("sl_pips_8") < pl.col("sl_pips"))
    flips = both.filter((pl.col("pips") > 0) & (pl.col("pips_8") < 0))
    saves = both.filter((pl.col("pips") < 0) & (pl.col("pips_8") > 0))
    stops = t8["sl_pips"]
    extra = {
        "same entries in both": both.height,
        "  046 pips / 048 pips on them": [round(both["pips"].sum(), 1), round(both["pips_8"].sum(), 1)],
        "  048 stop tighter than 046 on": f"{tighter.height}/{both.height}",
        "  winners in 046 stopped out in 048": f"{flips.height} ({flips['pips'].sum():+.1f} -> {flips['pips_8'].sum():+.1f})",
        "  losers in 046 that win in 048": f"{saves.height} ({saves['pips'].sum():+.1f} -> {saves['pips_8'].sum():+.1f})",
        "048 stop size p10/p50/p90": [round(stops.quantile(q), 1) for q in (0.1, 0.5, 0.9)],
        "046 stop size p10/p50/p90": [round(t6["sl_pips"].quantile(q), 1) for q in (0.1, 0.5, 0.9)],
    }
    for k, v in extra.items():
        print(f"{k:<40}{v}")
    (OUT / "comparison.json").write_text(json.dumps({"atr_046": a, "sweep3_048": b, "paired": extra}, indent=2, default=str))
    print(equity_and_monthly_png(t8, "048: London fade, stop = sweep candle + 3 pips, EURUSD 2023", OUT / "equity_monthly_2023.png"))


if __name__ == "__main__":
    main()
