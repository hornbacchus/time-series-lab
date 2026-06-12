"""Kronos inference runner -- EXECUTED BY THE PINNED KRONOS VENV, not by TSL's
engine Python (three incompatible interpreters: TSL packed 3.11 / dev 3.14 /
the Kronos artifact 3.12 + torch 2.12.0+cpu). Standalone by design: imports
only stdlib + the venv's numpy/pandas/torch + the VENDORED upstream
(sys.path -- never pip-installed). Protocol: argv[1] = request JSON
{csv_path, L, H, M, seed, T, top_p, hf_home, upstream_dir, expected:{...},
out_path}; writes the response JSON to out_path and prints stage lines to
stdout (the dispatch relays them as progress).

PINS-ASSERT FIRST (structured error, never a silent fallback): the upstream
clone commit, the model/tokenizer HF revisions (enforced via
from_pretrained(revision=...) under HF_HUB_OFFLINE), and the torch version
must match the characterized artifact (KRONOS_TSL_HANDOFF.md SS1).

Determinism: ONE predict_batch of M copies at sample_count=1 under one global
seed -- per-path retention per the handoff (sample_count=M would AVERAGE);
batched draws are reproducible AS A BATCH, which is exactly what the K2
reproduction check formalizes. Do NOT chunk the batch for progress: chunking
changes the path set under the same seed.
"""

import json
import os
import random
import subprocess
import sys
import time


def _fail(stage, detail, out_path):
    body = {"status": "error", "stage": stage, "detail": str(detail)[:500]}
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(body, fh)
    print(f"KRONOS-RUNNER ERROR [{stage}]: {detail}", flush=True)
    sys.exit(2)


def main():
    req = json.load(open(sys.argv[1], encoding="utf-8"))
    out_path = req["out_path"]
    exp = req["expected"]

    os.environ.setdefault("HF_HOME", req["hf_home"])
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    sys.path.insert(0, req["upstream_dir"])

    # --- pins-assert FIRST ---
    try:
        head = subprocess.run(
            ["git", "-C", req["upstream_dir"], "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=30).stdout.strip()
        if not head.startswith(exp["upstream_commit"]):
            _fail("pins", f"upstream clone at {head[:12]}, expected "
                          f"{exp['upstream_commit']}*", out_path)
    except FileNotFoundError:
        _fail("pins", "git unavailable -- cannot verify the upstream pin", out_path)
    import torch  # noqa: E402  (venv import, after HF_HOME is set)
    if not torch.__version__.startswith(exp["torch_version"]):
        _fail("pins", f"torch {torch.__version__}, expected "
                      f"{exp['torch_version']}*", out_path)

    import numpy as np  # noqa: E402
    import pandas as pd  # noqa: E402
    try:
        from model import Kronos, KronosTokenizer, KronosPredictor  # noqa: E402
    except ImportError as e:
        _fail("vendoring", f"upstream import failed: {e}", out_path)

    print("KRONOS-RUNNER stage=load", flush=True)
    t0 = time.perf_counter()
    try:
        tok = KronosTokenizer.from_pretrained(
            "NeoQuasar/Kronos-Tokenizer-base", revision=exp["tokenizer_rev"])
        mdl = Kronos.from_pretrained(
            "NeoQuasar/Kronos-base", revision=exp["model_rev"])
    except Exception as e:
        _fail("pins", f"pinned HF revision unavailable offline: {e}", out_path)
    predictor = KronosPredictor(mdl, tok, device="cpu", max_context=512)
    load_s = time.perf_counter() - t0

    df = pd.read_csv(req["csv_path"])
    L, H, M = req["L"], req["H"], req["M"]
    feats = [c for c in ("open", "high", "low", "close", "volume") if c in df.columns]
    x_df = df.iloc[-L:][feats].reset_index(drop=True)
    x_ts = pd.to_datetime(df["timestamps"]).iloc[-L:].reset_index(drop=True)
    y_ts = pd.Series(pd.bdate_range(x_ts.iloc[-1], periods=H + 1)[1:])

    print(f"KRONOS-RUNNER stage=predict M={M} H={H}", flush=True)
    random.seed(req["seed"]); np.random.seed(req["seed"]); torch.manual_seed(req["seed"])
    t1 = time.perf_counter()
    preds = predictor.predict_batch(
        df_list=[x_df.copy() for _ in range(M)], x_timestamp_list=[x_ts] * M,
        y_timestamp_list=[y_ts] * M, pred_len=H, T=req["T"], top_k=0,
        top_p=req["top_p"], sample_count=1, verbose=False)
    predict_s = time.perf_counter() - t1

    def mat(col):
        return [[float(v) for v in p[col].to_numpy()] for p in preds]

    o, h, l, c = mat("open"), mat("high"), mat("low"), mat("close")
    validity = [[bool(h[i][j] >= max(o[i][j], c[i][j]) and
                      l[i][j] <= min(o[i][j], c[i][j]) and h[i][j] >= l[i][j])
                 for j in range(H)] for i in range(M)]

    body = {"status": "ok",
            "pins": {"upstream_commit": head, "model_rev": exp["model_rev"],
                     "tokenizer_rev": exp["tokenizer_rev"],
                     "torch_version": torch.__version__,
                     "python_version": sys.version.split()[0]},
            "y_dates": [d.strftime("%Y-%m-%d") for d in y_ts],
            "close_paths": c, "open_paths": o, "high_paths": h, "low_paths": l,
            "validity": validity,
            "timings": {"load_s": round(load_s, 2), "predict_s": round(predict_s, 2)}}
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(body, fh)
    print("KRONOS-RUNNER stage=done", flush=True)


if __name__ == "__main__":
    main()
