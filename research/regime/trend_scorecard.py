"""Research 020 — trend-detector scorecard (see research/runs/020_trend_detector_scorecard).

    python -m research.regime.trend_scorecard --year 2023

For each timeframe (5m, 15m, 1h) and each of seven past-only detectors, measures how
well the detector at bar t ranks the NEXT 20 bars' efficiency ratio (FER), against a
cross-fitted time-of-day baseline and a sign-randomised (volatility-preserving) null.
No trades, no P&L. Writes results.json into the run folder.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, time, timezone
from pathlib import Path

import numpy as np
import polars as pl

from lib.data import load_1s_data, resample
from lib.signals import (adx, atr, choppiness, efficiency_ratio, return_autocorr,
                         rolling_r2, session_window, sma, variance_ratio)

RUN = Path(__file__).resolve().parents[1] / "runs" / "020_trend_detector_scorecard"
DATA = Path(__file__).resolve().parents[2] / "data"
H = 20                                   # look-ahead bars (= MA20 span)
TFS = {"5m": 5, "15m": 15, "1h": 60}
N_BOOT, N_NULL = 2000, 20
CI_LEVEL = 0.998                         # Bonferroni 0.05 / 21
NY, LONDON = "America/New_York", "Europe/London"


# --------------------------------------------------------------------------- bars
def mid_1m(year: int) -> pl.DataFrame:
    b = resample(load_1s_data(str(DATA / f"EURUSD_1s_{year}.csv"), verbose=False), "1m")
    m = lambda f: (pl.col(f"bid_{f}") + pl.col(f"ask_{f}")) / 2
    return b.select("timestamp", o=m("open"), h=m("high"), l=m("low"), c=m("close"))


def surrogate_1m(b: pl.DataFrame, seed: int) -> pl.DataFrame:
    """Random sign per 1m close-to-close return; a flipped bar's shape is mirrored.
    Keeps every bar's size, volatility clustering and time-of-day volatility."""
    rng = np.random.default_rng(seed)
    c = b["c"].to_numpy()
    r = np.diff(c, prepend=c[0])
    s = rng.choice([-1.0, 1.0], size=len(c))
    nc = c[0] + np.cumsum(s * r)
    o, h, l = (b[k].to_numpy() - c for k in ("o", "h", "l"))   # offsets from own close
    flip = s < 0
    no = np.where(flip, -o, o) + nc
    nh = np.where(flip, -l, h) + nc
    nl = np.where(flip, -h, l) + nc
    return pl.DataFrame({"timestamp": b["timestamp"], "o": no, "h": nh, "l": nl, "c": nc})


def aggregate(b1: pl.DataFrame, minutes: int) -> pl.DataFrame:
    if minutes == 1:
        out = b1
    else:
        out = (b1.group_by_dynamic("timestamp", every=f"{minutes}m", label="left", closed="left")
               .agg(pl.col("o").first(), pl.col("h").max(), pl.col("l").min(), pl.col("c").last()))
    return out.with_columns(close_time=pl.col("timestamp").dt.offset_by(f"{minutes}m"))


# ---------------------------------------------------------------------- features
DETECTORS = ["ER20", "ADX14", "SLOPE", "R2_20", "CHOP14_inv", "VR4_100", "AC1_50"]


def features(bars: pl.DataFrame, minutes: int) -> pl.DataFrame:
    c, h, l = pl.col("c"), pl.col("h"), pl.col("l")
    step = pl.duration(minutes=minutes * H)
    path_fwd = c.diff().abs().rolling_sum(H, min_samples=H).shift(-H)
    return bars.with_columns(
        ER20=efficiency_ratio(c, 20),
        ADX14=adx(h, l, c, 14),
        SLOPE=(sma(c, 20) - sma(c, 20).shift(5)).abs() / atr(h, l, c, 14),
        R2_20=rolling_r2(c, 20),
        CHOP14_inv=-choppiness(h, l, c, 14),
        VR4_100=variance_ratio(c, 4, 100),
        AC1_50=return_autocorr(c, 50),
        # label only (future): efficiency ratio of bars t+1..t+20
        FER=pl.when(path_fwd > 0).then((c.shift(-H) - c).abs() / path_fwd),
        _contig=(pl.col("timestamp").shift(-H) - pl.col("timestamp")) == step,
    )


def readings(f: pl.DataFrame) -> pl.DataFrame:
    ct = pl.col("close_time")
    inwin = session_window(ct, NY, time(7, 0), LONDON, time(16, 0)) & (ct.dt.convert_time_zone(NY).dt.weekday() <= 5)
    ny = ct.dt.convert_time_zone(NY)
    return f.filter(inwin & pl.col("_contig") & pl.col("FER").is_not_null()).with_columns(
        day=ny.dt.date(), slot=ny.dt.strftime("%H:%M"),
        half=pl.when(pl.col("timestamp").dt.month() <= 6).then(pl.lit("H1")).otherwise(pl.lit("H2")),
    )


# ------------------------------------------------------------------------ stats
def _rank(x: np.ndarray) -> np.ndarray:
    return pl.Series(x).rank("average").to_numpy().astype(float)


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    return float(np.corrcoef(_rank(x), _rank(y))[0, 1])


def boot_ci(x: np.ndarray, y: np.ndarray, day: np.ndarray, level: float, seed: int = 0):
    """Day-block bootstrap of the Pearson correlation of global ranks, via per-day
    sufficient statistics (fast and exact for that statistic)."""
    rx, ry = _rank(x), _rank(y)
    uniq, inv = np.unique(day, return_inverse=True)
    k = len(uniq)
    S = np.zeros((k, 6))
    for col, v in enumerate((np.ones_like(rx), rx, ry, rx * rx, ry * ry, rx * ry)):
        S[:, col] = np.bincount(inv, weights=v, minlength=k)
    rng = np.random.default_rng(seed)
    W = rng.multinomial(k, np.full(k, 1 / k), size=N_BOOT)       # day counts per resample
    T = W @ S
    n, sx, sy, sxx, syy, sxy = T.T
    cov = sxy / n - sx * sy / n ** 2
    vx, vy = sxx / n - (sx / n) ** 2, syy / n - (sy / n) ** 2
    r = cov / np.sqrt(vx * vy)
    a = (1 - level) / 2
    return float(np.quantile(r, a)), float(np.quantile(r, 1 - a))


def tod_residual(r: pl.DataFrame) -> np.ndarray:
    """FER minus its time-of-day slot mean, cross-fitted between halves."""
    means = {hf: r.filter(pl.col("half") == hf).group_by("slot").agg(m=pl.col("FER").mean())
             for hf in ("H1", "H2")}
    other = {"H1": "H2", "H2": "H1"}
    parts = []
    for hf in ("H1", "H2"):
        part = r.with_row_index("_i").filter(pl.col("half") == hf).join(
            means[other[hf]], on="slot", how="left")
        parts.append(part.select("_i", res=pl.col("FER") - pl.col("m").fill_null(pl.col("FER").mean())))
    return pl.concat(parts).sort("_i")["res"].to_numpy()


def score_tf(real: pl.DataFrame, nulls: list[pl.DataFrame]) -> dict:
    out = {"n_readings": real.height, "n_days": real["day"].n_unique()}
    fer = real["FER"].to_numpy()
    day = real["day"].cast(pl.Utf8).to_numpy()
    res = tod_residual(real)
    tod_pred = fer - res
    out["time_of_day_baseline_rho"] = spearman(tod_pred, fer)
    out["mean_FER"] = float(fer.mean())
    for d in DETECTORS:
        m = real[d].is_not_null().to_numpy()
        x, y = real[d].to_numpy()[m], fer[m]
        rho = spearman(x, y)
        q = np.quantile(x, [0.2, 0.8])
        null_rhos = []
        for nr in nulls:
            mm = nr[d].is_not_null().to_numpy()
            null_rhos.append(spearman(nr[d].to_numpy()[mm], nr["FER"].to_numpy()[mm]))
        halves = {}
        for hf in ("H1", "H2"):
            hm = (real["half"] == hf).to_numpy() & m
            halves[hf] = spearman(real[d].to_numpy()[hm], fer[hm])
        partial = spearman(x, res[m])
        out[d] = {
            "rho": rho,
            "ci_998": boot_ci(x, y, day[m], CI_LEVEL),
            "ci_95": boot_ci(x, y, day[m], 0.95),
            "partial_rho_ex_time_of_day": partial,
            "partial_ci_998": boot_ci(x, res[m], day[m], CI_LEVEL),
            "top_minus_bottom_quintile_FER": float(y[x >= q[1]].mean() - y[x <= q[0]].mean()),
            "null_rho_min": float(min(null_rhos)), "null_rho_max": float(max(null_rhos)),
            "null_rho_mean": float(np.mean(null_rhos)),
            "rho_H1": halves["H1"], "rho_H2": halves["H2"],
        }
        r_ = out[d]
        r_["useful"] = bool(r_["ci_998"][0] > 0 and r_["rho"] > r_["null_rho_max"]
                            and r_["partial_ci_998"][0] > 0 and r_["rho_H1"] > 0 and r_["rho_H2"] > 0)
        r_["weak"] = bool(not r_["useful"] and r_["ci_95"][0] > 0)
    return out


def main(year: int) -> None:
    b1 = mid_1m(year)
    result = {"year": year, "horizon_bars": H, "ci_level": CI_LEVEL}
    for tf, minutes in TFS.items():
        real = readings(features(aggregate(b1, minutes), minutes))
        nulls = []
        for seed in range(1, N_NULL + 1):
            sb = surrogate_1m(b1, seed)
            sr = features(aggregate(sb, minutes), minutes)
            # same reading rows as the real data (same timestamps)
            nulls.append(sr.join(real.select("timestamp"), on="timestamp", how="inner"))
        result[tf] = score_tf(real, nulls)
        print(f"{tf}: {result[tf]['n_readings']} readings, ToD rho {result[tf]['time_of_day_baseline_rho']:+.3f}", flush=True)
        for d in DETECTORS:
            r = result[tf][d]
            flag = "USEFUL" if r["useful"] else ("weak" if r["weak"] else "")
            print(f"  {d:<11} rho {r['rho']:+.3f} 99.8%[{r['ci_998'][0]:+.3f},{r['ci_998'][1]:+.3f}] "
                  f"partial {r['partial_rho_ex_time_of_day']:+.3f}[{r['partial_ci_998'][0]:+.3f},{r['partial_ci_998'][1]:+.3f}] "
                  f"null[{r['null_rho_min']:+.3f},{r['null_rho_max']:+.3f}] H1 {r['rho_H1']:+.3f} H2 {r['rho_H2']:+.3f} "
                  f"Q5-Q1 {r['top_minus_bottom_quintile_FER']:+.3f} {flag}", flush=True)
    RUN.mkdir(parents=True, exist_ok=True)
    (RUN / f"results_{year}.json").write_text(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2023)
    main(ap.parse_args().year)
