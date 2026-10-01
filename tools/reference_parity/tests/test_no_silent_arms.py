"""No silent arms (H1): output-level negative controls for 3e_mint_family.

A reference arm that cannot run must be reported (CAVEAT for the secondary
hierarchicalforecast arm, ERROR for the engine arm), never left absent under
a PASS. Each test runs the REAL check end to end through the runner
(run_check: TSL + R hts + hierarchicalforecast + compare) and forces one
failure. The first test is the positive control: untouched, the check is a
clean PASS with every hierarchicalforecast member actually compared, so each
forced failure below is a discrimination, not a check that never passes.

Before H1, the hierarchicalforecast arm raised a TypeError on every run (a
reconcile(S=...) call no 1.5.x accepts) and the check still reported PASS.

Run (repo root; PYTHONPATH=tools):
    python -m unittest discover -s tools/reference_parity/tests -p "test_*.py"
Needs R with hts (as the fast tier does). A check that SKIPs FAILS these
tests - a skipped control would pass the gate without running - except for
"R unavailable" on a machine outside CI (env CI unset).
"""

from __future__ import annotations

import os
import unittest
from unittest import mock

import numpy as np

from reference_parity.harness.checks import mint_family
from reference_parity.harness.checks.mint_family import MintFamilyParity
from reference_parity.harness.manifest import Manifest
from reference_parity.harness.runner import run_check

HF_METHODS = ("ols", "wls_variance", "mint_shrinkage")


def _run():
    return run_check(MintFamilyParity(), seed=42, manifest=Manifest.load())


def _refuse_to_skip(result):
    """A SKIPped check means the controls cannot run: fail, unless R itself is
    unavailable on a developer machine (never in CI, which installs R)."""
    if result.outcome != "SKIP":
        return
    if str(result.error).startswith("R unavailable") and not os.environ.get("CI"):
        raise unittest.SkipTest(f"{result.technique_id}: {result.error}")
    raise AssertionError(f"{result.technique_id} did not run (SKIP): {result.error}")


class NoSilentArmsMintFamily(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.baseline = _run()
        _refuse_to_skip(cls.baseline)

    def assertNotCleanPass(self, result, expected_outcome, needle):
        self.assertEqual(result.outcome, expected_outcome, result.diagnostics)
        reasons = " | ".join(result.diagnostics.get("not_clean", []))
        self.assertIn(needle, reasons)

    def test_0_positive_control_clean_pass_with_hf_compared(self):
        r = self.baseline
        self.assertEqual(r.outcome, "PASS", r.diagnostics)
        self.assertEqual(r.diagnostics.get("not_clean"), [])
        for m in HF_METHODS:
            self.assertEqual(r.metrics[m]["hf"]["status"], "PASS", m)
            self.assertLess(r.metrics[m]["hf"]["max_abs_diff"], 1e-12, m)
        self.assertEqual(r.metrics["mint_sample"]["status"], "expected_rank_deficient")

    def test_1_hf_arm_raises_is_caveat(self):
        with mock.patch.object(MintFamilyParity, "_run_hf",
                               side_effect=RuntimeError("forced: HF arm down")):
            r = _run()
        self.assertNotCleanPass(r, "CAVEAT", "hierarchicalforecast arm did not run")
        for m in HF_METHODS:
            self.assertEqual(r.metrics[m]["hf"]["status"], "unavailable", m)

    def test_2_hf_api_drift_is_caveat(self):
        # The exact failure CI hit: reconcile() rejecting a keyword.
        from hierarchicalforecast.core import HierarchicalReconciliation
        with mock.patch.object(
            HierarchicalReconciliation, "reconcile",
            side_effect=TypeError("reconcile() got an unexpected keyword argument 'S_df'"),
        ):
            r = _run()
        self.assertNotCleanPass(r, "CAVEAT", "unexpected keyword argument")

    def test_3_hf_disagreement_is_caveat(self):
        real = MintFamilyParity._run_hf

        def perturbed(self, fixture, n_total, h):
            out = real(self, fixture, n_total, h)
            return {k: (v + 1e-3 if isinstance(v, np.ndarray) else v) for k, v in out.items()}

        with mock.patch.object(MintFamilyParity, "_run_hf", perturbed):
            r = _run()
        self.assertNotCleanPass(r, "CAVEAT", "beyond the ladder")

    def test_4_engine_arm_failure_is_error(self):
        mint_family._ensure_engine_on_path()
        from techniques import forecast_reconciliation as fr
        orig = fr._estimate_W_matrix

        def boom(residuals, method):
            if method == "ols":
                raise ValueError("forced: engine arm down")
            return orig(residuals, method)

        with mock.patch.object(fr, "_estimate_W_matrix", boom):
            r = _run()
        self.assertNotCleanPass(r, "ERROR", "the TSL engine failed")
        self.assertIn("forced: engine arm down", r.error)

    # The documented B1 refusal (mint_sample) is accepted only in its exact
    # form and only while both references refuse too.

    def test_5_hts_stops_refusing_is_caveat(self):
        real = MintFamilyParity.run_reference

        def finite_sam(self, fixture):
            out = real(self, fixture)
            out["hts"]["mint_sample"] = np.ones_like(out["hts"]["mint_sample"])
            return out

        with mock.patch.object(MintFamilyParity, "run_reference", finite_sam):
            r = _run()
        self.assertNotCleanPass(r, "CAVEAT", "hts returned finite output")

    def test_6_hf_stops_refusing_is_caveat(self):
        real = MintFamilyParity._run_hf

        def hf_sam_result(self, fixture, n_total, h):
            out = real(self, fixture, n_total, h)
            out["mint_sample"] = np.zeros((n_total, h))
            return out

        with mock.patch.object(MintFamilyParity, "_run_hf", hf_sam_result):
            r = _run()
        self.assertNotCleanPass(r, "CAVEAT", "did not refuse mint_cov")

    def test_7_engine_fallback_refusal_is_error(self):
        mint_family._ensure_engine_on_path()
        from techniques import forecast_reconciliation as fr
        orig = fr._estimate_W_matrix

        def fallback(residuals, method):
            if method == "mint_sample":
                raise fr.RankDeficientWMatrixError(
                    "W matrix rank check raised; treating as rank-deficient "
                    "(fallback to next cascade method).")
            return orig(residuals, method)

        with mock.patch.object(fr, "_estimate_W_matrix", fallback):
            r = _run()
        self.assertNotCleanPass(r, "ERROR", "the TSL engine failed")


class NoSilentArmsConformalMapie(unittest.TestCase):
    """p3_conformal_cqr / p3_conformal_enbpi: MAPIE is the only independent
    package arm. A MAPIE failure was caught, noted as "SKIP" in the metrics,
    and the check still reported PASS (enbpi did exactly that in CI, where
    MAPIE was never installed). H1's one-line fix: CAVEAT when the MAPIE
    result is absent."""

    CASES = (
        ("p3_conformal_cqr", "ConformalizedQuantileRegressor"),
        ("p3_conformal_enbpi", "TimeSeriesRegressor"),
    )

    @staticmethod
    def _run(tid):
        from reference_parity.harness.runner import discover_checks
        return run_check(discover_checks()[tid](), seed=42, manifest=Manifest.load())

    def test_positive_control_and_forced_mapie_failure(self):
        import mapie.regression
        for tid, cls_name in self.CASES:
            with self.subTest(check=tid):
                clean = self._run(tid)
                _refuse_to_skip(clean)
                self.assertEqual(clean.outcome, "PASS", clean.metrics)
                self.assertEqual(clean.metrics["primary"]["crosspkg_width_ratio"]["status"], "PASS")

                def refuse(*args, **kwargs):
                    raise RuntimeError("forced: MAPIE arm down")

                with mock.patch.object(mapie.regression, cls_name, refuse):
                    forced = self._run(tid)
                self.assertEqual(forced.outcome, "CAVEAT", forced.metrics)
                self.assertIn("forced: MAPIE arm down",
                              forced.metrics["primary"]["crosspkg_width_ratio"]["note"])


if __name__ == "__main__":
    unittest.main()
