"""Run 073 — layer-by-layer results of the RSI(2) trend-dip strategy and the FTMO 1-step scorecard of the kept version.
Pre-registered in research/runs/073_trend_dip_rsi2/summary.md (2023 compared from 2023-04-13 on for every variant).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import polars as pl  # noqa: E402

from lib.evaluate import bootstrap_ci  # noqa: E402
from lib.prop_firms import ftmo_1step_scorecard  # noqa: E402
from research.regime.chart_images import equity_and_monthly_png  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "research" / "runs" / "073_trend_dip_rsi2"
START_2023 = date(2023, 4, 13)
NAMES = {"a": "A POI only", "b": "B +bias", "bp": "B' +context", "c": "C +bias +context",
         "d": "D +bias +context +confirm", "dp": "D' +bias +confirm", "dpp": "D'' +confirm"}


def load(v: str, y: int) -> pl.DataFrame:
    t = pl.read_parquet(RUN / f"{v}_{y}" / "trades.parquet").with_columns(R=pl.col("pips") / pl.col("sl_pips"))
    if y == 2023:
        t = t.filter(pl.col("entry_time").dt.date() >= START_2023)
    return t


def stats(t: pl.DataFrame) -> dict:
    if t.height < 3:
        return {"trades": t.height, "R_per_trade": None}
    ci = bootstrap_ci(t.with_columns(pips=pl.col("R")), seed=0)["expectancy_pips"]
    return {"trades": t.height, "R_per_trade": round(t["R"].mean(), 3), "R_total": round(t["R"].sum(), 1),
            "R_ci95": [round(ci["ci_low"], 3), round(ci["ci_high"], 3)], "win_%": round(100 * (t["pips"] > 0).mean(), 1),
            "net_pips": round(t["pips"].sum(), 1), "median_stop": round(t["sl_pips"].median(), 1),
            "costs_R": round(((t["spread_pips_paid"] + t["commission_pips"]) / t["sl_pips"]).mean(), 3)}


def better(new: dict, old: dict) -> bool:
    return all(new[y]["R_per_trade"] is not None and old[y]["R_per_trade"] is not None
               and new[y]["R_per_trade"] > old[y]["R_per_trade"] for y in ("2023", "2024"))


def main() -> None:
    res = {v: {str(y): stats(load(v, y)) for y in (2023, 2024)} for v in NAMES}
    for v, name in NAMES.items():
        r = res[v]
        print(f"{name:<28} 2023 (from Apr 13) {r['2023']}\n{'':<28} 2024 {r['2024']}")
    # pre-registered walk: bias -> context -> confirmation
    path, cur = ["a"], "a"
    log = []
    step_bias = "b"
    if better(res[step_bias], res[cur]):
        cur = step_bias; log.append("bias KEPT")
    else:
        log.append("bias DROPPED")
    nxt_ctx = "c" if cur == "b" else "bp"
    if better(res[nxt_ctx], res[cur]):
        cur = nxt_ctx; log.append("context KEPT")
    else:
        log.append("context DROPPED")
    nxt_conf = {"c": "d", "b": "dp", "a": "dpp", "bp": None}[cur]
    if nxt_conf and better(res[nxt_conf], res[cur]):
        cur = nxt_conf; log.append("confirmation KEPT")
    else:
        log.append("confirmation DROPPED" if nxt_conf else "confirmation: no pre-declared branch")
    print("\nlayer walk:", log, "-> final version:", NAMES[cur])

    final = pl.concat([load(cur, 2023), load(cur, 2024)])
    sc = ftmo_1step_scorecard(final, START_2023, date(2024, 12, 31), n_sims=1500, seed=4)
    print("FTMO 1-step scorecard:", json.dumps(sc, indent=1, default=str))
    cand = (res[cur]["2023"]["R_per_trade"] > 0 and res[cur]["2024"]["R_per_trade"] > 0 and sc["beats_twin"])
    out = {"variants": res, "layer_walk": log, "final": cur, "scorecard": sc, "candidate": cand}
    (RUN / "results.json").write_text(json.dumps(out, indent=2, default=str))
    print("CANDIDATE:", cand)
    equity_and_monthly_png(final.with_columns(pips=pl.col("R")), f"073 trend-dip RSI(2), final version {NAMES[cur]}, EURUSD (in R)",
                           RUN / "equity_R_final.png")
    fig, ax = plt.subplots(figsize=(12, 5))
    for v, name in NAMES.items():
        t = pl.concat([load(v, 2023), load(v, 2024)]).sort("exit_time")
        ax.plot(t["exit_time"].dt.replace_time_zone(None).to_list(), t["R"].cum_sum().to_list(), label=name,
                lw=2.4 if v == cur else 1.1)
    ax.axhline(0, color="#555", lw=0.7)
    ax.set_ylabel("cumulative R (after all FTMO costs)")
    ax.set_title("073 layer by layer: each version's equity, EURUSD Apr 2023 – Dec 2024 (thick = final kept version)", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(RUN / "layers_equity.png", dpi=110)


if __name__ == "__main__":
    main()
