# Strategy Research Journal

Index of every strategy experiment run in this repo, in order. See
[`strategy_research_protocol.md`](../strategy_research_protocol.md) for the
process this follows and the entry format. **Append-only** — a new result
gets a new numbered entry, never an edit to an old one.

Format: `- **00N** \`name\` (date) — hypothesis → decision + why. [details](runs/00N_name/summary.md)`

---

- **001** `sma_nywin_flat1600` (2026-10-05) — 5m SMA20/50 cross, 07:00 NY→16:00 London, SL10/TP15, flat 16:00 → **discarded**: +26.8 pips but expectancy CI [−1.20,+1.42] straddles 0, TP rate 40.9% vs 40% random-walk null, H1/H2 signs flip, ex-Nov −46.7. [details](runs/001_sma_nywin_flat1600/summary.md)
- **002** `sma_nywin_letrun` (2026-10-05) — as 001 but no time exit (let trades run) → **discarded**: win rate 40.23% vs 40.0% null (pure noise), CI [−1.45,+1.56], ex-Nov −120; the 16:00 flat changes ~12 pips over 68 trades. [details](runs/002_sma_nywin_letrun/summary.md)
- **003** `sma_nywin_atr` (2026-10-05) — as 001 with SL=2.5×ATR14, TP=1.5×SL → **discarded**: gross −102.7 (no edge before costs), CI [−1.92,+0.75], both halves negative; vol-scaled exits can't rescue an uninformative entry. [details](runs/003_sma_nywin_atr/summary.md)
- **004** `sma_mtf_align_1m` (2026-10-05) — 1m SMA20/50 cross only when 5m+15m SMA trends agree, SL4/TP6, flat 16:00 → **discarded**: −180.7 pips, gross −87.8, CI [−0.91,+0.02], negative both halves, TP 34.9% vs 37.6% spread-adjusted null. Also: null formula corrected to (SL−spread)/(SL+TP); errata appended to 001–003, conclusions unchanged. [details](runs/004_sma_mtf_align_1m/summary.md)
- **005** `orb_ny_prenews` (2026-10-05) — ORB: 07:00–08:30 NY range, first 1m close beyond it after 08:30, SL opposite side, TP 1.5×range, flat 16:00 → **discarded**: −165.4 pips, gross −104.3, CI [−2.55,+1.25], H1 +16 / H2 −181, TP 40.9% vs 45.5% null, NFP/CPI days no different (n=24). 46% of trades time-exited. [details](runs/005_orb_ny_prenews/summary.md)
