"""Composable signal primitives (spec §4).

Pure polars-expression helpers that `Strategy.generate_signals()` implementations
call into. They add no columns and mutate nothing — a caller wires them up with
`with_columns`.

This module currently holds the two pieces the reference `SmaCrossoverStrategy`
needs: `sma` and `crossover`. The 4H trend filter and the session-window flag
arrive later, alongside the strategies that use them.
"""

from __future__ import annotations

import polars as pl


def sma(values: pl.Expr, n: int) -> pl.Expr:
    """Simple moving average of `values` over `n` bars.

    `min_samples = n`, so the first `n - 1` outputs are **null**, never a partial
    average — a half-formed SMA is not what a crossover means, and letting it
    through invites a subtle early-bars artifact.
    """
    if n < 1:
        raise ValueError(f"n must be >= 1, got {n}")
    return values.rolling_mean(window_size=n, min_samples=n)


def crossover(fast: pl.Expr, slow: pl.Expr) -> tuple[pl.Expr, pl.Expr]:
    """Detect where `fast` crosses `slow`.

    Returns `(cross_up, cross_down)`, both **genuine `pl.Boolean`** with no stray
    nulls:

    - `cross_up`   — `fast` was `<= slow` on the previous bar and is `> slow` now
    - `cross_down` — `fast` was `>= slow` on the previous bar and is `< slow` now

    Warmup is handled for free by shifting the raw `fast - slow` difference: on
    the first bar where both SMAs are valid, `diff.shift(1)` is still null, so the
    `&` is null there and `fill_null(False)` clears it — the earliest possible
    signal is one bar *after* both inputs are non-null. No spurious crossover at
    the warmup boundary.

    This is the spec §0.4 / §6 function. The result stays `pl.Boolean` end to
    end; it never becomes an object-dtype column of Python bools (the trap where
    a later `~` silently does a bitwise invert and inflates the signal count).
    """
    diff = fast - slow
    prev = diff.shift(1)
    cross_up = ((prev <= 0) & (diff > 0)).fill_null(False)
    cross_down = ((prev >= 0) & (diff < 0)).fill_null(False)
    return cross_up, cross_down
