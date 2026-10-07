"""Run 077 — Asia-session results: per variant and year after FTMO costs, before-cost result, exit mix, FTMO 1-step
scorecard, and where the gap to the 076 session drift comes from (18:00–19:00 hour, costs, stops)."""

from __future__ import annotations

import json
from datetime import date, time, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import polars as pl  # noqa: E402

from lib.data import load_1s_data, pip_size, resample  # noqa: E402
from lib.prop_firms import ftmo_1step_scorecard  # noqa: E402
from research.regime.trend_dip_073 import stats  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "research" / "runs" / "077_asia_session"
SRC = ROOT / "research" / "runs" / "077_asia_session"
START = date(2023, 3, 14)
VARIANTS = {"gold_trend": "XAUUSD", "gold_always": "XAUUSD", "aud_trend": "AUDUSD", "aud_always": "AUDUSD"}
NY = "America/New_York"


def load(v: str, y: int) -> pl.DataFrame:
    t = pl.read_parquet(SRC / f"{v}_{VARIANTS[v]}_{y}" / "trades.parquet").with_columns(R=pl.col("pips") / pl.col("sl_pips"))
    return t.filter(pl.col("entry_time").dt.date() >= START) if y == 2023 else t


def hour_split(pair: str) -> dict:
    """Mid move (pips) 18:00->19:00 vs 19:00->03:00 NY, summed over FX days, per year."""
    out = {}
    for y in (2023, 2024):
        b = resample(load_1s_data(str(ROOT / "data" / f"{pair}_1s_{y}.csv"), verbose=False), "1m")
        t = pl.col("close_time").dt.convert_time_zone(NY)
        m = b.select(fxday=(pl.col("timestamp").dt.convert_time_zone(NY) + timedelta(hours=7)).dt.date(), clock=t.dt.time(),
                     mid=(pl.col("bid_close") + pl.col("ask_close")) / 2)
        def at(tt):
            return m.filter(pl.col("clock") == tt).select("fxday", pl.col("mid").alias(str(tt)))
        j = at(time(18, 1)).join(at(time(19, 0)), on="fxday").join(at(time(3, 0)), on="fxday")
        p = pip_size(pair)
        out[str(y)] = {"18:01->19:00": round(float(((j["19:00:00"] - j["18:01:00"]) / p).sum()), 1),
                       "19:00->03:00": round(float(((j["03:00:00"] - j["19:00:00"]) / p).sum()), 1), "days": j.height}
    return out


def main() -> None:
    res = {}
    fig, ax = plt.subplots(figsize=(12, 5))
    for v, pair in VARIANTS.items():
        both = pl.concat([load(v, 2023), load(v, 2024)])
        r = {str(y): stats(load(v, y)) for y in (2023, 2024)}
        r["both"] = stats(both)
        r["gross_pips"] = round(float((both["pips"] + both["spread_pips_paid"] + both["commission_pips"]).sum()), 1)
        r["costs_pips_total"] = round(float((both["spread_pips_paid"] + both["commission_pips"]).sum()), 1)
        r["exits"] = dict(both.group_by("exit_reason").len().iter_rows())
        r["long"] = stats(both.filter(pl.col("direction") == "long"))
        r["short"] = stats(both.filter(pl.col("direction") == "short"))
        sc = ftmo_1step_scorecard(both, START, date(2024, 12, 31), n_sims=1500, seed=4)
        r["scorecard"] = {"strategy": sc["strategy"], "zero_edge_twin": sc["zero_edge_twin"], "beats_twin": sc["beats_twin"]}
        if v.endswith("trend"):
            r["candidate"] = bool(r["2023"]["R_per_trade"] > 0 and r["2024"]["R_per_trade"] > 0
                                  and r["both"]["R_per_trade"] >= 0.05 and sc["beats_twin"])
        res[v] = r
        s, z = sc["strategy"], sc["zero_edge_twin"]
        print(f"\n== {v} ({pair})\n   2023 {r['2023']}\n   2024 {r['2024']}\n   both {r['both']}\n   gross {r['gross_pips']} pips, "
              f"costs {r['costs_pips_total']} pips, exits {r['exits']}\n   long {r['long']}\n   short {r['short']}\n"
              f"   FTMO 1-step: pass {s['pass_%']}% EV ${s['EV_net']} | twin pass {z['pass_%']}% EV ${z['EV_net']}"
              + (f" | CANDIDATE {r['candidate']}" if 'candidate' in r else ""))
        t = both.sort("exit_time")
        ax.plot(t["exit_time"].dt.replace_time_zone(None).to_list(), t["R"].cum_sum().to_list(), label=f"{v} ({pair})", lw=1.6)
    for pair in ("XAUUSD", "AUDUSD"):
        res[f"hour_split_{pair}"] = hour_split(pair)
        print(f"\n{pair} raw move by part of the Asian session (pips, summed): {res[f'hour_split_{pair}']}")
    ax.axhline(0, color="#555", lw=0.7)
    ax.set_ylabel("cumulative R (after FTMO costs)")
    ax.set_title("077 Asian-session trades (19:00 -> 03:00 New York), Mar 2023 – Dec 2024", fontsize=10)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(RUN / "asia_equity.png", dpi=110)
    (RUN / "results.json").write_text(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()
