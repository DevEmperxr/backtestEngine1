"""Run 061 — confirmation layer at the previous FX day's high/low (template layer 4): after the 060 touch,
is price back inside (rejection) or still beyond (acceptance) D minutes later, and does that predict the next
move? Pre-registered in research/runs/061_confirm_prev_day_levels/summary.md.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import polars as pl

from lib.data import PIP
from research.regime.poi_prev_day_060 import WINDOWS, bars

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "runs" / "061_confirm_prev_day_levels"
PAIRS, YEARS = ("EURUSD", "GBPUSD", "AUDUSD"), (2023, 2024)
DELAYS, XS, HORIZON = (5, 15), (0.25, 0.5), 240


def race(H, L, start, c0, sgn_expected, d) -> str:
    up, dn = c0 + sgn_expected * d, c0 - sgn_expected * d
    for j in range(start + 1, min(start + HORIZON + 1, len(H))):
        good = (H[j] >= up) if sgn_expected == 1 else (L[j] <= up)
        bad = (L[j] <= dn) if sgn_expected == 1 else (H[j] >= dn)
        if good and bad:
            return "tie"
        if good:
            return "success"
        if bad:
            return "fail"
    return "open"


def events(b: pl.DataFrame, wname: str) -> list[dict]:
    tz, t0, t1 = WINDOWS[wname]
    clock = pl.col("close_time").dt.convert_time_zone(tz)
    b = b.with_columns(inwin=(clock.dt.time() > t0) & (clock.dt.time() <= t1) & (clock.dt.weekday() <= 5))
    b = b.with_columns(hi_before=pl.col("h").cum_max().over("fxday").shift(1).over("fxday"),
                       lo_before=pl.col("l").cum_min().over("fxday").shift(1).over("fxday"))
    H, L, C = b["h"].to_numpy(), b["l"].to_numpy(), b["c"].to_numpy()
    out = []
    for side in ("high", "low"):
        lvl = "pdh" if side == "high" else "pdl"
        hit = (pl.col("inwin") & (pl.col("h") >= pl.col(lvl)) & (pl.col("hi_before") < pl.col(lvl))) if side == "high" \
            else (pl.col("inwin") & (pl.col("l") <= pl.col(lvl)) & (pl.col("lo_before") > pl.col(lvl)))
        x = b.with_row_index("i").filter(hit.fill_null(False))
        x = x.filter(pl.col("i") == pl.col("i").min().over("fxday"))
        for r in x.iter_rows(named=True):
            i, atr, level = r["i"], r["patr"], r[lvl]
            if atr is None or i + max(DELAYS) + HORIZON + 1 >= len(C):
                continue
            beyond = 1 if side == "high" else -1                 # direction beyond the level
            for D in DELAYS:
                k = i + D
                still_beyond = (C[k] > level) if side == "high" else (C[k] < level)
                label = "acceptance" if still_beyond else "rejection"
                sgn = beyond if label == "acceptance" else -beyond   # expected direction
                e = {"fxday": str(r["fxday"]), "side": side, "D": D, "label": label, "atr_pips": atr / PIP}
                for X in XS:
                    e[f"race{X}"] = race(H, L, k, C[k], sgn, X * atr)
                for h in (60, 240):
                    e[f"move{h}"] = sgn * (C[k + h] - C[k]) / PIP
                out.append(e)
    return out


def summarise(ev: list[dict]) -> dict:
    if not ev:
        return {"events": 0}
    d = pl.DataFrame(ev)
    s = {"events": d.height}
    for X in XS:
        col = d[f"race{X}"]
        ok, bad = int((col == "success").sum()), int((col == "fail").sum())
        n = ok + bad
        z = (ok - n / 2) / math.sqrt(n / 4) if n else float("nan")
        s[f"X={X}"] = {"success_%": round(100 * ok / n, 1) if n else None, "n": n,
                       "p_value": round(math.erfc(abs(z) / math.sqrt(2)), 4) if n else None,
                       "open": int((col == "open").sum()), "ties": int((col == "tie").sum())}
    s["move60_pips"] = round(float(d["move60"].mean()), 2)
    s["move240_pips"] = round(float(d["move240"].mean()), 2)
    return s


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ev = {}
    for pair in PAIRS:
        for y in YEARS:
            b = bars(pair, y)
            for w in WINDOWS:
                ev[(pair, y, w)] = events(b, w)
    res, verdict = {}, {}
    for w in WINDOWS:
        for D in DELAYS:
            for label in ("rejection", "acceptance"):
                sel = lambda pairs, years: [e for p in pairs for y in years for e in ev[(p, y, w)]
                                            if e["D"] == D and e["label"] == label]
                key = f"{w} D={D} {label}"
                r = {str(y): summarise(sel(("EURUSD", "GBPUSD"), (y,))) for y in YEARS}
                r["EUR+GBP both"] = summarise(sel(("EURUSD", "GBPUSD"), YEARS))
                r["AUDUSD both"] = summarise(sel(("AUDUSD",), YEARS))
                for p in ("EURUSD", "GBPUSD"):
                    r[f"{p} both"] = summarise(sel((p,), YEARS))
                res[key] = r
                a, b2, pooled = r["2023"]["X=0.25"], r["2024"]["X=0.25"], r["EUR+GBP both"]["X=0.25"]
                verdict[key] = bool(a["success_%"] and b2["success_%"] and a["success_%"] >= 55 and b2["success_%"] >= 55
                                    and pooled["p_value"] is not None and pooled["p_value"] < 0.006)
                print(f"{key:<26} EUR+GBP: 2023 {a['success_%']}% (n {a['n']}) | 2024 {b2['success_%']}% (n {b2['n']}) | "
                      f"both {pooled['success_%']}% p {pooled['p_value']} | move60 {r['EUR+GBP both']['move60_pips']} "
                      f"move240 {r['EUR+GBP both']['move240_pips']} | EUR {r['EURUSD both']['X=0.25']['success_%']}% "
                      f"GBP {r['GBPUSD both']['X=0.25']['success_%']}% AUD {r['AUDUSD both']['X=0.25']['success_%']}% "
                      f"| @0.5ATR {r['EUR+GBP both']['X=0.5']['success_%']}% (n {r['EUR+GBP both']['X=0.5']['n']})")
    res["CARRY FORWARD"] = verdict
    print("\ncarry forward:", {k: v for k, v in verdict.items() if v} or "none")
    (OUT / "results.json").write_text(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()
