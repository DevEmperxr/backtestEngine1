"""Run 088 — walk-forward test of "over-fit month by month" on GER40 2023 (pre-registered in
research/runs/088_walkforward_overfit/summary.md).

    .venv/Scripts/python.exe -m research.regime.walkforward_088

Every setup of the 087 menu is simulated once over 2023 (EUR + USD news ±2 min); per setup and month we keep trades,
3R wins and total R. Each month the setup with the most 3R wins over the previous L months is traded unchanged in that
month; only the stitched next-month results count.
"""

from __future__ import annotations

import json
from datetime import date
from importlib import import_module
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402

from lib.data import load_1s_data, resample  # noqa: E402
from lib.prop_firms import ftmo_1step_scorecard  # noqa: E402
from research.regime.news import apply_news_blackout  # noqa: E402
from research.regime.search_3r_087 import _sim  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "runs" / "088_walkforward_overfit"
S = import_module("research.strategies.087_overfit_3r")
LOOKBACKS = (1, 3)
MIN_PER_MONTH = 10


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    b = resample(load_1s_data(str(ROOT / "data" / "GER40_1s_2023.csv"), verbose=False), "1m")
    f = S.features(b)
    nb = apply_news_blackout(f.select("close_time").with_columns(long_signal=pl.lit(False), short_signal=pl.lit(False)),
                             ["EUR", "USD"])
    black = nb["news_blackout"].fill_null(True).to_numpy()
    day = f["day"].rank("dense").cast(pl.Int64).to_numpy()
    month = f["day"].dt.month().to_numpy()
    cmod = f["cmod"].to_numpy().astype(np.int64)
    ctime = f["close_time"].to_list()
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

    keys, N, W, RS = [], [], [], []
    trades_of = {}                              # key -> (signal bar idx, R, stop pts) for later stitching
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
                    dsig = day[sig]
                    for st in S.STOPS:
                        stp = np.where(dirs == 1, stops[st][0][sig], stops[st][1][sig])
                        R, hit = _sim(sig, dirs, stp, S.TARGET_R, day, cmod, P["ao"], P["bo"], P["ah"], P["al"],
                                      P["bh"], P["bl"], black, S.EXIT_MIN)
                        for (rd, bn), (la, sa) in bias.items():
                            m = np.where(dirs == 1, la[sig], sa[sig])
                            idx = np.flatnonzero(m)
                            if len(idx) < 30:
                                continue
                            keep = idx[np.r_[True, dsig[idx][1:] != dsig[idx][:-1]]]
                            ok = ~np.isnan(R[keep])
                            keep = keep[ok]
                            mo = month[sig[keep]] - 1
                            key = (rd, bn, lev, side, win, conf, st)
                            keys.append(key)
                            N.append(np.bincount(mo, minlength=12))
                            W.append(np.bincount(mo, weights=hit[keep].astype(float), minlength=12))
                            RS.append(np.bincount(mo, weights=R[keep], minlength=12))
                            trades_of[len(keys) - 1] = (sig[keep], R[keep], stp[keep])
            print(f"{lev:<11} {side:<9} ({len(keys):,} setups)", flush=True)

    N, W, RS = np.array(N), np.array(W), np.array(RS)
    res = {"setups": len(keys)}
    fig, ax = plt.subplots(2, 2, figsize=(15, 9))
    for col, L in enumerate(LOOKBACKS):
        months, picks, stitched = [], [], []
        for m in range(L, 12):
            lb = slice(m - L, m)
            n_lb, w_lb, r_lb = N[:, lb].sum(1), W[:, lb].sum(1), RS[:, lb].sum(1)
            elig = (N[:, lb] >= MIN_PER_MONTH).all(1)
            score = np.where(elig, w_lb * 1e6 + r_lb, -np.inf)
            k = int(np.argmax(score))
            nxt = N[:, m]
            rpt = np.where(nxt > 0, RS[:, m] / np.maximum(nxt, 1), np.nan)
            pool = rpt[elig & (nxt > 0)]
            pct = float(100 * (pool < rpt[k]).mean()) if nxt[k] > 0 else None
            picks.append({"month": m + 1, "setup": dict(zip(["context", "bias", "level", "side", "window", "confirm", "stop"], keys[k])),
                          "lookback_trades": int(n_lb[k]), "lookback_3R_wins": int(w_lb[k]),
                          "lookback_R_per_trade": round(float(r_lb[k] / n_lb[k]), 3),
                          "next_trades": int(nxt[k]), "next_3R_wins": int(W[k, m]),
                          "next_R_per_trade": None if nxt[k] == 0 else round(float(rpt[k]), 3),
                          "next_percentile": None if pct is None else round(pct, 1),
                          "all_setups_next_R_per_trade": round(float(np.nanmean(pool)), 3)})
            si, r, sp = trades_of[k]
            sel = month[si] == m + 1
            for i, rr, ss in zip(si[sel], r[sel], sp[sel]):
                stitched.append((ctime[i], float(rr * ss), float(ss), float(rr)))
            months.append(m + 1)
        t = pl.DataFrame(stitched, schema=["exit_time", "pips", "sl_pips", "R"], orient="row")
        n = t.height
        hits = sum(p["next_3R_wins"] for p in picks)
        sc = ftmo_1step_scorecard(t, date(2023, L + 1, 1), date(2023, 12, 31), n_sims=1500, seed=4)
        pcts = [p["next_percentile"] for p in picks if p["next_percentile"] is not None]
        lb_rpt = float(np.sum([p["lookback_R_per_trade"] * p["lookback_trades"] for p in picks]) / np.sum([p["lookback_trades"] for p in picks]))
        out = {"months_traded": len(picks), "trades": n, "3R_wins": hits, "hit_%": round(100 * hits / max(n, 1), 1),
               "R_per_trade": round(float(t["R"].mean()), 3), "R_total": round(float(t["R"].sum()), 1),
               "picks_lookback_R_per_trade": round(lb_rpt, 3),
               "random_pick_R_per_trade_avg": round(float(np.mean([p["all_setups_next_R_per_trade"] for p in picks])), 3),
               "avg_next_percentile": round(float(np.mean(pcts)), 1),
               "ftmo": {"pass_%": sc["strategy"]["pass_%"], "EV": sc["strategy"]["EV_net"],
                        "twin_pass_%": sc["zero_edge_twin"]["pass_%"], "twin_EV": sc["zero_edge_twin"]["EV_net"],
                        "beats_twin": sc["beats_twin"]},
               "picks": picks}
        out["method_shows_something"] = bool(out["R_per_trade"] > 0 and out["hit_%"] > 25 and out["avg_next_percentile"] > 60 and sc["beats_twin"])
        res[f"L{L}"] = out
        a = ax[0, col]
        xs = np.arange(len(picks))
        a.bar(xs - 0.2, [p["lookback_R_per_trade"] for p in picks], 0.4, label="pick's R/trade in the months it was chosen on", color="#9BB7E8")
        a.bar(xs + 0.2, [p["next_R_per_trade"] or 0 for p in picks], 0.4, label="same pick, next month (traded)", color="#D84A2E")
        a.axhline(0, color="#555", lw=0.7)
        a.set_xticks(xs, [f"{m:02d}" for m in months])
        a.set_xlabel("month traded (2023)")
        a.set_title(f"lookback {L} month(s): chosen-on vs next month (R per trade after costs)", fontsize=9)
        a.legend(fontsize=7)
        a = ax[1, col]
        ts = t.sort("exit_time")
        a.plot(ts["exit_time"].dt.replace_time_zone(None).to_list(), ts["R"].cum_sum().to_list(), lw=1.8)
        a.axhline(0, color="#555", lw=0.7)
        a.set_title(f"lookback {L}: stitched next-month trades, cumulative R ({n} trades, {out['R_per_trade']:+.3f} R/trade, "
                    f"3R hit {out['hit_%']}%)", fontsize=9)
        print(f"\nL={L}: " + json.dumps({k: v for k, v in out.items() if k != "picks"}, default=str))
        for p in picks:
            print(f"  {p['month']:>2}: chosen {p['lookback_3R_wins']} wins / {p['lookback_R_per_trade']:+.2f}R -> next "
                  f"{p['next_trades']} trades, {p['next_3R_wins']} wins, {p['next_R_per_trade']}R (pct {p['next_percentile']}, "
                  f"all setups {p['all_setups_next_R_per_trade']:+.3f})  {tuple(p['setup'].values())}")
    fig.suptitle(f"088 walk-forward of month-by-month over-fitting, GER40 2023 ({len(keys):,} setups each month)", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "walkforward.png", dpi=105)
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str))
    print(OUT / "walkforward.png")


if __name__ == "__main__":
    main()
