"""Run 043 — descriptive look at the NY-window trades of run 042 (Idea 1, 08-10 NY, 1h trending),
EURUSD 2023+2024. Splits only; no rule changes. A split counts as a lead only if it points the same
way in BOTH years. Small sample (157 trades): treat everything as hypotheses.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from research.regime.news import red_news_dates

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "research" / "runs" / "042_idea1_two_windows"


def table(t: pl.DataFrame, col: str) -> None:
    g = (t.group_by(col, pl.col("entry_time").dt.year().alias("y"))
         .agg(n=pl.len(), pips=pl.col("pips").sum().round(1), win=(pl.col("pips") > 0).mean().mul(100).round(0))
         .pivot(on="y", index=col, values=["n", "pips", "win"]).sort(col))
    tot = t.group_by(col).agg(n_all=pl.len(), pips_all=pl.col("pips").sum().round(1), per_trade=pl.col("pips").mean().round(2))
    print(f"\n== by {col}")
    print(g.join(tot, on=col).sort(col))


def main() -> None:
    allt = pl.read_parquet(RUN / "trades_tagged_2023_2024.parquet").sort("entry_time")
    ny_time = pl.col("entry_time").dt.convert_time_zone("America/New_York")
    allt = allt.with_columns(day=ny_time.dt.date())
    # nth trade of the day on the account (any window), and nth within the NY window
    allt = allt.with_columns(nth_day=pl.col("entry_time").rank("ordinal").over("day").cast(pl.Int32))
    t = allt.filter(pl.col("window_tag") == "ny_trend").with_columns(
        nth_ny=pl.col("entry_time").rank("ordinal").over("day").cast(pl.Int32))
    red = red_news_dates(["USD", "EUR"])
    t = t.with_columns(
        half_hour=pl.format("{}:{}", ny_time.dt.hour().cast(pl.Utf8).str.zfill(2),
                            pl.when(ny_time.dt.minute() < 30).then(pl.lit("00")).otherwise(pl.lit("30"))),
        red_news_day=pl.col("day").is_in(sorted(red)),
        london_trade_before=pl.col("nth_day") > pl.col("nth_ny"),
        nth_ny_cap=pl.col("nth_ny").clip(upper_bound=3),
        stop_size=pl.when(pl.col("sl_pips") < 5).then(pl.lit("a <5")).when(pl.col("sl_pips") < 8).then(pl.lit("b 5-8")).otherwise(pl.lit("c 8+")),
        target_vs_stop=pl.when(pl.col("tp_pips") / pl.col("sl_pips") < 1.2).then(pl.lit("a <1.2R"))
                         .when(pl.col("tp_pips") / pl.col("sl_pips") < 2).then(pl.lit("b 1.2-2R")).otherwise(pl.lit("c 2R+")),
        weekday=ny_time.dt.weekday(),
    )
    with pl.Config(tbl_rows=30, tbl_cols=20, tbl_width_chars=200, tbl_formatting="ASCII_MARKDOWN", tbl_hide_column_data_types=True, tbl_hide_dataframe_shape=True):
        for c in ("half_hour", "direction", "red_news_day", "nth_ny_cap", "london_trade_before",
                  "stop_size", "target_vs_stop", "weekday", "exit_reason"):
            table(t, c)
    t.write_parquet(ROOT / "research" / "runs" / "043_ny_window_diagnostics" / "ny_trades_tagged.parquet")


if __name__ == "__main__":
    (ROOT / "research" / "runs" / "043_ny_window_diagnostics").mkdir(parents=True, exist_ok=True)
    main()
