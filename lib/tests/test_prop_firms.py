"""Generic prop-firm rule simulator (lib/prop_firms.py)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from lib.prop import daily_R
from lib.prop_firms import FirmRules, run_phase, simulate_firm
from lib.tests.test_prop import _trades_from_days


class _Seq:
    """Deterministic stand-in for the rng: returns 0, 1, 2, ... (capped at the last day)."""

    def __init__(self, n_days: int) -> None:
        self.i, self.n = -1, n_days

    def integers(self, n):
        self.i += 1
        return min(self.i, self.n - 1)


def test_static_firm_payouts_and_timing():
    start = date(2024, 1, 1)
    days = daily_R(_trades_from_days([[1.0]] * 40, start), start, start + timedelta(days=55))
    f = FirmRules("t", targets=(10.0, 5.0), daily_loss=5.0, max_loss=10.0, min_days=4, fee=89.0)
    s = simulate_firm(days, f, risk_challenge=1.0, risk_funded=0.5, funded_days=20, payout_every=10, n_sims=20)
    assert s["pass_%"] == 100.0
    assert s["expected_gross"] == pytest.approx(800.0 + 89.0)      # two payouts of $400 + refund
    assert s["trades_to_pass"] == 15 and s["days_to_pass"] == 15   # 10 + 5 winning trades
    assert s["days_to_first_payout"] == 25                         # 15 + 10 funded days
    assert s["trades_to_profit"] == 25                             # first payout already exceeds the fee


def test_trailing_floor_follows_the_peak():
    days = [[1.0]] * 3 + [[-1.0]] * 10
    f = FirmRules("t", targets=(50.0,), daily_loss=5.0, max_loss=10.0, trailing_eod=True)
    res, n, bal, nt = run_phase(days, _Seq(len(days)), f, 50.0, 4.0, None, 13)
    assert res == "timeout" and bal == pytest.approx(4.0)        # 12 - 4 - 4 = 4; another -4 would hit the +2 floor


def test_static_floor_allows_the_same_path_to_continue_further():
    days = [[1.0]] * 3 + [[-1.0]] * 10
    f = FirmRules("t", targets=(50.0,), daily_loss=5.0, max_loss=10.0)
    res, n, bal, nt = run_phase(days, _Seq(len(days)), f, 50.0, 4.0, None, 13)
    assert res == "timeout" and bal == pytest.approx(-8.0)


def test_best_day_rule_blocks_a_single_big_day():
    days = [[10.0]] + [[0.0]] * 5
    f = FirmRules("t", targets=(10.0,), daily_loss=50.0, max_loss=50.0, best_day_frac=0.5)
    assert run_phase(days, _Seq(len(days)), f, 10.0, 1.0, None, 6)[0] == "timeout"
    f2 = FirmRules("t", targets=(10.0,), daily_loss=50.0, max_loss=50.0)
    assert run_phase(days, _Seq(len(days)), f2, 10.0, 1.0, None, 6)[0] == "pass"


def test_min_profitable_days():
    days = [[2.0]] * 5
    f = FirmRules("t", targets=(4.0,), daily_loss=5.0, max_loss=10.0, min_profitable_days=3, profitable_day_pct=0.5)
    res, n, _, _ = run_phase(days, _Seq(len(days)), f, 4.0, 1.0, None, 5)
    assert res == "pass" and n == 3


def test_ftmo_1step_scorecard_runs_and_compares_with_twin():
    from lib.prop_firms import ftmo_1step_scorecard
    start = date(2024, 1, 1)
    tr = _trades_from_days([[0.5]] * 30 + [[-0.3]] * 30, start)     # positive average R
    sc = ftmo_1step_scorecard(tr, start, start + timedelta(days=90), n_sims=50)
    assert sc["avg_R_per_trade"] == pytest.approx(0.1)
    assert sc["strategy"]["EV_net"] > sc["zero_edge_twin"]["EV_net"] and sc["beats_twin"]
