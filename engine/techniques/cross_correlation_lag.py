"""
Raw Cross-Correlation Lag Finder for Time Series Lab.

Computes the sample cross-correlation function (CCF) between two series
at various lags to identify lead/lag relationships. Unlike the prewhitened
CCF, this is the simple (raw) approach that does NOT remove autocorrelation
first -- useful as a quick exploratory tool or when prewhitening is undesired.
"""

import numpy as np
from scipy.stats import norm

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    dropna_aligned,
    bartlett_effective_n,
    format_significance_disclosure,
)


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Compute raw cross-correlation between two series across lags.

    Requires 2 series: first = X, second = Y.
    Positive lag means X leads Y. Negative lag means Y leads X.

    Parameters (via ctx.params)
    ---------------------------
    max_lag : int, optional
        Maximum lag to evaluate (positive and negative). Default depends on preset.
    significance_level : float, optional
        Alpha for Bartlett confidence bands. Default 0.05.
    normalize : bool, optional
        If True (default), normalize CCF so lag-0 auto-correlations are 1.
    """
    try:
        progress_callback("Validating inputs", 5)

        ctx.validate_min_series(2)
        all_series = ctx.get_all_series()
        warn_list = []
        if len(all_series) > 2:
            ignored = [s[0] for s in all_series[2:]]
            warn_list.append(
                f"Cross-correlation is a pairwise technique. Used "
                f"'{all_series[0][0]}' and '{all_series[1][0]}'; ignored "
                f"{len(ignored)} additional series: {', '.join(ignored)}."
            )
        x_name, x_vals = all_series[0]
        y_name, y_vals = all_series[1]

        if len(x_vals) != len(y_vals):
            return make_error_response(
                ctx,
                f"Series lengths differ: '{x_name}' has {len(x_vals)}, "
                f"'{y_name}' has {len(y_vals)}. They must be equal.",
                error_fixes=["Select two columns of the same length."],
            )

        x_clean, y_clean = dropna_aligned(x_vals, y_vals)
        n_dropped = len(x_vals) - len(x_clean)
        if n_dropped > 0:
            warn_list.append(f"{n_dropped} rows dropped due to missing values.")

        n = len(x_clean)
        if n < 8:
            return make_error_response(
                ctx,
                f"Only {n} valid observations. Need at least 8 for cross-correlation.",
                error_fixes=["Provide longer series."],
            )

        preset_defaults = {"Fast": 15, "Balanced": 30, "Thorough": 60}
        max_lag = ctx.get_param("max_lag")
        if max_lag is None:
            max_lag = preset_defaults.get(ctx.preset, 30)
        max_lag = int(max_lag)
        max_lag = min(max_lag, n // 3)

        significance = ctx.get_param("significance_level", 0.05)
        normalize = ctx.get_param("normalize", True)

        progress_callback("Computing cross-correlations", 20)

        x_dm = x_clean - np.mean(x_clean)
        y_dm = y_clean - np.mean(y_clean)

        # Normalizing denominators
        sx = np.sqrt(np.sum(x_dm ** 2))
        sy = np.sqrt(np.sum(y_dm ** 2))
        denom = sx * sy if normalize and sx > 1e-15 and sy > 1e-15 else n

        if sx < 1e-15 or sy < 1e-15:
            return make_error_response(
                ctx,
                "One or both series have zero variance. Cross-correlation is undefined.",
                error_fixes=["Ensure both series have varying values."],
            )

        # Compute CCF for lags from -max_lag to +max_lag
        # ccf(lag=k) = sum(x[t]*y[t+k]) / denom
        # Positive k: X leads Y (X[t] correlates with Y[t+k])
        # Negative k: Y leads X
        ccf_vals = np.zeros(2 * max_lag + 1)
        lags = np.arange(-max_lag, max_lag + 1)

        for idx, k in enumerate(lags):
            if k >= 0:
                ccf_vals[idx] = np.sum(x_dm[:n - k] * y_dm[k:]) / denom if k < n else 0.0
            else:
                ccf_vals[idx] = np.sum(x_dm[-k:] * y_dm[:n + k]) / denom if -k < n else 0.0

        progress_callback("Identifying significant lags", 60)

        # Bartlett confidence band. The naive ±z/sqrt(n) formula assumes
        # white-noise inputs; for autocorrelated time series it
        # systematically understates the band width. Apply the Bartlett
        # effective-n correction: n_eff = n / (1 + 2*sum(rho_x * rho_y)),
        # then use ±z/sqrt(n_eff). Disclose both in the audit sheet.
        z = norm.ppf(1.0 - significance / 2.0)
        conf_band_naive = z / np.sqrt(n)
        n_eff, ac_inflation = bartlett_effective_n(x_clean, y_clean)
        ac_corrected = ac_inflation >= 1.05
        if ac_corrected:
            conf_band = z / np.sqrt(n_eff)
        else:
            conf_band = conf_band_naive
        if ac_corrected and ac_inflation >= 1.5:
            warn_list.append(
                f"Autocorrelation inflation factor {ac_inflation:.1f}x "
                f"(effective n ≈ {n_eff:.0f} vs nominal {n}). Significance "
                f"band widened accordingly. Naive band would have been "
                f"±{conf_band_naive:.4f}; AC-corrected is ±{conf_band:.4f}."
            )

        # Build CCF table
        ccf_rows = []
        best_lag = 0
        best_abs = 0.0
        best_val = 0.0

        for idx, k in enumerate(lags):
            val = ccf_vals[idx]
            sig = abs(val) > conf_band
            ccf_rows.append([
                int(k),
                round(float(val), 6),
                round(float(abs(val)), 6),
                "Yes" if sig else "No",
            ])
            if abs(val) > best_abs:
                best_abs = abs(val)
                best_val = val
                best_lag = int(k)

        ccf_table = make_table(
            "Cross-Correlation Function",
            ["Lag", "CCF", "|CCF|", "Significant"],
            ccf_rows,
        )

        # Top significant lags
        sig_lags = [(int(lags[i]), ccf_vals[i]) for i in range(len(lags)) if abs(ccf_vals[i]) > conf_band]
        sig_lags.sort(key=lambda x: abs(x[1]), reverse=True)
        top_n = min(10, len(sig_lags))
        top_rows = []
        for lag, val in sig_lags[:top_n]:
            direction = _direction_label(lag, x_name, y_name)
            top_rows.append([lag, round(val, 6), direction])
        top_table = make_table(
            "Top Significant Lags",
            ["Lag", "CCF", "Interpretation"],
            top_rows,
        )

        # Summary
        summary_rows = [
            ["Series X", x_name],
            ["Series Y", y_name],
            ["Observations", n],
            ["Max Lag Tested", max_lag],
            ["Optimal Lag", best_lag],
            ["CCF at Optimal Lag", round(best_val, 6)],
            [f"Bartlett {int((1 - significance) * 100)}% Band", f"+/- {round(conf_band, 4)}"],
            ["Significant Lags (count)", len(sig_lags)],
            ["Normalized", normalize],
        ]
        summary_table = make_table("Summary", ["Field", "Value"], summary_rows)

        # Plain English
        n_sig = len(sig_lags)
        if n_sig == 0:
            plain = (
                f"No significant cross-correlations between '{x_name}' and '{y_name}' "
                f"at any lag from -{max_lag} to +{max_lag}. "
                "The series do not exhibit a detectable linear lead/lag relationship."
            )
        elif best_lag > 0:
            plain = (
                f"'{x_name}' leads '{y_name}' by approximately {best_lag} period(s) "
                f"(CCF={best_val:.4f}). "
                f"{n_sig} lag(s) exceeded the significance threshold."
            )
        elif best_lag < 0:
            plain = (
                f"'{y_name}' leads '{x_name}' by approximately {abs(best_lag)} period(s) "
                f"(CCF={best_val:.4f}). "
                f"{n_sig} lag(s) exceeded the significance threshold."
            )
        else:
            plain = (
                f"'{x_name}' and '{y_name}' are most strongly correlated at lag 0 "
                f"(CCF={best_val:.4f}), indicating contemporaneous co-movement. "
                f"{n_sig} lag(s) exceeded the significance threshold."
            )

        if n_sig > 0 and not ctx.get_param("prewhitened", False):
            plain += (
                " Note: raw CCF may show inflated correlations due to autocorrelation "
                "within each series. For a cleaner estimate, use the Prewhitened CCF technique."
            )

        charting = (
            "Stem/bar chart of CCF values from -max_lag to +max_lag, "
            f"with horizontal dashed lines at +/- {conf_band:.4f} (Bartlett band). "
            "Highlight the optimal lag."
        )

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=[ccf_table, top_table, summary_table],
            plain_english_summary=plain,
            warnings=warn_list,
            charting_suggestions=charting,
            audit_fields={
                "x_series": x_name,
                "y_series": y_name,
                "pair_used": [x_name, y_name],
                "pairs_ignored": [s[0] for s in all_series[2:]],
                "max_lag": max_lag,
                "optimal_lag": best_lag,
                "ccf_at_optimal": round(best_val, 6),
                "bartlett_band": round(conf_band, 4),
                "bartlett_band_naive_reference": round(conf_band_naive, 4),
                "ac_inflation_factor": round(float(ac_inflation), 2),
                "n_significant": n_sig,
                "n_valid": n,
                "normalized": normalize,
                **format_significance_disclosure(
                    test_name="Bartlett white-noise band",
                    critical_value_formula=(
                        f"±z(1-α/2)/sqrt(n_eff) with n_eff={n_eff:.1f} from "
                        f"Bartlett AC adjustment"
                        if ac_corrected else
                        f"±z(1-α/2)/sqrt(n) = ±{conf_band:.4f}"
                    ),
                    ac_corrected=bool(ac_corrected),
                    effective_n=float(n_eff) if ac_corrected else None,
                ),
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Cross-correlation failed: {e}",
            error_fixes=[
                "Ensure both series are numeric and the same length.",
                "Check for excessive missing values.",
                "Reduce max_lag if the series is very short.",
            ],
        )


def _direction_label(lag, x_name, y_name):
    """Human-readable direction."""
    if lag > 0:
        return f"{x_name} leads {y_name} by {lag}"
    elif lag < 0:
        return f"{y_name} leads {x_name} by {abs(lag)}"
    else:
        return "Contemporaneous"
