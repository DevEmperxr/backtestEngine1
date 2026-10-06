"""Run 053 — London fade 046 (1h/5m/1m) vs 053 (4h/15m/5m), EURUSD 2023."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from research.regime.chart_images import equity_and_monthly_png
from research.regime.compare_047 import sheet

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "runs" / "053_london_fade_higher_tf"


def main() -> None:
    a, b = sheet("046_london_fade_standalone"), sheet("053_london_fade_higher_tf")
    print(f"{'':<24}{'046 1h/5m/1m':>22}{'053 4h/15m/5m':>22}")
    for k in a:
        print(f"{k:<24}{str(a[k]):>22}{str(b[k]):>22}")
    (OUT / "comparison.json").write_text(json.dumps({"046": a, "053": b}, indent=2, default=str))
    t = pl.read_parquet(OUT / "main_2023" / "trades.parquet")
    print(equity_and_monthly_png(t, "053: London fade on 4h / 15m / 5m, EURUSD 2023", OUT / "equity_monthly_2023.png"))


if __name__ == "__main__":
    main()
