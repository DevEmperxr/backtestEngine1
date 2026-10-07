"""Run 064 — intraday momentum (Gao et al. 2018 adapted to FX): does the move from the FX-day open (17:00 NY)
to 09:30 NY predict the NY afternoon (12:00–16:00 NY) or the last half hour (15:30–16:00 NY)?
Pre-registered in research/runs/064_intraday_momentum/summary.md.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, time, timedelta
from pathlib import Path

import numpy as np
import polars as pl

from lib.data import PIP, load_1s_data, resample
from research.regime.news import pair_currencies, red_news_times

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "runs" / "064_intraday_momentum"
PAIRS, YEARS = ("EURUSD", "GBPUSD", "AUDUSD"), (2023, 2024)
NY = "America/New_York"
TARGETS = {"T1 NY afternoon 12-16": (time(12, 0), time(16, 0)), "T2 last half hour 15:30-16": (time(15, 30), time(16, 0))}
SPREAD = {"EURUSD": 0.3, "GBPUSD": 0.8, "AUDUSD": 1.0}


def daily_table(pair: str, y: int) -> pl.DataFrame:
    b = resample(load_1s_data(str(ROOT / "data" / f"{pair}_1s_{y}.csv"), verbose=False), "1m")
    b = b.select(ct=pl.col("close_time").dt.convert_time_zone(NY),
                 mid=(pl.col("bid_close") + pl.col("ask_close")) / 2,
                 spread=(pl.col("ask_close") - pl.col("bid_close")) / PIP)
    b = b.with_columns(day=pl.col("ct").dt.date(), clock=pl.col("ct").dt.time(), wd=pl.col("ct").dt.weekday())
    marks = {"open": time(17, 0), "m930": time(9, 30), "t12": time(12, 0), "t1530": time(15, 30), "t16": time(16, 0)}
    rows = {}
    for name, t in marks.items():
        x = b.filter(pl.col("clock") == t).select("day", pl.col("mid").alias(name), pl.col("spread").alias(f"sp_{name}"))
        if name == "open":                       # 17:00 the previous evening opens this FX day
            x = x.with_columns(day=pl.col("day") + timedelta(days=1))
        rows[name] = x
    d = rows["m930"]
    for name in ("open", "t12", "t1530", "t16"):
        d = d.join(rows[name], on="day", how="inner")
    d = d.filter(pl.col("day").dt.weekday() <= 5)
    # Monday's FX day opens Sunday 17:00
    return d.with_columns(
        morning=(pl.col("m930") - pl.col("open")) / PIP,
        T1=(pl.col("t16") - pl.col("t12")) / PIP,
        T2=(pl.col("t16") - pl.col("t1530")) / PIP,
        pair=pl.lit(pair), year=pl.lit(y))


def news_free(d: pl.DataFrame, pair: str) -> pl.DataFrame:
    times, whole = red_news_times(pair_currencies(pair))
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(NY)
    ev = sorted(t.astimezone(tz).replace(tzinfo=None) for t in times)
    ev_np = np.array(ev, dtype="datetime64[m]")
    out = {}
    for tname, (t0, t1) in TARGETS.items():
        ok = []
        for day in d["day"].to_list():
            if day in whole:
                ok.append(False)
                continue
            a = np.datetime64(datetime.combine(day, t0) - timedelta(hours=1), "m")
            b = np.datetime64(datetime.combine(day, t1), "m")
            i = np.searchsorted(ev_np, a)
            ok.append(not (i < len(ev_np) and ev_np[i] <= b))
        out[f"clean_{tname[:2]}"] = ok
    return d.with_columns(**{k: pl.Series(v) for k, v in out.items()})


def stats(x: np.ndarray) -> dict:
    n = len(x)
    if n < 3:
        return {"n": n}
    m, sd = float(x.mean()), float(x.std(ddof=1))
    return {"n": n, "mean_pips": round(m, 2), "t": round(m / (sd / math.sqrt(n)), 2), "hit_%": round(100 * float((x > 0).mean()), 1)}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    d = pl.concat([news_free(daily_table(p, y), p) for p in PAIRS for y in YEARS])
    d.write_parquet(OUT / "days.parquet")
    res, verdict = {}, {}
    for tname in TARGETS:
        col, clean = tname[:2], f"clean_{tname[:2]}"
        d2 = d.with_columns(signed=pl.col(col) * pl.col("morning").sign())
        r = {}
        for sample, filt in (("news-free", pl.col(clean)), ("all days", pl.lit(True))):
            s = {}
            for y in YEARS:
                s[f"EUR+GBP {y}"] = stats(d2.filter(filt & pl.col("pair").is_in(["EURUSD", "GBPUSD"]) & (pl.col("year") == y))["signed"].to_numpy())
            s["EUR+GBP both"] = stats(d2.filter(filt & pl.col("pair").is_in(["EURUSD", "GBPUSD"]))["signed"].to_numpy())
            for p in PAIRS:
                s[f"{p} both"] = stats(d2.filter(filt & (pl.col("pair") == p))["signed"].to_numpy())
            x = d2.filter(filt & pl.col("pair").is_in(["EURUSD", "GBPUSD"]))
            s["corr(morning, target)"] = round(float(np.corrcoef(x["morning"], x[col])[0, 1]), 3)
            med = float(x["morning"].abs().median())
            s["big morning moves"] = stats(x.filter(pl.col("morning").abs() >= med)["signed"].to_numpy())
            s["small morning moves"] = stats(x.filter(pl.col("morning").abs() < med)["signed"].to_numpy())
            r[sample] = s
        res[tname] = r
        p = r["news-free"]
        spread_bar = (SPREAD["EURUSD"] + SPREAD["GBPUSD"]) / 2
        verdict[tname] = bool(p["EUR+GBP 2023"]["mean_pips"] > 0 and p["EUR+GBP 2024"]["mean_pips"] > 0
                              and p["EUR+GBP both"]["t"] > 2.24 and p["EUR+GBP both"]["mean_pips"] > spread_bar)
        print(f"\n== {tname}")
        for sample in ("news-free", "all days"):
            s = r[sample]
            print(f"  {sample:<10} 2023 {s['EUR+GBP 2023']} | 2024 {s['EUR+GBP 2024']} | both {s['EUR+GBP both']}")
            print(f"  {'':<10} EUR {s['EURUSD both']} GBP {s['GBPUSD both']} AUD {s['AUDUSD both']}")
            print(f"  {'':<10} corr {s['corr(morning, target)']} | big moves {s['big morning moves']} | small {s['small morning moves']}")
    res["CARRY FORWARD"] = verdict
    print("\ncarry forward:", verdict)
    (OUT / "results.json").write_text(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()
