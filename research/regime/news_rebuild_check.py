"""Check the rebuilt USD news (research/regime/news_rebuild.py) against ForexFactory where both exist.

    .venv/Scripts/python.exe -m research.regime.news_rebuild_check

For 2024-01-01 .. 2025-04-07: every ForexFactory USD red event inside 09:55–16:00 New York, matched by exact time to
the rebuild (by event family), and the rebuild's events that ForexFactory does not have. No price data is used.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, time
from zoneinfo import ZoneInfo

from research.regime.news import red_news_events
from research.regime.news_rebuild import rebuilt_usd_events

NY = ZoneInfo("America/New_York")
START, END = date(2024, 1, 1), date(2025, 4, 7)
REBUILT_FAMILIES = {"ISM Manufacturing PMI", "ISM Services PMI", "JOLTS Job Openings", "FOMC Statement",
                    "Federal Funds Rate", "FOMC Press Conference", "FOMC Economic Projections", "FOMC Meeting Minutes",
                    "Fed Chair Powell Testifies"}


def main() -> None:
    ff, _ = red_news_events(["USD"])
    ff = [(t, e) for t, _, e in ff if START <= t.astimezone(NY).date() <= END
          and time(9, 55) <= t.astimezone(NY).time() < time(16, 0)]
    rb, _ = rebuilt_usd_events(START, END)
    rb_set = {(t, e) for t, _, e in rb}
    rb_times = {t for t, _, _ in rb}
    hit = Counter()
    miss = Counter()
    for t, e in ff:
        if e in REBUILT_FAMILIES:
            (hit if (t, e) in rb_set else miss)[e] += 1
    print("ForexFactory red USD events inside 09:55-16:00 NY,", START, "->", END, ":", len(ff))
    print("\nrebuilt families: matched / missed")
    for e in sorted(REBUILT_FAMILIES):
        print(f"  {e:<30} {hit[e]:>3} / {miss[e]}")
    for t, e in ff:
        if e in REBUILT_FAMILIES and (t, e) not in rb_set:
            print("    missed:", t.astimezone(NY).strftime("%Y-%m-%d %H:%M"), e)
    ff_set = set(ff)
    extra = [(t, e) for t, e in sorted(rb_set) if (t, e) not in ff_set]
    print(f"\nrebuild events ForexFactory did NOT mark red: {len(extra)}")
    for t, e in extra:
        print("   ", t.astimezone(NY).strftime("%Y-%m-%d %H:%M"), e)
    other = Counter(e for t, e in ff if e not in REBUILT_FAMILIES)
    covered = Counter(e for t, e in ff if e not in REBUILT_FAMILIES and t in rb_times)
    print("\nForexFactory events NOT rebuilt (count, of which at a time the rebuild blocks anyway):")
    for e, n in other.most_common():
        print(f"  {e:<34} {n:>3}  ({covered[e]} covered)")


if __name__ == "__main__":
    main()
