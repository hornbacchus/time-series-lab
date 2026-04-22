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


class TestGreekCitationFormInTier1(unittest.TestCase):
    """T4 (Prompt B revision) — Greek letters in Tier 1 are permitted
    **only** in citation form. Allowed:

      - Greek letter adjacent to ``=``, ``<``, ``>``, or ``≈`` followed
        by a numeric literal (optionally signed).
          e.g., ``ρ=−0.72``, ``α+β=0.97``, ``σ²=1.21``, ``μ<0``, ``p≈0.04``
      - Named compounds ``α+β`` and ``σ²`` are treated as a unit; the
        compound itself must be followed by an operator + value.

    Banned: standalone Greek as a bare noun ("the β coefficient", "use
    α=0.05 as threshold"). The regex walks each Greek token and checks
    the tail: if the next non-whitespace character is one of
    ``=, <, >, ≈, ⁺, +, ²`` *and* ultimately reaches a digit, the
    token passes. Otherwise it fails.
    """

    GREEK = tuple("αβγδεζηθικλμνξοπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ")
    GREEK_SET = set(GREEK)
    CITATION_OPERATORS = set("=<>≈")
    COMPOUND_LINKERS = set("+²")  # for α+β, σ² etc.

    @classmethod
    def _is_citation_form(cls, text: str, idx: int) -> bool:
        """Given a Greek letter at position idx, walk forward through any
        compound linkers (``+`` + another Greek letter, or ``²``), then
        expect an operator, then eventually a digit. Returns True iff
        the tail forms a valid citation like ``ρ=−0.72`` or ``α+β=0.97``."""
        n = len(text)
        j = idx + 1
        # Allow compound: "α+β" or "σ²" — walk past one chained Greek-or-²
        # pair before demanding the operator.
        while j < n and text[j] in cls.COMPOUND_LINKERS:
            j += 1
            # If the linker was "+", expect a second Greek letter
            # after it (for α+β). A "²" is a suffix on the first letter.
            if j < n and text[j - 1] == "+":
                if j >= n or text[j] not in cls.GREEK_SET:
                    return False
                j += 1
        # Skip whitespace
        while j < n and text[j] in " \t":
            j += 1
        # Need an operator from the citation set
        if j >= n or text[j] not in cls.CITATION_OPERATORS:
            return False
        j += 1
        # Skip whitespace, optional sign
        while j < n and text[j] in " \t":
            j += 1
        if j < n and text[j] in "+-−":
            j += 1
        while j < n and text[j] in " \t":
            j += 1
        # Must hit a digit
        return j < n and text[j].isdigit()

    def _assert_greek_only_in_citation_form(self, text: str, label: str = ""):
        for i, ch in enumerate(text):
            if ch in self.GREEK_SET:
                if not self._is_citation_form(text, i):
                    # Show 30-char context window
                    ctx = text[max(0, i - 10):i + 20]
                    self.fail(
                        f"{label}: standalone Greek letter {ch!r} at position "
                        f"{i} (context: {ctx!r}) violates T4 citation-form rule."
                    )

    def test_adf_stationary(self):
        out = build_interpretation("adf_test", _ADF_SINGLE_STATIONARY)
        self._assert_greek_only_in_citation_form(out["tier1"], "adf_stationary")

    def test_adf_unit_root(self):
        out = build_interpretation("adf_test", _ADF_TRIAGE_UNIT_ROOT)
        self._assert_greek_only_in_citation_form(out["tier1"], "adf_unit_root")

    def test_adf_conflicting(self):
        out = build_interpretation("adf_test", _ADF_TRIAGE_CONFLICTING)
        self._assert_greek_only_in_citation_form(out["tier1"], "adf_conflicting")

    def test_citation_form_detector_positives(self):
        """Self-test of the detector: strings that should PASS."""
        passes = [
            "ρ=−0.72",
            "α+β=0.97",
            "μ<0",
            "σ²=1.21",
            "p≈0.04",
            "ρ = 0.55",  # whitespace tolerance
            "shocks α+β=0.70 imply fade",  # within prose
        ]
        for text in passes:
            for i, ch in enumerate(text):
                if ch in self.GREEK_SET:
                    self.assertTrue(
                        self._is_citation_form(text, i),
                        f"Should accept citation form in: {text!r}"
                    )

    def test_citation_form_detector_negatives(self):
        """Self-test of the detector: strings that should FAIL."""
        fails = [
            "the β coefficient",
            "use α value",
            "ρ parameter",
        ]
        for text in fails:
            for i, ch in enumerate(text):
                if ch in self.GREEK_SET:
                    self.assertFalse(
                        self._is_citation_form(text, i),
                        f"Should reject standalone Greek in: {text!r}"
                    )


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


# =====================================================================
# Prompt B invariants: T8 (Jaccard), T9 (dangling stat), T10 (registry).
# =====================================================================

# Shared test fixtures per technique. Each entry is a list of (name,
# results_dict) pairs spanning the verdict space of that technique. The
# T8/T9 tests iterate every spec × every case.

_FIXTURES = {
    "adf_test": [
        ("single_stationary", _ADF_SINGLE_STATIONARY),
        ("triage_unit_root", _ADF_TRIAGE_UNIT_ROOT),
        ("triage_conflicting", _ADF_TRIAGE_CONFLICTING),
    ],
    "granger_causality": [
        ("significant", dict(
            series_name_x="X", series_name_y="Y", best_lag=2, best_f=8.40,
            best_p=0.0003, max_lag=8, n_obs=286, significance=0.05,
            reverse_f=0.90, reverse_p=0.41,
        )),
        ("no_causality", dict(
            series_name_x="X", series_name_y="Y", best_lag=2, best_f=1.20,
            best_p=0.31, max_lag=8, n_obs=286, significance=0.05,
            reverse_f=1.10, reverse_p=0.35,
        )),
    ],
    "rolling_ccf_lag": [
        ("single_regime", dict(
            series_name_x="GDP", series_name_y="Unemp", n_obs=286, window=60,
            n_windows=227, pct_significant=96.0, structural_break=False,
            single_median_rho=-0.72, single_median_lag=-1, n_excluded=0,
            ac_corrected=True,
        )),
        ("split_regime", dict(
            series_name_x="Real GDP", series_name_y="CPI", n_obs=286,
            window=60, n_windows=227, pct_significant=65.0,
            structural_break=True, frequency="quarterly",
            break_date="1995-06-15",
            pre_median_rho=-0.36, pre_median_lag=-1,
            pre_pct_significant=73.0, pre_n_windows=130,
            post_median_rho=0.13, post_median_lag=3,
            post_pct_significant=58.0, post_n_windows=111,
            n_excluded=7, ac_corrected=True,
        )),
    ],
    "vecm_model": [
        ("cointegrated", dict(
            variable_names=["US10Y", "US2Y"], coint_rank=1, lag_order=2,
            n_obs=500, beta_normalized=[[1.0], [-1.08]],
            alpha_normalized=[[-0.039], [0.012]], half_life_periods=18.0,
            trace_stat=22.50, trace_cv_5pct=15.50, trace_stat_r1=2.30,
            trace_cv_r1_5pct=3.80, significance=0.05,
        )),
        ("not_cointegrated", dict(
            variable_names=["FFR", "BTC"], coint_rank=0, lag_order=2,
            n_obs=500, beta_normalized=[[1.0], [0.0]],
            alpha_normalized=[[0.0], [0.0]], half_life_periods=None,
            trace_stat=5.20, trace_cv_5pct=15.50, trace_stat_r1=None,
            trace_cv_r1_5pct=None, significance=0.05,
        )),
    ],
    "var_model": [
        ("stable", dict(
            variable_names=["GDP", "CPI", "FFR"], var_order=2, n_variables=3,
            aic=3.2, bic=3.5, ic_used="aic", max_root_modulus=0.72, n_obs=280,
            granger_within_var=[
                ["GDP", "FFR", 2, 6.30, 0.002, True],
                ["CPI", "FFR", 2, 1.20, 0.30, False],
            ],
        )),
        ("near_unstable", dict(
            variable_names=["GDP", "CPI", "FFR"], var_order=2, n_variables=3,
            aic=3.2, bic=3.5, ic_used="aic", max_root_modulus=0.97, n_obs=280,
            granger_within_var=[
                ["GDP", "FFR", 2, 6.30, 0.002, True],
            ],
        )),
    ],
    "garch_model": [
        ("high_persistence", dict(
            series_name="SPX returns", n_obs=2500, dist="Normal",
            order_p=1, order_q=1, alpha=0.09, beta=0.88, persistence=0.97,
            ljung_box_sq_p=0.42,
        )),
        ("low_persistence", dict(
            series_name="Return series", n_obs=1500, dist="Normal",
            order_p=1, order_q=1, alpha=0.15, beta=0.55, persistence=0.70,
            ljung_box_sq_p=0.35,
        )),
    ],
    "markov_switching": [
        ("two_regime", dict(
            k_regimes=2, regime_means=[-1.20, 3.40],
            regime_stds=[1.10, 1.10], current_regime=1, current_prob=0.91,
            expected_durations=[12.0, 15.0],
            final_period_probs=[0.09, 0.91], sort_axis="mean",
        )),
        ("three_regime", dict(
            k_regimes=3, regime_means=[-2.10, 0.30, 2.80],
            regime_stds=[1.00, 0.90, 1.10], current_regime=1,
            current_prob=0.78,
            expected_durations=[10.0, 14.0, 11.0],
            final_period_probs=[0.11, 0.78, 0.11], sort_axis="mean",
        )),
        ("two_regime_variance_dominant", dict(
            # Motivating case: Real GDP Q/Q SAAR under switching_variance.
            # μ differs by 60bp; σ differs 3.5× (variance ratio 12×).
            # sort_axis="std" exercises the variance-dominant label path
            # added in Prompt 2 of the Markov batch.
            k_regimes=2, regime_means=[3.00, 3.60],
            regime_stds=[1.86, 6.48], current_regime=0, current_prob=0.95,
            expected_durations=[25.0, 8.0],
            final_period_probs=[0.95, 0.05], sort_axis="std",
        )),
    ],
    "pca_analysis": [
        ("strong_dominance", dict(
            n_series=4, n_obs=286, eigenvalues=[2.48, 0.84, 0.44, 0.24],
            explained_variance_ratio=[0.62, 0.21, 0.11, 0.06],
            cumulative_variance_ratio=[0.62, 0.83, 0.94, 1.00],
            loadings=[[0.85, 0.1, 0.1, 0.2], [0.5, 0.72, 0.1, 0.2],
                      [0.4, 0.3, 0.8, 0.2], [0.3, 0.2, 0.4, 0.9]],
            variable_names=["CPI", "GDP", "FFR", "UNEMP"],
            kaiser_components=1, n_80=2, top_pc1_loader="CPI",
            top_pc1_loading_value=0.85, top_pc2_loader="GDP",
            top_pc2_loading_abs=0.72, mean_off_diag_abs_rho=0.45,
        )),
        ("flat_spectrum", dict(
            n_series=4, n_obs=286, eigenvalues=[1.28, 1.12, 0.96, 0.64],
            explained_variance_ratio=[0.32, 0.28, 0.24, 0.16],
            cumulative_variance_ratio=[0.32, 0.60, 0.84, 1.00],
            loadings=[[0.51, 0.3, 0.2, 0.1], [0.3, 0.62, 0.2, 0.1],
                      [0.3, 0.2, 0.55, 0.1], [0.2, 0.1, 0.3, 0.68]],
            variable_names=["Y1", "Y2", "Y3", "Y4"],
            kaiser_components=0, n_80=3, top_pc1_loader="Y1",
            top_pc1_loading_value=0.51, top_pc2_loader="Y2",
            top_pc2_loading_abs=0.62, mean_off_diag_abs_rho=0.25,
        )),
    ],
}


# ---------- Stopwords for T8 content-word extraction --------------
_T8_STOPWORDS = frozenset([
    "a", "an", "the",
    "is", "are", "was", "were", "be", "been", "being", "am",
    "has", "have", "had", "having", "do", "does", "did", "doing",
    "will", "would", "can", "could", "shall", "should", "may",
    "might", "must",
    "of", "in", "on", "at", "to", "for", "with", "by", "from", "as",
    "into", "onto", "about", "against", "during", "before", "after",
    "over", "under", "between", "through", "across", "without", "within",
    "and", "or", "but", "nor", "so", "yet",
    "it", "its", "this", "that", "these", "those", "they", "them",
    "their", "there", "here", "which", "who", "whom", "whose", "what",
    "not", "no", "also", "however", "although", "though", "because",
    "while", "when", "where",
    "s",
])

_CONTENT_WORD_RE = re.compile(r"[A-Za-z']+")


def _content_words(sentence: str) -> set:
    lowered = sentence.lower()
    tokens = _CONTENT_WORD_RE.findall(lowered)
    return {t for t in tokens if t not in _T8_STOPWORDS and len(t) > 1}


def _split_sentences(text: str) -> list:
    """Split on '. ' plus end-of-string period."""
    cleaned = text.strip()
    if cleaned.endswith("."):
        cleaned = cleaned[:-1]
    parts = re.split(r"\.\s+", cleaned)
    return [p.strip() + "." for p in parts if p.strip()]


class TestT8TierActionNonOverlap(unittest.TestCase):
    """T8 — Tier 1's final sentence (where the actionable recommendation
    lives) must not be re-stated in Tier 2. Enforced by content-word
    Jaccard similarity < 0.5 between the final Tier 1 sentence and every
    Tier 2 sentence."""

    JACCARD_THRESHOLD = 0.5

    def test_all_specs_all_cases(self):
        failures = []
        for tech_id, cases in _FIXTURES.items():
            for case_name, results in cases:
                out = build_interpretation(tech_id, results)
                tier1 = out.get("tier1", "")
                tier2 = out.get("tier2", "")
                if not tier1 or not tier2:
                    continue
                t1_sentences = _split_sentences(tier1)
                if not t1_sentences:
                    continue
                t1_final = t1_sentences[-1]
                t1_words = _content_words(t1_final)
                if not t1_words:
                    continue
                for t2_sentence in _split_sentences(tier2):
                    t2_words = _content_words(t2_sentence)
                    if not t2_words:
                        continue
                    union = t1_words | t2_words
                    if not union:
                        continue
                    jaccard = len(t1_words & t2_words) / len(union)
                    if jaccard >= self.JACCARD_THRESHOLD:
                        failures.append(
                            f"{tech_id}/{case_name}: Jaccard={jaccard:.2f} "
                            f"between T1-final and T2-sentence: "
                            f"T1={t1_final!r} vs T2={t2_sentence!r}"
                        )
        self.assertFalse(
            failures,
            "T8 Jaccard violations:\n  " + "\n  ".join(failures)
        )


# ---------- T9 verb whitelist (dangling single-statistic check) ------
_T9_VERBS = frozenset([
    "is", "are", "was", "were", "has", "have", "had", "be", "been",
    "shows", "show", "indicates", "indicate", "suggests", "suggest",
    "rejects", "reject", "fails", "fail", "fits", "fit",
    "explains", "explain", "captures", "capture", "exceeds", "exceed",
    "lies", "sits", "sit", "falls", "fall", "passes", "pass",
    "reveals", "reveal", "drives", "drive", "contains", "contain",
    "holds", "hold", "differs", "differ", "remains", "remain",
    "becomes", "become", "stays", "stay", "leads", "lead",
    "lags", "lag", "follows", "follow", "uses", "use", "used",
    "applies", "apply", "gives", "give", "takes", "take",
    "means", "mean", "implies", "imply", "reports", "report",
    "estimates", "estimate", "accounts", "account",
    "tests", "test", "models", "model", "computes", "compute",
    "calculates", "calculate", "derives", "derive", "returns", "return",
    "matches", "match", "requires", "require", "spans", "span",
    "covers", "cover", "ranges", "range", "notes", "note",
    "compares", "compare", "considers", "consider",
    "decays", "decay", "accumulates", "accumulate", "moves", "move",
    "retains", "retain", "drops", "drop", "includes", "include",
    "excludes", "exclude", "affects", "affect", "supports", "support",
    "shifts", "shift", "tracks", "track", "rises", "rise",
    "clusters", "cluster", "agrees", "agree", "persists", "persist",
    "finds", "find", "identifies", "identify", "places", "place",
    "lands", "land",
    "governs", "govern", "widens", "widen", "yields", "yield",
    "establishes", "establish", "rules", "rule",
    "fades", "fade", "converges", "converge", "converged",
    "split", "splits", "characterize", "characterizes",
    "do", "does", "did",
    "make", "makes", "made", "created", "creates",
    "resolves", "resolve", "resolved",
    "sum", "sums", "summed",
    "form", "forms", "formed",
    "appear", "appears", "appeared",
    "run", "runs", "ran",
    "incorporate", "incorporates", "carry", "carries",
    "treat", "treats", "inspect", "inspects", "corroborate",
    "verify", "verifies", "verified",
    "refit", "refits", "difference", "differences",
    "serves", "serve", "lies",
    "reaches", "reach", "reached", "computed", "fit", "fits",
])

_T9_STAT_RE = re.compile(
    r"[=≈<>]\s*-?\d+\.?\d*|\b\d+\.?\d+\b|\b\d+\s*%"
)


def _sentence_has_verb(sentence: str) -> bool:
    tokens = [t.lower() for t in _CONTENT_WORD_RE.findall(sentence)]
    return any(t in _T9_VERBS for t in tokens)


def _is_dangling_stat_sentence(sentence: str) -> bool:
    clean = sentence.strip()
    # Fixture-validated rules:
    #   1. Ends with period
    #   2. Alphabetic word-count <= 15
    #   3. Contains a stat value
    #   4. Contains no verb from the whitelist
    if not clean.endswith("."):
        return False
    if clean.startswith("("):
        return False
    tokens = _CONTENT_WORD_RE.findall(clean)
    if len(tokens) > 15:
        return False
    if not _T9_STAT_RE.search(clean):
        return False
    return not _sentence_has_verb(clean)


class TestT9NoDanglingSingleStat(unittest.TestCase):
    """T9 — No sentence in Tier 2 may be a dangling single-statistic
    fragment (a short period-terminated clause that cites a number with
    no verb)."""

    def test_fixture_must_flag(self):
        """Self-test: sentences that MUST flag as dangling."""
        for s in [
            "Schwert bound 17 on 499 observations.",
            "AIC = 6721.3.",
        ]:
            self.assertTrue(
                _is_dangling_stat_sentence(s),
                f"Fixture should flag: {s!r}"
            )

    def test_fixture_must_not_flag(self):
        """Self-test: sentences that MUST NOT flag."""
        for s in [
            "The series shows no material linear trend.",
            "Augmented Dickey-Fuller rejects the unit-root null at the 1% level (ADF=-10.55, p<0.0001).",
        ]:
            self.assertFalse(
                _is_dangling_stat_sentence(s),
                f"Fixture should NOT flag: {s!r}"
            )

    def test_all_specs_all_cases(self):
        failures = []
        for tech_id, cases in _FIXTURES.items():
            for case_name, results in cases:
                out = build_interpretation(tech_id, results)
                tier2 = out.get("tier2", "")
                if not tier2:
                    continue
                for sentence in _split_sentences(tier2):
                    if _is_dangling_stat_sentence(sentence):
                        failures.append(
                            f"{tech_id}/{case_name}: dangling stat "
                            f"sentence {sentence!r}"
                        )
        self.assertFalse(
            failures,
            "T9 dangling-stat violations:\n  " + "\n  ".join(failures)
        )


class TestT10RegistryGrowth(unittest.TestCase):
    """T10 — The registry exposes the full Prompt A + Prompt B spec set."""

    EXPECTED = {
        # Prompt A + B (8)
        "adf_test",
        "granger_causality",
        "rolling_ccf_lag",
        "vecm_model",
        "var_model",
        "garch_model",
        "markov_switching",
        "pca_analysis",
        # Prompt C1 (26): Decomposition, Missing Data, Change Points,
        # Stationarity, Causality, Regimes, Evaluation
        "classical_decompose",
        "stl_decompose",
        "mstl_decompose",
        "x13_seasonal_adjust",
        "denton_chowlin_disaggregation",
        "kalman_imputation",
        "loess_interpolation",
        "bocpd",
        "cusum_page_hinkley",
        "intervention_analysis",
        "pelt_change_points",
        "stl_esd_anomaly",
        "kpss_test",
        "pp_test",
        "cross_correlation_lag",
        "prewhitened_ccf_lag",
        "dtw_alignment_lag",
        "gcc_phat_delay",
        "hmm",
        "star_model",
        "tar_setar",
        "block_bootstrap",
        "conformal_intervals",
        "forecast_combination",
        "robust_estimators",
        "rolling_origin_cv",
        # Prompt C2 (7): Forecasting Classical family
        "arima",
        "auto_arima",
        "ets",
        "holt_winters",
        "theta",
        "intermittent_demand",
        "prophet",
        # Prompt C3 (4): State Space family
        # (kalman_filter, kalman_smoother deferred — see registry.py
        # topology comment and follow-up backlog)
        "local_level",
        "local_linear_trend",
        "structural_ts",
        "particle_filter",
        # Prompt C4 (7): Frequency Domain family
        "fft_spectrum",
        "periodogram_spectral_density",
        "lomb_scargle",
        "wavelet_transform",
        "wavelet_coherence",
        "ssa_model",
        "emd_hht",
        # Prompt C5 (7): Multivariate remainder
        "arimax",
        "sarimax",
        "bvar",
        "dynamic_factor_model",
        "forecast_reconciliation",
        "johansen_cointegration",
        "transfer_function",
        # Prompt C6 (4): Volatility / Risk remainder
        "evt_pot_gpd",
        "stochastic_volatility",
        "har_rv",
        "caviar_quantile_dynamics",
        # Prompt C7 (15): ML / Deep Learning family
        "random_forest_forecast",
        "xgboost_forecast",
        "lightgbm_forecast",
        "gradient_boosting_forecast",
        "lstm_gru_forecast",
        "tcn_forecast",
        "transformer_forecast",
        "nbeats_forecast",
        "nhits_forecast",
        "nar_narx",
        "gaussian_process_forecast",
        "quantile_regression",
        "svr_forecast",
        "echo_state_network",
        "autoencoder_anomaly",
        # Follow-up 1b (1): TBATS / BATS multi-seasonal forecaster
        "tbats_forecast",
    }

    def test_registry_contains_expected_techniques(self):
        from interpretation import list_registered
        registered = set(list_registered())
        self.assertEqual(
            registered, self.EXPECTED,
            f"Registry mismatch. Expected: {sorted(self.EXPECTED)}. "
            f"Got: {sorted(registered)}."
        )


class TestT12NoBareParentheticalNumbers(unittest.TestCase):
    """T12 — No Tier 2 citation may contain a bare parenthetical number
    of the form ``(…, 0.NNNN)`` where the second value is a decimal
    without a label. This is the missing-``p=`` bug pattern, which
    previously slipped past T4 (Greek citation) and T9 (dangling stat)
    because it appears inside an otherwise-grammatical sentence.

    The regex ``r',\\s*[-]?0?\\.\\d+\\)'`` matches ``, 0.0020)`` and
    ``, -.5)`` and ``, 0.5)`` — comma, optional space, optional sign,
    optional leading zero, period, digits, closing paren — with no
    intervening label. Tuples of two numbers whose second value has a
    non-zero integer part (``(1, -1.080)``, ``(1, 3.40)``) are not
    matched and remain permitted."""

    _BARE_PAREN_RE = re.compile(r",\s*[-]?0?\.\d+\)")

    def test_all_specs_all_cases(self):
        failures = []
        for tech_id, cases in _FIXTURES.items():
            for case_name, results in cases:
                out = build_interpretation(tech_id, results)
                tier2 = out.get("tier2", "")
                if not tier2:
                    continue
                for m in self._BARE_PAREN_RE.finditer(tier2):
                    span = m.group(0)
                    # Show a small context window
                    start = max(0, m.start() - 30)
                    end = min(len(tier2), m.end() + 10)
                    failures.append(
                        f"{tech_id}/{case_name}: bare parenthetical "
                        f"number {span!r} in Tier 2 context "
                        f"{tier2[start:end]!r}"
                    )
        self.assertFalse(
            failures,
            "T12 bare-parenthetical-number violations:\n  "
            + "\n  ".join(failures)
        )


class TestT11PresetGatedClaims(unittest.TestCase):
    """T11 — Every spec module declares a ``PRESET_GATED_KEYS`` constant
    naming the input-dict keys that may be absent under lower presets
    (e.g., Fast drops the reverse-direction Granger test). Tier 1
    builders must branch on presence rather than assert unconditional
    claims about preset-gated facts (§4.4 honest disclosure)."""

    _EXPECTED_SPEC_MODULES = {
        "adf_test",
        "granger_causality",
        "rolling_ccf_lag",
        "vecm_model",
        "var_model",
        "garch_model",
        "markov_switching",
        "pca_analysis",
    }

    def test_all_specs_declare_preset_gated_keys(self):
        import importlib
        missing = []
        for tech_id in self._EXPECTED_SPEC_MODULES:
            module = importlib.import_module(
                f"interpretation.specs.{tech_id}"
            )
            if not hasattr(module, "PRESET_GATED_KEYS"):
                missing.append(tech_id)
                continue
            gated = module.PRESET_GATED_KEYS
            self.assertIsInstance(
                gated, tuple,
                f"{tech_id}.PRESET_GATED_KEYS must be a tuple; "
                f"got {type(gated).__name__}"
            )
            for key in gated:
                self.assertIsInstance(
                    key, str,
                    f"{tech_id}.PRESET_GATED_KEYS entries must be strings"
                )
        self.assertFalse(
            missing,
            f"Specs missing PRESET_GATED_KEYS: {missing}"
        )

    def test_granger_fast_preset_tier1_no_reverse_claim(self):
        """Under the Fast preset, reverse_f and reverse_p are absent.
        Tier 1 must not assert the reverse channel result, and must
        disclose that the reverse test was not run."""
        fast_fixture = dict(
            series_name_x="X", series_name_y="Y",
            best_lag=2, best_f=8.40, best_p=0.0003,
            max_lag=8, n_obs=286, significance=0.05,
            # reverse_f and reverse_p intentionally absent
        )
        out = build_interpretation("granger_causality", fast_fixture)
        tier1 = out["tier1"]
        banned_phrases = [
            "reverse channel is not significant",
            "reverse direction is also non-significant",
            "reverse channel is significant",
            "also rejects",
            "also significant",
        ]
        for phrase in banned_phrases:
            self.assertNotIn(
                phrase, tier1,
                f"Tier 1 under Fast preset must not claim reverse-direction "
                f"results. Found banned phrase {phrase!r} in: {tier1!r}"
            )
        # Must instead disclose that the reverse test was not run
        self.assertIn(
            "not tested at this preset", tier1,
            f"Tier 1 under Fast preset must disclose that the reverse "
            f"direction was not tested. Got: {tier1!r}"
        )

    def test_granger_fast_preset_tier2_acknowledges_missing_reverse(self):
        """Tier 2 under Fast preset must also acknowledge the missing
        reverse test rather than asserting a reverse-direction result."""
        fast_fixture = dict(
            series_name_x="X", series_name_y="Y",
            best_lag=2, best_f=8.40, best_p=0.0003,
            max_lag=8, n_obs=286, significance=0.05,
        )
        out = build_interpretation("granger_causality", fast_fixture)
        tier2 = out["tier2"]
        self.assertIn(
            "reverse-direction test was not run", tier2,
            f"Tier 2 under Fast preset must disclose that the reverse "
            f"test was not run. Got: {tier2!r}"
        )


class TestMarkovSwitchingVarianceDominantLabels(unittest.TestCase):
    """Under ``sort_axis="std"`` (the variance-dominant regime-labeling
    path added in Prompt 2 of the Markov batch), the rendered Tier 1
    must use σ-based labels (``low-σ regime``, ``high-σ regime``) and
    ``"standard deviation"`` in the sort-axis prose. The default
    ``sort_axis="mean"`` path continues to emit mean-based labels and
    is guarded by the existing ``two_regime`` / ``three_regime``
    fixtures via T4/T8/T9/T10/T11/T12.

    This test directly validates the spec's label-vs-prose translation
    for the variance-dominant case on the ``two_regime_variance_dominant``
    fixture (Real GDP Q/Q SAAR analogue: μ=(3.00, 3.60), σ=(1.86, 6.48))."""

    def test_variance_dominant_tier1_uses_sigma_labels(self):
        fixture = dict(_FIXTURES["markov_switching"][2][1])  # "two_regime_variance_dominant"
        out = build_interpretation("markov_switching", fixture)
        tier1 = out["tier1"]

        # Must contain σ-based regime labels.
        self.assertTrue(
            "low-σ" in tier1 or "high-σ" in tier1,
            f"Variance-dominant Tier 1 must use 'low-σ' / 'high-σ' "
            f"regime labels. Got: {tier1!r}"
        )

        # Must use full-prose form for the sort axis.
        self.assertIn(
            "standard deviation", tier1,
            f"Variance-dominant Tier 1 must say 'standard deviation' in "
            f"the sort-axis prose (not 'std' nor 'σ' in prose position). "
            f"Got: {tier1!r}"
        )

        # Must NOT contain mean-based labels (regression guard — the
        # hardcoded axis="mean" was removed in this prompt).
        self.assertNotIn(
            "low-mean", tier1,
            f"Variance-dominant Tier 1 must not emit 'low-mean' "
            f"labels. Got: {tier1!r}"
        )
        self.assertNotIn(
            "high-mean", tier1,
            f"Variance-dominant Tier 1 must not emit 'high-mean' "
            f"labels. Got: {tier1!r}"
        )

    def test_mean_dominant_tier1_still_uses_mean_labels(self):
        """Regression guard: the default ``sort_axis="mean"`` fixtures
        must continue to emit mean-based labels after the spec wiring
        change."""
        fixture = dict(_FIXTURES["markov_switching"][0][1])  # "two_regime"
        out = build_interpretation("markov_switching", fixture)
        tier1 = out["tier1"]
        self.assertTrue(
            "low-mean" in tier1 or "high-mean" in tier1,
            f"Mean-dominant Tier 1 must use 'low-mean' / 'high-mean' "
            f"regime labels. Got: {tier1!r}"
        )
        self.assertNotIn(
            "low-σ", tier1,
            f"Mean-dominant Tier 1 must not emit σ-labels. Got: {tier1!r}"
        )
        self.assertNotIn(
            "high-σ", tier1,
            f"Mean-dominant Tier 1 must not emit σ-labels. Got: {tier1!r}"
        )


class TestT13C1RegistryInventory(unittest.TestCase):
    """T13 — After Prompt C1 lands, the registry contains at least the
    Prompt A + Prompt B + Prompt C1 specs, totaling 34 techniques. Later
    prompts (C2-C7) extend the registry; T13 pins the C1 minimum so
    regressions in the C1 scope get caught immediately."""

    def test_at_least_34_specs_registered(self):
        from interpretation import list_registered
        registered = list_registered()
        self.assertGreaterEqual(
            len(registered), 34,
            f"Expected at least 34 registered specs (Prompt A/B: 8 + "
            f"Prompt C1: 26). Got {len(registered)}: {sorted(registered)}"
        )


class TestT16C2RegistryInventory(unittest.TestCase):
    """T16 — After Prompt C2 landed, the registry contained the
    Prompt A + Prompt B + Prompt C1 + Prompt C2 specs, totaling 41
    techniques. C3 extends the registry; T16 now pins the C2
    minimum so regressions against the C2 set get caught immediately.
    T17 pins the exact C3 count."""

    def test_at_least_41_specs_registered(self):
        from interpretation import list_registered
        registered = list_registered()
        self.assertGreaterEqual(
            len(registered), 41,
            f"Expected at least 41 registered specs (Prompt A/B: 8 + "
            f"Prompt C1: 26 + Prompt C2: 7). Got {len(registered)}: "
            f"{sorted(registered)}"
        )


class TestT17C3RegistryInventory(unittest.TestCase):
    """T17 — After Prompt C3 landed, the registry contained at least
    45 specs (41 + 4 State Space). C4 extends further; T17 now pins
    the C3 minimum. T18 pins the exact C4 count."""

    def test_at_least_45_specs_registered(self):
        from interpretation import list_registered
        registered = list_registered()
        self.assertGreaterEqual(
            len(registered), 45,
            f"Expected at least 45 registered specs (Prompt A/B: 8 + "
            f"Prompt C1: 26 + Prompt C2: 7 + Prompt C3: 4). Got "
            f"{len(registered)}: {sorted(registered)}"
        )


class TestT18C4RegistryInventory(unittest.TestCase):
    """T18 — After Prompt C4 landed, the registry contained at least 52
    specs (45 baseline + 7 Frequency Domain). Prompt C5 grows the set
    further; T18 now pins the C4 minimum and T19 pins the exact C5
    count."""

    def test_at_least_52_specs_registered(self):
        from interpretation import list_registered
        registered = list_registered()
        self.assertGreaterEqual(
            len(registered), 52,
            f"Expected at least 52 registered specs (Prompt A/B: 8 + "
            f"Prompt C1: 26 + Prompt C2: 7 + Prompt C3: 4 + Prompt "
            f"C4: 7). Got {len(registered)}: {sorted(registered)}"
        )


class TestT19C5RegistryInventory(unittest.TestCase):
    """T19 — After Prompt C5 landed, the registry contained at least
    59 specs (52 baseline + 7 Multivariate remainder). Prompt C6 grows
    the set further; T19 now pins the C5 minimum and T20 pins the
    exact C6 count."""

    def test_at_least_59_specs_registered(self):
        from interpretation import list_registered
        registered = list_registered()
        self.assertGreaterEqual(
            len(registered), 59,
            f"Expected at least 59 registered specs (Prompt A/B: 8 + "
            f"Prompt C1: 26 + Prompt C2: 7 + Prompt C3: 4 + Prompt "
            f"C4: 7 + Prompt C5: 7). Got {len(registered)}: "
            f"{sorted(registered)}"
        )


class TestT20C6RegistryInventory(unittest.TestCase):
    """T20 — After Prompt C6 landed, the registry contained at least
    63 specs (59 baseline + 4 Volatility / Risk remainder). Prompt C7
    grows the set further; T20 now pins the C6 minimum and T21 pins
    the exact C7 count."""

    def test_at_least_63_specs_registered(self):
        from interpretation import list_registered
        registered = list_registered()
        self.assertGreaterEqual(
            len(registered), 63,
            f"Expected at least 63 registered specs (Prompt A/B: 8 + "
            f"Prompt C1: 26 + Prompt C2: 7 + Prompt C3: 4 + Prompt "
            f"C4: 7 + Prompt C5: 7 + Prompt C6: 4). Got "
            f"{len(registered)}: {sorted(registered)}"
        )


class TestT21C7RegistryInventory(unittest.TestCase):
    """T21 — After Prompt C7 landed, the registry contained at least
    78 specs (63 baseline + 15 ML / Deep Learning family). Follow-up
    1b grows the set further; T21 now pins the C7 minimum and T22
    pins the exact post-1b count."""

    def test_at_least_78_specs_registered(self):
        from interpretation import list_registered
        registered = list_registered()
        self.assertGreaterEqual(
            len(registered), 78,
            f"Expected at least 78 registered specs (Prompt A/B: 8 + "
            f"Prompt C1: 26 + Prompt C2: 7 + Prompt C3: 4 + Prompt "
            f"C4: 7 + Prompt C5: 7 + Prompt C6: 4 + Prompt C7: 15). "
            f"Got {len(registered)}: {sorted(registered)}"
        )


class TestT22FollowUp1bRegistryInventory(unittest.TestCase):
    """T22 — After Follow-up 1b lands (TBATS wrapper creation), the
    registry contains exactly 79 specs (78 C7 baseline + 1 tbats_
    forecast). TBATS was deferred from Prompt C2 because no wrapper
    existed at the time; Follow-up 1b created the wrapper and added
    the interpretation spec."""

    def test_exactly_79_specs_registered(self):
        from interpretation import list_registered
        registered = list_registered()
        self.assertEqual(
            len(registered), 79,
            f"Expected exactly 79 registered specs (78 C7 baseline + "
            f"1 Follow-up 1b tbats_forecast). Got {len(registered)}: "
            f"{sorted(registered)}"
        )


class TestT14NoRaiseOnMinimalInputs(unittest.TestCase):
    """T14 — Every registered spec's tier builders must not raise on
    a minimal-valid input dict. Catches the class of bug where a
    spec's tier builder references a key that isn't always present.

    Minimal-input strategy: construct a dict of just a few harmless
    keys (series_name + n_obs + a handful of numeric defaults), invoke
    build_interpretation, and assert it returns a non-error dict
    rather than propagating a KeyError or AttributeError.

    Tier text may be gibberish under minimal inputs — that's fine.
    The invariant is "does not raise"; correctness of content is
    the job of T4/T5/T6/T7/T8/T9/T11/T12 on realistic fixtures."""

    _MINIMAL_INPUT = {
        "series_name": "test_series",
        "series_name_x": "X",
        "series_name_y": "Y",
        "n_obs": 100,
        "n": 100,
        "k_regimes": 2,
        "period": 12,
        "order": 1,
        "max_lag": 8,
        "best_lag": 0,
        "best_f": 1.0,
        "best_p": 0.5,
        "significance": 0.05,
        "seasonal_strength": 0.5,
        "trend_strength": 0.5,
        "model_type": "additive",
        "two_sided": True,
        "alpha": 0.05,
        "regression": "c",
        "stat_value": 1.0,
        "crit_value": 1.0,
        "rejected": False,
        "p_value": 0.5,
        "horizon": 10,
        "n_missing": 0,
        "n_gaps": 0,
        "max_gap": 0,
        "n_folds": 5,
        "mean_mase": 0.9,
        "std_mase": 0.1,
        "n_cps": 0,
        "n_change_points": 0,
        "n_anomalies": 0,
        "n_anomalies_upward": 0,
        "n_anomalies_downward": 0,
        "n_alarms_total": 0,
        "n_alarms_upward": 0,
        "n_alarms_downward": 0,
        "n_interventions": 0,
        "n_significant": 0,
        "target_coverage": 0.95,
        "avg_interval_width": 1.0,
        "n_models": 3,
        "n_resamples": 1000,
        "block_length": 10,
        "mean": 0.0,
        "median": 0.0,
        "std": 1.0,
        "mad_scale": 0.8,
        "regime_means": [0.0, 1.0],
        "regime_stds": [1.0, 1.0],
        "current_regime": 0,
        "current_prob": 0.5,
        "expected_durations": [10.0, 10.0],
        "final_period_probs": [0.5, 0.5],
        "sort_axis": "mean",
        # Prompt C2 forecasting-family fields
        "fit_rmse": 1.0,
        "baseline_rmse": 1.5,
        "baseline_label": "last-value naive",
        "last_observed_value": 1.0,
        "forecast_end_value": 1.0,
        "series_std": 1.0,
        "series_min": 0.5,
        "ljung_box_lag10_pvalue": 0.5,
        "seasonal_order": [0, 0, 0, 0],
        "ic": "aic",
        "stepwise": True,
        "n_candidates_searched": 10,
        "max_p": 5,
        "max_q": 5,
        "max_d": 2,
        "max_P": 2,
        "max_Q": 2,
        "max_D": 1,
        "seasonal_period_m": 12,
        "m_inferred_from_freq": False,
        "frequency": "M",
        "aic": 100.0,
        "bic": 110.0,
        "trend_type": "add",
        "seasonal_type": "mul",
        "seasonal_period": 12,
        "damped_trend": False,
        "beta": 0.1,
        "gamma": 0.1,
        # C6: phi was previously None (safe for ETS/HW via None guard).
        # Now set to 0.9 for SV (persistence parameter); ETS/HW still
        # tolerate via the same None guard path since the check is
        # ``if phi is not None``, which renders "damping φ=0.900" under
        # T14 minimal input — harmless for the no-raise invariant.
        "phi": 0.9,
        "deseasonalized": True,
        "method": "croston",
        "forecast_mean_per_period": 1.0,
        "baseline_mean": 1.0,
        "demand_pattern": "intermittent",
        "adi": 2.0,
        "cv2_demand": 0.3,
        "zero_rate": 0.5,
        "last10_all_zero": False,
        "backend": "prophet",
        "changepoint_prior_scale": 0.05,
        "yearly_seasonality_flag": "auto",
        "weekly_seasonality_flag": "False",
        "n_candidate_changepoints": 10,
        "most_recent_candidate_changepoint": "2000-01",
        "r2": 0.9,
        "historical_max": 10.0,
        "interval_width": 0.95,
        # Prompt C3 State Space fields
        "q_ratio": 0.5,
        "q_band_label": "moderate",
        "smoothed_final_level": 100.0,
        "smoothed_final_slope": 1.0,
        "sigma_trend": 0.1,
        "slope_adaptivity": 0.1,
        "slope_adaptivity_band": "moderately adaptive",
        "damped_not_wired": False,
        "components": ["Level", "Trend"],
        "variance_decomposition": {
            "Level": {"variance": 10.0, "pct_of_total": 80.0},
            "Trend": {"variance": 1.0, "pct_of_total": 10.0},
            "Residual": {"variance": 0.5, "pct_of_total": 10.0},
        },
        "dominant_component": "Level",
        "level_type": "local level",
        "cycle_enabled": False,
        "ar_order": 0,
        "durbin_watson": 2.0,
        "model_type": "local_level",
        "n_particles": 500,
        "sigma_state": 0.5,
        "sigma_obs": 0.5,
        "avg_ess": 250.0,
        "min_ess": 50.0,
        "n_resamples": 100,
        "resample_threshold": 0.5,
        "log_likelihood": -100.0,
        # Prompt C4 Frequency Domain fields
        "series_name_x": "X",
        "series_name_y": "Y",
        "dominant_frequency": 0.1,
        "dominant_period": 10.0,
        "top_peak_power_pct": 20.0,
        "top_peaks_power_pct": 50.0,
        "sampling_frequency": 1.0,
        "nyquist_frequency": 0.5,
        "frequency_resolution": 0.01,
        "total_power": 100.0,
        "spectral_entropy": 0.5,
        "spectral_centroid": 0.05,
        "spectral_bandwidth": 0.1,
        "spectral_edge_95": 0.2,
        "estimator_variant": "raw",
        # NOTE: "window" intentionally omitted from minimal input — it's
        # read as int by rolling_ccf_lag.py and as string by fft/periodogram
        # specs. Each spec's default handles absence.
        "detrend": "linear",
        "time_span": 100.0,
        "oversampling": 5,
        "n_freqs": 500,
        "fap_method": "baluev",
        "max_power": 0.2,
        "fap_at_dominant_peak": 0.05,
        "sampling_irregularity_cv": 0.0,
        "wavelet": "db4",
        "level": 3,
        "max_level": 4,
        "mode": "symmetric",
        "dominant_component": "Approximation (A)",
        "dominant_energy_pct": 80.0,
        "filter_length": 8,
        "detail_band_energies_pct": {"Detail D1": 5.0, "Detail D2": 10.0},
        "detail_band_periods": {"Detail D1": "2-4 obs", "Detail D2": "4-8 obs"},
        "dominant_band_period_range": "> 16 obs",
        "n_scales": 32,
        "smoothing_width": 5,
        "global_mean_coherence": 0.4,
        "max_coherence": 0.9,
        "best_scale": 10.0,
        "best_period": 10.0,
        "best_scale_coherence": 0.6,
        "best_scale_lag": 2.0,
        "high_coherence_pct": 25.0,
        "phase_degrees_at_dominant_scale": 45.0,
        "direction_verb": "leads",
        "window_length": 50,
        "n_components": 10,
        "n_groups": 5,
        "explained_variance_pct_1": 70.0,
        "components_for_95pct": 3,
        "components_for_99pct": 8,
        "total_variance": 100.0,
        "dominant_group_share": 70.0,
        "second_group_share": 15.0,
        "backend": "emd",
        "n_imfs": 3,
        "max_imfs": 5,
        "dominant_imf": 1,
        "dominant_imf_variance_pct": 40.0,
        "dominant_imf_period": 5.0,
        "per_imf_periods": [5.0, 10.0, 20.0],
        "residual_variance_pct": 20.0,
        # Prompt C5 Multivariate remainder fields
        # arimax / sarimax (inherit forecaster fields above, plus):
        "exog_count": 0,
        "exog_names": [],
        "exog_coefs": [],
        "converged": True,
        "jarque_bera_pvalue": 0.5,
        # bvar (inherit var_model fields where applicable, plus):
        "variables": ["A", "B", "C"],
        "n_variables": 3,
        "lags": 2,
        "lambda1": 0.1,
        "lambda2": 1.0,
        "lambda3": 1.0,
        "n_effective": 90,
        "n_draws": 1000,
        "total_params": 21,
        "bic_approx": 200.0,
        "rmse": {"A": 1.0, "B": 1.0, "C": 1.0},
        "prior_tightness_band": "moderate",
        "credible_interval_coverage": 0.90,
        "interval_type": "credible",
        # dynamic_factor_model
        "k_factors": 1,
        "factor_order": 2,
        "error_order": 1,
        "variance_explained_pct": 50.0,
        "n_observations": 100,
        "loadings_per_factor": [[0.8, 0.6, 0.4]],
        "communalities": [0.7, 0.5, 0.3],
        # forecast_reconciliation
        "top_series": "Total",
        "bottom_series": ["A", "B"],
        "n_bottom": 2,
        "methods": ["bottom_up"],
        "primary_method": "bottom_up",
        "primary_method_fell_back": False,
        "base_forecaster": "naive",
        "relative_incoherence": 0.0,
        # johansen_cointegration
        "variable_names": ["A", "B", "C"],
        "lag_order": 2,
        "det_order": 0,
        "trace_rank": 1,
        "max_eig_rank": 1,
        "trace_stat_at_decision": 30.0,
        "trace_cv_at_decision": 29.8,
        # NOTE: ``significance_level`` is intentionally omitted. ADF
        # reads it as a float (converted via ``float(...)``) whereas
        # Johansen reads it as a display string (``"5%"``); a single
        # minimal-input value can't satisfy both spec contracts, so
        # each spec falls back to its own default when the key is
        # absent.
        "eigenvalues": [0.1, 0.05, 0.01],
        "rank_implication_label": "VECM",
        "first_cointegrating_vector": [1.0, -0.5, 0.2],
        "tests_agree": True,
        # transfer_function
        "y_series": "Y",
        "x_series": "X",
        "polynomial": "unrestricted",
        "r_squared": 0.5,
        "adj_r_squared": 0.45,
        "rmse": 1.0,
        "long_run_multiplier": 0.3,
        "peak_lag": 1,
        "peak_lag_weight": 0.4,
        # Prompt C6 Volatility / Risk remainder fields
        # evt_pot_gpd
        "xi": 0.25,
        "sigma": 1.0,
        "threshold": 2.0,
        "threshold_quantile": 0.975,
        "n_exceedances": 50,
        "exceedance_rate": 0.025,
        "tail": "lower",
        "ks_stat": 0.05,
        "ks_pval": 0.5,
        "confidence_levels": [0.95, 0.99, 0.999],
        "var_values": [1.5, 3.0, 6.0],
        "es_values": [2.0, 4.0, 8.0],
        "is_time_series_input": True,
        "exceedances_below_30": False,
        # stochastic_volatility (phi already above; mu already above
        # from markov_switching shared key — compatible semantically
        # with SV as log-variance level, both are numeric)
        "sigma_eta": 0.2,
        "neg_loglik": 3000.0,
        "filtered_vol_min": 0.1,
        "filtered_vol_max": 5.0,
        "smoothed_vol_min": 0.15,
        "smoothed_vol_max": 4.5,
        "input_kurtosis": 10.0,
        "unconditional_log_vol_std": 0.5,
        "innovation_distribution": "Gaussian",
        # har_rv
        "use_log": False,
        "beta_d": 0.2,
        "beta_w": 0.4,
        "beta_m": 0.1,
        "persistence_sum": 0.7,
        "R2": 0.25,
        "R2_adj": 0.24,
        # caviar_quantile_dynamics (theta already present with
        # CAViaR-compatible numeric semantics; quantile_theta is our
        # alias alternative)
        "specification": "SAV",
        "parameter_names": ["beta_0", "beta_1", "beta_2"],
        "parameters": [0.02, 0.8, -0.4],
        "quantile_loss": 0.1,
        "n_violations": 50,
        "expected_violations": 50.0,
        "violation_ratio": 1.0,
        "kupiec_stat": 0.01,
        "kupiec_pval": 0.9,
        "christoffersen_stat": 1.0,
        "christoffersen_pval": 0.3,
        "dq_stat": 5.0,
        "dq_pval": 0.4,
        "distribution_free": True,
        "quantile_theta": 0.05,
        "theta": 0.05,  # CAViaR quantile level; no existing collision
        # Prompt C7 ML / Deep Learning fields
        # Tree cohort
        "n_estimators": 100,
        "max_depth": 6,
        "min_samples_leaf": 2,
        "learning_rate": 0.1,
        "subsample": 1.0,
        "num_leaves": 15,
        "train_rmse": 10.0,
        "train_mae": 8.0,
        "train_r2": 0.9,
        "cv_rmse": 15.0,
        "top_feature": "lag_1",
        "top_features": [
            {"name": "lag_1", "importance": 0.5},
            {"name": "lag_2", "importance": 0.2},
        ],
        "backend": "sklearn",
        # Neural sequence cohort
        "hidden_size": 32,
        "n_layers": 1,
        "epochs": 50,
        "final_loss": 0.1,
        "initial_loss": 1.0,
        "loss_curve_summary": {
            "initial": 1.0, "final": 0.1, "median_middle_30pct": 0.3, "n_epochs": 50,
        },
        "model_type": "lstm",  # used by lstm_gru_forecast
        "n_channels": [16, 16],
        "kernel_size": 3,
        "receptive_field": 8,
        "d_model": 32,
        "n_heads": 2,
        "n_encoder_layers": 1,
        "dim_feedforward": 64,
        "n_params": 1000,
        # Neural decomposition cohort
        "stack_types": ["generic"],
        "n_blocks": 2,
        "n_stacks": 2,
        "pooling_sizes": [2, 1],
        # nar_narx
        "ar_lags": 3,
        "hidden_layers": [10],
        "activation": "relu",
        "alpha_reg": 1e-4,
        "rmse_insample": 5.0,
        "mae_insample": 3.0,
        "r_squared": 0.3,
        "rmse_cv": None,
        "n_effective": 200,
        "n_features": 3,
        "training_iters": 100,
        "exogenous": [],
        "exog_lags": None,
        "model": "NAR",
        # GP
        "kernel_type": "rbf",
        "kernel_params": "RBF(length_scale=1.0)",
        "log_marginal_likelihood": -100.0,
        "avg_forecast_std": 1.0,
        "length_scale": 1.0,
        "length_scale_lower_bound": 1e-5,
        # Quantile regression (overlap with CAViaR keys theta/quantiles is fine)
        "n_quantiles": 5,
        "quantiles": [0.05, 0.25, 0.5, 0.75, 0.95],
        "n_lags": 6,
        "train_rmse_median": 0.5,
        "n_crossings": 0,
        "top_features_per_quantile": {
            "0.500": [{"name": "lag_1", "importance": 0.5}],
        },
        # SVR
        # NOTE: `gamma` key is NOT re-set here — ETS / HW / STAR specs
        # also read `gamma` as a float smoothing parameter. SVR spec
        # renders `gamma` gracefully when None (the wrapper exports it
        # as the string "scale" in practice, which would clash with
        # ETS / HW numeric-gamma). The SVR-specific fixture instead
        # relies on the earlier numeric `gamma` value; at runtime the
        # wrapper's actual string "scale" routes through the SVR spec
        # which formats with !r.
        "kernel": "rbf",
        "C": 1.0,
        "epsilon": 0.1,
        "n_support_vectors": 50,
        "sv_ratio": 0.3,
        "scaling_applied": True,
        # ESN
        "reservoir_size": 100,
        "spectral_radius": 0.9,
        "leak_rate": 0.3,
        "input_scaling": 1.0,
        "ridge_alpha": 1e-4,
        "sparsity": 0.1,
        "warmup": 10,
        "r2": 0.8,
        "rmse": 1.5,
        "mae": 1.0,
        # Autoencoder anomaly
        "window_size": 5,
        "hidden_dim": 8,
        "contamination": 0.05,
        "threshold": 0.5,
        "threshold_type": "percentile_of_training_error",
        "anomaly_rate": 0.05,
        "mean_recon_error": 0.1,
        "max_recon_error": 1.0,
        "most_extreme_idx": 500,
        "most_extreme_error": 1.0,
        "anomaly_indices": [100, 200],
        # Follow-up 1b TBATS fields
        "seasonal_periods_used": [7.0],
        "seasonal_periods_filtered": [],
        "seasonal_periods_source": "auto-inferred",
        "use_trigonometric": True,
        "use_box_cox_selected": False,
        "box_cox_lambda": None,
        "use_arma_errors_selected": False,
        "use_damped_trend_selected": False,
        "n_harmonics_per_period": [1],
        "gamma_per_period": [1e-6, 1e-6],
        "bats_rounding_applied": [],
        # Follow-up 1c BVAR IRF/FEVD fields
        "irf_fevd_computed": False,
        "identification_scheme": None,
        "variable_ordering": None,
        "irf_horizon": None,
        "fevd_horizons": [],
        "own_shock_share_longest_horizon": {},
        "fevd_longest_horizon": None,
        "zero_straddle_pairs": [],
        "irf_skip_reason": "fast_preset_default",
        "sigma_posterior_uncertainty_propagated": False,
    }

    def test_all_registered_specs_no_raise(self):
        from interpretation import list_registered
        failures = []
        for tech_id in list_registered():
            try:
                out = build_interpretation(tech_id, dict(self._MINIMAL_INPUT))
                # Must be a dict with tier1/tier2/tier3 keys
                if not isinstance(out, dict):
                    failures.append(f"{tech_id}: returned non-dict {type(out).__name__}")
                    continue
                if set(out.keys()) != {"tier1", "tier2", "tier3"}:
                    failures.append(
                        f"{tech_id}: returned keys {set(out.keys())} "
                        f"instead of {{tier1, tier2, tier3}}"
                    )
            except Exception as e:
                failures.append(f"{tech_id}: {type(e).__name__}: {e}")
        self.assertFalse(
            failures,
            "Specs raised on minimal-input probe:\n  " + "\n  ".join(failures)
        )


class TestT15NoProgrammaticTokenLeaks(unittest.TestCase):
    """T15 — No programmatic tokens (identifiers with underscores)
    leak into user-facing tier text. Regression guard for Prompt C1
    post-eval FIX 1: pp_test's Tier 1 rendered "unit_root null"
    verbatim because ``null_direction`` — a programmatic equality-
    check key — flowed into prose without humanization.

    Scan only **unquoted** prose tokens — quoted series names,
    intervention labels, and math notation inside ``(s_t;γ,c)``-
    style expressions are user content or legitimate notation and
    must not be flagged. Content inside ``'...'`` quotes, ``"..."``
    quotes, or mathematical parenthesized expressions is stripped
    before scanning.

    A specific allowlist tolerates common inline notation that
    legitimately uses underscores outside quotes (e.g., ``t_stat``,
    ``p_value`` — though these specifically should not appear since
    specs render them as ``t-stat`` / ``p-value`` via FMT_P_VALUE).
    """

    _TOKEN_RE = re.compile(r"(?<![a-zA-Z0-9_])[a-zA-Z]+_[a-zA-Z]+(?![a-zA-Z0-9_])")

    # Allowlist: tokens that are legitimate in user-facing prose even
    # though they contain underscores. Three categories:
    _ALLOWED = {
        # (a) math notation subscripts (time-series state variables,
        # theta-lines, updating-equation state):
        "s_t", "y_t", "x_t", "z_t", "e_t", "u_t", "d_t", "p_t",
        "b_t", "ell_t", "q_t",
        "s_T", "y_T", "x_T",  # terminal-value subscripts
        # (b) programmatic parameter names that specs cite verbatim in
        # honest-disclosure prose (library API surface that users type):
        "max_p", "max_q", "max_d", "max_P", "max_Q", "max_D",
        "changepoint_prior_scale", "seasonality_prior_scale",
        "country_holidays", "initial_trend", "initial_level",
        "n_particles",
        # (c) technique_ids cited by name when a spec references a
        # companion technique (e.g., arima's Tier 2 mentions that
        # auto_arima would surface alternative orders):
        "auto_arima",
        # (c2) Prompt C3 — particle_filter model_type built-ins cited
        # in Tier 2 honest-disclosure prose (user-visible library API
        # surface that users type as param values):
        "local_level", "Local_level", "local_level_sv",
        "nonlinear_growth", "random_walk_sv",
        # (c3) Prompt C4 — cross-technique name references and
        # cross-spectral math notation:
        "wavelet_transform", "periodogram_spectral_density",
        "S_xy", "S_xx", "S_yy",  # cross/auto-spectrum subscripts
        # (c4) Prompt C5 — cross-technique name references and
        # programmatic parameter names that specs cite verbatim in
        # Tier 2 honest-disclosure prose (model-order misspecification
        # caveat for transfer_function; Johansen deterministic order
        # flag; cross-spec pointers between var_model/bvar and between
        # arimax and auto_arima):
        "var_model", "dynamic_factor_model",
        "forecast_reconciliation", "johansen_cointegration",
        "transfer_function",
        "max_lag", "ar_order", "det_order",
        # Uppercase state-variable subscript cited by
        # transfer_function's Box-Jenkins equation:
        "Y_t",
        # (c5) Prompt C6 — programmatic parameter names and
        # math-notation subscripts cited in Volatility/Risk specs:
        # har_rv Tier 2/3 cite ``use_log`` as the wrapper's user-
        # facing param name (same category as changepoint_prior_scale
        # / seasonality_prior_scale etc. from Prompt C2 Prophet);
        # stochastic_volatility's SV log-variance equation cites
        # ``h_t`` as the latent AR(1) state variable subscript (same
        # category as y_t / x_t etc. from the Prompt A allowlist).
        "use_log", "h_t",
        # (c7) Follow-up 1b — TBATS programmatic parameter names
        # cited in Tier 2 disclosure. The tbats library exposes these
        # as constructor kwargs that users set via ctx.params:
        "use_trigonometric", "use_box_cox", "use_arma_errors",
        "use_damped_trend", "seasonal_periods", "box_cox_lambda",
        "n_jobs",
        # (c6) Prompt C7 — ML/DL programmatic hyperparameter names
        # cited in Tier 2 disclosure (sklearn / PyTorch / library API
        # surface that users type as param values). Tree cohort,
        # neural cohort, GP, SVR, ESN, autoencoder hyperparameters.
        "max_depth", "learning_rate", "num_leaves", "colsample_bytree",
        "min_samples_leaf", "min_child_samples",
        "hidden_size", "n_layers", "n_estimators", "n_lags",
        "d_model", "n_heads", "dim_feedforward",
        "n_blocks", "n_stacks", "stack_types", "pooling_sizes",
        "reservoir_size", "spectral_radius", "leak_rate",
        "input_scaling", "ridge_alpha",
        "length_scale", "length_scales", "noise_level", "signal_variance",
        "hidden_dim", "window_size",
        "ar_lags", "exog_lags", "alpha_reg",
        "early_stopping", "weight_decay",
        "changepoint_range",
        # Cross-technique names cited in C7 specs (e.g., NBEATS
        # references NHITS; neural decomposition references Ridge /
        # GBR / MLP fallbacks):
        "random_forest_forecast", "xgboost_forecast",
        "lightgbm_forecast", "gradient_boosting_forecast",
        "stl_esd_anomaly",
        # Math notation in C7 specs: W_out is the readout-weight
        # matrix in echo_state_network Tier 2 (same category as y_t /
        # x_t / h_t — state-variable subscript/suffix notation):
        "W_out",
        # (d) test-fixture identifier used by TestT14's minimal-input
        # probe — not a programmatic leak from production code:
        "test_series",
    }

    @staticmethod
    def _strip_quoted_and_math(text: str) -> str:
        """Remove content that legitimately contains underscore-bearing
        tokens: (a) single-quoted strings (series names, labels);
        (b) double-quoted strings; (c) parenthesized math expressions
        containing a semicolon (the convention for transition-function
        notation like ``G(s_t;γ,c)``)."""
        # Single-quoted
        text = re.sub(r"'[^']*'", "''", text)
        # Double-quoted
        text = re.sub(r'"[^"]*"', '""', text)
        # Parenthesized math (identified by inner semicolon)
        text = re.sub(r"\([^)]*;[^)]*\)", "(…)", text)
        return text

    def _scan_text(self, text: str, context: str, failures: list) -> None:
        scannable = self._strip_quoted_and_math(text)
        for match in self._TOKEN_RE.finditer(scannable):
            token = match.group(0)
            if token in self._ALLOWED:
                continue
            failures.append(f"{context}: token '{token}' in text: {text[:200]!r}")

    def test_no_underscored_tokens_in_t14_minimal_inputs(self):
        from interpretation import list_registered
        # Reuse T14's minimal input construction via import.
        minimal = TestT14NoRaiseOnMinimalInputs._MINIMAL_INPUT
        failures = []
        for tech_id in list_registered():
            try:
                out = build_interpretation(tech_id, dict(minimal))
            except Exception:
                continue
            if not isinstance(out, dict):
                continue
            for key in ("tier1", "tier2", "tier3"):
                val = out.get(key, "")
                if isinstance(val, list):
                    for item in val:
                        if isinstance(item, str):
                            self._scan_text(item, f"{tech_id}.{key}", failures)
                elif isinstance(val, str):
                    self._scan_text(val, f"{tech_id}.{key}", failures)
        self.assertFalse(
            failures,
            "Programmatic tokens leaked into rendered tier text:\n  "
            + "\n  ".join(failures)
        )

    def test_no_underscored_tokens_in_realistic_fixtures(self):
        failures = []
        for tech_id, cases in _FIXTURES.items():
            for case_name, fixture in cases:
                try:
                    out = build_interpretation(tech_id, dict(fixture))
                except Exception:
                    continue
                if not isinstance(out, dict):
                    continue
                ctx = f"{tech_id}[{case_name}]"
                for key in ("tier1", "tier2", "tier3"):
                    val = out.get(key, "")
                    if isinstance(val, list):
                        for item in val:
                            if isinstance(item, str):
                                self._scan_text(item, f"{ctx}.{key}", failures)
                    elif isinstance(val, str):
                        self._scan_text(val, f"{ctx}.{key}", failures)
        self.assertFalse(
            failures,
            "Programmatic tokens leaked in realistic fixtures:\n  "
            + "\n  ".join(failures)
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
