"""Run 075 — gold results: per idea and year after FTMO costs, long vs short, the drift check, and the FTMO 1-step
scorecard. Pre-registered in research/runs/075_gold_trend_bias/summary.md (from 2023-03-14)."""

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
RUN = ROOT / "research" / "runs" / "075_gold_trend_bias"
START = date(2023, 3, 14)
NAMES = {"g1": "G1 RSI(2) dip in trend", "g2": "G2 20-hour breakout in trend", "drift": "drift check (with-trend at 08:00 London)"}


def load(v: str, y: int) -> pl.DataFrame:
    t = pl.read_parquet(RUN / f"{v}_XAUUSD_{y}" / "trades.parquet").with_columns(R=pl.col("pips") / pl.col("sl_pips"))
    return t.filter(pl.col("entry_time").dt.date() >= START) if y == 2023 else t


def main() -> None:
    res = {}
    fig, ax = plt.subplots(figsize=(12, 5))
    for v, name in NAMES.items():
        both = pl.concat([load(v, 2023), load(v, 2024)])
        r = {str(y): stats(load(v, y)) for y in (2023, 2024)}
        r["both"] = stats(both)
        r["long"] = stats(both.filter(pl.col("direction") == "long"))
        r["short"] = stats(both.filter(pl.col("direction") == "short"))
        r["gross_R_per_trade"] = round(((both["pips"] + both["spread_pips_paid"] + both["commission_pips"]) / both["sl_pips"]).mean(), 3)
        if v != "drift":
            sc = ftmo_1step_scorecard(both, START, date(2024, 12, 31), n_sims=1500, seed=4)
            r["scorecard"] = {"strategy": sc["strategy"], "zero_edge_twin": sc["zero_edge_twin"], "beats_twin": sc["beats_twin"]}
        res[v] = r
        print(f"\n== {name}\n   2023 {r['2023']}\n   2024 {r['2024']}\n   both {r['both']}\n   long {r['long']}\n   short {r['short']}"
              f"\n   gross R/trade (before costs) {r['gross_R_per_trade']}")
        if v != "drift":
            s, z = r["scorecard"]["strategy"], r["scorecard"]["zero_edge_twin"]
            print(f"   FTMO 1-step: pass {s['pass_%']}% EV ${s['EV_net']} | twin pass {z['pass_%']}% EV ${z['EV_net']}")
        t = both.sort("exit_time")
        ax.plot(t["exit_time"].dt.replace_time_zone(None).to_list(), t["R"].cum_sum().to_list(), label=name, lw=1.6)
    for v in ("g1", "g2"):
        r = res[v]
        r["candidate"] = bool(r["2023"]["R_per_trade"] > 0 and r["2024"]["R_per_trade"] > 0 and r["both"]["R_per_trade"] >= 0.05
                              and r["both"]["R_per_trade"] > res["drift"]["both"]["R_per_trade"] and r["scorecard"]["beats_twin"])
    print("\ncandidates:", [NAMES[v] for v in ("g1", "g2") if res[v]["candidate"]] or "none")
    ax.axhline(0, color="#555", lw=0.7)
    ax.set_ylabel("cumulative R (after FTMO costs)")
    ax.set_title("075 gold (XAUUSD), daily-trend bias, Mar 2023 – Dec 2024", fontsize=10)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(RUN / "gold_equity.png", dpi=110)
    (RUN / "results.json").write_text(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()
