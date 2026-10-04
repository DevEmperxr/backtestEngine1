"""`FxChart` — the declarative `.plot(df, spec)` layer over `StreamChart`
(fx_visualizer_widget_spec.md §1-§7).

Everything in here reflects the hands-on findings from the §1.1 validation
spike (`notebooks/viz_spike.ipynb`), not just the library's docs:

- `StreamChart` ships a `Content-Security-Policy` header with no `style-src`,
  which silently blocks the inline-style mutations the JS uses to resize
  panes. `_patch_csp()` fixes this at the HTTP-response level, process-wide,
  the first time an `FxChart` is created (site-packages can't be hand-edited
  as a permanent fix — a reinstall would wipe it).
- Dynamic `add_pane()` needs a `resize` event dispatched afterward before the
  new layout actually renders.
- Lightweight Charts v5's line series does NOT render a gap for null values —
  it interpolates straight across them. Real gaps (including the bounded-hline
  case from spec §6.1) require splitting a column into one `create_line()`
  series per contiguous non-null run, which is what `_plot_line` does.
- `.delete()` on the only series of a dynamically-added pane throws and the
  pane does not collapse — this module simply never relies on that path.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import pandas as pd
import polars as pl
from lightweight_charts import StreamChart
from lightweight_charts.plugins.session_highlighting import SessionHighlighting

_TIME_COL = "timestamp"
_csp_patched = False


def _patch_csp() -> None:
    """Add `style-src 'self' 'unsafe-inline'` to any CSP header missing one.

    `StreamChart`'s own `/` route ships
    `Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-eval'`
    with no `style-src` — under default `default-src` fallback that blocks
    every inline `style=` mutation, which breaks dynamic pane rendering
    (confirmed hands-on, see the module docstring). Patching
    `FileResponse.__init__` is the only hook available without touching
    installed-package source (the header dict is a local variable inside a
    closure in `StreamWindow.show()`, not reachable from outside it).
    """
    global _csp_patched
    if _csp_patched:
        return
    from fastapi.responses import FileResponse

    _orig_init = FileResponse.__init__

    def _patched_init(self, *args, **kwargs):
        _orig_init(self, *args, **kwargs)
        csp = self.headers.get("content-security-policy")
        if csp and "style-src" not in csp:
            self.headers["content-security-policy"] = csp + "; style-src 'self' 'unsafe-inline'"

    FileResponse.__init__ = _patched_init
    _csp_patched = True

    # StreamWindow (used by StreamChart) doesn't inherit from the desktop
    # Window class and is missing `_id_gen`, which `marker()`/`marker_list()`
    # need to mint per-marker JS variable names -- without this, any marker
    # call on a StreamChart series raises AttributeError. Give it the same
    # shared ID generator the rest of the library uses.
    from lightweight_charts.stream import StreamWindow
    from lightweight_charts.util import IDGen

    if not hasattr(StreamWindow, "_id_gen"):
        StreamWindow._id_gen = IDGen()


def _contiguous_runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """[start, end) index pairs for each contiguous True run in a 1-D bool array."""
    if not mask.any():
        return []
    padded = np.concatenate(([0], mask.astype(np.int8), [0]))
    edges = np.flatnonzero(np.diff(padded))
    return list(zip(edges[0::2].tolist(), edges[1::2].tolist()))


def _to_pandas(df: pl.DataFrame | pd.DataFrame, time_col: str = _TIME_COL) -> pd.DataFrame:
    """Polars -> pandas with the tz-aware-datetime gotcha from the spike already applied."""
    if isinstance(df, pl.DataFrame):
        if df.schema[time_col].time_zone is not None:
            df = df.with_columns(pl.col(time_col).dt.replace_time_zone(None))
        pdf = df.to_pandas()
    else:
        pdf = df.copy()
        if isinstance(pdf[time_col].dtype, pd.DatetimeTZDtype):
            pdf[time_col] = pdf[time_col].dt.tz_localize(None)
    if time_col != "time":
        pdf = pdf.rename(columns={time_col: "time"})
    return pdf


class FxChart:
    """A live, in-notebook chart backed by `StreamChart`.

    ::

        chart = FxChart()   # cell 1, once
        chart              # displays the iframe

        chart.plot(df, spec=[...])   # cell 2, rerun freely -- viewport persists
    """

    def __init__(self, width: int = 820, height: int = 460, port: int = 8765):
        _patch_csp()
        self._sc = StreamChart(width=width, height=height)
        self._width = width
        self._height = height
        self._port = port
        self._panes_created = {0}
        # key -> series object (or list of Box objects for a bounded region)
        self._series: dict[tuple, Any] = {}
        self._sc.show(port=port, block=False)
        time.sleep(1.2)  # let uvicorn bind before the iframe's first connection attempt

    def _repr_html_(self) -> str:
        return (
            f'<iframe src="http://127.0.0.1:{self._port}" '
            f'width="{self._width + 20}" height="{self._height + 20}" '
            f'style="border:1px solid #333;border-radius:8px"></iframe>'
        )

    def stop(self) -> None:
        """Stop the local server. Not required for notebook use (daemon thread),
        but useful in scripts/tests that create many `FxChart`s."""
        self._sc.win.stop()

    # ------------------------------------------------------------------
    # declarative entry point
    # ------------------------------------------------------------------

    def plot(self, df: pl.DataFrame | pd.DataFrame, spec: list[dict] | None = None) -> None:
        """Render `spec` against `df`. Idempotent: calling again with the same
        spec/data updates existing series in place (preserving zoom/pan);
        series no longer present in `spec` are removed.
        """
        self._await_client()
        pdf = _to_pandas(df)
        if spec is None:
            spec = self._default_spec(pdf)
        if not spec:
            raise ValueError(
                "empty spec and no auto-detectable OHLC columns -- pass an explicit spec"
            )

        # Batch every script this call produces into one combined send instead
        # of many separate rapid-fire WS messages. Confirmed by direct testing:
        # a series' marker-plugin setup (async on the JS side) can lose a race
        # against a later script arriving right behind it when many small
        # messages are sent back to back (replayed-on-connect or live) --
        # `Cannot read properties of undefined (reading 'setMarkers')` with no
        # Python-side exception. One combined script has no message boundary
        # for that race to happen across.
        pane_added = False
        with self._sc.win.bulk_run:
            target_keys: set[tuple] = set()
            for entry in spec:
                kind = entry["kind"]
                pane = entry.get("pane", 0)
                pane_added |= self._ensure_pane(pane)
                if kind == "candle":
                    target_keys |= self._plot_candle(pdf, entry)
                elif kind == "line":
                    target_keys |= self._plot_line(pdf, entry, pane)
                elif kind == "marker":
                    target_keys |= self._plot_marker(pdf, entry, pane)
                elif kind == "region":
                    target_keys |= self._plot_region(pdf, entry, pane)
                else:
                    raise ValueError(f"unknown spec kind: {kind!r}")

            stale = set(self._series) - target_keys
            for key in stale:
                obj = self._series.pop(key)
                for item in (obj if isinstance(obj, list) else [obj]):
                    item.delete()

        if pane_added:
            time.sleep(0.3)

    def _await_client(self, timeout: float = 5.0) -> None:
        """Block briefly until a browser client is connected.

        `.plot()` batches its whole script into one send (see the `bulk_run`
        use below), which is the real fix for the marker-plugin race this
        method was originally written to work around. Kept as a cheap second
        line of defense: with nobody connected yet, scripts are buffered and
        only replayed once a client shows up, so there is no reason to build
        and discard the batch now versus waiting a few hundred ms. Falls back
        to proceeding anyway after `timeout` rather than hanging forever if
        the iframe was never displayed.
        """
        if self._sc.win._ws is not None:
            return
        deadline = time.time() + timeout
        while time.time() < deadline and self._sc.win._ws is None:
            time.sleep(0.1)

    @staticmethod
    def _default_spec(pdf: pd.DataFrame) -> list[dict]:
        if {"open", "high", "low", "close"}.issubset(pdf.columns):
            return [{"kind": "candle"}]
        return []

    def _ensure_pane(self, pane: int) -> bool:
        """Returns True iff a new pane was created (caller should settle after)."""
        if pane in self._panes_created:
            return False
        start = max(self._panes_created) + 1
        for _ in range(start, pane + 1):
            self._sc.add_pane(120)
        self._panes_created.update(range(start, pane + 1))
        # dynamic pane-add needs a resize nudge before the new layout renders
        # (confirmed in the §1.1 spike -- not a timing-sensitive guess). The
        # settle sleep happens once, after the whole batched script is sent
        # (see plot()) -- sleeping here would do nothing, since nothing has
        # actually reached the browser yet while bulk_run is still collecting.
        self._sc.run_script("window.dispatchEvent(new Event('resize'))")
        return True

    # ------------------------------------------------------------------
    # column-kind renderers
    # ------------------------------------------------------------------

    def _plot_candle(self, pdf: pd.DataFrame, entry: dict) -> set[tuple]:
        prefix = entry.get("column")
        o = entry.get("open", f"{prefix}_open" if prefix else "open")
        h = entry.get("high", f"{prefix}_high" if prefix else "high")
        l = entry.get("low", f"{prefix}_low" if prefix else "low")
        c = entry.get("close", f"{prefix}_close" if prefix else "close")
        missing = [col for col in (o, h, l, c) if col not in pdf.columns]
        if missing:
            raise ValueError(f"candle spec missing column(s): {missing}")
        sub = pdf[["time", o, h, l, c]].rename(
            columns={o: "open", h: "high", l: "low", c: "close"}
        )
        self._sc.set(sub)
        return {("candle", 0)}

    def _plot_line(self, pdf: pd.DataFrame, entry: dict, pane: int) -> set[tuple]:
        col = entry["column"]
        color = entry.get("color", "#2196F3")
        width = entry.get("width", 2)
        mask = pdf[col].notna().to_numpy()
        runs = _contiguous_runs(mask)
        keys: set[tuple] = set()
        for i, (a, b) in enumerate(runs):
            key = ("line", col, pane, i)
            series = self._series.get(key)
            if series is None:
                series = self._sc.create_line(
                    col, color=color, width=width, price_line=False, pane_index=pane
                )
                self._series[key] = series
            series.set(pdf.iloc[a:b][["time", col]])
            keys.add(key)
        return keys

    def _plot_marker(self, pdf: pd.DataFrame, entry: dict, pane: int) -> set[tuple]:
        col = entry["column"]
        shape = entry.get("shape", "circle")
        color = entry.get("color", "#2196F3")
        position = entry.get("position", "below")
        key = ("marker", col, pane)
        series = self._series.get(key)
        if series is None:
            # invisible carrier series -- markers are per-series in this library,
            # so each marker_column gets its own so columns don't clobber each
            # other's markers on re-plot.
            series = self._sc.create_line(
                f"__marker__{col}", color="rgba(0,0,0,0)", price_line=False, pane_index=pane
            )
            self._series[key] = series
        mask = pdf[col].astype(bool).to_numpy()
        markers = [
            {"time": t, "position": position, "shape": shape, "color": color, "text": ""}
            for t in pdf.loc[mask, "time"]
        ]
        series.clear_markers()
        if markers:
            series.marker_list(markers)
        return {key}

    def _plot_region(self, pdf: pd.DataFrame, entry: dict, pane: int) -> set[tuple]:
        col = entry["column"]
        top_col = entry.get("top_column")
        bot_col = entry.get("bottom_column")
        key = ("region", col, pane)
        mask = pdf[col].astype(bool).to_numpy()
        runs = _contiguous_runs(mask)

        if top_col and bot_col:
            for box in self._series.pop(key, []):
                box.delete()
            boxes = []
            for a, b in runs:
                t0, t1 = pdf["time"].iloc[a], pdf["time"].iloc[b - 1]
                top = pdf[top_col].iloc[a:b].dropna()
                bot = pdf[bot_col].iloc[a:b].dropna()
                if top.empty or bot.empty:
                    continue
                boxes.append(
                    self._sc.box(
                        t0, float(bot.iloc[0]), t1, float(top.iloc[0]),
                        color=entry.get("color", "#1E80F0"),
                        fill_color=entry.get("fill_color", "rgba(30, 128, 240, 0.15)"),
                    )
                )
            self._series[key] = boxes
        else:
            highlighter = self._series.get(key)
            if highlighter is None:
                highlighter = SessionHighlighting(self._sc)
                self._series[key] = highlighter
            sessions = [
                {
                    "start": int(pdf["time"].iloc[a].timestamp()),
                    "end": int(pdf["time"].iloc[b - 1].timestamp()),
                    "color": entry.get("color", "rgba(41, 98, 255, 0.08)"),
                }
                for a, b in runs
            ]
            highlighter.set_sessions(sessions)
        return {key}
