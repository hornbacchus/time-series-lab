"""Tests for src/bvar/conditioning.py — Step 4 BGL-2015 conditional forecasting."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from techniques.bond_yield_forecast.conditioning import (
    ConditionalForecast,
    ConditionalForecaster,
    EconomistProjections,
    PosteriorMetadata,
    YieldCurveForecast,
    write_projections_template,
)
from techniques.bond_yield_forecast.data import InputValidationError
from techniques.bond_yield_forecast.estimation import BVARSV
from techniques.bond_yield_forecast.priors import MinnesotaPrior


# ---------------------------------------------------------------------------
# Fixtures (small / fast to keep the suite under a few seconds)
# ---------------------------------------------------------------------------


def _toy_panel(T: int = 80, seed: int = 0) -> pd.DataFrame:
    """4-variable toy panel: 2 macros + 2 PCs.

    Generated as a stable VAR(1) so the BVAR-SV fit converges quickly on a
    short chain.
    """
    rng = np.random.default_rng(seed)
    n = 4
    cols = ["macro_a", "macro_b", "pc1", "pc2"]
    Y = np.zeros((T, n))
    Y[0] = rng.standard_normal(n) * 0.3
    for t in range(1, T):
        Y[t] = 0.5 * Y[t - 1] + rng.standard_normal(n) * 0.4
    idx = pd.period_range("1990-Q1", periods=T, freq="Q-DEC")
    return pd.DataFrame(Y, index=idx, columns=cols)


def _toy_results(seed: int = 0) -> "BVARSVResults":
    panel = _toy_panel(T=80, seed=seed)
    prior = MinnesotaPrior(
        n_vars=4, n_lags=1, training_data=panel,
        persistence_prior={"macro_a": 0.5, "macro_b": 0.5, "pc1": 0.9, "pc2": 0.5},
        variable_names=list(panel.columns),
    )
    bvar = BVARSV(panel, n_lags=1, prior=prior, n_draws=200, n_burn=80, seed=seed)
    return bvar.estimate()


def _toy_pca_dict() -> dict:
    """Identity-ish PCA dict consistent with target_names ['pc1', 'pc2']."""
    return {
        "loadings": np.array([[1.0, 0.0], [0.5, 0.7], [0.2, -0.3]]),  # (n_maturities, n_pc)
        "mean": np.array([3.0, 3.5, 4.0]),
        "explained_variance_ratio": np.array([0.7, 0.3]),
        "yield_names": ["3M", "1Y", "10Y"],
        "component_names": ["pc1", "pc2"],
    }


def _toy_projections(panel: pd.DataFrame, horizon: int, seed: int = 0) -> EconomistProjections:
    """Aligned projections of macro_a, macro_b for `horizon` quarters."""
    rng = np.random.default_rng(seed)
    last = panel.index[-1]
    fut = pd.period_range(last + 1, periods=horizon, freq="Q-DEC")
    df = pd.DataFrame(
        {
            "macro_a": rng.standard_normal(horizon) * 0.2,
            "macro_b": rng.standard_normal(horizon) * 0.2,
        },
        index=fut,
    )
    return EconomistProjections(df, macro_variables=["macro_a", "macro_b"])


def _conditioning_config(
    horizon: int = 4,
    n_paths_per_draw: int = 5,
    n_draws_subsample: int = 30,
    strict: bool = True,
    proj_unc: dict | None = None,
) -> dict:
    return {
        "horizon": horizon,
        "n_paths_per_draw": n_paths_per_draw,
        "n_draws_subsample": n_draws_subsample,
        "macro_variables": ["macro_a", "macro_b"],
        "enforce_strict_match": strict,
        "projection_uncertainty": proj_unc or {"macro_a": 0.5, "macro_b": 0.5},
        "workbook_sheet": "projections",
    }


# ---------------------------------------------------------------------------
# Test 1: validation
# ---------------------------------------------------------------------------


def test_economist_projections_validates_panel_alignment():
    panel = _toy_panel()
    last = panel.index[-1]

    # Aligned: passes.
    fut_ok = pd.period_range(last + 1, periods=4, freq="Q-DEC")
    df_ok = pd.DataFrame(
        {"macro_a": [0.1, 0.2, 0.3, 0.4], "macro_b": [0.1, 0.2, 0.3, 0.4]},
        index=fut_ok,
    )
    proj = EconomistProjections(df_ok, macro_variables=["macro_a", "macro_b"])
    proj.validate(panel, n_lags=1)  # no exception

    # Gap (skip a quarter): fails.
    fut_gap = pd.period_range(last + 2, periods=4, freq="Q-DEC")
    df_gap = pd.DataFrame(
        {"macro_a": [0.1] * 4, "macro_b": [0.1] * 4}, index=fut_gap
    )
    proj_gap = EconomistProjections(df_gap, macro_variables=["macro_a", "macro_b"])
    with pytest.raises(InputValidationError, match="projection_alignment"):
        proj_gap.validate(panel, n_lags=1)

    # Overlap (start at last in-sample period): fails.
    fut_over = pd.period_range(last, periods=4, freq="Q-DEC")
    df_over = pd.DataFrame(
        {"macro_a": [0.1] * 4, "macro_b": [0.1] * 4}, index=fut_over
    )
    proj_over = EconomistProjections(df_over, macro_variables=["macro_a", "macro_b"])
    with pytest.raises(InputValidationError, match="projection_alignment"):
        proj_over.validate(panel, n_lags=1)

    # Missing column: fails at construction.
    df_missing = pd.DataFrame({"macro_a": [0.1] * 4}, index=fut_ok)
    with pytest.raises(InputValidationError, match="missing_column"):
        EconomistProjections(df_missing, macro_variables=["macro_a", "macro_b"])

    # NaN: fails on validate.
    df_nan = df_ok.copy()
    df_nan.iloc[1, 0] = np.nan
    proj_nan = EconomistProjections(df_nan, macro_variables=["macro_a", "macro_b"])
    with pytest.raises(InputValidationError, match="projection_nan"):
        proj_nan.validate(panel, n_lags=1)


# ---------------------------------------------------------------------------
# Tests 2 + 3: unconditional recovery (per Step 4 refinement 1)
# ---------------------------------------------------------------------------


def test_soft_match_with_large_uncertainty_recovers_unconditional():
    """Soft match with large projection_uncertainty ≈ uninformative observation.

    The soft conditional posterior on targets should agree with the
    unconditional posterior within MC noise: per-target, per-horizon median
    and 16-84 band differ by < 0.10 in target-space units. Tests that the
    soft-conditioning math reduces correctly to the unconditional case in
    the limit of weak conditioning information.
    """
    results = _toy_results(seed=11)
    horizon = 4
    panel = results.data_used
    proj = _toy_projections(panel, horizon=horizon, seed=2)

    # Unconditional posterior predictive baseline.
    unc = results.posterior_predictive_unconditional(
        horizon=horizon, n_paths=20, seed=42,
    )
    # paths shape: (n_kept * n_paths, horizon, n_vars)
    pc_idx = [results.variable_names.index("pc1"), results.variable_names.index("pc2")]
    unc_target = unc["paths"][:, :, pc_idx]  # (P, H, 2)
    unc_q = np.quantile(unc_target, [0.16, 0.50, 0.84], axis=0)

    cfg = _conditioning_config(
        horizon=horizon, n_paths_per_draw=20, n_draws_subsample=None,
        strict=False, proj_unc={"macro_a": 100.0, "macro_b": 100.0},
    )
    cf = ConditionalForecaster(
        results=results, projections=proj, config_section=cfg, seed=42,
    ).forecast()
    cond_q = np.quantile(cf.target_paths, [0.16, 0.50, 0.84], axis=0)

    # Median + 16-84 band agree within 0.10 (target-space units, std~0.4).
    diff = np.abs(cond_q - unc_q)
    assert diff.max() < 0.10, (
        f"Soft-match conditional disagrees with unconditional: max |diff|={diff.max():.4f}"
    )


def test_strict_match_mean_recovers_unconditional_mean():
    """Strict match with projections = unconditional median path.

    Under strict match with the macro path pinned to the unconditional
    median, the MEAN of the conditional target distribution per horizon
    should approximately equal the unconditional MEAN per horizon (because
    the conditioning is on a path that IS the unconditional mean of the
    macros). Variance differs — that's expected, not a failure.
    """
    results = _toy_results(seed=13)
    horizon = 4

    # Unconditional baseline.
    unc = results.posterior_predictive_unconditional(
        horizon=horizon, n_paths=40, seed=7,
    )
    macro_idx = [results.variable_names.index("macro_a"), results.variable_names.index("macro_b")]
    pc_idx = [results.variable_names.index("pc1"), results.variable_names.index("pc2")]
    unc_macro_median = np.median(unc["paths"][:, :, macro_idx], axis=0)  # (H, 2)
    unc_target_mean = np.mean(unc["paths"][:, :, pc_idx], axis=0)         # (H, 2)

    # Build projections = unconditional macro median.
    last = results.last_observation_period
    fut = pd.period_range(last + 1, periods=horizon, freq="Q-DEC")
    df_proj = pd.DataFrame(
        unc_macro_median, index=fut, columns=["macro_a", "macro_b"]
    )
    proj = EconomistProjections(df_proj, macro_variables=["macro_a", "macro_b"])

    cfg = _conditioning_config(
        horizon=horizon, n_paths_per_draw=20, n_draws_subsample=None,
        strict=True,
    )
    cf = ConditionalForecaster(
        results=results, projections=proj, config_section=cfg, seed=7,
    ).forecast()
    cond_target_mean = np.mean(cf.target_paths, axis=0)  # (H, 2)

    diff = np.abs(cond_target_mean - unc_target_mean)
    assert diff.max() < 0.10, (
        f"Strict-match conditional MEAN disagrees with unconditional MEAN: "
        f"max |diff|={diff.max():.4f}"
    )


# ---------------------------------------------------------------------------
# Tests 4–8
# ---------------------------------------------------------------------------


def test_conditional_forecast_strict_match_pins_macros():
    results = _toy_results(seed=21)
    horizon = 4
    proj = _toy_projections(results.data_used, horizon=horizon, seed=5)
    cfg = _conditioning_config(horizon=horizon, strict=True)

    cf = ConditionalForecaster(
        results=results, projections=proj, config_section=cfg, seed=0,
    ).forecast()

    proj_arr = proj.to_array(["macro_a", "macro_b"])  # (H, 2)
    # Every path's macro path must equal the projection (numerically).
    diff = np.abs(cf.macro_paths - proj_arr[None, :, :])
    assert diff.max() < 1e-10, f"macro_paths not pinned: max diff={diff.max():.3e}"


def test_conditional_forecast_with_uncertainty_disperses_macros():
    results = _toy_results(seed=31)
    horizon = 4
    proj = _toy_projections(results.data_used, horizon=horizon, seed=3)
    proj_unc = {"macro_a": 0.5, "macro_b": 0.5}
    cfg = _conditioning_config(
        horizon=horizon, n_paths_per_draw=30, n_draws_subsample=None,
        strict=False, proj_unc=proj_unc,
    )

    cf = ConditionalForecaster(
        results=results, projections=proj, config_section=cfg, seed=0,
    ).forecast()
    # Across all paths, macro paths should have non-trivial spread (std > 0).
    macro_std = cf.macro_paths.std(axis=0)  # (H, 2)
    assert (macro_std > 0.05).all(), (
        f"macro_paths std too small for soft match: {macro_std}"
    )


def test_yield_space_conversion_is_smooth():
    results = _toy_results(seed=41)
    horizon = 4
    proj = _toy_projections(results.data_used, horizon=horizon, seed=7)
    cfg = _conditioning_config(horizon=horizon, strict=True, n_paths_per_draw=8,
                               n_draws_subsample=20)

    cf = ConditionalForecaster(
        results=results, projections=proj, config_section=cfg, seed=0,
    ).forecast()
    pca_dict = _toy_pca_dict()
    yc = cf.to_yield_space(pca_dict)
    # Median yield curve at each horizon: adjacent-maturity diff < 1 pct.
    median_yields = np.median(yc.yield_paths, axis=0)  # (H, n_maturities)
    for h in range(yc.horizon):
        diffs = np.abs(np.diff(median_yields[h]))
        assert diffs.max() < 1.5, (
            f"non-smooth median curve at h={h+1}: max diff={diffs.max():.3f}"
        )


def test_conditional_forecast_save_load_round_trip(tmp_path: Path):
    results = _toy_results(seed=51)
    horizon = 4
    proj = _toy_projections(results.data_used, horizon=horizon, seed=11)
    cfg = _conditioning_config(horizon=horizon, n_paths_per_draw=4, n_draws_subsample=10)

    cf = ConditionalForecaster(
        results=results, projections=proj, config_section=cfg, seed=0,
    ).forecast()
    cf_path = tmp_path / "cond.npz"
    cf.save(cf_path)
    cf_loaded = ConditionalForecast.load(cf_path)

    np.testing.assert_array_equal(cf.target_paths, cf_loaded.target_paths)
    np.testing.assert_array_equal(cf.macro_paths, cf_loaded.macro_paths)
    assert cf.target_names == cf_loaded.target_names
    assert cf.macro_names == cf_loaded.macro_names
    assert cf.origin_period == cf_loaded.origin_period
    assert cf.horizon == cf_loaded.horizon

    pca_dict = _toy_pca_dict()
    yc = cf.to_yield_space(pca_dict)
    yc_path = tmp_path / "yc.npz"
    yc.save(yc_path)
    yc_loaded = YieldCurveForecast.load(yc_path)
    np.testing.assert_array_equal(yc.yield_paths, yc_loaded.yield_paths)
    assert yc.maturity_names == yc_loaded.maturity_names
    assert yc.origin_period == yc_loaded.origin_period


def test_generate_projections_template_produces_correct_structure(tmp_path: Path):
    out = tmp_path / "tmpl.xlsx"
    last = pd.Period("2025-Q4", freq="Q-DEC")
    macro_columns = ["A", "B", "C"]
    write_projections_template(
        output_path=out,
        last_observation_period=last,
        horizon=8,
        macro_columns=macro_columns,
    )
    assert out.exists()

    # Read back.
    xl = pd.ExcelFile(out, engine="openpyxl")
    assert "projections" in xl.sheet_names
    assert "README" in xl.sheet_names
    df = pd.read_excel(out, sheet_name="projections")
    assert list(df.columns)[0] == "Quarter"
    assert list(df.columns)[1:] == macro_columns
    assert len(df) == 8
    assert df.iloc[0]["Quarter"] == "2026-Q1"
    assert df.iloc[-1]["Quarter"] == "2027-Q4"


def test_conditional_forecast_seed_reproducibility():
    results = _toy_results(seed=61)
    horizon = 4
    proj = _toy_projections(results.data_used, horizon=horizon, seed=13)
    cfg = _conditioning_config(horizon=horizon, n_paths_per_draw=6, n_draws_subsample=20)

    a = ConditionalForecaster(
        results=results, projections=proj, config_section=cfg, seed=999,
    ).forecast()
    b = ConditionalForecaster(
        results=results, projections=proj, config_section=cfg, seed=999,
    ).forecast()
    np.testing.assert_array_equal(a.target_paths, b.target_paths)
    np.testing.assert_array_equal(a.macro_paths, b.macro_paths)


# ---------------------------------------------------------------------------
# Numba-vs-Python reference: byte-equality check on the inner loop
# ---------------------------------------------------------------------------


def _python_reference_forecast_inner(
    B, A_inv, h_T, omega, phi, mu,
    state_init, projection,
    target_idx, macro_idx,
    strict, R_diag,
    rng_z_target, rng_z_macro, rng_z_h,
):
    """Pure-NumPy reference implementing the SAME algorithm as
    src/bvar/_conditional_inner.py:conditional_forecast_inner_loop.

    Uses np.linalg.cholesky and np.linalg.solve to match the JIT's
    library calls exactly. The reference's purpose is to validate
    'the JIT correctly executes the algorithm we wrote', not 'the
    JIT matches the pre-numba implementation' (the latter cannot
    match byte-for-byte due to Cholesky-vs-SVD basis difference).
    """
    n_vars = B.shape[0]
    n_kp1 = B.shape[1]
    n_t = target_idx.shape[0]
    n_m = macro_idx.shape[0]
    n_lags = state_init.shape[0]
    n_paths = rng_z_target.shape[0]
    horizon = rng_z_target.shape[1]

    target_paths = np.empty((n_paths, horizon, n_t))
    macro_paths = np.empty((n_paths, horizon, n_m))

    eye_t = np.eye(n_t)
    eye_joint = np.eye(n_t + n_m)
    ridge = 1e-12

    for path in range(n_paths):
        state = state_init.copy()
        h = h_T.copy()

        for t in range(horizon):
            x = np.empty(n_kp1)
            x[0] = 1.0
            offset = 1
            for l in range(n_lags):
                row = state[n_lags - 1 - l]
                for j in range(n_vars):
                    x[offset + j] = row[j]
                offset += n_vars

            mu_y = B @ x

            scaled = np.empty((n_vars, n_vars))
            for i in range(n_vars):
                for j in range(n_vars):
                    scaled[i, j] = A_inv[i, j] * np.exp(h[j])
            Sigma_y = scaled @ A_inv.T

            S_tt = np.empty((n_t, n_t))
            S_tm = np.empty((n_t, n_m))
            S_mm = np.empty((n_m, n_m))
            mu_t = np.empty(n_t)
            mu_m = np.empty(n_m)
            for i in range(n_t):
                mu_t[i] = mu_y[target_idx[i]]
                for j in range(n_t):
                    S_tt[i, j] = Sigma_y[target_idx[i], target_idx[j]]
                for j in range(n_m):
                    S_tm[i, j] = Sigma_y[target_idx[i], macro_idx[j]]
            for i in range(n_m):
                mu_m[i] = mu_y[macro_idx[i]]
                for j in range(n_m):
                    S_mm[i, j] = Sigma_y[macro_idx[i], macro_idx[j]]

            proj_t = projection[t]

            if strict:
                resid = np.linalg.solve(S_mm, proj_t - mu_m)
                cond_mean_t = mu_t + S_tm @ resid
                K = np.linalg.solve(S_mm, S_tm.T)
                cond_cov_t = S_tt - S_tm @ K
                L = np.linalg.cholesky(cond_cov_t + ridge * eye_t)
                target_t = cond_mean_t + L @ rng_z_target[path, t]
                macro_t = proj_t.copy()
            else:
                S_pp = S_mm.copy()
                for i in range(n_m):
                    S_pp[i, i] = S_pp[i, i] + R_diag[i]

                resid = np.linalg.solve(S_pp, proj_t - mu_m)
                cond_mean_t = mu_t + S_tm @ resid
                cond_mean_m = mu_m + S_mm @ resid
                K_pp = np.linalg.solve(S_pp, S_tm.T)
                cond_cov_t = S_tt - S_tm @ K_pp
                K_pm = np.linalg.solve(S_pp, S_mm)
                cond_cov_m = S_mm - S_mm @ K_pm
                cond_cov_tm = S_tm - S_tm @ K_pm

                joint_cov = np.empty((n_t + n_m, n_t + n_m))
                for i in range(n_t):
                    for j in range(n_t):
                        joint_cov[i, j] = cond_cov_t[i, j]
                    for j in range(n_m):
                        joint_cov[i, n_t + j] = cond_cov_tm[i, j]
                for i in range(n_m):
                    for j in range(n_t):
                        joint_cov[n_t + i, j] = cond_cov_tm[j, i]
                    for j in range(n_m):
                        joint_cov[n_t + i, n_t + j] = cond_cov_m[i, j]

                joint_mean = np.empty(n_t + n_m)
                for i in range(n_t):
                    joint_mean[i] = cond_mean_t[i]
                for i in range(n_m):
                    joint_mean[n_t + i] = cond_mean_m[i]

                z_joint = np.empty(n_t + n_m)
                for i in range(n_t):
                    z_joint[i] = rng_z_target[path, t, i]
                for i in range(n_m):
                    z_joint[n_t + i] = rng_z_macro[path, t, i]

                Lj = np.linalg.cholesky(joint_cov + ridge * eye_joint)
                sample = joint_mean + Lj @ z_joint
                target_t = sample[:n_t]
                macro_t = sample[n_t:]

            for i in range(n_t):
                target_paths[path, t, i] = target_t[i]
            for i in range(n_m):
                macro_paths[path, t, i] = macro_t[i]

            y_t = np.empty(n_vars)
            for i in range(n_t):
                y_t[target_idx[i]] = target_t[i]
            for i in range(n_m):
                y_t[macro_idx[i]] = macro_t[i]
            for l in range(n_lags - 1):
                state[l] = state[l + 1]
            state[n_lags - 1] = y_t

            for i in range(n_vars):
                h[i] = (
                    phi[i] * h[i]
                    + (1.0 - phi[i]) * mu[i]
                    + omega[i] * rng_z_h[path, t, i]
                )

    return target_paths, macro_paths


def test_conditional_forecast_numba_matches_pure_python_baseline():
    """The numba inner loop and a pure-Python reference of the same
    Cholesky-based algorithm must produce byte-identical paths.

    This is the strongest provable equivalence: same RNG-pre-draw
    pattern, same Cholesky transform, same step ordering. If they
    diverge there is a bug in the numba implementation.
    """
    from techniques.bond_yield_forecast._conditional_inner import conditional_forecast_inner_loop

    results = _toy_results(seed=11)
    horizon = 4
    proj = _toy_projections(results.data_used, horizon=horizon, seed=2)

    n_paths = 10
    n_draws_used = 20
    n_target = 2
    n_macro = 2
    n_vars = 4

    cfg = _conditioning_config(
        horizon=horizon, n_paths_per_draw=n_paths,
        n_draws_subsample=n_draws_used, strict=True,
    )

    forecaster = ConditionalForecaster(
        results=results, projections=proj, config_section=cfg, seed=42,
    )
    cf_numba = forecaster.forecast()

    # Re-run the same forecast through the pure-Python reference using
    # the exact same draw selection, RNG bulk pre-draw, and per-draw
    # parameters.
    rng = np.random.default_rng(forecaster.seed)
    n_kept = forecaster.results.coefficients.shape[0]
    draw_indices = rng.choice(n_kept, size=n_draws_used, replace=False)
    draw_indices.sort()
    n_total = n_draws_used * n_paths
    all_z = rng.standard_normal((n_total, horizon, n_target + n_macro + n_vars))
    rng_z_target = all_z[:, :, :n_target]
    rng_z_macro = all_z[:, :, n_target:n_target + n_macro]
    rng_z_h = all_z[:, :, n_target + n_macro:]

    target_idx_arr = np.asarray(forecaster.target_idx, dtype=np.int64)
    macro_idx_arr = np.asarray(forecaster.macro_idx, dtype=np.int64)
    state_init = forecaster.results.data_used.to_numpy(dtype=float)[
        -forecaster.results.n_lags:
    ].astype(float).copy()
    R_diag = np.zeros(n_macro, dtype=float)
    projection_arr = forecaster.projection_array.astype(float)

    target_paths_ref = np.empty((n_total, horizon, n_target))
    macro_paths_ref = np.empty((n_total, horizon, n_macro))
    idx = 0
    for d in draw_indices:
        B = forecaster.results.coefficients[d].astype(float)
        A = forecaster.results.A_lower_triangular[d]
        try:
            A_inv = np.linalg.inv(A).astype(float)
        except np.linalg.LinAlgError:
            A_inv = np.linalg.pinv(A).astype(float)
        h_T_d = forecaster.results.log_volatilities[d, -1, :].astype(float).copy()
        phi_d = forecaster.results.phi[d].astype(float)
        omega_d = forecaster.results.omega[d].astype(float)
        mu_d = forecaster.results.mu[d].astype(float)

        z_t = np.ascontiguousarray(rng_z_target[idx:idx + n_paths])
        z_m = np.ascontiguousarray(rng_z_macro[idx:idx + n_paths])
        z_h = np.ascontiguousarray(rng_z_h[idx:idx + n_paths])

        tgt, mac = _python_reference_forecast_inner(
            B, A_inv, h_T_d, omega_d, phi_d, mu_d,
            state_init, projection_arr,
            target_idx_arr, macro_idx_arr,
            True, R_diag,
            z_t, z_m, z_h,
        )
        target_paths_ref[idx:idx + n_paths] = tgt
        macro_paths_ref[idx:idx + n_paths] = mac
        idx += n_paths

    np.testing.assert_array_equal(cf_numba.target_paths, target_paths_ref)
    np.testing.assert_array_equal(cf_numba.macro_paths, macro_paths_ref)


# ---------------------------------------------------------------------------
# S0.7 — typed PosteriorMetadata dataclass
# ---------------------------------------------------------------------------


def _build_small_conditional_forecast():
    """Helper: produce a tiny ConditionalForecast for metadata tests."""
    results = _toy_results(seed=21)
    horizon = 4
    proj = _toy_projections(results.data_used, horizon=horizon, seed=5)
    cfg = _conditioning_config(horizon=horizon, n_paths_per_draw=4,
                               n_draws_subsample=10)
    forecaster = ConditionalForecaster(
        results=results, projections=proj, config_section=cfg, seed=0,
    )
    return forecaster.forecast()


def test_conditional_forecast_metadata_is_typed_dataclass():
    """ConditionalForecast.posterior_metadata is a PosteriorMetadata
    instance, not a dict (S0.7)."""
    cf = _build_small_conditional_forecast()
    assert isinstance(cf.posterior_metadata, PosteriorMetadata)
    # Attribute access works.
    assert isinstance(cf.posterior_metadata.n_total_paths, int)
    assert isinstance(cf.posterior_metadata.macro_variables, list)


def test_conditional_forecast_metadata_save_load_round_trip(tmp_path):
    """Save -> load preserves all PosteriorMetadata fields."""
    cf = _build_small_conditional_forecast()
    p = tmp_path / "cf.npz"
    cf.save(p)
    cf2 = ConditionalForecast.load(p)
    assert isinstance(cf2.posterior_metadata, PosteriorMetadata)
    assert cf.posterior_metadata == cf2.posterior_metadata


def test_yield_curve_forecast_metadata_is_typed_dataclass(tmp_path):
    """YieldCurveForecast.posterior_metadata is also PosteriorMetadata
    (parallel container; metadata is carried through to_yield_space)."""
    cf = _build_small_conditional_forecast()
    pca_dict = _toy_pca_dict()
    yc = cf.to_yield_space(pca_dict)
    assert isinstance(yc.posterior_metadata, PosteriorMetadata)
    # Save/load round-trips correctly.
    p = tmp_path / "yc.npz"
    yc.save(p)
    yc2 = YieldCurveForecast.load(p)
    assert isinstance(yc2.posterior_metadata, PosteriorMetadata)
    assert yc.posterior_metadata == yc2.posterior_metadata
