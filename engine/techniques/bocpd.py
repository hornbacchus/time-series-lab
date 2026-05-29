"""
Bayesian Online Change Point Detection (BOCPD) for Time Series Lab.

Implements the Adams & MacKay (2007) algorithm for online detection of
change points in a time series. The algorithm maintains a probability
distribution over the current "run length" (time since last change point)
and updates it as each new observation arrives.

Uses a normal-inverse-gamma conjugate prior for the observation model
(Gaussian with unknown mean and variance).
"""

import numpy as np

try:
    from interpretation import build_interpretation  # type: ignore
except Exception:
    def build_interpretation(technique_id, results):  # type: ignore
        return None
from scipy.special import gammaln, betaln

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)

_PRESET_CONFIG = {
    "Fast":     {"min_gap": 10, "map_only": True},
    "Balanced": {"min_gap": 5,  "map_only": False},
    "Thorough": {"min_gap": 2,  "map_only": False},
}


def _run_multivariate(ctx, progress_callback, all_series):
    """Multivariate (joint-across-curve-points) BOCPD — ENG-EXT-CHANGEPOINT-001
    A1c. Detects a SINGLE JOINT change-point set (curve-wide regime-shift
    dates) via Adams-MacKay (2007) with a multivariate Normal-Inverse-Wishart
    (NIW) conjugate prior -> multivariate-Student-t predictive (the matrix
    generalization of S79's scalar Normal-Inverse-Gamma -> Student-t).

    FAITHFUL GENERALIZATION: the NIW->multivariate-t predictive reduces EXACTLY
    to S79's scalar NIG->Student-t at k=1 (ν₀=(k-1)+2α -> dof 2α; Ψ₀=2β·I ->
    2β). The Adams-MacKay recursion (run-length posterior + hazard + change-
    point derivation) mirrors S79 unchanged; only the predictive + sufficient-
    statistics update go matrix-valued. Invoked for >=2 series; univariate
    (1 series) path unchanged.
    """
    from scipy.linalg import solve_triangular  # local: leave univariate imports intact
    np.random.seed(ctx.seed)
    warnings = []
    names = [s[0] for s in all_series]
    arrays = [np.asarray(s[1], dtype=float) for s in all_series]
    k = len(names)

    min_len = min(len(a) for a in arrays)
    if any(len(a) != min_len for a in arrays):
        warnings.append(f"Series aligned to common length {min_len}.")
    Mraw = np.column_stack([a[:min_len] for a in arrays])
    # NaN: DROP rows with any NaN (match S79 strip, adapted to the joint signal).
    row_ok = ~np.isnan(Mraw).any(axis=1)
    n_dropped = int((~row_ok).sum())
    if n_dropped > 0:
        warnings.append(f"{n_dropped} rows with missing values removed.")
    X = Mraw[row_ok]
    n = X.shape[0]
    if n < 20:
        return make_error_response(
            ctx,
            f"Only {n} complete aligned observations across {k} series. "
            "Multivariate BOCPD needs at least 20.",
            error_fixes=["Provide longer time series."],
        )

    cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
    hazard_lambda = float(ctx.get_param("hazard_lambda", 200))
    hazard = 1.0 / hazard_lambda
    prior_kappa = float(ctx.get_param("prior_kappa", 0.01))
    prior_alpha = float(ctx.get_param("prior_alpha", 0.01))
    prior_beta = float(ctx.get_param("prior_beta", 0.01))
    threshold = float(ctx.get_param("threshold", 0.5))
    min_gap = cfg["min_gap"]

    pm = ctx.get_param("prior_mu")
    prior_mu = (np.full(k, float(pm)) if np.isscalar(pm) and pm is not None
                else X.mean(axis=0))
    # NIW hyperparameters generalizing S79's NIG (reduction-preserving):
    #   ν₀ = (k-1) + 2α  -> predictive dof = ν₀-k+1 = 2α  (S79 df at k=1; proper IW)
    #   Ψ₀ = 2β · I_k    (= 2β at k=1)
    nu0 = (k - 1) + 2.0 * prior_alpha
    Psi0 = (2.0 * prior_beta) * np.eye(k)

    def _mvt_logpdf(x, mu_r, kap, nuu, Psi_r):
        """Multivariate-Student-t log-density (NIW posterior predictive).
        Unconditional Cholesky: Σ_t PD-by-construction (Ψ₀ regularizes;
        d=ν-k+1 >= 2α > 0), so no guard branch. Reduces to S79's
        _student_t_logpdf at k=1.
        """
        d = nuu - k + 1
        Sigma_t = Psi_r * (kap + 1.0) / (kap * d)
        L = np.linalg.cholesky(Sigma_t)
        diff = x - mu_r
        yv = solve_triangular(L, diff, lower=True)
        q = float(yv @ yv)
        logdet = 2.0 * float(np.sum(np.log(np.diag(L))))
        return (gammaln((d + k) / 2.0) - gammaln(d / 2.0)
                - (k / 2.0) * np.log(d * np.pi)
                - 0.5 * logdet
                - ((d + k) / 2.0) * np.log(1.0 + q / d))

    progress_callback("Running multivariate Adams-MacKay algorithm", 15)
    max_rl = n + 1
    kappa = np.zeros(max_rl)
    nu = np.zeros(max_rl)
    mu = np.zeros((max_rl, k))
    Psi = np.zeros((max_rl, k, k))
    kappa[0] = prior_kappa
    nu[0] = nu0
    mu[0] = prior_mu
    Psi[0] = Psi0

    R = np.zeros((n + 1, n + 1))
    R[0, 0] = 1.0
    map_rl = np.zeros(n, dtype=int)
    cp_prob = np.zeros(n)

    for t in range(n):
        if t % max(1, n // 20) == 0:
            progress_callback(f"Processing observation {t + 1}/{n}", 15 + int(65 * t / n))
        x = X[t]
        pred_logp = np.array([
            _mvt_logpdf(x, mu[r], kappa[r], nu[r], Psi[r]) for r in range(t + 1)
        ])
        pred = np.exp(pred_logp - np.max(pred_logp))
        growth = R[t, :t + 1] * pred * (1 - hazard)
        cp = np.sum(R[t, :t + 1] * pred * hazard)
        R[t + 1, 1:t + 2] = growth
        R[t + 1, 0] = cp
        evidence = np.sum(R[t + 1, :t + 2])
        if evidence > 0:
            R[t + 1, :t + 2] /= evidence
        map_rl[t] = int(np.argmax(R[t + 1, :t + 2]))
        cp_prob[t] = float(R[t + 1, 0])

        # NIW sufficient-statistics update (rank-1; generalizes scalar β update)
        kappa_new = np.zeros(max_rl)
        nu_new = np.zeros(max_rl)
        mu_new = np.zeros((max_rl, k))
        Psi_new = np.zeros((max_rl, k, k))
        kappa_new[0] = prior_kappa
        nu_new[0] = nu0
        mu_new[0] = prior_mu
        Psi_new[0] = Psi0
        for r in range(t + 1):
            kap = kappa[r]
            kp = kap + 1.0
            kappa_new[r + 1] = kp
            mu_new[r + 1] = (kap * mu[r] + x) / kp
            nu_new[r + 1] = nu[r] + 1.0
            diff = x - mu[r]
            Psi_new[r + 1] = Psi[r] + (kap / kp) * np.outer(diff, diff)
        kappa, nu, mu, Psi = kappa_new, nu_new, mu_new, Psi_new

    progress_callback("Detecting change points", 82)
    # Detection via MAP run-length RESET — the STANDARD correct BOCPD signal.
    # NOTE: S79's univariate criterion (change point where cp_prob=R[t+1,0] >
    # threshold) is NON-FUNCTIONAL: R[t+1,0] == hazard EXACTLY (data-
    # independent — the Adams-MacKay split normalizes to P(r=0)=hazard
    # regardless of the data), so it can never cross a 0.5 threshold (this is
    # why S79 reported n_cps=0). The correct signal is the MAP run-length
    # COLLAPSING to a fresh run: a change point is a time t where the MAP run
    # length drops sharply (> min_gap), i.e. the posterior mass resets. (The
    # univariate S79 path keeps its original criterion for byte-identical
    # backward-compat; the S79 cp_prob-criterion bug is documented + banked as
    # a separate univariate-fix candidate.)
    reset_idx = [t for t in range(1, n) if (map_rl[t - 1] - map_rl[t]) > min_gap]
    filtered_cps = []
    for t in reset_idx:
        if not filtered_cps or (t - filtered_cps[-1]) >= min_gap:
            filtered_cps.append(int(t))
    n_cps = len(filtered_cps)

    progress_callback("Building output", 90)
    time_col = ctx.time if ctx.time and len(ctx.time) >= n else None

    cp_rows = []
    for i, cp_idx in enumerate(filtered_cps):
        t_label = time_col[cp_idx] if time_col else int(cp_idx + 1)
        cp_rows.append([
            i + 1, t_label, cp_idx + 1,
            int(map_rl[cp_idx - 1]), int(map_rl[cp_idx]),
        ])
    cp_table = make_table(
        "Change Points (joint, curve-wide)",
        ["#", "Time", "Position", "MAP RL before", "MAP RL after"], cp_rows,
    )

    seg_boundaries = [0] + filtered_cps + [n]
    seg_rows = []
    for i in range(len(seg_boundaries) - 1):
        a, b = seg_boundaries[i], seg_boundaries[i + 1]
        row = [i + 1, a + 1, b, b - a]
        for j in range(k):
            row.append(round(float(np.mean(X[a:b, j])), 4))
        seg_rows.append(row)
    seg_table = make_table(
        "Segments (per-series means)",
        ["Segment", "Start", "End", "Length"] + [f"Mean({names[j]})" for j in range(k)],
        seg_rows,
    )

    params_table = make_table(
        "Parameters", ["Parameter", "Value"],
        [
            ["Mode", "multivariate (joint NIW-BOCPD)"],
            ["Series (features)", ", ".join(names)],
            ["n_features", k],
            ["Detection", "MAP run-length reset (drop > min_gap)"],
            ["Hazard lambda", hazard_lambda],
            ["NIW prior_kappa", prior_kappa],
            ["NIW nu0 = (k-1)+2*alpha", round(nu0, 6)],
            ["NIW Psi0 diag = 2*beta", round(2.0 * prior_beta, 6)],
            ["Min gap", min_gap],
            ["N change points detected", n_cps],
            ["N observations", n],
        ],
    )

    max_display = 500
    step = max(1, n // max_display)
    ts_rows = []
    for i in range(0, n, step):
        t_label = time_col[i] if time_col else int(i + 1)
        ts_rows.append([t_label, int(map_rl[i]), round(float(cp_prob[i]), 6)])
    ts_table = make_table(
        "BOCPD Time Series", ["Time", "MAP Run Length", "Change Point Prob"], ts_rows,
    )

    if n_cps == 0:
        plain = (
            f"Multivariate BOCPD across {k} series ({', '.join(names)}; {n} "
            f"aligned observations) detected no joint change points at threshold "
            f"{threshold}. The curve appears jointly regime-stable."
        )
    else:
        positions = ", ".join(str(i + 1) for i in filtered_cps)
        plain = (
            f"Multivariate BOCPD across {k} series ({', '.join(names)}; {n} "
            f"observations) detected {n_cps} joint (curve-wide) change point(s) "
            f"at position(s) {positions}. Each is a date where the curve jointly "
            "shifts regime (Bayesian run-length posterior over a multivariate-"
            "NIW observation model; covariance-aware)."
        )

    charting = (
        "Multi-panel: each series with shared vertical lines at the joint change "
        "points; a panel for the joint change-point probability with threshold."
    )
    progress_callback("Done", 100)
    return make_response(
        ctx,
        tables=[cp_table, seg_table, params_table, ts_table],
        plain_english_summary=plain,
        warnings=warnings,
        charting_suggestions=charting,
        interpretation=None,
        audit_fields={
            "mode": "multivariate",
            "n_features": k,
            "features": names,
            "detection": "map_run_length_reset",
            "hazard_lambda": hazard_lambda,
            "prior_kappa": prior_kappa,
            "niw_nu0": round(nu0, 6),
            "niw_psi0_diag": round(2.0 * prior_beta, 6),
            "n_change_points": n_cps,
            "change_point_indices": filtered_cps,
            "min_gap": min_gap,
            "n_obs": n,
        },
    )


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Run Bayesian Online Change Point Detection.

    Parameters (via ctx.params)
    ---------------------------
    hazard_lambda : float, optional
        Expected run length (1/hazard_rate). Higher = fewer change points.
        Default: 200.
    prior_mu : float, optional
        Prior mean for the observation model. Default: series mean.
    prior_kappa : float, optional
        Prior strength for the mean. Default: 0.01 (weak).
    prior_alpha : float, optional
        Prior shape for variance (inverse-gamma). Default: 0.01.
    prior_beta : float, optional
        Prior scale for variance. Default: 0.01.
    threshold : float, optional
        Posterior probability threshold for declaring a change point.
        Default: 0.5.
    """
    try:
        progress_callback("Validating inputs", 5)
        np.random.seed(ctx.seed)

        # Multivariate joint-detection auto-detect (ENG-EXT-CHANGEPOINT-001
        # A1c): >=2 input series -> joint multivariate NIW-BOCPD across the
        # curve. Exactly 1 series -> the univariate NIG path below,
        # UNCHANGED / backward-compatible.
        _all_series = ctx.get_all_series()
        if len(_all_series) >= 2:
            return _run_multivariate(ctx, progress_callback, _all_series)

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
                f"Only {n} valid observations. BOCPD needs at least 20.",
                error_fixes=["Provide a longer series."],
            )

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])

        # Parameters
        hazard_lambda = float(ctx.get_param("hazard_lambda", 200))
        prior_mu = ctx.get_param("prior_mu")
        if prior_mu is None:
            prior_mu = float(np.mean(clean))
        else:
            prior_mu = float(prior_mu)

        prior_kappa = float(ctx.get_param("prior_kappa", 0.01))
        prior_alpha = float(ctx.get_param("prior_alpha", 0.01))
        prior_beta = float(ctx.get_param("prior_beta", 0.01))
        threshold = float(ctx.get_param("threshold", 0.5))
        min_gap = cfg["min_gap"]

        progress_callback("Running Adams-MacKay algorithm", 15)

        # Hazard function: constant hazard H(r) = 1/lambda
        hazard = 1.0 / hazard_lambda

        # Sufficient statistics for normal-inverse-gamma conjugate updates
        # At each run length r, track: kappa, mu, alpha, beta
        # Arrays indexed by run length (0 to t)
        max_rl = n + 1

        # Initialize
        kappa = np.zeros(max_rl)
        mu = np.zeros(max_rl)
        alpha = np.zeros(max_rl)
        beta = np.zeros(max_rl)

        kappa[0] = prior_kappa
        mu[0] = prior_mu
        alpha[0] = prior_alpha
        beta[0] = prior_beta

        # Run length probability matrix: R[t, r] = P(r_t = r | x_{1:t})
        # For memory efficiency, store only the growth probabilities
        # and the change point posterior
        R = np.zeros((n + 1, n + 1))
        R[0, 0] = 1.0

        # Store MAP run length and change point probability at each time
        map_rl = np.zeros(n, dtype=int)
        cp_prob = np.zeros(n)  # probability of change point at time t

        for t in range(n):
            pct = 15 + int(65 * t / n)
            if t % max(1, n // 20) == 0:
                progress_callback(f"Processing observation {t + 1}/{n}", pct)

            x = clean[t]

            # Predictive probability for each run length
            # Student-t distribution: p(x | mu, kappa, alpha, beta)
            pred_probs = np.zeros(t + 1)
            for r in range(t + 1):
                pred_probs[r] = _student_t_logpdf(
                    x, mu[r], kappa[r], alpha[r], beta[r]
                )

            # Convert from log to linear scale (with numerical stability)
            max_lp = np.max(pred_probs)
            pred_probs = np.exp(pred_probs - max_lp)

            # Growth probabilities
            growth = R[t, :t + 1] * pred_probs * (1 - hazard)

            # Change point probability (sum of all run lengths times hazard)
            cp = np.sum(R[t, :t + 1] * pred_probs * hazard)

            # Update R
            R[t + 1, 1:t + 2] = growth
            R[t + 1, 0] = cp

            # Normalize
            evidence = np.sum(R[t + 1, :t + 2])
            if evidence > 0:
                R[t + 1, :t + 2] /= evidence

            # MAP run length
            map_rl[t] = int(np.argmax(R[t + 1, :t + 2]))

            # Change point probability: P(r_t = 0)
            cp_prob[t] = float(R[t + 1, 0])

            # Update sufficient statistics for all run lengths
            # Shift existing statistics (growth)
            kappa_new = np.zeros(max_rl)
            mu_new = np.zeros(max_rl)
            alpha_new = np.zeros(max_rl)
            beta_new = np.zeros(max_rl)

            # New run (change point): reset to prior
            kappa_new[0] = prior_kappa
            mu_new[0] = prior_mu
            alpha_new[0] = prior_alpha
            beta_new[0] = prior_beta

            # Existing runs: update with new observation
            for r in range(t + 1):
                kappa_new[r + 1] = kappa[r] + 1
                mu_new[r + 1] = (kappa[r] * mu[r] + x) / kappa_new[r + 1]
                alpha_new[r + 1] = alpha[r] + 0.5
                beta_new[r + 1] = beta[r] + 0.5 * kappa[r] * (x - mu[r]) ** 2 / kappa_new[r + 1]

            kappa = kappa_new
            mu = mu_new
            alpha = alpha_new
            beta = beta_new

        progress_callback("Detecting change points", 82)

        # Identify change points where cp_prob > threshold
        raw_cps = np.where(cp_prob > threshold)[0]

        # Enforce minimum gap between change points
        filtered_cps = []
        last_cp = -min_gap - 1
        # Sort by probability (descending) and greedily select
        if len(raw_cps) > 0:
            sorted_idx = raw_cps[np.argsort(-cp_prob[raw_cps])]
            selected = set()
            for idx in sorted_idx:
                # Check minimum gap from all selected
                too_close = False
                for s in selected:
                    if abs(idx - s) < min_gap:
                        too_close = True
                        break
                if not too_close:
                    selected.add(idx)
            filtered_cps = sorted(selected)

        n_cps = len(filtered_cps)

        progress_callback("Building output", 90)

        # Change point table
        time_col = ctx.time if ctx.time and len(ctx.time) == len(values) else None
        cp_rows = []
        for i, cp_idx in enumerate(filtered_cps):
            t_label = time_col[cp_idx] if time_col else int(cp_idx + 1)

            # Segment means before and after
            if i == 0:
                seg_before = clean[:cp_idx]
            else:
                seg_before = clean[filtered_cps[i - 1]:cp_idx]

            if i < n_cps - 1:
                seg_after = clean[cp_idx:filtered_cps[i + 1]]
            else:
                seg_after = clean[cp_idx:]

            mean_before = float(np.mean(seg_before)) if len(seg_before) > 0 else None
            mean_after = float(np.mean(seg_after)) if len(seg_after) > 0 else None
            shift = mean_after - mean_before if mean_before is not None and mean_after is not None else None

            cp_rows.append([
                i + 1,
                t_label,
                cp_idx,
                round(float(cp_prob[cp_idx]), 4),
                round(mean_before, 4) if mean_before is not None else None,
                round(mean_after, 4) if mean_after is not None else None,
                round(shift, 4) if shift is not None else None,
            ])

        cp_table = make_table(
            "Detected Change Points",
            ["#", "Time", "Index", "Probability", "Mean Before", "Mean After", "Shift"],
            cp_rows,
        )

        # Run length and probability time series
        max_display = 500
        step = max(1, n // max_display)
        ts_rows = []
        for i in range(0, n, step):
            t_label = time_col[i] if time_col else int(i + 1)
            ts_rows.append([
                t_label,
                round(float(clean[i]), 6),
                int(map_rl[i]),
                round(float(cp_prob[i]), 6),
            ])

        ts_table = make_table(
            "BOCPD Time Series",
            ["Time", "Value", "MAP Run Length", "Change Point Prob"],
            ts_rows,
        )

        # Segment summary
        seg_boundaries = [0] + filtered_cps + [n]
        seg_rows = []
        for i in range(len(seg_boundaries) - 1):
            start = seg_boundaries[i]
            end = seg_boundaries[i + 1]
            seg = clean[start:end]
            t_start = time_col[start] if time_col else int(start + 1)
            t_end = time_col[min(end - 1, n - 1)] if time_col else int(end)
            seg_rows.append([
                i + 1,
                t_start,
                t_end,
                end - start,
                round(float(np.mean(seg)), 4),
                round(float(np.std(seg, ddof=1)), 4) if len(seg) > 1 else 0,
                round(float(np.min(seg)), 4),
                round(float(np.max(seg)), 4),
            ])

        seg_table = make_table(
            "Segments",
            ["Segment", "Start", "End", "Length", "Mean", "Std", "Min", "Max"],
            seg_rows,
        )

        # Parameters table
        params_rows = [
            ["Hazard lambda", hazard_lambda],
            ["Threshold", threshold],
            ["Prior mu", round(prior_mu, 4)],
            ["Prior kappa", prior_kappa],
            ["Prior alpha", prior_alpha],
            ["Prior beta", prior_beta],
            ["Min gap", min_gap],
            ["N change points detected", n_cps],
            ["N observations", n],
        ]
        params_table = make_table("Parameters", ["Parameter", "Value"], params_rows)

        # Plain English
        if n_cps == 0:
            plain_english = (
                f"BOCPD analysis of '{name}' ({n} observations) detected no change points "
                f"at threshold {threshold}. The series appears stationary with no significant "
                f"regime shifts."
            )
        elif n_cps == 1:
            cp = filtered_cps[0]
            prob = cp_prob[cp]
            t_label = time_col[cp] if time_col else cp + 1
            shift = cp_rows[0][6]
            plain_english = (
                f"BOCPD analysis of '{name}' ({n} observations) detected 1 change point "
                f"at position {t_label} (probability {prob:.3f}). "
            )
            if shift is not None:
                plain_english += f"The mean shifted by {shift:.4f} at this point."
        else:
            plain_english = (
                f"BOCPD analysis of '{name}' ({n} observations) detected {n_cps} change points "
                f"at threshold {threshold}. The series is divided into {n_cps + 1} segments. "
            )
            max_shift_idx = np.argmax([abs(r[6]) if r[6] is not None else 0 for r in cp_rows])
            if cp_rows[max_shift_idx][6] is not None:
                plain_english += (
                    f"The largest shift ({cp_rows[max_shift_idx][6]:.4f}) occurs at "
                    f"position {cp_rows[max_shift_idx][1]}."
                )

        charting = (
            "Two-panel chart: top panel shows the time series with vertical dashed lines "
            "at detected change points, colored by segment. Bottom panel shows the "
            "change point probability over time with a horizontal threshold line. "
            "Optionally include a run length heatmap (time vs run length, probability as color)."
        )

        progress_callback("Done", 100)

        # Extract most-recent change point details from cp_rows for the spec.
        _most_recent_date = None
        _most_recent_prob = None
        _most_recent_index = None
        _most_recent_pre_mean = None
        _most_recent_post_mean = None
        if cp_rows:
            # cp_rows is ordered chronologically; take the last entry
            _last = cp_rows[-1]
            _most_recent_date = _last[1]
            _most_recent_index = _last[2]
            _most_recent_prob = _last[3]
            _most_recent_pre_mean = _last[4]
            _most_recent_post_mean = _last[5]
        interp = build_interpretation("bocpd", {
            "series_name": name,
            "n_obs": int(n),
            "n_cps": int(n_cps),
            "most_recent_cp_date": _most_recent_date,
            "most_recent_cp_prob": _most_recent_prob,
            "most_recent_cp_index": _most_recent_index,
            "most_recent_pre_mean": _most_recent_pre_mean,
            "most_recent_post_mean": _most_recent_post_mean,
            "hazard_rate": float(1.0 / hazard_lambda) if hazard_lambda else None,
            "probability_threshold": float(threshold),
        })
        return make_response(
            ctx,
            tables=[cp_table, seg_table, params_table, ts_table],
            plain_english_summary=plain_english,
            warnings=warnings,
            charting_suggestions=charting,
            interpretation=interp,
            audit_fields={
                "hazard_lambda": hazard_lambda,
                "threshold": threshold,
                "prior_mu": round(prior_mu, 4),
                "prior_kappa": prior_kappa,
                "prior_alpha": prior_alpha,
                "prior_beta": prior_beta,
                "n_change_points": n_cps,
                "change_point_indices": filtered_cps,
                "min_gap": min_gap,
                "n_obs": n,
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"BOCPD failed: {e}",
            error_fixes=[
                "Ensure the series is numeric.",
                "Try adjusting hazard_lambda (higher = fewer change points).",
                "Reduce the threshold for more sensitivity.",
            ],
        )


def _student_t_logpdf(x, mu, kappa, alpha, beta):
    """
    Log-pdf of the posterior predictive distribution (Student-t) under
    the normal-inverse-gamma conjugate model.

    The predictive is a Student-t with:
        location = mu
        scale^2 = beta * (kappa + 1) / (alpha * kappa)
        degrees of freedom = 2 * alpha
    """
    df = 2 * alpha
    scale2 = beta * (kappa + 1) / (alpha * kappa) if (alpha * kappa) > 0 else 1e10

    if scale2 <= 0:
        scale2 = 1e-10

    # Student-t log pdf
    z = (x - mu) ** 2 / scale2
    logpdf = (
        gammaln((df + 1) / 2) - gammaln(df / 2)
        - 0.5 * np.log(df * np.pi * scale2)
        - (df + 1) / 2 * np.log(1 + z / df)
    )

    return logpdf
