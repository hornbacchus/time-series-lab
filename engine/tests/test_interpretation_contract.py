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
    """T13 — After Prompt C1 lands, the registry contains exactly the
    Prompt A + Prompt B + Prompt C1 specs, totaling 34 techniques. If
    the set grows or shrinks unexpectedly, the registered-techniques
    list in test T10 catches the first deviation; this test pins the
    count independently."""

    def test_exactly_34_specs_registered(self):
        from interpretation import list_registered
        registered = list_registered()
        self.assertEqual(
            len(registered), 34,
            f"Expected exactly 34 registered specs (Prompt A/B: 8 + "
            f"Prompt C1: 26). Got {len(registered)}: {sorted(registered)}"
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
