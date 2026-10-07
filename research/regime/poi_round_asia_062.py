"""Run 062 — POI study: round numbers (00 / 50 levels: reversal at first touch, continuation after a cross) and
the Asian-session high/low touched in the London morning. Pre-registered in
research/runs/062_poi_round_numbers_asia/summary.md.
"""

from __future__ import annotations

import json
import math
from datetime import time
from pathlib import Path

import numpy as np
import polars as pl

from lib.data import PIP
from research.regime.poi_prev_day_060 import bars

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "runs" / "062_poi_round_numbers_asia"
PAIRS, YEARS = ("EURUSD", "GBPUSD", "AUDUSD"), (2023, 2024)
XS, HORIZON = (0.1, 0.25), 240
LONDON, NY = "Europe/London", "America/New_York"


def race(H, L, k, c0, sgn, d) -> str:
    good_lvl, bad_lvl = c0 + sgn * d, c0 - sgn * d
    for j in range(k + 1, min(k + HORIZON + 1, len(H))):
        good = (H[j] >= good_lvl) if sgn == 1 else (L[j] <= good_lvl)
        bad = (L[j] <= bad_lvl) if sgn == 1 else (H[j] >= bad_lvl)
        if good and bad:
            return "tie"
        if good:
            return "success"
        if bad:
            return "fail"
    return "open"


def record(kind, H, L, C, k, sgn, atr, fxday) -> dict:
    e = {"kind": kind, "fxday": str(fxday), "atr_pips": atr / PIP}
    for X in XS:
        e[f"race{X}"] = race(H, L, k, C[k], sgn, X * atr)
    for h in (30, 60, 120):
        e[f"move{h}"] = sgn * (C[k + h] - C[k]) / PIP if k + h < len(C) else np.nan
    return e


def round_events(b: pl.DataFrame) -> list[dict]:
    lon = pl.col("close_time").dt.convert_time_zone(LONDON)
    ny = pl.col("close_time").dt.convert_time_zone(NY)
    b = b.with_columns(inwin=((lon.dt.time() > time(7, 0)) & (ny.dt.time() <= time(12, 0))
                              & (ny.dt.weekday() <= 5) & (ny.dt.date() == lon.dt.date())).fill_null(False))
    H, L, C = b["h"].to_numpy(), b["l"].to_numpy(), b["c"].to_numpy()
    inwin, fx, atr = b["inwin"].to_numpy(), b["fxday"].to_list(), b["patr"].to_list()
    out, n = [], len(C)
    touched_today: set = set()
    pending: dict = {}                     # level -> crossing direction awaiting the first close beyond
    day = None
    for k in range(1, n - HORIZON - 1):
        if fx[k] != day:
            day, touched_today, pending = fx[k], set(), {}
        # levels traded during the FX day so far (also outside the window) count as touched
        lo_lvl, hi_lvl = math.ceil(round(L[k] / 0.005, 6)), math.floor(round(H[k] / 0.005, 6))
        levels = range(lo_lvl, hi_lvl + 1)
        if not inwin[k] or atr[k] is None:
            touched_today.update(levels)
            continue
        for m in levels:
            lvl = m * 0.005
            kind = "00" if m % 2 == 0 else "50"
            if m not in touched_today:
                touched_today.add(m)
                if C[k - 1] < lvl:            # approached from below: reversal = down
                    out.append(record(f"A1 reversal {kind}", H, L, C, k, -1, atr[k], fx[k]))
                    pending[m] = 1
                elif C[k - 1] > lvl:
                    out.append(record(f"A1 reversal {kind}", H, L, C, k, 1, atr[k], fx[k]))
                    pending[m] = -1
        for m, direction in list(pending.items()):
            lvl = m * 0.005
            if (direction == 1 and C[k] > lvl) or (direction == -1 and C[k] < lvl):
                kind = "00" if m % 2 == 0 else "50"
                out.append(record(f"A2 continuation {kind}", H, L, C, k, direction, atr[k], fx[k]))
                del pending[m]
    return out


def asia_events(b: pl.DataFrame) -> list[dict]:
    lon_open = pl.col("timestamp").dt.convert_time_zone(LONDON)
    lon = pl.col("close_time").dt.convert_time_zone(LONDON)
    b = b.with_columns(ldate=lon.dt.date(), oclock=lon_open.dt.time(), cclock=lon.dt.time(),
                       wk=lon.dt.weekday() <= 5)
    asia = (b.filter((pl.col("oclock") >= time(0, 0)) & (pl.col("oclock") < time(7, 0)) & pl.col("wk")
                     & (lon_open.dt.date() == pl.col("ldate")))
            .group_by("ldate").agg(ah=pl.col("h").max(), al=pl.col("l").min(), an=pl.len()))
    b = b.join(asia.filter(pl.col("an") >= 300), on="ldate", how="left")
    win = (pl.col("cclock") > time(7, 0)) & (pl.col("cclock") <= time(11, 0)) & pl.col("wk") & pl.col("ah").is_not_null()
    b = b.with_columns(win=win.fill_null(False)).with_row_index("i")
    # broken before the touch? running high/low since 07:00 London up to the previous bar
    b = b.with_columns(
        hi_prev=pl.when(pl.col("win")).then(pl.col("h")).cum_max().over("ldate").shift(1).over("ldate"),
        lo_prev=pl.when(pl.col("win")).then(pl.col("l")).cum_min().over("ldate").shift(1).over("ldate"))
    H, L, C = b["h"].to_numpy(), b["l"].to_numpy(), b["c"].to_numpy()
    out = []
    for side in ("high", "low"):
        if side == "high":
            hit = pl.col("win") & (pl.col("h") >= pl.col("ah")) & (pl.col("hi_prev").is_null() | (pl.col("hi_prev") < pl.col("ah")))
        else:
            hit = pl.col("win") & (pl.col("l") <= pl.col("al")) & (pl.col("lo_prev").is_null() | (pl.col("lo_prev") > pl.col("al")))
        x = b.filter(hit.fill_null(False))
        x = x.filter(pl.col("i") == pl.col("i").min().over("ldate"))
        for r in x.iter_rows(named=True):
            k = r["i"]
            if r["patr"] is None or k + HORIZON + 1 >= len(C):
                continue
            out.append(record("B asia reversal", H, L, C, k, -1 if side == "high" else 1, r["patr"], r["fxday"]))
    return out


def summarise(ev: list[dict], X: float) -> dict:
    if not ev:
        return {"n": 0}
    d = pl.DataFrame(ev)
    col = d[f"race{X}"]
    ok, bad = int((col == "success").sum()), int((col == "fail").sum())
    n = ok + bad
    z = (ok - n / 2) / math.sqrt(n / 4) if n else float("nan")
    return {"events": d.height, "n": n, "success_%": round(100 * ok / n, 1) if n else None,
            "p_value": round(math.erfc(abs(z) / math.sqrt(2)), 4) if n else None,
            "open": int((col == "open").sum()), "ties": int((col == "tie").sum()),
            "move30": round(float(np.nanmean(d["move30"].to_numpy())), 2),
            "move60": round(float(np.nanmean(d["move60"].to_numpy())), 2),
            "target_pips": round(float(d["atr_pips"].median()) * X, 1)}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ev = {}
    for pair in PAIRS:
        for y in YEARS:
            b = bars(pair, y)
            ev[(pair, y)] = round_events(b) + asia_events(b)
    kinds = ["A1 reversal 00", "A1 reversal 50", "A2 continuation 00", "A2 continuation 50", "B asia reversal"]
    primary = {k: (0.25 if k.startswith("B") else 0.1) for k in kinds}
    res, verdict = {}, {}
    for kind in kinds:
        r = {}
        for X in XS:
            sel = lambda pairs, years: [e for p in pairs for y in years for e in ev[(p, y)] if e["kind"] == kind]
            r[f"X={X}"] = {**{str(y): summarise(sel(("EURUSD", "GBPUSD"), (y,)), X) for y in YEARS},
                           "EUR+GBP both": summarise(sel(("EURUSD", "GBPUSD"), YEARS), X),
                           **{f"{p} both": summarise(sel((p,), YEARS), X) for p in PAIRS}}
        res[kind] = r
        X = primary[kind]
        a, b2, pooled = r[f"X={X}"]["2023"], r[f"X={X}"]["2024"], r[f"X={X}"]["EUR+GBP both"]
        up = a["success_%"] >= 55 and b2["success_%"] >= 55
        down = kind.startswith("B") and a["success_%"] <= 45 and b2["success_%"] <= 45
        verdict[kind] = bool((up or down) and pooled["p_value"] < 0.01)
        other = 0.25 if X == 0.1 else 0.1
        print(f"{kind:<20} primary X={X}: 2023 {a['success_%']}% (n {a['n']}) | 2024 {b2['success_%']}% (n {b2['n']}) | "
              f"both {pooled['success_%']}% p {pooled['p_value']} target ~{pooled['target_pips']} pips | "
              f"EUR {r[f'X={X}']['EURUSD both']['success_%']}% GBP {r[f'X={X}']['GBPUSD both']['success_%']}% "
              f"AUD {r[f'X={X}']['AUDUSD both']['success_%']}% | move30 {pooled['move30']} move60 {pooled['move60']} | "
              f"X={other}: {r[f'X={other}']['EUR+GBP both']['success_%']}% (n {r[f'X={other}']['EUR+GBP both']['n']})")
    res["CARRY FORWARD"] = verdict
    print("\ncarry forward:", {k: v for k, v in verdict.items() if v} or "none")
    (OUT / "results.json").write_text(json.dumps(res, indent=2, default=str))
    pl.DataFrame([dict(e, pair=p, year=y) for (p, y), es in ev.items() for e in es]).write_parquet(OUT / "events.parquet")


if __name__ == "__main__":
    main()
