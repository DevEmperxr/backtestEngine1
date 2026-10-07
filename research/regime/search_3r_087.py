"""Run 087 — DELIBERATE OVERFIT #2 (user request): maximise the number of 3R winners on GER40 Jan–Jun 2023, one trade
a day, over the setup elements in research/strategies/087_overfit_3r.py; then show Jul–Dec. NOT evidence; 2024 untouched.

    .venv/Scripts/python.exe -m research.regime.search_3r_087

Fast simulator = engine mirror (fill next bar open on ask/bid; stop/target on bid/ask 1m extremes, stop first if both
in one bar; exit next open after a news-blackout bar or the bar closing 17:25; FTMO +0.15 pt top-up).
Ranking: number of 3R target hits in Jan–Jun (tie-break total R).
"""

from __future__ import annotations

import json
from collections import Counter
from importlib import import_module
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402
from numba import njit  # noqa: E402

from lib.data import load_1s_data, resample  # noqa: E402
from research.regime.news import apply_news_blackout  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "runs" / "087_overfit_3r"
S = import_module("research.strategies.087_overfit_3r")
TOPUP = 0.15


@njit(cache=True)
def _sim(sig, dirs, stops, tr, day, cmod, ao, bo, ah, al, bh, bl, black, exit_min):
    n, N = len(sig), len(ao)
    R = np.full(n, np.nan)
    hit = np.zeros(n, np.bool_)
    for k in range(n):
        i = sig[k]
        e = i + 1
        stp = stops[k]
        if e >= N - 1 or day[e] != day[i] or cmod[e] > exit_min or not stp > 0:
            continue
        d = dirs[k]
        entry = ao[e] if d == 1 else bo[e]
        sl = entry - d * stp
        tp = entry + d * stp * tr
        pnl = np.nan
        for j in range(e, N - 1):
            if day[j] != day[e]:
                break
            if d == 1:
                if bl[j] <= sl:
                    pnl = (bo[j] if (j > e and bo[j] < sl) else sl) - entry
                    break
                if bh[j] >= tp:
                    pnl = (bo[j] if (j > e and bo[j] > tp) else tp) - entry
                    hit[k] = True
                    break
            else:
                if ah[j] >= sl:
                    pnl = entry - (ao[j] if (j > e and ao[j] > sl) else sl)
                    break
                if al[j] <= tp:
                    pnl = entry - (ao[j] if (j > e and ao[j] < tp) else tp)
                    hit[k] = True
                    break
            if black[j] or cmod[j] >= exit_min:
                pnl = (bo[j + 1] - entry) if d == 1 else (entry - ao[j + 1])
                break
        if pnl == pnl:
            R[k] = (pnl - TOPUP) / stp
    return R, hit


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    b = resample(load_1s_data(str(ROOT / "data" / "GER40_1s_2023.csv"), verbose=False), "1m")
    f = S.features(b)
    nb = apply_news_blackout(f.select("close_time").with_columns(long_signal=pl.lit(False), short_signal=pl.lit(False)), ["EUR"])
    black = nb["news_blackout"].fill_null(True).to_numpy()
    day = f["day"].rank("dense").cast(pl.Int64).to_numpy()
    month = f["day"].dt.month().to_numpy()
    cmod = f["cmod"].to_numpy().astype(np.int64)
    P = {k: f[c].to_numpy().astype(np.float64) for k, c in (("ao", "ask_open"), ("bo", "bid_open"), ("ah", "ask_high"),
                                                               ("al", "ask_low"), ("bh", "bid_high"), ("bl", "bid_low"))}
    stops = {}
    for st in S.STOPS:
        sl_l, sl_s = S.stop_expr(st)
        x = f.select(sl_l.alias("l"), sl_s.alias("s"))
        stops[st] = (x["l"].fill_null(np.nan).to_numpy(), x["s"].fill_null(np.nan).to_numpy())
    bias = {}
    for r in S.READERS:
        for bn in S.BIASES:
            la, sa = S.bias_ok(r, bn)
            x = f.select(la.alias("l"), sa.alias("s"))
            bias[(r, bn)] = (x["l"].to_numpy(), x["s"].to_numpy())

    rows = []
    for lev in S.LEVELS:
        for side in S.SIDES:
            for win in S.WINDOWS:
                if lev == "first_hour" and win == "09-10":
                    continue
                for conf in S.CONFIRMS:
                    lg, sh = S.raw_signals(f, lev, side, win, conf)
                    x = f.select(lg.alias("l"), sh.alias("s"))
                    l_, s_ = x["l"].to_numpy() & ~black, x["s"].to_numpy() & ~black
                    sig = np.flatnonzero(l_ | s_)
                    if len(sig) < 30:
                        continue
                    dirs = np.where(l_[sig], 1, -1).astype(np.int64)
                    dsig, msig = day[sig], month[sig]
                    for st in S.STOPS:
                        stp = np.where(dirs == 1, stops[st][0][sig], stops[st][1][sig])
                        R, hit = _sim(sig, dirs, stp, S.TARGET_R, day, cmod, P["ao"], P["bo"], P["ah"], P["al"],
                                      P["bh"], P["bl"], black, S.EXIT_MIN)
                        for (rd, bn), (la, sa) in bias.items():
                            m = np.where(dirs == 1, la[sig], sa[sig])
                            idx = np.flatnonzero(m)
                            if len(idx) < 20:
                                continue
                            keep = idx[np.r_[True, dsig[idx][1:] != dsig[idx][:-1]]]
                            r, h, mo = R[keep], hit[keep], msig[keep]
                            ok = ~np.isnan(r)
                            r, h, mo = r[ok], h[ok], mo[ok]
                            a1, a2 = mo <= 6, mo > 6
                            if a1.sum() < 20 or a2.sum() < 10:
                                continue
                            rows.append((rd, bn, lev, side, win, conf, st, int(a1.sum()), int(h[a1].sum()), float(r[a1].sum()),
                                         int(a2.sum()), int(h[a2].sum()), float(r[a2].sum())))
            print(f"{lev:<11} {side:<9} done ({len(rows):,} setups)", flush=True)

    cols = ["context", "bias", "level", "side", "window", "confirm", "stop", "H1_n", "H1_3R_wins", "H1_R",
            "H2_n", "H2_3R_wins", "H2_R"]
    t = (pl.DataFrame(rows, schema=cols, orient="row")
         .with_columns(H1_hit_pct=100 * pl.col("H1_3R_wins") / pl.col("H1_n"), H2_hit_pct=100 * pl.col("H2_3R_wins") / pl.col("H2_n"),
                       H1_R_per_trade=pl.col("H1_R") / pl.col("H1_n"), H2_R_per_trade=pl.col("H2_R") / pl.col("H2_n"))
         .sort(["H1_3R_wins", "H1_R"], descending=True))
    t.write_parquet(OUT / "all_setups.parquet")
    top = t.head(50)
    w = top.row(0, named=True)
    cfg = {"reader": w["context"], "bias": w["bias"], "level": w["level"], "side": w["side"], "window": w["window"],
           "confirm": w["confirm"], "stop": w["stop"]}
    res = {
        "setups_tried": t.height,
        "winner": w,
        "top20": top.head(20).to_dicts(),
        "top50_H1_hit_pct": round(float(top["H1_hit_pct"].mean()), 1), "top50_H2_hit_pct": round(float(top["H2_hit_pct"].mean()), 1),
        "top50_H1_R_per_trade": round(float(top["H1_R_per_trade"].mean()), 3), "top50_H2_R_per_trade": round(float(top["H2_R_per_trade"].mean()), 3),
        "all_H1_hit_pct": round(float(t["H1_hit_pct"].mean()), 1), "all_H2_hit_pct": round(float(t["H2_hit_pct"].mean()), 1),
        "all_H1_R_per_trade": round(float(t["H1_R_per_trade"].mean()), 3), "all_H2_R_per_trade": round(float(t["H2_R_per_trade"].mean()), 3),
        "corr_hit_pct_H1_H2": round(float(np.corrcoef(t["H1_hit_pct"], t["H2_hit_pct"])[0, 1]), 3),
        "corr_R_per_trade_H1_H2": round(float(np.corrcoef(t["H1_R_per_trade"], t["H2_R_per_trade"])[0, 1]), 3),
        "top50_element_counts": {k: dict(Counter(top[k].to_list()).most_common()) for k in
                                 ("context", "bias", "level", "side", "window", "confirm", "stop")},
    }
    (OUT / "winner.json").write_text(json.dumps({"config": cfg, "fast_sim": w}, indent=1, default=str))
    (OUT / "search_results.json").write_text(json.dumps(res, indent=1, default=str))

    fig, ax = plt.subplots(1, 2, figsize=(15, 5.5))
    ax[0].scatter(t["H1_hit_pct"], t["H2_hit_pct"], s=3, alpha=0.2)
    ax[0].scatter(top["H1_hit_pct"], top["H2_hit_pct"], s=18, color="red", label="top 50 by 3R wins Jan-Jun")
    ax[0].scatter([w["H1_hit_pct"]], [w["H2_hit_pct"]], s=140, marker="*", color="gold", edgecolor="k", label="winner")
    ax[0].axhline(25, color="#888", ls="--", lw=0.8)
    ax[0].axvline(25, color="#888", ls="--", lw=0.8)
    ax[0].set_xlabel("% of trades reaching 3R, Jan-Jun (searched)")
    ax[0].set_ylabel("% reaching 3R, Jul-Dec")
    ax[0].set_title(f"{t.height:,} setups: 3R hit rate (dashed 25% = break-even before costs)", fontsize=10)
    ax[0].legend(fontsize=8)
    ax[1].scatter(t["H1_R_per_trade"], t["H2_R_per_trade"], s=3, alpha=0.2)
    ax[1].scatter(top["H1_R_per_trade"], top["H2_R_per_trade"], s=18, color="red", label="top 50")
    ax[1].scatter([w["H1_R_per_trade"]], [w["H2_R_per_trade"]], s=140, marker="*", color="gold", edgecolor="k", label="winner")
    ax[1].axhline(0, color="#888", lw=0.7)
    ax[1].axvline(0, color="#888", lw=0.7)
    ax[1].set_xlabel("R per trade after FTMO costs, Jan-Jun")
    ax[1].set_ylabel("R per trade, Jul-Dec")
    ax[1].legend(fontsize=8)
    ax[1].set_title(f"R per trade; corr H1 vs H2 = {res['corr_R_per_trade_H1_H2']}", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "search_overview.png", dpi=105)
    print(json.dumps({k: v for k, v in res.items() if k != "top20"}, indent=1, default=str))
    with pl.Config(tbl_rows=20, tbl_cols=20, tbl_width_chars=260):
        print(top.head(20).select(cols[:7] + ["H1_n", "H1_3R_wins", "H1_hit_pct", "H1_R", "H2_n", "H2_3R_wins", "H2_hit_pct", "H2_R"]))


if __name__ == "__main__":
    main()
