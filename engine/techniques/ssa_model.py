"""
Singular Spectrum Analysis (SSA) for Time Series Lab.

SSA decomposes a time series into trend, oscillatory, and noise components
by embedding it into a trajectory matrix and applying SVD. The resulting
eigentriples can be grouped to reconstruct interpretable components.

Algorithm:
1. Embed the series into a Hankel (trajectory) matrix of dimension L x K.
2. SVD of the trajectory matrix.
3. Group eigentriples into meaningful components.
4. Reconstruct component time series via diagonal averaging.
"""

import numpy as np

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    flip_sign_svd,
)

_PRESET_CONFIG = {
    "Fast":     {"auto_group": True,  "n_components_report": 10},
    "Balanced": {"auto_group": True,  "n_components_report": 20},
    "Thorough": {"auto_group": True,  "n_components_report": 40},
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Perform Singular Spectrum Analysis.

    Parameters (via ctx.params)
    ---------------------------
    window_length : int, optional
        Embedding dimension L (default N//2 or N//3 depending on preset).
    n_components : int, optional
        Number of SVD components to keep (default: all up to n_components_report).
    groups : list[list[int]], optional
        Manual grouping of component indices. E.g. [[0,1],[2,3],[4]].
        If omitted, automatic grouping is used.
    """
    try:
        progress_callback("Validating inputs", 5)
        np.random.seed(ctx.seed)

        name, values = ctx.get_primary_series()
        warnings = []

        # Drop NaN (SSA needs contiguous data)
        nan_mask = np.isnan(values)
        if np.any(nan_mask):
            # Interpolate interior NaN
            nans = np.where(nan_mask)[0]
            valid = np.where(~nan_mask)[0]
            if len(valid) < 10:
                return make_error_response(
                    ctx,
                    "Too few non-missing values for SSA.",
                    error_fixes=["Provide a series with fewer gaps."],
                )
            filled = values.copy()
            filled[nans] = np.interp(nans, valid, values[valid])
            warnings.append(f"{len(nans)} missing values linearly interpolated for SSA.")
        else:
            filled = values.copy()

        n = len(filled)
        if n < 20:
            return make_error_response(
                ctx,
                f"Only {n} observations. SSA needs at least 20.",
                error_fixes=["Provide a longer time series."],
            )

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])

        # Window length
        L_param = ctx.get_param("window_length")
        if L_param is not None:
            L = int(L_param)
        else:
            if ctx.preset == "Fast":
                L = max(10, n // 4)
            else:
                L = max(10, n // 2)
        L = min(L, n // 2)  # L must be <= N/2
        K = n - L + 1  # number of columns

        n_comp_param = ctx.get_param("n_components")
        max_report = cfg["n_components_report"]
        if n_comp_param is not None:
            n_components = min(int(n_comp_param), L, K)
        else:
            n_components = min(max_report, L, K)

        progress_callback("Building trajectory matrix", 15)

        # Step 1: Embedding
        X = np.zeros((L, K))
        for i in range(K):
            X[:, i] = filled[i:i + L]

        progress_callback("Computing SVD", 30)

        # Step 2: SVD
        try:
            U, sigma, Vt = np.linalg.svd(X, full_matrices=False)
        except np.linalg.LinAlgError:
            return make_error_response(
                ctx,
                "SVD computation failed.",
                error_fixes=["Check for constant or near-constant series."],
            )

        # Truncate to n_components
        U = U[:, :n_components]
        sigma = sigma[:n_components]
        Vt = Vt[:n_components, :]

        # Sign-normalize the SVD basis. np.linalg.svd doesn't guarantee
        # a sign convention — U and Vt can flip between runs (different
        # numpy builds, different LAPACK backends, or just when data
        # changes by a rounding error). Flipping leaves sigma and Xi
        # (the rank-1 reconstruction below) unchanged mathematically,
        # but downstream the reconstructed trend / oscillatory
        # components swap polarity, so charts look different. Apply
        # sklearn's svd_flip convention (max-absolute entry of U
        # positive) — stable across runs.
        U, Vt = flip_sign_svd(U, Vt)

        total_variance = float(np.sum(sigma ** 2))

        # Eigenvalue spectrum
        eigenvalues = sigma ** 2
        explained_pct = 100 * eigenvalues / total_variance if total_variance > 0 else np.zeros_like(eigenvalues)
        cumulative_pct = np.cumsum(explained_pct)

        progress_callback("Reconstructing components", 50)

        # Step 4: Diagonal averaging (Hankelization) for each component
        reconstructed = np.zeros((n_components, n))
        for i in range(n_components):
            # Rank-1 matrix for component i
            Xi = sigma[i] * np.outer(U[:, i], Vt[i, :])
            reconstructed[i] = _diagonal_average(Xi, n, L, K)

        progress_callback("Grouping components", 65)

        # Automatic grouping using w-correlation
        groups_param = ctx.get_param("groups")
        if groups_param is not None and isinstance(groups_param, list):
            groups = groups_param
        elif cfg["auto_group"]:
            groups = _auto_group(reconstructed, n_components)
        else:
            groups = [[i] for i in range(n_components)]

        # Reconstruct grouped components
        group_names = []
        group_series = []
        for g_idx, group in enumerate(groups):
            valid_indices = [i for i in group if i < n_components]
            if not valid_indices:
                continue
            g_recon = np.sum(reconstructed[valid_indices], axis=0)
            group_series.append(g_recon)
            group_names.append(f"Group {g_idx + 1} ({','.join(str(i) for i in valid_indices)})")

        # Residual: original minus all grouped components
        total_reconstructed = np.sum(reconstructed, axis=0)
        residual = filled - total_reconstructed

        progress_callback("Building output tables", 80)

        # Eigenvalue table
        eigen_rows = []
        for i in range(n_components):
            eigen_rows.append([
                i + 1,
                round(float(sigma[i]), 6),
                round(float(eigenvalues[i]), 4),
                round(float(explained_pct[i]), 4),
                round(float(cumulative_pct[i]), 2),
            ])
        eigen_table = make_table(
            "Singular Values & Explained Variance",
            ["Component", "Singular Value", "Eigenvalue", "% Variance", "Cumulative %"],
            eigen_rows,
        )

        # Component time series table
        time_col = ctx.time if ctx.time and len(ctx.time) == n else list(range(1, n + 1))
        max_display = 500
        step = max(1, n // max_display)

        ts_rows = []
        ts_cols = ["Time", name]
        for gn in group_names:
            ts_cols.append(gn)
        ts_cols.append("Residual")

        for i in range(0, n, step):
            row = [time_col[i], round(float(filled[i]), 6)]
            for gs in group_series:
                row.append(round(float(gs[i]), 6))
            row.append(round(float(residual[i]), 6))
            ts_rows.append(row)

        ts_table = make_table("SSA Decomposition", ts_cols, ts_rows)

        # Group summary table
        group_rows = []
        for g_idx, (gn, gs) in enumerate(zip(group_names, group_series)):
            g_var = float(np.var(gs))
            g_pct = 100 * g_var / np.var(filled) if np.var(filled) > 0 else 0
            group_rows.append([
                gn,
                round(g_var, 6),
                round(g_pct, 2),
                round(float(np.mean(gs)), 6),
                round(float(np.std(gs)), 6),
            ])
        # Residual row
        r_var = float(np.var(residual))
        r_pct = 100 * r_var / np.var(filled) if np.var(filled) > 0 else 0
        group_rows.append([
            "Residual",
            round(r_var, 6),
            round(r_pct, 2),
            round(float(np.mean(residual)), 6),
            round(float(np.std(residual)), 6),
        ])

        group_table = make_table(
            "Component Groups",
            ["Group", "Variance", "% Total Var", "Mean", "Std Dev"],
            group_rows,
        )

        # W-correlation matrix (for first few components)
        n_wcorr = min(10, n_components)
        wcorr = _w_correlation_matrix(reconstructed[:n_wcorr], n, L)
        wcorr_rows = []
        for i in range(n_wcorr):
            row = [i + 1] + [round(float(wcorr[i, j]), 4) for j in range(n_wcorr)]
            wcorr_rows.append(row)
        wcorr_cols = ["Component"] + [str(j + 1) for j in range(n_wcorr)]
        wcorr_table = make_table("W-Correlation Matrix", wcorr_cols, wcorr_rows)

        # Summary
        n_95 = int(np.searchsorted(cumulative_pct, 95) + 1)
        n_99 = int(np.searchsorted(cumulative_pct, 99) + 1)

        plain_english = (
            f"SSA decomposition of '{name}' ({n} observations, window L={L}). "
            f"First component explains {explained_pct[0]:.1f}% of variance. "
            f"{n_95} components needed for 95% of variance, "
            f"{n_99} for 99%. "
            f"Decomposed into {len(groups)} groups plus residual. "
        )

        if len(group_series) > 0:
            largest_group_pct = max(
                100 * np.var(gs) / np.var(filled) for gs in group_series
            ) if np.var(filled) > 0 else 0
            plain_english += (
                f"The largest group captures {largest_group_pct:.1f}% of total variance."
            )

        charting = (
            "Multi-panel chart: top panel shows original series with trend (Group 1) overlay. "
            "Middle panels show each group component. Bottom panel shows residual. "
            "Also include an eigenvalue scree plot (log scale) and the W-correlation heatmap."
        )

        progress_callback("Done", 100)

        # Prompt C4: expose dominant and second-group variance shares
        # from the group_rows computation just above.
        group_shares = [float(row[2]) for row in group_rows if row[0] != "Residual"]
        dominant_group_share = group_shares[0] if len(group_shares) >= 1 else None
        second_group_share = group_shares[1] if len(group_shares) >= 2 else None

        audit = {
            "window_length": L,
            "n_components": n_components,
            "n_groups": len(groups),
            "groups": [[int(i) for i in g] for g in groups],
            "explained_variance_pct_1": round(float(explained_pct[0]), 4),
            "components_for_95pct": n_95,
            "components_for_99pct": n_99,
            "total_variance": round(total_variance, 4),
            "n_obs": n,
            "dominant_group_share": round(dominant_group_share, 2) if dominant_group_share is not None else None,
            "second_group_share": round(second_group_share, 2) if second_group_share is not None else None,
        }

        try:
            from interpretation import build_interpretation  # type: ignore
        except Exception:
            def build_interpretation(technique_id, results):  # type: ignore
                return None
        _interp_dict = dict(audit)
        _interp_dict["series_name"] = name
        interp = build_interpretation("ssa_model", _interp_dict)

        return make_response(
            ctx,
            tables=[eigen_table, group_table, wcorr_table, ts_table],
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
            f"SSA decomposition failed: {e}",
            error_fixes=[
                "Ensure the series is numeric.",
                "Try a smaller window_length if memory is limited.",
                "Check for constant series (zero variance).",
            ],
        )


def _diagonal_average(Xi, n, L, K):
    """
    Diagonal averaging (Hankelization) of a rank-1 matrix Xi (L x K) to
    reconstruct a time series of length n.
    """
    reconstructed = np.zeros(n)
    counts = np.zeros(n)

    for i in range(L):
        for j in range(K):
            reconstructed[i + j] += Xi[i, j]
            counts[i + j] += 1

    counts[counts == 0] = 1  # avoid division by zero
    return reconstructed / counts


def _w_correlation_matrix(reconstructed, n, L):
    """
    Compute the W-correlation matrix between reconstructed components.
    W-correlation uses weighted inner products where weights are the
    number of diagonal averages at each position.
    """
    K = n - L + 1
    n_comp = len(reconstructed)

    # Weights: w_i = min(i+1, L, K, n-i) for i = 0, ..., n-1
    w = np.array([min(i + 1, L, K, n - i) for i in range(n)])

    wcorr = np.zeros((n_comp, n_comp))
    for i in range(n_comp):
        for j in range(i, n_comp):
            num = np.sum(w * reconstructed[i] * reconstructed[j])
            denom_i = np.sqrt(np.sum(w * reconstructed[i] ** 2))
            denom_j = np.sqrt(np.sum(w * reconstructed[j] ** 2))
            if denom_i > 0 and denom_j > 0:
                wcorr[i, j] = abs(num / (denom_i * denom_j))
            wcorr[j, i] = wcorr[i, j]

    return wcorr


def _auto_group(reconstructed, n_components):
    """
    Automatic grouping based on W-correlation.
    Components with high W-correlation (> 0.5) are placed in the same group.
    """
    n = reconstructed.shape[1]
    # Simple L estimate
    L = n // 2

    wcorr = _w_correlation_matrix(reconstructed, n, L)

    assigned = set()
    groups = []

    for i in range(n_components):
        if i in assigned:
            continue
        group = [i]
        assigned.add(i)
        for j in range(i + 1, n_components):
            if j in assigned:
                continue
            if wcorr[i, j] > 0.5:
                group.append(j)
                assigned.add(j)
        groups.append(group)

    return groups
