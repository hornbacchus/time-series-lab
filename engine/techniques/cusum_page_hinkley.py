"""
CUSUM and Page-Hinkley change detection tests for Time Series Lab.

Implements two classical sequential change detection methods:

1. CUSUM (Cumulative Sum): Detects shifts in the mean of a process by
   accumulating deviations from a target. When the cumulative sum exceeds
   a threshold, a change is signaled.

2. Page-Hinkley (PH): A variant of CUSUM that detects changes in the mean
   by tracking the minimum of the cumulative deviation and signaling when
   the current deviation exceeds the minimum by a threshold.

Both methods can detect upward and downward shifts.
"""

import numpy as np

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

_PRESET_CONFIG = {
    "Fast":     {"bootstrap_threshold": False, "n_bootstrap": 0},
    "Balanced": {"bootstrap_threshold": True,  "n_bootstrap": 500},
    "Thorough": {"bootstrap_threshold": True,  "n_bootstrap": 2000},
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Run CUSUM and Page-Hinkley change detection tests.

    Parameters (via ctx.params)
    ---------------------------
    target : float, optional
        Target mean. Default: series mean (retrospective CUSUM).
    cusum_k : float, optional
        CUSUM allowance parameter (slack). Default: 0.5 * std(series).
    cusum_h : float, optional
        CUSUM decision threshold. Default: 5 * std(series).
    ph_delta : float, optional
        Page-Hinkley minimum detectable change. Default: 0.005 * std(series).
    ph_lambda : float, optional
        Page-Hinkley threshold. Default: 50.
    significance_level : float, optional
        For bootstrap threshold estimation. Default: 0.05.
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
        if n < 20:
            return make_error_response(
                ctx,
                f"Only {n} valid observations. CUSUM/PH needs at least 20.",
                error_fixes=["Provide a longer series."],
            )

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        sigma = float(np.std(clean, ddof=1))
        mu = float(np.mean(clean))

        if sigma < 1e-10:
            return make_error_response(
                ctx,
                "Series has near-zero variance. Cannot perform change detection.",
                error_fixes=["Ensure the series has variation."],
            )

        target = float(ctx.get_param("target", mu))
        cusum_k = float(ctx.get_param("cusum_k", 0.5 * sigma))
        cusum_h = float(ctx.get_param("cusum_h", 5.0 * sigma))
        ph_delta = float(ctx.get_param("ph_delta", 0.005 * sigma))
        ph_lambda = float(ctx.get_param("ph_lambda", 50.0))
        significance = float(ctx.get_param("significance_level", 0.05))

        progress_callback("Computing CUSUM statistics", 20)

        # ---- CUSUM ----
        # Standardize observations
        z = clean - target

        # Upper CUSUM (detects upward shifts)
        S_up = np.zeros(n)
        # Lower CUSUM (detects downward shifts)
        S_down = np.zeros(n)

        cusum_up_alarms = []
        cusum_down_alarms = []

        for t in range(n):
            S_up[t] = max(0, (S_up[t - 1] if t > 0 else 0) + z[t] - cusum_k)
            S_down[t] = max(0, (S_down[t - 1] if t > 0 else 0) - z[t] - cusum_k)

            if S_up[t] > cusum_h:
                cusum_up_alarms.append(t)
                S_up[t] = 0  # Reset after alarm
            if S_down[t] > cusum_h:
                cusum_down_alarms.append(t)
                S_down[t] = 0  # Reset after alarm

        progress_callback("Computing Page-Hinkley statistics", 45)

        # ---- Page-Hinkley ----
        # Detects increase in mean
        m_t = np.zeros(n)       # cumulative sum of (x_t - mean - delta)
        M_t = np.zeros(n)       # running minimum of m_t
        PH_up = np.zeros(n)     # m_t - M_t

        # Detects decrease in mean
        m_t_down = np.zeros(n)
        M_t_up = np.zeros(n)    # running maximum of m_t_down
        PH_down = np.zeros(n)

        ph_up_alarms = []
        ph_down_alarms = []

        running_mean = 0.0

        for t in range(n):
            running_mean = (running_mean * t + clean[t]) / (t + 1)

            # Upward shift detection
            m_t[t] = (m_t[t - 1] if t > 0 else 0) + (clean[t] - running_mean - ph_delta)
            M_t[t] = min(M_t[t - 1] if t > 0 else m_t[t], m_t[t])
            PH_up[t] = m_t[t] - M_t[t]

            if PH_up[t] > ph_lambda and t > 10:
                ph_up_alarms.append(t)

            # Downward shift detection
            m_t_down[t] = (m_t_down[t - 1] if t > 0 else 0) + (clean[t] - running_mean + ph_delta)
            M_t_up[t] = max(M_t_up[t - 1] if t > 0 else m_t_down[t], m_t_down[t])
            PH_down[t] = M_t_up[t] - m_t_down[t]

            if PH_down[t] > ph_lambda and t > 10:
                ph_down_alarms.append(t)

        progress_callback("Bootstrap threshold estimation", 60)

        # Bootstrap threshold (under null of no change)
        bootstrap_cusum_h = None
        bootstrap_ph_lambda = None

        if cfg["bootstrap_threshold"] and cfg["n_bootstrap"] > 0:
            cusum_maxes = np.zeros(cfg["n_bootstrap"])
            ph_maxes = np.zeros(cfg["n_bootstrap"])

            for b in range(cfg["n_bootstrap"]):
                shuffled = np.random.permutation(clean)
                z_b = shuffled - np.mean(shuffled)

                # CUSUM max
                s_up_b = 0
                max_s = 0
                for t in range(n):
                    s_up_b = max(0, s_up_b + z_b[t] - cusum_k)
                    max_s = max(max_s, s_up_b)
                cusum_maxes[b] = max_s

                # PH max
                m_b = 0
                min_m = 0
                max_ph = 0
                rm = 0
                for t in range(n):
                    rm = (rm * t + shuffled[t]) / (t + 1)
                    m_b += shuffled[t] - rm - ph_delta
                    min_m = min(min_m, m_b)
                    max_ph = max(max_ph, m_b - min_m)
                ph_maxes[b] = max_ph

            bootstrap_cusum_h = float(np.percentile(cusum_maxes, (1 - significance) * 100))
            bootstrap_ph_lambda = float(np.percentile(ph_maxes, (1 - significance) * 100))

        progress_callback("Building output", 85)

        # Consolidate all change points from both methods
        all_cps = set()
        for cp in cusum_up_alarms:
            all_cps.add(("CUSUM-up", cp))
        for cp in cusum_down_alarms:
            all_cps.add(("CUSUM-down", cp))
        for cp in ph_up_alarms:
            all_cps.add(("PH-up", cp))
        for cp in ph_down_alarms:
            all_cps.add(("PH-down", cp))

        all_cps_sorted = sorted(all_cps, key=lambda x: x[1])

        # Change points table
        time_col = ctx.time if ctx.time and len(ctx.time) == len(values) else None
        cp_rows = []
        for method, idx in all_cps_sorted:
            t_label = time_col[idx] if time_col else int(idx + 1)
            # Compute local statistics
            window = min(20, idx, n - idx - 1)
            if window > 0:
                before_mean = float(np.mean(clean[max(0, idx - window):idx]))
                after_mean = float(np.mean(clean[idx:min(n, idx + window)]))
                shift = after_mean - before_mean
            else:
                before_mean = after_mean = shift = None

            cp_rows.append([
                method,
                t_label,
                idx,
                round(before_mean, 4) if before_mean is not None else None,
                round(after_mean, 4) if after_mean is not None else None,
                round(shift, 4) if shift is not None else None,
            ])

        cp_table = make_table(
            "Detected Change Points",
            ["Method", "Time", "Index", "Mean Before", "Mean After", "Shift"],
            cp_rows,
        )

        # Parameters table
        params_rows = [
            ["Target mean", round(target, 6)],
            ["Series std", round(sigma, 6)],
            ["CUSUM k (allowance)", round(cusum_k, 6)],
            ["CUSUM h (threshold)", round(cusum_h, 6)],
            ["PH delta (min change)", round(ph_delta, 6)],
            ["PH lambda (threshold)", round(ph_lambda, 6)],
            ["N observations", n],
            ["CUSUM upward alarms", len(cusum_up_alarms)],
            ["CUSUM downward alarms", len(cusum_down_alarms)],
            ["PH upward alarms", len(ph_up_alarms)],
            ["PH downward alarms", len(ph_down_alarms)],
        ]
        if bootstrap_cusum_h is not None:
            params_rows.append(["Bootstrap CUSUM h (alpha=" + str(significance) + ")",
                                round(bootstrap_cusum_h, 4)])
        if bootstrap_ph_lambda is not None:
            params_rows.append(["Bootstrap PH lambda (alpha=" + str(significance) + ")",
                                round(bootstrap_ph_lambda, 4)])

        params_table = make_table("Parameters & Summary", ["Parameter", "Value"], params_rows)

        # Time series table with statistics
        max_display = 500
        step = max(1, n // max_display)
        ts_rows = []
        for i in range(0, n, step):
            t_label = time_col[i] if time_col else int(i + 1)
            ts_rows.append([
                t_label,
                round(float(clean[i]), 6),
                round(float(S_up[i]), 4),
                round(float(S_down[i]), 4),
                round(float(PH_up[i]), 4),
                round(float(PH_down[i]), 4),
            ])

        ts_table = make_table(
            "CUSUM & Page-Hinkley Statistics",
            ["Time", "Value", "CUSUM Up", "CUSUM Down", "PH Up", "PH Down"],
            ts_rows,
        )

        # Plain English
        n_cusum = len(cusum_up_alarms) + len(cusum_down_alarms)
        n_ph = len(ph_up_alarms) + len(ph_down_alarms)

        plain_english = (
            f"Change detection analysis of '{name}' ({n} observations). "
        )

        if n_cusum == 0 and n_ph == 0:
            plain_english += (
                "Neither CUSUM nor Page-Hinkley detected any significant change points. "
                "The series appears stable."
            )
        else:
            parts = []
            if n_cusum > 0:
                parts.append(
                    f"CUSUM detected {n_cusum} alarm(s) "
                    f"({len(cusum_up_alarms)} upward, {len(cusum_down_alarms)} downward)"
                )
            if n_ph > 0:
                parts.append(
                    f"Page-Hinkley detected {n_ph} alarm(s) "
                    f"({len(ph_up_alarms)} upward, {len(ph_down_alarms)} downward)"
                )
            plain_english += ". ".join(parts) + ". "

            # Find the most significant change
            if cp_rows:
                max_shift_row = max(cp_rows, key=lambda r: abs(r[5]) if r[5] is not None else 0)
                if max_shift_row[5] is not None:
                    plain_english += (
                        f"Largest detected shift: {max_shift_row[5]:.4f} "
                        f"at position {max_shift_row[1]} ({max_shift_row[0]})."
                    )

        if bootstrap_cusum_h is not None:
            adj_cusum_alarms = sum(1 for _, idx in all_cps_sorted
                                   if "CUSUM" in _ and
                                   max(S_up[idx], S_down[idx]) > bootstrap_cusum_h)
            if adj_cusum_alarms < n_cusum:
                warnings.append(
                    f"Using bootstrap threshold ({bootstrap_cusum_h:.2f}), "
                    f"only {adj_cusum_alarms} CUSUM alarms remain significant."
                )

        charting = (
            "Three-panel chart: top panel shows the time series with vertical lines at change points. "
            "Middle panel shows CUSUM statistics (upper and lower) with threshold lines. "
            "Bottom panel shows Page-Hinkley statistics with threshold line."
        )

        progress_callback("Done", 100)

        # Extract most-recent alarm details for the interp spec.
        _most_recent_date = None
        _most_recent_pre = None
        _most_recent_post = None
        _most_recent_method_agreement = False
        if cp_rows:
            _last_row = cp_rows[-1]
            _most_recent_date = _last_row[1]
            # cp_rows columns: [# or method-list, time, idx, method, pre_mean, post_mean, shift]
            # (exact layout varies by wrapper version; extract defensively)
            for v in _last_row:
                if isinstance(v, (int, float)):
                    continue
            # Method agreement: check if any two methods fire on the same index
            _last_idx = cp_rows[-1][2] if len(cp_rows[-1]) > 2 else None
            if _last_idx is not None:
                method_hits = sum(
                    1 for m, i in all_cps_sorted if i == _last_idx
                )
                _most_recent_method_agreement = method_hits > 1
            # Pre/post means are in the row (positions vary); try to extract numeric fields
            _numerics = [v for v in _last_row if isinstance(v, (int, float))]
            if len(_numerics) >= 2:
                _most_recent_pre = _numerics[-2]
                _most_recent_post = _numerics[-1]
        interp = build_interpretation("cusum_page_hinkley", {
            "series_name": name,
            "n_obs": int(n),
            "n_alarms_total": int(len(all_cps_sorted)),
            "n_alarms_upward": int(len(cusum_up_alarms) + len(ph_up_alarms)),
            "n_alarms_downward": int(len(cusum_down_alarms) + len(ph_down_alarms)),
            "n_alarms_cusum": int(len(cusum_up_alarms) + len(cusum_down_alarms)),
            "n_alarms_page_hinkley": int(len(ph_up_alarms) + len(ph_down_alarms)),
            "most_recent_alarm_date": _most_recent_date,
            "most_recent_pre_mean": _most_recent_pre,
            "most_recent_post_mean": _most_recent_post,
            "most_recent_method_agreement": _most_recent_method_agreement,
            "cusum_threshold": float(cusum_h),
            "ph_delta": float(ph_delta),
            "ph_lambda": float(ph_lambda),
        })
        return make_response(
            ctx,
            tables=[cp_table, params_table, ts_table],
            plain_english_summary=plain_english,
            warnings=warnings,
            charting_suggestions=charting,
            interpretation=interp,
            audit_fields={
                "target": round(target, 6),
                "cusum_k": round(cusum_k, 6),
                "cusum_h": round(cusum_h, 6),
                "ph_delta": round(ph_delta, 6),
                "ph_lambda": round(ph_lambda, 6),
                "n_cusum_up": len(cusum_up_alarms),
                "n_cusum_down": len(cusum_down_alarms),
                "n_ph_up": len(ph_up_alarms),
                "n_ph_down": len(ph_down_alarms),
                "bootstrap_cusum_h": round(bootstrap_cusum_h, 4) if bootstrap_cusum_h else None,
                "bootstrap_ph_lambda": round(bootstrap_ph_lambda, 4) if bootstrap_ph_lambda else None,
                "n_obs": n,
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"CUSUM/Page-Hinkley analysis failed: {e}",
            error_fixes=[
                "Ensure the series is numeric.",
                "Adjust cusum_h or ph_lambda thresholds.",
                "Check for constant series.",
            ],
        )
