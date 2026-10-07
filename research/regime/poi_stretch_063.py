"""Run 063 — POI only: price stretched 2 x ATR14 from the SMA20 on 5m / 15m / 1h during 08:00–10:00 London.
Does it snap back toward the mean more often than chance? Pre-registered in
research/runs/063_poi_stretch_scales/summary.md.
"""

from __future__ import annotations

import json
import math
from datetime import time
from pathlib import Path

import numpy as np
import polars as pl

from lib.data import PIP, load_1s_data, resample
from lib.signals import atr, sma

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "runs" / "063_poi_stretch_scales"
PAIRS, YEARS = ("EURUSD", "GBPUSD", "AUDUSD"), (2023, 2024)
SCALES = {"5m": (5, 120), "15m": (15, 240), "1h": (60, 480)}      # minutes per bar, race horizon (minutes)
LONDON = "Europe/London"


def one_minute(pair: str, y: int) -> pl.DataFrame:
    b = resample(load_1s_data(str(ROOT / "data" / f"{pair}_1s_{y}.csv"), verbose=False), "1m")
    mid = lambda f: (pl.col(f"bid_{f}") + pl.col(f"ask_{f}")) / 2
    return b.select("timestamp", "close_time", o=mid("open"), h=mid("high"), l=mid("low"), c=mid("close"))


def with_bands(m: pl.DataFrame, minutes: int) -> pl.DataFrame:
    tf = (m.group_by_dynamic("timestamp", every=f"{minutes}m", label="left", closed="left")
          .agg(pl.col("o").first(), pl.col("h").max(), pl.col("l").min(), pl.col("c").last())
          .with_columns(ct=pl.col("timestamp").dt.offset_by(f"{minutes}m"))
          .with_columns(ma=sma(pl.col("c"), 20), at=atr(pl.col("h"), pl.col("l"), pl.col("c"), 14))
          .select("ct", "ma", "at"))
    return m.join_asof(tf.drop_nulls(), left_on="close_time", right_on="ct", strategy="backward")


def race(H, L, k, c0, sgn, up_d, dn_d, horizon) -> str:
    good, bad = c0 + sgn * up_d, c0 - sgn * dn_d
    for j in range(k + 1, min(k + horizon + 1, len(H))):
        g = (H[j] >= good) if sgn == 1 else (L[j] <= good)
        b = (L[j] <= bad) if sgn == 1 else (H[j] >= bad)
        if g and b:
            return "tie"
        if g:
            return "success"
        if b:
            return "fail"
    return "open"


def events(m: pl.DataFrame, scale: str) -> list[dict]:
    minutes, horizon = SCALES[scale]
    b = with_bands(m, minutes)
    lon = pl.col("close_time").dt.convert_time_zone(LONDON)
    b = b.with_columns(ldate=lon.dt.date(),
                       win=((lon.dt.time() > time(8, 0)) & (lon.dt.time() <= time(10, 0)) & (lon.dt.weekday() <= 5)).fill_null(False)
                       ).with_row_index("i")
    H, L, C = b["h"].to_numpy(), b["l"].to_numpy(), b["c"].to_numpy()
    out = []
    for side in ("up", "down"):
        hit = pl.col("win") & ((pl.col("h") >= pl.col("ma") + 2 * pl.col("at")) if side == "up"
                               else (pl.col("l") <= pl.col("ma") - 2 * pl.col("at")))
        x = b.filter(hit.fill_null(False))
        x = x.filter(pl.col("i") == pl.col("i").min().over("ldate"))
        for r in x.iter_rows(named=True):
            k, ma, at = r["i"], r["ma"], r["at"]
            if k + horizon + 1 >= len(C):
                continue
            sgn = -1 if side == "up" else 1                   # toward the mean
            dist = abs(C[k] - ma)
            if not (dist > 0 and (C[k] - ma) * -sgn > 0):    # close already back across the mean: skip
                continue
            stop = 1.5 * at
            e = {"side": side, "atr_pips": at / PIP, "target_pips": dist / PIP,
                 "sym": race(H, L, k, C[k], sgn, at, at, horizon),
                 "bracket": race(H, L, k, C[k], sgn, dist, stop, horizon),
                 "bracket_null": stop / (stop + dist)}
            for h in (30, 60, 120):
                e[f"move{h}"] = sgn * (C[k + h] - C[k]) / PIP
            out.append(e)
    return out


def summarise(ev: list[dict]) -> dict:
    if not ev:
        return {"events": 0}
    d = pl.DataFrame(ev)
    s = {"events": d.height, "median_atr_pips": round(float(d["atr_pips"].median()), 1),
         "median_target_pips": round(float(d["target_pips"].median()), 1)}
    ok, bad = int((d["sym"] == "success").sum()), int((d["sym"] == "fail").sum())
    n = ok + bad
    z = (ok - n / 2) / math.sqrt(n / 4) if n else float("nan")
    s["sym_success_%"] = round(100 * ok / n, 1) if n else None
    s["sym_n"], s["sym_p"] = n, (round(math.erfc(abs(z) / math.sqrt(2)), 4) if n else None)
    bk = d.filter(pl.col("bracket").is_in(["success", "fail"]))
    s["bracket_success_%"] = round(100 * float((bk["bracket"] == "success").mean()), 1) if bk.height else None
    s["bracket_chance_%"] = round(100 * float(bk["bracket_null"].mean()), 1) if bk.height else None
    s["bracket_n"] = bk.height
    for h in (30, 60, 120):
        s[f"move{h}"] = round(float(d[f"move{h}"].mean()), 2)
    return s


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ev = {}
    for pair in PAIRS:
        for y in YEARS:
            m = one_minute(pair, y)
            for sc in SCALES:
                ev[(pair, y, sc)] = events(m, sc)
    res, verdict = {}, {}
    for sc in SCALES:
        sel = lambda pairs, years: [e for p in pairs for y in years for e in ev[(p, y, sc)]]
        r = {str(y): summarise(sel(("EURUSD", "GBPUSD"), (y,))) for y in YEARS}
        r["EUR+GBP both"] = summarise(sel(("EURUSD", "GBPUSD"), YEARS))
        for p in PAIRS:
            r[f"{p} both"] = summarise(sel((p,), YEARS))
        res[sc] = r
        a, b2, pooled = r["2023"], r["2024"], r["EUR+GBP both"]
        verdict[sc] = bool(a["sym_success_%"] >= 55 and b2["sym_success_%"] >= 55 and pooled["sym_p"] < 0.017)
        print(f"{sc:<4} EUR+GBP sym race: 2023 {a['sym_success_%']}% (n {a['sym_n']}) | 2024 {b2['sym_success_%']}% (n {b2['sym_n']}) | "
              f"both {pooled['sym_success_%']}% p {pooled['sym_p']} | bracket {pooled['bracket_success_%']}% vs chance "
              f"{pooled['bracket_chance_%']}% (n {pooled['bracket_n']}) | ATR ~{pooled['median_atr_pips']} target ~{pooled['median_target_pips']} pips | "
              f"move60 {pooled['move60']} move120 {pooled['move120']} | EUR {r['EURUSD both']['sym_success_%']}% "
              f"GBP {r['GBPUSD both']['sym_success_%']}% AUD {r['AUDUSD both']['sym_success_%']}%")
    res["CARRY FORWARD"] = verdict
    print("\ncarry forward:", verdict)
    (OUT / "results.json").write_text(json.dumps(res, indent=2, default=str))
    pl.DataFrame([dict(e, pair=p, year=y, scale=s) for (p, y, s), es in ev.items() for e in es]).write_parquet(OUT / "events.parquet")


if __name__ == "__main__":
    main()
