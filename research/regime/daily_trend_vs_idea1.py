"""Does Idea 1 (023A) lose when the daily trend changes? Descriptive analysis, EURUSD 2023+2024.

Daily bars: UTC daily mid closes from the 1s data. Daily trend at a trade = sign of
(close − SMA50) on the last daily bar CLOSED before the trade's entry (no lookahead). Late-2022
prices are used only to warm up the SMA50; no trade outside 2023+2024 is evaluated.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402
from importlib import import_module  # noqa: E402

from lib.data import load_1s_data, resample  # noqa: E402
from lib.evaluate import bootstrap_ci, evaluate  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "runs" / "031_idea1_vs_daily_trend"


def daily_bars() -> pl.DataFrame:
    parts = []
    for y in (2022, 2023, 2024):
        d = resample(load_1s_data(str(ROOT / "data" / f"EURUSD_1s_{y}.csv"), verbose=False), "1d")
        parts.append(d.select("timestamp", "close_time",
                              c=(pl.col("bid_close") + pl.col("ask_close")) / 2))
    d = pl.concat(parts).sort("timestamp").unique("timestamp", keep="last").sort("timestamp")
    return d.with_columns(sma50=pl.col("c").rolling_mean(50, min_samples=50)).with_columns(
        dtrend=pl.when(pl.col("c") > pl.col("sma50")).then(1).when(pl.col("c") < pl.col("sma50")).then(-1))


def idea1_trades(scratch: Path) -> pl.DataFrame:
    st = import_module("research.strategies.023_sweep_fade_rework").make_a()
    parts = []
    for y in (2023, 2024):
        bp = scratch / f"bars1m_{y}.parquet"
        b = pl.read_parquet(bp) if bp.exists() else resample(load_1s_data(str(ROOT / "data" / f"EURUSD_1s_{y}.csv"), verbose=False), "1m")
        ctx = st.generate_signals(b).select(pl.col("close_time").alias("entry_time"), "ctx_class")
        t = pl.read_parquet(ROOT / "research" / "runs" / "023_sweep_fade_rework" / f"a_{y}" / "trades.parquet")
        parts.append(t.join(ctx, on="entry_time"))
    return pl.concat(parts).sort("entry_time")


def main(scratch: Path) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    d = daily_bars()
    t = idea1_trades(scratch)
    # daily trend of the last daily bar closed before entry (as-of backward on close_time)
    t = t.join_asof(d.select(pl.col("close_time").alias("d_ct"), "dtrend"),
                    left_on="entry_time", right_on="d_ct", strategy="backward")
    tdir = pl.when(pl.col("direction") == "long").then(1).otherwise(-1)
    t = t.with_columns(daily_align=pl.when(pl.col("dtrend").is_null()).then(pl.lit("n/a"))
                       .when(tdir == pl.col("dtrend")).then(pl.lit("with daily trend"))
                       .otherwise(pl.lit("against daily trend")))
    tw = t.filter(pl.col("ctx_class") == "trend_with")

    print("== Idea 1, 1h-trend trades, split by DAILY trend (close vs SMA50 at entry)")
    for grp in ("with daily trend", "against daily trend"):
        for y in (2023, 2024, None):
            x = tw.filter(pl.col("daily_align") == grp)
            if y:
                x = x.filter(pl.col("entry_time").dt.year() == y)
            if x.height == 0:
                continue
            s = evaluate(x)["summary"]
            ci = bootstrap_ci(x, seed=0)["expectancy_pips"]
            print(f"   {grp:<20} {y or 'both':<5} n={s['n_trades']:3d} net={s['total_pips']:+7.1f} "
                  f"exp={s['expectancy_pips']:+.2f} 95%=[{ci['ci_low']:+.2f},{ci['ci_high']:+.2f}] win={s['win_rate']:.1f}%")

    # monthly: strategy P&L vs EURUSD monthly move
    m_pnl = tw.with_columns(month=pl.col("exit_time").dt.strftime("%Y-%m")).group_by("month").agg(pips=pl.col("pips").sum())
    dm = d.filter(pl.col("timestamp").dt.year().is_in([2023, 2024])).with_columns(
        month=pl.col("timestamp").dt.strftime("%Y-%m")).group_by("month").agg(
        first=pl.col("c").first(), last=pl.col("c").last(), hi=pl.col("c").max(), lo=pl.col("c").min()).with_columns(
        move=(pl.col("last") - pl.col("first")) / 1e-4, rng=(pl.col("hi") - pl.col("lo")) / 1e-4)
    mm = dm.join(m_pnl, on="month", how="left").with_columns(pl.col("pips").fill_null(0.0)).sort("month")
    c_move = float(np.corrcoef(mm["move"], mm["pips"])[0, 1])
    c_abs = float(np.corrcoef(mm["move"].abs(), mm["pips"])[0, 1])
    c_rng = float(np.corrcoef(mm["rng"], mm["pips"])[0, 1])
    print(f"== monthly correlation (24 months): P&L vs EURUSD monthly move {c_move:+.2f}; "
          f"vs size of move {c_abs:+.2f}; vs monthly range {c_rng:+.2f}")

    # figure: daily chart / equity / monthly bars on one time axis
    dd = d.filter(pl.col("timestamp").dt.year().is_in([2023, 2024]))
    x_d = dd["timestamp"].dt.replace_time_zone(None).to_list()
    fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(12, 10), sharex=True,
                                     gridspec_kw={"height_ratios": [1.3, 1, 0.9]})
    a1.plot(x_d, dd["c"].to_list(), color="#222", lw=1.2, label="EURUSD daily close")
    a1.plot(x_d, dd["sma50"].to_list(), color="#E8A33D", lw=1.4, label="50-day MA")
    tr = dd["dtrend"].to_list()
    for i in range(len(x_d) - 1):
        if tr[i] is not None:
            a1.axvspan(x_d[i], x_d[i + 1], color="#2E9E5B" if tr[i] > 0 else "#D84A2E", alpha=0.08, lw=0)
    a1.set_title("EURUSD daily (green = above 50-day MA, red = below)", fontsize=10)
    a1.legend(fontsize=8, loc="upper left")
    a1.grid(alpha=0.25)
    eq = tw["pips"].cum_sum().to_list()
    a2.plot(tw["exit_time"].dt.replace_time_zone(None).to_list(), eq, color="#2E6BD8", lw=1.6)
    a2.axhline(0, color="#888", lw=0.8)
    a2.set_title(f"Idea 1 (023A) equity, 1h-trend trades only · final {eq[-1]:+.1f} pips · {len(eq)} trades", fontsize=10)
    a2.set_ylabel("cumulative pips")
    a2.grid(alpha=0.25)
    from datetime import datetime
    mx = [datetime.strptime(mo + "-15", "%Y-%m-%d") for mo in mm["month"].to_list()]
    a3.bar(mx, mm["pips"].to_list(), width=20, color=["#2E9E5B" if v > 0 else "#D84A2E" for v in mm["pips"].to_list()])
    a3.axhline(0, color="#888", lw=0.8)
    a3.set_title(f"Idea 1 monthly P&L · correlation with EURUSD monthly move {c_move:+.2f}", fontsize=10)
    a3.set_ylabel("pips")
    a3.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT / "idea1_vs_daily_trend.png", dpi=110)
    t.write_parquet(OUT / "trades_with_daily_trend.parquet")
    print(OUT / "idea1_vs_daily_trend.png")


if __name__ == "__main__":
    import sys
    main(Path(sys.argv[1]))
