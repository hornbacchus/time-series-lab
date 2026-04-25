"""3c EVT Ferro-Segers extremal-index parity check.

Validates TSL's Ferro-Segers 2003 intervals estimator (used in
``evt_pot_gpd.py:_ferro_segers_extremal_index``) against R
``extRemes::extremalindex(method='intervals')`` on:

- **GARCH fixture** — clustered exceedances, theta < 1 expected.
- **iid fixture** — no clustering, theta near 1.0 expected.

Both fixtures use a pre-computed threshold (97.5th percentile of
absolute returns/data) passed to BOTH implementations. Per Q3,
threshold computation is held constant outside the parity test
to isolate the test to the Ferro-Segers math itself.

Phase 1 audit 3c (reports/3c_ferro_segers_audit.md) baseline:
GARCH theta diff 0.000e+00, iid theta diff 0.000e+00 — bitwise
match. Branch selection (the polynomial-form choice driven by
``max(T_i) <= 2`` vs ``> 2``) verified to match between TSL and
extRemes. Harness asserts the same.

Architectural decisions (locked in Session 3a design):

- **Q2.** Parity at 1e-6 absolute (TSL audit-field rounds to 6
  decimals); do NOT additionally assert ``theta > 0.9`` on iid.
  Parity IS the test.
- **Q3.** Threshold computed once outside both implementations
  and passed in as ``threshold_value`` (TSL) / ``threshold``
  (extRemes).

**TSL access.** TSL exposes ``extremal_index_theta`` (rounded to
6 decimals) and ``extremal_index_method`` (string e.g.
``"ferro_segers_2003 (T_i_form)"`` or ``"ferro_segers_2003
((T_i-1)(T_i-2)_form)"``). The branch label parses out of the
method string.
"""

from __future__ import annotations

import re
import sys
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityCheck, ParityResult
from reference_parity.harness.fixtures import FixtureLoader
from reference_parity.harness.manifest import Manifest
from reference_parity.harness.r_bridge import RBridge
from reference_parity.harness.tolerances import get_ladder


def _ensure_engine_on_path() -> None:
    import pathlib
    p = pathlib.Path(__file__).resolve()
    repo_root = None
    for parent in p.parents:
        if (parent / "engine").is_dir():
            repo_root = parent
            break
    if repo_root is None:
        raise RuntimeError(
            "Cannot locate engine/ from harness check module"
        )
    eng_path = str(repo_root / "engine")
    if eng_path not in sys.path:
        sys.path.insert(0, eng_path)


def _branch_from_max_t(max_t: int) -> str:
    """Phase 1 audit 3c branch-selection rule:
    max(T_i) <= 2 → T_i_form;  max(T_i) > 2 → (T_i-1)(T_i-2)_form.
    """
    return "T_i_form" if max_t <= 2 else "T_i_minus_1_T_i_minus_2_form"


class EvtFerroSegersParity(ParityCheck):
    """EVT extremal-index Ferro-Segers vs extRemes parity."""

    technique_id = "3c_evt_ferro_segers"
    tier = "fast"
    fixture_id = "3c_evt_garch"
    IID_FIXTURE_ID = "3c_evt_iid"

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        loader = FixtureLoader()
        # Phase 3.3: load() returns (data, metadata, sha).
        iid_data, _iid_metadata, iid_sha = loader.load(
            self.IID_FIXTURE_ID,
        )
        return {"iid": iid_data, "iid_sha": iid_sha}

    # -----------------------------------------------------------------
    # TSL side — invoke evt_pot_gpd wrapper with decluster=True
    # on each fixture.
    # -----------------------------------------------------------------

    def _run_tsl_one(
        self,
        data: np.ndarray,
        threshold_u: float,
        label: str,
    ) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext
        from techniques import evt_pot_gpd as evt
        T = len(data)
        ctx = RunContext({
            "run_id": f"parity_3c_{label}",
            "technique_id": "evt_pot_gpd",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "daily",
            "time": [f"d{i}" for i in range(T)],
            "series": [{"name": "x", "values": data.tolist()}],
            "params": {
                "threshold_value": float(threshold_u),
                "decluster": True,
                "tail": "upper",
            },
        })
        res = evt.run(ctx, lambda *a, **k: None)
        if res.get("status") != "success":
            return {
                "error": res.get("error_message", "TSL run failed"),
                "audit_status": res.get("status"),
            }
        a = res.get("audit_fields", {})
        theta = a.get("extremal_index_theta")
        method = a.get("extremal_index_method") or ""
        # Parse branch label from "ferro_segers_2003 (BRANCH_NAME)".
        # Branch labels can contain nested parens, e.g.
        # "((T_i-1)(T_i-2)_form)". Use greedy match anchored at
        # last close-paren to capture the full inner content.
        m = re.search(r"\((.+)\)\s*$", method)
        branch = m.group(1) if m else "unknown"
        return {
            "theta": (
                float(theta) if theta is not None else None
            ),
            "branch": branch,
            "method": method,
        }

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        # GARCH (main fixture)
        abs_r = np.asarray(fixture["abs_r"], dtype=np.float64)
        u_garch = float(np.asarray(fixture["threshold_u"]))
        garch = self._run_tsl_one(abs_r, u_garch, "garch")

        # iid
        iid_fx = fixture["iid"]
        abs_x = np.asarray(iid_fx["abs_x"], dtype=np.float64)
        u_iid = float(np.asarray(iid_fx["threshold_u"]))
        iid = self._run_tsl_one(abs_x, u_iid, "iid")

        return {"garch": garch, "iid": iid}

    # -----------------------------------------------------------------
    # Reference side: R extRemes::extremalindex
    # -----------------------------------------------------------------

    def _run_extremes_one(
        self,
        bridge: RBridge,
        data: np.ndarray,
        threshold_u: float,
    ) -> tuple[dict[str, Any], dict[str, str]]:
        r_code = r"""
            suppressPackageStartupMessages({ library(extRemes) })
            x <- as.numeric(read.csv("{{INPUT_x}}", header=FALSE)[, 1])
            u <- as.numeric(read.csv("{{INPUT_u}}", header=FALSE)[, 1])[1]

            # Ferro-Segers 2003 intervals estimator. extRemes
            # returns a numeric vector with named elements:
            #   [1] = extremal index theta
            #   [2] = number of clusters
            #   [3] = run length / cluster size
            result <- extremalindex(x, threshold = u,
                                     method = "intervals")
            theta <- as.numeric(result[1])

            # Inter-exceedance-time max for branch determination.
            # extRemes' branch selection is driven by max(T_i)
            # where T_i are the gaps between consecutive
            # exceedance positions: max(T_i) <= 2 → T_i_form;
            # max(T_i) > 2 → (T_i-1)(T_i-2) form.
            exceed_idx <- which(x > u)
            if (length(exceed_idx) >= 2) {
                gaps <- diff(exceed_idx)
                max_t <- max(gaps)
            } else {
                max_t <- NA
            }

            writeLines(sprintf("%.18e", theta), "{{OUTPUT_theta}}")
            writeLines(as.character(max_t), "{{OUTPUT_max_t}}")
        """
        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={
                "x": data.reshape(-1, 1),
                "u": np.array([[threshold_u]]),
            },
            output_names=["theta", "max_t"],
            timeout_sec=60,
            capture_versions_for=["extRemes"],
        )
        theta_arr = np.atleast_1d(outputs["theta"]).reshape(-1)
        max_t_arr = np.atleast_1d(outputs["max_t"]).reshape(-1)
        return (
            {
                "theta": float(theta_arr[0]),
                "max_t": int(max_t_arr[0])
                if np.isfinite(max_t_arr[0]) else None,
            },
            versions,
        )

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)

        abs_r = np.asarray(fixture["abs_r"], dtype=np.float64)
        u_garch = float(np.asarray(fixture["threshold_u"]))
        garch_out, versions = self._run_extremes_one(
            bridge, abs_r, u_garch,
        )

        iid_fx = fixture["iid"]
        abs_x = np.asarray(iid_fx["abs_x"], dtype=np.float64)
        u_iid = float(np.asarray(iid_fx["threshold_u"]))
        iid_out, _ = self._run_extremes_one(bridge, abs_x, u_iid)

        return {
            "garch": garch_out,
            "iid": iid_out,
            "extremes_version": versions.get("extRemes", "unknown"),
        }

    # -----------------------------------------------------------------
    # Compare
    # -----------------------------------------------------------------

    def compare(
        self,
        tsl: dict[str, Any],
        ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        metrics: dict[str, Any] = {}
        any_block = False

        for fxname, key_theta, key_branch in (
            ("garch", "theta_garch_vs_extremes",
             "polynomial_branch_consistency_garch"),
            ("iid",   "theta_iid_vs_extremes",
             "polynomial_branch_consistency_iid"),
        ):
            tsl_sub = tsl[fxname]
            ref_sub = ref[fxname]

            if "error" in tsl_sub:
                metrics[f"theta_{fxname}"] = {
                    "status": "BLOCK",
                    "error": tsl_sub["error"],
                }
                any_block = True
                continue

            tsl_theta = tsl_sub.get("theta")
            ref_theta = ref_sub.get("theta")
            if tsl_theta is None or ref_theta is None:
                metrics[f"theta_{fxname}"] = {
                    "status": "BLOCK",
                    "tsl_theta": tsl_theta,
                    "ref_theta": ref_theta,
                }
                any_block = True
                continue

            theta_tol = float(ladder[key_theta]["abs_tol"])
            theta_diff = abs(float(tsl_theta) - float(ref_theta))
            theta_rel = theta_diff / max(
                abs(float(tsl_theta)), abs(float(ref_theta)), 1e-300,
            )
            theta_rel_tol = float(ladder[key_theta]["rel_tol"])
            theta_ok = (
                theta_diff <= theta_tol or theta_rel <= theta_rel_tol
            )
            metrics[f"theta_{fxname}"] = {
                "status": "PASS" if theta_ok else "BLOCK",
                "tsl": float(tsl_theta),
                "ref": float(ref_theta),
                "abs_diff": theta_diff,
                "rel_diff": theta_rel,
                "tolerance": theta_tol,
            }
            if not theta_ok:
                any_block = True

            # Branch consistency: TSL parses the branch label;
            # extRemes doesn't expose its branch directly, so we
            # infer extRemes's branch from the same max(T_i) rule.
            tsl_branch = tsl_sub.get("branch", "unknown")
            ref_max_t = ref_sub.get("max_t")
            if ref_max_t is None:
                metrics[f"branch_{fxname}"] = {
                    "status": "BLOCK",
                    "note": "extRemes max_t not available",
                }
                any_block = True
                continue
            inferred_branch = _branch_from_max_t(int(ref_max_t))
            # TODO (future session): Both current fixtures (garch
            # T=2000, iid T=2000) land on the (T_i-1)(T_i-2)
            # bias-corrected branch. Phase 1 audit 3c specifically
            # flagged the max(T_i) <= 2 vs > 2 branch transition as
            # an edge case worth verifying. A third fixture
            # engineered to hit the T_i branch (very dense
            # exceedances) should be added to fully exercise both
            # Ferro-Segers polynomial branches. Without it, this
            # check confirms branch-label parity on one branch
            # only, not branch-decision rule equivalence between
            # TSL and extRemes.
            #
            # TSL emits one of:
            #   "T_i" (when max(T_i) <= 2 → simple form)
            #   "(T_i-1)(T_i-2)" (when max(T_i) > 2 → bias-
            #     corrected form)
            # Normalise to harness canonical labels.
            raw = tsl_branch.strip()
            if raw in ("T_i", "T_i_form"):
                tsl_branch_norm = "T_i_form"
            elif raw in (
                "(T_i-1)(T_i-2)",
                "(T_i-1)(T_i-2)_form",
                "T_i_minus_1_T_i_minus_2_form",
            ):
                tsl_branch_norm = "T_i_minus_1_T_i_minus_2_form"
            else:
                tsl_branch_norm = raw  # unknown; will fail below
            branch_ok = tsl_branch_norm == inferred_branch
            metrics[f"branch_{fxname}"] = {
                "status": "PASS" if branch_ok else "BLOCK",
                "tsl_branch_raw": tsl_branch,
                "tsl_branch_normalized": tsl_branch_norm,
                "ref_inferred_branch": inferred_branch,
                "ref_max_t": int(ref_max_t),
            }
            if not branch_ok:
                any_block = True

        outcome = "BLOCK" if any_block else "PASS"
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics=metrics,
            diagnostics={
                "extremes_version": ref.get(
                    "extremes_version", "unknown",
                ),
            },
        )
