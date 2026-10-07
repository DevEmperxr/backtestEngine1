"""Run 056 — monetary tide: 2-year rate-gap change + QE/QT force (combined), and the Wu–Xia shadow-rate
gap, as predictors of EUR/USD over the next 20 / 5 trading days. Daily DEXUSEU 2009–2020 only.
Pre-registered in research/runs/056_monetary_tide/summary.md (pass: t > 2.5).

All scores are EUR/USD-signed: positive = should push EUR/USD up.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import polars as pl  # noqa: E402

from research.regime import qe_force  # noqa: E402
from research.regime.qe_force_test1 import nw_ols  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
MACRO = ROOT / "data" / "macro"
OUT = ROOT / "research" / "runs" / "056_monetary_tide"
START, END = date(2009, 1, 1), date(2020, 12, 31)
T_BAR = 2.5


def _zscore(x: pl.Expr) -> pl.Expr:
    return x / x.shift(1).rolling_std(756, min_samples=756)


def _daily(path_or_df, lag_days: int) -> pl.DataFrame:
    return path_or_df.select(avail=pl.col("date") + timedelta(days=lag_days), v="v").sort("avail")


def _ecb_2y() -> pl.DataFrame:
    d = pl.read_csv(MACRO / "ECB_YC_AAA_2Y.csv", infer_schema_length=0)
    return d.select(date=pl.col("TIME_PERIOD").str.to_date(), v=pl.col("OBS_VALUE").cast(pl.Float64)).drop_nulls()


def _shadow(name: str) -> pl.DataFrame:
    x = pd.read_excel(MACRO / f"shadow_{name}.xlsx", header=None, engine="xlrd")
    rows = [(date(int(ym) // 100, int(ym) % 100, 1), float(v)) for ym, v in zip(x[0], x[1])]
    m = pl.DataFrame(rows, schema={"month": pl.Date, "v": pl.Float64}, orient="row")
    # usable 30 days after the month ends
    return m.select(avail=pl.col("month").dt.offset_by("1mo") + timedelta(days=30), v="v")


def build() -> pl.DataFrame:
    data = qe_force.load()
    fx = data["DEXUSEU"].filter(pl.col("date") <= END).sort("date").rename({"date": "day", "v": "px"})
    cal = fx.select("day")

    def asof(frame: pl.DataFrame, name: str) -> pl.DataFrame:
        return cal.join_asof(frame.rename({"v": name}), left_on="day", right_on="avail",
                             strategy="backward").drop("avail")

    us2 = qe_force._fred("DGS2", False)
    d = (fx.join(asof(_daily(us2, 1), "us2"), on="day")
         .join(asof(_daily(_ecb_2y(), 1), "ea2"), on="day")
         .join(asof(_shadow("us").sort("avail"), "sh_us"), on="day")
         .join(asof(_shadow("ea").sort("avail"), "sh_ea"), on="day")
         .join(qe_force.build(data, fx["day"], version="total").select("day", zF="z"), on="day"))
    d = d.with_columns(gap=pl.col("us2") - pl.col("ea2"), sgap=pl.col("sh_us") - pl.col("sh_ea"))
    d = d.with_columns(R=pl.col("gap") - pl.col("gap").shift(20))
    # shadow: change over the last 3 months of the (stepwise daily) monthly gap ~ 63 trading days
    d = d.with_columns(dS=pl.col("sgap") - pl.col("sgap").shift(63))
    d = d.with_columns(rate_score=-_zscore(pl.col("R")), shadow_score=-_zscore(pl.col("dS")))
    d = d.with_columns(C=(pl.col("rate_score") + pl.col("zF")) / 2)
    d = d.with_columns(combined_score=_zscore(pl.col("C")))
    d = d.with_columns(lp=pl.col("px").log())
    for h in (5, 20):
        d = d.with_columns((pl.col("lp").shift(-h) - pl.col("lp")).alias(f"fwd{h}"))
    return d.with_columns(mom20=pl.col("lp") - pl.col("lp").shift(20)).filter(pl.col("day") >= START)


def test(d: pl.DataFrame, score: str, h: int) -> dict:
    x = d.drop_nulls([score, f"fwd{h}", "mom20"]).with_columns(
        state=pl.when(pl.col(score) > 1).then(1).when(pl.col(score) < -1).then(-1).otherwise(0))
    y = x[f"fwd{h}"].to_numpy() * 100
    s = x[score].to_numpy()
    one = np.ones_like(s)
    b1, t1 = nw_ols(y, np.column_stack([one, s]), h)
    b2, t2 = nw_ols(y, np.column_stack([one, s, x["mom20"].to_numpy() * 100]), h)
    st = x.group_by("state").agg(days=pl.len(), mean_fwd_pct=(pl.col(f"fwd{h}").mean() * 100).round(3)).sort("state")
    m = dict(zip(st["state"].to_list(), st["mean_fwd_pct"].to_list()))
    halves = {}
    for name, a, b in (("2009-2014", date(2009, 1, 1), date(2014, 12, 31)), ("2015-2020", date(2015, 1, 1), END)):
        xs = x.filter((pl.col("day") >= a) & (pl.col("day") <= b))
        bh, th = nw_ols(xs[f"fwd{h}"].to_numpy() * 100, np.column_stack([np.ones(xs.height), xs[score].to_numpy()]), h)
        halves[name] = {"b": round(float(bh[1]), 4), "t": round(float(th[1]), 2)}
    ls = round(m[1] - m[-1], 3) if 1 in m and -1 in m else None
    r = {"days": x.height, "first_day": str(x["day"][0]), "states": st.to_dicts(), "long_minus_short_pct": ls,
         "b": round(float(b1[1]), 4), "t": round(float(t1[1]), 2),
         "b_with_mom": round(float(b2[1]), 4), "t_with_mom": round(float(t2[1]), 2), "halves": halves}
    r["pass"] = bool(ls is not None and ls > 0 and r["b"] > 0 and r["t"] > T_BAR and r["b_with_mom"] > 0
                     and r["t_with_mom"] > T_BAR and all(v["b"] > 0 for v in halves.values()))
    return r


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    d = build()
    res = {}
    for score in ("combined_score", "shadow_score", "rate_score"):
        res[score] = {f"{h}d": test(d, score, h) for h in (20, 5)}
        print(f"\n===== {score} =====")
        for h, r in res[score].items():
            print(f"-- {h}: pass={r['pass']} | days {r['days']} from {r['first_day']} | long-short {r['long_minus_short_pct']}% "
                  f"| t {r['t']} | t with momentum {r['t_with_mom']} | halves {r['halves']}")
            print(f"   states: {r['states']}")
    res["corr_between_scores"] = {
        "rate_vs_QE": round(d.select(pl.corr("rate_score", "zF")).item(), 2),
        "combined_vs_shadow": round(d.drop_nulls(["combined_score", "shadow_score"]).select(pl.corr("combined_score", "shadow_score")).item(), 2),
    }
    res["VERDICT"] = {"A combined (20d)": "PASS" if res["combined_score"]["20d"]["pass"] else "FAIL",
                      "B shadow (20d)": "PASS" if res["shadow_score"]["20d"]["pass"] else "FAIL"}
    print("\ncorrelations:", res["corr_between_scores"])
    print("VERDICT:", res["VERDICT"])
    (OUT / "results.json").write_text(json.dumps(res, indent=2, default=str))

    x = d["day"].to_list()
    fig, ax = plt.subplots(4, 1, figsize=(13, 12), sharex=True, gridspec_kw={"height_ratios": [1.3, 1, 1, 1]})
    ax[0].plot(x, d["px"].to_list(), color="#222", lw=1)
    ax[0].set_title("EUR/USD (shaded by the combined monetary tide: green > +1, red < -1)", fontsize=10)
    cs = d["combined_score"].to_list()
    for i in range(len(x) - 1):
        if cs[i] is not None and cs[i] > 1:
            ax[0].axvspan(x[i], x[i + 1], color="#2E9E5B", alpha=0.15, lw=0)
        elif cs[i] is not None and cs[i] < -1:
            ax[0].axvspan(x[i], x[i + 1], color="#D84A2E", alpha=0.15, lw=0)
    ax[1].plot(x, d["gap"].to_list(), color="#4E79A7", lw=1.1, label="US 2y − euro 2y (%)")
    ax[1].plot(x, d["sgap"].to_list(), color="#E8A33D", lw=1.1, label="US − euro shadow rate (%)")
    ax[1].legend(fontsize=8); ax[1].set_title("rate gaps", fontsize=10)
    ax[2].plot(x, d["combined_score"].to_list(), color="#B07AA1", lw=1.1)
    ax[2].set_title("combined monetary tide score (rates + QE/QT); > +1 favours EUR/USD up", fontsize=10)
    ax[3].plot(x, d["shadow_score"].to_list(), color="#59A14F", lw=1.1)
    ax[3].set_title("shadow-rate tide score; > +1 favours EUR/USD up", fontsize=10)
    for a in ax[2:]:
        for lv in (1, -1):
            a.axhline(lv, color="#888", lw=0.7, ls="--")
        a.axhline(0, color="#555", lw=0.6)
    for a in ax:
        a.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT / "monetary_tide_2009_2020.png", dpi=110)
    print(OUT / "monetary_tide_2009_2020.png")


if __name__ == "__main__":
    main()
