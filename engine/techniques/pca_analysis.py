"""
Principal Component Analysis for Time Series Lab.

Performs PCA on multiple time series to extract principal components,
loadings, explained variance, and reconstruct series from reduced dimensions.
Useful for dimensionality reduction, common-factor discovery, and
understanding the covariance structure of multivariate time series.
"""

import numpy as np

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


_PRESET_CONFIG = {
    "Fast": {
        "max_components": None,  # all components
        "standardize": True,
        "rotation": None,
        "compute_reconstruction": False,
    },
    "Balanced": {
        "max_components": None,
        "standardize": True,
        "rotation": None,
        "compute_reconstruction": True,
    },
    "Thorough": {
        "max_components": None,
        "standardize": True,
        "rotation": "varimax",
        "compute_reconstruction": True,
    },
}


def _prepare_matrix(ctx):
    """
    Build an (n_obs x n_series) matrix from input series.
    Drops rows where any series has NaN after interpolation.
    Returns: data matrix, series names, warning list.
    """
    all_series = ctx.get_all_series()
    if len(all_series) < 2:
        raise ValueError(
            "PCA requires at least 2 series, but only "
            f"{len(all_series)} were provided. Please select more data columns."
        )

    names = [name for name, _ in all_series]
    arrays = []
    warnings = []
    for name, vals in all_series:
        v = vals.copy()
        nans = np.isnan(v)
        if nans.all():
            raise ValueError(f"Series '{name}' is entirely NaN.")
        if nans.any():
            valid_idx = np.where(~nans)[0]
            if len(valid_idx) >= 2:
                v[nans] = np.interp(np.where(nans)[0], valid_idx, v[valid_idx])
                warnings.append(
                    f"Series '{name}': {int(nans.sum())} NaN values were interpolated."
                )
            else:
                raise ValueError(
                    f"Series '{name}' has too few non-NaN values for interpolation."
                )
        arrays.append(v)

    # Align lengths (trim to shortest)
    min_len = min(len(a) for a in arrays)
    if any(len(a) != min_len for a in arrays):
        warnings.append(
            f"Series lengths differ; trimmed all to shortest length ({min_len})."
        )
    arrays = [a[:min_len] for a in arrays]

    data = np.column_stack(arrays)  # shape (n_obs, n_series)

    # Drop any rows still containing NaN
    row_valid = ~np.any(np.isnan(data), axis=1)
    if not row_valid.all():
        data = data[row_valid]
        warnings.append(
            f"{int((~row_valid).sum())} rows dropped due to remaining NaN."
        )

    return data, names, warnings


def _varimax_rotation(loadings, max_iter=100, tol=1e-6):
    """
    Apply Varimax rotation to the loadings matrix.
    Returns rotated loadings.
    """
    p, k = loadings.shape
    rotation = np.eye(k)
    d = 0.0

    for _ in range(max_iter):
        old_d = d
        for i in range(k):
            for j in range(i + 1, k):
                # Compute 2x2 rotation angle
                u = loadings[:, i] ** 2 - loadings[:, j] ** 2
                v = 2 * loadings[:, i] * loadings[:, j]
                A = np.sum(u)
                B = np.sum(v)
                C = np.sum(u ** 2 - v ** 2)
                D = 2 * np.sum(u * v)
                num = D - 2 * A * B / p
                den = C - (A ** 2 - B ** 2) / p
                angle = 0.25 * np.arctan2(num, den)
                # Apply rotation
                cos_a = np.cos(angle)
                sin_a = np.sin(angle)
                new_i = loadings[:, i] * cos_a + loadings[:, j] * sin_a
                new_j = -loadings[:, i] * sin_a + loadings[:, j] * cos_a
                loadings[:, i] = new_i
                loadings[:, j] = new_j
                # Track rotation
                rot_i = rotation[:, i] * cos_a + rotation[:, j] * sin_a
                rot_j = -rotation[:, i] * sin_a + rotation[:, j] * cos_a
                rotation[:, i] = rot_i
                rotation[:, j] = rot_j

        d = np.sum(loadings ** 4) - np.sum(np.sum(loadings ** 2, axis=0) ** 2) / p
        if abs(d - old_d) < tol:
            break

    return loadings, rotation


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Principal Component Analysis on multivariate time series.

    Parameters (via ctx.params)
    ---------------------------
    n_components : int, optional
        Number of components to retain. Default: all.
    standardize : bool, optional
        Standardize series to zero mean / unit variance before PCA.
        Default: True.
    rotation : str or None, optional
        Apply rotation to loadings. 'varimax' or None. Default from preset.
    """
    try:
        progress_callback("Validating inputs", 5)
        np.random.seed(ctx.seed)

        data, series_names, warn_list = _prepare_matrix(ctx)
        n_obs, n_series = data.shape

        if n_obs < 3:
            return make_error_response(
                ctx,
                f"Only {n_obs} valid observations after cleaning. "
                "PCA requires at least 3.",
                error_fixes=["Provide longer time series.", "Reduce missing data."],
            )

        preset_cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])

        standardize = ctx.get_param("standardize", preset_cfg["standardize"])
        if isinstance(standardize, str):
            standardize = standardize.lower() in ("true", "1", "yes")
        rotation = ctx.get_param("rotation", preset_cfg["rotation"])
        compute_recon = preset_cfg["compute_reconstruction"]

        max_components = min(n_obs, n_series)
        n_components = ctx.get_param("n_components", preset_cfg["max_components"])
        if n_components is not None:
            n_components = int(n_components)
            n_components = min(n_components, max_components)
        else:
            n_components = max_components

        progress_callback("Standardizing data", 15)

        # Center (and optionally standardize) the data
        means = data.mean(axis=0)
        centered = data - means
        if standardize:
            stds = data.std(axis=0, ddof=1)
            stds[stds == 0] = 1.0  # avoid division by zero
            centered = centered / stds
        else:
            stds = np.ones(n_series)

        progress_callback("Computing covariance matrix", 25)

        # Compute covariance matrix and eigen-decomposition
        cov_matrix = np.cov(centered, rowvar=False)

        progress_callback("Eigen-decomposition", 40)

        eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)
        # Sort by descending eigenvalue
        order = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[order]
        eigenvectors = eigenvectors[:, order]

        # Ensure eigenvalues are non-negative (numerical precision)
        eigenvalues = np.maximum(eigenvalues, 0.0)

        # Retain requested number of components
        eigenvalues_all = eigenvalues.copy()
        eigenvalues = eigenvalues[:n_components]
        eigenvectors = eigenvectors[:, :n_components]

        total_variance = float(np.sum(eigenvalues_all))
        if total_variance == 0:
            return make_error_response(
                ctx,
                "Total variance is zero. All series may be constant.",
                error_fixes=["Provide series with variation."],
            )

        explained_ratio = eigenvalues / total_variance
        cumulative_ratio = np.cumsum(explained_ratio)

        progress_callback("Computing scores and loadings", 60)

        # Scores (projections): (n_obs x n_components)
        scores = centered @ eigenvectors

        # Loadings: eigenvectors scaled by sqrt(eigenvalue)
        loadings = eigenvectors * np.sqrt(eigenvalues)

        # Optional Varimax rotation
        rotated_label = ""
        if rotation and rotation.lower() == "varimax" and n_components >= 2:
            progress_callback("Applying Varimax rotation", 70)
            loadings, _ = _varimax_rotation(loadings.copy())
            rotated_label = " (Varimax-rotated)"
            # Recompute scores with rotated loadings
            # scores = centered @ loadings @ inv(loadings.T @ loadings) @ loadings.T
            # Simplified: use pseudo-inverse
            scores = centered @ np.linalg.pinv(loadings.T)

        progress_callback("Building output tables", 80)

        # --- Table 1: Eigenvalues & Explained Variance ---
        eig_rows = []
        for i in range(n_components):
            eig_rows.append([
                f"PC{i + 1}",
                round(float(eigenvalues[i]), 6),
                round(float(explained_ratio[i] * 100), 2),
                round(float(cumulative_ratio[i] * 100), 2),
            ])
        eig_table = make_table(
            "Explained Variance",
            ["Component", "Eigenvalue", "Variance %", "Cumulative %"],
            eig_rows,
        )

        # --- Table 2: Loadings ---
        loading_cols = ["Series"] + [f"PC{i + 1}" for i in range(n_components)]
        loading_rows = []
        for j in range(n_series):
            row = [series_names[j]]
            for i in range(n_components):
                row.append(round(float(loadings[j, i]), 4))
            loading_rows.append(row)
        loadings_table = make_table(
            f"Loadings{rotated_label}",
            loading_cols,
            loading_rows,
        )

        # --- Table 3: Component Scores (first 200 rows max) ---
        score_cols = ["Observation"] + [f"PC{i + 1}" for i in range(n_components)]
        max_score_rows = min(n_obs, 200)
        score_rows = []
        for t in range(max_score_rows):
            row = [t + 1]
            for i in range(n_components):
                row.append(round(float(scores[t, i]), 6))
            score_rows.append(row)
        scores_table = make_table("Component Scores", score_cols, score_rows)

        tables = [eig_table, loadings_table, scores_table]

        # --- Table 4: Reconstruction Error (Balanced/Thorough) ---
        if compute_recon and n_components < n_series:
            progress_callback("Computing reconstruction error", 88)
            reconstructed = scores @ loadings.T
            if standardize:
                reconstructed = reconstructed * stds + means
            else:
                reconstructed = reconstructed + means

            recon_error = data - reconstructed
            rmse_per_series = np.sqrt(np.mean(recon_error ** 2, axis=0))
            recon_rows = []
            for j in range(n_series):
                recon_rows.append([
                    series_names[j],
                    round(float(rmse_per_series[j]), 6),
                ])
            recon_table = make_table(
                "Reconstruction Error",
                ["Series", "RMSE"],
                recon_rows,
            )
            tables.append(recon_table)

        # --- Table 5: Model Summary ---
        # Kaiser criterion: components with eigenvalue > 1 (when standardized)
        n_kaiser = int(np.sum(eigenvalues_all > 1.0)) if standardize else n_components
        summary_rows = [
            ["Number of Series", n_series],
            ["Observations", n_obs],
            ["Components Retained", n_components],
            ["Standardized", "Yes" if standardize else "No"],
            ["Rotation", rotation if rotation else "None"],
            ["Total Variance", round(total_variance, 4)],
            ["Explained by Retained", f"{cumulative_ratio[-1] * 100:.1f}%"],
            ["Kaiser Criterion (eigenvalue > 1)", n_kaiser],
        ]
        summary_table = make_table("Model Summary", ["Metric", "Value"], summary_rows)
        tables.append(summary_table)

        # Determine how many components explain >=80% variance
        n_80 = int(np.searchsorted(cumulative_ratio, 0.80)) + 1
        n_80 = min(n_80, n_components)

        # Identify top-loading series for PC1
        pc1_abs = np.abs(loadings[:, 0])
        top_loader_idx = int(np.argmax(pc1_abs))
        top_loader = series_names[top_loader_idx]

        plain_english = (
            f"PCA on {n_series} series ({n_obs} observations). "
            f"PC1 explains {explained_ratio[0] * 100:.1f}% of variance; "
            f"{n_80} component{'s' if n_80 > 1 else ''} explain "
            f"{cumulative_ratio[min(n_80, n_components) - 1] * 100:.1f}%. "
            f"Strongest PC1 loading: '{top_loader}' ({loadings[top_loader_idx, 0]:.3f})."
        )

        charting = (
            "Scree plot: eigenvalues or variance % vs component number. "
            "Cumulative variance line chart. "
            "Biplot of PC1 vs PC2 scores with loading vectors. "
            "Heatmap of the loadings matrix."
        )

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=tables,
            plain_english_summary=plain_english,
            warnings=warn_list,
            charting_suggestions=charting,
            audit_fields={
                "n_series": n_series,
                "n_obs": n_obs,
                "n_components": n_components,
                "standardized": standardize,
                "rotation": rotation or "none",
                "pc1_variance_pct": round(float(explained_ratio[0] * 100), 2),
                "cumulative_variance_pct": round(float(cumulative_ratio[-1] * 100), 2),
                "kaiser_components": n_kaiser,
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"PCA failed: {e}",
            error_fixes=[
                "Ensure at least 2 numeric series are selected.",
                "Check for constant or nearly-constant series.",
                "Provide series with at least 3 observations.",
            ],
        )
