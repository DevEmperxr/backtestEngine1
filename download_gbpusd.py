"""Download GBPUSD 1s Dukascopy data (bid + ask) into data/GBPUSD_1s_<YEAR>.csv.

    .venv\\Scripts\\python.exe download_gbpusd.py             # 2023, 2024 first, then 2021, 2022, 2025
    .venv\\Scripts\\python.exe download_gbpusd.py --status    # progress; safe to run while downloading
    .venv\\Scripts\\python.exe download_gbpusd.py --years 2023 2024

Uses download_batch.run_job, so it behaves the same way: each year downloads to a .csv.partial
file and is renamed to .csv only when the whole year is complete; finished years are skipped, so
you can stop (Ctrl+C) and restart any time; a failed year is retried; logs go to
data/download_logs/GBPUSD_<YEAR>.log. About 1 GB per year.

2023 + 2024 are the practice years (research/DATA_SPLIT.md); 2021, 2022 and 2025 are for later
checks. 2026 is the held-out year and is refused.
"""

from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from download_batch import LOGS, free_gb, print_status, run_job

PAIR = "GBPUSD"
DEFAULT_YEARS = [2023, 2024, 2021, 2022, 2025]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--years", nargs="*", type=int, default=DEFAULT_YEARS)
    ap.add_argument("--workers", type=int, default=3, help="years downloaded at the same time (default 3)")
    ap.add_argument("--attempts", type=int, default=3)
    ap.add_argument("--min-free-gb", type=float, default=25.0)
    ap.add_argument("--status", action="store_true", help="print progress and exit")
    a = ap.parse_args()
    if a.status:
        print_status([PAIR], sorted(a.years))
        return
    if 2026 in a.years:
        sys.exit("2026 is the held-out year; remove it from --years.")
    LOGS.mkdir(parents=True, exist_ok=True)
    print(f"{PAIR}: years {a.years}, {a.workers} at a time, free disk {free_gb():.0f} GB", flush=True)
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(run_job, PAIR, y, a.attempts, a.min_free_gb) for y in a.years]
        for i, f in enumerate(as_completed(futs), 1):
            print(f"[{i}/{len(futs)}] {time.strftime('%H:%M:%S')} {f.result()}", flush=True)
    print("finished. Check with: .venv\\Scripts\\python.exe download_gbpusd.py --status", flush=True)


if __name__ == "__main__":
    main()
