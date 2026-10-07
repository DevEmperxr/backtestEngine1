"""Run 069 — which prop firm's rules give the most lenient (convex) payoff? Same trade shape for every firm
(EURUSD London-fade trades 2023–24 under FTMO costs, average edge replaced by 0 / −0.05 / −0.10 R per trade),
best of a small risk grid per firm. Rules gathered from public sources on 2026-10-07 (see summary.md);
fees are indicative ($10k tier, promos vary).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import polars as pl

from lib.prop_firms import FirmRules, simulate_firm

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "runs" / "069_prop_firm_shapes"
SRC = ROOT / "research" / "runs" / "066_ftmo_reruns"

FIRMS = [
    FirmRules("FTMO 2-step", (10.0, 5.0), 5.0, 10.0, min_days=4, split=0.8, refund_after_payouts=1, fee=89.0),
    FirmRules("FTMO 1-step", (10.0,), 3.0, 10.0, trailing_eod=True, best_day_frac=0.5, split=0.9,
              refund_after_payouts=1, fee=79.0),
    FirmRules("FundedNext Stellar 2-step", (8.0, 5.0), 5.0, 10.0, min_days=5, split=0.8, refund_after_payouts=1,
              challenge_profit_share=0.15, fee=90.0),
    FirmRules("The5ers High Stakes", (10.0, 5.0), 5.0, 10.0, min_profitable_days=3, profitable_day_pct=0.5,
              split=0.8, refund_after_payouts=1, fee=75.0),
    FirmRules("FundingPips 2-step (8/5)", (8.0, 5.0), 5.0, 10.0, min_days=3, split=0.8, refund_after_payouts=4,
              fee=60.0),
    FirmRules("FundingPips 2-step Pro", (6.0, 6.0), 3.0, 6.0, min_days=3, best_day_frac=0.45, split=0.8,
              refund_after_payouts=4, fee=55.0),
    FirmRules("Alpha Capital Pro 10%", (10.0, 5.0), 5.0, 10.0, min_days=3, split=0.8, refund_after_payouts=1, fee=80.0),
    FirmRules("Alpha Capital Pro 8%", (8.0, 5.0), 4.0, 8.0, min_days=3, split=0.8, refund_after_payouts=1, fee=80.0),
    FirmRules("E8 2-phase (8/5)", (8.0, 5.0), 4.0, 8.0, best_day_frac=0.35, split=0.8, refund_after_payouts=None,
              fee=80.0),
]
EDGES = (0.0, -0.05, -0.10)
GRID = [(1.0, 0.5), (1.0, 1.0), (2.0, 0.5), (2.0, 1.0)]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    trades = pl.concat([pl.read_parquet(SRC / f"london_fade_{y}" / "trades.parquet") for y in (2023, 2024)])
    start, end = date(2023, 1, 2), date(2024, 12, 31)
    res = {}
    for edge in EDGES:
        rows = []
        for f in FIRMS:
            best = None
            for rc, rf in GRID:
                s = simulate_firm(trades, start, end, f, risk_challenge=rc, risk_funded=rf,
                                  day_stop=0.4 * f.daily_loss, edge_shift=edge, n_sims=800, seed=7)
                if best is None or s["EV_net"] > best["EV_net"]:
                    best = s
            rows.append(best)
        rows.sort(key=lambda x: x["expected_gross"], reverse=True)
        res[f"edge {edge:+.2f}R"] = rows
        print(f"\n== average edge {edge:+.2f}R per trade (after costs)")
        for x in rows:
            print(f"   {x['firm']:<28} pass {x['pass_%']:>5}% | expected out ${x['expected_gross']:>7} | "
                  f"net of fee ${x['EV_net']:>7} | per $ of fee {x['value_per_fee']:>5} | P(ahead) {x['P(net>0)_%']}% "
                  f"| risk ch {x['risk_challenge']}% fu {x['risk_funded']}%")
    (OUT / "results.json").write_text(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()
