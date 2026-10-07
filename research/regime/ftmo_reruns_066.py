"""Run 066 — results of the FTMO re-check: per idea / pair / year after spread + commission (pips and R), and the
FTMO 2-step challenge simulation vs each idea's zero-edge twin. Plan: research/runs/066_ftmo_reruns/summary.md.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import polars as pl

from lib.evaluate import bootstrap_ci
from lib.prop import simulate_challenge
from research.regime.chart_images import equity_and_monthly_png

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "research" / "runs" / "066_ftmo_reruns"
IDEAS = ("london_fade", "london_fade_4r", "home_hours", "orb_nr7")
PAIRS, YEARS = ("EURUSD", "GBPUSD"), (2023, 2024)
RISKS = (0.25, 0.5, 1.0, 2.0)
START, END = date(2023, 1, 2), date(2024, 12, 31)


def load(idea: str, pair: str, y: int) -> pl.DataFrame:
    d = RUN / (f"{idea}_{y}" if pair == "EURUSD" else f"{idea}_{pair}_{y}")
    return pl.read_parquet(d / "trades.parquet").with_columns(R=pl.col("pips") / pl.col("sl_pips"))


def stats(t: pl.DataFrame) -> dict:
    if t.height == 0:
        return {"trades": 0}
    ci = bootstrap_ci(t.with_columns(pips=pl.col("R")), seed=0)["expectancy_pips"]
    return {"trades": t.height, "net_pips": round(t["pips"].sum(), 1), "R_total": round(t["R"].sum(), 1),
            "R_per_trade": round(t["R"].mean(), 3), "R_ci95": [round(ci["ci_low"], 3), round(ci["ci_high"], 3)],
            "win_%": round(100 * (t["pips"] > 0).mean(), 1), "median_stop": round(t["sl_pips"].median(), 1),
            "costs_per_trade_pips": round((t["spread_pips_paid"] + t["commission_pips"]).mean(), 2)}


def main() -> None:
    res: dict = {}
    for idea in IDEAS:
        for pair in PAIRS:
            ty = {y: load(idea, pair, y) for y in YEARS}
            both = pl.concat(list(ty.values()))
            key = f"{idea} {pair}"
            r = {str(y): stats(ty[y]) for y in YEARS} | {"both": stats(both)}
            sims = {}
            for risk in RISKS:
                real = simulate_challenge(both, START, END, risk_pct=risk, n_sims=3000, seed=1)
                zero = simulate_challenge(both, START, END, risk_pct=risk, n_sims=3000, seed=1, demean=True)
                sims[str(risk)] = {"real": real, "zero_edge": zero}
            r["ftmo"] = sims
            res[key] = r
            print(f"\n== {key}: 2023 {r['2023']} \n   2024 {r['2024']}\n   both {r['both']}")
            for risk in RISKS:
                s = sims[str(risk)]
                print(f"   risk {risk}%: pass {s['real']['pass_%']}% fail {s['real']['fail_%']}% (days to pass "
                      f"{s['real']['median_days_to_pass']}) | zero-edge twin pass {s['zero_edge']['pass_%']}% "
                      f"fail {s['zero_edge']['fail_%']}%")
            res[key]["candidate"] = bool(r["2023"]["R_per_trade"] > 0 and r["2024"]["R_per_trade"] > 0
                                         and sims["0.5"]["real"]["pass_%"] > sims["0.5"]["zero_edge"]["pass_%"])
            if pair == "EURUSD":
                equity_and_monthly_png(both.with_columns(pips=pl.col("R")),
                                       f"066 {idea}, EURUSD 2023+2024, FTMO rules (in R)", RUN / f"equity_R_{idea}_EURUSD.png")
    print("\ncandidates:", [k for k, v in res.items() if v["candidate"]] or "none")
    (RUN / "results.json").write_text(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()
