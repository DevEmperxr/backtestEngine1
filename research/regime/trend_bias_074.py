"""Run 074 — daily-trend bias + three POIs: per-year results after FTMO costs and the FTMO 1-step scorecard.
Pre-registered in research/runs/074_trend_bias_pois/summary.md (2023 from 2023-03-13 for every variant).
"""

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
RUN = ROOT / "research" / "runs" / "074_trend_bias_pois"
START = date(2023, 3, 13)
NAMES = {"p1": "P1 pullback to 1h SMA20", "p2": "P2 20-hour breakout", "p3": "P3 previous-day break"}


def load(v: str, y: int) -> pl.DataFrame:
    t = pl.read_parquet(RUN / f"{v}_{y}" / "trades.parquet").with_columns(R=pl.col("pips") / pl.col("sl_pips"))
    return t.filter(pl.col("entry_time").dt.date() >= START) if y == 2023 else t


def main() -> None:
    res = {}
    fig, ax = plt.subplots(figsize=(12, 5))
    for v, name in NAMES.items():
        r = {str(y): stats(load(v, y)) for y in (2023, 2024)}
        both = pl.concat([load(v, 2023), load(v, 2024)])
        r["both"] = stats(both)
        sc = ftmo_1step_scorecard(both, START, date(2024, 12, 31), n_sims=1500, seed=4)
        r["scorecard"] = sc
        cand = (r["2023"]["R_per_trade"] > 0 and r["2024"]["R_per_trade"] > 0 and r["both"]["R_per_trade"] >= 0.05
                and sc["beats_twin"])
        r["candidate"] = cand
        r["strong"] = bool(cand and r["both"]["R_ci95"][0] > 0)
        res[v] = r
        s, z = sc["strategy"], sc["zero_edge_twin"]
        print(f"\n== {name}\n   2023 {r['2023']}\n   2024 {r['2024']}\n   both {r['both']}")
        print(f"   FTMO 1-step: pass {s['pass_%']}% EV ${s['EV_net']} (risk {s['risk_challenge']}/{s['risk_funded']}) "
              f"trades to pass {s['trades_to_pass']} to profit {s['trades_to_profit']} | twin pass {z['pass_%']}% EV ${z['EV_net']}"
              f" | CANDIDATE {cand}")
        t = both.sort("exit_time")
        ax.plot(t["exit_time"].dt.replace_time_zone(None).to_list(), t["R"].cum_sum().to_list(), label=name, lw=1.6)
        equity_and_monthly_png(both.with_columns(pips=pl.col("R")), f"074 {name} + daily-trend bias, EURUSD (in R)",
                               RUN / f"equity_R_{v}.png")
    ax.axhline(0, color="#555", lw=0.7)
    ax.set_ylabel("cumulative R (after all FTMO costs)")
    ax.set_title("074: daily-trend bias with three POIs, EURUSD Mar 2023 – Dec 2024", fontsize=10)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(RUN / "pois_equity.png", dpi=110)
    (RUN / "results.json").write_text(json.dumps(res, indent=2, default=str))
    print("\ncandidates:", [NAMES[v] for v, r in res.items() if r["candidate"]] or "none")


if __name__ == "__main__":
    main()
