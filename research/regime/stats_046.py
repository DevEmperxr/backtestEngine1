"""Run 046 — full stat sheet, robustness slices and charts for the standalone London fade, 2023+2024."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import polars as pl  # noqa: E402

from research.regime.chart_images import equity_and_monthly_png  # noqa: E402
from research.regime.compare_044 import tagged  # noqa: E402
from research.regime.playbook_stats import stats  # noqa: E402
from lib.evaluate import bootstrap_ci  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "runs" / "046_london_fade_standalone"


def net(x: pl.DataFrame) -> str:
    if x.height == 0:
        return "n=0"
    return f"n={x.height}, {x['pips'].sum():+.1f} pips, {x['pips'].mean():+.2f}/trade"


def main(scratch: Path) -> None:
    t = tagged("046_london_fade_standalone", "046_london_fade_standalone", scratch)
    s = stats(t)
    ci = bootstrap_ci(t, seed=0)["expectancy_pips"]
    s["per_trade_ci95"] = [round(ci["ci_low"], 2), round(ci["ci_high"], 2)]
    for k, v in s.items():
        print(f"{k:<24}{v}")
    ny = pl.col("entry_time").dt.convert_time_zone("America/New_York")
    q = (pl.col("entry_time").dt.year().cast(pl.Utf8) + "-Q" + pl.col("entry_time").dt.quarter().cast(pl.Utf8))
    t = t.with_columns(quarter=q, hour=ny.dt.hour())
    slices = {
        "2023": net(t.filter(pl.col("entry_time").dt.year() == 2023)),
        "2024": net(t.filter(pl.col("entry_time").dt.year() == 2024)),
        **{f"quarter {k}": net(t.filter(pl.col("quarter") == k)) for k in sorted(t["quarter"].unique())},
        "long": net(t.filter(pl.col("direction") == "long")),
        "short": net(t.filter(pl.col("direction") == "short")),
        "entry 03:xx NY": net(t.filter(pl.col("hour") == 3)),
        "entry 04:xx NY": net(t.filter(pl.col("hour") == 4)),
        "without best 5": f"{t.sort('pips')['pips'].head(t.height - 5).sum():+.1f}",
        "without best 10": f"{t.sort('pips')['pips'].head(t.height - 10).sum():+.1f}",
        "2024 without its best 5": f"{t.filter(pl.col('entry_time').dt.year() == 2024).sort('pips')['pips'].head(-5).sum():+.1f}",
        "costs x2 (extra spread)": f"{(t['pips'] - t['spread_pips_paid']).sum():+.1f}",
    }
    print()
    for k, v in slices.items():
        print(f"{k:<26}{v}")
    (OUT / "stats.json").write_text(json.dumps({"stats": s, "slices": slices}, indent=2, default=str))
    t.write_parquet(OUT / "trades_2023_2024.parquet")
    print(equity_and_monthly_png(t, "046: London-open sideways fade alone (news blackout on), EURUSD 2023+2024", OUT / "equity_monthly_2023_2024.png"))

    fig, ax = plt.subplots(1, 3, figsize=(15, 4.3))
    ax[0].hist(t["r"].clip(-2, 4).to_list(), bins=30, color="#E8A33D")
    ax[0].axvline(0, color="#555", lw=0.8)
    ax[0].set_title("result per trade in R (1R = stop distance)")
    ax[1].hist(t["hold_min"].clip(upper_bound=240).to_list(), bins=40, color="#4E79A7")
    ax[1].set_title("holding time (minutes, capped at 240)")
    qs = sorted(t["quarter"].unique())
    v = [t.filter(pl.col("quarter") == k)["pips"].sum() for k in qs]
    ax[2].bar(qs, v, color=["#2E9E5B" if x > 0 else "#D84A2E" for x in v])
    ax[2].axhline(0, color="#555", lw=0.8)
    ax[2].set_title("pips per quarter")
    ax[2].tick_params(axis="x", rotation=45)
    for a in ax:
        a.grid(alpha=0.25)
    fig.suptitle("046 London fade: trade shapes", fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT / "trade_shapes.png", dpi=110)


if __name__ == "__main__":
    import sys
    main(Path(sys.argv[1]))
