"""Download SOL/USDT 1s candles from Binance's public API into the SAME
table shape the EURUSD files use, so it drops straight into lib.data.load_1s_data.

Columns (identical to data/EURUSD_1s_*.csv):
    timestamp,
    bid_open, bid_high, bid_low, bid_close, bid_volume,
    ask_open, ask_high, ask_low, ask_close, ask_volume

Binance's public klines API gives trade-based OHLCV only -- there is no free
historical bid/ask (quote) feed for crypto. bid_*/ask_* here are SYNTHETIC,
derived from the single OHLC by applying a fixed half-spread grounded in
Binance's actual documented numbers, not an invented heuristic:
    - a small real touch-spread component (SOL/USDT is very liquid: ~0.01%)
    - the real standard taker fee (0.1% per side, no BNB discount)
    -> HALF_SPREAD_PCT = 0.0011 (0.11%), so round-trip cost ~= 0.22%,
       matching fee (0.20%) + touch spread (0.02%).
Deliberately NOT volatility- or volume-scaled -- that's a real phenomenon but
modeling it without evidence would be exactly the kind of unvalidated
assumption strategy_research_protocol.md warns against; treat it as its own
hypothesis to test later if it matters, not something silently baked into
the base data.

Resumable: if --out already exists, picks up from its last timestamp instead
of re-fetching from the start (this is a multi-hour download at 1s
granularity over a multi-year range -- expect it to be interrupted).

Examples:
    python downloadSolanaData.py --start 2024-01-01 --end 2025-01-01 --out data/SOLUSDT_1s_2024.csv
    python downloadSolanaData.py --symbol SOLUSDT --interval 1s --start 2023-06-30 --end 2023-12-31 --out data/SOLUSDT_1s_2023.csv
"""

from __future__ import annotations

import argparse
import csv
import os
import time
from datetime import datetime, timedelta, timezone

import requests

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
MAX_ROWS_PER_REQUEST = 1000

# Grounded in Binance's real, documented numbers (see module docstring) --
# not an invented/volatility-scaled heuristic.
HALF_SPREAD_PCT = 0.0011

HEADER = [
    "timestamp",
    "bid_open", "bid_high", "bid_low", "bid_close", "bid_volume",
    "ask_open", "ask_high", "ask_low", "ask_close", "ask_volume",
]

INTERVAL_MS = {
    "1s": 1_000, "1m": 60_000, "5m": 300_000, "15m": 900_000,
    "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000,
}


def parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def fmt_ts(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S+00:00")


def last_timestamp_in(path: str) -> datetime | None:
    """Last row's timestamp, for resuming an interrupted download."""
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        if size < 2:
            return None
        back = min(size, 4096)
        f.seek(-back, os.SEEK_END)
        tail = f.read().decode("utf-8", errors="ignore")
    lines = [l for l in tail.splitlines() if l.strip()]
    if not lines or lines[-1].startswith("timestamp"):
        return None
    last = lines[-1].split(",", 1)[0]
    return datetime.strptime(last, "%Y-%m-%d %H:%M:%S%z")


def fetch_klines(symbol: str, interval: str, start_ms: int, end_ms: int) -> list:
    for attempt in range(6):
        resp = requests.get(
            BINANCE_KLINES_URL,
            params={
                "symbol": symbol, "interval": interval,
                "startTime": start_ms, "endTime": end_ms,
                "limit": MAX_ROWS_PER_REQUEST,
            },
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code in (429, 418):
            wait = int(resp.headers.get("Retry-After", 5)) + attempt * 5
            print(f"  rate-limited ({resp.status_code}), waiting {wait}s...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
    raise RuntimeError(f"gave up after repeated rate-limit errors for {start_ms}")


def kline_to_row(k: list) -> list:
    open_, high, low, close = float(k[1]), float(k[2]), float(k[3]), float(k[4])
    vol = float(k[5])
    h = HALF_SPREAD_PCT
    bid = [p * (1 - h) for p in (open_, high, low, close)]
    ask = [p * (1 + h) for p in (open_, high, low, close)]
    return [fmt_ts(k[0]), *bid, vol, *ask, vol]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download SOL/USDT 1s candles from Binance into the EURUSD-table shape."
    )
    parser.add_argument("--symbol", default="SOLUSDT")
    parser.add_argument("--interval", choices=INTERVAL_MS, default="1s")
    parser.add_argument("--start", type=parse_date, required=True)
    parser.add_argument("--end", type=parse_date, required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--sleep", type=float, default=0.12, help="delay between requests (s)")
    args = parser.parse_args()

    step_ms = INTERVAL_MS[args.interval] * MAX_ROWS_PER_REQUEST
    end_ms = int(args.end.timestamp() * 1000)

    resume_from = last_timestamp_in(args.out)
    if resume_from is not None:
        cur_ms = int(resume_from.timestamp() * 1000) + INTERVAL_MS[args.interval]
        print(f"Resuming {args.out} from {fmt_ts(cur_ms)}")
        out_mode = "a"
    else:
        cur_ms = int(args.start.timestamp() * 1000)
        out_mode = "w"

    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    total = 0
    t0 = time.time()
    with open(args.out, out_mode, newline="") as f:
        writer = csv.writer(f)
        if out_mode == "w":
            writer.writerow(HEADER)
        while cur_ms < end_ms:
            chunk_end = min(cur_ms + step_ms, end_ms)
            klines = fetch_klines(args.symbol, args.interval, cur_ms, chunk_end - 1)
            if klines:
                writer.writerows(kline_to_row(k) for k in klines)
                f.flush()
                total += len(klines)
                cur_ms = klines[-1][0] + INTERVAL_MS[args.interval]
            else:
                cur_ms = chunk_end
            if total and total % 50_000 < MAX_ROWS_PER_REQUEST:
                elapsed = time.time() - t0
                pct = (cur_ms - int(args.start.timestamp() * 1000)) / (end_ms - int(args.start.timestamp() * 1000)) * 100
                print(f"  {total:,} rows, {fmt_ts(cur_ms)} ({pct:.1f}%), {elapsed/60:.1f}min elapsed")
            time.sleep(args.sleep)

    print(f"Done. {total:,} new rows -> {args.out} ({(time.time()-t0)/60:.1f} min)")


if __name__ == "__main__":
    main()
