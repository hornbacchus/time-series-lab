"""Regression guard: PELT exposed knobs (Fix B pilot) — n_bkps / min_size / penalty_value.

The Fix B PELT pilot exposed n_bkps (force an EXACT break count, overrides the
penalty), min_size (granularity), and upgraded penalty to a dropdown
{auto,bic,aic,mbic} plus a manual penalty_value float (overrides the dropdown).
This guard locks the contract:
  - n_bkps forces an EXACT count and overrides the penalty (with a disclosure);
  - the exact feasible bound K <= floor(n/min_size)-1, fail-fast out of range;
  - penalty_value precedence (numeric > dropdown) + the >0 fail-fast guard;
  - empty-string knobs behave as unset (the dialog sends "" for a blank textbox);
  - backward-compat: the default path (penalty unset == "auto") is unchanged.

Run:
    pytest engine/tests/test_pelt_knobs.py -v
"""
import os
import sys
import unittest

_ENGINE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)

import techniques.pelt_change_points as pelt  # noqa: E402
from techniques.base import RunContext  # noqa: E402

# Two clean mean-shift breaks (3 regimes); l2 is the canonical mean-shift cost.
THREE = [0.0] * 40 + [6.0] * 40 + [0.0] * 40   # n = 120


def _run(params):
    raw = {"technique_id": "pelt_change_points", "preset": "Balanced",
           "series": [{"name": "y", "values": THREE}], "params": params}
    return pelt.run(RunContext(raw), lambda *a, **k: None)


def _ncp(resp):
    for t in resp.get("tables") or []:
        if str(t.get("name", "")).startswith("Change Points"):
            return len(t["rows"])
    return None


def _err(resp):
    return str(resp.get("error") or resp.get("error_message") or "")


class TestNbkpsExactCount(unittest.TestCase):
    def test_exact_count(self):
        for k in (1, 2, 3):
            r = _run({"model": "l2", "n_bkps": k})
            self.assertEqual(r.get("status"), "success", _err(r))
            self.assertEqual(_ncp(r), k, f"n_bkps={k} should yield exactly {k}")

    def test_overrides_penalty_with_disclosure(self):
        r = _run({"model": "l2", "n_bkps": 2, "penalty": "mbic"})
        self.assertEqual(_ncp(r), 2)
        self.assertTrue(
            any("forced to 2" in w for w in (r.get("warnings") or [])),
            f"expected the n_bkps-overrides-penalty disclosure; got {r.get('warnings')}",
        )


class TestNbkpsBound(unittest.TestCase):
    def test_out_of_range_fails_fast(self):
        # n=120, min_size=5 -> max feasible = 120//5 - 1 = 23; 24 must fail.
        r = _run({"model": "l2", "n_bkps": 24, "min_size": 5})
        self.assertEqual(r.get("status"), "failure")
        self.assertIn("out of range", _err(r))

    def test_max_feasible_runs(self):
        r = _run({"model": "l2", "n_bkps": 23, "min_size": 5})
        self.assertEqual(r.get("status"), "success", _err(r))


class TestPenaltyValue(unittest.TestCase):
    def test_numeric_override_runs(self):
        r = _run({"model": "l2", "penalty_value": 5.0})
        self.assertEqual(r.get("status"), "success", _err(r))

    def test_nonpositive_fails_fast(self):
        for bad in (0, -3.0):
            r = _run({"model": "l2", "penalty_value": bad})
            self.assertEqual(r.get("status"), "failure", f"penalty_value={bad}")
            self.assertIn("> 0", _err(r))

    def test_precedence_over_dropdown(self):
        # A huge manual penalty suppresses all breaks even with penalty=aic
        # (the most sensitive criterion) — proving penalty_value wins.
        r = _run({"model": "l2", "penalty": "aic", "penalty_value": 1e9})
        self.assertEqual(r.get("status"), "success", _err(r))
        self.assertEqual(_ncp(r), 0)


class TestEmptyStringUnset(unittest.TestCase):
    def test_blank_knobs_behave_as_unset(self):
        base = _run({"model": "l2"})
        blank = _run({"model": "l2", "n_bkps": "", "penalty_value": ""})
        self.assertEqual(blank.get("status"), "success", _err(blank))
        self.assertEqual(_ncp(base), _ncp(blank))


class TestBackwardCompatDefault(unittest.TestCase):
    def test_penalty_unset_equals_auto(self):
        a = _run({"model": "l2"})              # penalty unset
        b = _run({"model": "l2", "penalty": "auto"})
        self.assertEqual(a.get("status"), "success", _err(a))
        self.assertEqual(_ncp(a), _ncp(b))


if __name__ == "__main__":
    unittest.main(verbosity=2)
