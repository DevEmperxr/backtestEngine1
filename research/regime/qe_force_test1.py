"""Run 055 — Test 1: does the net Fed-vs-ECB QE/QT force (qe_force.py) predict EUR/USD over the next
20 (primary) / 5 trading days? Daily DEXUSEU 2009–2020 only (user permission: Test 1 only).
Pass bar pre-registered in research/runs/055_qe_qt_force_test1/summary.md.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402

from research.regime import qe_force  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "runs" / "055_qe_qt_force_test1"
START, END = date(2009, 1, 1), date(2020, 12, 31)


def nw_ols(y: np.ndarray, X: np.ndarray, lags: int) -> tuple[np.ndarray, np.ndarray]:
    """OLS with Newey–West (Bartlett) standard errors. X includes the constant column."""
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    u = y - X @ beta
    XtX_inv = np.linalg.inv(X.T @ X)
    Xu = X * u[:, None]
    S = Xu.T @ Xu
    for l in range(1, lags + 1):
        w = 1 - l / (lags + 1)
        G = Xu[l:].T @ Xu[:-l]
        S += w * (G + G.T)
    cov = XtX_inv @ S @ XtX_inv
    return beta, beta / np.sqrt(np.diag(cov))


def frame(version: str, data: dict) -> pl.DataFrame:
    fx = data["DEXUSEU"].filter(pl.col("date") <= END).sort("date")     # nothing after 2020 is read
    idx = qe_force.build(data, fx["date"], version=version)
    d = fx.rename({"date": "day", "v": "px"}).join(idx, on="day").with_columns(lp=pl.col("px").log())
    for h in (5, 20):
        d = d.with_columns((pl.col("lp").shift(-h) - pl.col("lp")).alias(f"fwd{h}"))
    d = d.with_columns(mom20=pl.col("lp") - pl.col("lp").shift(20))
    return d.filter((pl.col("day") >= START) & pl.col("z").is_not_null())


def test(d: pl.DataFrame, h: int) -> dict:
    x = d.drop_nulls([f"fwd{h}", "mom20"])
    y = x[f"fwd{h}"].to_numpy() * 100                                   # percent
    z = x["z"].to_numpy()
    one = np.ones_like(z)
    b1, t1 = nw_ols(y, np.column_stack([one, z]), h)
    b2, t2 = nw_ols(y, np.column_stack([one, z, x["mom20"].to_numpy() * 100]), h)
    st = x.group_by("state").agg(days=pl.len(), mean_fwd_pct=(pl.col(f"fwd{h}").mean() * 100).round(3)).sort("state")
    m = dict(zip(st["state"].to_list(), st["mean_fwd_pct"].to_list()))
    halves = {}
    for name, a, b in (("2009-2014", date(2009, 1, 1), date(2014, 12, 31)), ("2015-2020", date(2015, 1, 1), END)):
        xs = x.filter((pl.col("day") >= a) & (pl.col("day") <= b))
        bh, th = nw_ols(xs[f"fwd{h}"].to_numpy() * 100, np.column_stack([np.ones(xs.height), xs["z"].to_numpy()]), h)
        halves[name] = {"b": round(float(bh[1]), 4), "t": round(float(th[1]), 2)}
    res = {
        "days": x.height,
        "state_days_and_mean_fwd_pct": st.to_dicts(),
        "long_minus_short_pct": round(m.get(1, np.nan) - m.get(-1, np.nan), 3) if 1 in m and -1 in m else None,
        "b_z": round(float(b1[1]), 4), "t_z": round(float(t1[1]), 2),
        "b_z_with_mom": round(float(b2[1]), 4), "t_z_with_mom": round(float(t2[1]), 2),
        "b_mom": round(float(b2[2]), 4), "t_mom": round(float(t2[2]), 2),
        "halves": halves,
    }
    res["pass"] = bool(res["long_minus_short_pct"] is not None and res["long_minus_short_pct"] > 0
                       and res["b_z"] > 0 and res["t_z"] > 2 and res["b_z_with_mom"] > 0 and res["t_z_with_mom"] > 2
                       and all(v["b"] > 0 for v in halves.values()))
    return res


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = qe_force.load()
    res = {}
    frames = {}
    for version in ("total", "bonds"):
        d = frame(version, data)
        frames[version] = d
        res[version] = {f"{h}d": test(d, h) for h in (20, 5)}
        print(f"\n===== version: {version} =====")
        for h, r in res[version].items():
            print(f"-- horizon {h}: pass={r['pass']}")
            for k, v in r.items():
                if k != "pass":
                    print(f"   {k}: {v}")
    res["VERDICT (primary = total, 20d)"] = "PASS" if res["total"]["20d"]["pass"] else "FAIL"
    print("\nVERDICT:", res["VERDICT (primary = total, 20d)"])
    (OUT / "results.json").write_text(json.dumps(res, indent=2, default=str))

    d = frames["total"]
    x = d["day"].to_list()
    fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(13, 10), sharex=True, gridspec_kw={"height_ratios": [1.3, 1, 1]})
    a1.plot(x, d["px"].to_list(), color="#222", lw=1)
    stt = d["state"].to_list()
    for i in range(len(x) - 1):
        if stt[i] == 1:
            a1.axvspan(x[i], x[i + 1], color="#2E9E5B", alpha=0.15, lw=0)
        elif stt[i] == -1:
            a1.axvspan(x[i], x[i + 1], color="#D84A2E", alpha=0.15, lw=0)
    a1.set_title("EUR/USD (green = 'long tide' z > +1, red = 'short tide' z < -1)", fontsize=10)
    a2.plot(x, d["force_us"].to_list(), color="#4E79A7", lw=1.2, label="Fed force (13w change, % of US GDP)")
    a2.plot(x, d["force_ea"].to_list(), color="#E8A33D", lw=1.2, label="ECB force (13w change, % of EA GDP)")
    a2.axhline(0, color="#888", lw=0.7)
    a2.legend(fontsize=8)
    a2.set_title("each central bank's balance-sheet push (positive = QE, negative = QT)", fontsize=10)
    a3.plot(x, d["z"].to_list(), color="#B07AA1", lw=1.2)
    for lv in (1, -1):
        a3.axhline(lv, color="#888", lw=0.7, ls="--")
    a3.axhline(0, color="#555", lw=0.7)
    a3.set_title("net force z (Fed minus ECB, scaled); above +1 favours EUR/USD up, below -1 down", fontsize=10)
    for a in (a1, a2, a3):
        a.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT / "q_tide_2009_2020.png", dpi=110)
    print(OUT / "q_tide_2009_2020.png")


if __name__ == "__main__":
    main()
