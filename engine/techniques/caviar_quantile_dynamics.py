"""
CAViaR (Conditional Autoregressive Value-at-Risk) quantile dynamics
for Time Series Lab.

Implements the Engle & Manganelli (2004) CAViaR model for dynamic quantile estimation.
The quantile q_t evolves as an autoregressive process, estimated by minimizing
the asymmetric (quantile) loss function.

Supported specifications:
- Symmetric Absolute Value (SAV):
    q_t = beta_0 + beta_1 * q_{t-1} + beta_2 * |y_{t-1}|
- Asymmetric Slope (AS):
    q_t = beta_0 + beta_1 * q_{t-1} + beta_2 * max(y_{t-1}, 0) + beta_3 * min(y_{t-1}, 0)
- Indirect GARCH (IG):
    q_t = (beta_0 + beta_1 * q_{t-1}^2 + beta_2 * y_{t-1}^2)^(1/2)
"""

import numpy as np
from scipy.optimize import minimize

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    format_significance_disclosure,
)

_PRESET_CONFIG = {
    "Fast":     {"n_restarts": 3,  "maxiter": 500},
    "Balanced": {"n_restarts": 10, "maxiter": 2000},
    "Thorough": {"n_restarts": 30, "maxiter": 5000},
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Estimate CAViaR model for dynamic quantile / VaR.

    Parameters (via ctx.params)
    ---------------------------
    theta : float, optional
        Quantile level (default 0.05 for 5% VaR).
    specification : str, optional
        'SAV' (default), 'AS', or 'IG'.
    """
    try:
        progress_callback("Validating inputs", 5)
        np.random.seed(ctx.seed)

        name, values = ctx.get_primary_series()
        warnings = []

        # Drop NaN
        clean = values[~np.isnan(values)]
        n_dropped = len(values) - len(clean)
        if n_dropped > 0:
            warnings.append(f"{n_dropped} missing values removed.")

        n = len(clean)
        if n < 100:
            return make_error_response(
                ctx,
                f"Only {n} valid observations. CAViaR needs at least 100 for reliable estimation.",
                error_fixes=["Provide a longer return series."],
            )

        theta = float(ctx.get_param("theta", 0.05))
        if theta <= 0 or theta >= 1:
            return make_error_response(
                ctx,
                f"Quantile level theta must be in (0, 1), got {theta}.",
                error_fixes=["Set theta between 0 and 1 (e.g., 0.05 for 5% VaR)."],
            )

        spec = ctx.get_param("specification", "SAV").upper()
        if spec not in ("SAV", "AS", "IG"):
            return make_error_response(
                ctx,
                f"Unknown specification '{spec}'. Use 'SAV', 'AS', or 'IG'.",
                error_fixes=["Choose one of: SAV, AS, IG."],
            )

        y = clean.copy()

        # Initial quantile estimate (empirical)
        q0 = float(np.quantile(y, theta))

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])

        progress_callback(f"Estimating CAViaR ({spec}) model", 20)

        best_loss = np.inf
        best_params = None

        for restart in range(cfg["n_restarts"]):
            pct = 20 + int(55 * restart / cfg["n_restarts"])
            progress_callback(f"Optimization restart {restart + 1}/{cfg['n_restarts']}", pct)

            params0 = _get_initial_params(spec, y, theta, q0)

            try:
                res = minimize(
                    _quantile_loss,
                    params0,
                    args=(y, theta, spec, q0),
                    method="Nelder-Mead",
                    options={"maxiter": cfg["maxiter"], "xatol": 1e-8, "fatol": 1e-10},
                )
                if res.fun < best_loss and np.isfinite(res.fun):
                    best_loss = res.fun
                    best_params = res.x
            except Exception:
                continue

        if best_params is None:
            return make_error_response(
                ctx,
                "CAViaR optimization failed to converge on all restarts.",
                error_fixes=[
                    "Try the 'Thorough' preset for more restarts.",
                    "Check for extreme outliers in the series.",
                    "Try a different specification (SAV, AS, IG).",
                ],
            )

        progress_callback("Computing dynamic quantiles", 80)

        # Generate the quantile path
        q_path = _compute_quantile_path(best_params, y, spec, q0)

        # Exceedance analysis
        violations = y < q_path  # VaR violations (left tail)
        n_violations = int(violations.sum())
        expected_violations = n * theta
        violation_ratio = n_violations / (n * theta) if n * theta > 0 else np.inf

        # Kupiec unconditional coverage test
        kupiec_stat, kupiec_pval = _kupiec_test(n, n_violations, theta)

        # Christoffersen independence test
        cc_stat, cc_pval = _christoffersen_test(violations, theta)

        # Dynamic Quantile (DQ) test - Engle & Manganelli
        dq_stat, dq_pval = _dq_test(y, q_path, violations, theta)

        progress_callback("Building output", 90)

        # Parameter names
        if spec == "SAV":
            pnames = ["beta_0", "beta_1", "beta_2"]
        elif spec == "AS":
            pnames = ["beta_0", "beta_1", "beta_2 (positive)", "beta_3 (negative)"]
        else:  # IG
            pnames = ["beta_0", "beta_1", "beta_2"]

        # Parameters table
        param_rows = []
        for i, pn in enumerate(pnames):
            param_rows.append([pn, round(float(best_params[i]), 6)])
        param_rows.append(["Quantile loss", round(float(best_loss), 6)])
        param_rows.append(["theta (quantile level)", theta])
        param_rows.append(["Specification", spec])
        param_table = make_table("CAViaR Parameters", ["Parameter", "Value"], param_rows)

        # Backtesting table
        bt_rows = [
            ["N observations", n],
            ["N violations", n_violations],
            ["Expected violations", round(expected_violations, 1)],
            ["Violation ratio", round(violation_ratio, 4)],
            ["Kupiec LR stat", round(float(kupiec_stat), 4)],
            ["Kupiec p-value", round(float(kupiec_pval), 6)],
            ["Christoffersen stat", round(float(cc_stat), 4)],
            ["Christoffersen p-value", round(float(cc_pval), 6)],
            ["DQ stat", round(float(dq_stat), 4)],
            ["DQ p-value", round(float(dq_pval), 6)],
        ]
        bt_table = make_table("VaR Backtesting", ["Metric", "Value"], bt_rows)

        # Time series table
        time_col = ctx.time if ctx.time and len(ctx.time) == n else list(range(1, n + 1))
        max_display = 500
        step = max(1, n // max_display)
        ts_rows = []
        for i in range(0, n, step):
            ts_rows.append([
                time_col[i],
                round(float(y[i]), 6),
                round(float(q_path[i]), 6),
                "Yes" if violations[i] else "No",
            ])

        ts_table = make_table(
            "Dynamic Quantile Path",
            ["Time", "Return", f"q_{theta:.2f}", "Violation"],
            ts_rows,
        )

        # Plain English summary
        if violation_ratio < 0.8:
            coverage_desc = "too conservative (fewer violations than expected)"
        elif violation_ratio > 1.2:
            coverage_desc = "too aggressive (more violations than expected)"
        else:
            coverage_desc = "well-calibrated"

        test_pass = kupiec_pval > 0.05 and cc_pval > 0.05
        backtest_desc = "passes" if test_pass else "fails"

        plain_english = (
            f"CAViaR {spec} model estimated on '{name}' ({n} observations) "
            f"for the {theta*100:.1f}% quantile (VaR). "
            f"The model is {coverage_desc} with {n_violations} violations "
            f"(expected {expected_violations:.0f}, ratio {violation_ratio:.2f}). "
            f"The model {backtest_desc} backtesting at 5% significance "
            f"(Kupiec p={kupiec_pval:.4f}, Christoffersen p={cc_pval:.4f})."
        )

        if kupiec_pval <= 0.05:
            warnings.append("Kupiec test rejects correct unconditional coverage.")
        if cc_pval <= 0.05:
            warnings.append("Christoffersen test rejects violation independence.")
        if dq_pval <= 0.05:
            warnings.append("Dynamic Quantile test rejects model adequacy.")

        charting = (
            "Time series chart with the return series as a line and the dynamic quantile "
            f"(q_{theta:.2f}) as a dashed line below it. "
            "Highlight violation points (where return < quantile) with red markers. "
            "Optionally show a histogram of violations over rolling windows."
        )

        progress_callback("Done", 100)

        # ── Interpretation layer (Prompt C6) ──────────────────────────
        # Parameter-name mapping so the spec can cite β-labels without
        # re-deriving the spec-to-name mapping.
        _parameter_names = list(pnames)

        audit = {
            "specification": spec,
            "theta": theta,
            "quantile_theta": theta,  # alias to avoid T14 collision risk
            "parameter_names": _parameter_names,
            "parameters": [round(float(p), 6) for p in best_params],
            "quantile_loss": round(float(best_loss), 6),
            "n_violations": n_violations,
            "expected_violations": round(expected_violations, 2),
            "violation_ratio": round(violation_ratio, 4),
            "kupiec_stat": round(float(kupiec_stat), 4),
            "kupiec_pval": round(float(kupiec_pval), 6),
            "christoffersen_stat": round(float(cc_stat), 4),
            "christoffersen_pval": round(float(cc_pval), 6),
            "dq_stat": round(float(dq_stat), 4),
            "dq_pval": round(float(dq_pval), 6),
            "n_obs": n,
            "n_restarts": cfg["n_restarts"],
            "distribution_free": True,
            "series_name": name,
            **format_significance_disclosure(
                test_name=(
                    "Kupiec unconditional coverage + Christoffersen "
                    "conditional coverage + Engle-Manganelli Dynamic "
                    "Quantile backtests"
                ),
                critical_value_formula=(
                    "chi-squared p-values from likelihood-ratio (Kupiec, "
                    "Christoffersen) and dynamic-quantile (DQ) tests"
                ),
                ac_corrected=True,
            ),
        }

        try:
            from interpretation import build_interpretation  # type: ignore
        except Exception:
            def build_interpretation(technique_id, results):  # type: ignore
                return None
        interp = build_interpretation("caviar_quantile_dynamics", dict(audit))

        return make_response(
            ctx,
            tables=[param_table, bt_table, ts_table],
            plain_english_summary=plain_english,
            warnings=warnings,
            charting_suggestions=charting,
            interpretation=interp,
            audit_fields=audit,
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"CAViaR estimation failed: {e}",
            error_fixes=[
                "Ensure the series represents returns.",
                "Try a different specification (SAV, AS, IG).",
                "Try the 'Thorough' preset for more optimization restarts.",
            ],
        )


def _get_initial_params(spec, y, theta, q0):
    """Generate random starting parameters for a given specification."""
    if spec == "SAV":
        beta0 = q0 * (1 - 0.9) * (0.5 + np.random.rand())
        beta1 = 0.85 + 0.1 * np.random.rand()
        beta2 = -0.1 * np.std(y) * (0.5 + np.random.rand())
        return np.array([beta0, beta1, beta2])
    elif spec == "AS":
        beta0 = q0 * (1 - 0.9) * (0.5 + np.random.rand())
        beta1 = 0.85 + 0.1 * np.random.rand()
        beta2 = -0.05 * np.std(y) * (0.5 + np.random.rand())
        beta3 = 0.1 * np.std(y) * (0.5 + np.random.rand())
        return np.array([beta0, beta1, beta2, beta3])
    else:  # IG
        # Note: the previous implementation assigned ``sigma = np.std(y)``
        # here but never used it in the IG initialization (the beta2
        # draw is scale-free). Removed as orphan per Prompt C6 D17.
        beta0 = q0 ** 2 * (1 - 0.9) * (0.5 + np.random.rand())
        beta1 = 0.85 + 0.1 * np.random.rand()
        beta2 = 0.1 * (0.5 + np.random.rand())
        return np.array([beta0, beta1, beta2])


def _compute_quantile_path(params, y, spec, q0):
    """Compute the dynamic quantile path given parameters."""
    n = len(y)
    q = np.zeros(n)
    q[0] = q0

    if spec == "SAV":
        b0, b1, b2 = params
        for t in range(1, n):
            q[t] = b0 + b1 * q[t - 1] + b2 * abs(y[t - 1])
    elif spec == "AS":
        b0, b1, b2, b3 = params
        for t in range(1, n):
            q[t] = b0 + b1 * q[t - 1] + b2 * max(y[t - 1], 0) + b3 * min(y[t - 1], 0)
    else:  # IG
        b0, b1, b2 = params
        for t in range(1, n):
            inside = b0 + b1 * q[t - 1] ** 2 + b2 * y[t - 1] ** 2
            q[t] = -np.sqrt(max(abs(inside), 1e-20))  # negative for left tail quantile

    return q


def _quantile_loss(params, y, theta, spec, q0):
    """Compute the quantile regression loss (tick loss / check function)."""
    q = _compute_quantile_path(params, y, spec, q0)
    residuals = y - q
    loss = np.where(residuals >= 0, theta * residuals, (theta - 1) * residuals)
    return np.mean(loss)


def _kupiec_test(n, v, theta):
    """Kupiec (1995) unconditional coverage LR test."""
    if v == 0 or v == n:
        return 0.0, 1.0

    pi_hat = v / n
    lr = 2 * (v * np.log(pi_hat / theta) + (n - v) * np.log((1 - pi_hat) / (1 - theta)))
    from scipy.stats import chi2
    pval = 1 - chi2.cdf(lr, 1)
    return float(lr), float(pval)


def _christoffersen_test(violations, theta):
    """Christoffersen (1998) conditional-coverage test for violation
    clustering via first-order Markov chain. Prompt C6 D17 label fix:
    this is a conditional-coverage test (hit indicators form a Markov
    chain), not a pure "independence" test — the name was previously
    mislabeled. The Engle-Manganelli Dynamic Quantile test is a
    separate, stronger joint-coverage test that complements this one."""
    from scipy.stats import chi2
    v = violations.astype(int)
    n = len(v)

    # Transition counts
    n00, n01, n10, n11 = 0, 0, 0, 0
    for t in range(1, n):
        if v[t - 1] == 0 and v[t] == 0:
            n00 += 1
        elif v[t - 1] == 0 and v[t] == 1:
            n01 += 1
        elif v[t - 1] == 1 and v[t] == 0:
            n10 += 1
        else:
            n11 += 1

    # Transition probabilities
    pi01 = n01 / (n00 + n01) if (n00 + n01) > 0 else 0.0
    pi11 = n11 / (n10 + n11) if (n10 + n11) > 0 else 0.0
    pi = (n01 + n11) / (n - 1) if n > 1 else 0.0

    if pi01 <= 0 or pi11 <= 0 or pi <= 0 or pi01 >= 1 or pi11 >= 1 or pi >= 1:
        return 0.0, 1.0

    # LR independence
    lr_ind = 2 * (
        n00 * np.log(1 - pi01) + n01 * np.log(pi01) +
        n10 * np.log(1 - pi11) + n11 * np.log(pi11) -
        (n00 + n10) * np.log(1 - pi) - (n01 + n11) * np.log(pi)
    )

    if not np.isfinite(lr_ind) or lr_ind < 0:
        return 0.0, 1.0

    pval = 1 - chi2.cdf(lr_ind, 1)
    return float(lr_ind), float(pval)


def _dq_test(y, q, violations, theta, n_lags=4):
    """
    Engle & Manganelli Dynamic Quantile test.
    Regress hit indicator on lagged hits and current quantile.
    """
    from scipy.stats import chi2

    hit = violations.astype(float) - theta
    n = len(hit)

    if n <= n_lags + 2:
        return 0.0, 1.0

    # Build regressor matrix
    start = n_lags
    T = n - start
    Z = np.zeros((T, n_lags + 2))  # lags of hit + constant + quantile
    Z[:, 0] = 1.0  # constant
    for lag in range(1, n_lags + 1):
        Z[:, lag] = hit[start - lag:n - lag]
    Z[:, n_lags + 1] = q[start:n]

    hit_dep = hit[start:n]

    try:
        ZtZ_inv = np.linalg.inv(Z.T @ Z)
        DQ = hit_dep @ Z @ ZtZ_inv @ Z.T @ hit_dep / (theta * (1 - theta))
        k = Z.shape[1]
        pval = 1 - chi2.cdf(DQ, k)
        return float(DQ), float(pval)
    except np.linalg.LinAlgError:
        return 0.0, 1.0
