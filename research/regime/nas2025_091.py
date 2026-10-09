"""Run 091 — frozen 079 noise-area rules on NAS100 2025 (out-of-sample). Pre-registered in
research/runs/091_nas100_2025/summary.md.

    .venv/Scripts/python.exe -m research.regime.nas2025_091
"""

from __future__ import annotations

import functools
import json
from datetime import date, datetime, timedelta, timezone
from importlib import import_module
from pathlib import Path
from zoneinfo import ZoneInfo

import polars as pl

from lib.data import load_1s_data, pip_size, resample
from lib.engine import Engine
from lib.prop import prop_config_for
from lib.prop_firms import ftmo_1step_scorecard
from research.regime.chart_images import equity_and_monthly_png
from research.regime.trend_dip_073 import stats

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "research" / "runs" / "091_nas100_2025"
TRADES = ROOT / "research" / "runs" / "089_noise_area_indices" / "nas100_2025_NAS100_2025" / "trades.parquet"
NY = ZoneInfo("America/New_York")


def add_R(t: pl.DataFrame) -> pl.DataFrame:
    return t.with_columns(R=pl.col("pips") / pl.col("sl_pips"))


def main() -> None:
    t = add_R(pl.read_parquet(TRADES)).sort("entry_time")
    res: dict = {"2025": stats(t)}
    res["H1"] = stats(t.filter(pl.col("entry_time").dt.month() <= 6))
    res["H2"] = stats(t.filter(pl.col("entry_time").dt.month() > 6))
    res["long"] = stats(t.filter(pl.col("direction") == "long"))
    res["short"] = stats(t.filter(pl.col("direction") == "short"))
    gross = pl.col("pips") + pl.col("spread_pips_paid") + pl.col("commission_pips")
    res["gross_R_per_trade"] = round(t.select((gross / pl.col("sl_pips")).mean()).item(), 3)
    twin = t.with_columns(tw=pl.when(pl.col("direction") == "long").then(pl.col("pips"))
                          .otherwise(-gross - pl.col("spread_pips_paid") - pl.col("commission_pips")) / pl.col("sl_pips"))
    res["always_long_twin_R_per_trade"] = round(twin["tw"].mean(), 3)
    res["edge_over_long_twin"] = round(res["2025"]["R_per_trade"] - res["always_long_twin_R_per_trade"], 3)
    res["exits"] = dict(t.group_by("exit_reason").len().iter_rows())
    res["months"] = {m: [p.height, round(p["R"].sum(), 1)] for m in range(1, 13)
                     for p in [t.filter(pl.col("entry_time").dt.month() == m)]}
    sc = ftmo_1step_scorecard(t, date(2025, 1, 1), date(2025, 12, 31), n_sims=1500, seed=4)
    res["ftmo"] = {"strategy": sc["strategy"], "twin": sc["zero_edge_twin"], "beats_twin": sc["beats_twin"]}
    res["PASS"] = bool(res["2025"]["R_per_trade"] >= 0.05 and sc["beats_twin"])

    # Sensitivity A: Jan 1 - Apr 7 2025 with vs without the ForexFactory Trump-speech events
    m089 = import_module("research.strategies.089_noise_area_indices")
    a = load_1s_data(str(ROOT / "data" / "NAS100_1s_2025.csv"), verbose=False)
    a = a.filter(pl.col("timestamp") < datetime(2025, 4, 8, tzinfo=timezone.utc))
    eng = Engine(resample(a, "1m"), a, pip=pip_size("NAS100"))
    orig = m089.apply_news_blackout
    m089.apply_news_blackout = functools.partial(orig, exclude=("President Trump Speaks",))
    try:
        no_trump = add_R(eng.backtest(m089.make_nas100_2025(), prop=prop_config_for("NAS100")))
    finally:
        m089.apply_news_blackout = orig
    q1 = t.filter(pl.col("entry_time") < datetime(2025, 4, 8, tzinfo=timezone.utc))
    res["sensitivity_A_trump_jan_apr7"] = {"with_trump_blocked": stats(q1), "trump_not_blocked": stats(no_trump)}

    # Sensitivity B: trades entering at the 10:00 check on CB (last Tuesday) / Michigan prelim (2nd Friday) days after 7 Apr
    def last_tuesday(y, m):
        d = (date(y, m + 1, 1) if m < 12 else date(y + 1, 1, 1)) - timedelta(days=1)
        return d - timedelta(days=(d.weekday() - 1) % 7)

    def second_friday(y, m):
        d = date(y, m, 1)
        return d + timedelta(days=(4 - d.weekday()) % 7 + 7)
    extra = {last_tuesday(2025, m) for m in range(4, 13)} | {second_friday(2025, m) for m in range(4, 13)}
    extra = {d for d in extra if d > date(2025, 4, 7)}
    e_ny = t["entry_time"].dt.convert_time_zone("America/New_York")
    hit = t.with_columns(d=e_ny.dt.date(), hm=e_ny.dt.strftime("%H:%M")).filter(pl.col("d").is_in(sorted(extra)) & (pl.col("hm") == "10:00"))
    res["sensitivity_B_extra_10am_events"] = {"trades_affected": hit.height, "their_R_total": round(hit["R"].sum(), 2),
                                              "R_per_trade_without_them": round(t.filter(~pl.col("entry_time").is_in(hit["entry_time"]))["R"].mean(), 3)}
    for k, v in res.items():
        if k not in ("ftmo",):
            print(k, v)
    print("FTMO strategy:", {k: sc["strategy"][k] for k in ("risk_challenge", "risk_funded", "pass_%", "EV_net", "days_to_pass", "trades_to_pass")})
    print("FTMO twin:    ", {k: sc["zero_edge_twin"][k] for k in ("pass_%", "EV_net")})
    RUN.mkdir(parents=True, exist_ok=True)
    equity_and_monthly_png(t.with_columns(pips=pl.col("R")), "091 NAS100 noise-area (079 rules, frozen) on 2025 — out-of-sample, R after FTMO costs",
                           RUN / "nas100_2025.png")
    (RUN / "results.json").write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
