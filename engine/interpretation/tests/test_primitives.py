"""
Unit tests for the pure phrase-generator primitives.

U1 — interpret_pvalue at each of the four bands.
U2 — interpret_pvalue bit-identical across 1000 calls (determinism).
U3 — format_stat_technical produces the documented shape.

Run from repo root:
    pytest engine/interpretation/tests/ -v
"""
import os
import sys
import unittest


_ENGINE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)


from interpretation.primitives import (  # noqa: E402
    interpret_pvalue,
    interpret_correlation_strength,
    interpret_direction,
    interpret_coefficient_magnitude,
    interpret_regime_label,
    format_series_reference,
    format_stat_technical,
)


class TestInterpretPvalue(unittest.TestCase):
    """U1 — four-band classification produces the documented verbs."""

    def test_strong_band(self):
        out = interpret_pvalue(0.001)
        self.assertEqual(out["strength"], "strong")
        self.assertEqual(out["phrase"], "strongly rejects")
        self.assertAlmostEqual(out["band_upper"], 0.01)

    def test_standard_band(self):
        out = interpret_pvalue(0.03)
        self.assertEqual(out["strength"], "standard")
        self.assertEqual(out["phrase"], "rejects")
        self.assertAlmostEqual(out["band_upper"], 0.05)

    def test_marginal_band(self):
        out = interpret_pvalue(0.08)
        self.assertEqual(out["strength"], "marginal")
        self.assertEqual(out["phrase"], "marginally rejects")
        self.assertAlmostEqual(out["band_upper"], 0.10)

    def test_no_rejection(self):
        out = interpret_pvalue(0.50)
        self.assertEqual(out["strength"], "none")
        self.assertEqual(out["phrase"], "does not reject")
        self.assertAlmostEqual(out["band_upper"], 1.0)

    def test_zero_pvalue_treated_as_strongest(self):
        # Numerically zero p-values (common for very large test stats)
        # must land in the strongest band, not raise.
        out = interpret_pvalue(0.0)
        self.assertEqual(out["strength"], "strong")

    def test_thresholds_must_ascend(self):
        with self.assertRaises(ValueError):
            interpret_pvalue(0.05, thresholds=(0.10, 0.05, 0.01))


class TestInterpretPvalueDeterminism(unittest.TestCase):
    """U2 — 1000 repeated calls produce identical output."""

    def test_bit_identical_across_many_calls(self):
        first = interpret_pvalue(0.033)
        for _ in range(1000):
            out = interpret_pvalue(0.033)
            self.assertEqual(out, first)


class TestFormatStatTechnical(unittest.TestCase):
    """U3 — documented shapes for each argument combination."""

    def test_stat_only(self):
        self.assertEqual(
            format_stat_technical("ADF", -10.55),
            "ADF=-10.5500",
        )

    def test_stat_and_critical(self):
        self.assertEqual(
            format_stat_technical("ADF", -10.55, critical_value=-3.45),
            "ADF=-10.5500 vs critical value of -3.4500",
        )

    def test_stat_and_pvalue(self):
        self.assertEqual(
            format_stat_technical("ADF", -10.55, p_value=0.04),
            "ADF=-10.5500, p=0.0400",
        )

    def test_stat_critical_and_pvalue(self):
        self.assertEqual(
            format_stat_technical("ADF", -10.55, critical_value=-3.45,
                                   p_value=0.04),
            "ADF=-10.5500 vs critical value of -3.4500 (p=0.0400)",
        )

    def test_small_pvalue_rendered_as_lt_threshold(self):
        out = format_stat_technical("ADF", -10.55, p_value=0.00005)
        self.assertIn("p<0.0001", out)
        self.assertNotIn("0.0000", out.split(", ")[1])


class TestInterpretCorrelationStrength(unittest.TestCase):
    """C.2 primitive — six-band adjective mapping."""

    def test_bands(self):
        cases = [
            (0.05, "negligible"),
            (-0.05, "negligible"),
            (0.20, "weak"),
            (-0.40, "moderate"),
            (0.60, "strong"),
            (0.80, "very strong"),
            (0.95, "near-perfect"),
            (1.0, "near-perfect"),
        ]
        for rho, expected in cases:
            with self.subTest(rho=rho):
                out = interpret_correlation_strength(rho)
                self.assertEqual(out["band"], expected)
                self.assertEqual(out["adjective"], expected)
                self.assertAlmostEqual(out["abs_rho"], abs(rho))


class TestInterpretDirection(unittest.TestCase):
    """C.3 primitive — lead / lag / contemporaneous phrasing."""

    def test_x_leads(self):
        out = interpret_direction(3, "GDP", "CPI")
        self.assertEqual(out["verb"], "leads")
        self.assertEqual(out["leader"], "GDP")
        self.assertIn("'GDP' leads 'CPI' by 3 period(s)", out["phrase"])

    def test_y_leads(self):
        out = interpret_direction(-2, "GDP", "CPI")
        self.assertEqual(out["verb"], "leads")
        self.assertEqual(out["leader"], "CPI")
        self.assertIn("'CPI' leads 'GDP' by 2 period(s)", out["phrase"])

    def test_contemporaneous(self):
        out = interpret_direction(0, "GDP", "CPI")
        self.assertEqual(out["verb"], "co-moves with")
        self.assertIn("contemporaneously", out["phrase"])

    def test_custom_unit(self):
        out = interpret_direction(1, "X", "Y", unit="quarter")
        self.assertIn("quarter(s)", out["phrase"])


class TestInterpretCoefficientMagnitude(unittest.TestCase):
    """C.5 primitive — five-band magnitude adjectives, explicit unit."""

    def test_bands(self):
        cases = [
            (0.005, "near zero"),
            (-0.005, "near zero"),
            (0.05, "small"),
            (0.25, "moderate"),
            (0.75, "large"),
            (2.0, "extreme"),
        ]
        for coef, expected in cases:
            with self.subTest(coef=coef):
                out = interpret_coefficient_magnitude(coef, "%")
                self.assertEqual(out["band"], expected)
                self.assertIn("%", out["formatted"])

    def test_unit_required(self):
        with self.assertRaises(ValueError):
            interpret_coefficient_magnitude(0.5, "")
        with self.assertRaises(ValueError):
            interpret_coefficient_magnitude(0.5, "   ")


class TestInterpretRegimeLabel(unittest.TestCase):
    """C.6 primitive — label convention after sort-by-mean."""

    def test_two_regimes(self):
        self.assertEqual(
            interpret_regime_label(0, 2)["label"], "low-mean regime"
        )
        self.assertEqual(
            interpret_regime_label(1, 2)["label"], "high-mean regime"
        )

    def test_three_plus_regimes(self):
        self.assertEqual(
            interpret_regime_label(0, 3)["label"], "lowest-mean regime"
        )
        self.assertEqual(
            interpret_regime_label(1, 3)["label"], "mid-mean regime #1"
        )
        self.assertEqual(
            interpret_regime_label(2, 3)["label"], "highest-mean regime"
        )

    def test_custom_axis(self):
        out = interpret_regime_label(1, 2, axis="variance")
        self.assertIn("variance", out["label"])

    def test_out_of_range(self):
        with self.assertRaises(ValueError):
            interpret_regime_label(2, 2)


class TestFormatSeriesReference(unittest.TestCase):
    def test_quoted(self):
        self.assertEqual(format_series_reference("GDP"), "'GDP'")

    def test_unquoted(self):
        self.assertEqual(format_series_reference("GDP", with_quotes=False), "GDP")


if __name__ == "__main__":
    unittest.main(verbosity=2)
