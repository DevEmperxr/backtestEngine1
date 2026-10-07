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

from datetime import date, datetime, timedelta
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


# Official release clock times (home-zone local) for red events that never carry a time in the file.
OFFICIAL_TIMES = {
    ("USD", "Non-Farm Employment Change"): "08:30", ("USD", "Unemployment Rate"): "08:30",
    ("USD", "Retail Sales m/m"): "08:30", ("USD", "Employment Cost Index q/q"): "08:30",
    ("EUR", "German Flash Services PMI"): "09:30", ("EUR", "German Prelim CPI m/m"): "14:00",
    # Bank of England decision day (12:00 London) and fixed-time UK releases
    ("GBP", "Official Bank Rate"): "12:00", ("GBP", "MPC Official Bank Rate Votes"): "12:00",
    ("GBP", "Monetary Policy Summary"): "12:00", ("GBP", "Flash Services PMI"): "09:30",
    ("GBP", "Claimant Count Change"): "07:00", ("GBP", "Retail Sales m/m"): "07:00",
    ("GBP", "GDP m/m"): "07:00", ("GBP", "CPI y/y"): "07:00",
    # fixed-time Australian releases (ABS 11:30 Sydney) and the RBA decision (14:30 Sydney); the RBA
    # Monetary Policy Statement moved in 2024, so it stays a whole-day block
    ("AUD", "Unemployment Rate"): "11:30", ("AUD", "CPI y/y"): "11:30", ("AUD", "Trimmed Mean CPI q/q"): "11:30",
    ("AUD", "Wage Price Index q/q"): "11:30", ("AUD", "RBA Rate Statement"): "14:30",
}
HOME_TZ = {"USD": "America/New_York", "EUR": "Europe/Berlin", "GBP": "Europe/London", "AUD": "Australia/Sydney"}


def red_news_times(currencies: list[str], path: Path = CAL) -> tuple[list[datetime], set[date]]:
    """Release times (UTC) of High-impact events for `currencies`, plus New York dates of events
    whose time cannot be recovered (speeches without a usual time, summits, elections).

    Wall-clock offset: Iran observed DST up to 2022, so the file's own offset label is right up to
    2022; from 2023 the scraper still labels summer rows +04:30 but the clock is +03:30 (checked:
    FOMC 14:00 NY and NFP 08:30 NY line up only with +03:30). A missing time (00:00:00) is filled
    with the event's usual home-zone clock time from rows that have one (2019-2025, requires the
    usual time to cover >= 60% of them), else OFFICIAL_TIMES; otherwise the whole day is listed.
    """
    d = pl.read_csv(path, infer_schema_length=0).filter(
        (pl.col("Impact") == "High Impact Expected") & pl.col("Currency").is_in(currencies))
    wall = pl.col("DateTime").str.slice(0, 19).str.to_datetime("%Y-%m-%dT%H:%M:%S")
    d = d.with_columns(
        wall=wall, file_date=wall.dt.date(),
        known=~pl.col("DateTime").str.slice(11, 8).is_in(["00:00:00", "23:59:59"]),
        utc=pl.when(wall.dt.year() <= 2022)
        .then(pl.col("DateTime").str.to_datetime("%Y-%m-%dT%H:%M:%S%z").dt.convert_time_zone("UTC"))
        .otherwise((wall - timedelta(hours=3, minutes=30)).dt.replace_time_zone("UTC")))
    rows = d.to_dicts()
    from collections import Counter, defaultdict
    from zoneinfo import ZoneInfo
    seen: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for r in rows:
        if r["known"] and 2019 <= r["wall"].year <= 2025:
            seen[(r["Currency"], r["Event"])][r["utc"].astimezone(ZoneInfo(HOME_TZ[r["Currency"]])).strftime("%H:%M")] += 1
    times: list[datetime] = []
    whole_days: set[date] = set()
    for r in rows:
        if r["known"]:
            times.append(r["utc"])
            continue
        key = (r["Currency"], r["Event"])
        c = seen.get(key)
        hhmm = None
        if c and c.most_common(1)[0][1] / sum(c.values()) >= 0.6:
            hhmm = c.most_common(1)[0][0]
        hhmm = hhmm or OFFICIAL_TIMES.get(key)
        if hhmm is None:
            whole_days.add(r["file_date"])
            continue
        h, m = map(int, hhmm.split(":"))
        local = datetime(r["file_date"].year, r["file_date"].month, r["file_date"].day, h, m,
                         tzinfo=ZoneInfo(HOME_TZ[r["Currency"]]))
        times.append(local.astimezone(ZoneInfo("UTC")))
    return sorted(set(times)), whole_days


def apply_news_blackout(sig: pl.DataFrame, currencies: list[str], minutes: int = 60,
                        path: Path = CAL) -> pl.DataFrame:
    """Prop-firm news rule (user's standing rule since run 045): for every red release of
    `currencies`, no entries from `minutes` before to `minutes` after, and any open trade is closed
    `minutes` before (engine exit_signal, filled at the next bar's open = this bar's close_time).
    Days with a red event of unknown time are blocked entirely. Needs close_time, long_signal and
    short_signal; adds news_blackout and ORs it into exit_signal (created if absent)."""
    import numpy as np

    times, days = red_news_times(list(currencies), path)
    ev = np.array([int(t.timestamp() * 1e9) for t in times], dtype=np.int64)
    t = sig["close_time"].dt.epoch("ns").to_numpy()
    w = minutes * 60 * 1_000_000_000
    i = np.searchsorted(ev, t - w, side="left")                       # first release >= t - window
    nxt = np.where(i < len(ev), ev[np.minimum(i, len(ev) - 1)], np.iinfo(np.int64).max)
    near = pl.Series("news_blackout", nxt <= t + w)
    whole = sig["close_time"].dt.convert_time_zone("America/New_York").dt.date().is_in(sorted(days))
    out = sig.with_columns(near | whole)
    ex = pl.col("exit_signal") if "exit_signal" in sig.columns else pl.lit(False)
    return out.with_columns(
        long_signal=pl.col("long_signal") & ~pl.col("news_blackout"),
        short_signal=pl.col("short_signal") & ~pl.col("news_blackout"),
        exit_signal=(ex | pl.col("news_blackout")).fill_null(True),
    )
