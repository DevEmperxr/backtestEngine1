"""Run 085 — DELIBERATE OVERFIT (learning exercise, user-approved once): why did 084 a/b fail on GER40 2023, and what
does over-fitting the stop / exit / filters look like? NOT evidence of anything. 2024 is not touched.

    .venv/Scripts/python.exe -m research.regime.overfit_085

Takes the 084 engine entries (time, side, price; news blackout already applied) and re-simulates exits on 1m bid/ask
bars: stop (fixed points or the original 084 stop) checked on the adverse side (ask high for shorts, bid low for
longs), else exit at the open of the bar starting at the exit time on the closing side. FTMO top-up 0.15 pt per trade.
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
RUN84 = ROOT / "research" / "runs" / "084_dax_open_reversal"
OUT = ROOT / "research" / "runs" / "085_dax_overfit_lesson"
FRA = "Europe/Berlin"
TOPUP = 0.15
STOPS = [10, 15, 20, 30, 40, 60, 80, 100, 150, 200, 300]
EXITS = [time(10, 0), time(10, 30), time(11, 0), time(12, 0), time(13, 0), time(14, 0), time(15, 30), time(17, 25)]


def load_bars() -> dict:
    b = resample(load_1s_data(str(ROOT / "data" / "GER40_1s_2023.csv"), verbose=False), "1m")
    t = pl.col("timestamp").dt.convert_time_zone(FRA)
    b = b.with_columns(day=t.dt.date(), mod=t.dt.hour().cast(pl.Int32) * 60 + t.dt.minute().cast(pl.Int32))
    b = b.filter((pl.col("mod") >= 540) & (pl.col("mod") < 1050)).sort("timestamp")
    days = {}
    for (d,), g in b.group_by("day"):
        days[d] = {k: g[k].to_numpy() for k in ("mod", "ask_high", "bid_low", "ask_open", "bid_open", "ask_low", "bid_high")}
        days[d]["ts"] = g["timestamp"].to_list()
    return days


def sim(days: dict, tr: pl.DataFrame, stop: float | None, exit_t: time) -> np.ndarray:
    """Net points per trade. stop=None -> each trade's original 084 stop (sl_pips)."""
    xm = exit_t.hour * 60 + exit_t.minute
    out = np.full(tr.height, np.nan)
    for i, (et, d, ep, sl0) in enumerate(zip(tr["entry_time"], tr["direction"], tr["entry_price"], tr["sl_pips"])):
        day = et.astimezone(__import__("zoneinfo").ZoneInfo(FRA)).date()
        g = days.get(day)
        if g is None:
            continue
        em = et.astimezone(__import__("zoneinfo").ZoneInfo(FRA))
        em = em.hour * 60 + em.minute
        s = sl0 if stop is None else stop
        if xm <= em:
            continue
        idx = np.where((g["mod"] >= em) & (g["mod"] < xm))[0]
        xi = np.where(g["mod"] >= xm)[0]
        if len(idx) == 0 or len(xi) == 0:
            continue
        if d == "short":
            hit = np.where(g["ask_high"][idx] >= ep + s)[0]
            pnl = -s if len(hit) else ep - g["ask_open"][xi[0]]
        else:
            hit = np.where(g["bid_low"][idx] <= ep - s)[0]
            pnl = -s if len(hit) else g["bid_open"][xi[0]] - ep
        out[i] = pnl - TOPUP
    return out


def stats(p: np.ndarray, risk: np.ndarray) -> dict:
    m = ~np.isnan(p)
    p, risk = p[m], risk[m]
    r = p / risk
    return {"n": int(m.sum()), "pts_per_trade": round(float(p.mean()), 2), "R_per_trade": round(float(r.mean()), 3),
            "win_%": round(100 * float((p > 0).mean()), 1)}


def grid(days, tr, label) -> tuple[np.ndarray, np.ndarray]:
    R = np.zeros((len(STOPS), len(EXITS)))
    P = np.zeros_like(R)
    for i, s in enumerate(STOPS):
        for j, x in enumerate(EXITS):
            p = sim(days, tr, s, x)
            st = stats(p, np.full(len(p), float(s)))
            R[i, j], P[i, j] = st["R_per_trade"], st["pts_per_trade"]
    return R, P


def heat(ax, M, title, fmt):
    v = np.nanmax(np.abs(M))
    ax.imshow(M, cmap="RdYlGn", vmin=-v, vmax=v, aspect="auto")
    ax.set_xticks(range(len(EXITS)), [x.strftime("%H:%M") for x in EXITS], fontsize=8)
    ax.set_yticks(range(len(STOPS)), [f"{s}" for s in STOPS], fontsize=8)
    ax.set_xlabel("exit time (Frankfurt)")
    ax.set_ylabel("stop (points)")
    ax.set_title(title, fontsize=9)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, fmt.format(M[i, j]), ha="center", va="center", fontsize=6.5)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    days = load_bars()
    res: dict = {}
    trades = {v: pl.read_parquet(RUN84 / f"{v}_GER40_2023" / "trades.parquet").sort("entry_time") for v in ("a", "b")}

    for v, tr in trades.items():
        r: dict = {}
        # sanity: re-simulate the original rules and compare with the engine
        p0 = sim(days, tr, None, time(17, 25))
        r["resim_original"] = stats(p0, tr["sl_pips"].to_numpy())
        r["engine_original_R"] = round(float((tr["pips"] / tr["sl_pips"]).mean()), 3)
        # 1) why: stopped trades that would have won if held to 17:25 with no stop
        nostop = sim(days, tr, 10_000.0, time(17, 25))
        stopped = (tr["exit_reason"] == "sl").to_numpy()
        r["no_stop_hold_to_1725"] = {"pts_per_trade": round(float(np.nanmean(nostop)), 2),
                                     "win_%": round(100 * float(np.nanmean(nostop > 0)), 1),
                                     "t": round(float(np.nanmean(nostop) / (np.nanstd(nostop, ddof=1) / np.sqrt(np.sum(~np.isnan(nostop))))), 2)}
        r["stopped_trades"] = int(stopped.sum())
        r["stopped_but_right_by_1725_%"] = round(100 * float(np.nanmean(nostop[stopped] > 0)), 1)
        r["median_original_stop_pts"] = float(tr["sl_pips"].median())
        # 2) stop x exit grid, full year
        R, P = grid(days, tr, v)
        r["grid_R"], r["grid_pts"] = R.tolist(), P.tolist()
        res[v] = r
        fig, ax = plt.subplots(1, 2, figsize=(15, 5.5))
        heat(ax[0], R, f"084{v}: R per trade after costs (2023, OVERFIT GRID)", "{:+.2f}")
        heat(ax[1], P, f"084{v}: points per trade after costs (2023, OVERFIT GRID)", "{:+.1f}")
        fig.tight_layout()
        fig.savefig(OUT / f"grid_{v}.png", dpi=105)
        plt.close(fig)

    # 3) filters on idea a (wide stop, hold to 17:25): what "explains" the winners?
    tr = trades["a"]
    b = load_bars()
    pa = sim(b, tr, 150.0, time(17, 25))
    feat = []
    for et in tr["entry_time"]:
        z = et.astimezone(__import__("zoneinfo").ZoneInfo(FRA))
        g = b[z.date()]
        i0 = np.where(g["mod"] == 540)[0]
        i1 = np.where(g["mod"] == 570)[0]
        o = (g["ask_open"][i0[0]] + g["bid_open"][i0[0]]) / 2 if len(i0) else np.nan
        c = (g["ask_open"][i1[0]] + g["bid_open"][i1[0]]) / 2 if len(i1) else np.nan
        feat.append((abs(c - o), z.weekday(), z.month))
    f = np.array(feat, dtype=float)
    terc = np.nanpercentile(f[:, 0], [33.3, 66.7])
    filt = {}
    for name, m in (("first30 small", f[:, 0] <= terc[0]), ("first30 medium", (f[:, 0] > terc[0]) & (f[:, 0] <= terc[1])),
                    ("first30 large", f[:, 0] > terc[1])):
        filt[name] = stats(pa[m], np.full(m.sum(), 150.0))
    for k, wd in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri"]):
        m = f[:, 1] == k
        filt[wd] = stats(pa[m], np.full(m.sum(), 150.0))
    for side in ("long", "short"):
        m = (tr["direction"] == side).to_numpy()
        filt[side] = stats(pa[m], np.full(m.sum(), 150.0))
    filt["_terciles_pts"] = [round(float(x), 1) for x in terc]
    res["a_filters_stop150_exit1725"] = filt

    # 4) the over-fitting lesson: choose the best (stop, exit, filter) on Jan-Jun, check Jul-Dec
    h1 = (tr["entry_time"].dt.month() <= 6).to_numpy()
    filters = {"all": np.ones(tr.height, bool), "first30 small": f[:, 0] <= terc[0], "first30 large": f[:, 0] > terc[1],
               "not first30 large": f[:, 0] <= terc[1], "long only": (tr["direction"] == "long").to_numpy(),
               "short only": (tr["direction"] == "short").to_numpy()}
    for k, wd in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri"]):
        filters[f"skip {wd}"] = f[:, 1] != k
    rows = []
    for s in STOPS:
        for x in EXITS:
            p = sim(b, tr, float(s), x)
            for fn, m in filters.items():
                a1, a2 = p[m & h1], p[m & ~h1]
                a1, a2 = a1[~np.isnan(a1)], a2[~np.isnan(a2)]
                if len(a1) >= 30 and len(a2) >= 20:
                    rows.append((s, x.strftime("%H:%M"), fn, float((a1 / s).mean()), float((a2 / s).mean()), len(a1), len(a2), p, m))
    rows.sort(key=lambda z: -z[3])
    best = rows[0]
    res["overfit_lesson"] = {
        "configs_tried": len(rows),
        "best_on_H1": {"stop": best[0], "exit": best[1], "filter": best[2], "H1_R": round(best[3], 3), "H2_R": round(best[4], 3),
                       "H1_n": best[5], "H2_n": best[6]},
        "top10_on_H1_then_H2": [{"stop": z[0], "exit": z[1], "filter": z[2], "H1_R": round(z[3], 3), "H2_R": round(z[4], 3)} for z in rows[:10]],
        "avg_H2_R_of_top10": round(float(np.mean([z[4] for z in rows[:10]])), 3),
        "avg_H2_R_all_configs": round(float(np.mean([z[4] for z in rows])), 3),
        "corr_H1_vs_H2_across_configs": round(float(np.corrcoef([z[3] for z in rows], [z[4] for z in rows])[0, 1]), 3),
    }
    # chart: best-on-H1 equity through the year
    p, m = best[7], best[8]
    t = tr.with_columns(p=p).filter(pl.Series(m) & pl.col("p").is_not_nan()).sort("entry_time")
    fig, ax = plt.subplots(1, 2, figsize=(15, 5))
    x = t["entry_time"].dt.replace_time_zone(None).to_list()
    ax[0].plot(x, (t["p"] / best[0]).cum_sum().to_list(), lw=1.8)
    ax[0].axvline(__import__("datetime").datetime(2023, 7, 1), color="k", ls="--")
    ax[0].text(__import__("datetime").datetime(2023, 3, 1), 0, "chosen here (H1)", fontsize=9)
    ax[0].text(__import__("datetime").datetime(2023, 8, 1), 0, "then...", fontsize=9)
    ax[0].axhline(0, color="#888", lw=0.7)
    ax[0].set_title(f"best of {len(rows)} configs on Jan-Jun: stop {best[0]}, exit {best[1]}, '{best[2]}' (cumulative R)", fontsize=9)
    ax[1].scatter([z[3] for z in rows], [z[4] for z in rows], s=6, alpha=0.4)
    ax[1].scatter([z[3] for z in rows[:10]], [z[4] for z in rows[:10]], s=25, color="red", label="top 10 on H1")
    ax[1].axhline(0, color="#888", lw=0.7)
    ax[1].axvline(0, color="#888", lw=0.7)
    ax[1].set_xlabel("R per trade, Jan-Jun (where we chose)")
    ax[1].set_ylabel("R per trade, Jul-Dec (unseen half)")
    ax[1].set_title(f"every config: first half vs second half (corr {res['overfit_lesson']['corr_H1_vs_H2_across_configs']})", fontsize=9)
    ax[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "overfit_lesson.png", dpi=105)
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str))
    for v in ("a", "b"):
        print(v, {k: res[v][k] for k in res[v] if not k.startswith("grid")})
    print("filters a:", json.dumps(res["a_filters_stop150_exit1725"], indent=0))
    print("lesson:", json.dumps(res["overfit_lesson"], indent=0))


if __name__ == "__main__":
    main()
