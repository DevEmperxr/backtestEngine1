"""Download many pair-years of 1s Dukascopy data, a few at a time, resumably.

    python download_batch.py                      # the 21 G8 minor crosses, 2021-2025
    python download_batch.py --pairs EURGBP GBPJPY --years 2024 2025 --workers 2

Each job runs downloadData.py into data/<PAIR>_1s_<YEAR>.csv.partial and renames it
to .csv only when the whole year finished, so a .csv on disk is always complete.
Finished files are skipped, so the batch can be stopped and restarted any time.
A failed job is retried (downloadData.py already retries each month's fetch).
Stops launching new jobs if free disk falls below --min-free-gb.

2026 is deliberately not in the default years: it is held out as unseen data.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
LOGS = DATA / "download_logs"

MINOR_CROSSES = [
    "EURGBP", "EURJPY", "EURCHF", "EURAUD", "EURCAD", "EURNZD",
    "GBPJPY", "GBPCHF", "GBPAUD", "GBPCAD", "GBPNZD",
    "AUDJPY", "AUDCHF", "AUDCAD", "AUDNZD",
    "NZDJPY", "NZDCHF", "NZDCAD",
    "CADJPY", "CADCHF", "CHFJPY",
]


def free_gb() -> float:
    return shutil.disk_usage(DATA).free / 1e9


def run_job(pair: str, year: int, attempts: int, min_free_gb: float) -> str:
    final = DATA / f"{pair}_1s_{year}.csv"
    if final.exists():
        return f"{pair} {year}: already done"
    partial = final.with_suffix(".csv.partial")
    log = LOGS / f"{pair}_{year}.log"
    for attempt in range(1, attempts + 1):
        if free_gb() < min_free_gb:
            return f"{pair} {year}: SKIPPED, free disk {free_gb():.0f} GB < {min_free_gb} GB"
        with open(log, "a", encoding="utf-8") as fh:
            fh.write(f"\n=== attempt {attempt} {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            fh.flush()
            rc = subprocess.call(
                [sys.executable, str(ROOT / "downloadData.py"), "--instrument", pair,
                 "--start", f"{year}-01-01", "--end", f"{year + 1}-01-01",
                 "--interval", "1s", "--out", str(partial)],
                stdout=fh, stderr=subprocess.STDOUT, cwd=ROOT,
            )
        if rc == 0 and partial.exists() and partial.stat().st_size > 0:
            partial.replace(final)
            return f"{pair} {year}: done ({final.stat().st_size / 1e9:.2f} GB)"
        time.sleep(60 * attempt)
    return f"{pair} {year}: FAILED after {attempts} attempts (see {log.name})"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", nargs="*", default=MINOR_CROSSES)
    ap.add_argument("--years", nargs="*", type=int, default=[2021, 2022, 2023, 2024, 2025])
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--attempts", type=int, default=3)
    ap.add_argument("--min-free-gb", type=float, default=25.0)
    a = ap.parse_args()
    if 2026 in a.years:
        sys.exit("2026 is the held-out year; remove it from --years (ask the user first).")
    LOGS.mkdir(parents=True, exist_ok=True)
    jobs = [(p, y) for p in a.pairs for y in a.years]
    print(f"{len(jobs)} jobs, {a.workers} workers, free disk {free_gb():.0f} GB", flush=True)
    done = 0
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(run_job, p, y, a.attempts, a.min_free_gb): (p, y) for p, y in jobs}
        for f in as_completed(futs):
            done += 1
            print(f"[{done}/{len(jobs)}] {time.strftime('%H:%M:%S')} {f.result()}", flush=True)
    print("batch finished", flush=True)


if __name__ == "__main__":
    main()
