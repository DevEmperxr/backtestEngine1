"""Run 083 — how does the DAX (GER40) behave at the 09:00 Frankfurt cash open? Descriptive, 2023 only.

    .venv/Scripts/python.exe -m research.regime.dax_open_083

Per cash day (09:00–17:30 Frankfurt, mid prices from 1m bars):
- volatility (mean |1m change|) and median spread per 15 minutes of the day
- overnight gap (09:00 open vs previous 17:30 close): size, how often it fills, gap direction vs the first 30 minutes
- first 30 / 60 minutes: does their direction continue to 17:30 (momentum) or reverse?
- 15-minute opening range: first break side and the move from the break to 17:30 in the break direction
- when the day's high and low are set (share per half hour)
"""

from __future__ import annotations

import json
from datetime import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402

from lib.data import load_1s_data, resample  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "runs" / "083_dax_open_2023"
FRA = "Europe/Berlin"


def bars() -> pl.DataFrame:
    b = resample(load_1s_data(str(ROOT / "data" / "GER40_1s_2023.csv"), verbose=False), "1m")
    t = pl.col("timestamp").dt.convert_time_zone(FRA)
    return (b.select("timestamp", mo=(pl.col("bid_open") + pl.col("ask_open")) / 2,
                     mh=(pl.col("bid_high") + pl.col("ask_high")) / 2, ml=(pl.col("bid_low") + pl.col("ask_low")) / 2,
                     mc=(pl.col("bid_close") + pl.col("ask_close")) / 2, spr=pl.col("ask_close") - pl.col("bid_close"))
            .with_columns(day=t.dt.date(), clock=t.dt.time(), wd=t.dt.weekday(),
                          mod=t.dt.hour().cast(pl.Int32) * 60 + t.dt.minute().cast(pl.Int32))
            .filter(pl.col("wd") <= 5))


def at(cash: pl.DataFrame, hhmm: time, col: str = "mc") -> pl.DataFrame:
    """Per day: `col` of the 1m bar that starts at hhmm."""
    return cash.filter(pl.col("clock") == hhmm).select("day", pl.col(col))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    m = bars()
    res: dict = {}

    # 1) volatility and spread by 15 minutes (whole day, Frankfurt time)
    q = (m.with_columns(b15=(pl.col("mod") // 15) * 15, ab=(pl.col("mc") - pl.col("mo")).abs())
         .group_by("b15").agg(vol=pl.col("ab").mean(), spr=pl.col("spr").median(), n=pl.len()).sort("b15")
         .filter(pl.col("n") > 200))
    res["vol_spread_by_15m"] = {f"{b // 60:02d}:{b % 60:02d}": [round(v, 2), round(s, 2)]
                                for b, v, s in zip(q["b15"], q["vol"], q["spr"])}

    cash = m.filter((pl.col("clock") >= time(9, 0)) & (pl.col("clock") < time(17, 30)))
    day = (cash.group_by("day").agg(open=pl.col("mo").first(), close=pl.col("mc").last(), hi=pl.col("mh").max(),
                                    lo=pl.col("ml").min(), n=pl.len(),
                                    t_hi=pl.col("mod").get(pl.col("mh").arg_max()),
                                    t_lo=pl.col("mod").get(pl.col("ml").arg_min()))
           .filter(pl.col("n") >= 400).sort("day").with_columns(prev_close=pl.col("close").shift(1)))
    first_open = cash.filter(pl.col("clock") == time(9, 0)).select("day")
    day = day.join(first_open, on="day")      # needs a real 09:00 bar
    c0929 = at(cash, time(9, 29)).rename({"mc": "c30"})
    c0959 = at(cash, time(9, 59)).rename({"mc": "c60"})
    day = day.join(c0929, on="day").join(c0959, on="day").drop_nulls("prev_close")
    day = day.with_columns(gap=pl.col("open") - pl.col("prev_close"), r30=pl.col("c30") - pl.col("open"),
                           r60=pl.col("c60") - pl.col("open"), rest30=pl.col("close") - pl.col("c30"),
                           rest60=pl.col("close") - pl.col("c60"), day_rng=pl.col("hi") - pl.col("lo"))
    n = day.height
    res["days"] = n
    res["avg_cash_range_pts"] = round(day["day_rng"].mean(), 1)

    # 2) gap
    g = day.filter(pl.col("gap").abs() >= 5)
    filled = cash.join(day.select("day", "prev_close", "gap"), on="day").filter(pl.col("gap").abs() >= 5).with_columns(
        touch=((pl.col("gap") > 0) & (pl.col("ml") <= pl.col("prev_close"))) | ((pl.col("gap") < 0) & (pl.col("mh") >= pl.col("prev_close"))))
    fill_day = filled.group_by("day").agg(any=pl.col("touch").any(),
                                          by10=(pl.col("touch") & (pl.col("clock") < time(10, 0))).any())
    res["gap"] = {
        "median_abs_gap_pts": round(day["gap"].abs().median(), 1),
        "days_gap_ge_5pts": g.height,
        "filled_same_day_%": round(100 * fill_day["any"].mean(), 1),
        "filled_by_10:00_%": round(100 * fill_day["by10"].mean(), 1),
        "first30_same_direction_as_gap_%": round(100 * float((np.sign(g["gap"]) == np.sign(g["r30"])).mean()), 1),
        "first30_move_in_gap_direction_pts": round(float((np.sign(g["gap"]) * g["r30"]).mean()), 1),
    }

    # 3) does the opening move continue?
    def follow(first: str, rest: str) -> dict:
        s = np.sign(day[first].to_numpy())
        f = s * day[rest].to_numpy()
        return {"same_direction_%": round(100 * float((f > 0).mean()), 1),
                "avg_rest_of_day_in_open_direction_pts": round(float(f.mean()), 1),
                "t": round(float(f.mean() / (f.std(ddof=1) / np.sqrt(len(f)))), 2),
                "corr": round(float(np.corrcoef(day[first], day[rest])[0, 1]), 3),
                "avg_abs_first_pts": round(float(np.abs(day[first]).mean()), 1)}
    res["first30_then_rest"] = follow("r30", "rest30")
    res["first60_then_rest"] = follow("r60", "rest60")

    # 4) 15-minute opening range: first break after 09:15 and the move from the break to 17:30
    orr = cash.filter(pl.col("clock") < time(9, 15)).group_by("day").agg(orh=pl.col("mh").max(), orl=pl.col("ml").min())
    after = cash.filter(pl.col("clock") >= time(9, 15)).join(orr, on="day").join(day.select("day", "close"), on="day")
    brk = (after.with_columns(up=pl.col("mh") > pl.col("orh"), dn=pl.col("ml") < pl.col("orl"))
           .filter(pl.col("up") | pl.col("dn")).sort("day", "mod").group_by("day").first()
           .with_columns(side=pl.when(pl.col("up") & ~pl.col("dn")).then(1).when(pl.col("dn") & ~pl.col("up")).then(-1).otherwise(0))
           .filter(pl.col("side") != 0)
           .with_columns(lvl=pl.when(pl.col("side") == 1).then(pl.col("orh")).otherwise(pl.col("orl")),
                         or_w=pl.col("orh") - pl.col("orl"))
           .with_columns(follow=pl.col("side") * (pl.col("close") - pl.col("lvl"))))
    res["orb15"] = {"days_with_break": brk.height, "median_or_width_pts": round(brk["or_w"].median(), 1),
                    "median_break_time": str(time(int(brk["mod"].median()) // 60, int(brk["mod"].median()) % 60)),
                    "closed_beyond_break_level_%": round(100 * float((brk["follow"] > 0).mean()), 1),
                    "avg_break_to_close_pts": round(brk["follow"].mean(), 1),
                    "t": round(float(brk["follow"].mean() / (brk["follow"].std() / np.sqrt(brk.height))), 2)}

    # 5) when are the day's high and low set? (half-hour buckets from 09:00)
    ext = pl.concat([day.select(m=pl.col("t_hi")), day.select(m=pl.col("t_lo"))])
    hb = ext.with_columns(b=((pl.col("m") - 540) // 30)).group_by("b").len().sort("b")
    res["high_or_low_set_by_half_hour_%"] = {f"{(540 + 30 * b) // 60:02d}:{(540 + 30 * b) % 60:02d}": round(100 * k / (2 * n), 1)
                                              for b, k in zip(hb["b"], hb["len"])}
    res["day_high_or_low_in_first_hour_%"] = round(100 * float(((day["t_hi"] < 600) | (day["t_lo"] < 600)).mean()), 1)

    # chart
    fig, ax = plt.subplots(2, 2, figsize=(14, 9))
    a = ax[0, 0]
    x = [b / 60 for b in q["b15"]]
    a.bar(x, q["vol"], width=0.23, color="#2E6BD8")
    a.set_ylabel("avg |1m move| (points)")
    a2 = a.twinx()
    a2.plot(x, q["spr"], color="#D84A2E", lw=1.5)
    a2.set_ylabel("median spread (points)", color="#D84A2E")
    a.axvline(9, color="k", lw=0.8, ls="--")
    a.axvline(17.5, color="k", lw=0.8, ls="--")
    a.set_title("volatility (bars) and spread (red) by time of day, Frankfurt; dashed = cash open/close", fontsize=9)
    a = ax[0, 1]
    ks = list(res["high_or_low_set_by_half_hour_%"].keys())
    a.bar(ks, list(res["high_or_low_set_by_half_hour_%"].values()), color="#2E9E5B")
    a.set_title(f"when the cash-session high or low is set (% of {2 * n} extremes)", fontsize=9)
    a.tick_params(axis="x", rotation=60, labelsize=7)
    a = ax[1, 0]
    a.scatter(day["r30"], day["rest30"], s=10, alpha=0.6)
    a.axhline(0, color="#888", lw=0.7)
    a.axvline(0, color="#888", lw=0.7)
    a.set_xlabel("first 30 min (09:00–09:30), points")
    a.set_ylabel("rest of day (09:30–17:30), points")
    a.set_title(f"does the first 30 min continue? corr {res['first30_then_rest']['corr']}", fontsize=9)
    a = ax[1, 1]
    d = day.sort("day")
    a.plot(d["day"].to_list(), (np.sign(d["r30"]) * d["rest30"]).cum_sum().to_list(), label="with first 30 min (09:30 -> 17:30)")
    a.plot(d["day"].to_list(), (np.sign(d["r60"]) * d["rest60"]).cum_sum().to_list(), label="with first 60 min (10:00 -> 17:30)")
    b2 = brk.sort("day")
    a.plot(b2["day"].to_list(), b2["follow"].cum_sum().to_list(), label="15-min opening-range break -> 17:30")
    gg = d.filter(pl.col("gap").abs() >= 5)
    a.plot(gg["day"].to_list(), (-np.sign(gg["gap"]) * gg["r30"]).cum_sum().to_list(), label="fade the gap 09:00 -> 09:30")
    a.axhline(0, color="#888", lw=0.7)
    a.legend(fontsize=8)
    a.set_title("cumulative points, before costs (descriptive, not strategies)", fontsize=9)
    fig.suptitle(f"DAX (GER40) at the cash open, 2023 ({n} days)", fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT / "dax_open_2023.png", dpi=105)
    (OUT / "results.json").write_text(json.dumps(res, indent=2, default=str))
    print(json.dumps(res, indent=1))
    print(OUT / "dax_open_2023.png")


if __name__ == "__main__":
    main()
