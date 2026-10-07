"""Run 060 — POI study (template layer 3): what does price do after its first touch of the previous FX day's
high / low during the London morning (07:00–11:00 London) and the NY morning (08:00–11:00 NY)?
Descriptive; pre-registered in research/runs/060_poi_prev_day_levels/summary.md.
"""

from __future__ import annotations

import json
import math
from datetime import time, timedelta
from pathlib import Path

import numpy as np
import polars as pl

from lib.data import PIP, load_1s_data, resample

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "runs" / "060_poi_prev_day_levels"
PAIRS, YEARS = ("EURUSD", "GBPUSD", "AUDUSD"), (2023, 2024)
WINDOWS = {"london": ("Europe/London", time(7, 0), time(11, 0)), "ny": ("America/New_York", time(8, 0), time(11, 0))}
XS = (0.25, 0.5)
HORIZON = 240          # minutes
NY = "America/New_York"


def bars(pair: str, y: int) -> pl.DataFrame:
    b = resample(load_1s_data(str(ROOT / "data" / f"{pair}_1s_{y}.csv"), verbose=False), "1m")
    mid = lambda f: (pl.col(f"bid_{f}") + pl.col(f"ask_{f}")) / 2
    b = b.select("timestamp", "close_time", h=mid("high"), l=mid("low"), c=mid("close"))
    b = b.with_columns(fxday=(pl.col("timestamp").dt.convert_time_zone(NY) + timedelta(hours=7)).dt.date())
    d = (b.group_by("fxday").agg(dh=pl.col("h").max(), dl=pl.col("l").min(), dc=pl.col("c").last(), n=pl.len())
         .sort("fxday").filter(pl.col("n") >= 600))
    tr = pl.max_horizontal(pl.col("dh") - pl.col("dl"), (pl.col("dh") - pl.col("dc").shift(1)).abs(),
                           (pl.col("dl") - pl.col("dc").shift(1)).abs())
    d = d.with_columns(atr=tr.rolling_mean(20, min_samples=5)).with_columns(
        pdh=pl.col("dh").shift(1), pdl=pl.col("dl").shift(1), patr=pl.col("atr").shift(1))
    return b.join(d.select("fxday", "pdh", "pdl", "patr"), on="fxday", how="left")


def events(b: pl.DataFrame, wname: str) -> list[dict]:
    tz, t0, t1 = WINDOWS[wname]
    clock = pl.col("close_time").dt.convert_time_zone(tz)
    b = b.with_columns(inwin=(clock.dt.time() > t0) & (clock.dt.time() <= t1) & (clock.dt.weekday() <= 5))
    # running high/low of the FX day so far, up to the previous bar
    b = b.with_columns(hi_before=pl.col("h").cum_max().over("fxday").shift(1).over("fxday"),
                       lo_before=pl.col("l").cum_min().over("fxday").shift(1).over("fxday"))
    H, L, C = b["h"].to_numpy(), b["l"].to_numpy(), b["c"].to_numpy()
    out = []
    for side in ("high", "low"):
        lvl = "pdh" if side == "high" else "pdl"
        if side == "high":
            hit = pl.col("inwin") & (pl.col("h") >= pl.col(lvl)) & (pl.col("hi_before") < pl.col(lvl))
        else:
            hit = pl.col("inwin") & (pl.col("l") <= pl.col(lvl)) & (pl.col("lo_before") > pl.col(lvl))
        x = b.with_row_index("i").filter(hit.fill_null(False))
        x = x.filter(pl.col("i") == pl.col("i").min().over("fxday"))       # first touch per day
        for r in x.iter_rows(named=True):
            i, atr, level = r["i"], r["patr"], r[lvl]
            if atr is None or i + HORIZON + 1 >= len(C):
                continue
            sgn = 1 if side == "high" else -1                                   # + = continuation beyond the level
            e = {"fxday": str(r["fxday"]), "side": side, "atr_pips": atr / PIP}
            c0 = C[i]
            for h in (30, 60, 120, 240):
                e[f"ret{h}"] = sgn * (C[i + h] - c0) / PIP
            for X in XS:
                d = X * atr
                up, dn = c0 + sgn * d, c0 - sgn * d                             # continuation / reversal targets
                res = "open"
                for j in range(i + 1, i + HORIZON + 1):
                    cont = (H[j] >= up) if sgn == 1 else (L[j] <= up)
                    rev = (L[j] <= dn) if sgn == 1 else (H[j] >= dn)
                    if cont and rev:
                        res = "tie"; break
                    if cont:
                        res = "continuation"; break
                    if rev:
                        res = "reversal"; break
                e[f"race{X}"] = res
            out.append(e)
    return out


def summarise(ev: list[dict]) -> dict:
    if not ev:
        return {"events": 0}
    d = pl.DataFrame(ev)
    s = {"events": d.height, "median_atr_pips": round(float(d["atr_pips"].median()), 1)}
    for X in XS:
        col = d[f"race{X}"]
        rv, ct = int((col == "reversal").sum()), int((col == "continuation").sum())
        n = rv + ct
        p = rv / n if n else float("nan")
        # two-sided binomial test vs 0.5 (normal approximation)
        z = (rv - n / 2) / math.sqrt(n / 4) if n else float("nan")
        pval = math.erfc(abs(z) / math.sqrt(2)) if n else float("nan")
        s[f"X={X}"] = {"reversal_%": round(100 * p, 1), "n": n, "ties": int((col == "tie").sum()),
                       "open": int((col == "open").sum()), "p_value": round(pval, 4),
                       "target_pips_median": round(float(d["atr_pips"].median()) * X, 1)}
    for h in (30, 60, 120, 240):
        v = d[f"ret{h}"].to_numpy()
        s[f"mean_ret{h}_pips (+=continue)"] = round(float(v.mean()), 2)
    return s


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    allev: dict = {}
    for pair in PAIRS:
        for y in YEARS:
            b = bars(pair, y)
            for w in WINDOWS:
                allev[(pair, y, w)] = events(b, w)
    res = {}
    for w in WINDOWS:
        for pair in PAIRS:
            for y in YEARS:
                res[f"{w} {pair} {y}"] = summarise(allev[(pair, y, w)])
        for y in YEARS:
            res[f"{w} EUR+GBP {y}"] = summarise(allev[("EURUSD", y, w)] + allev[("GBPUSD", y, w)])
        res[f"{w} EUR+GBP 2023+2024"] = summarise(sum((allev[(p, y, w)] for p in ("EURUSD", "GBPUSD") for y in YEARS), []))
        for side in ("high", "low"):
            evs = [e for p in ("EURUSD", "GBPUSD") for y in YEARS for e in allev[(p, y, w)] if e["side"] == side]
            res[f"{w} EUR+GBP 2023+2024 {side} only"] = summarise(evs)
    for k, v in res.items():
        x5 = v.get("X=0.5", {})
        x25 = v.get("X=0.25", {})
        print(f"{k:<34} events {v['events']:>4} | rev@0.25ATR {x25.get('reversal_%')}% (p {x25.get('p_value')}) | "
              f"rev@0.5ATR {x5.get('reversal_%')}% (p {x5.get('p_value')}, ties {x5.get('ties')}, open {x5.get('open')}, "
              f"target ~{x5.get('target_pips_median')} pips) | ret60 {v.get('mean_ret60_pips (+=continue)')} ret240 {v.get('mean_ret240_pips (+=continue)')}")
    # pre-registered rule
    verdict = {}
    for w in WINDOWS:
        a, b2, pooled = res[f"{w} EUR+GBP 2023"]["X=0.5"], res[f"{w} EUR+GBP 2024"]["X=0.5"], res[f"{w} EUR+GBP 2023+2024"]["X=0.5"]
        same_dir = (a["reversal_%"] - 50) * (b2["reversal_%"] - 50) > 0
        verdict[w] = bool(same_dir and abs(a["reversal_%"] - 50) >= 5 and abs(b2["reversal_%"] - 50) >= 5
                          and pooled["p_value"] < 0.05)
    res["CARRY FORWARD (pre-registered rule)"] = verdict
    print("\ncarry forward:", verdict)
    (OUT / "results.json").write_text(json.dumps(res, indent=2, default=str))
    flat = [dict(e, pair=p, year=y, window=w) for (p, y, w), evs in allev.items() for e in evs]
    pl.DataFrame(flat).write_parquet(OUT / "events.parquet")


if __name__ == "__main__":
    main()
