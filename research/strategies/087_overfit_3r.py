"""087 — DELIBERATE OVERFIT #2 (user request): the GER40 setup with the MOST 3R winners on Jan–Jun 2023, one trade a
day, built strictly from the user's setup elements:

1 Context — where are we: up / down / range (reader = method x timeframe: SMA20+slope, efficiency ratio, swing
  structure HH/HL; daily, 1h, 15m; last closed bar only)
2 Bias — do we expect up or down: with the context, against it, range mean-reversion, range breakout
3 POI — level + time: previous-day H/L, pre-open range, first-hour range, round 100s, 5m Bollinger(20,2), last 1h
  swing H/L, day open, previous close; as a pullback level (support for longs) or a breakout level; in a time window
4 Confirmation — within 15 minutes of the POI touch: none, rejection, engulfing, micro break of structure, 3 closes
  holding beyond the level, RSI(14) turn
Execution: target 3R; stop beyond the swing since the touch, or 0.1 / 0.2 x daily ATR; exit 17:25 Frankfurt; EUR red
news ±2 min; FTMO costs. NOT a candidate. `features` / `signal_sets` are shared by the search and the engine.
"""

from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path

import numpy as np
import polars as pl

from lib.engine import Strategy
from research.regime.news import apply_news_blackout

ROOT = Path(__file__).resolve().parents[2]
FRA = "Europe/Berlin"
EXIT_MIN = 17 * 60 + 25
ARM = 15
_htf = import_module("research.strategies.022_sweep_fade_to_ma")._htf

TFS = ["D", "60", "15"]
METHODS = ["sma", "er", "struct"]
READERS = [f"{m}_{tf}" for tf in TFS for m in METHODS]
BIASES = ["with", "against", "range_meanrev", "range_breakout"]
LEVELS = {"prev_day": ("pH", "pL"), "pre_open": ("preH", "preL"), "first_hour": ("fhU", "fhLo"),
          "round_100": ("rU", "rL"), "boll_5m": ("bU", "bL"), "swing_1h": ("swH_60", "swL_60"),
          "day_open": ("dOx", "dOx"), "prev_close": ("pC", "pC")}
SIDES = ["pullback", "breakout"]
WINDOWS = {"09-10": (540, 600), "10-12": (600, 720), "12-14:30": (720, 870), "14:30-17": (870, 1020), "09-17": (540, 1020)}
CONFIRMS = ["none", "reject", "engulf", "bos", "hold3", "rsi"]
STOPS = ["swing", "atr0.1", "atr0.2"]
TARGET_R = 3.0


def _states(h: pl.DataFrame, tag: str) -> pl.DataFrame:
    """Context states (+1 up / -1 down / 0 range) of OHLC bars h (mo/mh/ml/mc), all known at each bar's close."""
    sma = pl.col("mc").rolling_mean(20)
    slope = sma - sma.shift(5)
    er = (pl.col("mc") - pl.col("mc").shift(20)).abs() / pl.col("mc").diff().abs().rolling_sum(20)
    chg = pl.col("mc") - pl.col("mc").shift(20)
    h = h.with_columns(
        **{f"sma_{tag}": pl.when((pl.col("mc") > sma) & (slope > 0)).then(1).when((pl.col("mc") < sma) & (slope < 0)).then(-1)
           .when(slope.is_not_null()).then(0),
           f"er_{tag}": pl.when((er >= 0.3) & (chg > 0)).then(1).when((er >= 0.3) & (chg < 0)).then(-1)
           .when(er.is_not_null()).then(0),
           f"mid_{tag}": (pl.col("mh").rolling_max(20) + pl.col("ml").rolling_min(20)) / 2})
    H, L = h["mh"].to_numpy(), h["ml"].to_numpy()
    n, k = len(H), 2
    st = np.full(n, np.nan)
    swh, swl = np.full(n, np.nan), np.full(n, np.nan)
    ph, pl_ = [], []
    for i in range(n):
        j = i - k                                   # pivot at j confirmed at the close of bar i
        if j - k >= 0:
            if H[j] == H[j - k:j + k + 1].max():
                ph.append(H[j])
            if L[j] == L[j - k:j + k + 1].min():
                pl_.append(L[j])
        if ph:
            swh[i] = ph[-1]
        if pl_:
            swl[i] = pl_[-1]
        if len(ph) >= 2 and len(pl_) >= 2:
            up, dn = ph[-1] > ph[-2] and pl_[-1] > pl_[-2], ph[-1] < ph[-2] and pl_[-1] < pl_[-2]
            st[i] = 1 if up else (-1 if dn else 0)
    return h.with_columns(pl.Series(f"struct_{tag}", st), pl.Series(f"swH_{tag}", swh), pl.Series(f"swL_{tag}", swl))


def features(df: pl.DataFrame) -> pl.DataFrame:
    mid = lambda f: (pl.col(f"bid_{f}") + pl.col(f"ask_{f}")) / 2
    ct = pl.col("close_time").dt.convert_time_zone(FRA)
    st = pl.col("timestamp").dt.convert_time_zone(FRA)
    f = df.with_columns(mo=mid("open"), mh=mid("high"), ml=mid("low"), mc=mid("close"), day=ct.dt.date(),
                        cmod=ct.dt.hour().cast(pl.Int32) * 60 + ct.dt.minute().cast(pl.Int32),
                        smod=st.dt.hour().cast(pl.Int32) * 60 + st.dt.minute().cast(pl.Int32), wd=ct.dt.weekday())
    base = f.select("timestamp", "mo", "mh", "ml", "mc")
    # daily (cash session 09:00-17:30), states known from the previous day
    cash = f.filter((pl.col("smod") >= 540) & (pl.col("smod") < 1050))
    d = (cash.group_by("day").agg(mo=pl.col("mo").first(), mh=pl.col("mh").max(), ml=pl.col("ml").min(),
                                  mc=pl.col("mc").last(), n=pl.len()).filter(pl.col("n") >= 300).sort("day"))
    d = _states(d, "D").with_columns(atr=(pl.col("mh") - pl.col("ml")).rolling_mean(14, min_samples=5))
    dcols = ["sma_D", "er_D", "struct_D", "mid_D", "atr"]
    d = d.with_columns([pl.col(c).shift(1) for c in dcols]).with_columns(
        pH=pl.col("mh").shift(1), pL=pl.col("ml").shift(1), pC=pl.col("mc").shift(1), dO=pl.col("mo"))
    f = f.join(d.select("day", "pH", "pL", "pC", "dO", *dcols), on="day", how="left")
    for tf in ("60", "15"):
        h = _states(_htf(base, int(tf)), tf)
        keep = ["ct", f"sma_{tf}", f"er_{tf}", f"struct_{tf}", f"mid_{tf}"] + ([f"swH_{tf}", f"swL_{tf}"] if tf == "60" else [])
        f = f.join_asof(h.select(keep).sort("ct"), left_on="close_time", right_on="ct", strategy="backward").drop("ct")
    pre = (f.filter((pl.col("smod") >= 135) & (pl.col("smod") < 540)).group_by("day")
           .agg(preH=pl.col("mh").max(), preL=pl.col("ml").min()))
    fh = (f.filter((pl.col("smod") >= 540) & (pl.col("smod") < 600)).group_by("day")
          .agg(fhH=pl.col("mh").max(), fhL=pl.col("ml").min(), fhn=pl.len()))
    f = f.join(pre, on="day", how="left").join(fh, on="day", how="left")
    b5 = (_htf(base, 5).with_columns(bm=pl.col("mc").rolling_mean(20), bs=pl.col("mc").rolling_std(20)).select("ct", "bm", "bs"))
    f = f.join_asof(b5, left_on="close_time", right_on="ct", strategy="backward").drop("ct")
    dlt = pl.col("mc").diff()
    up = dlt.clip(lower_bound=0).ewm_mean(alpha=1 / 14, adjust=False)
    dn = (-dlt).clip(lower_bound=0).ewm_mean(alpha=1 / 14, adjust=False)
    pc = pl.col("mc").shift(1)
    return f.with_columns(
        bU=pl.col("bm") + 2 * pl.col("bs"), bL=pl.col("bm") - 2 * pl.col("bs"),
        rU=(pc / 100).ceil() * 100, rL=(pc / 100).floor() * 100,
        fhU=pl.when((pl.col("cmod") > 600) & (pl.col("fhn") >= 50)).then(pl.col("fhH")),
        fhLo=pl.when((pl.col("cmod") > 600) & (pl.col("fhn") >= 50)).then(pl.col("fhL")),
        dOx=pl.when(pl.col("cmod") > 540).then(pl.col("dO")),
        pmc=pc, pmo=pl.col("mo").shift(1), rsi=100 - 100 / (1 + up / dn),
        lo15=pl.col("ml").rolling_min(ARM), hi15=pl.col("mh").rolling_max(ARM),
        hh5=pl.col("mh").shift(1).rolling_max(5), ll5=pl.col("ml").shift(1).rolling_min(5),
    )


def raw_signals(f: pl.DataFrame, level: str, side: str, window: str, confirm: str) -> tuple[pl.Expr, pl.Expr]:
    U, L = (pl.col(c) for c in LEVELS[level])
    a, b = WINDOWS[window]
    inwin = (pl.col("cmod") > a) & (pl.col("cmod") <= b) & (pl.col("wd") <= 5) & pl.col("atr").is_not_null()
    mo, mh, ml, mc, pmc, pmo = (pl.col(c) for c in ("mo", "mh", "ml", "mc", "pmc", "pmo"))
    if side == "pullback":            # long at support L, short at resistance U
        lv_l, lv_s = L, U
        t_l, t_s = ml <= L, mh >= U
    else:                             # breakout: long through U, short through L
        lv_l, lv_s = U, L
        t_l, t_s = (mh > U) & (pmc <= U), (ml < L) & (pmc >= L)
    t_l, t_s = (t_l & inwin).fill_null(False), (t_s & inwin).fill_null(False)
    arm_l = t_l.cast(pl.Int8).rolling_max(ARM).fill_null(0) == 1
    arm_s = t_s.cast(pl.Int8).rolling_max(ARM).fill_null(0) == 1
    if confirm == "none":
        c_l, c_s = t_l, t_s
    elif confirm == "reject":
        c_l, c_s = (ml <= lv_l) & (mc > lv_l), (mh >= lv_s) & (mc < lv_s)
    elif confirm == "engulf":
        c_l = (mc > mo) & (pmo > pmc) & (mc >= pmo) & (mo <= pmc)
        c_s = (mc < mo) & (pmo < pmc) & (mc <= pmo) & (mo >= pmc)
    elif confirm == "bos":
        c_l, c_s = mc > pl.col("hh5"), mc < pl.col("ll5")
    elif confirm == "hold3":
        c_l = (mc > lv_l) & (pmc > lv_l) & (mc.shift(2) > lv_l) & ~(mc.shift(3) > lv_l)
        c_s = (mc < lv_s) & (pmc < lv_s) & (mc.shift(2) < lv_s) & ~(mc.shift(3) < lv_s)
    else:
        r = pl.col("rsi")
        c_l, c_s = (r >= 30) & (r.shift(1) < 30), (r <= 70) & (r.shift(1) > 70)
    lg = (arm_l & c_l & inwin).fill_null(False)
    sh = (arm_s & c_s & inwin).fill_null(False)
    return lg & ~sh, sh & ~lg


def bias_ok(reader: str, bias: str) -> tuple[pl.Expr, pl.Expr]:
    """(long allowed, short allowed) from the context reader's state and the bias rule."""
    s = pl.col(reader)
    tf = reader.split("_")[1]
    mid = pl.col(f"mid_{tf}")
    if bias == "with":
        out = (s == 1, s == -1)
    elif bias == "against":
        out = (s == -1, s == 1)
    elif bias == "range_meanrev":
        out = ((s == 0) & (pl.col("mc") < mid), (s == 0) & (pl.col("mc") > mid))
    else:
        out = ((s == 0) & (pl.col("mc") > mid), (s == 0) & (pl.col("mc") < mid))
    return out[0].fill_null(False), out[1].fill_null(False)


def stop_expr(stop: str) -> tuple[pl.Expr, pl.Expr]:
    """Stop distance in points for (long, short) at the signal bar close."""
    if stop == "swing":
        buf = pl.max_horizontal(0.02 * pl.col("atr"), pl.lit(2.0))
        sl_l = pl.max_horizontal(pl.col("mc") - pl.col("lo15") + buf, pl.lit(5.0))
        sl_s = pl.max_horizontal(pl.col("hi15") - pl.col("mc") + buf, pl.lit(5.0))
        return sl_l, sl_s
    k = float(stop.replace("atr", ""))
    return k * pl.col("atr"), k * pl.col("atr")


class Overfit3R(Strategy):
    exit_on_opposite_signal = False
    reverse_on_opposite_signal = False
    pip_aware = True
    marker_columns = ["long_signal", "short_signal"]
    region_columns = ["in_window"]

    def __init__(self, cfg: dict | None = None, *, currencies: tuple[str, ...] = ("EUR",)) -> None:
        super().__init__(100.0, 1000.0, "1m")
        if cfg is None:
            cfg = json.loads((ROOT / "research" / "runs" / "087_overfit_3r" / "winner.json").read_text())["config"]
        self.cfg, self.currencies = cfg, tuple(currencies)

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        c = self.cfg
        f = features(df)
        lg, sh = raw_signals(f, c["level"], c["side"], c["window"], c["confirm"])
        la, sa = bias_ok(c["reader"], c["bias"])
        out = apply_news_blackout(f.with_columns(long_signal=lg & la, short_signal=sh & sa), list(self.currencies))
        sig = pl.col("long_signal") | pl.col("short_signal")
        first = sig.cast(pl.Int32).cum_sum().over("day") == 1
        out = out.with_columns(long_signal=pl.col("long_signal") & first, short_signal=pl.col("short_signal") & first)
        sl_l, sl_s = stop_expr(c["stop"])
        a, _ = WINDOWS[c["window"]]
        return out.with_columns(
            sl_pips=pl.when(pl.col("long_signal")).then(sl_l).when(pl.col("short_signal")).then(sl_s),
        ).with_columns(
            tp_pips=TARGET_R * pl.col("sl_pips"),
            in_window=((pl.col("cmod") > a) & (pl.col("cmod") < EXIT_MIN) & (pl.col("wd") <= 5)).fill_null(False),
        ).with_columns(exit_signal=(pl.col("exit_signal") | ~pl.col("in_window"))
                       & ~(pl.col("long_signal") | pl.col("short_signal")))


def make():
    return Overfit3R()


def make_runner_up():
    w = json.loads((ROOT / "research" / "runs" / "087_overfit_3r" / "winner.json").read_text())
    return Overfit3R(w["runner_up"]["config"])
