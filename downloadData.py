"""Download FX candles (default EURUSD) from Dukascopy into a single CSV.

Requires:
    pip install dukascopy-python pandas

Output: ONE csv with bid + ask OHLCV per candle. Columns:
    timestamp,
    bid_open, bid_high, bid_low, bid_close, bid_volume,
    ask_open, ask_high, ask_low, ask_close, ask_volume

Examples:
    python downloadData.py                                   # last 30 days, 1m
    python downloadData.py --start 2024-01-01 --end 2025-01-01 --interval 1s
    python downloadData.py --start 2024-01-01 --end 2025-01-01 --interval 1s --out data/EURUSD_1s_2024.csv
    python downloadData.py --instrument EURGBP --start 2024-01-01 --end 2025-01-01 --interval 1s --out data/EURGBP_1s_2024.csv

Each month's fetch is retried with backoff on network errors (a DNS blip once
killed a whole-year download), so one failure doesn't lose the run.
"""

from __future__ import annotations

import argparse
import os
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import dukascopy_python
from dukascopy_python import instruments as _instruments

# Human-friendly interval names -> dukascopy_python constants.
INTERVALS = {
    "1s": dukascopy_python.INTERVAL_SEC_1,
    "10s": dukascopy_python.INTERVAL_SEC_10,
    "1m": dukascopy_python.INTERVAL_MIN_1,
    "5m": dukascopy_python.INTERVAL_MIN_5,
    "15m": dukascopy_python.INTERVAL_MIN_15,
    "30m": dukascopy_python.INTERVAL_MIN_30,
    "1h": dukascopy_python.INTERVAL_HOUR_1,
    "4h": dukascopy_python.INTERVAL_HOUR_4,
    "1d": dukascopy_python.INTERVAL_DAY_1,
}

OHLCV = ["open", "high", "low", "close", "volume"]


def parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def month_ranges(start: datetime, end: datetime):
    """Yield (chunk_start, chunk_end) covering [start, end) one calendar month at a time."""
    cur = start
    while cur < end:
        if cur.month == 12:
            nxt = cur.replace(year=cur.year + 1, month=1, day=1)
        else:
            nxt = cur.replace(month=cur.month + 1, day=1)
        yield cur, min(nxt, end)
        cur = nxt


def resolve_instrument(pair: str) -> str:
    """'EURGBP' -> Dukascopy's 'EUR/GBP' constant (majors, crosses, ...)."""
    pair = pair.upper().replace("/", "")
    want = f"{pair[:3]}/{pair[3:]}"
    for name in dir(_instruments):
        if name.startswith("INSTRUMENT_FX_") and getattr(_instruments, name) == want:
            return getattr(_instruments, name)
    raise SystemExit(f"unknown FX instrument {pair!r}")


def fetch_side(instrument, interval, side, start, end, retries: int = 6) -> pd.DataFrame:
    for attempt in range(retries):
        try:
            df = dukascopy_python.fetch(instrument, interval, side, start, end)
            break
        except Exception as e:  # network/DNS/HTTP errors from requests
            if attempt == retries - 1:
                raise
            wait = 30 * 2 ** attempt
            print(f"  fetch failed ({type(e).__name__}); retry {attempt + 1}/{retries - 1} in {wait}s", flush=True)
            time.sleep(wait)
    if df is None or df.empty:
        return pd.DataFrame(columns=OHLCV)
    return df[OHLCV]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download FX bid+ask candles from Dukascopy into one CSV."
    )
    parser.add_argument("--instrument", default="EURUSD", help="Pair, e.g. EURUSD, EURGBP (default EURUSD).")
    parser.add_argument("--start", type=parse_date, help="Start date YYYY-MM-DD (UTC).")
    parser.add_argument("--end", type=parse_date, help="End date YYYY-MM-DD (UTC).")
    parser.add_argument(
        "--interval", choices=INTERVALS, default="1m", help="Candle size (default: 1m)."
    )
    parser.add_argument("--out", default=None, help="Output CSV path (default: auto).")
    args = parser.parse_args()

    end = args.end or datetime.now(timezone.utc)
    start = args.start or (end - timedelta(days=30))
    interval = INTERVALS[args.interval]
    pair = args.instrument.upper().replace("/", "")
    instrument = resolve_instrument(pair)

    out = args.out or f"{pair}_{args.interval}_bidask_{start:%Y%m%d}_{end:%Y%m%d}.csv"
    out_dir = os.path.dirname(out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    if os.path.exists(out):
        os.remove(out)

    total = 0
    wrote_header = False
    # Fetch month by month to keep memory bounded, then append to one CSV.
    for c_start, c_end in month_ranges(start, end):
        print(f"Fetching {pair} {args.interval} bid+ask {c_start:%Y-%m} ...", flush=True)
        bid = fetch_side(instrument, interval, dukascopy_python.OFFER_SIDE_BID, c_start, c_end)
        ask = fetch_side(instrument, interval, dukascopy_python.OFFER_SIDE_ASK, c_start, c_end)

        merged = bid.add_prefix("bid_").join(ask.add_prefix("ask_"), how="outer")
        if merged.empty:
            print("  no data")
            continue

        merged.index.name = "timestamp"
        merged.sort_index(inplace=True)
        merged.to_csv(out, mode="a", header=not wrote_header)
        wrote_header = True
        total += len(merged)
        print(f"  +{len(merged):,} rows (total {total:,})", flush=True)

    if total:
        print(f"Done. {total:,} rows -> {out}")
    else:
        print("No data returned for the requested range.")


if __name__ == "__main__":
    main()
