"""Run 089 — (1) NAS100 noise-area vs its always-long twin; (2) the same rules on GER40 and JPN225, 2023 + 2024, after
FTMO costs. Pre-registered in research/runs/089_noise_area_indices/summary.md."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import polars as pl  # noqa: E402

from lib.prop_firms import ftmo_1step_scorecard  # noqa: E402
from research.regime.chart_images import equity_and_monthly_png  # noqa: E402
from research.regime.trend_dip_073 import stats  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "research" / "runs" / "089_noise_area_indices"
PAIRS = {"nas100": "NAS100", "ger40": "GER40", "jpn225": "JPN225"}


def load(v: str, y: int) -> pl.DataFrame:
    return pl.read_parquet(RUN / f"{v}_{PAIRS[v]}_{y}" / "trades.parquet").with_columns(R=pl.col("pips") / pl.col("sl_pips"))


def main() -> None:
    res: dict = {}
    # (1) drift check on NAS100
    nas = pl.concat([load("nas100", 2023), load("nas100", 2024)])
    gross = pl.col("pips") + pl.col("spread_pips_paid") + pl.col("commission_pips")
    nas = nas.with_columns(long_twin_pips=pl.when(pl.col("direction") == "long").then(pl.col("pips"))
                           .otherwise(-gross - pl.col("spread_pips_paid") - pl.col("commission_pips")))
    nas = nas.with_columns(long_twin_R=pl.col("long_twin_pips") / pl.col("sl_pips"))
    d = {"strategy_R_per_trade": round(nas["R"].mean(), 3), "always_long_twin_R_per_trade": round(nas["long_twin_R"].mean(), 3)}
    for y in (2023, 2024):
        p = nas.filter(pl.col("entry_time").dt.year() == y)
        d[str(y)] = {"strategy": round(p["R"].mean(), 3), "long_twin": round(p["long_twin_R"].mean(), 3)}
    sh = nas.filter(pl.col("direction") == "short")
    d["short_trades"] = {"n": sh.height, "strategy_R": round(sh["R"].mean(), 3), "long_twin_R": round(sh["long_twin_R"].mean(), 3)}
    d["edge_over_long_twin"] = round(d["strategy_R_per_trade"] - d["always_long_twin_R_per_trade"], 3)
    d["direction_adds_value"] = bool(d["edge_over_long_twin"] >= 0.05 and d["short_trades"]["long_twin_R"] < 0)
    res["nas100_drift_check"] = d
    print("NAS100 drift check:", json.dumps(d))

    # (2) per index
    fig, ax = plt.subplots(figsize=(12, 5))
    for v, pair in PAIRS.items():
        t23, t24 = load(v, 2023), load(v, 2024)
        both = pl.concat([t23, t24]).sort("entry_time")
        r = {"2023": stats(t23), "2024": stats(t24), "both": stats(both),
             "long": stats(both.filter(pl.col("direction") == "long")), "short": stats(both.filter(pl.col("direction") == "short")),
             "gross_R_per_trade": round(((both["pips"] + both["spread_pips_paid"] + both["commission_pips"]) / both["sl_pips"]).mean(), 3),
             "exits": dict(both.group_by("exit_reason").len().iter_rows())}
        sc = ftmo_1step_scorecard(both, both["entry_time"].min().date(), date(2024, 12, 31), n_sims=1500, seed=4)
        r["ftmo"] = {"strategy": {k: sc["strategy"][k] for k in ("risk_challenge", "pass_%", "EV_net", "days_to_pass")},
                     "twin": {k: sc["zero_edge_twin"][k] for k in ("pass_%", "EV_net")}, "beats_twin": sc["beats_twin"]}
        r["candidate"] = bool(r["2023"]["R_per_trade"] > 0 and r["2024"]["R_per_trade"] > 0 and r["both"]["R_per_trade"] >= 0.05
                              and sc["beats_twin"])
        res[pair] = r
        print(f"\n== {pair}")
        for k in ("2023", "2024", "both", "long", "short"):
            print(f"  {k:<5}", r[k])
        print("  gross R/trade", r["gross_R_per_trade"], "| exits", r["exits"], "| FTMO", r["ftmo"], "| candidate", r["candidate"])
        equity_and_monthly_png(both.with_columns(pips=pl.col("R")), f"089 noise-area momentum on {pair}, 2023–24, R after FTMO costs",
                               RUN / f"{v}_equity.png")
        ax.plot(both["exit_time"].dt.replace_time_zone(None).to_list(), both["R"].cum_sum().to_list(), label=pair, lw=1.6)
    ax.axhline(0, color="#555", lw=0.7)
    ax.set_ylabel("cumulative R after FTMO costs")
    ax.set_title("089 noise-area momentum, same rules on three indices, 2023–24", fontsize=10)
    ax.legend()
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(RUN / "three_indices.png", dpi=110)
    (RUN / "results.json").write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
