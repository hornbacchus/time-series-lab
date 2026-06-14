"""Regression guard: BYF must reject n_draws <= n_burn at VALIDATION, not deep in the fit.

Station-A acceptance P2-11: a user ran Bond Yield Forecast with MCMC Draws=1000,
Burn-in=3000 (draws lowered for a quick run; burn-in left at the 3000 default).
Both values are independently in-bounds, so the pre-flight bounds loop passed —
and the run then failed 35% into "Fitting BVAR-SV" with the deep, cryptic
``ValueError: n_draws must exceed n_burn`` (estimation.py, BVARSV.__init__),
after the workbook read + PCA panel. n_draws is the TOTAL incl. burn-in, so it
must exceed n_burn; that constraint is knowable at input time and belongs at
validation.

This guard has three parts:

  1. The 5% pre-flight cross-field check (``_preflight_validate_params``) catches
     the case where the user set BOTH params (the reported case).
  2. The effective-value inversion: lowering ONLY draws leaves burn at the 3000
     default, so the params-only check can't see it — the post-merge check in
     run() compares the merged config and is the complete guard.
  3. run()-level: an inverted pair returns a clean validation error with the
     actionable message, NOT the deep BVARSV ValueError.

Run:
    pytest engine/tests/test_byf_draws_burn_validation.py -v
"""
import os
import sys
import unittest

_ENGINE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)

# Light import — BVARSV / numba / workbook readers are deferred inside run().
from techniques.bond_yield_forecast._dispatch import (  # noqa: E402
    _preflight_validate_params,
)
from techniques.base import RunContext  # noqa: E402

_CLEAR_MSG = "must be less than MCMC Draws"   # the actionable validation message
_DEEP_MSG = "must exceed n_burn"              # the deep BVARSV ValueError (what we replace)

_TEMPLATE = os.path.join(
    _ENGINE_DIR, "techniques", "bond_yield_forecast", "resources",
    "templates", "bond_yield_forecast_input_template.xlsx",
)


class TestPreflightCrossField(unittest.TestCase):
    """The 5% pre-flight check rejects an inverted draws/burn pair (both set)."""

    def test_inverted_pair_rejected(self):
        errs = _preflight_validate_params({"n_draws": 1000, "n_burn": 3000})
        self.assertTrue(
            any(_CLEAR_MSG in e for e in errs),
            f"expected a cross-field rejection; got {errs}",
        )

    def test_equal_pair_rejected(self):
        # n_draws must strictly exceed n_burn (BVARSV uses <=).
        errs = _preflight_validate_params({"n_draws": 2000, "n_burn": 2000})
        self.assertTrue(any(_CLEAR_MSG in e for e in errs), errs)

    def test_valid_pairs_pass(self):
        for nd, nb in ((10000, 3000), (4000, 1000)):
            errs = _preflight_validate_params({"n_draws": nd, "n_burn": nb})
            self.assertFalse(
                any(_CLEAR_MSG in e for e in errs),
                f"valid pair ({nd},{nb}) should not be flagged; got {errs}",
            )


class TestEffectivePartialOverride(unittest.TestCase):
    """Lowering ONLY draws inverts against the 3000 default burn-in — the reason
    the complete check runs on the merged (effective) config, not just params."""

    def test_partial_override_inverts_against_default_burn(self):
        try:
            from techniques.bond_yield_forecast.data import load_config
            from techniques.bond_yield_forecast._paths import package_default_config
            from techniques.bond_yield_forecast._dispatch import _apply_param_overrides
        except ImportError as e:
            self.skipTest(f"BYF config deps unavailable: {e}")
        config = load_config(package_default_config())
        self.assertEqual(int(config["estimation"]["n_burn"]), 3000,
                         "default burn-in expected 3000")
        merged = _apply_param_overrides(config, {"n_draws": 1000})
        nd = int(merged["estimation"]["n_draws"])
        nb = int(merged["estimation"]["n_burn"])
        self.assertEqual(nd, 1000)
        self.assertEqual(nb, 3000)
        self.assertLessEqual(nd, nb, "partial override should invert the effective pair")


class TestRunLevelCleanError(unittest.TestCase):
    """run() with an inverted pair returns the clean validation message, not the
    deep BVARSV ValueError. Fires at config-merge (12%), before the workbook read."""

    def _run(self, params):
        import techniques.bond_yield_forecast._dispatch as byf
        p = {"input_workbook": _TEMPLATE}
        p.update(params)
        return byf.run(RunContext({"run_id": "byf_guard", "technique_id": "bond_yield_forecast",
                                   "preset": "Balanced", "params": p}), lambda *a, **k: None)

    def test_partial_override_clean_validation_error(self):
        if not os.path.exists(_TEMPLATE):
            self.skipTest("BYF input template not found")
        resp = self._run({"n_draws": 1000})  # burn-in defaults to 3000
        msg = str(resp.get("error") or resp.get("error_message") or "")
        if "subpackage import failed" in msg:
            self.skipTest("BYF runtime deps (numba/openpyxl) unavailable")
        self.assertEqual(resp.get("status"), "failure", msg)
        self.assertIn(_CLEAR_MSG, msg, f"expected clean validation message; got: {msg}")
        self.assertNotIn(_DEEP_MSG, msg, f"should not reach the deep BVARSV ValueError; got: {msg}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
