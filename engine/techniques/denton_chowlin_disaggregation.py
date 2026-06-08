"""
Denton and Chow-Lin Temporal Disaggregation for Time Series Lab.

Converts a low-frequency time series (e.g., quarterly) to a higher frequency
(e.g., monthly) while preserving temporal aggregation constraints.

Implements:
- Denton (proportional first differences) method
- Chow-Lin (GLS regression-based) method

Both implemented from scratch with numpy/scipy.
"""

import numpy as np
from scipy import linalg, optimize

try:
    from interpretation import build_interpretation  # type: ignore
except Exception:
    def build_interpretation(technique_id, results):  # type: ignore
        return None

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


def _build_aggregation_matrix(n_high, conversion_ratio):
    """
    Build the aggregation matrix C such that C @ y_high = y_low.
    C is (n_low x n_high) with blocks of ones of size conversion_ratio.
    """
    n_low = n_high // conversion_ratio
    C = np.zeros((n_low, n_high))
    for i in range(n_low):
        start = i * conversion_ratio
        end = start + conversion_ratio
        C[i, start:end] = 1.0
    return C


def _denton_proportional(y_low, z_high, conversion_ratio):
    """
    Denton proportional first differences (PFD) method.

    y_low: (n_low,) array of low-frequency values
    z_high: (n_high,) array of high-frequency indicator or preliminary values.
            If None, uses a uniform distribution.
    conversion_ratio: e.g., 3 for quarterly -> monthly

    Returns: (n_high,) disaggregated high-frequency series
    """
    n_low = len(y_low)
    n_high = n_low * conversion_ratio

    if z_high is None:
        # Without indicator, use uniform initial distribution
        z_high = np.ones(n_high)
        for i in range(n_low):
            start = i * conversion_ratio
            end = start + conversion_ratio
            z_high[start:end] = y_low[i] / conversion_ratio

    z_high = z_high[:n_high]
    if len(z_high) < n_high:
        # Pad with last value if needed
        z_high = np.concatenate([z_high, np.full(n_high - len(z_high), z_high[-1])])

    C = _build_aggregation_matrix(n_high, conversion_ratio)

    # Build D matrix for first differences: D(i) = x(i)/z(i) - x(i-1)/z(i-1)
    # Minimize sum of squared proportional first differences
    # subject to C @ x = y_low

    # For the proportional Denton method:
    # min (x/z - shift(x/z))' (x/z - shift(x/z))
    # s.t. C @ x = y_low
    # This is solved via a linear system.

    # Build diagonal matrix of 1/z
    z_safe = np.where(np.abs(z_high) < 1e-10, 1.0, z_high)
    D_inv_z = np.diag(1.0 / z_safe)

    # First-difference matrix (n_high-1 x n_high)
    D1 = np.zeros((n_high - 1, n_high))
    for i in range(n_high - 1):
        D1[i, i] = -1.0
        D1[i, i + 1] = 1.0

    # H = D1 @ D_inv_z, then minimize ||H @ x||^2 s.t. C @ x = y_low
    H = D1 @ D_inv_z
    HtH = H.T @ H

    # Add small regularization for numerical stability
    HtH += np.eye(n_high) * 1e-10

    # Solve via KKT system:
    # [HtH  C'] [x    ]   [0    ]
    # [C    0 ] [lambda] = [y_low]
    n_total = n_high + n_low
    KKT = np.zeros((n_total, n_total))
    KKT[:n_high, :n_high] = HtH
    KKT[:n_high, n_high:] = C.T
    KKT[n_high:, :n_high] = C
    rhs = np.zeros(n_total)
    rhs[n_high:] = y_low

    try:
        solution = linalg.solve(KKT, rhs)
    except linalg.LinAlgError:
        solution = np.linalg.lstsq(KKT, rhs, rcond=None)[0]

    x_high = solution[:n_high]
    return x_high


def _chowlin(y_low, z_high, conversion_ratio, rho=0.5):
    """
    Chow-Lin temporal disaggregation using GLS regression.

    y_low: (n_low,) low-frequency series
    z_high: (n_high,) high-frequency indicator. If None, uses time trend.
    conversion_ratio: e.g., 3 for quarterly -> monthly
    rho: AR(1) parameter for residual autocorrelation. Default 0.5.

    Returns: (n_high,) disaggregated series, regression_info dict
    """
    n_low = len(y_low)
    n_high = n_low * conversion_ratio

    # Build indicator matrix (with intercept and trend)
    if z_high is not None:
        z_high = z_high[:n_high]
        if len(z_high) < n_high:
            z_high = np.concatenate([z_high, np.full(n_high - len(z_high), z_high[-1])])
        X_high = np.column_stack([np.ones(n_high), np.arange(1, n_high + 1, dtype=float), z_high])
    else:
        X_high = np.column_stack([np.ones(n_high), np.arange(1, n_high + 1, dtype=float)])

    C = _build_aggregation_matrix(n_high, conversion_ratio)

    # Aggregate X to low frequency
    X_low = C @ X_high

    # Build AR(1) covariance matrix for high-frequency residuals
    V_high = np.zeros((n_high, n_high))
    for i in range(n_high):
        for j in range(n_high):
            V_high[i, j] = rho ** abs(i - j)
    V_high /= (1.0 - rho ** 2)

    # Low-frequency covariance: V_low = C @ V_high @ C'
    V_low = C @ V_high @ C.T

    # GLS estimate of beta
    try:
        V_low_inv = linalg.inv(V_low)
    except linalg.LinAlgError:
        V_low_inv = np.linalg.pinv(V_low)

    XtVinvX = X_low.T @ V_low_inv @ X_low
    XtVinvy = X_low.T @ V_low_inv @ y_low
    try:
        beta = linalg.solve(XtVinvX, XtVinvy)
    except linalg.LinAlgError:
        beta = np.linalg.lstsq(XtVinvX, XtVinvy, rcond=None)[0]

    # Low-frequency residuals
    u_low = y_low - X_low @ beta

    # Distribution matrix: L = V_high @ C' @ V_low_inv
    L = V_high @ C.T @ V_low_inv

    # High-frequency series: y_high = X_high @ beta + L @ u_low
    x_high = X_high @ beta + L @ u_low

    info = {
        "beta": beta.tolist(),
        "rho": rho,
        "n_predictors": X_high.shape[1],
    }
    return x_high, info


def _estimate_rho(y_low, z_high, conversion_ratio):
    """
    Estimate optimal rho by maximizing the CONCENTRATED (profiled-sigma^2)
    Chow-Lin log-likelihood via continuous optimization.

    Replaces the prior 20/50-point grid maxlog. The grid maximized an
    UNPROFILED (sigma^2 = 1) objective ``-0.5*(logdet(V_low) + u'V_low^-1 u)``
    whose argmax differs from the profiled-sigma^2 concentrated likelihood
    that the canonical Chow-Lin maxlog (e.g. R ``tempdisagg::td``
    "chow-lin-maxlog") maximizes — because the ``1/(1-rho^2)`` AR(1) scale
    cancels in the profiled objective but NOT in the sigma^2=1 form. So the
    grid landed ~0.14 off the continuous-ML optimum: an OBJECTIVE mismatch,
    NOT a grid-resolution issue (the grid already nearly converged to its own,
    wrong, optimum). This profiles sigma^2 out and optimizes continuously over
    rho in [0, 0.999] (``truncated.rho = 0``), reproducing the canonical
    continuous-ML rho. The GLS distribution solve (``_chowlin``) is unchanged;
    only rho-SELECTION changed (fixed-rho paths are unaffected).
    """
    n_low = len(y_low)
    n_high = n_low * conversion_ratio

    if z_high is not None:
        z_h = z_high[:n_high]
        if len(z_h) < n_high:
            z_h = np.concatenate([z_h, np.full(n_high - len(z_h), z_h[-1])])
        X_high = np.column_stack([np.ones(n_high), np.arange(1, n_high + 1, dtype=float), z_h])
    else:
        X_high = np.column_stack([np.ones(n_high), np.arange(1, n_high + 1, dtype=float)])

    C = _build_aggregation_matrix(n_high, conversion_ratio)
    X_low = C @ X_high

    def _neg_concentrated_ll(rho):
        # Profiled-sigma^2 concentrated negative log-likelihood (up to const).
        V_high = np.zeros((n_high, n_high))
        for i in range(n_high):
            for j in range(n_high):
                V_high[i, j] = rho ** abs(i - j)
        V_high /= (1.0 - rho ** 2)
        V_low = C @ V_high @ C.T
        try:
            V_low_inv = linalg.inv(V_low)
            XtVinvX = X_low.T @ V_low_inv @ X_low
            beta = linalg.solve(XtVinvX, X_low.T @ V_low_inv @ y_low)
        except linalg.LinAlgError:
            return np.inf
        u_low = y_low - X_low @ beta
        sign, logdet = np.linalg.slogdet(V_low)
        quad = float(u_low.T @ V_low_inv @ u_low)
        if sign <= 0 or quad <= 0:
            return np.inf
        return 0.5 * (n_low * np.log(quad / n_low) + logdet)

    try:
        res = optimize.minimize_scalar(
            _neg_concentrated_ll, bounds=(0.0, 0.999), method="bounded",
        )
        if np.isfinite(res.fun):
            return float(res.x)
    except Exception:
        pass
    return 0.5


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Temporal disaggregation using Denton or Chow-Lin methods.

    Parameters (via ctx.params)
    ---------------------------
    method : str
        "denton" or "chowlin". Default "chowlin".
    conversion_ratio : int
        Ratio of high-frequency to low-frequency (e.g., 3 for Q->M). Default 3.
    rho : float or "auto", optional
        AR(1) parameter for Chow-Lin. Default "auto" (ML estimation).
    """
    try:
        progress_callback("Validating inputs", 5)
        np.random.seed(ctx.seed)

        series_list = ctx.get_all_series()
        if len(series_list) < 1:
            return make_error_response(
                ctx,
                "At least one series required (the low-frequency series to disaggregate).",
            )

        lo_name, lo_values = series_list[0]
        warn_list = []

        # Clean low-frequency series
        lo_nan_mask = np.isnan(lo_values)
        if lo_nan_mask.any():
            lo_clean = lo_values[~lo_nan_mask]
            warn_list.append(f"{int(lo_nan_mask.sum())} NaN values removed from low-frequency series.")
        else:
            lo_clean = lo_values.copy()

        n_low = len(lo_clean)
        if n_low < 4:
            return make_error_response(
                ctx,
                f"Low-frequency series has only {n_low} observations. Need at least 4.",
                error_fixes=["Provide a longer series."],
            )

        method = ctx.get_param("method", "chowlin").lower()
        # CAI Phase 2 Session 19 fix (F-MD-DENTON-METHOD): explicit
        # allowlist gate. Pre-fix, invalid `method` was silently
        # coerced to 'chowlin' with warning; now rejects explicitly.
        _METHOD_OPTS = ("denton", "chowlin")
        if method not in _METHOD_OPTS:
            return make_error_response(
                ctx,
                f"Unknown method '{method}'. Must be one of: "
                f"{', '.join(_METHOD_OPTS)}.",
                error_fixes=[
                    "Use 'denton' (Denton proportional first "
                    "differences; preserves indicator shape; "
                    "non-negative output) or 'chowlin' (default; "
                    "Chow-Lin GLS regression-based; uses indicator "
                    "as regressor with AR(1) residuals).",
                ],
            )

        conversion_ratio = int(ctx.get_param("conversion_ratio", 3))
        # CAI Phase 2 Session 19 fix (F-MD-DENTON-CONVRATIO):
        # explicit range gate. Pre-fix, conversion_ratio < 2 was
        # silently reset to 3.
        if conversion_ratio < 2:
            return make_error_response(
                ctx,
                f"conversion_ratio must be >= 2. Got {conversion_ratio}.",
                error_fixes=[
                    "Use conversion_ratio=3 for quarterly-to-monthly, "
                    "conversion_ratio=4 for annual-to-quarterly, "
                    "conversion_ratio=12 for annual-to-monthly.",
                ],
            )

        n_high = n_low * conversion_ratio

        # High-frequency indicator (optional second series)
        z_high = None
        z_name = None
        if len(series_list) >= 2:
            z_name, z_values = series_list[1]
            z_clean = z_values[~np.isnan(z_values)]
            if len(z_clean) >= n_high:
                z_high = z_clean[:n_high]
            else:
                warn_list.append(
                    f"High-frequency indicator '{z_name}' has {len(z_clean)} values, "
                    f"but {n_high} are needed. Using time trend instead."
                )

        progress_callback(f"Running {method.title()} disaggregation", 25)

        reg_info = {}
        if method == "denton":
            x_high = _denton_proportional(lo_clean, z_high, conversion_ratio)
        else:
            # Chow-Lin
            rho_param = ctx.get_param("rho", "auto")
            if rho_param == "auto" or rho_param is None:
                if ctx.preset == "Fast":
                    rho = 0.5
                    warn_list.append("Fast preset: using rho=0.5 without ML estimation.")
                else:
                    progress_callback("Estimating optimal rho via ML", 35)
                    rho = _estimate_rho(lo_clean, z_high, conversion_ratio)
            else:
                rho = float(rho_param)
                # CAI Phase 2 Session 19 fix (F-MD-DENTON-RHO):
                # explicit range gate. Pre-fix, out-of-range rho
                # was silently reset to 0.5.
                if not (0 < rho < 1):
                    return make_error_response(
                        ctx,
                        f"rho must be in (0, 1). Got {rho}.",
                        error_fixes=[
                            "Use a value in the open interval (0, 1) "
                            "for the AR(1) parameter, or rho='auto' "
                            "to estimate via maximum likelihood.",
                        ],
                    )

            x_high, reg_info = _chowlin(lo_clean, z_high, conversion_ratio, rho=rho)
            reg_info["rho"] = round(rho, 4)

        progress_callback("Validating aggregation constraint", 70)

        # Verify aggregation constraint
        C = _build_aggregation_matrix(n_high, conversion_ratio)
        aggregated_back = C @ x_high
        max_discrepancy = float(np.max(np.abs(aggregated_back - lo_clean)))

        if max_discrepancy > 1e-4:
            warn_list.append(
                f"Aggregation constraint not perfectly satisfied "
                f"(max discrepancy: {max_discrepancy:.6f})."
            )

        progress_callback("Building output", 80)

        # High-frequency output table
        hf_rows = []
        for i in range(n_high):
            lo_period = i // conversion_ratio
            sub_period = (i % conversion_ratio) + 1
            hf_rows.append([
                i + 1,
                lo_period + 1,
                sub_period,
                round(float(x_high[i]), 6),
            ])
        hf_table = make_table(
            "Disaggregated Series",
            ["High-Freq Index", "Low-Freq Period", "Sub-Period", "Value"],
            hf_rows,
        )

        # Aggregation check table
        agg_rows = []
        for i in range(n_low):
            agg_sum = float(aggregated_back[i])
            agg_rows.append([
                i + 1,
                round(float(lo_clean[i]), 6),
                round(agg_sum, 6),
                round(float(agg_sum - lo_clean[i]), 8),
            ])
        agg_table = make_table(
            "Aggregation Check",
            ["Low-Freq Period", "Original", "Re-Aggregated", "Discrepancy"],
            agg_rows,
        )

        # Summary statistics
        diag_rows = [
            ["Method", method.title()],
            ["Conversion Ratio", conversion_ratio],
            ["Low-Frequency Periods", n_low],
            ["High-Frequency Points", n_high],
            ["Indicator Used", z_name if z_high is not None else "None (time trend)"],
            ["Max Aggregation Discrepancy", f"{max_discrepancy:.2e}"],
        ]
        if method == "chowlin" and "rho" in reg_info:
            diag_rows.append(["Estimated rho", reg_info["rho"]])
        if "beta" in reg_info:
            for idx, b in enumerate(reg_info["beta"]):
                label = ["Intercept", "Trend", "Indicator"][idx] if idx < 3 else f"Beta_{idx}"
                diag_rows.append([f"Regression {label}", round(b, 6)])

        diag_table = make_table("Diagnostics", ["Metric", "Value"], diag_rows)

        # Descriptive stats of disaggregated series
        desc_rows = [
            ["Mean", round(float(np.mean(x_high)), 6)],
            ["Std Dev", round(float(np.std(x_high, ddof=1)), 6)],
            ["Min", round(float(np.min(x_high)), 6)],
            ["Max", round(float(np.max(x_high)), 6)],
        ]
        if np.any(lo_clean > 0) and np.any(x_high < 0):
            warn_list.append(
                "Some disaggregated values are negative despite all low-frequency values being positive. "
                "Consider using the Denton method for non-negativity preservation."
            )
        desc_table = make_table("Disaggregated Series Statistics", ["Metric", "Value"], desc_rows)

        indicator_note = (
            f" using '{z_name}' as high-frequency indicator"
            if z_high is not None else " without an external indicator"
        )
        plain_english = (
            f"{method.title()} temporal disaggregation of '{lo_name}' "
            f"from {n_low} low-frequency periods to {n_high} high-frequency points "
            f"(ratio {conversion_ratio}:1){indicator_note}. "
            f"Maximum aggregation discrepancy: {max_discrepancy:.2e}."
        )
        if method == "chowlin" and "rho" in reg_info:
            plain_english += f" Estimated AR(1) parameter rho={reg_info['rho']:.3f}."

        charting = (
            "Line chart with two panels: top panel shows the disaggregated high-frequency series, "
            "bottom panel shows the original low-frequency series as step function or bar chart. "
            "Overlay aggregated-back values to visually verify the constraint. "
            "If an indicator is used, show it as a secondary axis on the top panel."
        )

        progress_callback("Done", 100)

        audit = {
            "method": method,
            "conversion_ratio": conversion_ratio,
            "n_low": n_low,
            "n_high": n_high,
            "indicator": z_name,
            "max_discrepancy": round(max_discrepancy, 8),
        }
        audit.update(reg_info)

        interp = build_interpretation("denton_chowlin_disaggregation", {
            "series_name": lo_name,
            "method": method,
            "ratio": int(conversion_ratio),
            "n_low": int(n_low),
            "n_high": int(n_high),
            "indicator_name": z_name if z_high is not None else None,
            "max_discrepancy": float(max_discrepancy),
            "rho": reg_info.get("rho"),
            "betas": list(reg_info.get("beta") or []),
        })
        return make_response(
            ctx,
            tables=[hf_table, agg_table, diag_table, desc_table],
            plain_english_summary=plain_english,
            warnings=warn_list,
            charting_suggestions=charting,
            interpretation=interp,
            audit_fields=audit,
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Temporal disaggregation failed: {e}",
            error_fixes=[
                "Ensure your low-frequency series is numeric and has at least 4 observations.",
                "If using an indicator, it must have at least n_low * conversion_ratio values.",
                "Try method='denton' if 'chowlin' fails.",
                "Try a different conversion_ratio.",
            ],
        )
