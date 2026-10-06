"""Research 021 — how far does price stretch from the 1h MA20 before coming back?
(see research/runs/021_fib_stretch_1h)

    python -m research.regime.fib_stretch --year 2023

z = (1m mid close − MA20_1h) / σ20_1h, with MA/σ from the last CLOSED 1h bar (as-of
backward on close_time; σ = population SD of the 20 closes, as Bollinger Bands). An
excursion is a maximal run of 1m bars with z on one side of 0; its peak uses the 1m
mid high/low. Measurement only, no trades.
"""

from __future__ import annotations

import argparse
import json
from datetime import time
from pathlib import Path

import numpy as np
import polars as pl

from lib.signals import session_window
from research.regime.trend_scorecard import aggregate, mid_1m

RUN = Path(__file__).resolve().parents[1] / "runs" / "021_fib_stretch_1h"
BANDS = [0.382, 0.618, 1.0, 1.618, 2.618, 4.236]
FIB = [0.382, 0.618, 1.618, 2.618]
CONTROL = [0.5, 0.8, 1.3, 2.0, 2.2]
NY, LONDON = "America/New_York", "Europe/London"


def excursions(b1: pl.DataFrame) -> pl.DataFrame:
    h1 = aggregate(b1, 60).with_columns(
        ma=pl.col("c").rolling_mean(20, min_samples=20),
        sd=pl.col("c").rolling_std(20, min_samples=20, ddof=0),
    ).select(pl.col("close_time").alias("h_ct"), "ma", "sd")
    m = b1.with_columns(close_time=pl.col("timestamp").dt.offset_by("1m")).join_asof(
        h1, left_on="close_time", right_on="h_ct", strategy="backward"
    ).filter(pl.col("sd") > 0).with_columns(
        zc=(pl.col("c") - pl.col("ma")) / pl.col("sd"),
        zh=(pl.col("h") - pl.col("ma")) / pl.col("sd"),
        zl=(pl.col("l") - pl.col("ma")) / pl.col("sd"),
    ).with_columns(side=pl.col("zc").sign()).filter(pl.col("side") != 0)
    m = m.with_columns(ex=(pl.col("side") != pl.col("side").shift(1)).fill_null(True).cast(pl.Int64).cum_sum())
    ct = pl.col("close_time")
    ex = m.group_by("ex", maintain_order=True).agg(
        side=pl.col("side").first(),
        start=pl.col("timestamp").first(),
        end=ct.last(),
        n_bars=pl.len(),
        peak=pl.when(pl.col("side").first() > 0).then(pl.col("zh").max()).otherwise(-pl.col("zl").min()),
        peak_time=pl.when(pl.col("side").first() > 0)
                    .then(ct.sort_by(pl.col("zh")).last()).otherwise(ct.sort_by(pl.col("zl")).first()),
    )
    ex = ex.slice(1, ex.height - 2)                          # drop the first/last (incomplete) runs
    pt = pl.col("peak_time")
    return ex.with_columns(
        weekday_start=pl.col("start").dt.convert_time_zone(NY).dt.weekday() <= 5,
        peak_in_window=session_window(pt, NY, time(7, 0), LONDON, time(16, 0))
                       & (pt.dt.convert_time_zone(NY).dt.weekday() <= 5),
        minutes=(pl.col("end") - pl.col("start")).dt.total_minutes(),
    ).filter("weekday_start")


def hazard(peaks: np.ndarray, a: float, w: float = 0.1) -> float:
    at_risk = (peaks >= a).sum()
    return float(((peaks >= a) & (peaks < a + w)).sum() / at_risk) if at_risk else float("nan")


def local_excess(peaks: np.ndarray, lvl: float) -> float:
    return hazard(peaks, lvl) - (hazard(peaks, lvl - 0.2) + hazard(peaks, lvl + 0.2)) / 2


def summarise(peaks: np.ndarray, minutes: np.ndarray, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    out = {"n_excursions": int(len(peaks)),
           "peak_quantiles": {q: float(np.quantile(peaks, q)) for q in (0.5, 0.75, 0.9, 0.95, 0.99)},
           "minutes_quantiles": {q: float(np.quantile(minutes, q)) for q in (0.5, 0.9)},
           "share_reaching_band": {b: float((peaks >= b).mean()) for b in BANDS}}
    grid = np.round(np.arange(0.1, 5.0 + 1e-9, 0.1), 1)
    boots = [peaks[rng.integers(0, len(peaks), len(peaks))] for _ in range(1000)]
    out["hazard"] = [{"from": float(g), "hazard": hazard(peaks, g), "at_risk": int((peaks >= g).sum()),
                      "ci95": [float(np.nanquantile([hazard(bp, g) for bp in boots], q)) for q in (0.025, 0.975)]}
                     for g in grid]
    fib_ex = {l: local_excess(peaks, l) for l in FIB}
    ctl_ex = {l: local_excess(peaks, l) for l in CONTROL}
    diff = np.mean(list(fib_ex.values())) - np.mean(list(ctl_ex.values()))
    bd = []
    for _ in range(2000):
        bp = peaks[rng.integers(0, len(peaks), len(peaks))]
        bd.append(np.nanmean([local_excess(bp, l) for l in FIB]) - np.nanmean([local_excess(bp, l) for l in CONTROL]))
    out["fib_test"] = {"fib_local_excess": fib_ex, "control_local_excess": ctl_ex,
                       "fib_minus_control": float(diff),
                       "ci95": [float(np.nanquantile(bd, 0.025)), float(np.nanquantile(bd, 0.975))]}
    out["fib_matters"] = bool(out["fib_test"]["ci95"][0] > 0)
    return out


def main(year: int) -> None:
    ex = excursions(mid_1m(year))
    res = {"year": year,
           "all": summarise(ex["peak"].to_numpy(), ex["minutes"].to_numpy()),
           "peak_in_window": summarise(ex.filter("peak_in_window")["peak"].to_numpy(),
                                       ex.filter("peak_in_window")["minutes"].to_numpy())}
    RUN.mkdir(parents=True, exist_ok=True)
    ex.write_parquet(RUN / f"excursions_{year}.parquet")
    (RUN / f"results_{year}.json").write_text(json.dumps(res, indent=2, default=str))
    for k in ("all", "peak_in_window"):
        r = res[k]
        print(f"\n== {k}: {r['n_excursions']} excursions; peak quantiles {r['peak_quantiles']}; minutes {r['minutes_quantiles']}")
        print("  share reaching band:", {b: round(v, 3) for b, v in r["share_reaching_band"].items()})
        print("  fib test:", {kk: (round(v, 4) if isinstance(v, float) else v) for kk, v in r["fib_test"].items() if kk in ("fib_minus_control", "ci95")}, "fib_matters", r["fib_matters"])
        print("  local excess fib:", {l: round(v, 3) for l, v in r["fib_test"]["fib_local_excess"].items()},
              " control:", {l: round(v, 3) for l, v in r["fib_test"]["control_local_excess"].items()})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2023)
    main(ap.parse_args().year)
