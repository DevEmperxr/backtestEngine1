"""Download 1s Dukascopy data (bid + ask) for any pairs into data/<PAIR>_1s_<YEAR>.csv.

    .venv\\Scripts\\python.exe download_pairs.py XAUUSD AUDUSD             # 2023, 2024 first, then 2021, 2022, 2025
    .venv\\Scripts\\python.exe download_pairs.py XAUUSD AUDUSD --status    # progress; safe while downloading
    .venv\\Scripts\\python.exe download_pairs.py AUDUSD --years 2023 2024

Same behaviour as download_gbpusd.py / download_batch.py: each pair-year downloads to a .csv.partial
file and becomes .csv only when the whole year is complete; finished years are skipped, so you can
stop (Ctrl+C) and restart any time; failed years are retried; logs in data/download_logs/.
About 1 GB per pair-year. Works for FX majors, crosses and metals (XAUUSD = gold).

2023 + 2024 are the practice years (research/DATA_SPLIT.md); 2021, 2022 and 2025 are for later
checks. 2026 is the held-out year and is refused.
"""

from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from download_batch import LOGS, free_gb, print_status, run_job
from downloadData import resolve_instrument

DEFAULT_YEARS = [2023, 2024, 2021, 2022, 2025]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pairs", nargs="+", help="e.g. XAUUSD AUDUSD GBPUSD")
    ap.add_argument("--years", nargs="*", type=int, default=DEFAULT_YEARS)
    ap.add_argument("--workers", type=int, default=3, help="pair-years downloaded at the same time (default 3)")
    ap.add_argument("--attempts", type=int, default=3)
    ap.add_argument("--min-free-gb", type=float, default=25.0)
    ap.add_argument("--status", action="store_true", help="print progress and exit")
    a = ap.parse_args()
    pairs = [p.upper().replace("/", "") for p in a.pairs]
    for p in pairs:
        resolve_instrument(p)              # fail fast on a typo
    if a.status:
        print_status(pairs, sorted(a.years))
        return
    if 2026 in a.years:
        sys.exit("2026 is the held-out year; remove it from --years.")
    LOGS.mkdir(parents=True, exist_ok=True)
    jobs = [(p, y) for y in a.years for p in pairs]     # year-major: every pair's 2023 first
    print(f"{' '.join(pairs)}: years {a.years}, {len(jobs)} jobs, {a.workers} at a time, "
          f"free disk {free_gb():.0f} GB", flush=True)
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(run_job, p, y, a.attempts, a.min_free_gb) for p, y in jobs]
        for i, f in enumerate(as_completed(futs), 1):
            print(f"[{i}/{len(futs)}] {time.strftime('%H:%M:%S')} {f.result()}", flush=True)
    print(f"finished. Check with: .venv\\Scripts\\python.exe download_pairs.py {' '.join(pairs)} --status",
          flush=True)


if __name__ == "__main__":
    main()
