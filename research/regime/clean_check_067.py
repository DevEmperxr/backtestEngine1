"""Runs 067 + 068 — (067) the London fade under FTMO rules on unseen EURUSD 2025 (+ 2021–22 context), and
(068) the value of one paid FTMO attempt (challenge + a year funded) across risk settings, for the in-sample
trades (2023–24), the clean 2025 trades, and the zero-edge twin.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402

from lib.evaluate import bootstrap_ci  # noqa: E402
from lib.prop import simulate_challenge, simulate_lifecycle  # noqa: E402
from research.regime.chart_images import equity_and_monthly_png  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "research" / "runs" / "066_ftmo_reruns"
OUT7 = ROOT / "research" / "runs" / "067_clean_check_london_fade_ftmo"
OUT8 = ROOT / "research" / "runs" / "068_prop_attempt_value"
CAL_END = date(2025, 4, 7)


def load(y: int) -> pl.DataFrame:
    return pl.read_parquet(SRC / f"london_fade_{y}" / "trades.parquet").with_columns(R=pl.col("pips") / pl.col("sl_pips"))


def stats(t: pl.DataFrame) -> dict:
    ci = bootstrap_ci(t.with_columns(pips=pl.col("R")), seed=0)["expectancy_pips"]
    return {"trades": t.height, "net_pips": round(t["pips"].sum(), 1), "R_total": round(t["R"].sum(), 1),
            "R_per_trade": round(t["R"].mean(), 3), "R_ci95": [round(ci["ci_low"], 3), round(ci["ci_high"], 3)],
            "gross_pips": round((t["pips"] + t["spread_pips_paid"] + t["commission_pips"]).sum(), 1),
            "win_%": round(100 * (t["pips"] > 0).mean(), 1)}


def main() -> None:
    OUT7.mkdir(parents=True, exist_ok=True)
    OUT8.mkdir(parents=True, exist_ok=True)
    T = {y: load(y) for y in (2021, 2022, 2023, 2024, 2025)}
    r7 = {str(y): stats(t) for y, t in T.items()}
    early = T[2025].filter(pl.col("entry_time").dt.date() <= CAL_END)
    r7["2025 Jan 1 – Apr 7 (news filter complete)"] = stats(early)
    r7["2025 Apr 8 – Dec 31 (no news data)"] = stats(T[2025].filter(pl.col("entry_time").dt.date() > CAL_END))
    for k, v in r7.items():
        print(f"{k:<44} {v}")
    s25 = {str(rk): {"real": simulate_challenge(T[2025], date(2025, 1, 1), date(2025, 12, 31), risk_pct=rk, n_sims=3000, seed=1),
                     "zero_edge": simulate_challenge(T[2025], date(2025, 1, 1), date(2025, 12, 31), risk_pct=rk, n_sims=3000, seed=1, demean=True)}
           for rk in (0.5, 1.0, 2.0)}
    for rk, v in s25.items():
        print(f"2025 challenge @ {rk}%: pass {v['real']['pass_%']}% fail {v['real']['fail_%']}% | zero-edge twin pass {v['zero_edge']['pass_%']}%")
    r = r7["2025"]
    verdict = "STRONG PASS" if (r["R_per_trade"] > 0 and r["R_ci95"][0] > 0) else (
        "PASS" if (r["R_per_trade"] > 0 and s25["1.0"]["real"]["pass_%"] > s25["1.0"]["zero_edge"]["pass_%"]) else "FAIL")
    r7["challenge_2025"] = s25
    r7["VERDICT"] = verdict
    print("067 VERDICT:", verdict)
    (OUT7 / "results.json").write_text(json.dumps(r7, indent=2, default=str))
    equity_and_monthly_png(T[2025].with_columns(pips=pl.col("R")), "067 London fade, EURUSD 2025 (unseen), FTMO rules (in R)",
                           OUT7 / "equity_R_2025.png")

    # ---- 068: value of one paid attempt ----
    sets = {"in-sample 2023-24": (pl.concat([T[2023], T[2024]]), date(2023, 1, 2), date(2024, 12, 31), False),
            "clean 2025": (T[2025], date(2025, 1, 1), date(2025, 12, 31), False),
            "zero-edge twin (2023-24 shape)": (pl.concat([T[2023], T[2024]]), date(2023, 1, 2), date(2024, 12, 31), True)}
    grid = [(rc, rf, ds) for rc in (0.5, 1.0, 2.0) for rf in (0.25, 0.5, 1.0) for ds in (None, 2.0)]
    r8 = {}
    for name, (t, a, b, dm) in sets.items():
        rows = [simulate_lifecycle(t, a, b, risk_challenge=rc, risk_funded=rf, day_stop=ds, n_sims=2000, seed=2, demean=dm)
                for rc, rf, ds in grid]
        r8[name] = rows
        best = max(rows, key=lambda x: x["EV_per_attempt"])
        print(f"\n== 068 {name}: best EV {best}")
        for x in rows:
            print(f"   ch {x['risk_challenge']}% fu {x['risk_funded']}% stop {x['day_stop']}: pass {x['pass_%']}% "
                  f"EV ${x['EV_per_attempt']} P(net>0) {x['P(net > 0)_%']}% funded payout ${x['funded_mean_payout']} "
                  f"survive {x['funded_median_days_survived']}d breach {x['funded_breach_%']}%")
    (OUT8 / "results.json").write_text(json.dumps(r8, indent=2, default=str))

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8), sharey=True)
    for ax, (name, rows) in zip(axes, r8.items()):
        m = np.zeros((3, 3))
        for x in rows:
            if x["day_stop"] is None:
                m[[0.5, 1.0, 2.0].index(x["risk_challenge"]), [0.25, 0.5, 1.0].index(x["risk_funded"])] = x["EV_per_attempt"]
        im = ax.imshow(m, cmap="RdYlGn", vmin=-150, vmax=max(150, float(np.abs(m).max())))
        for i in range(3):
            for j in range(3):
                ax.text(j, i, f"${m[i, j]:.0f}", ha="center", va="center", fontsize=10)
        ax.set_xticks(range(3)); ax.set_xticklabels(["0.25%", "0.5%", "1%"]); ax.set_xlabel("risk per trade when funded")
        ax.set_yticks(range(3)); ax.set_yticklabels(["0.5%", "1%", "2%"])
        ax.set_title(name, fontsize=10)
    axes[0].set_ylabel("risk per trade in the challenge")
    fig.suptitle("Average money per €89 FTMO attempt (challenge + up to 1 year funded, no own daily stop)", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT8 / "attempt_value.png", dpi=110)


if __name__ == "__main__":
    main()
