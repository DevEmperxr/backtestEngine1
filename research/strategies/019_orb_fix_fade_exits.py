"""019 — 018's entry (fade the still-open 005 breakout at the 16:00 London fix)
with designed exits; flat at 16:00 New York in all cases.

    make_a(): time exit, disaster SL 3 x ATR(14, 1h), TP 10 x ATR (effectively none)
    make_b(): SL 1.5 x ATR, TP 1.5 x ATR
    make_c(): TP back to the broken range edge, SL 1.5 x ATR; no trade if already inside

See research/runs/019_orb_fix_fade_exits/summary.md.
"""

from importlib import import_module

OrbFixFadeStrategy = import_module("research.strategies.018_orb_fix_fade").OrbFixFadeStrategy


def make_a() -> OrbFixFadeStrategy:
    return OrbFixFadeStrategy(exit_mode="time", atr_tf="1h", atr_n=14)


def make_b() -> OrbFixFadeStrategy:
    return OrbFixFadeStrategy(exit_mode="atr", atr_tf="1h", atr_n=14, sl_atr=1.5, tp_atr=1.5)


def make_c() -> OrbFixFadeStrategy:
    return OrbFixFadeStrategy(exit_mode="range", atr_tf="1h", atr_n=14, sl_atr=1.5)


make = make_a
