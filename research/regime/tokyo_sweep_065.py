"""Run 065 — layer-by-layer results for the Tokyo second-hour sweep fade (AUDUSD primary; EURUSD, GBPUSD checks).
L3 POI only and L4 + sweep: race "back to the first-hour midpoint" vs "the same distance further" (mid prices,
chance 50%). L5: the engine's trades (run_experiment 065), in pips and R. Pre-registration:
research/runs/065_tokyo_second_hour_sweep/summary.md.
"""

from __future__ import annotations

import json
import math
from datetime import time
from importlib import import_module
from pathlib import Path

import numpy as np
import polars as pl

from lib.data import PIP, load_1s_data, resample
from lib.evaluate import bootstrap_ci
from research.regime.chart_images import equity_and_monthly_png

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "research" / "runs" / "065_tokyo_second_hour_sweep"
STRAT_RUN = ROOT / "research" / "runs" / "065_tokyo_sweep"
PAIRS, YEARS = ("AUDUSD", "EURUSD", "GBPUSD"), (2023, 2024)
HORIZON = 120


def race(H, L, k, c0, sgn, good_d, bad_d) -> str:
    g_lvl, b_lvl = c0 + sgn * good_d, c0 - sgn * bad_d
    for j in range(k + 1, min(k + HORIZON + 1, len(H))):
        g = (H[j] >= g_lvl) if sgn == 1 else (L[j] <= g_lvl)
        b = (L[j] <= b_lvl) if sgn == 1 else (H[j] >= b_lvl)
        if g and b:
            return "tie"
        if g:
            return "success"
        if b:
            return "fail"
    return "open"


def layer_events(pair: str, y: int) -> dict[str, list[str]]:
    b = resample(load_1s_data(str(ROOT / "data" / f"{pair}_1s_{y}.csv"), verbose=False), "1m")
    st = import_module("research.strategies.065_tokyo_sweep").TokyoSweep(currencies=(pair[:3], pair[3:]))
    s = st.generate_signals(b).with_row_index("i")
    H, L, C = s["mh"].to_numpy(), s["ml"].to_numpy(), s["mc"].to_numpy()
    win = ((pl.col("clock") > time(10, 0)) & (pl.col("clock") <= time(11, 0)) & pl.col("wk")
           & pl.col("r_high").is_not_null() & ~pl.col("news_blackout"))
    out = {"L3 POI only": [], "L4 + sweep": []}
    # L3: first bar of hour 2 trading beyond either edge (first per day)
    beyond = win & ((pl.col("mh") > pl.col("r_high")) | (pl.col("ml") < pl.col("r_low")))
    x = s.filter(beyond.fill_null(False))
    x = x.filter(pl.col("i") == pl.col("i").min().over("tday"))
    for r in x.iter_rows(named=True):
        k = r["i"]
        up = r["mh"] > r["r_high"]
        sgn = -1 if up else 1
        d = abs(C[k] - r["r_mid"])
        if d <= 0 or (C[k] - r["r_mid"]) * sgn > 0:
            continue
        out["L3 POI only"].append(race(H, L, k, C[k], sgn, d, d))
    # L4: the strategy's sweep signals
    for r in s.filter(pl.col("long_signal") | pl.col("short_signal")).iter_rows(named=True):
        k, sgn = r["i"], (1 if r["long_signal"] else -1)
        d = abs(C[k] - r["r_mid"])
        out["L4 + sweep"].append(race(H, L, k, C[k], sgn, d, d))
    return out


def race_stats(xs: list[str]) -> dict:
    ok, bad = xs.count("success"), xs.count("fail")
    n = ok + bad
    z = (ok - n / 2) / math.sqrt(n / 4) if n else float("nan")
    return {"n": n, "success_%": round(100 * ok / n, 1) if n else None,
            "p": round(math.erfc(abs(z) / math.sqrt(2)), 4) if n else None, "open": xs.count("open")}


def trades(pair: str, y: int) -> pl.DataFrame:
    d = STRAT_RUN / (f"main_{y}" if pair == "EURUSD" and y != 2024 else ("" if pair == "EURUSD" else f"main_{pair}_{y}"))
    return pl.read_parquet(d / "trades.parquet").with_columns(R=pl.col("pips") / pl.col("sl_pips"), pair=pl.lit(pair), year=pl.lit(y))


def trade_stats(t: pl.DataFrame) -> dict:
    if t.height == 0:
        return {"trades": 0}
    ci = bootstrap_ci(t.with_columns(pips=pl.col("R")), seed=0)["expectancy_pips"]
    er = dict(t.group_by("exit_reason").len().iter_rows())
    return {"trades": t.height, "net_pips": round(t["pips"].sum(), 1), "gross_pips": round((t["pips"] + t["spread_pips_paid"]).sum(), 1),
            "R_total": round(t["R"].sum(), 2), "R_per_trade": round(t["R"].mean(), 3),
            "R_ci95": [round(ci["ci_low"], 3), round(ci["ci_high"], 3)], "win_%": round(100 * (t["pips"] > 0).mean(), 1),
            "median_stop": round(t["sl_pips"].median(), 1), "median_target": round(t["tp_pips"].median(), 1),
            "spread_per_trade": round(t["spread_pips_paid"].mean(), 2), "exits": er}


def main() -> None:
    res = {}
    for pair in PAIRS:
        for y in YEARS:
            lev = layer_events(pair, y)
            t = trades(pair, y)
            res[f"{pair} {y}"] = {k: race_stats(v) for k, v in lev.items()} | {"L5 trades": trade_stats(t)}
            r = res[f"{pair} {y}"]
            print(f"{pair} {y}: L3 {r['L3 POI only']} | L4 {r['L4 + sweep']}\n   L5 {r['L5 trades']}")
        both = pl.concat([trades(pair, y) for y in YEARS])
        res[f"{pair} 2023+2024 L5"] = trade_stats(both)
        print(f"{pair} 2023+2024 L5: {res[f'{pair} 2023+2024 L5']}")
        equity_and_monthly_png(both.with_columns(pips=pl.col("R")), f"065 Tokyo 2nd-hour sweep fade, {pair} 2023+2024 (in R)",
                               RUN / f"equity_monthly_R_{pair}.png")
    a = res["AUDUSD 2023+2024 L5"]
    passed = (res["AUDUSD 2023"]["L5 trades"]["R_total"] > 0 and res["AUDUSD 2024"]["L5 trades"]["R_total"] > 0
              and a["R_per_trade"] >= 0.10 and a["R_ci95"][0] > 0)
    res["VERDICT (AUDUSD)"] = "PASS" if passed else "FAIL"
    print("\nVERDICT (AUDUSD):", res["VERDICT (AUDUSD)"])
    (RUN / "results.json").write_text(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()
