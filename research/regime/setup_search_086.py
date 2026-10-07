"""Run 086 — DELIBERATE OVERFIT search (user-approved one-off): the best-fitted GER40 setup on Jan–Jun 2023 over the
user's setup template, then the same configs on Jul–Dec 2023. NOT evidence; 2024 untouched.

    .venv/Scripts/python.exe -m research.regime.setup_search_086

Grid (research/strategies/086_overfit_setup.py): Context 7 x Bias 7 x POI 6 x window 4 x Confirmation 4 x
stop 3 x target 4 = ~54k configs. Fast simulator mirrors the engine: signal on bar i, fill at bar i+1 open (ask long /
bid short), stop/target on bid/ask 1m extremes (stop first if both in one bar), exit at the next open after a news
blackout bar or the bar closing 17:25, FTMO +0.15 pt spread top-up, one trade per day (first signal after filters).
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
OUT = ROOT / "research" / "runs" / "086_overfit_setup"
S = import_module("research.strategies.086_overfit_setup")
TOPUP = 0.15
MIN_H1_TRADES = 30


@njit(cache=True)
def _sim(sig, dirs, smult, tmult, atr, day, smod, cmod, ao, bo, ah, al, bh, bl, black, exit_min):
    n, N = len(sig), len(ao)
    R = np.full(n, np.nan)
    for k in range(n):
        i = sig[k]
        e = i + 1
        if e >= N - 1 or day[e] != day[i] or cmod[e] > exit_min:
            continue
        stp = smult * atr[i]
        if not stp > 0:
            continue
        tgt = stp * tmult if tmult > 0 else 1e9
        d = dirs[k]
        entry = ao[e] if d == 1 else bo[e]
        sl = entry - d * stp
        tp = entry + d * tgt
        pnl = np.nan
        for j in range(e, N - 1):
            if day[j] != day[e]:
                break
            if d == 1:
                if bl[j] <= sl:
                    px = bo[j] if (j > e and bo[j] < sl) else sl
                    pnl = px - entry
                    break
                if bh[j] >= tp:
                    px = bo[j] if (j > e and bo[j] > tp) else tp
                    pnl = px - entry
                    break
            else:
                if ah[j] >= sl:
                    px = ao[j] if (j > e and ao[j] > sl) else sl
                    pnl = entry - px
                    break
                if al[j] <= tp:
                    px = ao[j] if (j > e and ao[j] < tp) else tp
                    pnl = entry - px
                    break
            if black[j] or cmod[j] >= exit_min:
                pnl = (bo[j + 1] - entry) if d == 1 else (entry - ao[j + 1])
                break
        if pnl == pnl:
            R[k] = (pnl - TOPUP) / stp
    return R


def load() -> pl.DataFrame:
    b = resample(load_1s_data(str(ROOT / "data" / "GER40_1s_2023.csv"), verbose=False), "1m")
    f = S.features(b)
    nb = apply_news_blackout(f.select("close_time").with_columns(long_signal=pl.lit(False), short_signal=pl.lit(False)), ["EUR"])
    return f.with_columns(black=nb["news_blackout"])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    f = load()
    day_codes = f["day"].rank("dense").cast(pl.Int64).to_numpy()
    month = f["day"].dt.month().to_numpy()
    A = {k: f[c].to_numpy().astype(np.float64) for k, c in (("ao", "ask_open"), ("bo", "bid_open"), ("ah", "ask_high"),
                                                               ("al", "ask_low"), ("bh", "bid_high"), ("bl", "bid_low"))}
    atr = f["atr"].fill_null(np.nan).to_numpy().astype(np.float64)
    smod, cmod = f["smod"].to_numpy().astype(np.int64), f["cmod"].to_numpy().astype(np.int64)
    black = f["black"].fill_null(True).to_numpy()
    ctx = {c: f.select(S.context_mask(c).alias("m"))["m"].to_numpy() if c != "none" else np.ones(f.height, bool) for c in S.CONTEXTS}
    bias = {}
    for bn in S.BIASES:
        la, sa = S.bias_masks(bn)
        x = f.select(la.alias("l"), sa.alias("s")) if bn != "both" else None
        bias[bn] = (np.ones(f.height, bool), np.ones(f.height, bool)) if x is None else (x["l"].to_numpy(), x["s"].to_numpy())

    rows = []
    for poi in S.POIS:
        for win in S.WINDOWS:
            if poi == "first_hour" and win == "09-10":
                continue
            for conf in S.CONFIRMS:
                lg, sh = S.raw_signals(f, poi, win, conf)
                x = f.select(lg.alias("l"), sh.alias("s"))
                l_, s_ = x["l"].to_numpy() & ~black, x["s"].to_numpy() & ~black
                both = l_ & s_
                l_, s_ = l_ & ~both, s_ & ~both
                sig = np.flatnonzero(l_ | s_)
                if len(sig) == 0:
                    continue
                dirs = np.where(l_[sig], 1, -1).astype(np.int64)
                dsig, msig = day_codes[sig], month[sig]
                for sm in S.STOPS:
                    for tm in S.TARGETS:
                        R = _sim(sig, dirs, sm, tm if tm is not None else 0.0, atr, day_codes, smod, cmod, A["ao"], A["bo"],
                                 A["ah"], A["al"], A["bh"], A["bl"], black, S.EXIT_MIN)
                        for c in S.CONTEXTS:
                            cm = ctx[c][sig]
                            for bn in S.BIASES:
                                la, sa = bias[bn]
                                m = cm & np.where(dirs == 1, la[sig], sa[sig])
                                idx = np.flatnonzero(m)
                                if len(idx) == 0:
                                    continue
                                keep = idx[np.r_[True, dsig[idx][1:] != dsig[idx][:-1]]]
                                r = R[keep]
                                ok = ~np.isnan(r)
                                r, mo = r[ok], msig[keep][ok]
                                r1, r2 = r[mo <= 6], r[mo > 6]
                                if len(r1) < MIN_H1_TRADES or len(r2) < 10:
                                    continue
                                rows.append((c, bn, poi, win, conf, sm, tm, len(r1), float(r1.sum()), float(r1.mean()),
                                             len(r2), float(r2.sum()), float(r2.mean())))
                print(f"{poi:<11} {win:<9} done ({len(rows)} configs so far)", flush=True)

    cols = ["context", "bias", "poi", "window", "confirm", "stop_atr", "target_R", "H1_n", "H1_R", "H1_R_per_trade",
            "H2_n", "H2_R", "H2_R_per_trade"]
    t = pl.DataFrame(rows, schema=cols, orient="row").sort("H1_R", descending=True)
    t.write_parquet(OUT / "all_configs.parquet")
    top = t.head(50)
    win = top.row(0, named=True)
    cfg = {k: win[k] for k in ("context", "bias", "poi", "window", "confirm")}
    cfg["stop"], cfg["target"] = win["stop_atr"], win["target_R"]
    res = {
        "configs_tried": t.height,
        "winner_on_H1": win,
        "top20": top.head(20).to_dicts(),
        "top50_H2_R_per_trade_avg": round(float(top["H2_R_per_trade"].mean()), 3),
        "all_H2_R_per_trade_avg": round(float(t["H2_R_per_trade"].mean()), 3),
        "share_H1_positive_%": round(100 * float((t["H1_R"] > 0).mean()), 1),
        "share_H2_positive_%": round(100 * float((t["H2_R"] > 0).mean()), 1),
        "corr_H1_H2_per_trade": round(float(np.corrcoef(t["H1_R_per_trade"], t["H2_R_per_trade"])[0, 1]), 3),
        "top50_element_counts": {k: dict(Counter(top[k].cast(pl.Utf8).to_list()).most_common()) for k in
                                 ("context", "bias", "poi", "window", "confirm", "stop_atr", "target_R")},
    }
    (OUT / "winner.json").write_text(json.dumps({"config": cfg, "fast_sim": win}, indent=1, default=str))
    (OUT / "search_results.json").write_text(json.dumps(res, indent=1, default=str))

    fig, ax = plt.subplots(1, 2, figsize=(15, 5.5))
    ax[0].hist(t["H1_R_per_trade"], bins=80, alpha=0.6, label="Jan-Jun (searched)")
    ax[0].hist(t["H2_R_per_trade"], bins=80, alpha=0.6, label="Jul-Dec (same configs)")
    ax[0].axvline(0, color="k", lw=0.8)
    ax[0].set_xlabel("R per trade after FTMO costs")
    ax[0].set_title(f"{t.height:,} setups: R per trade, first half vs second half", fontsize=10)
    ax[0].legend()
    ax[1].scatter(t["H1_R"], t["H2_R"], s=3, alpha=0.25)
    ax[1].scatter(top["H1_R"], top["H2_R"], s=18, color="red", label="top 50 on Jan-Jun")
    ax[1].scatter([win["H1_R"]], [win["H2_R"]], s=120, marker="*", color="gold", edgecolor="k", label="winner")
    ax[1].axhline(0, color="#888", lw=0.7)
    ax[1].axvline(0, color="#888", lw=0.7)
    ax[1].set_xlabel("total R, Jan-Jun (where we chose)")
    ax[1].set_ylabel("total R, Jul-Dec")
    ax[1].legend(fontsize=8)
    ax[1].set_title(f"total R per setup; corr of R/trade H1 vs H2 = {res['corr_H1_H2_per_trade']}", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "search_overview.png", dpi=105)
    print(json.dumps({k: v for k, v in res.items() if k != "top20"}, indent=1, default=str))
    with pl.Config(tbl_rows=20, tbl_cols=20, tbl_width_chars=250):
        print(top.head(20))


if __name__ == "__main__":
    main()
