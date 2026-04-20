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
    """U3 — documented shapes for each argument combination. Per R6
    (§4.5 determinism), the stat value routes through
    ``FMT_STAT_BY_NAME`` with ``FMT_STAT_DEFAULT`` as the fallback."""

    def test_stat_only(self):
        self.assertEqual(
            format_stat_technical("ADF", -10.55),
            "ADF=-10.55",
        )

    def test_stat_and_critical(self):
        self.assertEqual(
            format_stat_technical("ADF", -10.55, critical_value=-3.45),
            "ADF=-10.55 vs critical value of -3.45",
        )

    def test_stat_and_pvalue(self):
        self.assertEqual(
            format_stat_technical("ADF", -10.55, p_value=0.04),
            "ADF=-10.55, p=0.0400",
        )

    def test_stat_critical_and_pvalue(self):
        self.assertEqual(
            format_stat_technical("ADF", -10.55, critical_value=-3.45,
                                   p_value=0.04),
            "ADF=-10.55 vs critical value of -3.45 (p=0.0400)",
        )

    def test_small_pvalue_rendered_as_lt_threshold(self):
        out = format_stat_technical("ADF", -10.55, p_value=0.00005)
        self.assertIn("p<0.0001", out)
        self.assertNotIn("0.0000", out.split(", ")[1])

    def test_f_stat_uses_f_format(self):
        """F-statistic routes through FMT_F_STAT = '{:.2f}' — not the
        old hardcoded '{:.4f}'."""
        self.assertEqual(
            format_stat_technical("F", 8.40, p_value=0.0003),
            "F=8.40, p=0.0003",
        )
        self.assertEqual(
            format_stat_technical("F", 0.9, p_value=0.41),
            "F=0.90, p=0.4100",
        )

    def test_unknown_stat_name_falls_back_to_default(self):
        """Stat names not in FMT_STAT_BY_NAME use FMT_STAT_DEFAULT =
        '{:.2f}' rather than raising or emitting a different format."""
        self.assertEqual(
            format_stat_technical("LR", 12.3456),
            "LR=12.35",
        )
        self.assertEqual(
            format_stat_technical("Q", 3.14159, p_value=0.05),
            "Q=3.14, p=0.0500",
        )


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


# ---------------------------------------------------------------------
# R6 — Format-specifier constants (Prompt B determinism)
# ---------------------------------------------------------------------

class TestFormatConstants(unittest.TestCase):
    """Every spec routes numeric rendering through these constants so
    two calls with the same input produce bit-identical strings across
    platforms and Python versions."""

    def test_p_value_format(self):
        from interpretation.primitives import FMT_P_VALUE
        self.assertEqual(FMT_P_VALUE.format(0.0003), "0.0003")
        self.assertEqual(FMT_P_VALUE.format(0.5), "0.5000")

    def test_rho_format(self):
        from interpretation.primitives import FMT_RHO
        self.assertEqual(FMT_RHO.format(-0.7234), "-0.72")
        self.assertEqual(FMT_RHO.format(0.0), "0.00")

    def test_signed_coefficient_format(self):
        from interpretation.primitives import FMT_COEF_SIGNED
        # Sign-preserving: + on positive, - on negative, even for zero
        self.assertEqual(FMT_COEF_SIGNED.format(-1.08), "-1.080")
        self.assertEqual(FMT_COEF_SIGNED.format(0.039), "+0.039")

    def test_unsigned_coefficient_format(self):
        from interpretation.primitives import FMT_COEF_UNSIGNED
        self.assertEqual(FMT_COEF_UNSIGNED.format(0.723), "0.723")

    def test_f_stat_format(self):
        from interpretation.primitives import FMT_F_STAT
        self.assertEqual(FMT_F_STAT.format(8.401), "8.40")

    def test_persistence_format(self):
        from interpretation.primitives import FMT_PERSISTENCE
        self.assertEqual(FMT_PERSISTENCE.format(0.9734), "0.973")

    def test_eigenvalue_format(self):
        from interpretation.primitives import FMT_EIGENVALUE
        # Use unambiguous rounding targets — 2.485 is subject to Python's
        # banker's rounding (→ 2.48 not 2.49).
        self.assertEqual(FMT_EIGENVALUE.format(2.47), "2.47")
        self.assertEqual(FMT_EIGENVALUE.format(0.621), "0.62")

    def test_probability_format(self):
        from interpretation.primitives import FMT_PROBABILITY
        self.assertEqual(FMT_PROBABILITY.format(0.913), "0.91")

    def test_half_life_format(self):
        from interpretation.primitives import FMT_HALF_LIFE
        self.assertEqual(FMT_HALF_LIFE.format(22.671), "22.7")


# ---------------------------------------------------------------------
# R7 — Break-date formatting helper
# ---------------------------------------------------------------------

class TestFormatBreakDate(unittest.TestCase):
    """Frequency-keyed rendering must be deterministic and pure."""

    def _date(self):
        import pandas as pd
        return pd.Timestamp("1995-06-15")

    def test_quarterly(self):
        from interpretation.primitives import format_break_date
        self.assertEqual(format_break_date(self._date(), "quarterly"), "1995-Q2")

    def test_quarterly_q1(self):
        from interpretation.primitives import format_break_date
        import pandas as pd
        self.assertEqual(
            format_break_date(pd.Timestamp("2020-02-10"), "quarterly"),
            "2020-Q1",
        )

    def test_monthly(self):
        from interpretation.primitives import format_break_date
        self.assertEqual(format_break_date(self._date(), "monthly"), "1995-06")

    def test_daily(self):
        from interpretation.primitives import format_break_date
        self.assertEqual(format_break_date(self._date(), "daily"), "1995-06-15")

    def test_annual(self):
        from interpretation.primitives import format_break_date
        self.assertEqual(format_break_date(self._date(), "annual"), "1995")

    def test_unknown_frequency_fallback(self):
        from interpretation.primitives import format_break_date
        # Unknown frequency falls back to ISO date rendering (no raise)
        out = format_break_date(self._date(), "unknown-freq")
        self.assertEqual(out, "1995-06-15")

    def test_case_insensitive(self):
        from interpretation.primitives import format_break_date
        self.assertEqual(format_break_date(self._date(), "QUARTERLY"), "1995-Q2")
        self.assertEqual(format_break_date(self._date(), "  Monthly  "), "1995-06")

    def test_string_input(self):
        from interpretation.primitives import format_break_date
        self.assertEqual(format_break_date("1995-06-15", "quarterly"), "1995-Q2")

    def test_determinism_across_repeated_calls(self):
        from interpretation.primitives import format_break_date
        first = format_break_date(self._date(), "quarterly")
        for _ in range(200):
            self.assertEqual(format_break_date(self._date(), "quarterly"), first)


if __name__ == "__main__":
    unittest.main(verbosity=2)
