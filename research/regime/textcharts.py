"""Plain-text charts for showing results directly in the chat (the user asked for equity and
monthly P&L "here in the chat"). Pure formatting: the numbers come from a trade log
(`pips`, `exit_time`); nothing here computes strategy metrics beyond cumulative sums.
"""

from __future__ import annotations

import polars as pl


def equity_chart(trades: pl.DataFrame, title: str, width: int = 60, height: int = 12) -> str:
    """Cumulative pips after each trade, drawn as a block chart."""
    t = trades.sort("exit_time")
    eq = t["pips"].cum_sum().to_list()
    if not eq:
        return f"{title}\n(no trades)"
    n = len(eq)
    cols = [eq[min(n - 1, round(i * (n - 1) / max(1, width - 1)))] for i in range(min(width, n))]
    lo, hi = min(0.0, min(cols)), max(0.0, max(cols))
    span = (hi - lo) or 1.0
    rows = []
    for r in range(height, -1, -1):
        level = lo + span * r / height
        line = "".join("█" if (v >= level >= 0) or (v <= level <= 0) else " " for v in cols)
        zero = abs(level) < span / height / 2
        label = f"{level:+8.0f} │"
        rows.append(label + (line.replace(" ", "─") if zero else line))
    first, last = t["exit_time"][0].strftime("%Y-%m"), t["exit_time"][-1].strftime("%Y-%m")
    rows.append(" " * 9 + "└" + "─" * len(cols))
    rows.append(" " * 10 + f"{first}{' ' * max(1, len(cols) - 14)}{last}")
    return f"{title}  (final {eq[-1]:+.1f} pips, {n} trades, max {max(eq):+.1f}, min {min(eq):+.1f})\n" + "\n".join(rows)


def monthly_chart(trades: pl.DataFrame, title: str, width: int = 30) -> str:
    """One row per month: net pips as a bar left (loss) or right (profit) of zero."""
    m = (trades.with_columns(month=pl.col("exit_time").dt.strftime("%Y-%m"))
         .group_by("month").agg(pips=pl.col("pips").sum(), n=pl.len()).sort("month"))
    if m.height == 0:
        return f"{title}\n(no trades)"
    big = max(abs(v) for v in m["pips"].to_list()) or 1.0
    half = width // 2
    lines = [title]
    for month, pips, n in m.iter_rows():
        k = round(abs(pips) / big * half)
        bar = (" " * (half - k) + "▓" * k + "│" + " " * half) if pips < 0 else (" " * half + "│" + "█" * k + " " * (half - k))
        lines.append(f"{month} {bar} {pips:+7.1f} ({n})")
    pos = (m["pips"] > 0).sum()
    lines.append(f"{pos}/{m.height} months positive · total {m['pips'].sum():+.1f} pips · █ profit ▓ loss")
    return "\n".join(lines)
