"""AUD-D1 regression - johansen first_cointegrating_vector (interpretation layer).

The Harness Integrity Audit found johansen_cointegration.py referencing an
undefined name (`model` instead of `result`) inside the fail-soft
interpretation block: the NameError was swallowed by the bare except and
audit_fields["first_cointegrating_vector"] was silently None on EVERY
rank>=1 run since the field's birth (f56d52b). Statistics were never
affected. This test pins the contract: on a cointegrated (rank>=1) fixture
the field POPULATES and matches coint_johansen's evec[:, 0] under the
wrapper's round-4 convention, recomputed at the audited spec
(det_order + lag_order == k_ar_diff).

Runs in ci_gate step 3 AND inside the verify_pack F4 gate (sub-check a),
so every future deployment bundle re-proves the fix.

Run:
    pytest engine/tests/test_johansen_interpretation.py -v
"""
import os
import sys
import unittest

_ENGINE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)

import numpy as np  # noqa: E402

from techniques.base import RunContext  # noqa: E402
import techniques.johansen_cointegration as jc  # noqa: E402


def _rank1_fixture(n=300, seed=42):
    """Two series sharing one stochastic trend -> cointegrating rank 1."""
    rng = np.random.default_rng(seed)
    trend = np.cumsum(rng.standard_normal(n))
    y1 = trend + rng.standard_normal(n) * 0.5
    y2 = 0.8 * trend + rng.standard_normal(n) * 0.5
    return y1, y2


class TestJohansenFirstCointegratingVector(unittest.TestCase):
    def _run_engine(self):
        y1, y2 = _rank1_fixture()
        ctx = RunContext({
            "run_id": "test_johansen_interpretation",
            "technique_id": "johansen_cointegration",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "M",
            "time": list(range(len(y1))),
            "series": [
                {"name": "y1", "values": y1.tolist()},
                {"name": "y2", "values": y2.tolist()},
            ],
            "params": {},
        })
        return jc.run(ctx, lambda *a, **kw: None)

    def test_field_populates_and_matches_evec(self):
        resp = self._run_engine()
        self.assertEqual(resp.get("status"), "success")
        a = resp.get("audit_fields", {})

        # Precondition: this fixture must be rank >= 1, else the test is inert.
        rank = int(a.get("cointegrating_rank"))
        self.assertGreaterEqual(
            rank, 1,
            "fixture no longer cointegrated at rank>=1 - the regression "
            "assertion below would be vacuous; re-pin the fixture",
        )

        # The AUD-D1 contract: the field POPULATES at rank >= 1 ...
        fcv = a.get("first_cointegrating_vector")
        self.assertIsNotNone(
            fcv,
            "first_cointegrating_vector is None at rank>=1 - the AUD-D1 "
            "defect class (a swallowed extraction failure) has recurred",
        )
        self.assertEqual(len(fcv), 2)
        self.assertTrue(all(np.isfinite(v) for v in fcv))

        # ... and matches coint_johansen's evec[:, 0] recomputed at the
        # audited spec, under the wrapper's round-4 convention.
        from statsmodels.tsa.vector_ar.vecm import coint_johansen
        y1, y2 = _rank1_fixture()
        stacked = np.column_stack([y1, y2])
        result = coint_johansen(
            stacked,
            det_order=int(a.get("det_order", 0)),
            k_ar_diff=int(a.get("lag_order")),
        )
        expected = [round(float(v), 4) for v in np.asarray(result.evec)[:, 0]]
        self.assertEqual(fcv, expected)


if __name__ == "__main__":
    unittest.main()
