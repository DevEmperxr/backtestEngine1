"""Red-news (ForexFactory "High Impact Expected") calendar days.

Source: Tropstan/Forex_Factory_Calendar on Hugging Face (MIT), scraped from ForexFactory,
2007-01-01 -> 2025-04-07, saved as data/forex_factory_calendar.csv. Timestamps carry a
+03:30 (Asia/Tehran) offset.

Data quirk (checked 2026-10-06): ForexFactory prints a time only on the first event of a
same-minute block. The scraper stored the rest as 00:00:00 (about half of 2023–2024's red
USD/EUR/GBP events, including NFP and CPI). Their **date** is still the calendar day the site
showed. So:
  * rows with a real time  -> convert to America/New_York and take that date;
  * rows at 00:00:00 or 23:59:59 (missing / all-day) -> take the file's own date as is.
Residual error: a late-evening New York event (e.g. a 19:00 NY speech = 03:30 Tehran next day)
can land one day late. These are rare.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl

CAL = Path(__file__).resolve().parents[2] / "data" / "forex_factory_calendar.csv"


def red_news_dates(currencies: list[str], path: Path = CAL) -> set[date]:
    """New York calendar dates with at least one High-impact event for any of `currencies`."""
    d = pl.read_csv(path, infer_schema_length=0).filter(
        (pl.col("Impact") == "High Impact Expected") & pl.col("Currency").is_in(currencies)
    )
    local_time = pl.col("DateTime").str.slice(11, 8)
    no_time = local_time.is_in(["00:00:00", "23:59:59"])
    ny_date = (pl.col("DateTime").str.to_datetime("%Y-%m-%dT%H:%M:%S%z")
               .dt.convert_time_zone("America/New_York").dt.date())
    file_date = pl.col("DateTime").str.slice(0, 10).str.to_date("%Y-%m-%d")
    out = d.select(day=pl.when(no_time).then(file_date).otherwise(ny_date))
    return set(out["day"].to_list())


def pair_currencies(pair: str) -> list[str]:
    pair = pair.upper()
    return [pair[:3], pair[3:]]
