"""Run 041 — trade-shape statistics and fair Sharpe for the EURUSD playbook pieces (040), 2023+2024.

Metrics from lib.evaluate (summary, sharpe_all_days); shape stats (holding time, streaks,
exit mix, R multiples) are counted from the trade logs.
"""

from __future__ import annotations

from datetime import date
from importlib import import_module
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402

from lib.evaluate import evaluate, sharpe_all_days  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "runs" / "041_playbook_trade_shapes"
COLS = ["entry_time", "exit_time", "pips", "direction", "exit_reason", "spread_pips_paid", "sl_pips", "tp_pips"]


def load(scratch: Path) -> pl.DataFrame:
    M25 = import_module("research.strategies.025_turn_confirm_continuation")
    p1 = []
    for y in (2023, 2024):
        b5 = pl.read_parquet(scratch / f"bars5m_{y}.parquet")
        ctx = M25.make_b().generate_signals(b5).select(pl.col("close_time").alias("entry_time"), "ctx_class")
        p1.append(pl.read_parquet(ROOT / f"research/runs/025_turn_confirm_continuation/b_{y}/trades.parquet")
                  .join(ctx, on="entry_time").filter(pl.col("ctx_class") == "trend_with").select(COLS))
    a = pl.concat(p1).with_columns(strat=pl.lit("Idea 2 (trend, 2R)"))
    b = pl.concat([pl.read_parquet(ROOT / f"research/runs/034_idea1_lon_ny/trades_with_hour_{y}.parquet")
                   .filter(pl.col("hour").is_in([3, 4]) & (pl.col("ctx_class") == "sideways")).select(COLS)
                   for y in (2023, 2024)]).with_columns(strat=pl.lit("London-open sideways fade"))
    c = pl.concat([pl.read_parquet(ROOT / "research/runs/018_orb_fix_fade/main_2023/trades.parquet").select(COLS),
                   pl.read_parquet(ROOT / "research/runs/018_orb_fix_fade/trades.parquet").select(COLS)]
                  ).with_columns(strat=pl.lit("Fix fade (018)"))
    return pl.concat([a, b, c]).sort("exit_time").with_columns(
        r=pl.col("pips") / pl.col("sl_pips"),
        hold_min=(pl.col("exit_time") - pl.col("entry_time")).dt.total_seconds() / 60,
    )


def streak(p: list[float]) -> int:
    best = cur = 0
    for v in p:
        cur = cur + 1 if v < 0 else 0
        best = max(best, cur)
    return best


def dd_duration_days(x: pl.DataFrame) -> float:
    eq = x["pips"].cum_sum().to_list()
    t = x["exit_time"].to_list()
    peak, peak_t, longest = 0.0, t[0], 0.0
    for v, ti in zip(eq, t):
        if v >= peak:
            peak, peak_t = v, ti
        else:
            longest = max(longest, (ti - peak_t).total_seconds() / 86400)
    return longest


def stats(x: pl.DataFrame) -> dict:
    x = x.sort("exit_time")
    s = evaluate(x)["summary"]
    fair = sharpe_all_days(x, date(2023, 1, 2), date(2024, 12, 31))
    er = dict(x.group_by("exit_reason").agg(pl.len()).iter_rows())
    n = x.height
    months = x.with_columns(m=pl.col("exit_time").dt.strftime("%Y-%m")).group_by("m").agg(p=pl.col("pips").sum())
    return {
        "trades": n, "trades_per_month": round(n / 24, 1),
        "win_rate_%": round(s["win_rate"], 1),
        "avg_win_pips": round(s["avg_win_pips"], 1), "avg_loss_pips": round(s["avg_loss_pips"], 1),
        "payoff_ratio": round(s["avg_win_pips"] / abs(s["avg_loss_pips"]), 2),
        "profit_factor": round(s["profit_factor"], 2),
        "expectancy_pips": round(s["expectancy_pips"], 2),
        "avg_R": round(x["r"].mean(), 2),
        "best_trade": round(x["pips"].max(), 1), "worst_trade": round(x["pips"].min(), 1),
        "median_stop_pips": round(x["sl_pips"].median(), 1), "median_target_pips": round(x["tp_pips"].median(), 1),
        "exits_tp_sl_time_%": [round(100 * er.get(k, 0) / n) for k in ("tp", "sl")]
                              + [round(100 * sum(v for k, v in er.items() if k not in ("tp", "sl")) / n)],
        "median_hold_min": round(x["hold_min"].median()), "p90_hold_min": round(x["hold_min"].quantile(0.9)),
        "max_losing_streak": streak(x["pips"].to_list()),
        "max_drawdown_%": round(s["max_drawdown_pct"], 2),
        "max_drawdown_pips": round(min(0.0, min(np.array(x["pips"].cum_sum().to_list()) - np.maximum.accumulate(np.maximum(0, np.array(x["pips"].cum_sum().to_list()))))), 1),
        "longest_drawdown_days": round(dd_duration_days(x)),
        "months_positive": f"{int((months['p'] > 0).sum())}/24",
        "sharpe_traded_days": round(s["sharpe"], 2) if s["sharpe"] is not None else None,
        "sharpe_all_days": round(fair["sharpe"], 2), "sortino_all_days": round(fair["sortino"], 2),
        "days_with_trades": f"{fair['days_with_trades']}/{fair['n_days']}",
        "total_pips": round(s["total_pips"], 1),
    }


def main(scratch: Path) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    allt = load(scratch)
    names = ["Idea 2 (trend, 2R)", "London-open sideways fade", "Fix fade (018)"]
    table = {n: stats(allt.filter(pl.col("strat") == n)) for n in names}
    table["COMBINED"] = stats(allt)
    keys = list(table["COMBINED"])
    print(f"{'':<24}" + "".join(f"{n[:22]:>24}" for n in table))
    for k in keys:
        print(f"{k:<24}" + "".join(f"{str(table[n][k]):>24}" for n in table))
    import json
    (OUT / "stats.json").write_text(json.dumps(table, indent=2, default=str))

    colors = {"Idea 2 (trend, 2R)": "#59A14F", "London-open sideways fade": "#E8A33D", "Fix fade (018)": "#B07AA1"}
    fig, ax = plt.subplots(2, 2, figsize=(13, 9))
    for n in names:
        x = allt.filter(pl.col("strat") == n)
        ax[0, 0].hist(x["pips"].to_list(), bins=40, alpha=0.55, color=colors[n], label=n)
        ax[0, 1].hist(x["r"].clip(-2, 4).to_list(), bins=30, alpha=0.55, color=colors[n], label=n)
    ax[0, 0].set_title("result per trade (pips)"); ax[0, 0].axvline(0, color="#555", lw=0.8); ax[0, 0].legend(fontsize=8)
    ax[0, 1].set_title("result per trade in R (1R = the stop distance; clipped at −2 / +4)"); ax[0, 1].axvline(0, color="#555", lw=0.8)
    ax[1, 0].boxplot([allt.filter(pl.col("strat") == n)["hold_min"].to_list() for n in names], tick_labels=[n.replace(" (", "\n(") for n in names], showfliers=False)
    ax[1, 0].set_title("holding time (minutes, box = middle 50%)")
    w = 0.25
    for i, n in enumerate(names):
        tp, sl, tm = table[n]["exits_tp_sl_time_%"]
        ax[1, 1].bar(np.arange(3) + (i - 1) * w, [tp, sl, tm], w, color=colors[n], label=n)
    ax[1, 1].set_xticks(range(3)); ax[1, 1].set_xticklabels(["target", "stop", "time / signal exit"]); ax[1, 1].set_ylabel("% of trades")
    ax[1, 1].set_title("how trades end"); ax[1, 1].legend(fontsize=8)
    for a in ax.flat:
        a.grid(alpha=0.25)
    fig.suptitle("EURUSD playbook pieces, 2023+2024: trade shapes", fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT / "trade_shapes.png", dpi=110)


if __name__ == "__main__":
    import sys
    main(Path(sys.argv[1]))
