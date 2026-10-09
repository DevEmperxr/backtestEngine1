"""Run 092 — frozen 079 noise-area rules on NAS100 2021 + 2022 (out-of-sample). Pre-registered in
research/runs/092_nas100_2021_2022/summary.md. Also draws all five years (2021–2025) of the same rules.

    .venv/Scripts/python.exe -m research.regime.nas2122_092
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
RUN = ROOT / "research" / "runs" / "092_nas100_2021_2022"
R089 = ROOT / "research" / "runs" / "089_noise_area_indices"
FILES = {2021: R089 / "nas100_2122_NAS100_2021", 2022: R089 / "nas100_2122_NAS100_2022",
         2023: R089 / "nas100_NAS100_2023", 2024: R089 / "nas100_NAS100_2024", 2025: R089 / "nas100_2025_NAS100_2025"}


def load(y: int) -> pl.DataFrame:
    return pl.read_parquet(FILES[y] / "trades.parquet").with_columns(R=pl.col("pips") / pl.col("sl_pips"))


def long_twin(t: pl.DataFrame) -> float:
    gross = pl.col("pips") + pl.col("spread_pips_paid") + pl.col("commission_pips")
    tw = pl.when(pl.col("direction") == "long").then(pl.col("pips")).otherwise(
        -gross - pl.col("spread_pips_paid") - pl.col("commission_pips")) / pl.col("sl_pips")
    return round(t.select(tw.mean()).item(), 3)


def main() -> None:
    RUN.mkdir(parents=True, exist_ok=True)
    t21, t22 = load(2021), load(2022)
    both = pl.concat([t21, t22]).sort("entry_time")
    res = {"2021": stats(t21), "2022": stats(t22), "both": stats(both),
           "long": stats(both.filter(pl.col("direction") == "long")), "short": stats(both.filter(pl.col("direction") == "short")),
           "gross_R_per_trade": round(both.select(((pl.col("pips") + pl.col("spread_pips_paid") + pl.col("commission_pips"))
                                                   / pl.col("sl_pips")).mean()).item(), 3),
           "always_long_twin": {"2021": long_twin(t21), "2022": long_twin(t22), "both": long_twin(both)},
           "exits": dict(both.group_by("exit_reason").len().iter_rows())}
    for y, t in (("2021", t21), ("2022", t22)):
        res[f"{y}_long"] = stats(t.filter(pl.col("direction") == "long"))
        res[f"{y}_short"] = stats(t.filter(pl.col("direction") == "short"))
    sc = ftmo_1step_scorecard(both, both["entry_time"].min().date(), date(2022, 12, 31), n_sims=1500, seed=4)
    res["ftmo"] = {"strategy": sc["strategy"], "twin": sc["zero_edge_twin"], "beats_twin": sc["beats_twin"]}
    res["PASS"] = bool(res["both"]["R_per_trade"] >= 0.05 and sc["beats_twin"])
    # all five years, same rules
    allt = {y: load(y) for y in FILES}
    res["five_years"] = {str(y): {"trades": t.height, "R_per_trade": round(t["R"].mean(), 3), "R_total": round(t["R"].sum(), 1),
                                  "always_long_twin": long_twin(t)} for y, t in allt.items()}
    five = pl.concat(list(allt.values())).sort("entry_time")
    res["five_years"]["all"] = stats(five)
    for k, v in res.items():
        if k != "ftmo":
            print(k, v)
    print("FTMO 2021-22:", {k: sc["strategy"][k] for k in ("risk_challenge", "pass_%", "EV_net", "days_to_pass")},
          "| twin", {k: sc["zero_edge_twin"][k] for k in ("pass_%", "EV_net")}, "| beats", sc["beats_twin"])
    equity_and_monthly_png(both.with_columns(pips=pl.col("R")), "092 NAS100 noise-area (079 rules, frozen) on 2021–22 — out-of-sample, R after FTMO costs",
                           RUN / "nas100_2021_2022.png")
    fig, ax = plt.subplots(figsize=(13, 5))
    x = five["entry_time"].dt.replace_time_zone(None).to_list()
    ax.plot(x, five["R"].cum_sum().to_list(), lw=1.8, color="#2E6BD8")
    for y in (2022, 2023, 2025):
        ax.axvline(__import__("datetime").datetime(y, 1, 1), color="#888", lw=0.8, ls="--")
    ax.axhline(0, color="#555", lw=0.7)
    ax.text(__import__("datetime").datetime(2021, 3, 1), 2, "2021–22: unseen", fontsize=9)
    ax.text(__import__("datetime").datetime(2023, 3, 1), 2, "2023–24: rules built", fontsize=9)
    ax.text(__import__("datetime").datetime(2025, 2, 1), 2, "2025: unseen", fontsize=9)
    f = res["five_years"]["all"]
    ax.set_title(f"NAS100 noise-area momentum, same rules 2021–2025: {f['trades']} trades, {f['R_per_trade']:+.3f} R/trade, "
                 f"{f['R_total']:+.1f} R total (after FTMO costs)", fontsize=10)
    ax.set_ylabel("cumulative R")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(RUN / "nas100_five_years.png", dpi=110)
    (RUN / "results.json").write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
