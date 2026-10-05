"""Run pre-registered research experiments end to end.

    python -m research.run_experiment 001 002 003
    python -m research.run_experiment 016:a 016:b --year 2025

`NNN:v` calls the strategy file's `make_v()` instead of `make()`. `--year Y`
backtests data/EURUSD_1s_Y.csv (default 2024) and, for any year other than 2024
or any variant, writes into research/runs/NNN_*/<v|main>_<Y>/ so runs never
overwrite each other.

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

import argparse
import json
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path

import numpy as np
import polars as pl

from lib.data import PIP, load_1s_data, resample
from lib.engine import Engine
from lib.evaluate import plot_equity, plot_mc_drawdown, plot_monthly

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT.parent / "data"
SEED = 0
YEAR = 2024                                     # set by main(); H1/H2 split at Jul 1 of it


def _find(num: str, folder: str, suffix: str) -> Path:
    hits = sorted((ROOT / folder).glob(f"{num}_*{suffix}"))
    if len(hits) != 1:
        raise SystemExit(f"expected exactly one {folder}/{num}_*{suffix}, found {hits}")
    return hits[0]


def _load(spec: str):
    num, _, variant = spec.partition(":")
    mod = import_module(f"research.strategies.{_find(num, 'strategies', '.py').stem}")
    return getattr(mod, f"make_{variant}" if variant else "make")()


def _run_dir(spec: str) -> Path:
    num, _, variant = spec.partition(":")
    d = ROOT / "runs" / _find(num, "strategies", ".py").stem
    if variant or YEAR != 2024:
        d = d / f"{variant or 'main'}_{YEAR}"
    d.mkdir(parents=True, exist_ok=True)
    return d


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
    if isinstance(x, (str, int, float, bool)) or x is None:
        return x
    if hasattr(x, "__dict__"):           # e.g. a nested Strategy (018 wraps 005)
        return {"type": type(x).__name__, **_jsonable(vars(x))}
    return repr(x)


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


def lookahead_audit(strategy, bars: pl.DataFrame, trades: pl.DataFrame, base_1s: pl.DataFrame) -> dict:
    """Independent re-derivation of every entry from the signal frame.

    Each trade must enter exactly at the close_time of a bar where the matching
    crossover fired inside the window (i.e. at the NEXT bar's open, never the
    crossover bar itself); force-flat runs must have no exit later than the
    session end; ATR runs must use exactly the signal bar's ATR-derived SL/TP.
    """
    sig = strategy.generate_signals(bars).with_row_index("bar")
    keyed = trades.with_row_index("trade").join(
        sig.select("bar", "timestamp", "close_time", "long_signal", "short_signal", "in_window",
                   *(["sl_pips"] if "sl_pips" in sig.columns else [])).rename(
            {"timestamp": "signal_bar_start", "sl_pips": "signal_sl_pips"}, strict=False),
        left_on="entry_time", right_on="close_time", how="left",
    )
    is_long = pl.col("direction") == "long"
    problems = {
        "no_signal_bar_closing_at_entry": keyed.filter(pl.col("bar").is_null()).height,
        "signal_does_not_match_direction": keyed.filter(
            pl.col("bar").is_not_null()
            & ~pl.when(is_long).then(pl.col("long_signal")).otherwise(pl.col("short_signal"))
        ).height,
        "signal_bar_outside_window": keyed.filter(
            pl.col("bar").is_not_null() & ~pl.col("in_window")).height,
    }
    # every in-window crossover that occurs while flat should be traded; count
    # signals vs trades so a silently-dropped/extra entry shows up
    n_signals = sig.filter(pl.col("long_signal") | pl.col("short_signal")).height
    out = {"n_window_signals": n_signals, "n_trades": trades.height, **problems}

    if getattr(strategy, "force_flat", False):
        # no position may survive past the session end (default 16:00 London)
        end_tz = getattr(strategy, "window_end_tz", "Europe/London")
        end_t = getattr(strategy, "window_end", None)
        end_min = 16 * 60 if end_t is None else end_t.hour * 60 + end_t.minute
        local_exit = trades["exit_time"].dt.convert_time_zone(end_tz)
        local_entry = trades["entry_time"].dt.convert_time_zone(end_tz)
        late = trades.filter(
            (local_exit.dt.date() != local_entry.dt.date())
            | (local_exit.dt.hour().cast(pl.Int32) * 60 + local_exit.dt.minute().cast(pl.Int32) > end_min)
        )
        out["force_flat_violations"] = late.height
    for tf in getattr(strategy, "trend_timeframes", ()):
        # Independent path: bars straight from the 1s data via lib.data.resample
        # (not the strategy's own 1m-derived bars), last bar closed <= entry.
        htf = resample(base_1s, tf).with_columns(
            mid=(pl.col("bid_close") + pl.col("ask_close")) / 2
        ).with_columns(
            trend=pl.col("mid").rolling_mean(strategy.fast_n) - pl.col("mid").rolling_mean(strategy.slow_n)
        ).select(pl.col("close_time").alias("htf_close_time"), "trend")
        chk = trades.sort("entry_time").join_asof(
            htf, left_on="entry_time", right_on="htf_close_time", strategy="backward")
        wrong = chk.filter(
            pl.col("trend").is_null()
            | ((pl.col("direction") == "long") & (pl.col("trend") <= 0))
            | ((pl.col("direction") == "short") & (pl.col("trend") >= 0))
        )
        out[f"trend_{tf}_mismatch"] = wrong.height
    if hasattr(strategy, "range_start"):
        out.update(_orb_audit(strategy, trades, base_1s))
    kind = getattr(strategy, "audit_kind", None)
    if kind == "fix_fade":
        out.update(_fix_audit(strategy, trades, base_1s))
    elif kind == "round_number":
        out.update(_round_audit(strategy, trades, base_1s))
    elif kind == "band_rsi":
        out.update(_band_audit(strategy, trades, base_1s))
    elif kind == "bb15x5":
        out.update(_bb15x5_audit(strategy, trades, base_1s))
    elif kind == "orb_fix_fade":
        out.update(_orbfade_audit(strategy, bars, trades, base_1s))
    if "signal_sl_pips" in keyed.columns:
        out["sl_mismatch_vs_signal_bar"] = keyed.filter(
            (pl.col("sl_pips") - pl.col("signal_sl_pips")).abs() > 1e-9).height
    out["ok"] = all(v == 0 for k, v in out.items()
                    if k not in ("n_window_signals", "n_trades") and not k.startswith("info_"))
    return out


def _orb_audit(strategy, trades: pl.DataFrame, base_1s: pl.DataFrame) -> dict:
    """Independent ORB re-check: 1m bars rebuilt from the 1s data, the opening
    range recomputed here with plain wall-clock filtering (not the strategy's
    code), then for every trade: the signal bar (closing at entry_time) closed
    beyond the range on the trade's side, it closed after the range ended, no
    earlier bar that day closed beyond the range, and <= 1 trade per day."""
    ny = "America/New_York"
    b = resample(base_1s, "1m").with_columns(
        mid_c=(pl.col("bid_close") + pl.col("ask_close")) / 2,
        mid_h=(pl.col("bid_high") + pl.col("ask_high")) / 2,
        mid_l=(pl.col("bid_low") + pl.col("ask_low")) / 2,
        t0=pl.col("timestamp").dt.convert_time_zone(ny),
        t1=pl.col("close_time").dt.convert_time_zone(ny),
    ).with_columns(d=pl.col("t0").dt.date())
    rs, re_ = strategy.range_start, strategy.range_end
    rng = b.filter((pl.col("t0").dt.time() >= rs) & (pl.col("t1").dt.time() <= re_)
                   & (pl.col("t1").dt.date() == pl.col("d"))).group_by("d").agg(
        hi=pl.col("mid_h").max(), lo=pl.col("mid_l").min())
    after = b.filter(pl.col("t1").dt.time() > re_).join(rng, on="d")
    first_brk = after.filter((pl.col("mid_c") > pl.col("hi")) | (pl.col("mid_c") < pl.col("lo")))         .group_by("d").agg(first_close=pl.col("close_time").min())
    t = trades.with_columns(d=pl.col("entry_time").dt.convert_time_zone(ny).dt.date())         .join(rng, on="d", how="left").join(first_brk, on="d", how="left")         .join(b.select("close_time", "mid_c", "t1"), left_on="entry_time", right_on="close_time", how="left")
    long = pl.col("direction") == "long"
    return {
        "orb_range_missing": t.filter(pl.col("hi").is_null()).height,
        "orb_signal_not_beyond_range": t.filter(
            pl.when(long).then(pl.col("mid_c") <= pl.col("hi")).otherwise(pl.col("mid_c") >= pl.col("lo"))
        ).height,
        "orb_signal_not_after_range": t.filter(pl.col("t1").dt.time() <= re_).height,
        "orb_not_first_breakout": t.filter(pl.col("entry_time") != pl.col("first_close")).height,
        "orb_days_with_multiple_trades": t.group_by("d").len().filter(pl.col("len") > 1).height,
    }


def _mid_bars(base_1s: pl.DataFrame, tf: str) -> pl.DataFrame:
    """Bars rebuilt from the 1s data, mid OHLC in pips (audit-only helper)."""
    return resample(base_1s, tf).with_columns(
        **{f: (pl.col(f"bid_{f}") + pl.col(f"ask_{f}")) / 2 / PIP for f in ("open", "high", "low", "close")}
    ).select("timestamp", "close_time", "open", "high", "low", "close")


def _fix_audit(strategy, trades: pl.DataFrame, base_1s: pl.DataFrame) -> dict:
    """Entry exactly at the fix (London clock), direction = -sign(fix close - close
    `lookback_min` earlier), recomputed by wall-clock lookup on rebuilt 1m bars."""
    b = _mid_bars(base_1s, "1m")
    close_at = dict(zip(b["close_time"].to_list(), b["close"].to_list()))
    from datetime import timedelta
    london = trades["entry_time"].dt.convert_time_zone("Europe/London").dt.time().to_list()
    wrong_time = sum(t != strategy.fix_time for t in london)
    wrong_dir = missing = 0
    for et, d in zip(trades["entry_time"].to_list(), trades["direction"].to_list()):
        c1, c0 = close_at.get(et), close_at.get(et - timedelta(minutes=strategy.lookback_min))
        if c1 is None or c0 is None:
            missing += 1
            continue
        want = "long" if c1 - c0 < 0 else "short"
        wrong_dir += (d != want)
    out = {"fix_entry_not_at_fix": wrong_time, "fix_direction_mismatch": wrong_dir,
           "fix_bars_missing": missing}
    n = getattr(strategy, "filter_days", None)
    if n:
        # every weekday fix in the data, |r| recomputed here; threshold = median
        # of the n strictly-earlier fix days (plain Python, independent of polars)
        lt = b["close_time"].dt.convert_time_zone("Europe/London")
        fixes = b.filter((lt.dt.time() == strategy.fix_time) & (lt.dt.weekday() <= 5))["close_time"].to_list()
        absr = {}
        for t in fixes:
            c0 = close_at.get(t - timedelta(minutes=strategy.lookback_min))
            if c0 is not None:
                absr[t] = abs(close_at[t] - c0)
        days = sorted(absr)
        pos = {t: i for i, t in enumerate(days)}
        below = 0
        for et in trades["entry_time"].to_list():
            i = pos.get(et)
            past = [absr[d] for d in days[max(0, i - n):i]] if i is not None else []
            if len(past) < n:
                below += 1
                continue
            past.sort()
            m = len(past)
            med = past[m // 2] if m % 2 else (past[m // 2 - 1] + past[m // 2]) / 2
            below += not (absr[et] > med)
        out["fix_filter_threshold_violations"] = below
    return out


def _round_audit(strategy, trades: pl.DataFrame, base_1s: pl.DataFrame) -> dict:
    """The signal bar (closing at entry) must have a step-pip level touched from the
    open side and closed back, on the traded side. Plain Python scan of levels."""
    import math
    b = _mid_bars(base_1s, "1m")
    rows = {r["close_time"]: r for r in b.iter_rows(named=True)}
    step, bad = strategy.step_pips, 0
    for et, d in zip(trades["entry_time"].to_list(), trades["direction"].to_list()):
        r = rows.get(et)
        o, h, l, c = (round(r[k], 4) for k in ("open", "high", "low", "close"))
        lo_m, hi_m = math.floor(l / step) * step, math.ceil(h / step) * step
        levels = range(int(lo_m), int(hi_m) + step, step)
        if d == "short":
            ok = any(o < m <= h and c < m for m in levels)
        else:
            ok = any(l <= m < o and c > m for m in levels)
        bad += not ok
    return {"round_signal_bar_invalid": bad}


def _band_audit(strategy, trades: pl.DataFrame, base_1s: pl.DataFrame) -> dict:
    """Bollinger + Wilder RSI recomputed with explicit numpy loops on rebuilt bars;
    the signal bar must satisfy both conditions on the traded side (1e-9 tol)."""
    b = _mid_bars(base_1s, strategy.timeframe)
    c = b["close"].to_numpy()
    n, k, rn = strategy.bb_n, strategy.bb_k, strategy.rsi_n
    mid = np.full(len(c), np.nan)
    sd = np.full(len(c), np.nan)
    for i in range(n - 1, len(c)):
        w = c[i - n + 1:i + 1]
        mid[i], sd[i] = w.mean(), w.std(ddof=1)
    r = np.full(len(c), np.nan)
    g = lo = None
    for i in range(1, len(c)):
        ch = c[i] - c[i - 1]
        gi, li = max(ch, 0.0), max(-ch, 0.0)
        g = gi if g is None else g + (gi - g) / rn
        lo = li if lo is None else lo + (li - lo) / rn
        if i >= rn:
            r[i] = 100.0 if lo == 0 else 100 - 100 / (1 + g / lo)
    idx = {t: i for i, t in enumerate(b["close_time"].to_list())}
    bad, tol = 0, 1e-9
    for et, d in zip(trades["entry_time"].to_list(), trades["direction"].to_list()):
        i = idx[et]
        if d == "long":
            ok = c[i] < mid[i] - k * sd[i] + tol and r[i] < strategy.rsi_lo + 1e-6
        else:
            ok = c[i] > mid[i] + k * sd[i] - tol and r[i] > strategy.rsi_hi - 1e-6
        bad += not ok
    return {"band_signal_bar_invalid": bad}


def _bb15x5_audit(strategy, trades: pl.DataFrame, base_1s: pl.DataFrame) -> dict:
    """15m bands and 5m SMAs recomputed with numpy on bars rebuilt from 1s. Each
    trade needs (a) a closed 15m bar outside the band on the faded side with
    close_time in [entry - setup_life, entry], and (b) a 5m SMA fast/slow cross in
    the trade direction on the signal bar (the 5m bar closing at entry)."""
    from datetime import timedelta
    b15 = _mid_bars(base_1s, strategy.bb_tf)
    c15 = b15["close"].to_numpy()
    n, k = strategy.bb_n, strategy.bb_k
    lo_out, hi_out = np.zeros(len(c15), bool), np.zeros(len(c15), bool)
    for i in range(n - 1, len(c15)):
        w = c15[i - n + 1:i + 1]
        m, s = w.mean(), w.std(ddof=1)
        lo_out[i], hi_out[i] = c15[i] < m - k * s, c15[i] > m + k * s
    ct15 = b15["close_time"].to_list()
    b5 = _mid_bars(base_1s, strategy.timeframe)
    c5 = b5["close"].to_numpy()
    o5, h5, l5 = (b5[k].to_numpy() for k in ("open", "high", "low"))

    def sma_np(x, p):
        out = np.full(len(x), np.nan)
        cs = np.cumsum(np.insert(x, 0, 0.0))
        out[p - 1:] = (cs[p:] - cs[:-p]) / p
        return out
    f, sl = sma_np(c5, strategy.fast_n), sma_np(c5, strategy.slow_n)
    idx5 = {t: i for i, t in enumerate(b5["close_time"].to_list())}
    life = timedelta(minutes=strategy.setup_life_min)
    no_setup = no_cross = 0
    for et, d in zip(trades["entry_time"].to_list(), trades["direction"].to_list()):
        flags = lo_out if d == "long" else hi_out
        no_setup += not any(flags[j] and et - life <= ct15[j] <= et for j in range(len(ct15))
                            if et - life - timedelta(minutes=15) <= ct15[j] <= et)
        i = idx5[et]
        if getattr(strategy, "confirm", "sma_cross") == "engulf_outside":
            # green and close above the prior bar's high (bearish mirrored)
            if d == "long":
                ok = c5[i] > o5[i] and c5[i] > h5[i - 1]
            else:
                ok = c5[i] < o5[i] and c5[i] < l5[i - 1]
        else:
            prev, now = f[i - 1] - sl[i - 1], f[i] - sl[i]
            ok = (prev <= 0 < now) if d == "long" else (prev >= 0 > now)
        no_cross += not ok
    return {"bb15x5_no_setup_in_life": no_setup, "bb15x5_no_confirm_on_signal_bar": no_cross}


def _orbfade_audit(strategy, bars: pl.DataFrame, trades: pl.DataFrame, base_1s: pl.DataFrame) -> dict:
    """Run the underlying 005 breakout through the real Engine (separate code path
    from 018's own touch check). Every fade must sit on a day where the breakout
    exited `exit_signal` at the fix, opposite direction, entry = that exit time,
    fade TP/SL levels = breakout SL/TP levels (tol 1.5 pips: distances are measured
    from the signal-bar mid, the entry fills at bid/ask). Also counts breakout
    days still open at the fix that produced no fade."""
    orb_trades = Engine(bars, base_1s).backtest(strategy.orb)
    held = orb_trades.filter(pl.col("exit_reason") == "exit_signal")
    lt = held["exit_time"].dt.convert_time_zone("Europe/London").dt.time()
    held = held.filter(lt == strategy.fix_time)
    by_time = {r["exit_time"]: r for r in held.iter_rows(named=True)}
    tol = 1.5 * PIP
    no_match = wrong_dir = bad_levels = 0
    for r in trades.iter_rows(named=True):
        b = by_time.get(r["entry_time"])
        if b is None:
            no_match += 1
            continue
        if r["direction"] == b["direction"]:
            wrong_dir += 1
            continue
        d = 1 if b["direction"] == "long" else -1
        b_sl = b["entry_price"] - d * b["sl_pips"] * PIP
        b_tp = b["entry_price"] + d * b["tp_pips"] * PIP
        f_tp = r["entry_price"] - d * r["tp_pips"] * PIP    # fade direction is -d
        f_sl = r["entry_price"] + d * r["sl_pips"] * PIP
        bad_levels += not (abs(f_tp - b_sl) <= tol and abs(f_sl - b_tp) <= tol)
    return {"fade_no_matching_open_breakout": no_match, "fade_same_direction_as_breakout": wrong_dir,
            "fade_levels_not_mirrored": bad_levels,
            "info_breakouts_open_at_fix": held.height,
            "info_open_breakouts_without_fade": held.height - (trades.height - no_match)}


def random_walk_baseline(trades: pl.DataFrame) -> dict:
    """What an edge-free entry would score with these exits.

    Under a driftless random walk a bracket of SL/TP pips is hit TP-first with
    probability ~(SL - spread)/(SL+TP) (the spread is paid against you on both
    legs; the plain SL/(SL+TP) used for 001-003 ignored it), and its expected gross P&L is 0 (so expected net =
    -spread). Time-exited trades break the win-rate formula, so it is reported
    over SL/TP-resolved trades only; gross expectancy is compared to 0 over all.
    """
    bracket = trades.filter(pl.col("exit_reason").is_in(["sl", "tp"]))
    # TP needs a mid move of tp + spread, SL only sl - spread (entry at the far
    # side, exit at the near side) -> null TP-first rate (sl - spread)/(sl + tp).
    # spread_pips_paid (half in + half out) ~ one full spread.
    exp_win = ((bracket["sl_pips"] - bracket["spread_pips_paid"])
               / (bracket["sl_pips"] + bracket["tp_pips"])).mean()
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
    path = _find(num.partition(":")[0], "strategies", ".py")
    strategy = _load(num)
    run_dir = _run_dir(num)
    split = datetime(YEAR, 7, 1, tzinfo=timezone.utc)   # H1 = Jan-Jun, H2 = Jul-Dec (by entry)

    trades = engine.backtest(strategy)
    trades.write_parquet(run_dir / "trades.parquet")
    report = engine.evaluate(trades, starting_balance=10_000, pip_value=1.0, seed=SEED)

    halves = {}
    for name, part in (("H1_jan_jun", trades.filter(pl.col("entry_time") < split)),
                       ("H2_jul_dec", trades.filter(pl.col("entry_time") >= split))):
        r = engine.evaluate(part, starting_balance=10_000, pip_value=1.0, seed=SEED)
        halves[name] = {"summary": r["summary"], "verdict": r["verdict"],
                        "bootstrap_ci": r["adversarial"]["bootstrap_ci"],
                        "gross_vs_net": r["adversarial"]["gross_vs_net"]}

    for name, part in (strategy.report_splits(trades, strategy.generate_signals(bars)).items()
                       if hasattr(strategy, "report_splits") else ()):
        r = engine.evaluate(part, starting_balance=10_000, pip_value=1.0, seed=SEED)
        halves[f"split_{name}"] = {"summary": r["summary"], "verdict": r["verdict"],
                                   "bootstrap_ci": r["adversarial"]["bootstrap_ci"],
                                   "gross_vs_net": r["adversarial"]["gross_vs_net"]}

    result = {
        "run": f"{path.stem} [{num}] {YEAR}",
        "data_file": f"EURUSD_1s_{YEAR}.csv",
        "strategy": {k: v for k, v in vars(strategy).items()},
        "full_year": _headline(report),
        "halves": halves,
        "random_walk_baseline": random_walk_baseline(trades),
        "lookahead_audit": lookahead_audit(strategy, bars, trades, engine.base_1s),
        "monthly": report["monthly"].to_dicts(),
    }
    (run_dir / "results.json").write_text(json.dumps(_jsonable(result), indent=2))

    plot_equity(report).savefig(run_dir / "equity.png", dpi=110, bbox_inches="tight")
    plot_monthly(report).savefig(run_dir / "monthly.png", dpi=110, bbox_inches="tight")
    plot_mc_drawdown(report["adversarial"]["mc_drawdown"]).savefig(
        run_dir / "mc_drawdown.png", dpi=110, bbox_inches="tight")
    return result


def main(nums: list[str], year: int = 2024) -> None:
    global YEAR
    YEAR = year
    base = load_1s_data(str(DATA_DIR / f"EURUSD_1s_{year}.csv"), verbose=False)
    engines: dict[str, Engine] = {}   # one Engine per signal timeframe
    for num in nums:
        tf = _load(num).timeframe
        if tf not in engines:
            engines[tf] = Engine(resample(base, tf), base)
        r = run(num, engines[tf], engines[tf].signal_df)
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
    ap = argparse.ArgumentParser()
    ap.add_argument("specs", nargs="*", default=["001", "002", "003"])
    ap.add_argument("--year", type=int, default=2024)
    a = ap.parse_args()
    main(a.specs, a.year)
