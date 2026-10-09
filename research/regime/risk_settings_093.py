"""Run 093 — FTMO 1-step risk settings for the NAS100 noise-area strategy (pre-registered in
research/runs/093_nas100_risk_settings/summary.md).

    .venv/Scripts/python.exe -m research.regime.risk_settings_093
"""

from __future__ import annotations

import json
from datetime import date
from itertools import product
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402

from lib.prop import daily_R  # noqa: E402
from lib.prop_firms import FTMO_1STEP, simulate_firm  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "runs" / "093_nas100_risk_settings"
R089 = ROOT / "research" / "runs" / "089_noise_area_indices"
FILES = {2021: "nas100_2122_NAS100_2021", 2022: "nas100_2122_NAS100_2022", 2023: "nas100_NAS100_2023",
         2024: "nas100_NAS100_2024", 2025: "nas100_2025_NAS100_2025"}
CH = [0.5, 0.75, 1.0, 1.5, 2.0]
FU = [0.25, 0.5, 0.75, 1.0]
STOPS = [1.2, 2.0, None]
N = 2000


def year_days(y: int) -> list[list[float]]:
    t = pl.read_parquet(R089 / FILES[y] / "trades.parquet")
    return daily_R(t, date(y, 1, 1), date(y, 12, 31))


def twin(days: list[list[float]]) -> list[list[float]]:
    mu = float(np.mean([r for d in days for r in d]))
    return [[r - mu for r in d] for d in days]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    yd = {y: year_days(y) for y in FILES}
    pooled = [d for y in FILES for d in yd[y]]
    rows = []
    for ch, fu, ds in product(CH, FU, STOPS):
        s = simulate_firm(pooled, FTMO_1STEP, risk_challenge=ch, risk_funded=fu, day_stop=ds, n_sims=N, seed=1)
        per_year = {y: simulate_firm(yd[y], FTMO_1STEP, risk_challenge=ch, risk_funded=fu, day_stop=ds, n_sims=N // 2, seed=2)["EV_net"]
                    for y in FILES}
        rows.append({"challenge_%": ch, "funded_%": fu, "day_stop_%": ds if ds else "3 (FTMO)", "pass_%": s["pass_%"],
                     "EV_net": s["EV_net"], "P(net>0)_%": s["P(net>0)_%"], "days_to_pass": s["days_to_pass"],
                     "days_to_first_payout": s["days_to_first_payout"],
                     **{f"EV_{y}": per_year[y] for y in FILES}, "worst_year_EV": min(per_year.values())})
        print(f"ch {ch:<4} fu {fu:<4} stop {str(ds):<4} | pass {s['pass_%']:>5}% EV ${s['EV_net']:>7} P>0 {s['P(net>0)_%']:>5}% "
              f"days {s['days_to_pass']} | worst year ${min(per_year.values()):>7}", flush=True)
    t = pl.DataFrame(rows).sort("EV_net", descending=True)
    t.write_csv(OUT / "grid.csv")
    ok = t.filter(pl.col("worst_year_EV") > 0)
    best = ok.row(0, named=True)
    close = ok.filter(pl.col("EV_net") >= 0.95 * best["EV_net"]).sort(["challenge_%", "funded_%"])
    pick = close.row(0, named=True)
    ds = None if isinstance(pick["day_stop_%"], str) else pick["day_stop_%"]
    tw = simulate_firm(twin(pooled), FTMO_1STEP, risk_challenge=pick["challenge_%"], risk_funded=pick["funded_%"], day_stop=ds, n_sims=N, seed=1)
    res = {"options": t.height, "options_positive_every_year": ok.height, "best_by_EV": best, "within_5pct": close.to_dicts(),
           "PICK": pick, "pick_zero_edge_twin": {k: tw[k] for k in ("pass_%", "EV_net", "P(net>0)_%", "days_to_pass")}}
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str))
    print("\nbest by EV (positive every year):", best)
    print("within 5% (lowest risk first):")
    for r in close.to_dicts():
        print("  ", r)
    print("\nPICK:", pick)
    print("zero-edge twin at the pick:", res["pick_zero_edge_twin"])

    # chart: EV by challenge x funded risk at the picked day stop, and per-year EV of the pick
    sub = t.filter(pl.col("day_stop_%").cast(pl.Utf8) == str(pick["day_stop_%"]))
    M = np.array([[sub.filter((pl.col("challenge_%") == c) & (pl.col("funded_%") == f))["EV_net"][0] for f in FU] for c in CH])
    fig, ax = plt.subplots(1, 2, figsize=(14, 5))
    im = ax[0].imshow(M, cmap="Greens", aspect="auto")
    ax[0].set_xticks(range(len(FU)), [f"{f}%" for f in FU])
    ax[0].set_yticks(range(len(CH)), [f"{c}%" for c in CH])
    ax[0].set_xlabel("funded risk per trade")
    ax[0].set_ylabel("challenge risk per trade")
    for i in range(len(CH)):
        for j in range(len(FU)):
            ax[0].text(j, i, f"${M[i, j]:,.0f}", ha="center", va="center", fontsize=8)
    ax[0].set_title(f"expected $ per $89 attempt, 2021–25 (own daily stop {pick['day_stop_%']}%)", fontsize=10)
    ys = list(FILES)
    ax[1].bar([str(y) for y in ys], [pick[f"EV_{y}"] for y in ys], color="#2E6BD8")
    ax[1].axhline(0, color="#555", lw=0.7)
    ax[1].set_title(f"picked setting (challenge {pick['challenge_%']}%, funded {pick['funded_%']}%): expected $ per attempt by year",
                    fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "risk_settings.png", dpi=110)


if __name__ == "__main__":
    main()
