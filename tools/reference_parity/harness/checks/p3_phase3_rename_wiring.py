"""Phase 3 batch A — inert-control rename WIRING discrimination (8 controls).

Eight dialog controls were inert because the catalog key did not match the
engine's get_param key (the user's setting was silently dropped). The fix renamed
each catalog key to the engine key it already reads. This check proves each
renamed control now reaches the engine AND the engine ACTS on the value: it runs
each technique at two distinct values of the (now-aligned) key and asserts the
output differs. A control that does not change the output would mean the
disposition was wrong (the engine reads-but-ignores) -> BLOCK.

Renames covered (catalog key -> engine key):
  tar_setar max_lag->ar_order; nar_narx max_lag->ar_lags, hidden_size->hidden_layers;
  fft_spectrum top_n->n_top; stl_decompose seasonal_window->seasonal;
  autoencoder_anomaly encoding_dim->hidden_dim; rolling_origin_cv n_folds->folds;
  bocpd hazard_rate->hazard_lambda.

The structural alignment (catalog name == engine key) is separately enforced by
catalog_key_alignment; this check is the BEHAVIORAL proof (the control has effect).
"""

from __future__ import annotations

import hashlib
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.path_setup import _ensure_engine_on_path


def _ar(n: int, phi: float, seed: int) -> list:
    r = np.random.default_rng(seed)
    e = r.standard_normal(n)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + e[t]
    return x.tolist()


def _digest(res: dict) -> str:
    vals = []
    for t in res.get("tables", []) or []:
        for row in t.get("rows", []) or []:
            for c in row:
                if isinstance(c, (int, float)) and not isinstance(c, bool):
                    vals.append(round(float(c), 6))
    a = res.get("audit_fields", {}) or {}
    for k in sorted(a):
        if isinstance(a[k], (int, float)) and not isinstance(a[k], bool):
            vals.append(round(float(a[k]), 6))
    return hashlib.sha1((",".join(map(str, vals))).encode()).hexdigest()[:16]


class Phase3RenameWiringParity(P3ParityCheck):
    technique_id = "p3_phase3_rename_wiring"
    tier = "fast"
    fixture_id = ""
    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Self-contained wiring discrimination: each renamed inert control must, "
        "now that its catalog key matches the engine's get_param key, change the "
        "engine's (deterministic) output when set to two distinct values. No "
        "external reference -- a control whose output is invariant to its value "
        "means the engine reads-but-ignores it (wrong disposition) -> BLOCK."
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        rng = np.random.default_rng(0)
        return {
            "seas": (50 + 0.2 * np.arange(120)
                     + 8 * np.sin(2 * np.pi * np.arange(120) / 12)
                     + rng.standard_normal(120)).tolist(),
            "tm12": [f"{2010 + i // 12}-{(i % 12) + 1:02d}-01" for i in range(120)],
            "cps": np.concatenate([rng.standard_normal(100),
                                   5 + rng.standard_normal(100)]).tolist(),
            "fft": (np.sin(2 * np.pi * np.arange(256) * 0.05)
                    + 0.5 * np.sin(2 * np.pi * np.arange(256) * 0.12)
                    + 0.3 * np.sin(2 * np.pi * np.arange(256) * 0.20)
                    + 0.2 * rng.standard_normal(256)).tolist(),
            "arx": _ar(180, 0.6, 1),
        }

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import importlib

        seas, tm12, cps, fft, arx = (fixture["seas"], fixture["tm12"],
                                     fixture["cps"], fixture["fft"], fixture["arx"])
        ae = (np.asarray(arx) + np.concatenate([np.zeros(170), 6 * np.ones(10)])).tolist()
        # (label, technique, engine_key, v1, v2, values, base_params, time, freq)
        controls = [
            ("tar_setar:ar_order", "tar_setar", "ar_order", 1, 3, arx, {}, None, ""),
            ("nar_narx:ar_lags", "nar_narx", "ar_lags", 1, 5, arx, {"epochs": 40}, None, ""),
            ("nar_narx:hidden_layers", "nar_narx", "hidden_layers", 8, 40, arx, {"epochs": 40}, None, ""),
            ("fft_spectrum:n_top", "fft_spectrum", "n_top", 2, 6, fft, {}, None, ""),
            ("stl_decompose:seasonal", "stl_decompose", "seasonal", 7, 25, seas, {}, tm12, "M"),
            ("autoencoder_anomaly:hidden_dim", "autoencoder_anomaly", "hidden_dim", 4, 16, ae,
             {"epochs": 30, "window_size": 10}, None, ""),
            ("rolling_origin_cv:folds", "rolling_origin_cv", "folds", 2, 4, seas, {"horizon": 4}, tm12, "M"),
            ("bocpd:hazard_lambda", "bocpd", "hazard_lambda", 50, 500, cps, {}, None, ""),
        ]
        out = {}
        for label, tid, key, v1, v2, vals, base, time, freq in controls:
            mod = importlib.import_module("techniques." + tid)
            n = len(vals)
            tcol = time if time is not None else list(range(n))

            def run(v):
                p = dict(base); p[key] = v
                ctx = RunContext({"run_id": "p3_phase3", "technique_id": tid, "preset": "Balanced",
                                  "seed": 42, "frequency": freq, "time": tcol,
                                  "series": [{"name": "y", "values": vals}], "params": p})
                return mod.run(ctx, lambda *a, **k: None)
            r1, r2 = run(v1), run(v2)
            out[label] = {
                "ok": r1.get("status") == "success" and r2.get("status") == "success",
                "differs": _digest(r1) != _digest(r2),
                "status": (r1.get("status"), r2.get("status")),
            }
        return out

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        return {"expected": "every renamed control changes the output"}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        primary = {}
        for label, r in tsl.items():
            has_effect = bool(r["ok"] and r["differs"])
            primary[label] = {"status": "PASS" if has_effect else "BLOCK",
                              "differs": r["differs"], "run_status": r["status"]}
        outcome = "BLOCK" if any(v["status"] == "BLOCK" for v in primary.values()) else "PASS"
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={"n_controls": len(tsl),
                         "all_have_effect": outcome == "PASS"},
        )
