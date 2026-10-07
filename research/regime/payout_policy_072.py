"""Run 072 — when to take profits out of a funded FTMO 1-step account (modelling).

Funded stage only (the account starts at $10k, 90% split). Trading days drawn from the London-fade trade shape
(2023–24), edge before commission 0 / +0.10 / +0.20 R, FTMO $5 commission. 260 trading days.
Withdrawal policies:
    every2w_all     : every 10 trading days (~2 weeks), withdraw all profit
    asap_1pct       : first payout after 10 trading days, then any day profit >= 1% -> withdraw all
    asap_2pct       : same with >= 2%
    asap_5pct       : same with >= 5%
    every2w_keep2   : every ~2 weeks withdraw profit above a 2% buffer (keep 2% in the account)
Trailing floor after a withdrawal (FTMO doesn't say publicly):
    reset : the floor restarts 10% below the balance left after the withdrawal
    stays : the floor stays where the highest end-of-day balance put it (a withdrawal eats the cushion)
Rules: 3% daily loss (never take a trade that could breach it), 10% max loss trailing end-of-day, risk per trade
capped at 1% (FTMO's rule after the first payout).
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

from lib.prop_firms import FTMO_1STEP, firm_days  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "runs" / "072_payout_policy"
SRC = ROOT / "research" / "runs" / "066_ftmo_reruns"
POLICIES = {"every2w_all": ("every", 0.0, 0.0), "asap_1pct": ("asap", 1.0, 0.0), "asap_2pct": ("asap", 2.0, 0.0),
            "asap_5pct": ("asap", 5.0, 0.0), "every2w_keep2": ("every", 0.0, 2.0)}


def funded_year(days, rng, risk, policy, floor_mode, n_days=260, first_after=10, every=10, split=0.9,
                daily=3.0, max_loss=10.0, account=10_000.0):
    kind, threshold, keep = POLICIES[policy]
    bal, peak, floor, paid, n_pay = 0.0, 0.0, -max_loss, 0.0, 0
    for n in range(1, n_days + 1):
        day = days[rng.integers(len(days))]
        start = bal
        for r in day:
            if (bal - start) - risk < -daily or bal - risk <= floor:
                break
            bal += r * risk
            if bal <= floor or (bal - start) <= -daily:
                return paid, n_pay, True, n
        if bal > peak:                                   # end-of-day trailing
            peak = bal
            floor = max(floor, peak - max_loss)
        eligible = n >= first_after and (kind == "asap" if n_pay else n % every == 0) if kind == "asap" \
            else (n >= first_after and n % every == 0)
        if eligible and bal - keep >= max(threshold, 1e-9):
            w = bal - keep
            paid += w / 100 * account * split
            n_pay += 1
            bal -= w
            if floor_mode == "reset":
                peak, floor = bal, bal - max_loss
    return paid, n_pay, False, n_days


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    trades = pl.concat([pl.read_parquet(SRC / f"london_fade_{y}" / "trades.parquet") for y in (2023, 2024)])
    res = {}
    for edge in (0.0, 0.10, 0.20):
        days = firm_days(trades, date(2023, 1, 2), date(2024, 12, 31), FTMO_1STEP, edge)
        after = float(np.mean([r for d in days for r in d]))
        for risk in (0.5, 1.0):
            for floor_mode in ("reset", "stays"):
                for policy in POLICIES:
                    rng = np.random.default_rng(21)
                    sims = [funded_year(days, rng, risk, policy, floor_mode) for _ in range(1500)]
                    paid = np.array([s[0] for s in sims])
                    r = {"edge_before_comm": edge, "avg_R_after_costs": round(after, 3), "risk": risk,
                         "floor_after_payout": floor_mode, "policy": policy,
                         "mean_paid_$": round(float(paid.mean()), 1), "median_paid_$": round(float(np.median(paid)), 1),
                         "P(any payout)_%": round(100 * float((paid > 0).mean()), 1),
                         "P(breach in year)_%": round(100 * float(np.mean([s[2] for s in sims])), 1),
                         "mean_payouts": round(float(np.mean([s[1] for s in sims])), 1)}
                    res[f"{edge}|{risk}|{floor_mode}|{policy}"] = r
                    print(f"edge {edge:+.2f} (after costs {after:+.3f}R) risk {risk}% floor {floor_mode:<5} {policy:<14} "
                          f"mean paid ${r['mean_paid_$']:>7} | any payout {r['P(any payout)_%']:>5}% | "
                          f"breach {r['P(breach in year)_%']:>5}% | payouts {r['mean_payouts']}")
    (OUT / "results.json").write_text(json.dumps(res, indent=2, default=str))

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8), sharey=False)
    for ax, edge in zip(axes, (0.0, 0.10, 0.20)):
        for floor_mode, hatch in (("reset", ""), ("stays", "//")):
            vals = [res[f"{edge}|1.0|{floor_mode}|{p}"]["mean_paid_$"] for p in POLICIES]
            x = np.arange(len(POLICIES)) + (0 if floor_mode == "reset" else 0.4)
            ax.bar(x, vals, 0.4, hatch=hatch, color="#4E79A7" if floor_mode == "reset" else "#E8A33D",
                   label=f"floor {floor_mode} after a payout")
        ax.set_xticks(np.arange(len(POLICIES)) + 0.2)
        ax.set_xticklabels(list(POLICIES), rotation=25, fontsize=8)
        ax.set_title(f"edge {edge:+.2f}R before commission (1% risk)", fontsize=10)
        ax.set_ylabel("average $ paid out in the first funded year")
        ax.grid(axis="y", alpha=0.25)
        ax.legend(fontsize=8)
    fig.suptitle("FTMO 1-step funded: when to take profits out", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "payout_policy.png", dpi=110)


if __name__ == "__main__":
    main()
