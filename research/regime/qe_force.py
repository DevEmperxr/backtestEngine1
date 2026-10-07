""""Q Tide" — net QE/QT balance-sheet force of the Fed vs the ECB on EUR/USD (run 055).

force_US = 13-week change in Fed assets / US annual nominal GDP x 100 (% of GDP)
force_EA = same for the ECB with euro area GDP
net F    = force_US - force_EA   (positive: Fed expanding faster -> EUR/USD should rise)
z        = F / std of F over the previous 756 trading days; state +1 if z > 1, -1 if z < -1, else 0

Every input is used only from the day it was published (conservative lags below), so the value on day
d never uses information released after d.

Data (cached in data/macro/, re-downloaded with refresh=True):
  FRED WALCL, WSHOSHO (Fed total assets / securities held outright, weekly Wednesday, millions USD)
  FRED ECBASSETSW (ECB total assets, weekly Friday, millions EUR)
  ECB ILM.W.U2.C.A070100.U2.EUR (securities held for monetary policy purposes, ISO week, millions EUR)
  FRED GDP (US nominal, quarterly SAAR, billions USD), EUNNGDP (euro area nominal, quarterly, millions EUR)
  FRED DEXUSEU (EUR/USD daily noon New York rate)
"""

from __future__ import annotations

import io
import subprocess
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import polars as pl

ROOT = Path(__file__).resolve().parents[2]
MACRO = ROOT / "data" / "macro"
FRED = ["WALCL", "WSHOSHO", "ECBASSETSW", "GDP", "EUNNGDP", "DEXUSEU"]
ECB_SEC = "ILM.W.U2.C.A070100.U2.EUR"
LAG_FED, LAG_ECB, LAG_GDP = 2, 5, 90        # days after the observation date (GDP: after quarter end)


def _fred(series: str, refresh: bool) -> pl.DataFrame:
    f = MACRO / f"{series}.csv"
    if refresh or not f.exists():
        MACRO.mkdir(parents=True, exist_ok=True)
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
        f.write_bytes(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=120).read())
    d = pl.read_csv(f, infer_schema_length=0)
    return d.select(date=pl.col(d.columns[0]).str.to_date(), v=pl.col(d.columns[1]).cast(pl.Float64, strict=False)).drop_nulls()


def _ecb_securities(refresh: bool) -> pl.DataFrame:
    f = MACRO / "ECB_securities_mpp.csv"
    if refresh or not f.exists():
        MACRO.mkdir(parents=True, exist_ok=True)
        url = f"https://data-api.ecb.europa.eu/service/data/ILM/{ECB_SEC.split('.', 1)[1]}?format=csvdata"
        # curl: Python's certificate store fails on this host here; curl's works
        f.write_bytes(subprocess.run(["curl", "-s", "--max-time", "300", url], check=True, capture_output=True).stdout)
    d = pl.read_csv(f, infer_schema_length=0).select("TIME_PERIOD", "OBS_VALUE")
    rows = []
    for p, v in d.iter_rows():
        y, w = p.split("-W")
        rows.append((date.fromisocalendar(int(y), int(w), 5), float(v)))
    return pl.DataFrame(rows, schema={"date": pl.Date, "v": pl.Float64}, orient="row")


def load(refresh: bool = False) -> dict[str, pl.DataFrame]:
    out = {s: _fred(s, refresh) for s in FRED}
    out["ECB_SEC"] = _ecb_securities(refresh)
    return out


def _weekly_force(assets: pl.DataFrame, lag_days: int) -> pl.DataFrame:
    """13-week change of a weekly level, stamped with the day it becomes usable."""
    a = assets.sort("date").with_columns(chg=pl.col("v") - pl.col("v").shift(13))
    return a.drop_nulls().select(avail=pl.col("date") + timedelta(days=lag_days), chg="chg")


def _gdp(g: pl.DataFrame, mult: float) -> pl.DataFrame:
    """Quarterly GDP -> annual level in millions, usable LAG_GDP days after the quarter ends."""
    return g.sort("date").select(
        avail=pl.col("date").dt.offset_by("3mo") + timedelta(days=LAG_GDP), gdp=pl.col("v") * mult)


def build(data: dict[str, pl.DataFrame], days: pl.Series, *, version: str = "total") -> pl.DataFrame:
    """Daily index on the given trading days. version: "total" (total assets) or "bonds" (securities)."""
    fed, ecb = (data["WALCL"], data["ECBASSETSW"]) if version == "total" else (data["WSHOSHO"], data["ECB_SEC"])
    cal = pl.DataFrame({"day": days}).sort("day")

    def asof(frame: pl.DataFrame, name: str) -> pl.DataFrame:
        return cal.join_asof(frame.sort("avail").rename({frame.columns[1]: name}),
                             left_on="day", right_on="avail", strategy="backward").drop("avail")

    out = (asof(_weekly_force(fed, LAG_FED), "chg_us")
           .join(asof(_weekly_force(ecb, LAG_ECB), "chg_ea"), on="day")
           .join(asof(_gdp(data["GDP"], 1000.0), "gdp_us"), on="day")       # billions SAAR -> millions
           .join(asof(_gdp(data["EUNNGDP"], 4.0), "gdp_ea"), on="day"))     # quarterly millions -> annual
    out = out.with_columns(
        force_us=pl.col("chg_us") / pl.col("gdp_us") * 100,
        force_ea=pl.col("chg_ea") / pl.col("gdp_ea") * 100,
    ).with_columns(F=pl.col("force_us") - pl.col("force_ea"))
    out = out.with_columns(z=pl.col("F") / pl.col("F").shift(1).rolling_std(756, min_samples=756))
    return out.with_columns(state=pl.when(pl.col("z") > 1).then(1).when(pl.col("z") < -1).then(-1)
                            .when(pl.col("z").is_not_null()).then(0))
