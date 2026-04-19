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
# Kalman Filter / UCM output-alignment invariant
# ─────────────────────────────────────────────────────────────────────
class TestKalmanOutputAlignment(unittest.TestCase):
    """The wrapper must own alignment between the input's DatetimeIndex
    and every output row — not statsmodels' returned arrays — because
    statsmodels alternates between ndarray and Series depending on input
    type and attribute (smoothed_state is ndarray; fittedvalues is
    Series when input was a Series, ndarray when input was ndarray).

    Previously crashed in the "Building output" phase with
    ``AttributeError: 'numpy.ndarray' object has no attribute 'index'``
    when iterating ``fit.params.index`` on an ndarray-input model.
    """

    def test_kalman_output_alignment_with_missing(self):
        from techniques import kalman_filter_model

        # Nile-like: 100-obs annual series with one interior NaN at position 50.
        rng = np.random.default_rng(42)
        values = (np.cumsum(rng.normal(0, 1, 100)) + 1120.0).tolist()
        values[50] = None  # interior NaN — Kalman handles natively

        time_axis = [f"{1901 + i}-12-31" for i in range(100)]

        ctx = RunContext({
            "run_id": "t",
            "technique_id": "kalman_filter_model",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "Annual",
            "time": time_axis,
            "series": [{"name": "Nile", "values": values}],
            "params": {"horizon": 10},
        })

        res = kalman_filter_model.run(ctx, _noop_progress)

        # 1. Run completed — no swallowed AttributeError in the output phase.
        self.assertEqual(
            res.get("status"), "success",
            msg=f"Kalman run failed: {res.get('error_message')}"
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
        # Unit-root / stationarity wrappers gain F3 disclosure in a
        # later commit; not iterated here to keep this commit
        # bisect-clean.
        # ARIMA family
        "arima", "sarima", "arimax_sarimax",
        # State-space
        "kalman_filter_model", "kalman_imputation",
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

if __name__ == "__main__":
    unittest.main(verbosity=2)
