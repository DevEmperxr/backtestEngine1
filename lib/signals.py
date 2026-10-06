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



# --------------------------------------------------------------------------- #
# Trend / regime detectors (research 020). All use only bars <= t for row t.
# --------------------------------------------------------------------------- #

def efficiency_ratio(values: pl.Expr, n: int) -> pl.Expr:
    """Kaufman efficiency ratio over the last `n` bars: |net change| / sum of
    |bar-to-bar changes|. 1 = straight line, ~0 = chop. Null for the first `n`
    rows; null (not inf) if price did not move at all."""
    if n < 1:
        raise ValueError(f"n must be >= 1, got {n}")
    path = values.diff().abs().rolling_sum(window_size=n, min_samples=n)
    net = (values - values.shift(n)).abs()
    return pl.when(path > 0).then(net / path)


def adx(high: pl.Expr, low: pl.Expr, close: pl.Expr, n: int) -> pl.Expr:
    """Wilder's ADX(n). +DM/-DM and TR smoothed with Wilder's recursive average
    (alpha = 1/n, adjust=False, as `rsi`), DX = 100·|+DI − −DI| / (+DI + −DI),
    ADX = Wilder average of DX. Direction-free trend strength, 0–100."""
    if n < 1:
        raise ValueError(f"n must be >= 1, got {n}")
    up, down = high.diff(), -low.diff()
    plus_dm = pl.when((up > down) & (up > 0)).then(up).otherwise(0.0)
    minus_dm = pl.when((down > up) & (down > 0)).then(down).otherwise(0.0)
    prev = close.shift(1)
    tr = pl.max_horizontal(high - low, (high - prev).abs(), (low - prev).abs())
    w = lambda e: e.ewm_mean(alpha=1 / n, adjust=False, min_samples=n)
    s_tr = w(tr)
    pdi, mdi = 100 * w(plus_dm) / s_tr, 100 * w(minus_dm) / s_tr
    dx = pl.when((pdi + mdi) > 0).then(100 * (pdi - mdi).abs() / (pdi + mdi)).otherwise(0.0)
    return dx.ewm_mean(alpha=1 / n, adjust=False, min_samples=n)


def choppiness(high: pl.Expr, low: pl.Expr, close: pl.Expr, n: int) -> pl.Expr:
    """Choppiness Index(n) = 100·log10(ΣTR_n / (max high_n − min low_n)) / log10(n).
    High (→100) = choppy, low = trending. n >= 2."""
    if n < 2:
        raise ValueError(f"n must be >= 2, got {n}")
    import math
    prev = close.shift(1)
    tr = pl.max_horizontal(high - low, (high - prev).abs(), (low - prev).abs())
    rng = high.rolling_max(n, min_samples=n) - low.rolling_min(n, min_samples=n)
    s = tr.rolling_sum(n, min_samples=n)
    return pl.when(rng > 0).then(100 * (s / rng).log10() / math.log10(n))


def rolling_r2(values: pl.Expr, n: int) -> pl.Expr:
    """R² of a straight-line fit of the last `n` values on time (= squared
    correlation with a time index). 1 = perfectly linear path."""
    if n < 3:
        raise ValueError(f"n must be >= 3, got {n}")
    t = pl.int_range(0, pl.len()).cast(pl.Float64)
    return pl.rolling_corr(values, t, window_size=n, min_samples=n) ** 2


def variance_ratio(values: pl.Expr, q: int, n: int) -> pl.Expr:
    """Lo–MacKinlay variance ratio over the last `n` bars: Var(q-bar changes) /
    (q · Var(1-bar changes)). >1 trending (positive autocorrelation), <1 mean
    reverting, ≈1 random walk. (Overlapping q-bar changes; no bias correction.)"""
    if q < 2 or n <= q:
        raise ValueError(f"need q >= 2 and n > q, got q={q}, n={n}")
    r1 = values.diff()
    rq = values - values.shift(q)
    return rq.rolling_var(n, min_samples=n) / (q * r1.rolling_var(n, min_samples=n))


def return_autocorr(values: pl.Expr, n: int, lag: int = 1) -> pl.Expr:
    """Correlation of bar-to-bar changes with their own value `lag` bars earlier,
    over the last `n` changes. >0 = moves tend to continue."""
    if n < 3 or lag < 1:
        raise ValueError(f"need n >= 3 and lag >= 1, got n={n}, lag={lag}")
    r = values.diff()
    return pl.rolling_corr(r, r.shift(lag), window_size=n, min_samples=n)
