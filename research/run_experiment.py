"""Run pre-registered research experiments end to end.

    python -m research.run_experiment 001 002 003

For each NNN: imports research/strategies/NNN_*.py, calls its `make()`,
backtests on the 2024 EURUSD data through `Engine`, evaluates through
`Engine.evaluate` (all metrics come from lib/evaluate.py — nothing hand-rolled),
and writes into research/runs/NNN_*/:

  results.json   full report + H1/H2 split + random-walk baseline + lookahead audit
  trades.parquet the trade log
  equity.png, monthly.png, mc_drawdown.png

It does not touch summary.md: the interpretation is written by hand from these
outputs, once.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path

import numpy as np
import polars as pl

from lib.data import load_1s_data, resample
from lib.engine import Engine
from lib.evaluate import plot_equity, plot_mc_drawdown, plot_monthly

ROOT = Path(__file__).resolve().parent
DATA = ROOT.parent / "data" / "EURUSD_1s_2024.csv"
SEED = 0
SPLIT = datetime(2024, 7, 1, tzinfo=timezone.utc)   # H1 = Jan-Jun, H2 = Jul-Dec (by entry)


def _find(num: str, folder: str, suffix: str) -> Path:
    hits = sorted((ROOT / folder).glob(f"{num}_*{suffix}"))
    if len(hits) != 1:
        raise SystemExit(f"expected exactly one {folder}/{num}_*{suffix}, found {hits}")
    return hits[0]


def _jsonable(x):
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, pl.DataFrame):
        return None  # frames are saved separately / plotted, not dumped
    if isinstance(x, np.ndarray):
        return x.tolist() if x.size <= 50 else None  # e.g. the 10k MC samples: plotted, not dumped
    if isinstance(x, float) and x != x:
        return None
    if hasattr(x, "isoformat"):
        return x.isoformat()
    if hasattr(x, "item"):
        return x.item()
    return x


def _headline(report: dict) -> dict:
    s, adv = report["summary"], report["adversarial"]
    return {
        "summary": s,
        "verdict": report["verdict"],
        "gross_vs_net": adv["gross_vs_net"],
        "bootstrap_ci": adv["bootstrap_ci"],
        "mc_drawdown": adv["mc_drawdown"],
        "ex_best_month": adv["ex_best_month"],
        "ex_best_trades": adv["ex_best_trades"],
        "sample_size": adv["sample_size"],
    }


def lookahead_audit(strategy, bars: pl.DataFrame, trades: pl.DataFrame) -> dict:
    """Independent re-derivation of every entry from the signal frame.

    Each trade must enter exactly at the close_time of a bar where the matching
    crossover fired inside the window (i.e. at the NEXT bar's open, never the
    crossover bar itself); force-flat runs must have no exit later than the
    session end; ATR runs must use exactly the signal bar's ATR-derived SL/TP.
    """
    sig = strategy.generate_signals(bars).with_row_index("bar")
    keyed = trades.with_row_index("trade").join(
        sig.select("bar", "timestamp", "close_time", "cross_up", "cross_down", "in_window",
                   *(["sl_pips"] if "sl_pips" in sig.columns else [])).rename(
            {"timestamp": "signal_bar_start", "sl_pips": "signal_sl_pips"}, strict=False),
        left_on="entry_time", right_on="close_time", how="left",
    )
    is_long = pl.col("direction") == "long"
    problems = {
        "no_signal_bar_closing_at_entry": keyed.filter(pl.col("bar").is_null()).height,
        "cross_does_not_match_direction": keyed.filter(
            pl.col("bar").is_not_null()
            & ~pl.when(is_long).then(pl.col("cross_up")).otherwise(pl.col("cross_down"))
        ).height,
        "signal_bar_outside_window": keyed.filter(
            pl.col("bar").is_not_null() & ~pl.col("in_window")).height,
    }
    # every in-window crossover that occurs while flat should be traded; count
    # signals vs trades so a silently-dropped/extra entry shows up
    n_signals = sig.filter(pl.col("long_signal") | pl.col("short_signal")).height
    out = {"n_window_signals": n_signals, "n_trades": trades.height, **problems}

    if getattr(strategy, "force_flat", False):
        # no position may survive past the first bar boundary at/after 16:00 London
        london_exit = trades["exit_time"].dt.convert_time_zone("Europe/London")
        london_entry = trades["entry_time"].dt.convert_time_zone("Europe/London")
        late = trades.filter(
            (london_exit.dt.date() != london_entry.dt.date())
            | (london_exit.dt.hour().cast(pl.Int32) * 60 + london_exit.dt.minute().cast(pl.Int32) > 16 * 60)
        )
        out["force_flat_violations"] = late.height
    if "signal_sl_pips" in keyed.columns:
        out["sl_mismatch_vs_signal_bar"] = keyed.filter(
            (pl.col("sl_pips") - pl.col("signal_sl_pips")).abs() > 1e-9).height
    out["ok"] = all(v == 0 for k, v in out.items()
                    if k not in ("n_window_signals", "n_trades"))
    return out


def random_walk_baseline(trades: pl.DataFrame) -> dict:
    """What an edge-free entry would score with these exits.

    Under a driftless random walk a bracket of SL/TP pips is hit TP-first with
    probability SL/(SL+TP), and its expected gross P&L is 0 (so expected net =
    -spread). Time-exited trades break the win-rate formula, so it is reported
    over SL/TP-resolved trades only; gross expectancy is compared to 0 over all.
    """
    bracket = trades.filter(pl.col("exit_reason").is_in(["sl", "tp"]))
    exp_win = (bracket["sl_pips"] / (bracket["sl_pips"] + bracket["tp_pips"])).mean()
    act_win = (bracket["exit_reason"] == "tp").mean()
    gross = trades["pips"] + trades["spread_pips_paid"]
    return {
        "n_bracket_trades": bracket.height,
        "null_tp_rate_pct": None if exp_win is None else round(exp_win * 100, 2),
        "actual_tp_rate_pct": None if act_win is None else round(act_win * 100, 2),
        "gross_expectancy_pips": round(gross.mean(), 3),
        "net_expectancy_pips": round(trades["pips"].mean(), 3),
        "avg_spread_paid_pips": round(trades["spread_pips_paid"].mean(), 3),
        "exit_reasons": dict(trades.group_by("exit_reason").agg(pl.len()).iter_rows()),
    }


def run(num: str, engine: Engine, bars: pl.DataFrame) -> dict:
    path = _find(num, "strategies", ".py")
    strategy = import_module(f"research.strategies.{path.stem}").make()
    run_dir = ROOT / "runs" / path.stem
    run_dir.mkdir(exist_ok=True)

    trades = engine.backtest(strategy)
    trades.write_parquet(run_dir / "trades.parquet")
    report = engine.evaluate(trades, starting_balance=10_000, pip_value=1.0, seed=SEED)

    halves = {}
    for name, part in (("H1_jan_jun", trades.filter(pl.col("entry_time") < SPLIT)),
                       ("H2_jul_dec", trades.filter(pl.col("entry_time") >= SPLIT))):
        r = engine.evaluate(part, starting_balance=10_000, pip_value=1.0, seed=SEED)
        halves[name] = {"summary": r["summary"], "verdict": r["verdict"],
                        "bootstrap_ci": r["adversarial"]["bootstrap_ci"],
                        "gross_vs_net": r["adversarial"]["gross_vs_net"]}

    result = {
        "run": path.stem,
        "strategy": {k: v for k, v in vars(strategy).items()},
        "full_year": _headline(report),
        "halves": halves,
        "random_walk_baseline": random_walk_baseline(trades),
        "lookahead_audit": lookahead_audit(strategy, bars, trades),
        "monthly": report["monthly"].to_dicts(),
    }
    (run_dir / "results.json").write_text(json.dumps(_jsonable(result), indent=2))

    plot_equity(report).savefig(run_dir / "equity.png", dpi=110, bbox_inches="tight")
    plot_monthly(report).savefig(run_dir / "monthly.png", dpi=110, bbox_inches="tight")
    plot_mc_drawdown(report["adversarial"]["mc_drawdown"]).savefig(
        run_dir / "mc_drawdown.png", dpi=110, bbox_inches="tight")
    return result


def main(nums: list[str]) -> None:
    base = load_1s_data(str(DATA), verbose=False)
    bars = resample(base, "5m")
    engine = Engine(bars, base)
    for num in nums:
        r = run(num, engine, bars)
        fy = r["full_year"]
        print(f"\n=== {r['run']} ===")
        print(json.dumps(_jsonable({
            "summary": fy["summary"], "verdict": fy["verdict"],
            "gross_vs_net": fy["gross_vs_net"], "bootstrap_ci": fy["bootstrap_ci"],
            "mc_drawdown": {k: v for k, v in fy["mc_drawdown"].items() if k != "note"},
            "ex_best_month": fy["ex_best_month"], "ex_best_trades": fy["ex_best_trades"],
            "halves": {k: {"n": v["summary"]["n_trades"], "pips": v["summary"]["total_pips"],
                           "win": v["summary"]["win_rate"],
                           "exp_ci": v["bootstrap_ci"]["expectancy_pips"],
                           "edge": v["gross_vs_net"]["edge_assessment"]}
                       for k, v in r["halves"].items()},
            "random_walk_baseline": r["random_walk_baseline"],
            "lookahead_audit": r["lookahead_audit"],
        }), indent=1))


if __name__ == "__main__":
    main(sys.argv[1:] or ["001", "002", "003"])
