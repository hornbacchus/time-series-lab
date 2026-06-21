"""
STL + Generalized ESD anomaly detection for Time Series Lab.

Two-stage anomaly detection:
1. STL decomposition to separate trend, seasonal, and remainder components.
2. Generalized Extreme Studentized Deviate (ESD) test on the remainder
   to identify anomalous observations.

The STL step removes expected patterns so that the ESD test can focus on
genuine anomalies in the residuals. This approach is similar to Twitter's
anomaly detection algorithm.
"""

import numpy as np

try:
    from interpretation import build_interpretation  # type: ignore
except Exception:
    def build_interpretation(technique_id, results):  # type: ignore
        return None
from scipy import stats as sp_stats

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    format_significance_disclosure,
)

_PRESET_CONFIG = {
    "Fast":     {"stl_robust": False, "inner_iter": 2, "outer_iter": 0},
    "Balanced": {"stl_robust": True,  "inner_iter": 5, "outer_iter": 2},
    "Thorough": {"stl_robust": True,  "inner_iter": 10, "outer_iter": 5},
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Detect anomalies using STL decomposition + Generalized ESD test.

    Parameters (via ctx.params)
    ---------------------------
    period : int, optional
        Seasonal period. Auto-inferred from frequency if omitted.
    max_anomalies_pct : float, optional
        Maximum percentage of observations that can be anomalies (default 0.10 = 10%).
    alpha : float, optional
        Significance level for the ESD test (default 0.05).
    direction : str, optional
        Which direction to test: 'both' (default), 'upper', 'lower'.
    """
    try:
        progress_callback("Validating inputs", 5)
        np.random.seed(ctx.seed)

        name, values = ctx.get_primary_series()
        warnings = []

        n = len(values)

        # Handle NaN for STL
        nan_mask = np.isnan(values)
        nan_count = int(nan_mask.sum())
        if nan_count > 0:
            if nan_count > n * 0.3:
                return make_error_response(
                    ctx,
                    f"Too many missing values ({nan_count}/{n} = {100*nan_count/n:.0f}%). "
                    "STL+ESD needs at least 70% valid observations.",
                    error_fixes=["Fill or remove missing values first."],
                )
            filled = values.copy()
            nans = np.where(nan_mask)[0]
            valid = np.where(~nan_mask)[0]
            filled[nans] = np.interp(nans, valid, values[valid])
            warnings.append(f"{nan_count} missing values linearly interpolated for STL.")
        else:
            filled = values.copy()

        # Infer period
        period = ctx.get_param("period")
        if period is not None:
            period = int(period)
        else:
            period = _infer_period(ctx.frequency)
            if period is None:
                return make_error_response(
                    ctx,
                    "Cannot infer seasonal period from frequency. Please supply 'period' parameter.",
                    error_fixes=[
                        "Set period=12 for monthly data with yearly seasonality.",
                        "Set period=7 for daily data with weekly seasonality.",
                    ],
                )

        if n < 2 * period + 1:
            return make_error_response(
                ctx,
                f"Series length ({n}) must be at least 2*period+1 ({2*period+1}) for STL decomposition.",
                error_fixes=["Provide a longer series or reduce the period."],
            )

        max_anomalies_pct = float(ctx.get_param("max_anomalies_pct", 0.10))
        alpha = float(ctx.get_param("alpha", 0.05))
        direction = ctx.get_param("direction", "both").lower()
        # CAI Phase 2 Session 15 fix (F-CP-STL-DIRECTION): explicit
        # allowlist gate. Pre-fix, invalid `direction` strings
        # fell through the if/elif/else chain in
        # _generalized_esd to the `else:  # lower` branch
        # silently. audit_fields["direction"] still reported the
        # user's invalid string, misrepresenting the test that
        # actually ran.
        _DIRECTION_OPTS = ("both", "upper", "lower")
        if direction not in _DIRECTION_OPTS:
            return make_error_response(
                ctx,
                f"Unknown direction '{direction}'. Must be one "
                f"of: {', '.join(_DIRECTION_OPTS)}.",
                error_fixes=[
                    "Use 'both' (default; two-sided test "
                    "detecting both upper and lower anomalies), "
                    "'upper' (one-sided; flags only unusually "
                    "high values), or 'lower' (one-sided; flags "
                    "only unusually low values).",
                ],
            )

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])

        progress_callback("Running STL decomposition", 20)

        # STL decomposition
        try:
            from statsmodels.tsa.seasonal import STL

            seasonal_window = max(7, period + (1 if period % 2 == 0 else 2))
            stl = STL(
                filled,
                period=period,
                seasonal=seasonal_window,
                robust=cfg["stl_robust"],
            )
            result = stl.fit(
                inner_iter=cfg["inner_iter"],
                outer_iter=cfg["outer_iter"],
            )
            trend = result.trend
            seasonal = result.seasonal
            remainder = result.resid
        except Exception as stl_err:
            return make_error_response(
                ctx,
                f"STL decomposition failed: {stl_err}",
                error_fixes=[
                    "Check that the period is correct for your data.",
                    "Ensure sufficient data length.",
                ],
            )

        progress_callback("Running Generalized ESD test on remainder", 50)

        # Generalized ESD test on the remainder
        max_anomalies = max(1, int(n * max_anomalies_pct))

        # Use only non-NaN positions for the ESD test
        if nan_count > 0:
            test_indices = np.where(~nan_mask)[0]
            remainder_test = remainder[test_indices]
        else:
            test_indices = np.arange(n)
            remainder_test = remainder.copy()

        n_test = len(remainder_test)
        max_anomalies = min(max_anomalies, n_test // 2)

        anomaly_indices, esd_results = _generalized_esd(
            remainder_test, max_anomalies, alpha, direction
        )

        # Map back to original indices
        anomaly_original_indices = test_indices[anomaly_indices] if len(anomaly_indices) > 0 else []
        n_anomalies = len(anomaly_original_indices)

        progress_callback("Computing anomaly scores", 70)

        # Compute anomaly scores (absolute deviation from median / MAD)
        median_r = float(np.median(remainder_test))
        mad = float(np.median(np.abs(remainder_test - median_r)))
        if mad < 1e-10:
            mad = float(np.std(remainder_test))
        if mad < 1e-10:
            mad = 1.0

        anomaly_scores = np.abs(remainder - median_r) / mad

        progress_callback("Building output", 85)

        time_col = ctx.time if ctx.time and len(ctx.time) == n else list(range(1, n + 1))

        # Anomalies table
        anomaly_rows = []
        anomaly_set = set(anomaly_original_indices.tolist()) if len(anomaly_original_indices) > 0 else set()
        for idx in sorted(anomaly_set):
            t_label = time_col[idx]
            anomaly_rows.append([
                t_label,
                idx,
                round(float(values[idx]), 6) if not np.isnan(values[idx]) else None,
                round(float(remainder[idx]), 6),
                round(float(anomaly_scores[idx]), 4),
                "Upper" if remainder[idx] > median_r else "Lower",
            ])

        anomaly_table = make_table(
            "Detected Anomalies",
            ["Time", "Index", "Value", "Remainder", "Anomaly Score (MAD)", "Direction"],
            anomaly_rows,
        )

        # ESD test results table
        esd_rows = []
        for i, (test_stat, critical_val, is_anomaly) in enumerate(esd_results):
            esd_rows.append([
                i + 1,
                round(test_stat, 6),
                round(critical_val, 6),
                "Yes" if is_anomaly else "No",
            ])
        esd_table = make_table(
            "Generalized ESD Test Results",
            ["Iteration", "Test Statistic", "Critical Value", "Anomaly?"],
            esd_rows,
        )

        # Decomposition + anomaly time series
        max_display = 500
        step_ts = max(1, n // max_display)
        ts_rows = []
        for i in range(0, n, step_ts):
            is_anom = "Yes" if i in anomaly_set else "No"
            ts_rows.append([
                time_col[i],
                round(float(filled[i]), 6),
                round(float(trend[i]), 6),
                round(float(seasonal[i]), 6),
                round(float(remainder[i]), 6),
                round(float(anomaly_scores[i]), 4),
                is_anom,
            ])

        ts_table = make_table(
            "Decomposition & Anomaly Scores",
            ["Time", "Value", "Trend", "Seasonal", "Remainder", "Anomaly Score", "Is Anomaly"],
            ts_rows,
        )

        # Summary table
        summary_rows = [
            ["Series", name],
            ["Observations", n],
            ["Period", period],
            ["Anomalies detected", n_anomalies],
            ["Anomaly rate", f"{100*n_anomalies/n:.2f}%"],
            ["Max anomalies tested", max_anomalies],
            ["Alpha (significance)", alpha],
            ["Direction", direction],
            ["Median remainder", round(median_r, 6)],
            ["MAD of remainder", round(mad, 6)],
            ["STL robust", cfg["stl_robust"]],
        ]
        summary_table = make_table("Summary", ["Metric", "Value"], summary_rows)

        # Plain English
        if n_anomalies == 0:
            plain_english = (
                f"STL+ESD anomaly detection on '{name}' ({n} observations, period={period}). "
                f"No anomalies detected at {alpha*100:.0f}% significance level. "
                "The series residuals are consistent with normal variation after removing "
                "trend and seasonal components."
            )
        else:
            # Characterize anomalies
            upper_count = sum(1 for idx in anomaly_set if remainder[idx] > median_r)
            lower_count = n_anomalies - upper_count

            plain_english = (
                f"STL+ESD anomaly detection on '{name}' ({n} observations, period={period}). "
                f"Detected {n_anomalies} anomaly/anomalies ({100*n_anomalies/n:.1f}% of data): "
                f"{upper_count} upper (unusually high), {lower_count} lower (unusually low). "
            )

            # Most extreme anomaly
            if len(anomaly_original_indices) > 0:
                max_score_idx = anomaly_original_indices[
                    np.argmax(anomaly_scores[anomaly_original_indices])
                ]
                t_label = time_col[max_score_idx]
                plain_english += (
                    f"Most extreme anomaly at {t_label} "
                    f"(value={values[max_score_idx]:.4f}, score={anomaly_scores[max_score_idx]:.2f} MADs)."
                )

        charting = (
            "Four-panel stacked chart: (1) Original series with anomaly points highlighted in red, "
            "(2) Trend component, (3) Seasonal component, "
            "(4) Remainder with anomaly threshold lines and anomaly points marked. "
            "Use filled red circles for anomalies."
        )

        progress_callback("Done", 100)

        # Count anomalies by direction and find most extreme.
        _n_up = sum(1 for r in anomaly_rows if r[5] == "Upper")
        _n_down = sum(1 for r in anomaly_rows if r[5] == "Lower")
        _most_extreme_date = None
        _most_extreme_z = None
        if anomaly_rows:
            _sorted_by_score = sorted(
                anomaly_rows, key=lambda r: r[4] if r[4] is not None else 0,
                reverse=True,
            )
            _most_extreme_date = _sorted_by_score[0][0]
            _most_extreme_z = _sorted_by_score[0][4]
        interp = build_interpretation("stl_esd_anomaly", {
            "series_name": name,
            "n_obs": int(n),
            "n_anomalies": int(n_anomalies),
            "alpha": float(alpha),
            "n_anomalies_upward": int(_n_up),
            "n_anomalies_downward": int(_n_down),
            "most_extreme_date": _most_extreme_date,
            "most_extreme_z_score": _most_extreme_z,
            "max_anomalies": int(max_anomalies),
        })
        return make_response(
            ctx,
            tables=[anomaly_table, summary_table, esd_table, ts_table],
            plain_english_summary=plain_english,
            warnings=warnings,
            charting_suggestions=charting,
            interpretation=interp,
            audit_fields={
                "period": period,
                "alpha": alpha,
                "direction": direction,
                "max_anomalies_pct": max_anomalies_pct,
                "max_anomalies": int(max_anomalies),
                "n_anomalies": n_anomalies,
                "anomaly_rate": round(n_anomalies / n, 6),
                "median_remainder": round(median_r, 6),
                "mad_remainder": round(mad, 6),
                "stl_robust": cfg["stl_robust"],
                "n_obs": n,
                "anomaly_indices": [int(i) for i in anomaly_original_indices] if n_anomalies > 0 else [],
                **format_significance_disclosure(
                    test_name=(
                        "Generalized ESD test on STL remainder (Rosner 1983)"
                    ),
                    critical_value_formula=(
                        "λ_i = (n-i-1)·t_crit / sqrt((n-i-2+t_crit²)(n-i)) "
                        "with t_crit = t.ppf(1 - α/(2(n-i)), n-i-2). "
                        "Bonferroni-adjusted DoF; NOT AC-aware — assumes STL "
                        "remainder is iid. Residual autocorrelation inflates "
                        "false-positive rate."
                    ),
                    ac_corrected=False,
                ),
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"STL+ESD anomaly detection failed: {e}",
            error_fixes=[
                "Ensure the series is numeric.",
                "Check the period parameter.",
                "Try reducing max_anomalies_pct if the test is too slow.",
            ],
        )


def _generalized_esd(data, max_k, alpha, direction):
    """
    Generalized Extreme Studentized Deviate (ESD) test.

    Tests for up to max_k outliers simultaneously. Returns the indices
    of detected outliers and the test statistics/critical values for each iteration.

    Parameters
    ----------
    data : ndarray
        The data to test (typically STL residuals).
    max_k : int
        Maximum number of outliers to test for.
    alpha : float
        Significance level.
    direction : str
        'both', 'upper', or 'lower'.

    Returns
    -------
    anomaly_indices : ndarray
        Indices of detected anomalies in the original data array.
    esd_results : list of (test_stat, critical_value, is_anomaly)
    """
    n = len(data)
    residuals = data.copy()
    original_indices = np.arange(n)
    removed_indices = []
    esd_results = []

    for i in range(max_k):
        n_current = len(residuals)
        if n_current < 3:
            break

        mean_r = np.mean(residuals)
        std_r = np.std(residuals, ddof=1)

        if std_r < 1e-10:
            break

        if direction == "both":
            deviations = np.abs(residuals - mean_r)
        elif direction == "upper":
            deviations = residuals - mean_r
        else:  # lower
            deviations = mean_r - residuals

        max_idx = np.argmax(deviations)
        test_stat = deviations[max_idx] / std_r

        # Critical value from t-distribution
        p = 1 - alpha / (2 * (n_current - i))
        t_crit = sp_stats.t.ppf(p, df=n_current - i - 2)
        critical_value = (
            (n_current - i - 1) * t_crit /
            np.sqrt((n_current - i - 2 + t_crit ** 2) * (n_current - i))
        )

        is_anomaly = test_stat > critical_value

        esd_results.append((float(test_stat), float(critical_value), is_anomaly))

        # Remove the most extreme point and continue
        removed_indices.append(original_indices[max_idx])
        residuals = np.delete(residuals, max_idx)
        original_indices = np.delete(original_indices, max_idx)

    # Determine the number of actual anomalies:
    # Find the largest i where test_stat > critical_value for all j <= i
    n_anomalies = 0
    for i, (ts, cv, ia) in enumerate(esd_results):
        if ia:
            n_anomalies = i + 1
        else:
            break

    anomaly_indices = np.array(removed_indices[:n_anomalies], dtype=int) if n_anomalies > 0 else np.array([], dtype=int)

    return anomaly_indices, esd_results


def _infer_period(frequency):
    """Infer seasonal period from frequency string."""
    if not frequency:
        return None

    freq_map = {
        "D": 7, "B": 5, "W": 52, "M": 12, "MS": 12,
        "Q": 4, "QS": 4, "H": 24, "T": 60, "min": 60, "S": 60,
    }

    freq = frequency.strip().upper()
    if freq in freq_map:
        return freq_map[freq]

    freq_lower = frequency.strip()
    if freq_lower in freq_map:
        return freq_map[freq_lower]

    return None
