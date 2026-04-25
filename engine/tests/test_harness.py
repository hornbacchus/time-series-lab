"""Unit tests for the reference-parity harness internals.

Validates the Phase 2 Session 1 deliverables:
- Manifest TOML loading + stale-detection
- FixtureLoader hash verification (load + write_with_sha)
- FixtureLoader raises FixtureHashMismatchError on tampered file
- Runner outcome aggregation + exit-code derivation
- Runner SKIP on RNotAvailableError
- Runner ERROR on unexpected exception
- CAVEAT re-roll PASS-on-retry promotes to PASS
- CAVEAT re-roll CAVEAT-on-retry escalates to BLOCK
- JSON output validity

Tests use ``unittest.mock`` to avoid invoking R or running real
parity checks; the live-R + 3e PoC validation lives in Phase 5
verification gates rather than the unit-test suite.
"""

from __future__ import annotations

import datetime
import importlib
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np


# Add tools/ to sys.path so reference_parity is importable
_TOOLS = pathlib.Path(__file__).resolve().parents[2] / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))


from reference_parity.harness.base import (
    ParityCheck,
    ParityResult,
    aggregate_outcomes,
)
from reference_parity.harness.fixtures import (
    FixtureLoader,
    FixtureHashMismatchError,
)
from reference_parity.harness.manifest import Manifest
from reference_parity.harness.r_bridge import RNotAvailableError
from reference_parity.harness.runner import (
    run_check,
    _exit_code_for,
    _emit_results,
)


class TestManifestLoading(unittest.TestCase):
    """Manifest.load parses TOML correctly."""

    def test_default_manifest_loads(self):
        m = Manifest.load()
        self.assertEqual(m.r.version, "4.5.3")
        self.assertIn("hts", m.r.packages)
        self.assertIn("statsmodels", m.python.packages)

    def test_stale_detection(self):
        m = Manifest.load()
        future = m.next_review + datetime.timedelta(days=1)
        self.assertTrue(m.is_stale(today=future))
        before = m.next_review - datetime.timedelta(days=1)
        self.assertFalse(m.is_stale(today=before))


class TestFixtureLoader(unittest.TestCase):
    """FixtureLoader hashing + integrity."""

    def test_write_then_load(self):
        with tempfile.TemporaryDirectory() as d:
            loader = FixtureLoader(root=pathlib.Path(d))
            data = {
                "x": np.array([1.0, 2.0, 3.0]),
                "y": np.eye(3, dtype=np.float64),
            }
            npz_p, sha_p, sha = loader.write_with_sha("t1", data)
            self.assertTrue(npz_p.exists())
            self.assertTrue(sha_p.exists())
            loaded, sha2 = loader.load("t1")
            self.assertEqual(sha, sha2)
            np.testing.assert_array_equal(loaded["x"], data["x"])
            np.testing.assert_array_equal(loaded["y"], data["y"])

    def test_hash_mismatch_raises(self):
        with tempfile.TemporaryDirectory() as d:
            loader = FixtureLoader(root=pathlib.Path(d))
            loader.write_with_sha("t2", {"a": np.array([1.0])})
            # Tamper with the .npz file (append a byte)
            npz_path = pathlib.Path(d) / "t2.npz"
            with open(npz_path, "ab") as f:
                f.write(b"\x00")
            with self.assertRaises(FixtureHashMismatchError):
                loader.load("t2")


class TestRunnerSkip(unittest.TestCase):
    """run_check returns SKIP when R unavailable."""

    def test_skip_on_r_unavailable(self):

        class DummyCheck(ParityCheck):
            technique_id = "dummy_skip"
            tier = "fast"
            fixture_id = ""

            def setup_fixture(self, seed):
                return {"x": np.array([1.0])}

            def run_tsl(self, fixture):
                return {"value": 1.0}

            def run_reference(self, fixture):
                raise RNotAvailableError(
                    "Rscript not on PATH (test simulation)"
                )

            def compare(self, tsl, ref):
                return ParityResult(
                    technique_id=self.technique_id, outcome="PASS",
                )

        result = run_check(DummyCheck())
        self.assertEqual(result.outcome, "SKIP")
        self.assertIn("R unavailable", result.error)


class TestRunnerError(unittest.TestCase):
    """run_check returns ERROR on unexpected exception."""

    def test_error_on_runtime_failure(self):

        class CrashCheck(ParityCheck):
            technique_id = "dummy_crash"
            tier = "fast"
            fixture_id = ""

            def setup_fixture(self, seed):
                return {}

            def run_tsl(self, fixture):
                raise ValueError("intentional crash")

            def run_reference(self, fixture):
                return {}

            def compare(self, tsl, ref):
                return ParityResult(
                    technique_id=self.technique_id, outcome="PASS",
                )

        result = run_check(CrashCheck())
        self.assertEqual(result.outcome, "ERROR")
        self.assertIn("ValueError", result.error)


class TestCaveatReroll(unittest.TestCase):
    """CAVEAT re-roll behaviour."""

    def test_caveat_then_pass_promotes(self):

        class Reroller(ParityCheck):
            technique_id = "dummy_reroll_pass"
            tier = "fast"
            fixture_id = ""

            def __init__(self):
                self.calls = 0

            def setup_fixture(self, seed):
                return {"seed": seed}

            def run_tsl(self, fixture):
                self.calls += 1
                return {"calls": self.calls}

            def run_reference(self, fixture):
                return {}

            def compare(self, tsl, ref):
                if tsl["calls"] == 1:
                    return ParityResult(
                        technique_id=self.technique_id,
                        outcome="CAVEAT",
                    )
                return ParityResult(
                    technique_id=self.technique_id, outcome="PASS",
                )

        result = run_check(Reroller(), seed=42)
        self.assertEqual(result.outcome, "PASS")
        self.assertEqual(result.seed_used, 43)

    def test_caveat_then_caveat_escalates(self):

        class StuckReroller(ParityCheck):
            technique_id = "dummy_reroll_stuck"
            tier = "fast"
            fixture_id = ""

            def setup_fixture(self, seed):
                return {}

            def run_tsl(self, fixture):
                return {}

            def run_reference(self, fixture):
                return {}

            def compare(self, tsl, ref):
                return ParityResult(
                    technique_id=self.technique_id,
                    outcome="CAVEAT",
                )

        result = run_check(StuckReroller(), seed=42)
        self.assertEqual(result.outcome, "BLOCK")
        self.assertIn("escalated", result.diagnostics["caveat_reroll"])


class TestExitCodes(unittest.TestCase):
    """Outcome aggregation + exit-code mapping."""

    def test_aggregate_priority(self):
        self.assertEqual(
            aggregate_outcomes(["PASS", "PASS", "CAVEAT"]), "CAVEAT",
        )
        self.assertEqual(
            aggregate_outcomes(["PASS", "CAVEAT", "BLOCK"]), "BLOCK",
        )
        self.assertEqual(
            aggregate_outcomes(["SKIP", "PASS"]), "PASS",
        )
        self.assertEqual(aggregate_outcomes([]), "PASS")
        self.assertEqual(
            aggregate_outcomes(["ERROR", "CAVEAT"]), "ERROR",
        )
        self.assertEqual(
            aggregate_outcomes(["BLOCK", "ERROR"]), "BLOCK",
        )

    def test_exit_code_mapping(self):
        self.assertEqual(_exit_code_for("PASS"), 0)
        self.assertEqual(_exit_code_for("SKIP"), 0)
        self.assertEqual(_exit_code_for("CAVEAT"), 2)
        self.assertEqual(_exit_code_for("BLOCK"), 1)
        self.assertEqual(_exit_code_for("ERROR"), 3)


class TestJsonOutput(unittest.TestCase):
    """JSON emission produces valid parseable output."""

    def test_emit_results_json_valid(self):
        results = [
            ParityResult(
                technique_id="t1", outcome="PASS",
                metrics={"max_abs_diff": 1e-15, "rms": 5e-16},
                duration_sec=0.1, seed_used=42,
            ),
            ParityResult(
                technique_id="t2", outcome="SKIP",
                error="R missing",
                duration_sec=0.0, seed_used=42,
            ),
        ]
        import io
        buf = io.StringIO()
        old_stdout = sys.stdout
        try:
            sys.stdout = buf
            code = _emit_results(results, json_out=True)
        finally:
            sys.stdout = old_stdout
        text = buf.getvalue().strip()
        parsed = json.loads(text)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["technique_id"], "t1")
        self.assertEqual(parsed[0]["outcome"], "PASS")
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
