"""Download 1s Dukascopy data (bid + ask) for stock indices: NAS 100, DAX and Nikkei 225.

    .venv\\Scripts\\python.exe download_indices.py             # NAS100 GER40 JPN225; 2023, 2024 first, then 2021, 2022, 2025
    .venv\\Scripts\\python.exe download_indices.py --status    # progress; safe to run while downloading
    .venv\\Scripts\\python.exe download_indices.py --pairs NAS100 --years 2023 2024

Files: data/NAS100_1s_<YEAR>.csv, data/GER40_1s_<YEAR>.csv, data/JPN225_1s_<YEAR>.csv
(Dukascopy instruments E_NQ-100, E_DAAX, E_N225Jap; prices in index points; the Nikkei is quoted in yen).
Same behaviour as download_pairs.py: each year goes to a .csv.partial and becomes .csv only when complete; finished
years are skipped, so you can stop (Ctrl+C) and restart any time; failed years are retried; logs in data/download_logs/.
2026 is the held-out year and is refused.
"""

from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from download_batch import LOGS, free_gb, print_status, run_job
from downloadData import resolve_instrument

INDICES = ["NAS100", "GER40", "JPN225"]
DEFAULT_YEARS = [2023, 2024, 2021, 2022, 2025]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pairs", nargs="*", default=INDICES, help="any of NAS100 GER40 JPN225 (DAX / NIKKEI also accepted)")
    ap.add_argument("--years", nargs="*", type=int, default=DEFAULT_YEARS)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--attempts", type=int, default=3)
    ap.add_argument("--min-free-gb", type=float, default=25.0)
    ap.add_argument("--status", action="store_true", help="print progress and exit")
    a = ap.parse_args()
    names = {"DAX": "GER40", "NIKKEI": "JPN225", "NASDAQ": "NAS100"}
    pairs = [names.get(p.upper(), p.upper()) for p in a.pairs]
    for p in pairs:
        resolve_instrument(p)              # fail fast on a typo
    if a.status:
        print_status(pairs, sorted(a.years))
        return
    if 2026 in a.years:
        sys.exit("2026 is the held-out year; remove it from --years.")
    LOGS.mkdir(parents=True, exist_ok=True)
    jobs = [(p, y) for y in a.years for p in pairs]     # every index's 2023 first, then 2024, ...
    print(f"{' '.join(pairs)}: years {a.years}, {len(jobs)} jobs, {a.workers} at a time, free disk {free_gb():.0f} GB", flush=True)
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(run_job, p, y, a.attempts, a.min_free_gb) for p, y in jobs]
        for i, f in enumerate(as_completed(futs), 1):
            print(f"[{i}/{len(futs)}] {time.strftime('%H:%M:%S')} {f.result()}", flush=True)
    print("finished. Check with: .venv\\Scripts\\python.exe download_indices.py --status", flush=True)


if __name__ == "__main__":
    main()
