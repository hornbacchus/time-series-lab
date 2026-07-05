"""Kronos Forecast (Bespoke #3, EXPERIMENTAL) -- cross-source REPRODUCTION check.

★ HONEST FRAMING (the check's entire claim): this is a REPRODUCTION of a
characterized artifact -- NOT validation of forecast skill. The Kronos
evaluation program (KXAF_CLOSEOUT_MEMO.md, Kronos repo @ 68dcff9) found NO
confirmed predictive or distributional value out-of-sample (Jul 2025 - Jun
2026); that record is carried, not contradicted, by this check. What IS
validated: the TSL integration's runner (engine/techniques/kronos_forecast/
runner.py) produces the SAME (M, H) close-path matrix as the evaluation
program's own forecaster (kxaf/forecaster.py rollout_paths_batched) under the
same seed, pins, and inputs -- i.e., the tool faithfully reproduces the
characterized artifact, byte-for-byte AS A BATCH (both sides seed once and run
ONE predict_batch of M x sample_count=1; chunking would change the path set).

GRACEFUL SKIP (part of the contract): the pinned Kronos venv, the HF cache,
and the Kronos repo live on the owner's box (C:\\KronosDev + the OneDrive
repo). On any runner/CI host without those assets this check returns SKIP
with the missing-asset reason -- never ERROR; a false red is worse than an
honest skip.

tier = "slow": never wired into the fast CI lane (two model loads ~= 25-30s +
sampling; ~60-90s total at the bounded M=2/H=5 load).
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder

_KRONOS_REPO = os.environ.get(
    "TSL_KRONOS_REPO",
    r"C:\Users\matth\OneDrive\Projects\Kronos Cross-Asset Forecaster")
# kxaf EVALUATION-repo dormancy-HEAD pin (post-closure audit, 2026-07-05): recorded metadata for
# the eval-repo commit whose kxaf/forecaster.py rollout_paths_batched this check reproduces (verified
# byte-identical, max_abs_diff 0.0, at re-pin time). This is NOT the shiyu-coder upstream MODEL commit
# (_dispatch.PINS["upstream_commit"] = 67b630e6 -- a different repository, asserted by runner.py) --
# that pin is unchanged. Recorded, not repo-read; the owner confirmed the checkout at this commit.
_KRONOS_EVAL_REPO_COMMIT = "0771cc3288ddf8922074843b4801361744c1d84f"
_M, _H, _L, _SEED = 2, 5, 120, 9000


class KronosReproductionParity(P3ParityCheck):
    """TSL kronos runner vs kxaf.forecaster.rollout_paths_batched -- same
    seed/pins/inputs -> the same (M, H) close matrix, AS A BATCH."""

    technique_id = "p3_kronos_reproduction"
    tier = "slow"
    fixture_id = ""

    verdict_class = "dl_seed_pinned"
    verdict_class_rationale = (
        "Seed-pinned torch sampling: both arms seed the global RNGs once "
        "(random/numpy/torch.manual_seed) and run ONE predict_batch of M x "
        "sample_count=1 against the SAME pinned artifact (upstream 67b630e6; "
        "model 2b554741; tokenizer 0e011738; torch 2.12.0+cpu in the pinned "
        "venv), so the close matrices must agree to machine precision. This "
        "REPRODUCES the characterized artifact across two independent wrapper "
        "implementations (the TSL runner vs the evaluation program's "
        "kxaf/forecaster.py); it does NOT validate forecast skill -- the "
        "evaluation record (KXAF_CLOSEOUT_MEMO.md) found none, and the tool "
        "ships EXPERIMENTAL by design."
    )

    # ---- asset availability (the SKIP contract) ----
    def _missing_assets(self):
        from techniques.kronos_forecast import _dispatch as kd  # type: ignore
        missing = []
        if not os.path.exists(kd.KRONOS_PYTHON):
            missing.append(f"venv python ({kd.KRONOS_PYTHON})")
        if not os.path.isdir(kd.KRONOS_UPSTREAM):
            missing.append(f"upstream clone ({kd.KRONOS_UPSTREAM})")
        if not os.path.isdir(kd.KRONOS_HF_HOME):
            missing.append(f"HF cache ({kd.KRONOS_HF_HOME})")
        csv = os.path.join(_KRONOS_REPO, "data", "examples", "IEF_sample_250.csv")
        if not os.path.exists(csv):
            missing.append(f"Kronos repo example data ({csv})")
        return missing, csv

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        # The fixture is the lineage-verified IEF extract (static, committed in
        # the Kronos repo); the seed argument is unused -- the reproduction is
        # pinned at the production seed 9000 by contract.
        return {}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        missing, csv = self._missing_assets()
        if missing:
            return {"skip": "; ".join(missing)}
        from techniques.kronos_forecast import _dispatch as kd  # type: ignore
        import pandas as pd
        df = pd.read_csv(csv)
        td = tempfile.mkdtemp(prefix="tsl_krepro_")
        in_csv = os.path.join(td, "in.csv")
        df[["timestamps", "open", "high", "low", "close", "volume"]].to_csv(
            in_csv, index=False)
        out = os.path.join(td, "out.json")
        req = {"csv_path": in_csv, "L": _L, "H": _H, "M": _M, "seed": _SEED,
               "T": 0.6, "top_p": 0.90, "hf_home": kd.KRONOS_HF_HOME,
               "upstream_dir": kd.KRONOS_UPSTREAM, "expected": kd.PINS,
               "out_path": out}
        rp = os.path.join(td, "req.json")
        json.dump(req, open(rp, "w"))
        runner = os.path.join(os.path.dirname(os.path.abspath(kd.__file__)),
                              "runner.py")
        proc = subprocess.run([kd.KRONOS_PYTHON, runner, rp],
                              capture_output=True, text=True, timeout=600)
        res = json.load(open(out, encoding="utf-8"))
        if res.get("status") != "ok":
            raise RuntimeError(f"TSL runner failed: {res}")
        return {"matrix": res["close_paths"], "pins": res["pins"],
                "stderr_tail": (proc.stderr or "")[-200:]}

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        missing, csv = self._missing_assets()
        if missing:
            return {"skip": "; ".join(missing)}
        from techniques.kronos_forecast import _dispatch as kd  # type: ignore
        # READ-ONLY invocation of the evaluation program's own forecaster, in
        # the SAME pinned venv: kxaf.forecaster.rollout_paths_batched (seed
        # once -> ONE predict_batch).
        script = f"""
import json, os, sys
import pandas as pd
os.environ.setdefault("HF_HOME", {kd.KRONOS_HF_HOME!r})
os.environ.setdefault("HF_HUB_OFFLINE", "1")
sys.path.insert(0, {_KRONOS_REPO!r})
from kxaf.forecaster import KronosForecaster
df = pd.read_csv({csv!r})
x_df = df.iloc[-{_L}:][["open","high","low","close","volume"]].reset_index(drop=True)
x_ts = pd.to_datetime(df["timestamps"]).iloc[-{_L}:].reset_index(drop=True)
y_ts = pd.Series(pd.bdate_range(x_ts.iloc[-1], periods={_H}+1)[1:])
f = KronosForecaster()   # defaults ARE the pins + T=0.6/top_p=0.90
paths, tally = f.rollout_paths_batched(x_df, x_ts, y_ts, H_max={_H}, M={_M}, base_seed={_SEED})
print(json.dumps({{"matrix": paths.tolist(), "tally": tally}}))
"""
        proc = subprocess.run([kd.KRONOS_PYTHON, "-c", script],
                              capture_output=True, text=True, timeout=600)
        if proc.returncode != 0:
            raise RuntimeError(f"reference arm failed: {proc.stderr[-300:]}")
        body = json.loads(proc.stdout.strip().splitlines()[-1])
        ladder = get_ladder(self.technique_id)
        return {"matrix": body["matrix"],
                "abs_tol": float(ladder["default"]["abs_tol"])}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        if "skip" in tsl or "skip" in ref:
            reason = tsl.get("skip") or ref.get("skip")
            return ParityResult(
                technique_id=self.technique_id, outcome="SKIP",
                metrics={"primary": {"reproduction": {"status": "SKIP",
                                                      "missing": reason}}},
                diagnostics={"scope": "Kronos assets absent on this host -- "
                                      "the reproduction runs on the owner's box only."})
        a = np.array(tsl["matrix"], dtype=float)
        b = np.array(ref["matrix"], dtype=float)
        if a.shape != b.shape:
            status, max_abs = "BLOCK", float("inf")
        else:
            max_abs = float(np.max(np.abs(a - b)))
            status = "PASS" if max_abs <= ref["abs_tol"] else "BLOCK"
        primary = {"reproduction": {
            "status": status, "shape": list(a.shape),
            "max_abs_diff": max_abs, "abs_tol": ref["abs_tol"],
            "note": ("TSL runner == kxaf/forecaster.py rollout_paths_batched, "
                     "same seed/pins, AS A BATCH -- a REPRODUCTION of the "
                     "characterized artifact, NOT forecast-skill validation")}}
        return ParityResult(
            technique_id=self.technique_id,
            outcome="PASS" if status == "PASS" else "BLOCK",
            metrics={"primary": primary},
            diagnostics={"pins": tsl.get("pins", {}),
                         "kxaf_eval_repo_commit": _KRONOS_EVAL_REPO_COMMIT,
                         "load": f"M={_M}, H={_H}, L={_L}, seed={_SEED}"})
