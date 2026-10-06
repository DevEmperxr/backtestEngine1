"""Run 036 — lookahead checks for the London-open sideways slice (034 strategy).

1. Future-scramble: corrupt every 1m bar after a cut-off (prices replaced by a random walk at a
   different level), regenerate signals, and require every signal column before the cut-off to
   be identical to the clean run.
2. One-minute-late entry: shift every signal (and its sl/tp/context) one bar later, so each
   trade enters at bar t+2's open instead of t+1's, and re-run the engine. A real edge should
   survive a 1-minute delay; one that depended on peeking at bar t+1 would collapse.
"""

from __future__ import annotations

from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path

import numpy as np
import polars as pl

from lib.data import load_1s_data, resample
from lib.engine import Engine
from lib.evaluate import bootstrap_ci, evaluate

ROOT = Path(__file__).resolve().parents[2]
COLS = ["long_signal", "short_signal", "sl_pips", "tp_pips", "ctx_class", "swing_hi", "swing_lo",
        "ma5", "atr5", "in_window", "exit_signal"]


def scramble_test(b1: pl.DataFrame, cutoff: datetime) -> dict:
    st = import_module("research.strategies.034_idea1_lon_ny").make()
    clean = st.generate_signals(b1)
    rng = np.random.default_rng(1)
    after = (b1["timestamp"] >= cutoff).to_numpy()
    n = int(after.sum())
    walk = 1.30 + np.cumsum(rng.normal(0, 2e-4, n))           # a different price level and path
    bad = b1.clone()
    for side, off in (("bid", 0.0), ("ask", 1e-4)):
        for f, adj in (("open", 0.0), ("high", 3e-4), ("low", -3e-4), ("close", 0.0)):
            col = f"{side}_{f}"
            vals = bad[col].to_numpy().copy()
            vals[after] = walk + off + adj
            bad = bad.with_columns(pl.Series(col, vals))
    dirty = st.generate_signals(bad)
    keep = clean["timestamp"] < cutoff
    a, b = clean.filter(keep).select(COLS), dirty.filter(keep).select(COLS)
    diffs = {c: int((a[c].cast(pl.Utf8).fill_null("∅") != b[c].cast(pl.Utf8).fill_null("∅")).sum()) for c in COLS}
    n_sig = int((a["long_signal"] | a["short_signal"]).sum())
    return {"rows_before_cutoff": a.height, "signals_before_cutoff": n_sig, "differences": diffs,
            "clean_after_cutoff_signals": int(clean.filter(~keep).select(pl.col("long_signal") | pl.col("short_signal")).to_series().sum()),
            "dirty_after_cutoff_signals": int(dirty.filter(~keep).select(pl.col("long_signal") | pl.col("short_signal")).to_series().sum())}


class _Late:
    """Wrap a strategy: every signal row is moved one bar later."""

    def __init__(self, inner):
        self.inner = inner
        for k, v in vars(inner).items():
            setattr(self, k, v)
        self.exit_on_opposite_signal = inner.exit_on_opposite_signal
        self.reverse_on_opposite_signal = inner.reverse_on_opposite_signal

    def generate_signals(self, df):
        s = self.inner.generate_signals(df)
        mv = ["long_signal", "short_signal", "sl_pips", "tp_pips", "ctx_class"]
        s = s.with_columns(*[pl.col(c).shift(1) for c in mv])
        return s.with_columns(pl.col("long_signal").fill_null(False), pl.col("short_signal").fill_null(False),
                              # a moved signal may now sit on a bar that is flagged exit_signal
                              exit_signal=pl.col("exit_signal") & ~(pl.col("long_signal").fill_null(False) | pl.col("short_signal").fill_null(False)))


def slice_stats(trades: pl.DataFrame, sig: pl.DataFrame) -> dict:
    t = trades.join(sig.select(pl.col("close_time").alias("entry_time"), "ctx_class"), on="entry_time", how="left")
    t = t.with_columns(hour=pl.col("entry_time").dt.convert_time_zone("America/New_York").dt.hour())
    x = t.filter(pl.col("hour").is_in([3, 4]) & (pl.col("ctx_class") == "sideways"))
    s = evaluate(x)["summary"]
    ci = bootstrap_ci(x, seed=0)["expectancy_pips"]
    return {"n": s["n_trades"], "net": round(s["total_pips"], 1), "per_trade": round(s["expectancy_pips"], 2),
            "ci95": [round(ci["ci_low"], 2), round(ci["ci_high"], 2)]}


def main() -> None:
    out = {}
    for year in (2023, 2024):
        base = load_1s_data(str(ROOT / "data" / f"EURUSD_1s_{year}.csv"), verbose=False)
        b1 = resample(base, "1m")
        out[f"scramble_{year}"] = scramble_test(b1, datetime(year, 7, 1, tzinfo=timezone.utc))
        st = import_module("research.strategies.034_idea1_lon_ny").make()
        eng = Engine(b1, base)
        on_time = eng.backtest(st)
        late_st = _Late(st)
        late = eng.backtest(late_st)
        out[f"on_time_{year}"] = slice_stats(on_time, st.generate_signals(b1))
        # for the late run, the context sits on the shifted (entry - 1) row
        out[f"one_minute_late_{year}"] = slice_stats(late, late_st.generate_signals(b1))
        print(year, out[f"scramble_{year}"], "\n   on time:", out[f"on_time_{year}"],
              "\n   1 min late:", out[f"one_minute_late_{year}"], flush=True)
    import json
    d = ROOT / "research" / "runs" / "036_lookahead_check_london_sideways"
    d.mkdir(parents=True, exist_ok=True)
    (d / "results.json").write_text(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
