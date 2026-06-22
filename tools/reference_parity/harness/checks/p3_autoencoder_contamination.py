"""Phase 3 batch C — autoencoder_anomaly contamination expose discrimination.

Batch C removed the fake `threshold_sigma` control (the engine never read it; it
uses a percentile threshold via `contamination`, not a sigma z-score) and newly
exposed the engine's REAL threshold knob `contamination` (autoencoder_anomaly.py
reads it, default 0.05, and sets the reconstruction-error percentile threshold).

This check proves the newly-exposed control has effect: at two distinct
contamination values the flagged-anomaly set / output differs. A no-effect result
would mean the expose was wrong.
"""

from __future__ import annotations

import hashlib
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.path_setup import _ensure_engine_on_path


def _digest(res: dict) -> str:
    vals = []
    for t in res.get("tables", []) or []:
        for row in t.get("rows", []) or []:
            for c in row:
                if isinstance(c, (int, float)) and not isinstance(c, bool):
                    vals.append(round(float(c), 5))
    a = res.get("audit_fields", {}) or {}
    for k in sorted(a):
        if isinstance(a[k], (int, float)) and not isinstance(a[k], bool):
            vals.append(round(float(a[k]), 5))
    return hashlib.sha1(",".join(map(str, vals)).encode()).hexdigest()[:12]


class AutoencoderContaminationParity(P3ParityCheck):
    technique_id = "p3_autoencoder_contamination"
    tier = "fast"
    fixture_id = ""
    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Expose discrimination for autoencoder_anomaly contamination (the engine's "
        "real percentile-threshold knob, newly exposed after the fake "
        "threshold_sigma was removed). Two distinct contamination values must "
        "produce different anomaly output -> the control has effect."
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        rng = np.random.default_rng(5)
        x = np.zeros(180)
        for t in range(1, 180):
            x[t] = 0.6 * x[t - 1] + rng.standard_normal()
        y = x + np.concatenate([np.zeros(170), 6 * np.ones(10)])
        return {"y": y.tolist()}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.autoencoder_anomaly as ae  # type: ignore

        y = fixture["y"]

        def run(contam):
            ctx = RunContext({"run_id": "p3_contam", "technique_id": "autoencoder_anomaly",
                              "preset": "Balanced", "seed": 42, "frequency": "",
                              "time": list(range(len(y))),
                              "series": [{"name": "y", "values": y}],
                              "params": {"epochs": 30, "window_size": 10, "contamination": contam}})
            return ae.run(ctx, lambda *a, **k: None)
        r1, r2 = run(0.02), run(0.15)
        return {"ok": r1.get("status") == "success" and r2.get("status") == "success",
                "differs": _digest(r1) != _digest(r2)}

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        return {"expected": "contamination changes the anomaly output"}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        passed = bool(tsl["ok"] and tsl["differs"])
        return ParityResult(
            technique_id=self.technique_id,
            outcome="PASS" if passed else "BLOCK",
            metrics={"primary": {"contamination_has_effect": {
                "status": "PASS" if passed else "BLOCK", "differs": tsl["differs"]}}},
            diagnostics={"run_ok": tsl["ok"]},
        )
