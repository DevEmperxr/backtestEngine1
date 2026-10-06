"""Run 054 — what was different in the market when the London fade (046) lost vs won? Descriptive,
EURUSD 2021-2024 by quarter. No rule changes.

Per quarter: 046 trades / net / gross pips; EURUSD quarterly move, average daily range and daily
trendiness (|close - open| / range, UTC days, mid); in the entry window 03:00-04:59 NY: average 5m
ATR (pips), average spread, share of minutes with a "sideways" 1h context, lag-1 autocorrelation of
1m mid returns (negative = moves tend to reverse), and the share of 2xATR stretches that touch the
5m SMA20 within 60 minutes before going a further 1.5 ATR against (a strategy-free snap-back rate).
"""

from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402

from lib.data import load_1s_data, resample  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "research" / "runs"
OUT = RUNS / "054_market_by_quarter"
NY = "America/New_York"


def trades(y: int) -> pl.DataFrame:
    d = RUNS / "046_london_fade_standalone"
    return pl.read_parquet((d if y == 2024 else d / f"main_{y}") / "trades.parquet")


def year_metrics(y: int, scratch: Path) -> pl.DataFrame:
    bp = scratch / f"bars1m_{y}.parquet"
    if bp.exists():
        b = pl.read_parquet(bp)
    else:
        b = resample(load_1s_data(str(ROOT / "data" / f"EURUSD_1s_{y}.csv"), verbose=False), "1m")
    st = import_module("research.strategies.046_london_fade_standalone").make()
    s = st.generate_signals(b).with_columns(
        mid=(pl.col("bid_close") + pl.col("ask_close")) / 2,
        mh=(pl.col("bid_high") + pl.col("ask_high")) / 2, ml=(pl.col("bid_low") + pl.col("ask_low")) / 2,
        spread=(pl.col("ask_close") - pl.col("bid_close")) / 1e-4,
        q=pl.col("timestamp").dt.quarter(),
        hr=pl.col("close_time").dt.convert_time_zone(NY).dt.hour(),
    ).with_columns(ret=pl.col("mid").diff())
    # strategy-free snap-back: window bars whose 1m high/low reaches the 2xATR band
    mh, ml = s["mh"].to_numpy(), s["ml"].to_numpy()
    ma, at = s["ma5"].to_numpy(), s["atr5"].to_numpy()
    inwin = s["hr"].is_in([3, 4]).to_numpy()
    with np.errstate(invalid="ignore"):
        up = inwin & (mh >= ma + 2 * at)
        dn = inwin & (ml <= ma - 2 * at)
    snap = np.full(len(s), np.nan)
    for i in np.flatnonzero(up | dn):
        if i + 61 >= len(s) or not np.isfinite(at[i]):
            continue
        short = up[i]
        tgt = ma[i]
        adv = (mh[i] + 1.5 * at[i]) if short else (ml[i] - 1.5 * at[i])
        for j in range(i + 1, i + 61):
            if (ml[j] <= tgt) if short else (mh[j] >= tgt):
                snap[i] = 1.0
                break
            if (mh[j] >= adv) if short else (ml[j] <= adv):
                snap[i] = 0.0
                break
    s = s.with_columns(snap=pl.Series(snap))
    w = s.filter(pl.col("hr").is_in([3, 4]))
    win = w.group_by("q").agg(
        range5m_pips=(pl.col("atr5").mean() / 1e-4),
        spread_pips=pl.col("spread").mean(),
        sideways_share=(pl.col("ctx") == "sideways").mean(),
        autocorr_1m=pl.corr("ret", pl.col("ret").shift(1)),
        snapback_rate=pl.col("snap").drop_nans().mean(),
        n_stretches=pl.col("snap").drop_nans().len(),
    )
    dd = s.group_by(pl.col("timestamp").dt.date().alias("d")).agg(
        q=pl.col("q").first(), hi=pl.col("mh").max(), lo=pl.col("ml").min(),
        o=pl.col("mid").first(), c=pl.col("mid").last()).sort("d")
    dly = dd.group_by("q").agg(
        daily_range_pips=((pl.col("hi") - pl.col("lo")) / 1e-4).mean(),
        daily_trendiness=((pl.col("c") - pl.col("o")).abs() / (pl.col("hi") - pl.col("lo"))).mean(),
        q_move_pips=((pl.col("c").last() - pl.col("o").first()) / 1e-4),
        level=pl.col("c").mean())
    t = trades(y).with_columns(q=pl.col("entry_time").dt.quarter())
    tq = t.group_by("q").agg(trades=pl.len(), net=pl.col("pips").sum(),
                             gross_per_trade=(pl.col("pips") + pl.col("spread_pips_paid")).mean(),
                             net_per_trade=pl.col("pips").mean(),
                             win_rate=(pl.col("pips") > 0).mean(),
                             stop=pl.col("sl_pips").median(), target=pl.col("tp_pips").median())
    return (tq.join(win, on="q").join(dly, on="q")
            .with_columns(quarter=pl.lit(f"{y}-Q") + pl.col("q").cast(pl.Utf8)).sort("q"))


def main(scratch: Path) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    m = pl.concat([year_metrics(y, scratch) for y in (2021, 2022, 2023, 2024)])
    cols = ["quarter", "trades", "net", "net_per_trade", "gross_per_trade", "win_rate", "q_move_pips",
            "level", "daily_range_pips", "daily_trendiness", "range5m_pips", "spread_pips", "sideways_share",
            "autocorr_1m", "snapback_rate", "n_stretches", "stop", "target"]
    m = m.select(cols).with_columns(pl.col(pl.Float64).round(3))
    cfg = dict(tbl_rows=30, tbl_cols=30, tbl_width_chars=300, tbl_formatting="ASCII_MARKDOWN",
               tbl_hide_column_data_types=True, tbl_hide_dataframe_shape=True)
    with pl.Config(**cfg):
        print(m)
    corr = {c: round(float(np.corrcoef(m["net_per_trade"], m[c])[0, 1]), 2)
            for c in cols[4:] if c != "win_rate"}
    print("correlation with net per trade (16 quarters):", corr)
    yr = (m.with_columns(year=pl.col("quarter").str.slice(0, 4)).group_by("year").agg(
        pl.col("net").sum(), pl.col("trades").sum(), pl.col("q_move_pips").sum(), pl.col("daily_range_pips").mean(),
        pl.col("daily_trendiness").mean(), pl.col("range5m_pips").mean(), pl.col("spread_pips").mean(),
        pl.col("sideways_share").mean(), pl.col("autocorr_1m").mean(), pl.col("snapback_rate").mean())
        .sort("year").with_columns(pl.col(pl.Float64).round(3)))
    with pl.Config(**cfg):
        print(yr)
    m.write_parquet(OUT / "by_quarter.parquet")
    (OUT / "results.json").write_text(json.dumps({"by_quarter": m.to_dicts(), "by_year": yr.to_dicts(),
                                                  "corr_with_net_per_trade": corr}, indent=2, default=str))
    show = [("net", "London fade net pips"), ("q_move_pips", "EURUSD quarterly move (pips)"),
            ("range5m_pips", "5m candle size (ATR) at the London open, pips"),
            ("daily_trendiness", "how much each day trends (0 = chop, 1 = one-way)"),
            ("autocorr_1m", "1m return autocorrelation at the London open (negative = moves reverse)"),
            ("snapback_rate", "share of 2xATR stretches that snap back to the average first")]
    fig, ax = plt.subplots(len(show), 1, figsize=(12, 13), sharex=True)
    x = np.arange(m.height)
    for a, (c, title) in zip(ax, show):
        v = m[c].to_list()
        if c == "net":
            colors = ["#2E9E5B" if val > 0 else "#D84A2E" for val in v]
        else:
            colors = "#4E79A7"
        a.bar(x, v, color=colors)
        a.set_title(title, fontsize=10)
        a.grid(axis="y", alpha=0.25)
        a.axhline(0, color="#555", lw=0.6)
        if c in ("range5m_pips", "daily_trendiness", "snapback_rate"):
            a.set_ylim(min(v) * 0.9, max(v) * 1.05)
    ax[-1].set_xticks(x)
    ax[-1].set_xticklabels(m["quarter"].to_list(), rotation=45)
    fig.suptitle("London fade vs market conditions, EURUSD by quarter 2021-2024", fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT / "market_by_quarter.png", dpi=110)
    print(OUT / "market_by_quarter.png")


if __name__ == "__main__":
    import sys
    main(Path(sys.argv[1]))
