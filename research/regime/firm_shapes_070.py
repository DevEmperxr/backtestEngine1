"""Run 070 — prop-firm payoff shapes in USD, with each firm's commission, and the number of trades / trading days
to pass, to the first payout, and until the money received exceeds the fee. Same trade shape for every firm
(EURUSD London-fade trades 2023–24), average edge BEFORE commission set to 0 / +0.05 / +0.10 R per trade, then each
firm's own commission charged. Best of a small risk grid per firm. Rules/prices/commissions: public sources,
2026-10-07 (see summary.md).
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

from lib.prop_firms import FirmRules, firm_days, simulate_firm  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "runs" / "070_prop_firm_shapes_usd"
SRC = ROOT / "research" / "runs" / "066_ftmo_reruns"
EURUSD = 1.126                     # FRED DEXUSEU, 2026-10-02 (1.1259)

FIRMS = [
    FirmRules("FTMO 1-step", (10.0,), 3.0, 10.0, trailing_eod=True, best_day_frac=0.5, split=0.9,
              refund_after_payouts=1, fee=round(79 * EURUSD), commission_usd=3.0),
    FirmRules("FTMO 2-step", (10.0, 5.0), 5.0, 10.0, min_days=4, split=0.8, refund_after_payouts=1,
              fee=round(89 * EURUSD), commission_usd=3.0),
    FirmRules("FundedNext Stellar 2-step", (8.0, 5.0), 5.0, 10.0, min_days=5, split=0.8, refund_after_payouts=1,
              challenge_profit_share=0.15, fee=90.0, commission_usd=5.0),
    FirmRules("The5ers High Stakes", (10.0, 5.0), 5.0, 10.0, min_profitable_days=3, profitable_day_pct=0.5,
              split=0.8, refund_after_payouts=1, fee=75.0, commission_usd=4.0),
    FirmRules("FundingPips 2-step (8/5)", (8.0, 5.0), 5.0, 10.0, min_days=3, split=0.8, refund_after_payouts=4,
              fee=60.0, commission_usd=5.0),
    FirmRules("FundingPips 2-step Pro", (6.0, 6.0), 3.0, 6.0, min_days=3, best_day_frac=0.45, split=0.8,
              refund_after_payouts=4, fee=55.0, commission_usd=5.0),
    FirmRules("Alpha Capital Pro 10%", (10.0, 5.0), 5.0, 10.0, min_days=3, split=0.8, refund_after_payouts=1,
              fee=80.0, commission_usd=2.5),
    FirmRules("Alpha Capital Pro 8%", (8.0, 5.0), 4.0, 8.0, min_days=3, split=0.8, refund_after_payouts=1,
              fee=80.0, commission_usd=2.5),
    FirmRules("E8 2-phase (8/5)", (8.0, 5.0), 4.0, 8.0, best_day_frac=0.35, split=0.8, refund_after_payouts=None,
              fee=80.0, commission_usd=5.0),
]
EDGES = (0.0, 0.05, 0.10)          # average R per trade BEFORE commission (spread already included)
GRID = [(1.0, 0.5), (1.0, 1.0), (2.0, 0.5), (2.0, 1.0)]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    trades = pl.concat([pl.read_parquet(SRC / f"london_fade_{y}" / "trades.parquet") for y in (2023, 2024)])
    start, end = date(2023, 1, 2), date(2024, 12, 31)
    print(f"trade shape: {trades.height} trades, median stop {trades['sl_pips'].median():.1f} pips")
    res = {}
    for edge in EDGES:
        rows = []
        for f in FIRMS:
            days = firm_days(trades, start, end, f, edge)
            best = None
            for rc, rf in GRID:
                s = simulate_firm(days, f, risk_challenge=rc, risk_funded=rf, day_stop=0.4 * f.daily_loss,
                                  n_sims=800, seed=11)
                if best is None or s["EV_net"] > best["EV_net"]:
                    best = s
            rows.append(best)
        rows.sort(key=lambda x: x["EV_net"], reverse=True)
        res[f"edge {edge:+.2f}R before commission"] = rows
        print(f"\n== average edge {edge:+.2f}R per trade BEFORE commission")
        for x in rows:
            print(f"   {x['firm']:<26} fee ${x['fee']:>4.0f} comm ${x['commission_usd']:.1f} | pass {x['pass_%']:>5}% | "
                  f"net ${x['EV_net']:>7} | trades to pass {x['trades_to_pass']} ({x['days_to_pass']}d) | "
                  f"to 1st payout {x['trades_to_first_payout']} ({x['days_to_first_payout']}d) | "
                  f"to profit {x['trades_to_profit']} ({x['days_to_profit']}d) | risk {x['risk_challenge']}/{x['risk_funded']}")
    (OUT / "results.json").write_text(json.dumps(res, indent=2, default=str))

    key = "edge +0.05R before commission"
    order = [x["firm"] for x in res[key]]
    lab = {x["firm"]: x for x in res[key]}
    fig, ax = plt.subplots(figsize=(14, 6.6))
    w = 0.27
    cols = {"edge +0.00R before commission": "#D84A2E", "edge +0.05R before commission": "#E8A33D",
            "edge +0.10R before commission": "#2E9E5B"}
    for i, (k, c) in enumerate(cols.items()):
        m = {x["firm"]: x["EV_net"] for x in res[k]}
        bars = ax.bar(np.arange(len(order)) + (i - 1) * w, [m[f] for f in order], w, color=c,
                      label=k.replace("edge", "average edge per trade"))
        for b, f in zip(bars, order):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + (10 if b.get_height() >= 0 else -28),
                    f"${m[f]:.0f}", ha="center", fontsize=6.5)
    ax.axhline(0, color="#555", lw=0.8)
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([f"{f}\nfee ${lab[f]['fee']:.0f} · comm ${lab[f]['commission_usd']:.1f}/lot\n"
                        f"pass in ~{lab[f]['trades_to_pass']} trades · profit in ~{lab[f]['trades_to_profit']}"
                        for f in order], rotation=25, ha="right", fontsize=7.5)
    ax.set_ylabel("average $ per attempt, after the fee (USD)")
    ax.set_title("Prop-firm payoff shapes, $10k account, USD, each firm's commission charged\n"
                 "trade counts = median trades to pass / until money received exceeds the fee, at +0.05R edge before commission",
                 fontsize=10)
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT / "firm_shapes_usd.png", dpi=110)
    print(OUT / "firm_shapes_usd.png")


if __name__ == "__main__":
    main()
