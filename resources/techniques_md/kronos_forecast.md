# Kronos Forecast (EXPERIMENTAL)

> **EXPERIMENTAL — research curiosity, not a validated forecaster.** Out-of-sample
> evaluation (Jul 2025–Jun 2026) found no confirmed predictive or distributional
> value; shaded bands are sampled path spread, not calibrated confidence
> intervals; model knowledge ends ~June 2025 (it cannot know current events).
> Not for published research. Validation re-test scheduled 2026-12-01
> (RATES_RERUN_PROTOCOL.md). Full record: KXAF_CLOSEOUT_MEMO.md.

## What it does

Samples M independent close-price paths over an H-day horizon from the Kronos
financial foundation model (NeoQuasar/Kronos-base, a decoder-only transformer
pre-trained on financial OHLCV series), given the last L bars of any OHLCV
series you paste into the input template. Outputs the path matrix, the
median/quartile/decile summary across paths, and a parameter echo with the
exact model pins and runtime.

**Close paths only are rendered.** Under production sampling the model emits
structurally invalid OHLC bars (high < max(open, close), etc.) at material
rates; the close channel is the only one the evaluation program validated as
always-sane. An optional raw-OHLC sheet (with per-bar validity flags) can be
enabled in the template — the violation count is itself a demo curiosity.

## How to use it

1. **Open Input Template** — a pre-filled workbook (the last 250 trading days
   of IEF from the evaluation program's frozen, sha-manifested snapshot; a
   static example, not a live feed). Paste any OHLCV series over the data
   block (≥120 rows; Volume may be left blank).
2. Set the parameter cells: lookback `L` (120–250), horizon `H` (cap 25
   trading days — the tested envelope), paths `M` (cap 50; latency is roughly
   linear in M×H — defaults run in ~30–60 s, M=50/H=25 ≈ 5–7 min), and the
   seed (identical inputs + seed reproduce identical outputs).
3. **Run Kronos Forecast** — progress reports elapsed vs expected; the result
   lands in a new output sheet, input never modified.

## Status and guardrails

- EXPERIMENTAL labeling on the template and every output — by design.
- No pathway into other TSL techniques: the output feeds nothing.
- Compute is local CPU only (no data leaves the machine); the model, tokenizer,
  and upstream code are pinned to the evaluated artifact and asserted at run.
- The validation evidence for this tool is a seed-pinned REPRODUCTION check
  against the evaluation program's own forecaster — it demonstrates the TSL
  integration faithfully reproduces the characterized artifact, NOT that the
  model has forecast skill (the evaluation found it does not, to date).
