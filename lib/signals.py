"""Composable signal primitives (spec §4).

Pure polars-expression helpers that `Strategy.generate_signals()` implementations
call into. They add no columns and mutate nothing — a caller wires them up with
`with_columns`.

`sma` and `crossover` serve the reference `SmaCrossoverStrategy`; `atr` and the
DST-aware `session_window` arrived with research runs 001-003. The 4H trend
filter arrives later, alongside the strategy that uses it.
"""

from __future__ import annotations

from datetime import time

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


def atr(high: pl.Expr, low: pl.Expr, close: pl.Expr, n: int) -> pl.Expr:
    """Average true range: simple `n`-bar mean of the true range.

    TR_t = max(high_t - low_t, |high_t - close_{t-1}|, |low_t - close_{t-1}|).
    Only bars <= t feed row t (the previous close is a backward shift), so it is
    lookahead-safe. The first bar has no previous close -> TR is just high-low;
    the first `n - 1` outputs are **null**, like `sma`. Price units in, price
    units out (divide by PIP for pips).
    """
    if n < 1:
        raise ValueError(f"n must be >= 1, got {n}")
    prev = close.shift(1)
    tr = pl.max_horizontal(high - low, (high - prev).abs(), (low - prev).abs())
    return tr.rolling_mean(window_size=n, min_samples=n)


def session_window(
    ts: pl.Expr, start_tz: str, start: time, end_tz: str, end: time
) -> pl.Expr:
    """`pl.Boolean`: is `ts` inside [`start` in `start_tz`, `end` in `end_tz`)?

    Each zone's own clock and DST apply, so e.g. 07:00 America/New_York ->
    16:00 Europe/London is 4h most of the year and 5h in the weeks the US and UK
    DST switches disagree. The window is anchored on `ts`'s calendar date in
    `start_tz`: both bounds are built on that date, so a timestamp late in the
    evening (already "tomorrow" in London) is never mistaken for being before
    the next day's end bound. Start inclusive, end exclusive. `ts` must be
    tz-aware. Pure clock arithmetic — no lookahead concern.
    """
    day = ts.dt.convert_time_zone(start_tz).dt.date().cast(pl.Datetime("us"))

    def _bound(t: time, tz: str) -> pl.Expr:
        offset = pl.duration(hours=t.hour, minutes=t.minute, seconds=t.second)
        return (day + offset).dt.replace_time_zone(tz).dt.convert_time_zone("UTC")

    ts_utc = ts.dt.convert_time_zone("UTC")
    return ((ts_utc >= _bound(start, start_tz)) & (ts_utc < _bound(end, end_tz))).fill_null(False)


def higher_tf_join(
    df: pl.DataFrame, timeframe: str, close_col: str, features: dict[str, pl.Expr]
) -> pl.DataFrame:
    """Add higher-timeframe `features` to a lower-timeframe frame, lookahead-safe.

    Builds `timeframe` bars from `df[close_col]` (bucket close = the last
    lower-timeframe close in the bucket; buckets `label=left, closed=left`, as
    `resample`), evaluates `features` on that series (exprs over `pl.col("close")`,
    e.g. `{"up_15m": sma(pl.col("close"), 20) > sma(pl.col("close"), 50)}`), and
    joins them back **as-of backward on close_time**: row t sees only the latest
    higher-timeframe bar whose close_time <= row t's close_time — a bar still
    forming at t is invisible. Rows before the first such bar get null.

    `df` needs `timestamp`, `close_time` and `close_col`, sorted, with bars that
    nest inside the higher buckets (e.g. 1m inside 5m) — else `ValueError`.
    Returns `df` plus the feature columns; pure.
    """
    bucket_end = pl.col("timestamp").dt.truncate(timeframe).dt.offset_by(timeframe)
    if not df.select((pl.col("close_time") <= bucket_end).all()).item():
        raise ValueError(f"bars in df do not nest inside {timeframe} buckets")
    htf = (
        df.group_by_dynamic("timestamp", every=timeframe, label="left", closed="left")
        .agg(close=pl.col(close_col).last())
        .with_columns(_htf_close_time=pl.col("timestamp").dt.offset_by(timeframe))
        .with_columns(**features)
        .select("_htf_close_time", *features)
    )
    return df.join_asof(
        htf, left_on="close_time", right_on="_htf_close_time", strategy="backward"
    ).drop("_htf_close_time")


def rsi(values: pl.Expr, n: int) -> pl.Expr:
    """Wilder's RSI over `n` bars, 0-100.

    Gains/losses are bar-to-bar changes; both are smoothed with Wilder's
    recursive average (alpha = 1/n, adjust=False — equivalent to the classic
    seed-then-smooth form after warmup). Only bars <= t feed row t. The first
    `n` outputs are null (n changes need n+1 prices). All-gain → 100.
    """
    if n < 1:
        raise ValueError(f"n must be >= 1, got {n}")
    d = values.diff()
    gain = d.clip(lower_bound=0).ewm_mean(alpha=1 / n, adjust=False, min_samples=n)
    loss = (-d).clip(lower_bound=0).ewm_mean(alpha=1 / n, adjust=False, min_samples=n)
    return pl.when(loss == 0).then(100.0).otherwise(100 - 100 / (1 + gain / loss))
