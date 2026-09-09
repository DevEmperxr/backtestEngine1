"""Evaluation (spec §3).

- `evaluate(trades)` — the normal metrics (§3.1): headline scalars + equity curve
  + monthly breakdown.
- `adversarial(trades)` — the deterministic adversarial metrics (§3.2):
  gross-vs-net cost decomposition, P&L excluding the best month, P&L excluding
  the best N% of trades, and the sample-size gate on the verdict.
- `bootstrap_ci(trades)` — percentile-bootstrap CIs on win rate and expectancy.
- `mc_drawdown(trades)` — Monte-Carlo trade-order shuffle → max-drawdown
  distribution + a fragility flag.

A full §3.2 report is `adversarial` + `bootstrap_ci` + `mc_drawdown`.

Conventions
-----------
- **rf = 0** throughout. Sharpe and Sortino are excess-return ratios with a zero
  risk-free rate — not subtracted anywhere.
- **Fixed position size.** `pip_value` = dollars of P&L per pip; the engine
  tracks trades in pips only, sizing is purely an evaluate-time input (spec §2.4).
- **A trade is a "win" iff `pips > 0`, a "loss" iff `pips < 0`.** An exact
  break-even (`pips == 0`) counts toward `n_trades` but neither rate.
- **Daily returns** bucket realized P&L by `exit_time` date, over the days that
  actually had an exit (no zero-filled flat days), and `daily_return =
  daily_pnl / starting_balance` (simple, non-compounding).
- **`max_drawdown_pct`** is signed and negative (e.g. `-12.5` == equity fell
  12.5% below its high-water mark, which starts at `starting_balance`).
"""

from __future__ import annotations

from math import ceil, sqrt
from typing import Iterable

import numpy as np
import polars as pl

_TRADING_DAYS = 252
_YEAR_DAYS = 365.25

_SCALAR_KEYS = (
    "n_trades", "win_rate", "expectancy_pips", "profit_factor",
    "avg_win_pips", "avg_loss_pips", "total_pips", "total_return_pct",
    "max_drawdown_pct", "max_drawdown_date", "sharpe", "sortino", "mar",
)


def _empty_summary() -> dict:
    d = {k: None for k in _SCALAR_KEYS}
    d["n_trades"] = 0
    d["total_pips"] = 0.0
    d["total_return_pct"] = 0.0
    d["max_drawdown_pct"] = 0.0
    return d


def _monthly_breakdown(t: pl.DataFrame, pip_value: float) -> pl.DataFrame:
    """One row per calendar month (bucketed by `exit_time`): month, pips, pnl,
    n_trades, win_rate. Assumes `t` non-empty."""
    return (
        t.with_columns(month=pl.col("exit_time").dt.truncate("1mo").dt.date())
         .group_by("month")
         .agg(pips=pl.col("pips").sum(),
              n_trades=pl.len(),
              _wins=(pl.col("pips") > 0).sum())
         .sort("month")
         .with_columns(pnl=pl.col("pips") * pip_value,
                       win_rate=pl.col("_wins") / pl.col("n_trades") * 100.0)
         .select("month", "pips", "pnl", "n_trades", "win_rate")
    )


def evaluate(
    trades: pl.DataFrame,
    *,
    starting_balance: float = 10_000.0,
    pip_value: float = 1.0,
) -> dict:
    """Normal performance metrics for a trade log (spec §3.1).

    Parameters
    ----------
    trades : pl.DataFrame
        As returned by `Engine.backtest` — needs at least `pips` (float) and
        `exit_time` (datetime).
    starting_balance : float
        Account equity at t0, in dollars.
    pip_value : float
        Dollars of P&L per pip (fixed position size, spec §2.4).

    Returns
    -------
    dict with keys:
        summary       : dict of scalars (see module docstring for conventions)
        equity_curve  : pl.DataFrame — exit_time, cum_pips, equity, drawdown_pct
                        (one row per trade, exit order)
        monthly       : pl.DataFrame — month (date), pips, pnl, n_trades, win_rate
    """
    ts_dtype = trades.schema["exit_time"] if "exit_time" in trades.schema else pl.Datetime("us")
    empty_equity = pl.DataFrame(schema={
        "exit_time": ts_dtype, "cum_pips": pl.Float64,
        "equity": pl.Float64, "drawdown_pct": pl.Float64,
    })
    empty_monthly = pl.DataFrame(schema={
        "month": pl.Date, "pips": pl.Float64, "pnl": pl.Float64,
        "n_trades": pl.UInt32, "win_rate": pl.Float64,
    })

    if trades.height == 0:
        return {"summary": _empty_summary(), "equity_curve": empty_equity, "monthly": empty_monthly}

    t = trades.sort("exit_time")
    pips = t["pips"]
    n = t.height

    wins = pips.filter(pips > 0)
    losses = pips.filter(pips < 0)
    gross_win = float(wins.sum())          # >= 0
    gross_loss = float(losses.sum())       # <= 0

    if gross_loss == 0.0:
        profit_factor = float("inf") if gross_win > 0 else None
    else:
        profit_factor = gross_win / abs(gross_loss)

    # ---- equity curve ($) with HWM anchored at starting_balance ----
    cum_pips = pips.cum_sum()
    equity = starting_balance + cum_pips * pip_value
    hwm = pl.concat([pl.Series([float(starting_balance)]), equity]).cum_max()[1:]
    drawdown_pct = (equity - hwm) / hwm * 100.0

    equity_curve = pl.DataFrame({
        "exit_time": t["exit_time"],
        "cum_pips": cum_pips,
        "equity": equity,
        "drawdown_pct": drawdown_pct,
    })

    min_dd = drawdown_pct.min()
    if min_dd is not None and min_dd < 0:
        trough = drawdown_pct.arg_min()
        max_drawdown_pct = float(min_dd)
        max_drawdown_date = t["exit_time"][trough]
    else:
        max_drawdown_pct = 0.0
        max_drawdown_date = None

    # ---- daily returns -> Sharpe / Sortino (annualized, rf = 0) ----
    daily = (
        t.group_by(pl.col("exit_time").dt.date().alias("d"))
         .agg(pnl=pl.col("pips").sum() * pip_value)
         .sort("d")
    )
    daily_ret = daily["pnl"] / starting_balance
    ann = sqrt(_TRADING_DAYS)

    sd = daily_ret.std()  # sample std, ddof=1
    sharpe = float(daily_ret.mean() / sd * ann) if sd else None

    downside = daily_ret.filter(daily_ret < 0)
    dsd = downside.std()
    sortino = float(daily_ret.mean() / dsd * ann) if dsd else None

    # ---- CAGR / MAR ----
    span_days = (t["exit_time"].max() - t["entry_time"].min()).total_seconds() / 86_400
    total_pips = float(pips.sum())
    final_equity = starting_balance + total_pips * pip_value
    years = span_days / _YEAR_DAYS
    if years > 0 and final_equity > 0:
        cagr = (final_equity / starting_balance) ** (1.0 / years) - 1.0
    else:
        cagr = None

    max_dd_frac = max_drawdown_pct / 100.0
    mar = cagr / abs(max_dd_frac) if (cagr is not None and max_dd_frac < 0) else None

    monthly = _monthly_breakdown(t, pip_value)

    summary = {
        "n_trades": n,
        "win_rate": wins.len() / n * 100.0,
        "expectancy_pips": float(pips.mean()),
        "profit_factor": profit_factor,
        "avg_win_pips": float(wins.mean()) if wins.len() else None,
        "avg_loss_pips": float(losses.mean()) if losses.len() else None,
        "total_pips": total_pips,
        "total_return_pct": total_pips * pip_value / starting_balance * 100.0,
        "max_drawdown_pct": max_drawdown_pct,
        "max_drawdown_date": max_drawdown_date,
        "sharpe": sharpe,
        "sortino": sortino,
        "mar": mar,
    }
    return {"summary": summary, "equity_curve": equity_curve, "monthly": monthly}


# --------------------------------------------------------------------------- #
# adversarial metrics — deterministic subset (spec §3.2)
# --------------------------------------------------------------------------- #

_DEFAULT_EXCLUDE_PCT = (0.01, 0.05)


def adversarial(
    trades: pl.DataFrame,
    *,
    starting_balance: float = 10_000.0,
    pip_value: float = 1.0,
    exclude_best_pct: Iterable[float] = _DEFAULT_EXCLUDE_PCT,
    min_trades: int = 100,
) -> dict:
    """Deterministic adversarial checks (spec §3.2) — no resampling.

    Returns a dict:

    gross_vs_net : {net_pips, spread_paid_pips, gross_pips, net_pnl, gross_pnl,
                    spread_paid_pnl, edge_assessment}
        `gross = net + spread` — if `gross_pips <= 0` there was never an edge;
        if `gross > 0` but `net <= 0` the edge was real and the spread ate it.
        Needs the `spread_pips_paid` column from `Engine.backtest`.
    ex_best_month : {dropped_month, dropped_month_pips, pips, pnl, full_pips}
        totals with the single best (by pips) calendar month removed.
    ex_best_trades : list of {pct, n_dropped, pips, pnl}
        totals with the top `ceil(n * pct)` trades by pips removed, one entry per
        requested pct.
    sample_size : {n_trades, min_trades, low_sample, warning}
    verdict : str
        gated by sample size — below `min_trades` it reads
        "inconclusive (N trades, need ≥min)", never "profitable"/"unprofitable".
    """
    pcts = list(exclude_best_pct)
    n = trades.height
    low_sample = n < min_trades
    warning = (
        f"low sample: {n} trades (< {min_trades}) — estimates are imprecise, "
        f"the verdict is withheld"
        if low_sample else None
    )

    if n == 0:
        return {
            "gross_vs_net": {
                "net_pips": 0.0, "spread_paid_pips": 0.0, "gross_pips": 0.0,
                "net_pnl": 0.0, "gross_pnl": 0.0, "spread_paid_pnl": 0.0,
                "edge_assessment": "no trades",
            },
            "ex_best_month": {"dropped_month": None, "dropped_month_pips": 0.0,
                              "pips": 0.0, "pnl": 0.0, "full_pips": 0.0},
            "ex_best_trades": [{"pct": p, "n_dropped": 0, "pips": 0.0, "pnl": 0.0}
                               for p in pcts],
            "sample_size": {"n_trades": 0, "min_trades": min_trades,
                            "low_sample": True, "warning": warning},
            "verdict": f"inconclusive (0 trades, need ≥{min_trades})",
        }

    if "spread_pips_paid" not in trades.columns:
        raise ValueError(
            "trades is missing 'spread_pips_paid' — regenerate it with the "
            "current Engine.backtest (spec §3.2 step 0)"
        )

    # ---- gross vs net ----
    net_pips = float(trades["pips"].sum())
    spread_paid_pips = float(trades["spread_pips_paid"].sum())
    gross_pips = net_pips + spread_paid_pips
    if gross_pips <= 0:
        edge = "no edge — gross P&L (before spread) is not positive"
    elif net_pips <= 0:
        edge = "edge existed, costs ate it — gross positive but net not"
    else:
        edge = "profitable after costs"

    gross_vs_net = {
        "net_pips": net_pips,
        "spread_paid_pips": spread_paid_pips,
        "gross_pips": gross_pips,
        "net_pnl": net_pips * pip_value,
        "gross_pnl": gross_pips * pip_value,
        "spread_paid_pnl": spread_paid_pips * pip_value,
        "edge_assessment": edge,
    }

    # ---- P&L excluding the single best month ----
    monthly = _monthly_breakdown(trades, pip_value)
    best_month = monthly.sort("pips", descending=True).row(0, named=True)
    rem_month_pips = float(
        monthly.filter(pl.col("month") != best_month["month"])["pips"].sum()
    )
    ex_best_month = {
        "dropped_month": best_month["month"],
        "dropped_month_pips": float(best_month["pips"]),
        "pips": rem_month_pips,
        "pnl": rem_month_pips * pip_value,
        "full_pips": float(monthly["pips"].sum()),
    }

    # ---- P&L excluding the best N% of trades ----
    by_pips_desc = trades["pips"].sort(descending=True)
    ex_best_trades = []
    for p in pcts:
        k = ceil(n * p)
        rem = float(by_pips_desc.slice(k).sum())          # drop the top k
        ex_best_trades.append({
            "pct": p, "n_dropped": k, "pips": rem, "pnl": rem * pip_value,
        })

    # ---- verdict, gated by sample size ----
    if low_sample:
        verdict = f"inconclusive ({n} trades, need ≥{min_trades})"
    else:
        verdict = "profitable" if net_pips > 0 else "unprofitable"

    return {
        "gross_vs_net": gross_vs_net,
        "ex_best_month": ex_best_month,
        "ex_best_trades": ex_best_trades,
        "sample_size": {"n_trades": n, "min_trades": min_trades,
                        "low_sample": low_sample, "warning": warning},
        "verdict": verdict,
    }


# --------------------------------------------------------------------------- #
# adversarial metrics — resampling subset (spec §3.2)
# --------------------------------------------------------------------------- #

_MC_SCOPE_NOTE = (
    "This tests sequence risk on the trades you already have — it cannot detect "
    "a missing edge, and a good shuffle distribution is not validation of the "
    "strategy."
)


def _pips_array(trades: pl.DataFrame) -> np.ndarray:
    return trades["pips"].to_numpy() if trades.height else np.empty(0, dtype=float)


def bootstrap_ci(
    trades: pl.DataFrame,
    *,
    n_resamples: int = 10_000,
    confidence: float = 0.95,
    seed: int | None = None,
) -> dict:
    """Percentile-bootstrap confidence intervals on win rate and expectancy.

    Resamples the realized `pips` array **with replacement** `n_resamples` times
    and reads the CI off the percentiles of the resulting distribution — no
    normal approximation, so it holds up under the skewed / fat-tailed trade P&L
    (fixed TP, variable-size losses; spec §3.2). Deterministic given `seed`.

    Returns, for each of `win_rate` (%) and `expectancy_pips`:
        {observed, mean, ci_low, ci_high}
    plus `n_resamples`, `confidence`, `seed`.
    """
    pips = _pips_array(trades)
    n = pips.size
    lo_q = (1.0 - confidence) / 2.0 * 100.0
    hi_q = 100.0 - lo_q

    meta = {"n_resamples": n_resamples, "confidence": confidence, "seed": seed}
    if n == 0:
        blank = {"observed": None, "mean": None, "ci_low": None, "ci_high": None}
        return {"win_rate": dict(blank), "expectancy_pips": dict(blank), **meta}

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_resamples, n))
    samples = pips[idx]                                    # (B, n)
    win_rates = (samples > 0).mean(axis=1) * 100.0
    expectancies = samples.mean(axis=1)

    def _stat(observed: float, dist: np.ndarray) -> dict:
        return {
            "observed": float(observed),
            "mean": float(dist.mean()),
            "ci_low": float(np.percentile(dist, lo_q)),
            "ci_high": float(np.percentile(dist, hi_q)),
        }

    return {
        "win_rate": _stat((pips > 0).mean() * 100.0, win_rates),
        "expectancy_pips": _stat(pips.mean(), expectancies),
        **meta,
    }


def _max_drawdown_pct(seqs: np.ndarray, starting_balance: float, pip_value: float) -> np.ndarray:
    """Signed (≤ 0) max drawdown % for each row of pip sequences `seqs` (R × n).
    HWM anchored at `starting_balance`."""
    equity = starting_balance + np.cumsum(seqs, axis=1) * pip_value
    anchor = np.full((equity.shape[0], 1), float(starting_balance))
    hwm = np.maximum.accumulate(np.concatenate([anchor, equity], axis=1), axis=1)[:, 1:]
    return ((equity - hwm) / hwm * 100.0).min(axis=1)


def mc_drawdown(
    trades: pl.DataFrame,
    *,
    n_shuffles: int = 10_000,
    starting_balance: float = 10_000.0,
    pip_value: float = 1.0,
    seed: int | None = None,
) -> dict:
    """Monte-Carlo trade-order shuffle → distribution of max drawdown.

    Shuffles the **order** of the realized pips `n_shuffles` times (the values,
    and therefore total P&L, are unchanged — only the equity path) and rebuilds
    the max drawdown each time. Answers: was the historical drawdown just a lucky
    ordering? Deterministic given `seed`.

    Returns:
        observed_max_drawdown_pct  — the real historical ordering (≤ 0)
        median, p95, worst         — of the shuffled max-DD distribution; `p95`
                                     is the 5th percentile of the signed values
                                     (the worse tail), `worst` the minimum
        percentile_rank            — % of reorderings that ended up worse than
                                     the real one
        fragile (bool) + fragile_note
        note                       — the scope caveat (spec §3.2, verbatim)
        distribution               — the `n_shuffles` max-DD values (np.ndarray),
                                     for `plot_mc_drawdown`
    """
    pips = _pips_array(trades)
    n = pips.size
    meta = {"n_shuffles": n_shuffles, "seed": seed, "note": _MC_SCOPE_NOTE}

    if n == 0:
        return {
            "observed_max_drawdown_pct": 0.0, "median": None, "p95": None,
            "worst": None, "percentile_rank": None, "fragile": False,
            "fragile_note": "no trades", **meta,
        }

    observed = float(_max_drawdown_pct(pips[None, :], starting_balance, pip_value)[0])

    rng = np.random.default_rng(seed)
    orders = rng.random((n_shuffles, n)).argsort(axis=1)   # random permutations
    # sort the source first so the distribution depends only on the *multiset*
    # of realized pips, not the order they arrived in — total P&L is invariant,
    # only the equity path changes.
    shuffled_dd = _max_drawdown_pct(np.sort(pips)[orders], starting_balance, pip_value)

    p25 = float(np.percentile(shuffled_dd, 25))
    fragile = bool(observed > p25)                         # milder than 25% of reorderings

    return {
        "observed_max_drawdown_pct": observed,
        "median": float(np.median(shuffled_dd)),
        "p95": float(np.percentile(shuffled_dd, 5)),       # worse tail (signed)
        "worst": float(shuffled_dd.min()),
        "percentile_rank": float((shuffled_dd < observed).mean() * 100.0),
        "fragile": fragile,
        "fragile_note": (
            "fragile == the real ordering's drawdown is milder than the 25th "
            "percentile of the shuffled distribution — a large fraction of "
            "reorderings would have been worse, so the reported drawdown may be "
            "a lucky-ordering artifact."
        ),
        "distribution": shuffled_dd,                       # for plot_mc_drawdown
        **meta,
    }


# --------------------------------------------------------------------------- #
# plots — matplotlib is lazy-imported so headless / CI never pays for it
# (same rule as the deferred viz.py). Each returns a Figure; the caller shows
# or saves it.
# --------------------------------------------------------------------------- #

def plot_equity(result: dict):
    """$ equity curve over time with the drawdown shaded on a second axis.

    `result` is an `evaluate()` (or `Engine.evaluate()`) return — uses
    `result["equity_curve"]`.
    """
    import matplotlib.pyplot as plt

    ec = result["equity_curve"]
    fig, ax = plt.subplots(figsize=(11, 4))

    if ec.height:
        x = ec["exit_time"].to_list()
        ax.plot(x, ec["equity"].to_list(), color="#1f77b4", lw=1.3, label="equity ($)")
        dd = ax.twinx()
        dd.fill_between(x, ec["drawdown_pct"].to_list(), 0.0,
                        color="#d62728", alpha=0.20, step="post")
        dd.set_ylabel("drawdown (%)", color="#d62728")
        dd.tick_params(axis="y", colors="#d62728")
        dd.set_ylim(min(ec["drawdown_pct"].min() * 1.2, -0.1), 0.0)

    ax.set_title("Equity curve")
    ax.set_ylabel("equity ($)")
    ax.set_xlabel("exit time")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    return fig


def plot_monthly(result: dict):
    """Monthly P&L bar chart (green ≥ 0 / red < 0). Uses `result["monthly"]`."""
    import matplotlib.pyplot as plt

    m = result["monthly"]
    fig, ax = plt.subplots(figsize=(11, 4))

    if m.height:
        months = [d.isoformat()[:7] for d in m["month"].to_list()]
        pnl = m["pnl"].to_list()
        ax.bar(months, pnl, color=["#2ca02c" if v >= 0 else "#d62728" for v in pnl])
        ax.axhline(0.0, color="black", lw=0.8)
        ax.tick_params(axis="x", rotation=45)

    ax.set_title("Monthly P&L ($)")
    ax.set_ylabel("P&L ($)")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    return fig


def plot_mc_drawdown(mc_result: dict):
    """Histogram of the Monte-Carlo shuffled max-drawdown distribution, with the
    observed (real-ordering) drawdown marked. `mc_result` is an `mc_drawdown()`
    return (needs its `distribution` array)."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 4))
    dist = mc_result.get("distribution")
    if dist is not None and len(dist):
        ax.hist(np.asarray(dist), bins=50, color="#9467bd", alpha=0.8)
        obs = mc_result["observed_max_drawdown_pct"]
        ax.axvline(obs, color="black", lw=2,
                   label=f"observed {obs:.1f}%  (rank {mc_result['percentile_rank']:.0f}%)")
        ax.axvline(mc_result["median"], color="#7f7f7f", ls="--", lw=1, label="shuffle median")
        ax.legend()

    ax.set_title("Max drawdown across trade-order shuffles"
                 + ("  — FRAGILE" if mc_result.get("fragile") else ""))
    ax.set_xlabel("max drawdown (%)")
    ax.set_ylabel("shuffles")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    return fig
