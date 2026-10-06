"""Web viewer for a research strategy's trades, built on fx_viz (Strategy.visualize).

    .venv/Scripts/python.exe -m research.viz.trade_viewer 046 --year 2023 [--port 8765]

Opens a live chart at http://127.0.0.1:<port>: 1m candles, the strategy's lines/markers, and each
trade as a TradingView long/short box (red = stop, green = target). Topbar: "< prev" / "next >" jump
to the previous/next trade (label shows trade number, New York time, direction, result), plus the
usual timeframe switcher. Drag to pan (more candles load near the edges), scroll to zoom.
Keeps running until stopped (Ctrl+C).
"""

from __future__ import annotations

import argparse
import time
from importlib import import_module
from pathlib import Path

import polars as pl

from lib.data import load_1s_data, resample
from lib.engine import Engine

ROOT = Path(__file__).resolve().parents[2]
NY = "America/New_York"


def _strategy(num: str):
    hits = sorted((ROOT / "research" / "strategies").glob(f"{num}_*.py"))
    if not hits:
        raise SystemExit(f"no strategy file research/strategies/{num}_*.py")
    return import_module(f"research.strategies.{hits[0].stem}").make()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("num")
    ap.add_argument("--year", type=int, default=2023)
    ap.add_argument("--pair", default="EURUSD")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--warmup", type=int, default=2000, help="history bars for indicators (1h context needs ~1500 1m bars)")
    a = ap.parse_args()
    if a.year >= 2026:
        raise SystemExit("2026 is the holdout year: not loaded without the user's explicit permission")

    st = _strategy(a.num)
    base = load_1s_data(str(ROOT / "data" / f"{a.pair}_1s_{a.year}.csv"), verbose=False)
    eng = Engine(resample(base, st.timeframe), base)

    from fx_viz import FxChart
    chart = FxChart(width=1400, height=760, port=a.port)
    st.visualize(eng, chart=chart, show_trades=True, warmup_bars=a.warmup, initial_bars=400)
    live = chart._fx_live
    trades = live["trades"].sort("entry_time")
    n = trades.height
    print(f"{n} trades, {trades['pips'].sum():+.1f} pips", flush=True)

    sc = chart._sc
    pos = {"i": -1}

    def show(i: int) -> None:
        i = max(0, min(n - 1, i))
        pos["i"] = i
        r = trades.row(i, named=True)
        bars = live["bars"]
        k = int((bars["timestamp"] < r["entry_time"]).sum())
        held = max(1, int((bars["timestamp"] < r["exit_time"]).sum()) - k)
        # load a wide window but zoom to the trade only: if the whole loaded window were on screen,
        # both edges would sit inside edge_margin and lazy-loading would keep fetching (the chart
        # "moves on its own")
        s, e = max(0, k - 1500), min(bars.height, k + held + 1500)
        live["render"](bars, s, e)
        a = bars["timestamp"][max(0, k - 90)].timestamp()
        b = bars["timestamp"][min(bars.height - 1, k + held + 60)].timestamp()
        sc.run_script(f"{sc.id}.chart.timeScale().setVisibleRange({{from: {int(a)}, to: {int(b)}}})")
        t = r["entry_time"].astimezone(__import__("zoneinfo").ZoneInfo(NY)).strftime("%a %Y-%m-%d %H:%M")
        sc.topbar["info"].set(
            f"trade {i + 1}/{n} | {t} NY | {r['direction']} | {r['exit_reason']} {r['pips']:+.1f} pips | "
            f"stop {r['sl_pips']:.1f} target {r['tp_pips']:.1f}")

    sc.topbar.button("prev", "< prev", func=lambda _c: show(pos["i"] - 1))
    sc.topbar.button("next", "next >", func=lambda _c: show(pos["i"] + 1))
    sc.topbar.button("first", "first", func=lambda _c: show(0))
    sc.topbar.button("worst", "worst", func=lambda _c: show(int(trades["pips"].arg_min())))
    sc.topbar.button("best", "best", func=lambda _c: show(int(trades["pips"].arg_max())))
    sc.topbar.textbox("info", f"{n} trades, {trades['pips'].sum():+.1f} pips. Click next >")
    show(0)
    print(f"open http://127.0.0.1:{a.port}", flush=True)
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
