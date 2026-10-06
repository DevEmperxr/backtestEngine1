"""Run 032 — how far does price move in our favour after an Idea 1 (023A) entry, before the stop
is hit or 16:00 London? (Maximum favourable excursion, MFE.) Descriptive; 2023 only.

For each 023A trade: walk the 1s path from the entry second until the 1.5x5m-ATR stop is touched
(exit side: ask for shorts, bid for longs; the stop second itself is excluded) or the 16:00 London
flat. MFE = best exit-side price reached in favour, minus the entry price, in pips. Also as
multiples of the stop distance (R) and as a fraction of the distance to the 5m SMA20 at entry
(the current target).
"""

from __future__ import annotations

import json
from datetime import time
from importlib import import_module
from pathlib import Path

import numpy as np
import polars as pl

from lib.data import PIP, load_1s_data

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "runs" / "032_idea1_mfe"


def mfe_table(year: int, scratch: Path) -> pl.DataFrame:
    base = load_1s_data(str(ROOT / "data" / f"EURUSD_1s_{year}.csv"), verbose=False)
    ts = base["timestamp"].dt.epoch("ns").to_numpy()
    ah, al = base["ask_high"].to_numpy(), base["ask_low"].to_numpy()
    bh, bl = base["bid_high"].to_numpy(), base["bid_low"].to_numpy()
    st = import_module("research.strategies.023_sweep_fade_rework").make_a()
    b1 = pl.read_parquet(scratch / f"bars1m_{year}.parquet")
    ctx = st.generate_signals(b1).select(pl.col("close_time").alias("entry_time"), "ctx_class")
    t = pl.read_parquet(ROOT / "research" / "runs" / "023_sweep_fade_rework" / f"a_{year}" / "trades.parquet").join(ctx, on="entry_time")
    flat = t.select(
        flat=pl.col("entry_time").dt.convert_time_zone("Europe/London").dt.replace(hour=16, minute=0, second=0, microsecond=0)
             .dt.convert_time_zone("UTC").dt.epoch("ns")
    )["flat"].to_numpy()
    rows = []
    for r, f in zip(t.iter_rows(named=True), flat):
        s = int(np.searchsorted(ts, int(r["entry_time"].timestamp() * 1e9), side="left"))
        e = int(np.searchsorted(ts, f, side="left"))
        short = r["direction"] == "short"
        stop = r["entry_price"] + (1 if short else -1) * r["sl_pips"] * PIP
        hit = (ah[s:e] >= stop) if short else (bl[s:e] <= stop)
        k = int(np.argmax(hit)) if hit.any() else e - s           # bars before the stop second
        stop_hit = bool(hit.any())
        seg_fav = al[s:s + k] if short else bh[s:s + k]
        if len(seg_fav):
            best = seg_fav.min() if short else seg_fav.max()
            mfe = ((r["entry_price"] - best) if short else (best - r["entry_price"])) / PIP
        else:
            mfe = 0.0
        rows.append({"entry_time": r["entry_time"], "ctx_class": r["ctx_class"], "direction": r["direction"],
                     "sl_pips": r["sl_pips"], "dist_ma_pips": r["tp_pips"], "mfe_pips": max(mfe, 0.0),
                     "stop_hit": stop_hit, "minutes_to_end": (k) / 60})
    return pl.DataFrame(rows).with_columns(
        mfe_R=pl.col("mfe_pips") / pl.col("sl_pips"),
        mfe_frac_ma=pl.col("mfe_pips") / pl.col("dist_ma_pips"),
    )


def reach_table(x: pl.DataFrame) -> dict:
    out = {}
    for col, levels in (("mfe_pips", [2, 4, 6, 8, 10, 12, 15, 20]),
                        ("mfe_R", [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0]),
                        ("mfe_frac_ma", [0.25, 0.5, 0.75, 1.0, 1.25, 1.5])):
        out[col] = {str(l): float((x[col] >= l).mean()) for l in levels}
    out["median"] = {c: float(x[c].median()) for c in ("mfe_pips", "mfe_R", "mfe_frac_ma", "sl_pips", "dist_ma_pips")}
    out["n"] = x.height
    out["stop_hit_share"] = float(x["stop_hit"].mean())
    return out


def main(year: int, scratch: Path) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    m = mfe_table(year, scratch)
    m.write_parquet(OUT / f"mfe_{year}.parquet")
    res = {"trend_with": reach_table(m.filter(pl.col("ctx_class") == "trend_with")), "all": reach_table(m)}
    (OUT / f"results_{year}.json").write_text(json.dumps(res, indent=2))
    for k, v in res.items():
        print(f"== {k}: n={v['n']}, stop hit before 16:00 in {v['stop_hit_share']*100:.0f}%; medians {{{', '.join(f'{a}: {b:.2f}' for a, b in v['median'].items())}}}")
        for col in ("mfe_pips", "mfe_R", "mfe_frac_ma"):
            print(f"   reached ≥ ({col}): " + "  ".join(f"{l}: {p*100:.0f}%" for l, p in v[col].items()))


if __name__ == "__main__":
    import sys
    main(int(sys.argv[1]), Path(sys.argv[2]))
