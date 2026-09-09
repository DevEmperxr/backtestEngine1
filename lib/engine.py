"""Backtest engine (spec §2).

Contains the `Strategy` ABC (§2.2) and `Engine` (§2.1), plus the numba 1s-path
SL/TP resolver (`_resolve_exit`, §2.3). `backtest` is complete: rising-edge
entries with t+1 timing (§0.1), spread-correct fills (§0.3), and per-trade exit
resolved on the real 1s path — SL / TP / opposite-signal / end-of-data, with the
within-bar ordering of §0.2 respected.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
import polars as pl
from numba import njit

from lib.data import PIP, validate_1s

_PRICE_COLUMNS = tuple(
    f"{side}_{field}"
    for side in ("bid", "ask")
    for field in ("open", "high", "low", "close")
)

# _resolve_exit reason codes
_NO_TOUCH = 0
_HIT_SL = 1
_HIT_TP = 2


@njit(cache=True)
def _resolve_exit(exit_high, exit_low, start_idx, end_idx,
                  direction, sl_level, tp_level):
    """Walk the 1s path [start_idx, end_idx) for the first SL or TP touch.

    `exit_high` / `exit_low` are the 1s high/low of the side the trade exits
    *against* (spec §0.3): a long exits by selling, so the caller passes the BID
    arrays; a short exits by buying, so the caller passes the ASK arrays. This
    function neither knows nor cares which side it was handed.

    direction: +1 long, -1 short.
      long : SL when exit_low[k]  <= sl_level ; TP when exit_high[k] >= tp_level
      short: SL when exit_high[k] >= sl_level ; TP when exit_low[k]  <= tp_level
    Touches are inclusive.

    Returns (hit_idx, exit_price, reason_code):
        reason 0 (_NO_TOUCH) -> hit_idx == end_idx, exit_price == 0.0
        reason 1 (_HIT_SL)   -> hit_idx == k, exit_price == sl_level
        reason 2 (_HIT_TP)   -> hit_idx == k, exit_price == tp_level

    exit_price is the level itself — we model a resting stop / limit order that
    fills at its price, not at the traded extreme.

    If a single 1s bar's [low, high] straddles BOTH levels, SL wins. This is the
    spec's old "assume SL hit first" tie-break, but now it only bites within one
    second of price action rather than across a whole signal-timeframe bar, so
    it is rare and its cost is bounded.
    """
    for k in range(start_idx, end_idx):
        if direction == 1:
            sl_hit = exit_low[k] <= sl_level
            tp_hit = exit_high[k] >= tp_level
        else:
            sl_hit = exit_high[k] >= sl_level
            tp_hit = exit_low[k] <= tp_level

        if sl_hit:
            return k, sl_level, _HIT_SL
        if tp_hit:
            return k, tp_level, _HIT_TP

    return end_idx, 0.0, _NO_TOUCH


def _sl_tp_levels(direction, entry_price, sl_pips, tp_pips, pip=PIP):
    """Absolute SL/TP price levels for a position.

    long  (+1): SL below entry, TP above.
    short (-1): SL above entry, TP below.

    Returns (sl_level, tp_level).
    """
    offset_sl = sl_pips * pip
    offset_tp = tp_pips * pip
    if direction == 1:
        return entry_price - offset_sl, entry_price + offset_tp
    return entry_price + offset_sl, entry_price - offset_tp


class Strategy(ABC):
    """Formal strategy interface (spec §2.2).

    A concrete strategy is a small subclass that implements `generate_signals`.
    SL/TP and the timeframe are part of what *defines* a strategy variant, so
    they are constructor args, not engine-run arguments. A subclass calls
    `super().__init__(...)` then adds its own params (e.g. `fast_n`, `slow_n`).

    Attributes
    ----------
    sl_pips : float
        Stop-loss distance in pips (> 0).
    tp_pips : float
        Take-profit distance in pips (> 0).
    timeframe : str
        Resampled timeframe this strategy operates on ("5m", "1h", ...). Drives
        the no-lookahead "bar t's close" calculation below.
    exit_on_opposite_signal : bool, class attribute, default True
        Whether the engine also closes an open position when the opposite signal
        fires, on top of SL/TP. Set False on a subclass to exit only via SL/TP.
    reverse_on_opposite_signal : bool, class attribute, default False
        On an opposite-signal exit, immediately open the opposite position at the
        same bar/open ("always in the market"). Requires
        `exit_on_opposite_signal`. A trade that exits via SL/TP/end-of-data stops
        the reversal chain — the engine goes flat.
    """

    exit_on_opposite_signal: bool = True
    reverse_on_opposite_signal: bool = False

    def __init__(self, sl_pips: float, tp_pips: float, timeframe: str) -> None:
        if not (sl_pips > 0):
            raise ValueError(f"sl_pips must be > 0, got {sl_pips!r}")
        if not (tp_pips > 0):
            raise ValueError(f"tp_pips must be > 0, got {tp_pips!r}")
        if not isinstance(timeframe, str) or not timeframe:
            raise ValueError(f"timeframe must be a non-empty str, got {timeframe!r}")
        if self.reverse_on_opposite_signal and not self.exit_on_opposite_signal:
            raise ValueError(
                "reverse_on_opposite_signal requires exit_on_opposite_signal"
            )
        self.sl_pips = float(sl_pips)
        self.tp_pips = float(tp_pips)
        self.timeframe = timeframe

    @abstractmethod
    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        """Pure signal computation: does not mutate `df`, returns a new frame.

        Must add at least two columns: `long_signal` and `short_signal`, both
        genuine `pl.Boolean` dtype. The engine trusts these are real booleans —
        this is exactly where the spec §0.4 boolean-dtype trap bites (a
        `.shift(1)` that upcasts to object and turns `~` into a bitwise op).

        May add any number of other columns (SMA values, `trend_direction`,
        session flags); the engine ignores them — they exist for debugging and
        the deferred visualizer.

        Responsible for its OWN no-lookahead correctness: a value at row `t` may
        only use information available through bar `t`'s close, where "bar `t`'s
        close" = `bar_start + self.timeframe` — computed from the actual
        timeframe, never a hardcoded +5m. The engine separately enforces the
        "act at `t+1`" timing rule; that is a different responsibility (§0.1).
        """


class Engine:
    """Runs a `Strategy` over resampled bars and produces a trade log (spec §2.1).

    Loading is a separate concern — `Engine` is handed frames that were already
    cleaned upstream (`data.load_1s_data` / `data.resample`), and re-checks the
    1s base at construction so a dirty frame fails loudly here rather than
    silently corrupting a backtest.

    `backtest`: rising-edge entries honour the t+1 rule (§0.1) and spread-correct
    fills (§0.3). Each trade's exit is then resolved on the real 1s path
    (`_resolve_exit`, §2.3): SL / TP first-touch, an opposite-signal exit raced
    against them (only if `strategy.exit_on_opposite_signal`), or a force-close
    at end of data (§2.4). If `strategy.reverse_on_opposite_signal`, an
    opposite-signal exit immediately opens the opposite position at the same
    open — the chain continues until a trade exits via SL/TP/end-of-data.
    Scanning then resumes at the first signal bar at/after that exit, so trades
    never overlap in wall-clock time.
    """

    _TRADE_SCHEMA_TAIL = {
        "entry_price": pl.Float64,
        "direction": pl.String,
        "exit_price": pl.Float64,
        "pips": pl.Float64,
        "exit_reason": pl.String,
        "spread_pips_paid": pl.Float64,
    }
    _TRADE_COLUMNS = (
        "entry_time", "entry_price", "direction",
        "exit_time", "exit_price", "pips", "exit_reason", "spread_pips_paid",
    )

    def __init__(self, signal_df: pl.DataFrame, base_1s: pl.DataFrame) -> None:
        # Validate base_1s with the data layer's single source of truth
        # (spec §2.1) — never re-implement the §0.5 checks here.
        validate_1s(base_1s)
        self.base_1s = base_1s

        missing = [
            c for c in ("timestamp", "close_time", *_PRICE_COLUMNS)
            if c not in signal_df.columns
        ]
        if missing:
            raise ValueError(f"signal_df is missing column(s): {missing}")
        if not signal_df["timestamp"].is_sorted():
            raise ValueError("signal_df must be sorted by timestamp")
        self.signal_df = signal_df

        # Cache the 1s path as plain arrays once — the per-trade walk needs
        # contiguous numpy, and rebuilding it per trade would dominate runtime.
        self._ts_ns = base_1s["timestamp"].dt.epoch("ns").to_numpy()
        self._bid_high = base_1s["bid_high"].to_numpy()
        self._bid_low = base_1s["bid_low"].to_numpy()
        self._bid_close = base_1s["bid_close"].to_numpy()
        self._ask_high = base_1s["ask_high"].to_numpy()
        self._ask_low = base_1s["ask_low"].to_numpy()
        self._ask_close = base_1s["ask_close"].to_numpy()

    def backtest(self, strategy: Strategy) -> pl.DataFrame:
        """Run `strategy`; return the trade log.

        Columns: entry_time, entry_price, direction ("long"/"short"), exit_time,
        exit_price, pips, exit_reason in {"sl", "tp", "opposite_signal",
        "end_of_data"}, spread_pips_paid (half-spread in + half-spread out, pips —
        so gross = net pips + spread_pips_paid).
        """
        sig = strategy.generate_signals(self.signal_df)
        for col in ("long_signal", "short_signal"):
            if col not in sig.columns:
                raise ValueError(f"generate_signals did not add a {col!r} column")
            if sig.schema[col] != pl.Boolean:
                raise ValueError(
                    f"{col} must be pl.Boolean dtype, got {sig.schema[col]} (spec §0.4)"
                )
        if (sig["long_signal"] & sig["short_signal"]).any():
            raise ValueError("ambiguous bar: long_signal and short_signal both True")

        # Rising edges only — enter on a fresh False->True transition, not on
        # every bar a state signal stays True. shift(1, fill_value=False) keeps a
        # genuine Boolean dtype; `~` is a real logical-not here (spec §0.4).
        sig = sig.with_columns(
            _entry_long=pl.col("long_signal") & ~pl.col("long_signal").shift(1, fill_value=False),
            _entry_short=pl.col("short_signal") & ~pl.col("short_signal").shift(1, fill_value=False),
        )

        sig_ts = sig["timestamp"].to_list()                       # for the log
        sig_ts_ns = sig["timestamp"].dt.epoch("ns").to_numpy()    # for searchsorted
        ask_open = sig["ask_open"].to_list()
        bid_open = sig["bid_open"].to_list()
        entry_long = sig["_entry_long"].to_list()
        entry_short = sig["_entry_short"].to_list()

        base_ts = self.base_1s["timestamp"]
        n_sig = sig.height
        n_base = len(self._ts_ns)

        def resolve(entry_bar: int, direction: int):
            """Resolve one trade opened at signal bar `entry_bar`'s open,
            direction +1/-1. Returns (trade, resume_t, reversal); `reversal` is
            (new_entry_bar, new_direction) iff the trade exited opposite_signal
            and the strategy reverses, else None."""
            entry_time = sig_ts[entry_bar]
            # long fills at ask, short at bid — for a fresh entry AND a reversal
            # (the close and the re-open are the same side of the book, §0.3).
            entry_price = ask_open[entry_bar] if direction == 1 else bid_open[entry_bar]
            entry_half_spread = (ask_open[entry_bar] - bid_open[entry_bar]) / 2 / PIP
            sl_level, tp_level = _sl_tp_levels(
                direction, entry_price, strategy.sl_pips, strategy.tp_pips
            )

            # First 1s row at/after entry — the entry second is exposed to its
            # own range (open first, then the range unfolds, §0.2).
            start_idx = int(np.searchsorted(self._ts_ns, sig_ts_ns[entry_bar], side="left"))
            if direction == 1:                       # long exits by selling -> bid
                exit_high, exit_low = self._bid_high, self._bid_low
            else:                                    # short exits by buying -> ask
                exit_high, exit_low = self._ask_high, self._ask_low

            # Opposite-signal exit (spec §2.2) — race it against SL/TP. First
            # opposite rising edge at bar k >= entry_bar, acted on at k+1's open.
            end_idx = n_base
            signal_exit = None
            opp_bar = None
            if strategy.exit_on_opposite_signal:
                opp_edge = entry_short if direction == 1 else entry_long
                k = entry_bar
                while k < n_sig and not opp_edge[k]:
                    k += 1
                if k < n_sig and k + 1 < n_sig:
                    # Walk only up to (not including) bar k+1's open: the signal
                    # exit fills at that open, BEFORE the bar's range unfolds, so
                    # the position never sees k+1's intrabar SL/TP (§0.2).
                    end_idx = int(np.searchsorted(self._ts_ns, sig_ts_ns[k + 1], side="left"))
                    signal_exit = (
                        sig_ts[k + 1],
                        bid_open[k + 1] if direction == 1 else ask_open[k + 1],
                        int(sig_ts_ns[k + 1]),
                    )
                    opp_bar = k

            hit_idx, exit_price, reason = _resolve_exit(
                exit_high, exit_low, start_idx, end_idx, direction, sl_level, tp_level
            )

            if reason == _HIT_SL:  # SL genuinely happened first
                exit_time, exit_ns, exit_reason = base_ts[hit_idx], int(self._ts_ns[hit_idx]), "sl"
                exit_price = float(exit_price)
            elif reason == _HIT_TP:
                exit_time, exit_ns, exit_reason = base_ts[hit_idx], int(self._ts_ns[hit_idx]), "tp"
                exit_price = float(exit_price)
            elif signal_exit is not None:  # nothing touched first -> signal wins
                exit_time, exit_price, exit_ns = signal_exit[0], float(signal_exit[1]), signal_exit[2]
                exit_reason = "opposite_signal"
            else:  # _NO_TOUCH, no signal exit -> force close at end of data (§2.4)
                exit_time = base_ts[n_base - 1]
                exit_price = float(self._bid_close[-1] if direction == 1 else self._ask_close[-1])
                exit_ns, exit_reason = int(self._ts_ns[n_base - 1]), "end_of_data"

            if direction == 1:
                pips = (exit_price - entry_price) / PIP
            else:
                pips = (entry_price - exit_price) / PIP

            # Half-spread paid getting out, at the exit instant (spec §3.2 needs
            # the round-trip spread cost; entry-at-ask/exit-at-bid already bakes
            # it into `pips`, so gross = net + spread_pips_paid).
            if exit_reason in ("sl", "tp"):
                exit_half_spread = (self._ask_close[hit_idx] - self._bid_close[hit_idx]) / 2 / PIP
            elif exit_reason == "opposite_signal":
                exit_half_spread = (ask_open[opp_bar + 1] - bid_open[opp_bar + 1]) / 2 / PIP
            else:  # end_of_data
                exit_half_spread = (self._ask_close[-1] - self._bid_close[-1]) / 2 / PIP

            trade = {
                "entry_time": entry_time,
                "entry_price": float(entry_price),
                "direction": "long" if direction == 1 else "short",
                "exit_time": exit_time,
                "exit_price": exit_price,
                "pips": float(pips),
                "exit_reason": exit_reason,
                "spread_pips_paid": float(entry_half_spread + exit_half_spread),
            }

            resume_t = int(np.searchsorted(sig_ts_ns, exit_ns, side="left"))
            reversal = None
            if exit_reason == "opposite_signal" and strategy.reverse_on_opposite_signal:
                # re-open the opposite at the same bar/open we just closed at.
                # opp_bar strictly increases down the chain, so it terminates.
                reversal = (opp_bar + 1, -direction)
            return trade, resume_t, reversal

        trades: list[dict] = []
        t = 0
        # Small outer loop over the resampled frame — not the bottleneck (§2.3).
        while t < n_sig:
            if entry_long[t] and t + 1 < n_sig:
                direction = 1
            elif entry_short[t] and t + 1 < n_sig:
                direction = -1
            else:
                t += 1
                continue

            entry_bar = t + 1                        # acted on at t+1's open (§0.1)
            while True:
                trade, resume_t, reversal = resolve(entry_bar, direction)
                trades.append(trade)
                if reversal is None:
                    # Resume at the first signal bar at/after this exit — no
                    # wall-clock overlap, mid-hold edges skipped. max(t+1, …)
                    # guarantees progress.
                    t = max(t + 1, resume_t)
                    break
                entry_bar, direction = reversal      # keep flipping while opposite exits

        ts_dtype = self.base_1s["timestamp"].dtype
        return pl.DataFrame(
            trades,
            schema={
                "entry_time": ts_dtype,
                "exit_time": ts_dtype,
                **self._TRADE_SCHEMA_TAIL,
            },
        ).select(*self._TRADE_COLUMNS)

    def evaluate(
        self,
        trades: pl.DataFrame,
        *,
        starting_balance: float = 10_000.0,
        pip_value: float = 1.0,
        seed: int | None = None,
        **kw,
    ) -> dict:
        """Full performance report for a `backtest` trade log (spec §2.1 / §3).

        Thin orchestration over `lib.evaluate` — `evaluate` (§3.1) plus the four
        §3.2 checks (`adversarial`, `bootstrap_ci`, `mc_drawdown`). `seed` is
        passed to the resampling ones for reproducibility; extra kwargs
        (`exclude_best_pct`, `min_trades`, `n_resamples`, `n_shuffles`,
        `confidence`) are routed to whichever function accepts them.

        Returns::

            {"summary", "equity_curve", "monthly",   # from evaluate()
             "adversarial": {"gross_vs_net", "ex_best_month", "ex_best_trades",
                             "sample_size", "bootstrap_ci", "mc_drawdown"},
             "verdict": str}                          # sample-size-gated
        """
        from lib import evaluate as ev

        money = dict(starting_balance=starting_balance, pip_value=pip_value)
        adv = ev.adversarial(
            trades, **money,
            **{k: kw[k] for k in ("exclude_best_pct", "min_trades") if k in kw},
        )
        adv["bootstrap_ci"] = ev.bootstrap_ci(
            trades, seed=seed,
            **{k: kw[k] for k in ("n_resamples", "confidence") if k in kw},
        )
        adv["mc_drawdown"] = ev.mc_drawdown(
            trades, seed=seed, **money,
            **{k: kw[k] for k in ("n_shuffles",) if k in kw},
        )
        verdict = adv.pop("verdict")

        return {**ev.evaluate(trades, **money), "adversarial": adv, "verdict": verdict}