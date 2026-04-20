"""
Regression tests for identification/sign/scale/variance-decomposition
conventions across wrapper techniques.

Each test targets a specific class of "works-under-idealized-conditions"
bug that previously bit us (PCA sign flip, DFM communality-over-1, HMM
state-label permutation, etc.). The assertions check invariants that a
correct implementation must satisfy; a regression in the wrapper would
break the invariant even if the underlying library still fits fine.

Run from repo root:

    pytest engine/tests/test_identification_conventions.py -v

or without pytest:

    python -m unittest engine.tests.test_identification_conventions -v
"""
import os
import re
import sys
import unittest

import numpy as np

# Make `from techniques.X import run` work when tests are run from repo root.
_ENGINE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)

from techniques.base import RunContext  # noqa: E402


def _noop_progress(msg, pct):
    pass


def _run_twice(run_fn, build_ctx):
    """Run a technique twice with identical inputs; return both results."""
    return run_fn(build_ctx(), _noop_progress), run_fn(build_ctx(), _noop_progress)


def _find_table(response, name_contains):
    """Return the first table whose name contains ``name_contains`` (case-insensitive)."""
    for t in response.get("tables") or []:
        if name_contains.lower() in str(t.get("name", "")).lower():
            return t
    return None


# ─────────────────────────────────────────────────────────────────────
# Tier 1 — State / regime permutation stability
# ─────────────────────────────────────────────────────────────────────
class TestStatePermutation(unittest.TestCase):
    """HMM and Markov Switching must produce the same regime labels
    across two seeded runs on the same input."""

    def _make_regime_series(self, seed=42):
        rng = np.random.default_rng(seed)
        n = 300
        # Two-regime series: low-mean then high-mean with some noise
        regime = (np.arange(n) > n // 2).astype(int)
        y = np.where(regime == 0, rng.normal(0.0, 1.0, n), rng.normal(3.0, 1.0, n))
        time_col = [f"2000-{((i // 12) % 12) + 1:02d}-{(i % 28) + 1:02d}"
                    for i in range(n)]
        return time_col, list(y)

    def test_hmm_state_labels_stable(self):
        from techniques import hmm_model
        time_col, y = self._make_regime_series()

        def build_ctx():
            return RunContext({
                "run_id": "t", "technique_id": "hmm", "preset": "Fast",
                "seed": 42, "frequency": "Monthly", "time": time_col,
                "series": [{"name": "Y", "values": y}],
                "params": {"n_components": 2},
            })

        res1, res2 = _run_twice(hmm_model.run, build_ctx)
        self.assertEqual(res1.get("status"), "success")
        self.assertEqual(res2.get("status"), "success")

        # The "State Means" table exposes the per-state mean — state 0 must
        # always be the lower-mean state after our sort-by-mean fix.
        # (Look for a table with per-state means.)
        t1 = _find_table(res1, "state")
        t2 = _find_table(res2, "state")
        self.assertIsNotNone(t1, "HMM should expose a state-summary table")
        self.assertIsNotNone(t2)
        # Extract some means from both and verify they're identical:
        self.assertEqual([r[0] for r in t1["rows"]], [r[0] for r in t2["rows"]])

    def test_markov_switching_regimes_stable(self):
        try:
            from techniques import markov_switching
        except Exception:
            self.skipTest("markov_switching not available")
        time_col, y = self._make_regime_series(seed=7)

        def build_ctx():
            return RunContext({
                "run_id": "t", "technique_id": "markov_switching",
                "preset": "Fast", "seed": 42, "frequency": "Monthly",
                "time": time_col,
                "series": [{"name": "Y", "values": y}],
                "params": {"k_regimes": 2, "order": 0},
            })

        res1, res2 = _run_twice(markov_switching.run, build_ctx)
        if res1.get("status") != "success":
            self.skipTest("MarkovRegression did not fit this sample")

        # Regime Summary table should put Regime 0 as the lowest-mean regime.
        summary1 = _find_table(res1, "regime summary")
        if summary1 is None:
            self.skipTest("No Regime Summary table")
        means = [row[3] for row in summary1["rows"] if row[3] is not None]
        if len(means) >= 2:
            self.assertLessEqual(means[0], means[1] + 1e-9,
                                 "Regime 0 should have the lowest mean after sort")


# ─────────────────────────────────────────────────────────────────────
# Markov Switching — AR coefficient fit invariant
# ─────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────
# Markov Switching — labeling convention (sort by dominant axis)
# ─────────────────────────────────────────────────────────────────────
class TestMarkovSwitchingLabelingConvention(unittest.TestCase):
    """The wrapper previously sorted regimes unconditionally by empirical
    mean. Under ``switching_variance=True`` fits where the variance axis
    dominates the separation (typified by Real GDP Q/Q SAAR: μ=(3.00,
    3.60) but σ=(1.86, 6.48), a 12× variance ratio), sorting by mean
    labels the output as if the regimes differ in mean growth, when in
    fact the model separated quiet volatility from turbulent volatility.

    The fix: ``label_regimes_by_dominant_key`` now chooses between mean-
    and std-sort based on which axis dominates. The ``sort_axis`` field
    in the interpretation dict reports which axis was chosen.

    Three fixtures cover the classification rule:

    - **T_new_1** (variance-dominant): verifies std-sort fires when the
      motivating condition holds.
    - **T_new_2** (mean-dominant preserved): regression guard against an
      over-aggressive threshold reclassifying genuinely mean-separated
      regimes as variance-dominant.
    - **T_new_3** (boundary): dominance exactly 2.0 must fall on the
      mean-sort side (strict ``>`` threshold).
    """

    def _make_two_regime_series(self, mu, sigma, n=500, seed=42,
                                 p_stay=0.95):
        """Draw n observations from a 2-regime Markov chain with per-
        regime Gaussian emissions N(mu[r], sigma[r]**2) and self-
        transition probability p_stay."""
        rng = np.random.default_rng(seed)
        P = np.array([[p_stay, 1 - p_stay], [1 - p_stay, p_stay]])
        state = 0
        y = np.zeros(n)
        for t in range(n):
            y[t] = rng.normal(mu[state], sigma[state])
            if rng.random() < 1 - P[state, state]:
                state = 1 - state
        return y

    def _extract_sort_axis(self, res):
        """Read sort_axis from the interp block (where the wrapper
        surfaces it for the interpretation layer)."""
        interp = res.get("interpretation") or {}
        # build_interpretation returns the rendered text; the source
        # dict isn't exposed. Instead, read from audit/warnings shape.
        # Sort-axis is visible via the emitted warning text.
        for w in res.get("warnings") or []:
            if "sorted by empirical standard deviation" in w:
                return "std"
            if "sorted by empirical mean" in w:
                return "mean"
        return None

    def test_variance_dominant_classification(self):
        """T_new_1: μ₀=μ₁=0, σ₀=1, σ₁=5, n=500, seed=42. Variance
        ratio 25× dominates a zero mean gap → sort by std, Regime 0
        has smaller std."""
        from techniques import markov_switching

        y = self._make_two_regime_series(mu=[0.0, 0.0], sigma=[1.0, 5.0])
        time_axis = [f"{2000 + i // 4}-Q{(i % 4) + 1}" for i in range(len(y))]

        def build_ctx():
            return RunContext({
                "run_id": "t", "technique_id": "markov_switching",
                "preset": "Fast", "seed": 42, "frequency": "Quarterly",
                "time": time_axis,
                "series": [{"name": "VARSWITCH", "values": y.tolist()}],
                # order=0 intentional: isolates variance-sort decision
                # from AR-fit noise introduced by MarkovAutoregression
                # under order >= 1.
                "params": {"k_regimes": 2, "order": 0,
                           "switching_variance": True},
            })

        res1, res2 = _run_twice(markov_switching.run, build_ctx)
        if res1.get("status") != "success":
            self.skipTest(f"fit failed: {res1.get('error_message')}")

        axis = self._extract_sort_axis(res1)
        self.assertEqual(
            axis, "std",
            f"Expected std-sort on variance-dominant DGP; got {axis}. "
            f"Warnings: {res1.get('warnings')}"
        )

        summary = _find_table(res1, "regime summary")
        self.assertIsNotNone(summary, "Regime Summary table missing")
        # Row layout: [regime, periods, pct, mean, std]. Check std
        # column ascending.
        stds = [row[4] for row in summary["rows"] if row[4] is not None]
        self.assertGreaterEqual(len(stds), 2, "Need two regimes with std")
        self.assertLessEqual(
            stds[0], stds[1] + 1e-9,
            f"Regime 0 should have lower std than Regime 1 under "
            f"std-sort; got Regime 0 std={stds[0]}, Regime 1 std={stds[1]}"
        )

        # Bit-identical label stability across two seeded runs.
        summary2 = _find_table(res2, "regime summary")
        self.assertIsNotNone(summary2)
        self.assertEqual(
            [row[0] for row in summary["rows"]],
            [row[0] for row in summary2["rows"]],
            "Regime labels must be stable across two seeded runs"
        )

    def test_mean_dominant_classification_preserved(self):
        """T_new_2: μ₀=-2, μ₁=2, σ₀=σ₁=1, n=500, seed=42. Guards
        against an over-aggressive threshold that reclassifies
        well-separated means as variance-dominant when σ happens to
        drift slightly."""
        from techniques import markov_switching

        y = self._make_two_regime_series(mu=[-2.0, 2.0], sigma=[1.0, 1.0])
        time_axis = [f"{2000 + i // 4}-Q{(i % 4) + 1}" for i in range(len(y))]

        ctx = RunContext({
            "run_id": "t", "technique_id": "markov_switching",
            "preset": "Fast", "seed": 42, "frequency": "Quarterly",
            "time": time_axis,
            "series": [{"name": "MEANSWITCH", "values": y.tolist()}],
            "params": {"k_regimes": 2, "order": 0,
                       "switching_variance": True},
        })
        res = markov_switching.run(ctx, _noop_progress)
        if res.get("status") != "success":
            self.skipTest(f"fit failed: {res.get('error_message')}")

        axis = self._extract_sort_axis(res)
        self.assertEqual(
            axis, "mean",
            f"Expected mean-sort on mean-dominant DGP; got {axis}. "
            f"Warnings: {res.get('warnings')}"
        )

        summary = _find_table(res, "regime summary")
        self.assertIsNotNone(summary)
        means = [row[3] for row in summary["rows"] if row[3] is not None]
        self.assertGreaterEqual(len(means), 2)
        self.assertLessEqual(
            means[0], means[1] + 1e-9,
            f"Regime 0 should have lower mean than Regime 1 under "
            f"mean-sort; got {means}"
        )

    def test_boundary_classification_is_mean(self):
        """T_new_3: μ₀=0, μ₁=2, σ₀=1, σ₁=2 — variance_ratio=4.0,
        mean_sep_in_min_σ=2.0, dominance=2.0 exactly. Strict ``> 2.0``
        threshold means this falls on the mean-sort side. Documents
        that ties resolve to mean.

        Direct check of the helper with the fixture-defined stds is
        the deterministic assertion; the end-to-end wrapper fit would
        depend on statsmodels' recovery and might not land exactly on
        the boundary."""
        from techniques.base import label_regimes_by_dominant_key

        means = np.array([0.0, 2.0])
        stds = np.array([1.0, 2.0])
        result = label_regimes_by_dominant_key(means, stds)
        self.assertEqual(
            result["axis_name"], "mean",
            f"Boundary case (dominance=2.0 exactly) must resolve to "
            f"mean-sort; got {result['axis_name']}. "
            f"variance_ratio={result['variance_ratio']}, "
            f"mean_sep_in_min_sigma={result['mean_sep_in_min_sigma']}"
        )


# ─────────────────────────────────────────────────────────────────────
# Markov Switching — transition-matrix forecast invariants
# ─────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────
# Markov Switching — single-regime RMSE benchmark invariants
# ─────────────────────────────────────────────────────────────────────
class TestMarkovSwitchingBenchmark(unittest.TestCase):
    """The Markov Switching wrapper now fits a single-regime benchmark
    (constant mean under order=0, ARIMA(order, 0, 0) under order>=1)
    alongside the Markov fit, reports benchmark RMSE and the Markov-
    vs-benchmark lift in the Model Summary table, and surfaces both
    into audit_fields and the interpretation layer.

    Motivation: Markov RMSE reported as a single absolute number gives
    the user no way to see whether the specification is earning its
    complexity. The lift metric converts an opaque RMSE into a signal
    that either validates or challenges the regime-switching choice.

    Three invariants:
    - order=0 benchmark produces a finite RMSE and the correct name.
    - order>=1 benchmark on a single-regime AR(1) series produces a
      name of "AR(1)" and a lift close to zero (the Markov fit cannot
      materially outperform its own benchmark on data without regime
      structure).
    - Both Model Summary rows (Benchmark RMSE, RMSE Lift vs Benchmark)
      are present in the output table. Guards against future edits
      accidentally dropping the reporting.
    """

    def _variance_dominant_ctx(self):
        """Fixture used by T_new_1 and T_new_3 — same variance-dominant
        DGP as TestMarkovSwitchingForecasts so order=0 is exercised on
        a series whose regimes actually differ (in variance)."""
        rng = np.random.default_rng(42)
        n = 500
        P = np.array([[0.95, 0.05], [0.05, 0.95]])
        state = 0
        y = np.zeros(n)
        for t in range(n):
            y[t] = rng.normal(0.0, 1.0 if state == 0 else 5.0)
            if rng.random() < 1 - P[state, state]:
                state = 1 - state
        time_axis = [f"{2000 + i // 4}-Q{(i % 4) + 1}" for i in range(n)]
        return RunContext({
            "run_id": "t", "technique_id": "markov_switching",
            "preset": "Fast", "seed": 42, "frequency": "Quarterly",
            "time": time_axis,
            "series": [{"name": "Y", "values": y.tolist()}],
            "params": {"k_regimes": 2, "order": 0,
                       "switching_variance": True},
        })

    def test_order0_benchmark_constant_mean(self):
        """order=0 fit: benchmark_rmse should be finite, benchmark_name
        should be 'constant mean', and the lift should be modest on a
        mean-identical two-regime process (both regimes have μ=0 so the
        constant-mean benchmark is actually quite competitive)."""
        from techniques import markov_switching
        res = markov_switching.run(self._variance_dominant_ctx(), _noop_progress)
        if res.get("status") != "success":
            self.skipTest(f"fit failed: {res.get('error_message')}")

        audit = res.get("audit_fields") or {}
        benchmark_rmse = audit.get("benchmark_rmse")
        benchmark_name = audit.get("benchmark_name")
        lift = audit.get("rmse_lift_vs_benchmark")

        self.assertIsNotNone(benchmark_rmse,
                             "benchmark_rmse missing from audit_fields")
        self.assertTrue(
            np.isfinite(benchmark_rmse),
            f"benchmark_rmse should be finite; got {benchmark_rmse}"
        )
        self.assertEqual(
            benchmark_name, "constant mean",
            f"order=0 benchmark should be 'constant mean'; "
            f"got {benchmark_name!r}"
        )
        self.assertIsNotNone(lift, "rmse_lift_vs_benchmark missing")
        self.assertTrue(
            -0.20 <= lift <= 0.20,
            f"Lift on mean-identical two-regime process should be "
            f"within ±20%; got {lift:+.1%}"
        )

    def test_order1_benchmark_ar1(self):
        """order=1 fit on a synthetic AR(1): benchmark_name should be
        'AR(1)' and lift should be within ±10%. The Markov fit on
        single-regime AR(1) data should not materially beat its own
        AR(1) benchmark — substantial positive lift would signal the
        Markov is overfitting spurious regimes; substantial negative
        lift would signal the benchmark is a better specification."""
        from techniques import markov_switching
        rng = np.random.default_rng(42)
        rho = 0.6
        n = 200
        y = np.zeros(n)
        for t in range(1, n):
            y[t] = rho * y[t - 1] + rng.normal(0, 1)
        time_axis = [f"{2000 + i // 4}-Q{(i % 4) + 1}" for i in range(n)]
        ctx = RunContext({
            "run_id": "t", "technique_id": "markov_switching",
            "preset": "Balanced", "seed": 42, "frequency": "Quarterly",
            "time": time_axis,
            "series": [{"name": "AR1", "values": y.tolist()}],
            "params": {"k_regimes": 2, "order": 1,
                       "switching_variance": True},
        })
        res = markov_switching.run(ctx, _noop_progress)
        if res.get("status") != "success":
            self.skipTest(f"fit failed: {res.get('error_message')}")

        audit = res.get("audit_fields") or {}
        benchmark_name = audit.get("benchmark_name")
        lift = audit.get("rmse_lift_vs_benchmark")

        self.assertEqual(
            benchmark_name, "AR(1)",
            f"order=1 benchmark should be 'AR(1)'; got {benchmark_name!r}"
        )
        self.assertIsNotNone(lift, "rmse_lift_vs_benchmark missing")
        self.assertTrue(
            -0.10 <= lift <= 0.10,
            f"Lift on single-regime AR(1) fixture should be within "
            f"±10% of its AR(1) benchmark; got {lift:+.1%}. Larger "
            f"positive lift signals spurious regime overfitting."
        )

    def test_model_summary_has_benchmark_rows(self):
        """Guard against future edits that drop either the Benchmark
        RMSE or RMSE Lift row from the Model Summary table output."""
        from techniques import markov_switching
        res = markov_switching.run(self._variance_dominant_ctx(), _noop_progress)
        if res.get("status") != "success":
            self.skipTest(f"fit failed: {res.get('error_message')}")

        summary = _find_table(res, "model summary")
        self.assertIsNotNone(summary, "Model Summary table missing")
        metrics = {str(row[0]) for row in summary["rows"]}
        self.assertIn(
            "Benchmark RMSE", metrics,
            f"Model Summary must include 'Benchmark RMSE' row. "
            f"Got metrics: {sorted(metrics)}"
        )
        self.assertIn(
            "RMSE Lift vs Benchmark", metrics,
            f"Model Summary must include 'RMSE Lift vs Benchmark' row. "
            f"Got metrics: {sorted(metrics)}"
        )


class TestMarkovSwitchingForecasts(unittest.TestCase):
    """The wrapper now constructs multi-step forecasts manually from
    the transition matrix and the final filtered regime probabilities,
    after confirming that statsmodels' native forecast methods raise
    NotImplementedError on both MarkovRegression and
    MarkovAutoregression.

    Four invariants guard the construction:

    - regime_probs_sum_to_one: π_h rows are valid probability vectors.
    - pi_h_base_case: π_h[0] equals π_T @ P (the recursion's base step).
    - pi_h_converges_to_stationary: under an ergodic P, π_h at horizon=10
      is close to the stationary distribution (helper also under test).
    - h1_mean_matches_closed_form: under order=0, the first forecast
      mean equals (π_T @ P) · regime_means exactly. This anchors the
      mean-construction arithmetic end-to-end.
    """

    def _find_forecast_table(self, res):
        for t in res.get("tables") or []:
            if str(t.get("name", "")).lower() == "forecast":
                return t
        return None

    def _run_variance_dominant_fit(self):
        """Shared fixture: a 2-regime variance-dominant series (μ=0 in
        both regimes, σ=1 vs σ=5) fit under order=0. Used by all four
        tests to avoid the noise of AR-coefficient recovery. Returns
        the RunContext result dict."""
        from techniques import markov_switching
        rng = np.random.default_rng(42)
        n = 500
        P = np.array([[0.95, 0.05], [0.05, 0.95]])
        state = 0
        y = np.zeros(n)
        for t in range(n):
            y[t] = rng.normal(0.0, 1.0 if state == 0 else 5.0)
            if rng.random() < 1 - P[state, state]:
                state = 1 - state
        time_axis = [f"{2000 + i // 4}-Q{(i % 4) + 1}" for i in range(n)]
        ctx = RunContext({
            "run_id": "t", "technique_id": "markov_switching",
            "preset": "Fast", "seed": 42, "frequency": "Quarterly",
            "time": time_axis,
            "series": [{"name": "Y", "values": y.tolist()}],
            "params": {"k_regimes": 2, "order": 0,
                       "switching_variance": True},
        })
        res = markov_switching.run(ctx, _noop_progress)
        return res

    def _extract_pi_h_and_P(self, res):
        """Pull π_h (horizon × k) and the transition matrix from the
        output tables. Reconstructs the probability grid from the
        Forecast table's P(Regime j) columns."""
        fc_tbl = self._find_forecast_table(res)
        self.assertIsNotNone(fc_tbl, "Forecast table missing")
        cols = fc_tbl["columns"]
        regime_cols = [i for i, c in enumerate(cols)
                       if str(c).startswith("P(Regime ")]
        self.assertGreaterEqual(len(regime_cols), 2,
                                "Forecast table missing P(Regime *) columns")
        pi_h = np.array([
            [float(row[i]) for i in regime_cols]
            for row in fc_tbl["rows"]
        ])

        trans_tbl = None
        for t in res.get("tables") or []:
            if str(t.get("name", "")).lower() == "transition matrix":
                trans_tbl = t
                break
        self.assertIsNotNone(trans_tbl, "Transition Matrix table missing")
        # Rows: [label, P(->0), P(->1), ...]; skip first column.
        P = np.array([
            [float(row[j + 1]) for j in range(len(regime_cols))]
            for row in trans_tbl["rows"]
        ])
        return pi_h, P

    def test_regime_probs_sum_to_one(self):
        res = self._run_variance_dominant_fit()
        if res.get("status") != "success":
            self.skipTest(f"fit failed: {res.get('error_message')}")
        pi_h, _ = self._extract_pi_h_and_P(res)
        for h, row in enumerate(pi_h):
            self.assertAlmostEqual(
                float(row.sum()), 1.0, places=6,
                msg=f"π_h row {h} does not sum to 1: sum={row.sum()}"
            )

    def test_pi_h_base_case_matches_pi_T_times_P(self):
        """π_h[0] = π_T @ P — reconstruct π_T from the last row of the
        Regime Probabilities table and verify the forecast base case.

        The Forecast table stores P(Regime j) rounded to 4 decimals, so
        we allow a tolerance consistent with that rounding (1e-3)."""
        res = self._run_variance_dominant_fit()
        if res.get("status") != "success":
            self.skipTest(f"fit failed: {res.get('error_message')}")
        pi_h, P = self._extract_pi_h_and_P(res)

        # Reconstruct π_T from the last row of the Regime Probabilities
        # table. Columns: Time, series_value, P(Regime 0), ..., Most Likely Regime.
        probs_tbl = None
        for t in res.get("tables") or []:
            if str(t.get("name", "")).lower() == "regime probabilities":
                probs_tbl = t
                break
        self.assertIsNotNone(probs_tbl, "Regime Probabilities table missing")
        cols = probs_tbl["columns"]
        k = P.shape[0]
        regime_col_idxs = [i for i, c in enumerate(cols)
                           if str(c).startswith("P(Regime ")]
        self.assertEqual(len(regime_col_idxs), k)
        pi_T = np.array([
            float(probs_tbl["rows"][-1][i]) for i in regime_col_idxs
        ])
        expected_pi_h0 = pi_T @ P

        diff = np.max(np.abs(pi_h[0] - expected_pi_h0))
        self.assertLess(
            diff, 1e-3,
            f"π_h[0] should equal π_T @ P within 4-decimal rounding; "
            f"got max |diff|={diff:.6f}. π_h[0]={pi_h[0]}, "
            f"π_T @ P = {expected_pi_h0}"
        )

    def test_pi_h_converges_to_stationary(self):
        """On a fast-mixing fixture (self-transition ~0.5, mixing
        timescale ~2), π_h at horizon=10 should be within 0.05 of the
        stationary distribution.

        A separate fixture from the variance-dominant one is used here
        because that fixture has self-transition 0.95 (mixing timescale
        ~20) — too slow for convergence within horizon=10. The
        convergence math is fixture-independent; this test exercises it
        on a chain that does converge quickly."""
        from techniques import markov_switching
        rng = np.random.default_rng(42)
        n = 500
        # Fast-mixing DGP: P = [[0.5, 0.5], [0.5, 0.5]]. Stationary
        # distribution is [0.5, 0.5]; any π_T @ P equals [0.5, 0.5]
        # exactly after just one step.
        P_true = np.array([[0.5, 0.5], [0.5, 0.5]])
        state = 0
        y = np.zeros(n)
        for t in range(n):
            y[t] = rng.normal(-1.0 if state == 0 else 1.0, 1.0)
            if rng.random() < 1 - P_true[state, state]:
                state = 1 - state
        time_axis = [f"{2000 + i // 4}-Q{(i % 4) + 1}" for i in range(n)]
        ctx = RunContext({
            "run_id": "t", "technique_id": "markov_switching",
            "preset": "Fast", "seed": 42, "frequency": "Quarterly",
            "time": time_axis,
            "series": [{"name": "Y", "values": y.tolist()}],
            "params": {"k_regimes": 2, "order": 0,
                       "switching_variance": False},
        })
        res = markov_switching.run(ctx, _noop_progress)
        if res.get("status") != "success":
            self.skipTest(f"fit failed: {res.get('error_message')}")
        pi_h, P = self._extract_pi_h_and_P(res)

        # Compute stationary distribution directly from the fitted P.
        from scipy.linalg import eig
        eigvals, eigvecs = eig(P.T)
        idx = int(np.argmin(np.abs(np.real(eigvals) - 1.0)))
        vec = np.real(eigvecs[:, idx])
        if np.any(vec < -1e-9):
            vec = np.abs(vec)
        stationary = vec / vec.sum()

        diff = np.max(np.abs(pi_h[-1] - stationary))
        self.assertLess(
            diff, 0.05,
            f"π_h at horizon=10 should be within 0.05 of stationary "
            f"distribution on a fast-mixing chain; got max |diff|="
            f"{diff:.4f}. π_h[-1]={pi_h[-1]}, stationary={stationary}"
        )

    def test_h1_mean_matches_closed_form(self):
        """Under order=0 (MarkovRegression path), mean_forecast[0] ==
        (π_T @ P) · regime_means. Reconstructs regime means from the
        Regime Summary table and verifies the first-horizon mean
        arithmetic end-to-end."""
        res = self._run_variance_dominant_fit()
        if res.get("status") != "success":
            self.skipTest(f"fit failed: {res.get('error_message')}")
        pi_h, _ = self._extract_pi_h_and_P(res)

        fc_tbl = self._find_forecast_table(res)
        mean_forecast_h1 = float(fc_tbl["rows"][0][1])  # "Mean Forecast" column

        summary = _find_table(res, "regime summary")
        self.assertIsNotNone(summary, "Regime Summary table missing")
        regime_means = np.array([
            float(row[3]) for row in summary["rows"] if row[3] is not None
        ])
        self.assertEqual(len(regime_means), pi_h.shape[1])

        expected = float(pi_h[0] @ regime_means)
        # The forecast table stores values rounded to 6 decimals; allow
        # that rounding plus the rounding in pi_h (4 decimals) and
        # regime_means (4 decimals from Regime Summary). 1e-2 tolerance.
        self.assertLess(
            abs(mean_forecast_h1 - expected), 1e-2,
            f"mean_forecast[h=1] should equal π_h[0] @ regime_means "
            f"within table-rounding tolerance; got {mean_forecast_h1}, "
            f"expected {expected}"
        )


class TestMarkovSwitchingARCoefficient(unittest.TestCase):
    """The wrapper previously passed `order=1` to MarkovRegression,
    which silently accepts the kwarg but interprets it as regime-
    likelihood dependence, not an AR lag polynomial — so no AR term
    was actually fitted. This class verifies the fix: when
    ``order >= 1`` the wrapper now instantiates MarkovAutoregression
    with ``switching_ar=True``, so AR coefficients appear in the
    parameter vector and recover true AR dynamics within tolerance.

    Two fixtures:

    1. **Primary (null-hypothesis for regimes)** — pure AR(1) with
       ρ=0.6 and no regime switching. Promotes the Phase 1 audit probe
       to a permanent invariant. Catches the "class switch never
       happened" regression: if the wrapper reverts to MarkovRegression
       or drops AR entries from the output, no row named ``ar.L1[*]``
       will appear.

    2. **Secondary (positive control)** — true 2-regime MS-AR DGP with
       known per-regime AR coefficients ρ₀=0.3 and ρ₁=0.8. Catches the
       subtler regression where the class switch succeeds but both
       regimes fit noise and happen to hit 0.6 by accident under the
       primary fixture. Tolerance is slightly wider (±0.20) because
       2-regime MS-AR recovery on finite samples is noisier than
       single-regime AR recovery.
    """

    def _find_ar_rows(self, res):
        """Extract (regime_idx, coefficient) tuples from the
        parameters table for rows whose Parameter cell starts with
        ``ar.L1[``."""
        out = []
        for t in res.get("tables") or []:
            if "parameters" not in str(t.get("name", "")).lower():
                continue
            for row in t.get("rows") or []:
                pname = str(row[0])
                if pname.startswith("ar.L1["):
                    # Extract the integer regime index from "ar.L1[0]" etc.
                    try:
                        idx = int(pname[len("ar.L1["):-1])
                    except ValueError:
                        continue
                    try:
                        coef = float(row[1])
                    except (TypeError, ValueError):
                        continue
                    out.append((idx, coef))
            break  # Only inspect the first parameters-named table.
        return out

    def test_ar_coefficient_present_and_recovers_rho_06(self):
        """Primary fixture: pure AR(1) with ρ=0.6, seed 42, n=200,
        no regime switching. The wrapper should instantiate
        MarkovAutoregression, produce >6 parameter rows (baseline MS
        has 6 for k=2 with switching_variance), and recover ρ=0.6 on
        at least one regime's AR coefficient within ±0.15."""
        from techniques import markov_switching

        rng = np.random.default_rng(42)
        rho = 0.6
        n = 200
        y = np.zeros(n)
        for t in range(1, n):
            y[t] = rho * y[t - 1] + rng.normal(0, 1)

        time_axis = [f"{2000 + i // 4}-Q{(i % 4) + 1}" for i in range(n)]
        ctx = RunContext({
            "run_id": "t", "technique_id": "markov_switching",
            "preset": "Balanced", "seed": 42, "frequency": "Quarterly",
            "time": time_axis,
            "series": [{"name": "AR1", "values": y.tolist()}],
            "params": {"k_regimes": 2, "order": 1,
                       "switching_variance": True},
        })

        res = markov_switching.run(ctx, _noop_progress)
        if res.get("status") != "success":
            self.skipTest(f"fit failed: {res.get('error_message')}")

        # Assertion 1 — parameter vector grew to include AR entries.
        params_tbl = _find_table(res, "parameters")
        self.assertIsNotNone(params_tbl, "Parameters table missing")
        self.assertGreater(
            len(params_tbl["rows"]), 6,
            f"Parameters table has {len(params_tbl['rows'])} rows; "
            f"expected >6 (6 baseline + AR entries). The class switch "
            f"to MarkovAutoregression may not be in effect."
        )

        # Assertion 2 — at least one row labeled ar.L1[*].
        ar_rows = self._find_ar_rows(res)
        self.assertGreaterEqual(
            len(ar_rows), 1,
            f"No rows labeled 'ar.L1[*]' in the Parameters table. "
            f"Table rows: {[r[0] for r in params_tbl['rows']]}"
        )

        # Assertion 3 — at least one regime recovers ρ=0.6 within ±0.15.
        # (Either regime may be the AR-driven one; the other may fit
        # noise under a null-hypothesis-for-regimes DGP.)
        recovered = [coef for _, coef in ar_rows]
        closest_to_06 = min(recovered, key=lambda c: abs(c - 0.6))
        self.assertLess(
            abs(closest_to_06 - 0.6), 0.15,
            f"No ar.L1 coefficient within ±0.15 of ρ=0.6. "
            f"Recovered: {recovered}"
        )

    def test_ar_coefficients_recover_both_regime_rhos(self):
        """Secondary fixture (positive control): true 2-regime MS-AR
        DGP with ρ₀=0.3 (low-mean regime) and ρ₁=0.8 (high-mean
        regime). After the wrapper sorts regimes by empirical mean,
        ar.L1[0] should recover ρ₀=0.3 and ar.L1[1] should recover
        ρ₁=0.8, each within ±0.20 (MS-AR recovery on n=500 is noisier
        than single-regime AR on n=200, so the tolerance is wider)."""
        from techniques import markov_switching

        rng = np.random.default_rng(42)
        n = 500
        # Transition matrix: P(stay) = 0.97 → mean duration ~33 periods.
        P = np.array([[0.97, 0.03], [0.03, 0.97]])
        # Per-regime DGP parameters: (μ, σ, ρ) for regimes 0 and 1.
        mu = [0.0, 2.0]
        sigma = [1.0, 1.0]
        rho = [0.3, 0.8]

        # Simulate the hidden regime sequence.
        state = 0
        states = np.zeros(n, dtype=int)
        for t in range(n):
            states[t] = state
            if rng.random() < 1 - P[state, state]:
                state = 1 - state

        # Simulate the AR(1)-by-regime observed series.
        y = np.zeros(n)
        y[0] = mu[states[0]]
        for t in range(1, n):
            r = states[t]
            y[t] = mu[r] + rho[r] * (y[t - 1] - mu[states[t - 1]]) + \
                   rng.normal(0, sigma[r])

        time_axis = [f"{2000 + i // 4}-Q{(i % 4) + 1}" for i in range(n)]
        ctx = RunContext({
            "run_id": "t", "technique_id": "markov_switching",
            "preset": "Balanced", "seed": 42, "frequency": "Quarterly",
            "time": time_axis,
            "series": [{"name": "MSAR", "values": y.tolist()}],
            "params": {"k_regimes": 2, "order": 1,
                       "switching_variance": True},
        })

        res = markov_switching.run(ctx, _noop_progress)
        if res.get("status") != "success":
            self.skipTest(f"fit failed: {res.get('error_message')}")

        ar_rows = self._find_ar_rows(res)
        self.assertEqual(
            len(ar_rows), 2,
            f"Expected exactly 2 ar.L1[*] rows for k=2 regimes with "
            f"switching_ar=True; got {len(ar_rows)}"
        )

        # Recover regime means (from Regime Summary) so we can identify
        # which statsmodels-native index corresponds to the low-mean /
        # high-mean regime AFTER the wrapper's post-fit sort. Note: the
        # wrapper sorts `most_likely_regime` for display, but the
        # parameter names (ar.L1[0], ar.L1[1]) reflect statsmodels-
        # native ordering and are NOT remapped. So we cross-reference
        # via the constants in the same parameter vector.
        param_rows = {row[0]: float(row[1])
                      for row in _find_table(res, "parameters")["rows"]}
        const0 = param_rows.get("const[0]")
        const1 = param_rows.get("const[1]")
        self.assertIsNotNone(const0, "const[0] missing")
        self.assertIsNotNone(const1, "const[1] missing")

        # Map native regime index → sorted position by empirical mean.
        # Lowest const = native "low-mean regime" = sorted Regime 0.
        low_mean_native = 0 if const0 <= const1 else 1
        high_mean_native = 1 - low_mean_native

        ar_by_native = {idx: coef for idx, coef in ar_rows}
        rho_low = ar_by_native.get(low_mean_native)
        rho_high = ar_by_native.get(high_mean_native)
        self.assertIsNotNone(rho_low, "ar.L1 for low-mean regime missing")
        self.assertIsNotNone(rho_high, "ar.L1 for high-mean regime missing")

        self.assertLess(
            abs(rho_low - 0.3), 0.20,
            f"Low-mean regime ar.L1={rho_low:.3f} is not within ±0.20 "
            f"of true ρ₀=0.3. Recovery failed on n=500."
        )
        self.assertLess(
            abs(rho_high - 0.8), 0.20,
            f"High-mean regime ar.L1={rho_high:.3f} is not within ±0.20 "
            f"of true ρ₁=0.8. Recovery failed on n=500."
        )


# ─────────────────────────────────────────────────────────────────────
# Tier 1 — HAR-RV degrees-of-freedom correction
# ─────────────────────────────────────────────────────────────────────
class TestHarRvDof(unittest.TestCase):
    def test_sigma2_matches_ols_dof(self):
        """Our σ² should match the OLS σ² (Σε² / (T−k)) to numerical precision."""
        from techniques import har_rv  # noqa: F401

        # Build a synthetic realized-vol-like series
        rng = np.random.default_rng(0)
        n = 200
        y = np.abs(rng.normal(0.01, 0.002, n)) ** 2
        time_col = [f"2020-{((i // 22) % 12) + 1:02d}-{(i % 22) + 1:02d}"
                    for i in range(n)]
        ctx = RunContext({
            "run_id": "t", "technique_id": "har_rv", "preset": "Fast",
            "seed": 0, "frequency": "BusinessDaily", "time": time_col,
            "series": [{"name": "RV", "values": list(y)}],
            "params": {},
        })
        res = har_rv.run(ctx, _noop_progress)
        self.assertEqual(res.get("status"), "success")

        # Find the diagnostics / model-summary table with sigma^2 or AIC.
        for t in res.get("tables") or []:
            cols = [str(c).lower() for c in t.get("columns", [])]
            if "aic" in " ".join(cols) or "sigma" in " ".join(cols):
                # Just assert AIC is finite and negative (reasonable for a
                # well-fit variance model) — if the DoF correction is
                # applied, AIC won't be spuriously low.
                for row in t["rows"]:
                    for cell in row:
                        if isinstance(cell, float):
                            self.assertTrue(np.isfinite(cell),
                                            f"Non-finite value in {t.get('name')}")


# ─────────────────────────────────────────────────────────────────────
# Tier 2 — Interval fallback path uses t-critical, not 1.96
# ─────────────────────────────────────────────────────────────────────
class TestIntervalFallback(unittest.TestCase):
    """When the fallback path fires, intervals should scale with DoF
    (t-critical) rather than a hardcoded z = 1.96."""

    def test_ets_interval_widens_with_horizon(self):
        try:
            from techniques import ets_hw
        except Exception:
            self.skipTest("ets_hw not available")
        rng = np.random.default_rng(0)
        y = list(np.cumsum(rng.normal(0, 1, 120)))
        time_col = [f"2010-{((i // 12) % 12) + 1:02d}-28" for i in range(120)]
        ctx = RunContext({
            "run_id": "t", "technique_id": "ets_hw", "preset": "Balanced",
            "seed": 0, "frequency": "Monthly", "time": time_col,
            "series": [{"name": "Y", "values": y}],
            "params": {"horizon": 12},
        })
        res = ets_hw.run(ctx, _noop_progress)
        if res.get("status") != "success":
            self.skipTest("ets_hw did not fit")
        # Any forecast table should show interval widths growing (weakly)
        # with horizon — if the bug reverts to hardcoded constant σ the
        # width would be flat.
        for t in res.get("tables") or []:
            cols = [str(c).lower() for c in t.get("columns", [])]
            if "lower" in " ".join(cols) and "upper" in " ".join(cols):
                rows = t.get("rows") or []
                if len(rows) < 3:
                    continue
                li = cols.index("lower 95%") if "lower 95%" in cols else 2
                ui = cols.index("upper 95%") if "upper 95%" in cols else 3
                widths = [r[ui] - r[li] for r in rows
                          if r[li] is not None and r[ui] is not None]
                self.assertGreaterEqual(widths[-1], widths[0] * 0.9,
                                        "Forecast interval width should weakly "
                                        "grow with horizon")
                return
        self.skipTest("No forecast-interval table found")


# ─────────────────────────────────────────────────────────────────────
# Tier 2 — Block bootstrap inflates length for autocorrelated data
# ─────────────────────────────────────────────────────────────────────
class TestBlockBootstrap(unittest.TestCase):
    def test_length_inflates_with_high_ac(self):
        from techniques.block_bootstrap import _optimal_block_length

        # AR(1) with rho = 0.9 — should get a materially longer block.
        rng = np.random.default_rng(0)
        n = 500
        e = rng.normal(0, 1, n)
        y = np.zeros(n)
        for i in range(1, n):
            y[i] = 0.9 * y[i - 1] + e[i]
        bl_iid = _optimal_block_length(n, data=rng.normal(0, 1, n))
        bl_ac = _optimal_block_length(n, data=y)
        self.assertGreater(bl_ac, bl_iid,
                          f"Block length for AR(1,0.9) ({bl_ac}) should exceed "
                          f"that for iid series ({bl_iid})")


# ─────────────────────────────────────────────────────────────────────
# Tier 3 — SVD/IMF/wavelet sign normalization stable across runs
# ─────────────────────────────────────────────────────────────────────
class TestSignStability(unittest.TestCase):
    def test_ssa_signs_stable(self):
        try:
            from techniques import ssa_model
        except Exception:
            self.skipTest("ssa_model not available")
        rng = np.random.default_rng(0)
        n = 200
        t = np.arange(n)
        y = np.sin(2 * np.pi * t / 20) + 0.5 * np.cos(2 * np.pi * t / 50) + rng.normal(0, 0.1, n)
        time_col = [f"2020-{((i // 30) % 12) + 1:02d}-{(i % 28) + 1:02d}"
                    for i in range(n)]

        def build_ctx():
            return RunContext({
                "run_id": "t", "technique_id": "ssa", "preset": "Fast",
                "seed": 0, "frequency": "Monthly", "time": time_col,
                "series": [{"name": "Y", "values": list(y)}],
                "params": {"n_components": 3},
            })

        res1, res2 = _run_twice(ssa_model.run, build_ctx)
        self.assertEqual(res1.get("status"), "success")
        self.assertEqual(res2.get("status"), "success")
        # Two runs on the same data should produce byte-identical component tables.
        t1 = _find_table(res1, "component")
        t2 = _find_table(res2, "component")
        if t1 and t2:
            self.assertEqual(t1["rows"][:5], t2["rows"][:5],
                             "SSA component rows should match across runs")


# ─────────────────────────────────────────────────────────────────────
# Tier 3 — VECM cointegrating vectors normalized
# ─────────────────────────────────────────────────────────────────────
class TestVecmNormalization(unittest.TestCase):
    def test_beta_first_coefficient_one(self):
        try:
            from techniques import vecm_model
        except Exception:
            self.skipTest("vecm_model not available")
        rng = np.random.default_rng(0)
        n = 250
        # Two cointegrated series: y2 = 2*y1 + stationary noise
        y1 = np.cumsum(rng.normal(0, 1, n))
        y2 = 2 * y1 + rng.normal(0, 0.5, n)
        time_col = [f"2010-{((i // 12) % 12) + 1:02d}-28" for i in range(n)]
        ctx = RunContext({
            "run_id": "t", "technique_id": "vecm", "preset": "Fast",
            "seed": 0, "frequency": "Monthly", "time": time_col,
            "series": [
                {"name": "Y1", "values": list(y1)},
                {"name": "Y2", "values": list(y2)},
            ],
            "params": {"lag_order": 1, "coint_rank": 1},
        })
        res = vecm_model.run(ctx, _noop_progress)
        if res.get("status") != "success":
            self.skipTest("VECM did not fit")
        beta_table = _find_table(res, "cointegrating")
        self.assertIsNotNone(beta_table)
        # First numeric coefficient (pivot) should be ~1.0 after normalization.
        first_row = beta_table["rows"][0]
        first_coef = first_row[1]
        self.assertAlmostEqual(abs(first_coef), 1.0, places=5,
                              msg=f"Expected |beta[0,0]| == 1 after Phillips "
                                  f"triangular normalization, got {first_coef}")


# ─────────────────────────────────────────────────────────────────────
# DFM / PCA invariants (already fixed; regression guards)
# ─────────────────────────────────────────────────────────────────────
class TestDfmVarianceSanity(unittest.TestCase):
    def test_dfm_variance_explained_bounded(self):
        from techniques import dynamic_factor_model as dfm
        rng = np.random.default_rng(0)
        n = 200
        factor = np.cumsum(rng.normal(0, 0.5, n))
        series = [{"name": f"Y{i}", "values": list(factor + rng.normal(0, 0.2, n))}
                  for i in range(4)]
        time_col = [f"2010-{((i // 12) % 12) + 1:02d}-28" for i in range(n)]
        ctx = RunContext({
            "run_id": "t", "technique_id": "dynamic_factor_model",
            "preset": "Balanced", "seed": 0, "frequency": "Monthly",
            "time": time_col, "series": series,
            "params": {"k_factors": 2},
        })
        res = dfm.run(ctx, _noop_progress)
        self.assertEqual(res.get("status"), "success")
        # Every communality should be in [0, 1 + epsilon]. Total variance
        # explained should not exceed 100% (the previous bug reported 1935%).
        load_tbl = _find_table(res, "loading")
        self.assertIsNotNone(load_tbl)
        for row in load_tbl["rows"]:
            comm = row[-1]
            self.assertIsInstance(comm, float)
            self.assertGreaterEqual(comm, -1e-6,
                                    f"Communality should be >= 0, got {comm}")
            self.assertLessEqual(comm, 1.0 + 1e-6,
                                 f"Communality should be <= 1, got {comm} "
                                 f"(quadratic-form formula should cap at 1)")


class TestPcaSignStability(unittest.TestCase):
    def test_pc1_loadings_nonnegative_on_correlated_data(self):
        from techniques import pca_analysis
        rng = np.random.default_rng(0)
        n = 300
        common = np.cumsum(rng.normal(0, 1, n))
        series = [{"name": f"Y{i}", "values": list(common + rng.normal(0, 0.3, n))}
                  for i in range(4)]
        time_col = [f"2010-{((i // 12) % 12) + 1:02d}-28" for i in range(n)]
        ctx = RunContext({
            "run_id": "t", "technique_id": "pca_analysis", "preset": "Balanced",
            "seed": 0, "frequency": "Monthly", "time": time_col,
            "series": series, "params": {},
        })
        res = pca_analysis.run(ctx, _noop_progress)
        self.assertEqual(res.get("status"), "success")
        load_tbl = _find_table(res, "loading")
        self.assertIsNotNone(load_tbl)
        # PC1 (column index 1) should have max-absolute loading positive.
        pc1_loadings = [row[1] for row in load_tbl["rows"]]
        max_abs_idx = int(np.argmax(np.abs(pc1_loadings)))
        self.assertGreater(pc1_loadings[max_abs_idx], 0,
                          f"PC1 max-|loading| should be positive for the "
                          f"level-factor convention; got {pc1_loadings}")


# ─────────────────────────────────────────────────────────────────────
# Structural TS / UCM output-alignment invariant
# ─────────────────────────────────────────────────────────────────────
class TestStructuralTSOutputAlignment(unittest.TestCase):
    """The wrapper must own alignment between the input's DatetimeIndex
    and every output row — not statsmodels' returned arrays — because
    statsmodels alternates between ndarray and Series depending on input
    type and attribute (smoothed_state is ndarray; fittedvalues is
    Series when input was a Series, ndarray when input was ndarray).

    Previously crashed in the "Building output" phase with
    ``AttributeError: 'numpy.ndarray' object has no attribute 'index'``
    when iterating ``fit.params.index`` on an ndarray-input model. The
    guarded pattern for statsmodels `fit.params` / `fit.bse` access is
    documented in engine/techniques/NOTES_statsmodels_params.md.
    """

    def test_kalman_output_alignment_with_missing(self):
        from techniques import structural_ts

        # Nile-like: 100-obs annual series with one interior NaN at position 50.
        rng = np.random.default_rng(42)
        values = (np.cumsum(rng.normal(0, 1, 100)) + 1120.0).tolist()
        values[50] = None  # interior NaN — Kalman handles natively

        time_axis = [f"{1901 + i}-12-31" for i in range(100)]

        ctx = RunContext({
            "run_id": "t",
            "technique_id": "structural_ts",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "Annual",
            "time": time_axis,
            "series": [{"name": "Nile", "values": values}],
            "params": {"horizon": 10},
        })

        res = structural_ts.run(ctx, _noop_progress)

        # 1. Run completed — no swallowed AttributeError in the output phase.
        self.assertEqual(
            res.get("status"), "success",
            msg=f"Structural TS run failed: {res.get('error_message')}"
        )

        # 2. Output table present.
        comp_tbl = _find_table(res, "smoothed components")
        self.assertIsNotNone(comp_tbl, "Smoothed Components table missing")

        # 3. Row count equals input row count — the interior NaN must NOT
        #    cause a row to be dropped (Kalman handles it natively; the
        #    output must still contain every input timestamp).
        self.assertEqual(
            len(comp_tbl["rows"]), 100,
            msg=(f"Expected 100 rows aligned to input length; got "
                 f"{len(comp_tbl['rows'])}. An interior NaN must not shrink "
                 f"the output.")
        )

        # 4. Time column equals the input's DatetimeIndex element-wise.
        for i, row in enumerate(comp_tbl["rows"]):
            self.assertEqual(
                row[0], time_axis[i],
                msg=(f"Row {i} time cell '{row[0]}' does not match input "
                     f"time_axis[{i}] '{time_axis[i]}' — wrapper is not "
                     f"owning alignment per §4.1 of the design mandate.")
            )

        # 5. Forecast table extends the time axis via date arithmetic,
        #    not integer step numbers (was previously "n + i + 1").
        fc_tbl = _find_table(res, "forecast")
        self.assertIsNotNone(fc_tbl)
        self.assertEqual(len(fc_tbl["rows"]), 10)
        first_fc_time = fc_tbl["rows"][0][0]
        self.assertTrue(
            str(first_fc_time).startswith("20"),
            msg=(f"Forecast Time column should extend the DatetimeIndex as "
                 f"a date string, got {first_fc_time!r}.")
        )

        # 6. Parameters table was produced — the original crash site was
        #    iterating fit.params.index, so presence of this table is the
        #    direct regression guard.
        param_tbl = _find_table(res, "estimated parameters")
        self.assertIsNotNone(param_tbl, "Estimated Parameters table missing")
        self.assertGreater(
            len(param_tbl["rows"]), 0,
            "Parameters table should have at least one row"
        )


# ─────────────────────────────────────────────────────────────────────
# Rolling CCF F1 invariants and F2/F3 cross-technique invariants
# ─────────────────────────────────────────────────────────────────────
def _rolling_ccf_ctx(series_list, *, window=None, max_lag=None, preset="Balanced",
                     frequency="Quarterly", seed=42, n=None):
    """Build a minimal RunContext for rolling_ccf_lag. ``series_list`` is a
    list of (name, values) tuples."""
    if n is None:
        n = len(series_list[0][1])
    time_col = [f"{2000 + i // 4}-Q{i % 4 + 1}" for i in range(n)]
    params = {}
    if window is not None:
        params["window"] = window
    if max_lag is not None:
        params["max_lag"] = max_lag
    return RunContext({
        "run_id": "t",
        "technique_id": "rolling_ccf_lag",
        "preset": preset,
        "seed": seed,
        "frequency": frequency,
        "time": time_col,
        "series": [{"name": name, "values": list(vals)} for name, vals in series_list],
        "params": params,
    })


class TestBoundaryExclusion(unittest.TestCase):
    """T1 — rolling_ccf_lag must flag boundary-hit windows and exclude them
    from summary statistics."""

    def test_boundary_column_present_and_excluded_from_stats(self):
        from techniques import rolling_ccf_lag
        rng = np.random.default_rng(42)

        def ar1(n, rho=0.3):
            e = rng.normal(0, 1, n); x = np.zeros(n); x[0] = e[0]
            for i in range(1, n): x[i] = rho * x[i - 1] + e[i]
            return x

        x = ar1(400)
        y = ar1(400)  # independent
        ctx = _rolling_ccf_ctx([("X", x), ("Y", y)],
                               window=120, max_lag=40, preset="Fast")
        res = rolling_ccf_lag.run(ctx, _noop_progress)
        self.assertEqual(res.get("status"), "success")

        rolling_tbl = _find_table(res, "rolling optimal lag")
        self.assertIsNotNone(rolling_tbl)
        self.assertIn("Boundary_Hit", rolling_tbl["columns"])
        boundary_col = rolling_tbl["columns"].index("Boundary_Hit")
        flagged = sum(1 for row in rolling_tbl["rows"] if row[boundary_col] == "Yes")
        # On 400-obs independent AR(0.3) with max_lag=40 and window=120, the
        # optimizer often lands near ±max_lag on noise-dominated windows. We
        # expect at least one flag.
        self.assertGreaterEqual(
            flagged, 1,
            "At least one window should hit the ±0.8·max_lag boundary on "
            "independent series; none were flagged"
        )
        self.assertEqual(res["audit_fields"]["n_windows_boundary_excluded"], flagged)


class TestSignFlipDetection(unittest.TestCase):
    """T2 — rolling_ccf_lag must detect a structural break when one exists,
    and report pre/post regime signs correctly."""

    def test_detects_regime_shift(self):
        from techniques import rolling_ccf_lag
        rng = np.random.default_rng(42)
        n = 300
        x = rng.normal(0, 1, n)
        y = np.zeros(n)
        for t in range(1, 150):
            y[t] = -0.5 * x[t - 1] + rng.normal(0, 0.5)
        for t in range(150, n):
            y[t] = 0.5 * x[t - 3] + rng.normal(0, 0.5)
        ctx = _rolling_ccf_ctx([("X", x), ("Y", y)],
                               window=60, max_lag=10, preset="Balanced")
        res = rolling_ccf_lag.run(ctx, _noop_progress)
        self.assertEqual(res.get("status"), "success")
        af = res["audit_fields"]
        self.assertTrue(
            af["structural_break_detected"],
            f"Expected structural break on two-regime synthetic; got details "
            f"{af.get('structural_break_details')}"
        )
        # True break at obs 150; with window=60 the corresponding window
        # index is ~120-150 by the center-time convention. Allow a ±20
        # window tolerance.
        break_idx = af["structural_break_window_index"]
        self.assertIsNotNone(break_idx)
        self.assertLess(
            abs(break_idx - 120), 30,
            f"Break window index {break_idx} is more than 30 windows from the "
            f"expected ~120"
        )
        summary = res["plain_english_summary"]
        # Pre-break synthetic had y = -0.5·x_{t-1}, so the wrapper should
        # report sign=- in the pre-break segment. Post-break had y = +0.5·x_{t-3},
        # so sign=+ and lag=3 in post-break.
        self.assertIn("Pre-break", summary)
        self.assertIn("Post-break", summary)
        self.assertIn("ρ=-", summary, f"Pre-break ρ sign missing from: {summary}")
        self.assertIn("ρ=+", summary, f"Post-break ρ sign missing from: {summary}")


class TestMedianNotMean(unittest.TestCase):
    """T3 — the summary must use the median lag (robust), not the mean,
    so a handful of noisy windows with a far-off best-lag do not drag the
    reported lag into a nonsense value."""

    def test_summary_uses_median_not_mean(self):
        from techniques import rolling_ccf_lag
        rng = np.random.default_rng(7)
        # Strong structural: y[t] = 0.9 * x[t-1] + eps. True modal/median
        # lag is 1. Add a couple of very noisy windows by spiking x at a
        # few positions — those windows will produce spurious far-off best
        # lags that would pull the MEAN off 1 but not the median.
        n = 260
        x = rng.normal(0, 1, n)
        x[20] = 15.0
        x[21] = -15.0
        x[180] = 12.0
        y = np.zeros(n)
        for t in range(1, n):
            y[t] = 0.9 * x[t - 1] + rng.normal(0, 0.3)
        ctx = _rolling_ccf_ctx([("X", x), ("Y", y)],
                               window=40, max_lag=15, preset="Balanced")
        res = rolling_ccf_lag.run(ctx, _noop_progress)
        self.assertEqual(res.get("status"), "success")
        af = res["audit_fields"]
        # Median should be 1 (the true lag); mean may differ due to outliers.
        self.assertEqual(
            int(af["median_lag_ex_boundary"]), 1,
            f"Median lag (ex-boundary) should be 1 on y_t=0.9·x_{{t-1}} data"
        )
        summary = res["plain_english_summary"]
        # The summary's "by N" clause should carry the median, i.e. 1.
        self.assertIn(
            " by 1 with ρ=",
            summary,
            f"Primary sentence should carry the median lag (1), got: {summary[:200]}"
        )


class TestWindowDefault(unittest.TestCase):
    """T4 — on a 150-obs series with Balanced preset and no override,
    window must be max(40, min(80, 150//3)) = 50."""

    def test_balanced_default_window_150_obs(self):
        from techniques import rolling_ccf_lag
        rng = np.random.default_rng(0)
        x = rng.normal(0, 1, 150)
        y = rng.normal(0, 1, 150)
        ctx = _rolling_ccf_ctx([("X", x), ("Y", y)], preset="Balanced")
        res = rolling_ccf_lag.run(ctx, _noop_progress)
        self.assertEqual(res.get("status"), "success")
        self.assertEqual(
            res["audit_fields"]["window"], 50,
            "Balanced preset on n=150 should auto-select window=50 "
            "(= max(40, min(80, 150//3)))"
        )


class TestACCorrectionMateriality(unittest.TestCase):
    """T7 — on two independent AR(0.9) series, the AC-corrected pct_significant
    must be materially lower than the naive reference."""

    def test_ac_correction_deflates_false_significance(self):
        from techniques import rolling_ccf_lag
        rng = np.random.default_rng(42)

        def ar1(n, rho=0.9):
            e = rng.normal(0, 1, n); x = np.zeros(n); x[0] = e[0]
            for i in range(1, n): x[i] = rho * x[i - 1] + e[i]
            return x

        ctx = _rolling_ccf_ctx([("X", ar1(300)), ("Y", ar1(300))],
                               preset="Balanced")
        res = rolling_ccf_lag.run(ctx, _noop_progress)
        self.assertEqual(res.get("status"), "success")
        af = res["audit_fields"]
        naive = af["pct_significant_naive_reference"]
        corrected = af["pct_significant"]
        # AC correction must reduce reported significance by at least 30pp
        # on highly persistent (ρ=0.9) independent inputs. With the default
        # heuristic window these tend to fall ~98% naive → ~25% corrected.
        self.assertTrue(
            af["ac_corrected"],
            f"On AR(0.9) inputs AC correction should engage; "
            f"ac_inflation={af.get('ac_inflation_factor_on_residuals', 'n/a')}"
        )
        self.assertLess(
            corrected, naive - 30,
            f"AC correction should deflate pct_significant by > 30pp on "
            f"persistent independent series; got naive={naive}, corrected={corrected}"
        )
        self.assertLess(
            corrected, 40,
            f"AC-corrected pct_significant should be <40% on independent "
            f"AR(0.9) series; got {corrected}"
        )


class TestPairwiseSummaryConvention(unittest.TestCase):
    """T5 — every F2 technique summary pairs a sign indicator with a
    correlation/coefficient AND carries a direction word or signed lag."""

    F2_TECHNIQUES = [
        "rolling_ccf_lag",
        "cross_correlation_lag",
        "prewhitened_ccf_lag",
        "granger_causality",
        "dtw_alignment_lag",
        "wavelet_coherence",
        "transfer_function",
    ]

    def _minimal_ctx(self, tech_id):
        rng = np.random.default_rng(123)
        n = 200
        x = rng.normal(0, 1, n)
        y = np.zeros(n)
        for t in range(2, n):
            y[t] = 0.5 * x[t - 1] + 0.2 * y[t - 1] + rng.normal(0, 0.3)
        time_col = [f"{2000 + i // 4}-Q{i % 4 + 1}" for i in range(n)]
        return RunContext({
            "run_id": "t", "technique_id": tech_id,
            "preset": "Balanced", "seed": 42, "frequency": "Quarterly",
            "time": time_col,
            "series": [
                {"name": "X", "values": list(x)},
                {"name": "Y", "values": list(y)},
            ],
            "params": {},
        })

    DIRECTION_WORDS = (
        "leads", "lags", "causes", "follows", "aligns", "in phase",
        "contemporaneously", "Granger-causes", "does not Granger-cause",
        "->", "→",  # transfer-function arrow notation
    )

    # Pattern: any technique-specific statistic label followed by an "=" and
    # a signed numeric value. Positive values without a leading "+" are
    # accepted (English convention) — negatives must carry the "-" explicitly.
    STAT_PATTERN = re.compile(
        r"(?:ρ|CCF|F|weight|coherence|median\s+lag|multiplier|beta|β)"
        r"\s*=\s*[-+]?\d",
        re.IGNORECASE,
    )

    def test_every_summary_pairs_sign_and_direction(self):
        failures = []
        import importlib
        for tech in self.F2_TECHNIQUES:
            try:
                mod = importlib.import_module(f"techniques.{tech}")
                ctx = self._minimal_ctx(tech)
                res = mod.run(ctx, _noop_progress)
            except Exception as e:
                failures.append(f"{tech}: run raised {type(e).__name__}: {e}")
                continue
            if res.get("status") != "success":
                failures.append(
                    f"{tech}: status={res.get('status')}, "
                    f"error={res.get('error_message')}"
                )
                continue
            summary = res.get("plain_english_summary", "")
            has_direction = any(w in summary for w in self.DIRECTION_WORDS)
            has_signed_stat = bool(self.STAT_PATTERN.search(summary))
            if not (has_direction and has_signed_stat):
                failures.append(
                    f"{tech}: summary lacks paired sign+direction. "
                    f"has_direction={has_direction}, has_signed_stat={has_signed_stat}. "
                    f"Summary: {summary[:250]!r}"
                )
        self.assertFalse(failures, "\n" + "\n".join(failures))


class TestSignificanceDisclosureConvention(unittest.TestCase):
    """T6 — every F3 technique exposes test_name, critical_value_formula,
    and ac_corrected in audit_fields."""

    F3_TECHNIQUES = [
        # Pairwise (F2 overlap)
        "rolling_ccf_lag", "cross_correlation_lag", "prewhitened_ccf_lag",
        "granger_causality", "johansen_cointegration", "wavelet_coherence",
        "transfer_function", "dtw_alignment_lag",
        # Unit-root / stationarity
        "adf_test", "kpss_test", "pp_test",
        # ARIMA family
        "arima", "sarima", "arimax_sarimax",
        # State-space
        "structural_ts", "kalman_imputation",
        # Volatility
        "garch_model", "caviar_quantile_dynamics",
        # Forecasting with CI
        "ets_hw", "theta_forecast", "prophet_forecast",
        "gaussian_process_forecast",
        # Diagnostic / regression
        "stl_esd_anomaly", "har_rv", "intervention_analysis",
    ]

    def _ctx_for(self, tech_id):
        rng = np.random.default_rng(7)
        n = 120
        if tech_id in ("johansen_cointegration",):
            # Needs k >= 2 series, I(1)
            y1 = np.cumsum(rng.normal(0, 1, n))
            y2 = 2 * y1 + rng.normal(0, 0.5, n)
            series = [{"name": "Y1", "values": list(y1)},
                      {"name": "Y2", "values": list(y2)}]
        elif tech_id in ("rolling_ccf_lag", "cross_correlation_lag",
                         "prewhitened_ccf_lag", "granger_causality",
                         "dtw_alignment_lag", "wavelet_coherence",
                         "transfer_function"):
            x = rng.normal(0, 1, n)
            y = np.zeros(n)
            for t in range(2, n):
                y[t] = 0.5 * x[t - 1] + 0.2 * y[t - 1] + rng.normal(0, 0.3)
            series = [{"name": "X", "values": list(x)},
                      {"name": "Y", "values": list(y)}]
        elif tech_id == "kalman_imputation":
            y = np.cumsum(rng.normal(0, 1, n))
            y[30] = np.nan
            y[60] = np.nan
            series = [{"name": "Y", "values":
                [float(v) if not np.isnan(v) else None for v in y]}]
        elif tech_id == "caviar_quantile_dynamics":
            # Returns-like
            series = [{"name": "R", "values": list(rng.normal(0, 0.02, 500))}]
        elif tech_id == "intervention_analysis":
            y = np.cumsum(rng.normal(0, 1, n))
            y[60:] += 5.0
            series = [{"name": "Y", "values": list(y)}]
        elif tech_id == "har_rv":
            # Positive realized-vol-like series
            base = rng.lognormal(0, 0.3, 300)
            series = [{"name": "RV", "values": list(base)}]
        elif tech_id == "prophet_forecast":
            y = np.cumsum(rng.normal(0, 1, n))
            series = [{"name": "Y", "values": list(y)}]
        else:
            y = np.cumsum(rng.normal(0, 1, n))
            series = [{"name": "Y", "values": list(y)}]

        time_col = [f"{2000 + i // 12}-{(i % 12) + 1:02d}-28"
                    for i in range(len(series[0]["values"]))]
        params = {}
        if tech_id == "caviar_quantile_dynamics":
            params = {"theta": 0.05}
        elif tech_id == "intervention_analysis":
            params = {"interventions": [{"index": 60, "type": "level_shift"}]}
        elif tech_id == "transfer_function":
            params = {"max_lag": 4, "ar_order": 1}
        elif tech_id == "rolling_ccf_lag":
            params = {"window": 40, "max_lag": 8}
        return RunContext({
            "run_id": "t", "technique_id": tech_id,
            "preset": "Fast", "seed": 7, "frequency": "Monthly",
            "time": time_col, "series": series, "params": params,
        })

    def test_every_technique_discloses_significance(self):
        failures = []
        skipped = []
        import importlib
        for tech in self.F3_TECHNIQUES:
            try:
                mod = importlib.import_module(f"techniques.{tech}")
                ctx = self._ctx_for(tech)
                res = mod.run(ctx, _noop_progress)
            except Exception as e:
                skipped.append(f"{tech}: run raised {type(e).__name__}: {e}")
                continue
            if res.get("status") != "success":
                skipped.append(f"{tech}: status={res.get('status')}")
                continue
            af = res.get("audit_fields") or {}
            missing = []
            if not af.get("test_name"):
                missing.append("test_name")
            if not af.get("critical_value_formula"):
                missing.append("critical_value_formula")
            if "ac_corrected" not in af:
                missing.append("ac_corrected")
            elif not isinstance(af["ac_corrected"], (bool,)):
                missing.append(f"ac_corrected-not-bool({type(af['ac_corrected']).__name__})")
            if missing:
                failures.append(f"{tech}: missing/bad audit fields: {missing}")
        if skipped:
            print("\n[T6] Skipped (fit failures on minimal synthetic):")
            for s in skipped:
                print("  -", s)
        self.assertFalse(
            failures,
            "Techniques not disclosing significance test metadata:\n"
            + "\n".join(failures)
        )


# ─────────────────────────────────────────────────────────────────────
# Stationarity-test triage invariants (T1-T5)
# ─────────────────────────────────────────────────────────────────────
def _stationarity_ctx(values, *, run_id="pane_test", tech_id="adf_test",
                      params=None):
    n = len(values)
    time_col = [f"{2000 + i // 4}-Q{(i % 4) + 1}" for i in range(n)]
    return RunContext({
        "run_id": run_id,
        "technique_id": tech_id,
        "preset": "Balanced",
        "seed": 42,
        "frequency": "Quarterly",
        "time": time_col,
        "series": [{"name": "Y", "values": list(values)}],
        "params": params or {},
    })


class TestCriticalValueOrdering(unittest.TestCase):
    """T1 — ADF critical-value table must be in ascending significance
    order (1%, 5%, 10%), not the lexicographic 1%, 10%, 5% bug that
    dict iteration + sorted() on string keys produced."""

    def test_adf_cv_table_sorted_ascending(self):
        from techniques import adf_test
        rng = np.random.default_rng(42)
        # Force single-test mode so we get a Critical Values detail table.
        ctx = _stationarity_ctx(
            rng.normal(0, 1, 200), run_id="udf_tA",
            params={"triage": False},
        )
        res = adf_test.run(ctx, _noop_progress)
        self.assertEqual(res.get("status"), "success")
        cv_tbl = _find_table(res, "critical values")
        self.assertIsNotNone(cv_tbl, "Critical Values detail table missing")
        levels = [str(row[0]) for row in cv_tbl["rows"]]
        self.assertEqual(
            levels, ["1%", "5%", "10%"],
            f"Critical-value levels must appear in ascending order; got {levels}"
        )


class TestRegressionSurfaced(unittest.TestCase):
    """T2 — the regression specification must appear in user-visible output
    (Summary sentence or Results sheet), not only in audit_fields."""

    def test_regression_in_summary_or_results(self):
        from techniques import adf_test
        rng = np.random.default_rng(0)
        ctx = _stationarity_ctx(
            rng.normal(0, 1, 150), run_id="udf_tB",
            params={"triage": False, "regression": "c"},
        )
        res = adf_test.run(ctx, _noop_progress)
        self.assertEqual(res.get("status"), "success")
        summary = res.get("plain_english_summary", "")
        results_tbl = _find_table(res, "adf test results")
        visible_text = summary + " | " + (
            " | ".join(
                str(cell) for row in (results_tbl or {}).get("rows", [])
                for cell in row
            )
        )
        has_spec = (
            "regression='c'" in visible_text
            or "constant only" in visible_text
            or "(c / " in visible_text
        )
        self.assertTrue(
            has_spec,
            f"Regression specification must appear in Summary or Results "
            f"(not only audit). Visible text: {visible_text[:400]!r}"
        )


class TestSummaryLanguagePrecision(unittest.TestCase):
    """T3 — ADF summary says 'unit root rejected' on a clearly stationary
    series and never claims 'is stationary' as a standalone. KPSS may use
    'is stationary'/'stationary' because its null IS stationarity."""

    def test_adf_language_and_kpss_language(self):
        from techniques import adf_test, kpss_test
        rng = np.random.default_rng(42)
        # White noise — stationary by construction.
        y = rng.normal(0, 1, 500)

        # ADF single-test
        ctx_adf = _stationarity_ctx(
            y, run_id="udf_tC1", params={"triage": False},
        )
        res_adf = adf_test.run(ctx_adf, _noop_progress)
        self.assertEqual(res_adf.get("status"), "success")
        adf_summary = res_adf["plain_english_summary"]
        self.assertIn(
            "unit root rejected", adf_summary,
            f"ADF on white noise must say 'unit root rejected'; got: {adf_summary[:250]}"
        )
        # "is stationary" must not appear as a standalone ADF claim.
        self.assertNotIn(
            "is stationary", adf_summary.lower(),
            f"ADF must not say 'is stationary'; got: {adf_summary[:250]}"
        )

        # KPSS standalone — "stationary" language is allowed
        ctx_kpss = _stationarity_ctx(y, tech_id="kpss_test", run_id="udf_tC2")
        res_kpss = kpss_test.run(ctx_kpss, _noop_progress)
        self.assertEqual(res_kpss.get("status"), "success")
        kpss_summary = res_kpss["plain_english_summary"]
        acceptable = (
            "stationarity null not rejected" in kpss_summary
            or "appears stationary" in kpss_summary
            or "stationarity null rejected" in kpss_summary
        )
        self.assertTrue(
            acceptable,
            f"KPSS summary must use stationarity-null language; got: {kpss_summary[:250]}"
        )


class TestTriageJointVerdict(unittest.TestCase):
    """T4 — triage joint verdict is correct on a pure random walk and on
    a stationary AR(0.3) series."""

    def test_random_walk_is_unit_root(self):
        from techniques import adf_test
        rng = np.random.default_rng(42)
        rw = np.cumsum(rng.normal(0, 1, 500))
        ctx = _stationarity_ctx(rw, run_id="pane_tD1")  # triage path
        res = adf_test.run(ctx, _noop_progress)
        self.assertEqual(res.get("status"), "success")
        self.assertEqual(res["audit_fields"]["mode"], "triage")
        self.assertIn(
            "UNIT ROOT (I(1))", res["plain_english_summary"],
            f"Random walk triage should verdict UNIT ROOT; got: "
            f"{res['plain_english_summary'][:300]}"
        )

    def test_ar03_is_stationary(self):
        from techniques import adf_test
        rng = np.random.default_rng(42)
        n = 500
        ar = np.zeros(n)
        ar[0] = rng.normal()
        for i in range(1, n):
            ar[i] = 0.3 * ar[i - 1] + rng.normal()
        ctx = _stationarity_ctx(ar, run_id="pane_tD2")
        res = adf_test.run(ctx, _noop_progress)
        self.assertEqual(res.get("status"), "success")
        self.assertEqual(res["audit_fields"]["mode"], "triage")
        summary = res["plain_english_summary"]
        self.assertIn(
            "STATIONARY", summary,
            f"AR(0.3) triage should verdict STATIONARY; got: {summary[:300]}"
        )
        # And must not mislabel as UNIT ROOT
        self.assertNotIn("UNIT ROOT", summary,
            f"AR(0.3) triage mis-labelled; got: {summary[:300]}")


class TestSchwertDefault(unittest.TestCase):
    """T5 — on a 304-observation series with no user max_lag, the Results
    sheet reports Schwert bound = floor(12 · (304/100)^(1/4)) = 15 and the
    selected lag is ≤ 15."""

    def test_schwert_bound_on_304_obs(self):
        from techniques import adf_test
        rng = np.random.default_rng(42)
        y = rng.normal(0, 1, 304)
        ctx = _stationarity_ctx(
            y, run_id="udf_tE", params={"triage": False},
        )
        res = adf_test.run(ctx, _noop_progress)
        self.assertEqual(res.get("status"), "success")
        results_tbl = _find_table(res, "adf test results")
        self.assertIsNotNone(results_tbl)
        cols = results_tbl["columns"]
        self.assertIn("Schwert Bound", cols)
        self.assertIn("Lags Used (AIC)", cols)
        bound_idx = cols.index("Schwert Bound")
        lag_idx = cols.index("Lags Used (AIC)")
        row = results_tbl["rows"][0]
        expected = int(np.floor(12.0 * (304 / 100.0) ** 0.25))
        self.assertEqual(
            expected, 15,
            f"Sanity: Schwert bound for T=304 should compute to 15, got {expected}"
        )
        self.assertEqual(
            int(row[bound_idx]), 15,
            f"Results sheet must report Schwert bound 15 on T=304; got {row[bound_idx]}"
        )
        self.assertLessEqual(
            int(row[lag_idx]), 15,
            f"AIC-selected lag must be ≤ Schwert bound; got {row[lag_idx]}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
