"""Rebuilt USD red-news times for dates after the ForexFactory file ends (2025-04-07), from official schedules.

Only events that ForexFactory marked red in its most recent months (Oct 2024 – Apr 2025) AND that fall inside US cash
hours are rebuilt; 08:30 / 09:45 releases are not needed by strategies that are flat before 10:00 New York (the 079
noise-area rule). Validated against ForexFactory in research/regime/news_rebuild_check.py.

Sources (fetched 2026-10-09):
- FOMC meetings, SEP meetings and minutes: federalreserve.gov/monetarypolicy/fomccalendars.htm
- JOLTS actual publication dates (incl. the 2025 shutdown: Sep 2025 not published, Oct 2025 on 9 Dec):
  bls.gov/bls/news-release/jolts.htm
- Chair Powell 2025 speeches and testimony: federalreserve.gov/newsevents/2025-speeches.htm, 2025-testimony.htm
- ISM Manufacturing = 1st business day (2nd in January), ISM Services = 3rd business day (4th in January), 10:00 ET;
  rule checked against ForexFactory 2023–Apr 2025.
NOT rebuildable: "President Trump Speaks" (red on ForexFactory from 2025, irregular times). Its effect is measured on
Jan–Mar 2025 instead.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")

FOMC = {  # decision day -> has SEP
    date(2024, 1, 31): False, date(2024, 3, 20): True, date(2024, 5, 1): False, date(2024, 6, 12): True,
    date(2024, 7, 31): False, date(2024, 9, 18): True, date(2024, 11, 7): False, date(2024, 12, 18): True,
    date(2025, 1, 29): False, date(2025, 3, 19): True, date(2025, 5, 7): False, date(2025, 6, 18): True,
    date(2025, 7, 30): False, date(2025, 9, 17): True, date(2025, 10, 29): False, date(2025, 12, 10): True,
}
FOMC_MINUTES = [date(2024, 1, 3), date(2024, 2, 21), date(2024, 4, 10), date(2024, 5, 22), date(2024, 7, 3), date(2024, 8, 21),
                date(2024, 10, 9), date(2024, 11, 26), date(2025, 1, 8), date(2025, 2, 19), date(2025, 4, 9),
                date(2025, 5, 28), date(2025, 7, 9), date(2025, 8, 20), date(2025, 10, 8), date(2025, 11, 19),
                date(2025, 12, 30)]
JOLTS = [date(2024, 1, 3), date(2024, 1, 30), date(2024, 3, 6), date(2024, 4, 2), date(2024, 5, 1), date(2024, 6, 4),
         date(2024, 7, 2), date(2024, 7, 30), date(2024, 9, 4), date(2024, 10, 1), date(2024, 10, 29), date(2024, 12, 3),
         date(2025, 1, 7), date(2025, 2, 4), date(2025, 3, 11), date(2025, 4, 1), date(2025, 4, 29), date(2025, 6, 3),
         date(2025, 7, 1), date(2025, 7, 29), date(2025, 9, 3), date(2025, 9, 30), date(2025, 12, 9)]
POWELL_TESTIFIES = [date(2024, 3, 6), date(2024, 3, 7), date(2024, 7, 9), date(2024, 7, 10),
                    date(2025, 2, 11), date(2025, 2, 12), date(2025, 6, 24), date(2025, 6, 25)]
# policy speeches ("Economic Outlook" / framework / balance sheet); time not published -> whole-day block
POWELL_SPEECH_DAYS = [date(2025, 4, 16), date(2025, 8, 22), date(2025, 9, 23), date(2025, 10, 14)]


def _holidays(y: int) -> set[date]:
    """Federal holidays that can fall in the first four business days of a month."""
    sep1 = date(y, 9, 1)
    labor = sep1 + timedelta(days=(0 - sep1.weekday()) % 7)
    out = {date(y, 1, 1), date(y, 7, 4), labor}
    for d in list(out):                     # observed on Friday / Monday
        if d.weekday() == 5:
            out.add(d - timedelta(days=1))
        elif d.weekday() == 6:
            out.add(d + timedelta(days=1))
    return out


def nth_business_day(y: int, m: int, n: int) -> date:
    hol = _holidays(y)
    d, k = date(y, m, 1), 0
    while True:
        if d.weekday() < 5 and d not in hol:
            k += 1
            if k == n:
                return d
        d += timedelta(days=1)


def _at(d: date, hh: int, mm: int) -> datetime:
    return datetime.combine(d, time(hh, mm), tzinfo=NY).astimezone(UTC)


def rebuilt_usd_events(start: date, end: date) -> tuple[list[tuple[datetime, str, str]], set[date]]:
    """(UTC time, 'USD', event) for start <= NY date <= end, plus whole-day blocks."""
    ev: list[tuple[datetime, str, str]] = []
    for y in range(start.year, end.year + 1):
        for m in range(1, 13):
            ev.append((_at(nth_business_day(y, m, 2 if m == 1 else 1), 10, 0), "USD", "ISM Manufacturing PMI"))
            ev.append((_at(nth_business_day(y, m, 4 if m == 1 else 3), 10, 0), "USD", "ISM Services PMI"))
    for d, sep in FOMC.items():
        ev += [(_at(d, 14, 0), "USD", "FOMC Statement"), (_at(d, 14, 0), "USD", "Federal Funds Rate"),
               (_at(d, 14, 30), "USD", "FOMC Press Conference")]
        if sep:
            ev.append((_at(d, 14, 0), "USD", "FOMC Economic Projections"))
    ev += [(_at(d, 14, 0), "USD", "FOMC Meeting Minutes") for d in FOMC_MINUTES]
    ev += [(_at(d, 10, 0), "USD", "JOLTS Job Openings") for d in JOLTS]
    ev += [(_at(d, 10, 0), "USD", "Fed Chair Powell Testifies") for d in POWELL_TESTIFIES]
    ev = [e for e in ev if start <= e[0].astimezone(NY).date() <= end]
    whole = {d for d in POWELL_SPEECH_DAYS if start <= d <= end}
    return sorted(set(ev)), whole
