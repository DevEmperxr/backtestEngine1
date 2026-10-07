"""086 — DELIBERATE OVERFIT (user-approved one-off learning exercise): the best-fitted GER40 setup on Jan–Jun 2023,
searched over the user's setup template (Context / Bias / POI + window / Confirmation / Execution). NOT a candidate.

`features(df)` and `signals(feat, cfg)` are shared by the fast search (research/regime/setup_search_086.py) and by
the engine strategy below, so the engine replays exactly the rules the search picked. Frankfurt time, mid prices for
levels/signals; fills, stops and targets on bid/ask by the engine. FTMO rules: EUR red news ±2 min, flat 17:25
Frankfurt (well before 16:55 New York), one trade per day, no VWAP.
"""

from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path

import polars as pl

from lib.engine import Strategy
from research.regime.news import apply_news_blackout

ROOT = Path(__file__).resolve().parents[2]
FRA = "Europe/Berlin"
EXIT_MIN = 17 * 60 + 25                     # close-time minute of the exit bar
_htf = import_module("research.strategies.022_sweep_fade_to_ma")._htf

CONTEXTS = ["none", "prev_narrow", "prev_wide", "gap_big", "gap_small", "vol_rising", "vol_falling"]
BIASES = ["both", "with_trend", "against_trend", "with_gap", "against_gap", "with_prevday", "against_prevday"]
POIS = ["prev_day", "pre_open", "first_hour", "pivot_r1s1", "boll_5m", "round_100"]
WINDOWS = {"09-10": (540, 600), "10-12": (600, 720), "12-14:30": (720, 870), "14:30-17": (870, 1020)}
CONFIRMS = ["reject", "pin_reject", "break", "retest"]
STOPS = [0.1, 0.2, 0.35]                    # x daily ATR14 (cash-session range)
TARGETS = [1.0, 2.0, 3.0, None]             # R multiples; None = hold to 17:25


def features(df: pl.DataFrame) -> pl.DataFrame:
    mid = lambda f: (pl.col(f"bid_{f}") + pl.col(f"ask_{f}")) / 2
    ct = pl.col("close_time").dt.convert_time_zone(FRA)
    st = pl.col("timestamp").dt.convert_time_zone(FRA)
    f = df.with_columns(mo=mid("open"), mh=mid("high"), ml=mid("low"), mc=mid("close"), day=ct.dt.date(),
                        cmod=ct.dt.hour().cast(pl.Int32) * 60 + ct.dt.minute().cast(pl.Int32),
                        smod=st.dt.hour().cast(pl.Int32) * 60 + st.dt.minute().cast(pl.Int32), wd=ct.dt.weekday())
    cash = f.filter((pl.col("smod") >= 540) & (pl.col("smod") < 1050))
    d = (cash.group_by("day").agg(dO=pl.col("mo").first(), dH=pl.col("mh").max(), dL=pl.col("ml").min(),
                                  dC=pl.col("mc").last(), n=pl.len()).filter(pl.col("n") >= 300).sort("day")
         .with_columns(rng=pl.col("dH") - pl.col("dL")))
    d = d.with_columns(
        pH=pl.col("dH").shift(1), pL=pl.col("dL").shift(1), pC=pl.col("dC").shift(1), pO=pl.col("dO").shift(1),
        prng=pl.col("rng").shift(1),
        atr=pl.col("rng").rolling_mean(14, min_samples=5).shift(1),
        atr5=pl.col("rng").rolling_mean(5, min_samples=5).shift(1),
        atr20=pl.col("rng").rolling_mean(20, min_samples=10).shift(1),
        sma10=pl.col("dC").rolling_mean(10, min_samples=5).shift(1),
    ).with_columns(gap=pl.col("dO") - pl.col("pC"))
    d = d.with_columns(piv=(pl.col("pH") + pl.col("pL") + pl.col("pC")) / 3).with_columns(
        r1=2 * pl.col("piv") - pl.col("pL"), s1=2 * pl.col("piv") - pl.col("pH"))
    pre = (f.filter((pl.col("smod") >= 135) & (pl.col("smod") < 540)).group_by("day")
           .agg(preH=pl.col("mh").max(), preL=pl.col("ml").min()))
    fh = (f.filter((pl.col("smod") >= 540) & (pl.col("smod") < 600)).group_by("day")
          .agg(fhH=pl.col("mh").max(), fhL=pl.col("ml").min(), fhn=pl.len()))
    f = (f.join(d.drop("n", "rng"), on="day", how="left").join(pre, on="day", how="left")
         .join(fh, on="day", how="left"))
    b5 = (_htf(f.select("timestamp", "mo", "mh", "ml", "mc"), 5)
          .with_columns(bm=pl.col("mc").rolling_mean(20), bs=pl.col("mc").rolling_std(20)).select("ct", "bm", "bs"))
    f = f.join_asof(b5, left_on="close_time", right_on="ct", strategy="backward").drop("ct")
    pc = pl.col("mc").shift(1)
    return f.with_columns(
        bU=pl.col("bm") + 2 * pl.col("bs"), bL=pl.col("bm") - 2 * pl.col("bs"),
        rU=(pc / 100).ceil() * 100, rL=(pc / 100).floor() * 100,
        fhU=pl.when((pl.col("cmod") > 600) & (pl.col("fhn") >= 50)).then(pl.col("fhH")),
        fhLo=pl.when((pl.col("cmod") > 600) & (pl.col("fhn") >= 50)).then(pl.col("fhL")),
        pmc=pc,
    )


LEVELS = {"prev_day": ("pH", "pL"), "pre_open": ("preH", "preL"), "first_hour": ("fhU", "fhLo"),
          "pivot_r1s1": ("r1", "s1"), "boll_5m": ("bU", "bL"), "round_100": ("rU", "rL")}


def raw_signals(f: pl.DataFrame, poi: str, window: str, confirm: str) -> tuple[pl.Expr, pl.Expr]:
    """Long / short expressions for one POI + window + confirmation (before context / bias / one-per-day)."""
    U, L = (pl.col(c) for c in LEVELS[poi])
    a, b = WINDOWS[window]
    inwin = (pl.col("cmod") > a) & (pl.col("cmod") <= b) & (pl.col("wd") <= 5) & pl.col("atr").is_not_null()
    mh, ml, mc, pmc = pl.col("mh"), pl.col("ml"), pl.col("mc"), pl.col("pmc")
    pos = (mc - ml) / (mh - ml)
    if confirm in ("reject", "pin_reject"):
        s = (mh > U) & (mc < U)
        l_ = (ml < L) & (mc > L)
        if confirm == "pin_reject":
            s, l_ = s & (pos <= 0.3), l_ & (pos >= 0.7)
    elif confirm == "break":
        l_ = (mc > U) & (pmc <= U)
        s = (mc < L) & (pmc >= L)
    else:   # retest: earlier close beyond the level today, now touches it and closes beyond again
        above = (mc > U).cast(pl.Int32).cum_sum().over("day").shift(1).fill_null(0) > 0
        below = (mc < L).cast(pl.Int32).cum_sum().over("day").shift(1).fill_null(0) > 0
        l_ = above & (ml <= U) & (mc > U)
        s = below & (mh >= L) & (mc < L)
    return (inwin & l_).fill_null(False), (inwin & s).fill_null(False)


def context_mask(c: str) -> pl.Expr:
    return {"none": pl.lit(True), "prev_narrow": pl.col("prng") < 0.8 * pl.col("atr"),
            "prev_wide": pl.col("prng") > 1.2 * pl.col("atr"),
            "gap_big": pl.col("gap").abs() > 0.3 * pl.col("atr"), "gap_small": pl.col("gap").abs() <= 0.3 * pl.col("atr"),
            "vol_rising": pl.col("atr5") > pl.col("atr20"), "vol_falling": pl.col("atr5") <= pl.col("atr20")}[c].fill_null(False)


def bias_masks(bname: str) -> tuple[pl.Expr, pl.Expr]:
    """(long allowed, short allowed)."""
    up = {"with_trend": pl.col("pC") > pl.col("sma10"), "against_trend": pl.col("pC") < pl.col("sma10"),
          "with_gap": pl.col("gap") > 0, "against_gap": pl.col("gap") < 0,
          "with_prevday": pl.col("pC") > pl.col("pO"), "against_prevday": pl.col("pC") < pl.col("pO")}
    if bname == "both":
        return pl.lit(True), pl.lit(True)
    return up[bname].fill_null(False), (~up[bname]).fill_null(False)


def signals(f: pl.DataFrame, cfg: dict) -> pl.DataFrame:
    lg, sh = raw_signals(f, cfg["poi"], cfg["window"], cfg["confirm"])
    cm = context_mask(cfg["context"])
    la, sa = bias_masks(cfg["bias"])
    out = f.with_columns(long_signal=lg & cm & la, short_signal=sh & cm & sa)
    out = out.with_columns(long_signal=pl.col("long_signal") & ~pl.col("short_signal"),
                           short_signal=pl.col("short_signal") & ~pl.col("long_signal"))
    return out


class OverfitSetup(Strategy):
    exit_on_opposite_signal = False
    reverse_on_opposite_signal = False
    pip_aware = True
    marker_columns = ["long_signal", "short_signal"]
    region_columns = ["in_window"]

    def __init__(self, cfg: dict | None = None, *, currencies: tuple[str, ...] = ("EUR",)) -> None:
        super().__init__(100.0, 1000.0, "1m")
        if cfg is None:
            cfg = json.loads((ROOT / "research" / "runs" / "086_overfit_setup" / "winner.json").read_text())["config"]
        self.cfg, self.currencies = cfg, tuple(currencies)

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        out = apply_news_blackout(signals(features(df), self.cfg), list(self.currencies))
        sig = pl.col("long_signal") | pl.col("short_signal")
        first = sig.cast(pl.Int32).cum_sum().over("day") == 1
        out = out.with_columns(long_signal=pl.col("long_signal") & first, short_signal=pl.col("short_signal") & first)
        sig = pl.col("long_signal") | pl.col("short_signal")
        stop = self.cfg["stop"] * pl.col("atr")
        tgt = stop * self.cfg["target"] if self.cfg["target"] is not None else pl.lit(5000.0)
        a, _ = WINDOWS[self.cfg["window"]]
        return out.with_columns(
            sl_pips=pl.when(sig).then(stop), tp_pips=pl.when(sig).then(tgt),
            in_window=((pl.col("cmod") > a) & (pl.col("cmod") < EXIT_MIN) & (pl.col("wd") <= 5)).fill_null(False),
        ).with_columns(exit_signal=(pl.col("exit_signal") | ~pl.col("in_window")) & ~sig)


def make():
    return OverfitSetup()
