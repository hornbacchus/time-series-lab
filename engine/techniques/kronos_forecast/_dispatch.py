"""TSL dispatch for Kronos Forecast: workbook -> subprocess (the pinned Kronos
venv) -> response tables. EXPERIMENTAL by design -- the status block and the
exact band label travel on every output.

Latency design (the chunking trap): predict_batch runs all M draws in ONE
autoregressive loop and batched draws are reproducible only AS A BATCH --
chunking for per-path progress would change the path set under the same seed
and falsify the K2 cross-source reproduction. So: ONE batch + a TIMER TICKER
that emits progress (elapsed vs expected, from the handoff's measured timing
formula) every ~10s while the subprocess runs -- the named-pipe heartbeat
(300s silence ceiling) stays alive at M=50/H=25 (~5-7 min) and the button
never looks hung.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import subprocess
import tempfile
import time

from techniques.base import make_error_response, make_response, make_table

from .workbook_input import TemplateError, read_workbook

# Path constants -- single-user prototype (the owner's box), centralized with
# env overrides so later packaging swaps these without touching logic.
KRONOS_PYTHON = os.environ.get(
    "TSL_KRONOS_PYTHON", r"C:\KronosDev\venv-kronos\Scripts\python.exe")
KRONOS_UPSTREAM = os.environ.get(
    "TSL_KRONOS_UPSTREAM", r"C:\KronosDev\kronos-upstream")
KRONOS_HF_HOME = os.environ.get("TSL_KRONOS_HF_HOME", r"C:\KronosDev\hf-cache")

# The characterized artifact (KRONOS_TSL_HANDOFF.md SS1/SS6) -- asserted by the
# runner before any inference; a mismatch is a structured error, never a
# silent fallback.
PINS = {
    "upstream_commit": "67b630e6",
    "model_rev": "2b554741eca47781b64468546e77fef3e85130e6",
    "tokenizer_rev": "0e0117387f39004a9016484a186a908917e22426",
    "torch_version": "2.12.0",
}

T_FIXED, TOP_P_FIXED = 0.6, 0.90

STATUS_BLOCK = (
    "EXPERIMENTAL -- research curiosity, not a validated forecaster; "
    "out-of-sample evaluation (Jul 2025 - Jun 2026) found no confirmed "
    "predictive or distributional value; bands are sampled path spread, not "
    "calibrated confidence intervals; model knowledge ends ~June 2025; not "
    "for published research; re-test 2026-12-01 per RATES_RERUN_PROTOCOL.md; "
    "see KXAF_CLOSEOUT_MEMO.md.")
BAND_LABEL = "sampled path spread -- NOT calibrated confidence bands"


def _expected_seconds(M: int, H: int) -> float:
    """Measured (KRONOS_TSL_HANDOFF.md SS3): ~10.7s cold load + 0.52 s/bar
    at ~1.6x batch efficiency."""
    return 11.0 + (M * H * 0.52) / 1.6


def run(ctx, progress_callback) -> dict:
    """``ctx.params['input_workbook']`` = path to the kronos_input template."""
    try:
        progress_callback("Reading the Kronos input workbook", 5)
        wb_path = ctx.get_param("input_workbook")
        if not wb_path or not os.path.exists(str(wb_path)):
            return make_error_response(
                ctx, "No input workbook. Use 'Open Input Template', fill the "
                     "kronos_input sheet, then Run.",
                error_fixes=["Open the Kronos Forecast input template first."])
        try:
            inp = read_workbook(str(wb_path))
        except TemplateError as e:
            return make_error_response(ctx, str(e), error_fixes=[
                "Fix the kronos_input sheet and re-run (the template's notes "
                "column documents each parameter)."])

        if not os.path.exists(KRONOS_PYTHON):
            return make_error_response(
                ctx, f"Kronos venv python not found at {KRONOS_PYTHON}.",
                error_fixes=["Install the Kronos environment (KRONOS_TSL_"
                             "HANDOFF.md SS1) or set TSL_KRONOS_PYTHON."])

        L, H, M, seed = inp["L"], inp["H"], inp["M"], inp["seed"]
        est = _expected_seconds(M, H)
        progress_callback(
            f"Launching Kronos (M={M} paths, H={H} days) -- expect ~{est:.0f}s "
            f"incl. model load. EXPERIMENTAL: no validated predictive value.", 10)

        tmpdir = tempfile.mkdtemp(prefix="tsl_kronos_")
        csv_path = os.path.join(tmpdir, "input.csv")
        out_path = os.path.join(tmpdir, "out.json")
        req_path = os.path.join(tmpdir, "request.json")
        inp["df"].to_csv(csv_path, index=False)
        with open(req_path, "w", encoding="utf-8") as fh:
            json.dump({"csv_path": csv_path, "L": L, "H": H, "M": M,
                       "seed": seed, "T": T_FIXED, "top_p": TOP_P_FIXED,
                       "hf_home": KRONOS_HF_HOME, "upstream_dir": KRONOS_UPSTREAM,
                       "expected": PINS, "out_path": out_path}, fh)

        runner = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runner.py")
        t0 = time.perf_counter()
        proc = subprocess.Popen(
            [KRONOS_PYTHON, runner, req_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

        # The timer ticker: keep the pipe alive + the expectation honest.
        last_tick = 0.0
        while proc.poll() is None:
            time.sleep(2)
            elapsed = time.perf_counter() - t0
            if elapsed - last_tick >= 10:
                last_tick = elapsed
                pct = min(90, 10 + int(75 * elapsed / max(est, 1)))
                progress_callback(
                    f"Kronos sampling {M} paths x {H} days -- elapsed "
                    f"{elapsed:.0f}s of ~{est:.0f}s expected", pct)
        wall = time.perf_counter() - t0

        if not os.path.exists(out_path):
            err = (proc.stderr.read() or proc.stdout.read() or "no output")[-400:]
            return make_error_response(
                ctx, f"Kronos runner produced no output (exit {proc.returncode}): {err}",
                error_fixes=["Check the Kronos environment (KRONOS_TSL_HANDOFF.md SS1)."])
        res = json.load(open(out_path, encoding="utf-8"))
        if res.get("status") != "ok":
            return make_error_response(
                ctx, f"Kronos runner error at stage '{res.get('stage')}': "
                     f"{res.get('detail')}",
                error_fixes=["The pinned artifact must match KRONOS_TSL_HANDOFF.md "
                             "SS1 exactly -- pins are asserted, never upgraded silently."])

        progress_callback("Building output tables", 92)
        dates = res["y_dates"]
        closes = res["close_paths"]
        last_close = float(inp["df"]["close"].iloc[-1])

        import numpy as np
        cm = np.array(closes)  # (M, H)
        qs = {q: np.percentile(cm, q, axis=0) for q in (10, 25, 50, 75, 90)}

        tables = [
            make_table("Kronos Parameters", ["Parameter", "Value"], [
                ["status", "EXPERIMENTAL (see the status block below)"],
                ["lookback_L", L], ["horizon_H", H], ["paths_M", M],
                ["seed", seed], ["T (fixed)", T_FIXED], ["top_p (fixed)", TOP_P_FIXED],
                ["last input close", round(last_close, 6)],
                ["model pin", f"NeoQuasar/Kronos-base @ {res['pins']['model_rev'][:8]}"],
                ["tokenizer pin", f"@ {res['pins']['tokenizer_rev'][:8]}"],
                ["upstream commit", res["pins"]["upstream_commit"][:12]],
                ["runner torch / python", f"{res['pins']['torch_version']} / "
                                          f"{res['pins']['python_version']}"],
                ["model load (s)", res["timings"]["load_s"]],
                ["sampling (s)", res["timings"]["predict_s"]],
                ["total wall (s)", round(wall, 1)],
                # The "(local)" suffix keeps Excel from coercing the stamp
                # into a raw date serial on write (display-only fix).
                ["run stamp", _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " (local)"],
                ["band labeling", BAND_LABEL],
            ]),
            make_table("Kronos Close Paths", ["Path"] + dates,
                       [[i + 1] + [round(v, 6) for v in row]
                        for i, row in enumerate(closes)]),
            make_table(f"Kronos Forecast Summary ({BAND_LABEL})",
                       ["Date", "Median Close", "P25", "P75", "P10", "P90"],
                       [[dates[j]] + [round(float(qs[q][j]), 6)
                                      for q in (50, 25, 75, 10, 90)]
                        for j in range(H)]),
        ]

        n_invalid = int(sum(1 for row in res["validity"] for v in row if not v))
        warnings = [STATUS_BLOCK,
                    f"Shaded areas are {BAND_LABEL}."] + inp["clamp_notes"]
        if inp["show_raw_ohlc"]:
            rows = []
            for i in range(M):
                for j in range(H):
                    rows.append([i + 1, dates[j],
                                 round(res["open_paths"][i][j], 6),
                                 round(res["high_paths"][i][j], 6),
                                 round(res["low_paths"][i][j], 6),
                                 round(closes[i][j], 6),
                                 "OK" if res["validity"][i][j] else "INVALID BAR"])
            tables.append(make_table(
                "Kronos Raw Sampled OHLC (EXPERIMENTAL -- bars may be "
                "structurally invalid)",
                ["Path", "Date", "Open", "High", "Low", "Close", "Bar Validity"],
                rows))
            warnings.append(
                f"Raw OHLC: {n_invalid} of {M * H} sampled bars are structurally "
                f"invalid (e.g. high < max(open, close)) -- a known model "
                f"property; only CLOSE paths are rendered as forecasts.")

        end_med = float(qs[50][-1])
        chg = 100.0 * (end_med / last_close - 1.0)
        plain = (f"{STATUS_BLOCK} Median sampled close at day {H}: "
                 f"{end_med:.4f} ({chg:+.2f}% vs the last input close). "
                 f"Bands are {BAND_LABEL}.")

        progress_callback("Done", 100)
        return make_response(
            ctx, tables=tables, plain_english_summary=plain, warnings=warnings,
            audit_fields={
                "experimental": True, "status_block": STATUS_BLOCK,
                "band_label": BAND_LABEL, "pins": res["pins"],
                "lookback_L": L, "horizon_H": H, "paths_M": M, "seed": seed,
                "T": T_FIXED, "top_p": TOP_P_FIXED,
                "n_input_rows": int(len(inp["df"])),
                "invalid_ohlc_bars": n_invalid, "total_bars": M * H,
                "timings": res["timings"], "wall_s": round(wall, 1),
                "clamp_notes": inp["clamp_notes"],
            },
            charting_suggestions=(
                "Fan chart: line = 'Median Close'; shaded bands P10-P90 and "
                "P25-P75 from 'Kronos Forecast Summary'. Title the shading "
                f"EXACTLY: '{BAND_LABEL}'."))
    except Exception as e:  # noqa: BLE001 -- the bespoke catch-all, breakeven-style
        return make_error_response(
            ctx, f"Kronos Forecast failed: {e}",
            error_fixes=["Check the kronos_input sheet and the Kronos "
                         "environment (KRONOS_TSL_HANDOFF.md)."])
