"""
Vector Autoregression (VAR) model for Time Series Lab.

Fits a VAR(p) model to two or more series, producing impulse responses,
forecast error variance decomposition, and multi-step forecasts.

References
----------
Sims 1980 (VAR origin); Lütkepohl 2005 *New Introduction to Multiple
Time Series Analysis*; statsmodels `tsa.api.VAR` (the underlying
estimator). Reference parity check: R `vars::VAR` at Phase 1 audit 1c
(closed-form match at machine precision given fixed coefficients).

Audit fields
------------
- ``companion_eig_magnitudes``: list of |λ_i| for the VAR(p) companion
  matrix. Stationarity requires max |λ| < 1; Pattern F structural
  invariant ``var_eigenvalues`` (P-2 §D.1) verifies this. See P-3
  §3.4.1 (O-1) for the near-unit-root margin observation banked at
  BYF Mod-2 + corrective Pattern F threshold tightening to 0.9995
  at Phase 4 S9.
"""

import numpy as np
import warnings as _warnings
from statsmodels.tsa.api import VAR

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    dropna_aligned,
)

try:
    from interpretation import build_interpretation  # type: ignore
except Exception:
    def build_interpretation(technique_id, results):  # type: ignore
        return None


def _prepare_series(values):
    """Strip edge NaN, interpolate interior."""
    first = 0
    while first < len(values) and np.isnan(values[first]):
        first += 1
    last = len(values) - 1
    while last >= 0 and np.isnan(values[last]):
        last -= 1
    if first > last:
        return np.array([])
    trimmed = values[first:last + 1].copy()
    nan_count = int(np.isnan(trimmed).sum())
    if nan_count > 0:
        nans = np.where(np.isnan(trimmed))[0]
        valid = np.where(~np.isnan(trimmed))[0]
        if len(valid) >= 2:
            trimmed[nans] = np.interp(nans, valid, trimmed[valid])
    return trimmed


def _blanchard_quah_b0(fit):
    """Blanchard–Quah (1989) structural identification via LONG-RUN
    restrictions (ENG-EXT-MULTIVARIATE-001 M3a net-new — statsmodels SVAR
    is A/B/AB short-run only).

    The structural impact matrix ``B0`` (u_t = B0 ε_t, Σ = B0 B0ᵀ) is pinned
    by requiring the LONG-RUN cumulative impact ``C(1)·B0`` to be lower-
    triangular (shock j has no permanent effect on variable i for i<j),
    where ``C(1) = (I − A₁ − … − Aₚ)⁻¹`` is the VAR long-run multiplier::

        C(1)·B0 = cholesky_lower(C(1)·Σ·C(1)ᵀ)   (unique, +diagonal)
        ⇒  B0 = C(1)⁻¹ · cholesky_lower(C(1)·Σ·C(1)ᵀ)

    Returns ``(B0, lrim)`` where ``lrim = C(1)·B0`` is the (lower-triangular)
    long-run impact matrix. Identical to R ``vars::BQ`` (``$B`` / ``$LRIM``);
    sign convention matches (positive-diagonal long-run Cholesky). The
    structural IRF at horizon h is ``ma_rep(h)[h] @ B0`` (impact = B0).
    Unconditional Cholesky — PD by construction (Σ PD ⇒ C(1)ΣC(1)ᵀ PD).
    """
    C1 = np.asarray(fit.long_run_effects(), dtype=np.float64)
    Sigma = np.asarray(fit.sigma_u, dtype=np.float64)
    M = C1 @ Sigma @ C1.T
    P = np.linalg.cholesky(M)  # lower-triangular, positive diagonal
    B0 = np.linalg.solve(C1, P)
    lrim = C1 @ B0
    # Defensive column-sign canonicalization: enforce non-negative diagonal
    # of the long-run impact matrix (already true from the +diagonal
    # Cholesky, but guards against a future fixture flipping a column
    # relative to the R reference convention).
    for j in range(lrim.shape[1]):
        if lrim[j, j] < 0:
            B0[:, j] = -B0[:, j]
            lrim[:, j] = -lrim[:, j]
    return B0, lrim


def _proxy_svar(fit, instrument, normalize_var=0):
    """Proxy / external-instrument (IV) SVAR identification of ONE structural
    shock (ENG-EXT-MULTIVARIATE-001 M3c net-new — statsmodels SVAR is A/B/AB
    short-run only; no proxy-SVAR).

    Stock-Watson / Mertens-Ravn: given the reduced-form VAR residuals u_t and
    an external instrument z_t correlated with the target structural shock ε₁
    and uncorrelated with the others, ``E[u z] = B·E[ε z] = b₁·α`` — so the
    sample covariance ``Cov(u, z)`` is proportional to the target shock's
    impact column b₁. Normalize to unit impact on ``normalize_var`` (the
    column is identified only up to scale and sign). The identified shock
    series is the GLS projection ``ε₁_hat = (u Σ⁻¹ b1)/(b1ᵀ Σ⁻¹ b1)``; its
    correlation with z is the instrument-relevance (first-stage) diagnostic —
    the scheme-DEFINING property.

    Returns ``(b1, eps_hat, relevance)``: b1 the (relative) impact column
    (b1[normalize_var]=1), eps_hat the identified shock series (nobs,),
    relevance = corr(eps_hat, z). Structural IRF (target shock) =
    ``ma_rep(h)[h] @ b1``. Point-identified (relative IRF unique given z).
    """
    u = np.asarray(fit.resid, dtype=np.float64)  # (nobs, k)
    nobs = u.shape[0]
    z = np.asarray(instrument, dtype=np.float64).reshape(-1)
    z = z[-nobs:]  # align to the residual sample (drop the first p observations)
    z = z - z.mean()
    cov_uz = (u * z[:, None]).mean(axis=0)  # E[u z], shape (k,)
    if abs(float(cov_uz[normalize_var])) < 1e-300:
        raise ValueError(
            "Proxy instrument has ~zero covariance with the normalization "
            "variable; choose a different proxy_normalize_var or a relevant "
            "instrument."
        )
    b1 = cov_uz / cov_uz[normalize_var]  # relative impact column
    Sigma = np.asarray(fit.sigma_u, dtype=np.float64)
    Sinv = np.linalg.inv(Sigma)
    denom = float(b1 @ Sinv @ b1)
    eps_hat = (u @ Sinv @ b1) / denom  # identified target shock series (nobs,)
    zs = np.std(z)
    es = np.std(eps_hat)
    relevance = (float(np.corrcoef(eps_hat, z)[0, 1])
                 if zs > 0 and es > 0 else 0.0)
    return b1, eps_hat, relevance


def _mc_irf_bands(fit, steps, repl, signif, seed, orth=True, burn=100):
    """Monte-Carlo confidence bands for the (orthogonalized) IRF.

    ENG-EXT-MULTIVARIATE-001 M1. Reimplements statsmodels'
    ``VARResults.irf_resim`` body but with DISTINCT per-replication seeds
    derived deterministically from ``seed`` (master ``RandomState(seed)`` →
    ``repl`` child seeds). This works around a statsmodels bug: ``irf_resim``
    passes the SAME fixed ``seed`` to ``util.varsim`` on every replication,
    so ``RandomState(seed=seed)`` reproduces the IDENTICAL simulation each
    iteration → zero across-replication variance → a degenerate (lower==upper)
    band; while ``seed=None`` restores variance but is non-deterministic
    (ignores any global seed). Distinct-per-replication seeds give BOTH proper
    variance (each replication a different simulation) AND reproducibility
    (the whole ensemble is a deterministic function of ``seed``).

    Returns ``(lower, upper)`` each shape ``(steps + 1, neqs, neqs)``, indexed
    ``[horizon, response, shock]`` (same convention as ``orth_irfs``).
    """
    from statsmodels.tsa.api import VAR as _VAR
    from statsmodels.tsa.vector_ar import util as _util

    coefs = fit.coefs
    intercept = fit.intercept
    sigma_u = fit.sigma_u
    k_ar = fit.k_ar
    neqs = fit.neqs
    nobs = fit.nobs
    trend = fit.trend
    exog = getattr(fit, "exog", None)
    nobs_original = nobs + k_ar

    master = np.random.RandomState(seed)
    child_seeds = master.randint(0, 2 ** 31 - 1, size=repl)

    ma_coll = np.zeros((repl, steps + 1, neqs, neqs))
    for i in range(repl):
        sim = _util.varsim(
            coefs, intercept, sigma_u,
            seed=int(child_seeds[i]), steps=nobs_original + burn,
        )[burn:]
        refit = _VAR(sim, exog=exog).fit(maxlags=k_ar, trend=trend)
        ma = refit.orth_ma_rep(maxn=steps) if orth else refit.ma_rep(maxn=steps)
        ma_coll[i, :, :, :] = ma

    ma_sort = np.sort(ma_coll, axis=0)
    low_idx = int(round(signif / 2 * repl) - 1)
    upp_idx = int(round((1 - signif / 2) * repl) - 1)
    return ma_sort[low_idx, :, :, :], ma_sort[upp_idx, :, :, :]


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Fit a VAR model to 2+ series.

    Parameters (via ctx.params)
    ---------------------------
    max_lag : int, optional
        Maximum lag for order selection. Default depends on preset.
    ic : str, optional
        Information criterion for lag selection: 'aic', 'bic', 'hqic', 'fpe'. Default 'aic'.
    lag : int, optional
        Fixed lag order. If provided, overrides automatic selection.
    horizon : int, optional
        Forecast steps. Default 10.
    irf_periods : int, optional
        Number of periods for impulse response function. Default 20.
    trend : str, optional
        'c' (constant, default), 'ct' (constant+trend), 'n' (none).
    """
    try:
        progress_callback("Validating inputs", 5)

        ctx.validate_min_series(2)
        all_series = ctx.get_all_series()
        names = [s[0] for s in all_series]
        warn_list = []

        # Prepare and align all series
        arrays = []
        for name, vals in all_series:
            arrays.append(vals)

        # Check equal lengths
        lengths = [len(a) for a in arrays]
        if len(set(lengths)) > 1:
            min_len = min(lengths)
            warn_list.append(
                f"Series have different lengths {lengths}. Truncating all to {min_len}."
            )
            arrays = [a[:min_len] for a in arrays]

        # Aligned NaN removal
        stacked = np.column_stack(arrays)
        mask = np.all(~np.isnan(stacked), axis=1)
        n_dropped = int(np.sum(~mask))
        if n_dropped > 0:
            # Interpolate instead of dropping to keep alignment
            for col in range(stacked.shape[1]):
                nan_idx = np.where(np.isnan(stacked[:, col]))[0]
                valid_idx = np.where(~np.isnan(stacked[:, col]))[0]
                if len(valid_idx) >= 2 and len(nan_idx) > 0:
                    stacked[nan_idx, col] = np.interp(nan_idx, valid_idx, stacked[valid_idx, col])
            warn_list.append(f"{n_dropped} rows had missing values that were interpolated.")

        # Final NaN check
        final_mask = np.all(~np.isnan(stacked), axis=1)
        stacked = stacked[final_mask]
        n = stacked.shape[0]
        k = stacked.shape[1]

        if n < 3 * k + 5:
            return make_error_response(
                ctx,
                f"Too few observations ({n}) for {k} variables. Need at least {3 * k + 5}.",
                error_fixes=["Provide longer series or fewer variables."],
            )

        horizon = int(ctx.get_param("horizon", 10))
        irf_periods = int(ctx.get_param("irf_periods", 20))
        trend_param = ctx.get_param("trend", "c")

        # Lag selection
        progress_callback("Selecting VAR lag order", 15)

        preset_max = {"Fast": 4, "Balanced": 8, "Thorough": 16}
        max_lag = int(ctx.get_param("max_lag", preset_max.get(ctx.preset, 8)))
        max_lag = min(max_lag, (n // (k + 1)) - 1, n // 3)
        max_lag = max(max_lag, 1)

        ic = ctx.get_param("ic", "aic")

        fixed_lag = ctx.get_param("lag")
        if fixed_lag is not None:
            p = int(fixed_lag)
        else:
            import pandas as pd
            df = pd.DataFrame(stacked, columns=names)
            with _warnings.catch_warnings():
                _warnings.simplefilter("ignore")
                var_model = VAR(df, missing="drop")
                try:
                    lag_select = var_model.select_order(maxlags=max_lag, trend=trend_param)
                    p = getattr(lag_select, ic, None)
                    if p is None or p == 0:
                        p = lag_select.aic
                    if p == 0:
                        p = 1
                except Exception:
                    p = min(2, max_lag)
                    warn_list.append(f"Automatic lag selection failed. Using p={p}.")

        progress_callback(f"Fitting VAR({p})", 30)

        import pandas as pd
        df = pd.DataFrame(stacked, columns=names)

        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            model = VAR(df)
            try:
                fit = model.fit(maxlags=p, trend=trend_param)
            except np.linalg.LinAlgError:
                warn_list.append("Singular matrix. Trying with 'n' trend.")
                fit = model.fit(maxlags=p, trend="n")

        progress_callback("Generating forecasts", 55)

        # Forecasts
        fc = fit.forecast(stacked[-p:], steps=horizon)
        fc_rows = []
        for i in range(horizon):
            row = [n + i + 1]
            for j in range(k):
                row.append(round(float(fc[i, j]), 6))
            fc_rows.append(row)
        fc_table = make_table(
            "VAR Forecast",
            ["Step"] + names,
            fc_rows,
        )

        # Impulse Response Function (orthogonalized via Cholesky).
        # The Cholesky factorization depends on the order of variables
        # in the input, so the choice of ordering is a structural
        # assumption the user is making: variable 1 can contemporaneously
        # affect variables 2..k; variable 2 can contemporaneously affect
        # 3..k but NOT 1; etc. This is the standard recursive identification.
        # We pin the ordering to the user's selection order (names[]) and
        # surface a warning so the user knows the output is ordering-sensitive.
        progress_callback("Computing impulse responses", 65)
        warn_list.append(
            "Impulse responses and FEVD are orthogonalized using a Cholesky "
            f"decomposition with ordering = {list(names)}. This is an identifying "
            "assumption: the first-listed variable can contemporaneously affect "
            "all others, but not vice versa. Re-running with a different series "
            "order will give different IRF and FEVD numbers."
        )
        try:
            irf = fit.irf(irf_periods)
            # Use orthogonalized IRFs (orth_irfs) so they're consistent
            # with the Cholesky-based FEVD reported below. The raw
            # `irfs` attribute contains non-orthogonalized responses,
            # which don't correspond to interpretable "shocks."
            irf_data = getattr(irf, "orth_irfs", None)
            if irf_data is None:
                irf_data = irf.irfs  # fallback for older statsmodels
            irf_rows = []
            for t in range(min(irf_periods + 1, irf_data.shape[0])):
                for shock_idx in range(k):
                    for resp_idx in range(k):
                        irf_rows.append([
                            t,
                            names[shock_idx],
                            names[resp_idx],
                            round(float(irf_data[t, resp_idx, shock_idx]), 6),
                        ])
            irf_table = make_table(
                "Impulse Response Function (Orthogonalized)",
                ["Period", "Shock", "Response", "IRF"],
                irf_rows,
            )
        except Exception as e:
            irf_table = make_table("Impulse Response Function", ["Note"], [["IRF computation failed: " + str(e)]])
            warn_list.append(f"IRF computation failed: {e}")

        # Forecast Error Variance Decomposition
        progress_callback("Variance decomposition", 75)
        try:
            fevd = fit.fevd(irf_periods)
            fevd_rows = []
            for var_idx in range(k):
                decomp = fevd.decomp[var_idx]  # shape: (periods, k)
                for t in range(decomp.shape[0]):
                    row = [names[var_idx], t + 1]
                    for src_idx in range(k):
                        row.append(round(float(decomp[t, src_idx]) * 100, 2))
                    fevd_rows.append(row)
            fevd_table = make_table(
                "Forecast Error Variance Decomposition (%)",
                ["Variable", "Period"] + [f"Due to {n}" for n in names],
                fevd_rows,
            )
        except Exception as e:
            fevd_table = make_table("FEVD", ["Note"], [["FEVD computation failed: " + str(e)]])
            warn_list.append(f"FEVD computation failed: {e}")

        # Model summary table
        progress_callback("Building output", 85)
        aic = float(fit.aic)
        bic = float(fit.bic)
        fpe = float(fit.fpe) if hasattr(fit, 'fpe') else None

        # Companion-matrix stability: max root modulus. statsmodels VAR's
        # ``fit.roots`` returns the inverse companion-matrix eigenvalues,
        # so max|eig| = 1/min|root|. Stable iff < 1.0. Surfaces as a
        # user-visible fact in the Model Summary and as an audit field for
        # the interpretation spec to route on.
        try:
            roots = fit.roots
            min_abs_root = float(min(abs(r) for r in roots))
            max_root_modulus = (1.0 / min_abs_root) if min_abs_root > 0 else float("inf")
        except Exception:
            max_root_modulus = None

        summary_rows = [
            ["VAR Order (p)", p],
            ["Variables", k],
            ["Observations (effective)", fit.nobs],
            ["AIC", round(aic, 4)],
            ["BIC", round(bic, 4)],
        ]
        if max_root_modulus is not None:
            summary_rows.append(
                ["Max Companion-Root Modulus", round(max_root_modulus, 4)]
            )
        if fpe is not None:
            summary_rows.append(["FPE", round(fpe, 6)])
        summary_rows.append(["Trend", trend_param])
        summary_rows.append(["Forecast Horizon", horizon])
        summary_rows.append(["IRF Periods", irf_periods])

        summary_table = make_table("Model Summary", ["Metric", "Value"], summary_rows)

        # Coefficient table
        coef_rows = []
        for eq_name in names:
            params = fit.params[eq_name] if eq_name in fit.params.columns else None
            if params is not None:
                for param_name, value in params.items():
                    coef_rows.append([eq_name, str(param_name), round(float(value), 6)])
        coef_table = make_table(
            "Coefficients",
            ["Equation", "Parameter", "Estimate"],
            coef_rows,
        )

        # Granger causality summary (quick check)
        gc_rows = []
        if ctx.preset in ("Balanced", "Thorough"):
            try:
                for caused in names:
                    for causing in names:
                        if caused != causing:
                            test = fit.test_causality(caused, [causing], kind="f", signif=0.05)
                            gc_rows.append([
                                causing, caused,
                                round(float(test.test_statistic), 4),
                                round(float(test.pvalue), 6),
                                "Yes" if test.pvalue < 0.05 else "No",
                            ])
            except Exception:
                pass

        # ENG-EXT-MULTIVARIATE-001 M1 — IRF confidence bands (ADDITIVE).
        # Parametric Gaussian Monte-Carlo error bands around the
        # orthogonalized point IRF: simulate `repl` datasets from the fitted
        # VAR (Gaussian innovations), refit each, take the signif/2 &
        # 1-signif/2 percentiles. Uses the in-engine `_mc_irf_bands` helper
        # (DISTINCT per-replication seeds derived from ctx.seed) rather than
        # statsmodels `errband_mc`, which has a seed bug that collapses the
        # band to zero width (see the helper docstring). Preset-gated
        # (Balanced/Thorough only; Fast skips — MC bootstrap is expensive)
        # and deterministic in ctx.seed. Computed LAST (after every
        # deterministic output above) so the band RNG cannot perturb any
        # existing result — the point-IRF / FEVD tables are byte-identical;
        # the band table is a purely additive output.
        irf_band_table = None
        irf_band_signif = 0.05
        irf_band_repl = {"Balanced": 500, "Thorough": 2000}.get(ctx.preset, 0)
        irf_band_seed = int(ctx.seed)
        irf_band_computed = False
        if irf_band_repl > 0:
            progress_callback("Bootstrapping IRF confidence bands", 80)
            try:
                band_irf = fit.irf(irf_periods)
                lower, upper = _mc_irf_bands(
                    fit, irf_periods, irf_band_repl,
                    irf_band_signif, irf_band_seed, orth=True,
                )
                band_point = getattr(band_irf, "orth_irfs", None)
                if band_point is None:
                    band_point = band_irf.irfs
                band_rows = []
                n_band_t = min(irf_periods + 1, lower.shape[0])
                for t in range(n_band_t):
                    for shock_idx in range(k):
                        for resp_idx in range(k):
                            band_rows.append([
                                t,
                                names[shock_idx],
                                names[resp_idx],
                                round(float(band_point[t, resp_idx, shock_idx]), 6),
                                round(float(lower[t, resp_idx, shock_idx]), 6),
                                round(float(upper[t, resp_idx, shock_idx]), 6),
                            ])
                irf_band_table = make_table(
                    "Impulse Response Function — Confidence Bands",
                    ["Period", "Shock", "Response", "IRF", "Lower", "Upper"],
                    band_rows,
                )
                irf_band_computed = True
                warn_list.append(
                    f"IRF {int((1 - irf_band_signif) * 100)}% confidence bands "
                    f"computed via Monte-Carlo bootstrap ({irf_band_repl} "
                    f"replications, seed={irf_band_seed}). Bands are around the "
                    "orthogonalized (Cholesky) point IRF and inherit the same "
                    "ordering assumption."
                )
            except Exception as e:
                warn_list.append(f"IRF confidence-band computation failed: {e}")
                irf_band_computed = False

        # ENG-EXT-MULTIVARIATE-001 M3a — Blanchard–Quah SVAR identification
        # (ADDITIVE; the scheme-selector pattern). Default
        # svar_identification="cholesky" leaves the existing output
        # byte-identical (this branch not entered); "blanchard_quah" ADDS
        # structural-identification tables (B0 / long-run impact / structural
        # IRF / structural FEVD) alongside the UNCHANGED Cholesky IRF + bands +
        # FEVD. This scheme-selector + structural-output structure is the
        # pattern M3c (proxy) + M3b (sign-restriction) reuse.
        svar_identification = str(ctx.get_param("svar_identification", "cholesky"))
        bq_tables = []
        bq_computed = False
        if svar_identification == "blanchard_quah":
            progress_callback("Blanchard-Quah identification", 88)
            try:
                B0, lrim = _blanchard_quah_b0(fit)
                shock_cols = [f"Shock {j + 1}" for j in range(k)]
                bq_tables.append(make_table(
                    "Structural Impact Matrix (Blanchard-Quah)",
                    ["Variable"] + shock_cols,
                    [[names[i]] + [round(float(B0[i, j]), 6) for j in range(k)]
                     for i in range(k)],
                ))
                bq_tables.append(make_table(
                    "Long-Run Impact Matrix (Blanchard-Quah)",
                    ["Variable"] + shock_cols,
                    [[names[i]] + [round(float(lrim[i, j]), 6) for j in range(k)]
                     for i in range(k)],
                ))
                # Structural IRF: Θ_h = Φ_h @ B0 (Φ = reduced-form MA rep).
                Phi = np.asarray(fit.ma_rep(maxn=irf_periods), dtype=np.float64)
                Theta = np.einsum("hrs,sc->hrc", Phi, B0)  # [h, resp, struct-shock]
                sirf_rows = []
                for t in range(Theta.shape[0]):
                    for shock_idx in range(k):
                        for resp_idx in range(k):
                            sirf_rows.append([
                                t, f"Shock {shock_idx + 1}", names[resp_idx],
                                round(float(Theta[t, resp_idx, shock_idx]), 6),
                            ])
                bq_tables.append(make_table(
                    "Structural IRF (Blanchard-Quah)",
                    ["Period", "Shock", "Response", "IRF"], sirf_rows,
                ))
                # Structural FEVD: cumulative squared structural IRF, normalized
                # per response variable per horizon.
                sfevd_rows = []
                contrib = np.zeros((k, k))
                for h in range(min(irf_periods, Theta.shape[0])):
                    contrib = contrib + Theta[h] ** 2
                    rt = contrib.sum(axis=1, keepdims=True)
                    rt = np.where(rt < 1e-300, 1.0, rt)
                    share = contrib / rt
                    for var_idx in range(k):
                        sfevd_rows.append(
                            [names[var_idx], h + 1]
                            + [round(float(share[var_idx, s]) * 100, 2) for s in range(k)]
                        )
                bq_tables.append(make_table(
                    "Structural FEVD (Blanchard-Quah) (%)",
                    ["Variable", "Period"] + [f"Due to Shock {j + 1}" for j in range(k)],
                    sfevd_rows,
                ))
                bq_computed = True
                warn_list.append(
                    "Blanchard-Quah long-run-restriction SVAR identification "
                    "applied: structural shocks are identified by restricting "
                    "the long-run cumulative impact matrix to lower-triangular "
                    "(shock j has no permanent effect on variable i for i<j)."
                )
            except Exception as e:
                warn_list.append(f"Blanchard-Quah identification failed: {e}")
                bq_computed = False

        # ENG-EXT-MULTIVARIATE-001 M3c — Proxy / IV-SVAR identification
        # (ADDITIVE; reuses the M3a scheme-selector pattern). Identifies ONE
        # structural shock via an external instrument (proxy) correlated with
        # the target shock + uncorrelated with the others. No usable
        # cross-package library exists → validated by self-parity + a
        # load-bearing instrument-relevance functional check.
        proxy_tables = []
        proxy_computed = False
        proxy_instrument_corr = None
        if svar_identification == "proxy":
            progress_callback("Proxy/IV-SVAR identification", 88)
            instrument = ctx.get_param("proxy_instrument")
            normalize_var = int(ctx.get_param("proxy_normalize_var", 0))
            if instrument is None:
                warn_list.append(
                    "Proxy/IV-SVAR identification requested but no "
                    "'proxy_instrument' provided; skipping."
                )
            else:
                try:
                    b1, eps_hat, relevance = _proxy_svar(
                        fit, instrument, normalize_var=normalize_var,
                    )
                    proxy_instrument_corr = round(float(relevance), 6)
                    proxy_tables.append(make_table(
                        "Structural Impact Vector (Proxy-SVAR)",
                        ["Variable", "Impact"],
                        [[names[i], round(float(b1[i]), 6)] for i in range(k)],
                    ))
                    Phi = np.asarray(fit.ma_rep(maxn=irf_periods), dtype=np.float64)
                    sirf_rows = []
                    for t in range(Phi.shape[0]):
                        theta_t = Phi[t] @ b1  # (k,) response to the target shock
                        for resp_idx in range(k):
                            sirf_rows.append([
                                t, names[resp_idx], round(float(theta_t[resp_idx]), 6),
                            ])
                    proxy_tables.append(make_table(
                        "Structural IRF (Proxy-SVAR)",
                        ["Period", "Response", "IRF"], sirf_rows,
                    ))
                    relevant = abs(float(relevance)) >= 0.2
                    proxy_tables.append(make_table(
                        "Proxy Instrument Relevance",
                        ["Metric", "Value"],
                        [
                            ["Corr(identified shock, instrument)",
                             round(float(relevance), 6)],
                            ["Relevant (|corr| >= 0.2)", "Yes" if relevant else "No"],
                        ],
                    ))
                    proxy_computed = True
                    warn_list.append(
                        "Proxy/IV-SVAR identification applied: the target "
                        "structural shock is identified via the external "
                        "instrument (impact column ∝ Cov(residuals, "
                        "instrument), normalized to unit impact on "
                        f"'{names[normalize_var]}'). Instrument-relevance "
                        f"corr = {round(float(relevance), 4)}."
                    )
                    if not relevant:
                        warn_list.append(
                            "WARNING: weak instrument — |corr| < 0.2; the "
                            "proxy identification may be unreliable."
                        )
                except Exception as e:
                    warn_list.append(f"Proxy/IV-SVAR identification failed: {e}")
                    proxy_computed = False

        tables = [fc_table, summary_table, coef_table, irf_table, fevd_table]
        if irf_band_table is not None:
            tables.append(irf_band_table)
        tables.extend(bq_tables)
        tables.extend(proxy_tables)
        if gc_rows:
            gc_table = make_table(
                "Granger Causality (from VAR)",
                ["Causing", "Caused", "F-Statistic", "P-Value", "Significant"],
                gc_rows,
            )
            tables.append(gc_table)

        # Plain English
        plain = (
            f"VAR({p}) model fitted to {k} series: {', '.join(names)} "
            f"({fit.nobs} effective observations). AIC={aic:.2f}. "
            f"{horizon}-step forecasts and {irf_periods}-period impulse responses produced."
        )
        if gc_rows:
            sig_pairs = [(r[0], r[1]) for r in gc_rows if r[4] == "Yes"]
            if sig_pairs:
                plain += " Significant Granger causality: " + "; ".join(
                    f"{a} -> {b}" for a, b in sig_pairs
                ) + "."

        if irf_band_computed:
            plain += (
                f" {int((1 - irf_band_signif) * 100)}% Monte-Carlo confidence "
                "bands accompany the impulse responses."
            )

        charting = (
            "Multi-panel line chart: one panel per variable showing original, "
            "fitted, and forecast. Separate IRF chart: grid of impulse-response "
            "plots, each with its confidence band (lower/upper) shaded around "
            "the point response. FEVD stacked area chart."
        )

        progress_callback("Done", 100)

        interp = build_interpretation("var_model", {
            "variable_names": names,
            "var_order": p,
            "n_variables": k,
            "aic": float(aic),
            "bic": float(bic),
            "ic_used": str(ic),
            "max_root_modulus": max_root_modulus,
            "granger_within_var": gc_rows,
            "n_obs": int(fit.nobs),
        })

        return make_response(
            ctx,
            tables=tables,
            plain_english_summary=plain,
            warnings=warn_list,
            charting_suggestions=charting,
            interpretation=interp,
            audit_fields={
                "var_order": p,
                "n_variables": k,
                "variable_names": names,
                "aic": round(aic, 4),
                "bic": round(bic, 4),
                "ic_used": ic,
                "horizon": horizon,
                "irf_periods": irf_periods,
                "trend": trend_param,
                "max_root_modulus": (round(max_root_modulus, 4)
                                     if max_root_modulus is not None else None),
                "granger_within_var": gc_rows,
                # ENG-EXT-MULTIVARIATE-001 M1 — IRF confidence-band metadata.
                "irf_band_computed": bool(irf_band_computed),
                "irf_band_signif": float(irf_band_signif),
                "irf_band_repl": int(irf_band_repl),
                "irf_band_method": "montecarlo_gaussian_distinct_seed",
                "irf_band_seed": int(irf_band_seed),
                # ENG-EXT-MULTIVARIATE-001 M3a — SVAR identification scheme.
                "svar_identification": svar_identification,
                "bq_computed": bool(bq_computed),
                # ENG-EXT-MULTIVARIATE-001 M3c — proxy/IV-SVAR.
                "proxy_computed": bool(proxy_computed),
                "proxy_instrument_corr": proxy_instrument_corr,
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"VAR model failed: {e}",
            error_fixes=[
                "Ensure all series are numeric and the same length.",
                "Provide at least 2 series for VAR.",
                "Reduce max_lag if the series is short.",
                "Check for constant or collinear series.",
            ],
        )
