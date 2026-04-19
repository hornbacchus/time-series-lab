"""
Contract-level invariants for the plain-language Interpretation layer.

Tests the public behavior of ``build_interpretation`` against the shape
promised to callers (the C# writer and the downstream UI).
Determinism, fallback, Greek-letter ban in Tier 1, and specification
disclosure in Tier 2 are all enforced here.

Run from repo root:
    pytest engine/tests/test_interpretation_contract.py -v
"""
import os
import re
import sys
import unittest


_ENGINE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)


from interpretation import build_interpretation, PLACEHOLDER_TIER1  # noqa: E402


# Shared reference facts for the canonical ADF-on-stationary-data case
# (Real GDP Q/Q SAAR analogue). Uses the exact shape the ADF wrapper's
# _build_interp_dict_single produces.
_ADF_SINGLE_STATIONARY = {
    "mode": "single_test",
    "series_name": "Real GDP Q/Q SAAR",
    "adf_stat": -10.55,
    "p_value": 0.00001,
    "regression": "c",
    "used_lag": 1,
    "schwert_bound": 15,
    "n_obs": 286,
    "crit_1pct": -3.4524,
    "crit_5pct": -2.8712,
    "significance_level": 0.05,
    "trending": False,
    "t_stat_trend": 0.3,
    "decision_rejected": True,
}


_ADF_TRIAGE_UNIT_ROOT = {
    "mode": "triage",
    "series_name": "Random walk",
    "adf_stat": -2.71,
    "p_value": 0.073,
    "regression": "c",
    "used_lag": 1,
    "schwert_bound": 17,
    "n_obs": 500,
    "crit_1pct": -3.44,
    "crit_5pct": -2.87,
    "significance_level": 0.05,
    "trending": True,
    "t_stat_trend": 6.4,
    "decision_rejected": False,
    "kpss_stat": 0.76,
    "kpss_pvalue": 0.01,
    "kpss_rejected": True,
    "pp_stat": -2.50,
    "pp_pvalue": 0.11,
    "pp_rejected": False,
    "joint_verdict": "UNIT ROOT (I(1))",
}


_ADF_TRIAGE_CONFLICTING = {
    "mode": "triage",
    "series_name": "Persistent series",
    "adf_stat": -3.20,
    "p_value": 0.02,
    "regression": "c",
    "used_lag": 2,
    "schwert_bound": 16,
    "n_obs": 400,
    "crit_1pct": -3.45,
    "crit_5pct": -2.87,
    "significance_level": 0.05,
    "trending": False,
    "t_stat_trend": 0.8,
    "decision_rejected": True,
    "kpss_stat": 0.52,
    "kpss_pvalue": 0.02,
    "kpss_rejected": True,
    "pp_stat": -3.15,
    "pp_pvalue": 0.03,
    "pp_rejected": True,
    "joint_verdict": "CONFLICTING",
}


class TestContractShape(unittest.TestCase):
    """T1 — returned dict has exactly the keys {tier1, tier2, tier3}
    with correct types, and tier1/tier2 are non-empty on a registered
    technique."""

    def test_adf_returns_three_required_keys(self):
        out = build_interpretation("adf_test", _ADF_SINGLE_STATIONARY)
        self.assertIsInstance(out, dict)
        self.assertEqual(set(out.keys()), {"tier1", "tier2", "tier3"})
        self.assertIsInstance(out["tier1"], str)
        self.assertIsInstance(out["tier2"], str)
        self.assertIsInstance(out["tier3"], list)
        self.assertTrue(out["tier1"].strip(),
                        "tier1 must be non-empty on registered technique")
        self.assertTrue(out["tier2"].strip(),
                        "tier2 must be non-empty on registered technique")
        for c in out["tier3"]:
            self.assertIsInstance(c, str)


class TestDeterminism(unittest.TestCase):
    """T2 — two calls on identical input produce bit-identical output."""

    def test_adf_stationary_bit_identical(self):
        first = build_interpretation("adf_test", dict(_ADF_SINGLE_STATIONARY))
        second = build_interpretation("adf_test", dict(_ADF_SINGLE_STATIONARY))
        self.assertEqual(first, second)

    def test_adf_triage_bit_identical(self):
        first = build_interpretation("adf_test", dict(_ADF_TRIAGE_CONFLICTING))
        second = build_interpretation("adf_test", dict(_ADF_TRIAGE_CONFLICTING))
        self.assertEqual(first, second)


class TestFallback(unittest.TestCase):
    """T3 — unregistered technique id returns the exact P.6 placeholder."""

    def test_unregistered_returns_placeholder(self):
        out = build_interpretation("nonexistent_technique_xyz", {})
        self.assertEqual(out["tier1"], PLACEHOLDER_TIER1)
        self.assertEqual(out["tier2"], "")
        self.assertEqual(out["tier3"], [])


class TestNoGreekInTier1(unittest.TestCase):
    """T4 — Tier 1 must not contain common Greek letters."""

    GREEK = tuple("αβγδεζηθκλμνξπρστφχψωΑΒΓΔΕΖΗΘΚΛΜΝΞΠΡΣΤΦΧΨΩ")
    GREEK_REGEX = re.compile("[" + "".join(GREEK) + "]")

    def _assert_no_greek(self, text: str):
        m = self.GREEK_REGEX.search(text)
        self.assertIsNone(
            m,
            f"Tier 1 must not contain Greek letters; found {m.group() if m else None!r} "
            f"in {text!r}"
        )

    def test_adf_stationary(self):
        out = build_interpretation("adf_test", _ADF_SINGLE_STATIONARY)
        self._assert_no_greek(out["tier1"])

    def test_adf_unit_root(self):
        out = build_interpretation("adf_test", _ADF_TRIAGE_UNIT_ROOT)
        self._assert_no_greek(out["tier1"])

    def test_adf_conflicting(self):
        out = build_interpretation("adf_test", _ADF_TRIAGE_CONFLICTING)
        self._assert_no_greek(out["tier1"])


class TestSpecificationDisclosureInTier2(unittest.TestCase):
    """T5 — Tier 2 must surface the regression specification."""

    def test_tier2_contains_regression_spec(self):
        out = build_interpretation("adf_test", _ADF_SINGLE_STATIONARY)
        tier2 = out["tier2"]
        # Either "regression='c'" or "constant only" or "constant-only"
        # satisfies the disclosure — all three are valid renderings of
        # the same specification.
        ok = (
            "regression='c'" in tier2
            or "constant only" in tier2
            or "constant-only" in tier2
        )
        self.assertTrue(
            ok,
            f"Tier 2 must disclose the regression specification; "
            f"got: {tier2[:200]!r}"
        )


class TestTier1LengthBounds(unittest.TestCase):
    """T6 — Tier 1 string is between 150 and 600 characters across the
    three reference cases. Out of bounds on either side indicates voice
    drift that will propagate across 67 technique specs."""

    MIN_LEN = 150
    MAX_LEN = 600

    def _check(self, results: dict, label: str):
        out = build_interpretation("adf_test", results)
        n = len(out["tier1"])
        self.assertGreaterEqual(
            n, self.MIN_LEN,
            f"{label} Tier 1 is only {n} chars (< {self.MIN_LEN}). "
            "Likely missing the practical implication."
        )
        self.assertLessEqual(
            n, self.MAX_LEN,
            f"{label} Tier 1 is {n} chars (> {self.MAX_LEN}). "
            "Drifted out of the 2-4 sentence contract."
        )

    def test_stationary(self):
        self._check(_ADF_SINGLE_STATIONARY, "stationary")

    def test_unit_root(self):
        self._check(_ADF_TRIAGE_UNIT_ROOT, "unit-root")

    def test_conflicting(self):
        self._check(_ADF_TRIAGE_CONFLICTING, "CONFLICTING")


class TestTier2ContainsTestStatistics(unittest.TestCase):
    """T7 — Tier 2 must include the ADF statistic and either a p-value
    or a critical-value comparison (or both)."""

    def test_tier2_has_stat_and_p_or_crit(self):
        out = build_interpretation("adf_test", _ADF_SINGLE_STATIONARY)
        tier2 = out["tier2"]
        # Statistic value
        self.assertIn("ADF=-10.55", tier2.replace(" ", "").replace("ADF=", "ADF="))
        # Either p-value or critical value
        has_p = ("p<0.0001" in tier2) or re.search(r"p=\d+\.\d+", tier2)
        has_crit = "critical value" in tier2
        self.assertTrue(
            has_p or has_crit,
            f"Tier 2 must carry a p-value or a critical-value comparison; "
            f"got: {tier2[:250]!r}"
        )


class TestTier3Triggers(unittest.TestCase):
    """Not a numbered invariant but worth pinning — the four ADF
    Tier 3 triggers fire when their conditions hold."""

    def test_trending_series_trigger_on_unit_root_case(self):
        # Case (b) has trending=True and regression='c' and |t|=6.4 > 2.0
        out = build_interpretation("adf_test", _ADF_TRIAGE_UNIT_ROOT)
        found = any("regression='ct'" in c for c in out["tier3"])
        self.assertTrue(
            found,
            f"Trending-series trigger must fire on case (b); got: {out['tier3']!r}"
        )

    def test_no_trending_trigger_when_not_trending(self):
        # Case (a) has trending=False — trigger must not fire
        out = build_interpretation("adf_test", _ADF_SINGLE_STATIONARY)
        for c in out["tier3"]:
            self.assertNotIn("regression='ct'", c)

    def test_borderline_p_stricter_direction(self):
        results = dict(_ADF_SINGLE_STATIONARY)
        results["p_value"] = 0.045  # below 0.05 → stricter flip direction
        out = build_interpretation("adf_test", results)
        joined = " ".join(out["tier3"])
        self.assertIn("stricter (1%)", joined)

    def test_borderline_p_looser_direction(self):
        results = dict(_ADF_SINGLE_STATIONARY)
        results["p_value"] = 0.055
        results["decision_rejected"] = False
        out = build_interpretation("adf_test", results)
        joined = " ".join(out["tier3"])
        self.assertIn("looser (10%)", joined)

    def test_small_sample_trigger(self):
        results = dict(_ADF_SINGLE_STATIONARY)
        results["n_obs"] = 30
        out = build_interpretation("adf_test", results)
        self.assertTrue(
            any("n=30" in c for c in out["tier3"]),
            f"Small-sample trigger must fire on n=30; got: {out['tier3']!r}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
