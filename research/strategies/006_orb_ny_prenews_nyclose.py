"""006 — as 005 (07:00-08:30 NY opening range, first 1m close beyond it), but
the entry window and the force-flat end at 16:00 New York instead of 16:00
London.

See research/runs/006_orb_ny_prenews_nyclose/summary.md.
"""

from datetime import time
from importlib import import_module

_orb = import_module("research.strategies.005_orb_ny_prenews")
OrbStrategy = _orb.OrbStrategy


def make() -> OrbStrategy:
    return OrbStrategy(
        range_start=time(7, 0), range_end=time(8, 30), tp_range_mult=1.5,
        window_end=time(16, 0), window_end_tz=_orb.NY,
    )
