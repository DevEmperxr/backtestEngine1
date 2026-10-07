"""Generic prop-firm rule simulator (lib/prop_firms.py)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from lib.prop_firms import FirmRules, run_phase, simulate_firm
from lib.tests.test_prop import _trades_from_days


class _Seq:
    """Deterministic stand-in for the rng: returns 0, 1, 2, ... (capped at the last day)."""

    def __init__(self, n_days: int) -> None:
        self.i, self.n = -1, n_days

    def integers(self, n):
        self.i += 1
        return min(self.i, self.n - 1)


def test_static_firm_reproduces_simple_payouts():
    start = date(2024, 1, 1)
    tr = _trades_from_days([[1.0]] * 40, start)
    f = FirmRules("t", targets=(10.0, 5.0), daily_loss=5.0, max_loss=10.0, min_days=4, fee=89.0)
    s = simulate_firm(tr, start, start + timedelta(days=55), f, risk_challenge=1.0, risk_funded=0.5,
                      funded_days=20, payout_every=10, n_sims=20)
    assert s["pass_%"] == 100.0
    assert s["expected_gross"] == pytest.approx(800.0 + 89.0)      # two payouts of $400 + refund


def test_trailing_floor_follows_the_peak():
    # +1R for 3 days then -1R days at 4% risk, 10% trailing: peak +12% -> floor +2%; the next trade that could
    # breach the floor is skipped, so the phase never fails but stalls -> timeout
    days = [[1.0]] * 3 + [[-1.0]] * 10
    f = FirmRules("t", targets=(50.0,), daily_loss=5.0, max_loss=10.0, trailing_eod=True)
    res, n, bal = run_phase(days, _Seq(len(days)), f, 50.0, 4.0, None, 13)
    assert res == "timeout" and bal == pytest.approx(4.0)        # 12 - 4 - 4 = 4; another -4 would hit +2 floor


def test_static_floor_allows_the_same_path_to_continue_further():
    days = [[1.0]] * 3 + [[-1.0]] * 10
    f = FirmRules("t", targets=(50.0,), daily_loss=5.0, max_loss=10.0)
    res, n, bal = run_phase(days, _Seq(len(days)), f, 50.0, 4.0, None, 13)
    assert res == "timeout" and bal == pytest.approx(-8.0)       # 12 - 5 x 4 = -8; next -4 would hit -10


def test_best_day_rule_blocks_a_single_big_day():
    days = [[10.0]] + [[0.0]] * 5
    f = FirmRules("t", targets=(10.0,), daily_loss=50.0, max_loss=50.0, best_day_frac=0.5)
    res, n, _ = run_phase(days, _Seq(len(days)), f, 10.0, 1.0, None, 6)
    assert res == "timeout"
    f2 = FirmRules("t", targets=(10.0,), daily_loss=50.0, max_loss=50.0)
    assert run_phase(days, _Seq(len(days)), f2, 10.0, 1.0, None, 6)[0] == "pass"


def test_min_profitable_days():
    days = [[2.0]] * 5
    f = FirmRules("t", targets=(4.0,), daily_loss=5.0, max_loss=10.0, min_profitable_days=3, profitable_day_pct=0.5)
    res, n, _ = run_phase(days, _Seq(len(days)), f, 4.0, 1.0, None, 5)
    assert res == "pass" and n == 3                              # +2% a day: target on day 2, 3 profitable days on day 3
