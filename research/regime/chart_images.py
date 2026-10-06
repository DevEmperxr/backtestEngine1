"""PNG equity + monthly P&L charts for showing results in the chat (user preference:
real images, not text charts). Pure presentation of a trade log's `pips` / `exit_time`.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import polars as pl  # noqa: E402


def equity_and_monthly_png(trades: pl.DataFrame, title: str, out: Path) -> Path:
    t = trades.sort("exit_time")
    eq = t["pips"].cum_sum().to_list()
    x = t["exit_time"].dt.replace_time_zone(None).to_list()
    m = (t.with_columns(month=pl.col("exit_time").dt.strftime("%Y-%m"))
         .group_by("month").agg(pips=pl.col("pips").sum(), n=pl.len()).sort("month"))

    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 7.5), gridspec_kw={"height_ratios": [1.15, 1]})
    a1.plot(x, eq, color="#2E6BD8", lw=1.8)
    a1.fill_between(x, eq, 0, where=[v >= 0 for v in eq], color="#2E6BD8", alpha=0.12)
    a1.fill_between(x, eq, 0, where=[v < 0 for v in eq], color="#D84A2E", alpha=0.12)
    a1.axhline(0, color="#888", lw=0.8)
    a1.set_title(f"{title}\nfinal {eq[-1]:+.1f} pips · {len(eq)} trades · peak {max(eq):+.1f} · low {min(eq):+.1f}",
                 fontsize=11)
    a1.set_ylabel("cumulative pips")
    a1.grid(alpha=0.25)

    colors = ["#2E9E5B" if v > 0 else "#D84A2E" for v in m["pips"].to_list()]
    a2.bar(m["month"].to_list(), m["pips"].to_list(), color=colors)
    for i, (v, n) in enumerate(zip(m["pips"].to_list(), m["n"].to_list())):
        a2.text(i, v + (2 if v >= 0 else -2), f"{n}", ha="center", va="bottom" if v >= 0 else "top", fontsize=7, color="#555")
    a2.axhline(0, color="#888", lw=0.8)
    pos = int((m["pips"] > 0).sum())
    a2.set_title(f"monthly P&L (pips; number = trades) · {pos}/{m.height} months positive", fontsize=10)
    a2.set_ylabel("pips")
    a2.tick_params(axis="x", rotation=60, labelsize=8)
    a2.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=110)
    plt.close(fig)
    return out
