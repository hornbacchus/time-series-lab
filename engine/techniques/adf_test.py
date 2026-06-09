"""
Augmented Dickey-Fuller (ADF) unit root test for Time Series Lab.

Default behavior on the ribbon path is a **joint stationarity triage**: ADF +
KPSS + Phillips-Perron are run together and a single joint verdict is
emitted. ADF alone rejects the unit-root null, which is not the same as
concluding the series is stationary — only the joint rubric (ADF null
rejected AND KPSS stationarity null not rejected) supports that conclusion.

UDF callers (``TSL_ADF`` in Excel) default to single-test mode for
backward compatibility; the distinction is detected via ``ctx.run_id``
prefix (``udf_*`` → single, ``pane_*`` / anything else → triage). The
caller can always override with ``params['triage'] = True`` or ``False``.

Specification transparency (P.1): the regression form (c / ct / ctt / n),
the Schwert-rule max-lag bound, and the actual AIC-selected lag are
surfaced in the user-visible Results sheet, not only the audit sheet.
Summary language (P.2) says "unit root rejected" / "unit root not
rejected" — never "is stationary", which is a triage-only conclusion.
"""

import numpy as np
from statsmodels.tsa.stattools import adfuller

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    format_significance_disclosure,
    order_critical_values,
)

# Interpretation layer (Prompt A). Import pulls in the registered spec
# for 'adf_test' via side-effect imports in
# ``interpretation.registry``.
try:
    from interpretation import build_interpretation  # type: ignore
except Exception:
    # Defensive: if the interpretation module is unavailable for any
    # reason (installation skew, circular import during a partial
    # deployment), fall back to returning None so make_response omits
    # the key and the C# writer renders the sheet as before.
    def build_interpretation(technique_id, results):  # type: ignore
        return None


_REGRESSION_LABEL = {
    "c":   "constant only",
    "ct":  "constant + linear trend",
    "ctt": "constant + linear + quadratic trend",
    "n":   "no deterministic term",
    "nc":  "no deterministic term",
}


def _schwert_bound(n: int) -> int:
    """Schwert's rule: max_lag = floor(12 * (T/100)^(1/4)). Macro-standard
    upper bound for ADF lag selection."""
    if n < 12:
        return 1
    return int(np.floor(12.0 * (n / 100.0) ** 0.25))


def _prepare_series(values: np.ndarray, name: str, warnings: list) -> np.ndarray:
    """Strip edge NaN and linearly interpolate interior NaN."""
    first_valid = 0
    while first_valid < len(values) and np.isnan(values[first_valid]):
        first_valid += 1
    last_valid = len(values) - 1
    while last_valid >= 0 and np.isnan(values[last_valid]):
        last_valid -= 1
    if first_valid > last_valid:
        return np.array([])
    trimmed = values[first_valid:last_valid + 1].copy()
    nan_count = int(np.isnan(trimmed).sum())
    if nan_count > 0:
        nans = np.where(np.isnan(trimmed))[0]
        valid = np.where(~np.isnan(trimmed))[0]
        if len(valid) >= 2:
            trimmed[nans] = np.interp(nans, valid, trimmed[valid])
            warnings.append(
                f"'{name}': {nan_count} interior NaN values linearly "
                "interpolated for ADF test."
            )
        else:
            return trimmed[~np.isnan(trimmed)]
    return trimmed


def _detect_trend(clean: np.ndarray, t_threshold: float = 2.0) -> tuple:
    """Simple trend heuristic: regress y on linear time and check |t-stat|.

    Used for the advisory note in P.6 — if the user is running
    ``regression='c'`` on an apparently trending series, the summary gets
    a "consider regression='ct'" note. Never auto-switches the
    specification; disclosure only.

    Returns ``(is_trending: bool, t_stat: float)``.
    """
    n = len(clean)
    if n < 10:
        return False, 0.0
    t = np.arange(n, dtype=float)
    t_c = t - t.mean()
    y_c = clean - clean.mean()
    denom = float(np.sum(t_c ** 2))
    if denom <= 0:
        return False, 0.0
    slope = float(np.sum(t_c * y_c)) / denom
    resid = y_c - slope * t_c
    dof = max(1, n - 2)
    sigma2 = float(np.sum(resid ** 2)) / dof
    se_slope = float(np.sqrt(sigma2 / denom)) if denom > 0 else 0.0
    if se_slope <= 0:
        return False, 0.0
    t_stat = slope / se_slope
    return abs(t_stat) > t_threshold, float(t_stat)


def _run_adf_single(clean: np.ndarray, regression: str, max_lag_param,
                    autolag: str) -> dict:
    """Run ADF on one prepared series. Returns a raw-results dict used by
    both the single-test path and the triage path in this file.

    Keys:
        stat, pvalue, used_lag, nobs, critical_values_ordered (list of
        (level, value, rejects_H0) tuples), regression, regression_label,
        schwert_bound, autolag, decision_h0_rejected, error (str or None).
    """
    out = {
        "stat": None, "pvalue": None, "used_lag": None, "nobs": None,
        "critical_values_ordered": [], "regression": regression,
        "regression_label": _REGRESSION_LABEL.get(regression, regression),
        "schwert_bound": None, "autolag": autolag,
        "decision_h0_rejected": None, "error": None,
    }
    n = len(clean)
    if n < 12:
        out["error"] = f"Too few observations ({n}; need ≥ 12)"
        return out
    schwert = _schwert_bound(n)
    out["schwert_bound"] = schwert
    # If the user didn't pin max_lag, apply the Schwert bound. Autolag
    # selects the best lag via AIC within [0, schwert].
    if max_lag_param is None:
        maxlag = schwert
    else:
        maxlag = int(max_lag_param)
    try:
        adf_stat, p_value, used_lag, nobs, crit_vals, ic_best = adfuller(
            clean, maxlag=maxlag, regression=regression, autolag=autolag,
        )
    except Exception as e:
        out["error"] = str(e)
        return out
    ordered = order_critical_values(crit_vals)
    out["stat"] = float(adf_stat)
    out["pvalue"] = float(p_value)
    out["used_lag"] = int(used_lag)
    out["nobs"] = int(nobs)
    out["critical_values_ordered"] = [
        (lvl, cv, adf_stat < cv) for (lvl, cv) in ordered
    ]
    return out


def _summary_adf(name: str, single: dict, significance: float,
                 trending: bool, t_stat: float) -> str:
    """Build the ADF-only single-test plain-English summary per P.2."""
    if single.get("error"):
        return f"'{name}': ADF test failed ({single['error']})."
    p = single["pvalue"]
    stat = single["stat"]
    lag = single["used_lag"]
    reg = single["regression"]
    reg_label = single["regression_label"]
    rejected = p < significance
    if rejected:
        verdict = (
            f"'{name}': unit root rejected at the {significance*100:.0f}% "
            f"level (ADF={stat:.4f}, p={p:.4f}, regression='{reg}' / "
            f"{reg_label}, lag={lag})."
        )
    else:
        verdict = (
            f"'{name}': unit root not rejected at the {significance*100:.0f}% "
            f"level (ADF={stat:.4f}, p={p:.4f}, regression='{reg}' / "
            f"{reg_label}, lag={lag}). Consider differencing."
        )
    if trending and reg == "c":
        verdict += (
            f" Note: series appears trending (|t|={abs(t_stat):.2f} on a "
            f"linear time regressor). Consider re-running with "
            f"regression='ct'."
        )
    return verdict


def _joint_verdict(adf_rejected, kpss_rejected) -> tuple:
    """Return (verdict_label, recommendation) per the P.3 rubric.

    ADF null = unit root. KPSS null = stationarity.
    """
    if adf_rejected and not kpss_rejected:
        return (
            "STATIONARY",
            "Both tests agree: series looks stationary in levels.",
        )
    if not adf_rejected and kpss_rejected:
        return (
            "UNIT ROOT (I(1))",
            "Both tests agree: differencing is appropriate before "
            "stationary modelling.",
        )
    if adf_rejected and kpss_rejected:
        return (
            "CONFLICTING",
            "Tests disagree — likely a structural break or near-unit-root "
            "process. Consider Zivot-Andrews (flagged future work) or "
            "splitting the sample.",
        )
    return (
        "INCONCLUSIVE",
        "Neither null is rejected — low test power on this sample. Consider "
        "a longer series, a different regression specification (e.g., 'ct' "
        "if trending), or the Phillips-Perron row for a tie-breaker.",
    )


def _is_triage_mode(ctx) -> bool:
    """Dispatch rule: honor explicit ``triage`` param if present; otherwise
    use ``ctx.run_id`` prefix. UDF path (`udf_*`) → single-test for
    backward compat; ribbon/pane path → triage."""
    explicit = ctx.get_param("triage", None)
    if explicit is not None:
        return bool(explicit)
    rid = str(ctx.run_id or "")
    return not rid.startswith("udf_")


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Augmented Dickey-Fuller unit-root test with optional joint-triage mode.

    Parameters (via ctx.params)
    ---------------------------
    regression : str, optional
        'c' (constant only, default), 'ct' (constant + trend),
        'ctt' (constant + linear + quadratic trend), 'n' (no constant).
    max_lag : int or None, optional
        Maximum lag. If omitted, Schwert's rule is applied:
        max_lag = floor(12 · (T/100)^(1/4)). Also sourced from the `max_lags`
        dialog control: the string "auto" (its default) -> auto-lag selection
        (Schwert + autolag, == omitting it); an int -> a fixed maxlag cap.
    autolag : str, optional
        'AIC' (default), 'BIC', 't-stat', or None.
    significance_level : float, optional
        P-value threshold. Default 0.05.
    triage : bool, optional
        Default: True for ribbon invocations, False for UDF invocations.
        When True, runs ADF + KPSS + PP jointly and emits a joint verdict.
        When False, runs ADF alone (backward-compat with single-test UDFs).
    """
    try:
        progress_callback("Validating inputs", 5)

        all_series = ctx.get_all_series()
        if not all_series:
            return make_error_response(
                ctx, "No series provided. Please select at least one data column.",
                error_fixes=["Select a column of numeric data in Excel."],
            )

        regression = ctx.get_param("regression", "c")
        # max_lag sourced from the `max_lags` dialog control (label "Max Lags",
        # default the STRING "auto"); precedence max_lag (THOROUGH granular int)
        # > max_lags (dialog) > None. The string "auto" is a SENTINEL for
        # auto-lag selection (Schwert bound + autolag) == the current default --
        # branch it HERE; never int-cast it downstream (_run_adf_single does
        # int(max_lag_param), and int("auto") raises ValueError). An int (or
        # int-string) sets a fixed maxlag cap.
        max_lag_param = ctx.get_param("max_lag", ctx.get_param("max_lags", None))
        if isinstance(max_lag_param, str):
            _ml = max_lag_param.strip().lower()
            if _ml in ("", "auto", "none"):
                max_lag_param = None
            else:
                try:
                    max_lag_param = int(_ml)
                except ValueError:
                    return make_error_response(
                        ctx,
                        f"max_lags must be 'auto' or an integer, got "
                        f"'{max_lag_param}'.",
                        error_fixes=[
                            "Use 'auto' (Schwert bound + auto-lag selection) "
                            "or a positive integer maximum lag.",
                        ],
                    )
        autolag_param = ctx.get_param("autolag", "AIC")
        if max_lag_param is not None and autolag_param is None:
            autolag = None
        else:
            autolag = autolag_param
        significance = float(ctx.get_param("significance_level", 0.05))

        # CAI Phase 2 Session 17 fix (F-ST-ADF-REGRESSION,
        # F-ST-ADF-AUTOLAG): explicit allowlist gates. Pre-fix,
        # invalid `regression` and `autolag` strings flowed into
        # statsmodels.adfuller, which raised ValueError that was
        # caught inside _run_adf_single and stored as a per-series
        # error — but the wrapper still returned status=success
        # with audit_fields recording the user's invalid value
        # and an error row in the table. Now: allowlist-reject
        # BEFORE entering the run path so the user gets a clear
        # error message instead of a "successful" run with no
        # actual test result.
        _REGRESSION_OPTS = ("c", "ct", "ctt", "n", "nc")
        if regression not in _REGRESSION_OPTS:
            return make_error_response(
                ctx,
                f"Unknown regression '{regression}'. Must be one "
                f"of: {', '.join(_REGRESSION_OPTS)}.",
                error_fixes=[
                    "Use 'c' (constant only; default), 'ct' "
                    "(constant + linear trend), 'ctt' (constant + "
                    "linear + quadratic trend), or 'n'/'nc' (no "
                    "deterministic term).",
                ],
            )
        _AUTOLAG_OPTS = ("AIC", "BIC", "t-stat", None)
        # Statsmodels accepts case-insensitive strings; normalize
        # for the allowlist check while preserving the original
        # value for downstream display.
        _autolag_check = (
            autolag.upper() if isinstance(autolag, str) and autolag.upper() in ("AIC", "BIC")
            else autolag.lower() if isinstance(autolag, str) and autolag.lower() == "t-stat"
            else autolag
        )
        if _autolag_check not in _AUTOLAG_OPTS:
            return make_error_response(
                ctx,
                f"Unknown autolag '{autolag}'. Must be one of: "
                "AIC, BIC, t-stat, or None.",
                error_fixes=[
                    "Use 'AIC' (default; Akaike information "
                    "criterion), 'BIC' (Bayesian information "
                    "criterion), 't-stat' (t-statistic-based "
                    "selection), or None (use max_lag directly).",
                ],
            )

        if _is_triage_mode(ctx):
            return _run_triage(
                ctx, progress_callback, all_series, regression, max_lag_param,
                autolag, significance,
            )
        return _run_single_test(
            ctx, progress_callback, all_series, regression, max_lag_param,
            autolag, significance,
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx, f"ADF test failed: {e}",
            error_fixes=[
                "Ensure the series is numeric.",
                "Check for constant or near-constant series (zero variance).",
                "Try a different regression type ('c', 'ct', or 'n').",
            ],
        )


def _run_single_test(ctx, progress_callback, all_series, regression,
                     max_lag_param, autolag, significance):
    """ADF-only path. Preserves UDF backward compatibility."""
    warnings = []
    result_rows = []
    all_summaries = []
    detail_tables = []
    # First successfully-fit series' facts — fed to build_interpretation
    # below. Multi-series runs still get one interpretation block (on the
    # first series); the per-series Summary sentences remain as before.
    first_interp_results = None

    progress_callback("Running ADF tests", 15)

    for idx, (name, values) in enumerate(all_series):
        pct = 15 + int(70 * (idx + 1) / len(all_series))
        progress_callback(f"Testing '{name}'", pct)

        clean = _prepare_series(values, name, warnings)
        trending, t_stat = _detect_trend(clean)
        single = _run_adf_single(clean, regression, max_lag_param, autolag)

        if single["error"] is not None:
            result_rows.append([
                name, None, None, None, None, None, regression,
                single.get("schwert_bound"), len(clean), single["error"],
            ])
            all_summaries.append(
                f"'{name}': {single['error']}."
            )
            continue

        rejected = single["pvalue"] < significance
        single["decision_h0_rejected"] = bool(rejected)
        decision = "Reject H0 (UR null)" if rejected else "Fail to reject H0"

        result_rows.append([
            name,
            round(single["stat"], 4),
            round(single["pvalue"], 6),
            single["used_lag"],
            single["nobs"],
            decision,
            f"{regression} ({single['regression_label']})",
            single["schwert_bound"],
            len(clean),
            "",
        ])

        cv_rows = [
            [lvl, round(cv, 4), "Yes" if rej else "No"]
            for (lvl, cv, rej) in single["critical_values_ordered"]
        ]
        detail_tables.append(make_table(
            f"Critical Values - {name}",
            ["Significance Level", "Critical Value", "Reject H0?"],
            cv_rows,
        ))

        all_summaries.append(_summary_adf(name, single, significance,
                                          trending, t_stat))

        if first_interp_results is None:
            first_interp_results = _build_interp_dict_single(
                name=name, single=single, regression=regression,
                significance=significance, trending=trending, t_stat=t_stat,
            )

    progress_callback("Building output", 90)

    main_table = make_table(
        "ADF Test Results",
        ["Series", "ADF Statistic", "P-Value", "Lags Used (AIC)", "N Obs",
         "Decision", "Regression", "Schwert Bound", "N Total", "Notes"],
        result_rows,
    )

    plain_english = (" ".join(all_summaries)
                     if all_summaries else "No test results produced.")

    charting = (
        "Table display with color coding: green where H0 is rejected "
        "(likely stationary), red/orange where not. Optionally a bar "
        "chart comparing ADF statistic to the 1%/5%/10% critical values."
    )

    progress_callback("Done", 100)

    interp = (
        build_interpretation("adf_test", first_interp_results)
        if first_interp_results is not None else None
    )

    return make_response(
        ctx,
        tables=[main_table] + detail_tables,
        plain_english_summary=plain_english,
        warnings=warnings,
        charting_suggestions=charting,
        interpretation=interp,
        audit_fields={
            "regression": regression,
            "regression_label": _REGRESSION_LABEL.get(regression, regression),
            "autolag": autolag,
            "max_lag_param": (int(max_lag_param)
                              if max_lag_param is not None else None),
            "schwert_bound_used": (
                _schwert_bound(len(all_series[0][1]))
                if max_lag_param is None else None
            ),
            "significance_level": significance,
            "n_series_tested": len(all_series),
            "mode": "single_test",
            **format_significance_disclosure(
                test_name="Augmented Dickey-Fuller (ADF)",
                critical_value_formula=(
                    "MacKinnon critical values via "
                    "statsmodels.tsa.stattools.adfuller; lag-augmented "
                    "regression with Schwert bound + AIC lag selection"
                ),
                ac_corrected=True,
            ),
        },
    )


def _build_interp_dict_single(*, name, single, regression, significance,
                              trending, t_stat) -> dict:
    """Convert an ADF per-series result into the interpretation spec's
    input dict. Isolates the naming translation so the spec layer can
    change fields without touching every call site."""
    cv_1 = cv_5 = None
    for lvl, cv, _rej in single.get("critical_values_ordered", []):
        if str(lvl).strip() == "1%":
            cv_1 = float(cv)
        elif str(lvl).strip() == "5%":
            cv_5 = float(cv)
    return {
        "mode": "single_test",
        "series_name": name,
        "adf_stat": float(single["stat"]),
        "p_value": float(single["pvalue"]),
        "regression": regression,
        "used_lag": int(single["used_lag"]),
        "schwert_bound": int(single["schwert_bound"]),
        "n_obs": int(single["nobs"]),
        "crit_1pct": cv_1,
        "crit_5pct": cv_5,
        "significance_level": float(significance),
        "trending": bool(trending),
        "t_stat_trend": float(t_stat),
        "decision_rejected": bool(single.get("decision_h0_rejected")),
    }


def _run_triage(ctx, progress_callback, all_series, regression,
                max_lag_param, autolag, significance):
    """Joint ADF + KPSS + PP triage. Single-series input expected; for
    multi-series, each series gets its own row in the triage table."""
    # Local imports so unit-test/UDF paths don't eagerly import arch/kpss.
    from techniques.kpss_test import _run_kpss_single
    from techniques.pp_test import _run_pp_single

    warnings = []
    triage_rows = []
    per_series_summaries = []
    detail_tables = []
    first_interp_results = None

    progress_callback("Running ADF + KPSS + PP triage", 10)

    for idx, (name, values) in enumerate(all_series):
        pct = 10 + int(75 * (idx + 1) / len(all_series))
        progress_callback(f"Testing '{name}' (ADF/KPSS/PP)", pct)

        clean = _prepare_series(values, name, warnings)
        trending, t_stat = _detect_trend(clean)

        adf = _run_adf_single(clean, regression, max_lag_param, autolag)
        # KPSS takes the same regression family, mapped to {c, ct}.
        kpss_reg = "ct" if regression == "ct" else "c"
        kpss = _run_kpss_single(clean, kpss_reg, nlags="auto")
        # PP takes {n, c, ct} (arch trend codes). Map from our space.
        pp_trend = "ct" if regression == "ct" else ("n" if regression in ("n", "nc") else "c")
        pp = _run_pp_single(clean, pp_trend, lags=None)

        # Decisions
        adf_err = adf.get("error") is not None
        kpss_err = kpss.get("error") is not None
        pp_err = pp.get("error") is not None
        adf_rej = (not adf_err) and adf["pvalue"] < significance
        # KPSS null = stationarity; "rejected" here means p < α, meaning NOT stationary.
        kpss_rej = (not kpss_err) and kpss["pvalue"] < significance
        pp_rej = (not pp_err) and pp["pvalue"] < significance

        adf["decision_h0_rejected"] = bool(adf_rej)
        kpss["decision_h0_rejected"] = bool(kpss_rej)
        pp["decision_h0_rejected"] = bool(pp_rej)

        # Joint verdict driven by ADF + KPSS; PP is a confirmation line.
        if adf_err or kpss_err:
            verdict = "ERROR"
            recommendation = (
                f"ADF error: {adf.get('error') or 'none'}. "
                f"KPSS error: {kpss.get('error') or 'none'}."
            )
        else:
            verdict, recommendation = _joint_verdict(adf_rej, kpss_rej)
            # PP acting as tie-breaker on the unit-root side
            if verdict == "CONFLICTING" and not pp_err:
                pp_note = (
                    "PP agrees with ADF (unit root rejected)" if pp_rej
                    else "PP agrees with KPSS (unit root not rejected)"
                )
                recommendation = f"{recommendation} Tie-breaker: {pp_note}."

        # Triage rows — one per test per series
        def _add_row(series_name, test_label, raw, reg_label, lag_desc,
                     h0_label, rejected):
            if raw.get("error") is not None:
                triage_rows.append([
                    series_name, test_label, None, None, lag_desc,
                    reg_label, f"ERROR: {raw['error']}"
                ])
                return
            triage_rows.append([
                series_name,
                test_label,
                round(float(raw["stat"]), 4),
                round(float(raw["pvalue"]), 6),
                lag_desc,
                reg_label,
                (f"Reject H0 ({h0_label})" if rejected
                 else f"Fail to reject H0 ({h0_label})"),
            ])

        _add_row(
            name, "ADF", adf,
            f"{regression} ({adf['regression_label']})",
            f"AIC-selected lag={adf.get('used_lag')}, "
            f"Schwert bound={adf.get('schwert_bound')}",
            "unit root", adf_rej,
        )
        _add_row(
            name, "KPSS", kpss,
            f"{kpss_reg} ({kpss.get('regression_label', kpss_reg)})",
            f"nlags={kpss.get('used_lag')}",
            "stationarity", kpss_rej,
        )
        _add_row(
            name, "PP", pp,
            f"{pp_trend} ({pp.get('regression_label', pp_trend)})",
            f"truncation lag={pp.get('used_lag')}",
            "unit root", pp_rej,
        )

        # Per-test critical value detail tables
        for test_label, raw in (("ADF", adf), ("KPSS", kpss), ("PP", pp)):
            if raw.get("error") is not None:
                continue
            cv_rows = [
                [lvl, round(cv, 4), "Yes" if rej else "No"]
                for (lvl, cv, rej) in raw["critical_values_ordered"]
            ]
            detail_tables.append(make_table(
                f"{test_label} Critical Values - {name}",
                ["Significance Level", "Critical Value", "Reject H0?"],
                cv_rows,
            ))

        # Per-series Summary sentence
        if verdict == "ERROR":
            sentence = (
                f"'{name}': triage could not complete. {recommendation}"
            )
        else:
            adf_phrase = (
                "unit root rejected" if adf_rej else "unit root not rejected"
            )
            kpss_phrase = (
                "stationarity null rejected" if kpss_rej
                else "stationarity null not rejected"
            )
            pp_phrase = (
                "" if pp_err else
                (" PP " + ("rejects the unit-root null" if pp_rej
                          else "does not reject the unit-root null") + ".")
            )
            sentence = (
                f"'{name}': Joint verdict = {verdict}. ADF {adf_phrase} "
                f"(p={adf['pvalue']:.4f}); KPSS {kpss_phrase} "
                f"(p={kpss['pvalue']:.4f}).{pp_phrase} {recommendation}"
            )
            if trending and regression == "c":
                sentence += (
                    f" Note: series appears trending "
                    f"(|t|={abs(t_stat):.2f} on linear time). Consider "
                    f"re-running with regression='ct'."
                )
        per_series_summaries.append(sentence)

        if first_interp_results is None and not adf_err:
            first_interp_results = _build_interp_dict_triage(
                name=name, adf=adf, kpss=kpss, pp=pp,
                adf_rej=adf_rej, kpss_rej=kpss_rej, pp_rej=pp_rej,
                regression=regression, significance=significance,
                trending=trending, t_stat=t_stat, verdict=verdict,
            )

    triage_table = make_table(
        "Stationarity Triage",
        ["Series", "Test", "Statistic", "P-Value", "Lag / Bandwidth",
         "Regression", "Decision"],
        triage_rows,
    )

    tables = [triage_table] + detail_tables

    plain_english = (" ".join(per_series_summaries)
                     if per_series_summaries
                     else "No test results produced.")

    charting = (
        "Triage table with per-test rows color-coded by decision. "
        "A joint-verdict banner summarizes ADF + KPSS agreement; PP "
        "serves as a tie-breaker line on the unit-root side."
    )

    progress_callback("Done", 100)

    # Audit trail exposes all three test disclosures.
    disclosure = format_significance_disclosure(
        test_name="Stationarity triage: ADF + KPSS + PP joint verdict",
        critical_value_formula=(
            "ADF (MacKinnon CVs, Schwert-bounded AIC lag); "
            "KPSS (KPSS CVs, Newey-West bandwidth); "
            "PP (Dickey-Fuller CVs, Newey-West spectral correction)"
        ),
        ac_corrected=True,
    )

    interp = (
        build_interpretation("adf_test", first_interp_results)
        if first_interp_results is not None else None
    )

    return make_response(
        ctx,
        tables=tables,
        plain_english_summary=plain_english,
        warnings=warnings,
        charting_suggestions=charting,
        interpretation=interp,
        audit_fields={
            "mode": "triage",
            "regression_adf": regression,
            "regression_kpss": ("ct" if regression == "ct" else "c"),
            "regression_pp": ("ct" if regression == "ct"
                              else ("n" if regression in ("n", "nc") else "c")),
            "significance_level": significance,
            "n_series_tested": len(all_series),
            **disclosure,
        },
    )


def _build_interp_dict_triage(*, name, adf, kpss, pp, adf_rej, kpss_rej,
                              pp_rej, regression, significance, trending,
                              t_stat, verdict) -> dict:
    """Convert triage per-series results into the interpretation spec's
    input dict."""
    cv_1 = cv_5 = None
    for lvl, cv, _rej in adf.get("critical_values_ordered", []):
        if str(lvl).strip() == "1%":
            cv_1 = float(cv)
        elif str(lvl).strip() == "5%":
            cv_5 = float(cv)
    return {
        "mode": "triage",
        "series_name": name,
        "adf_stat": float(adf["stat"]),
        "p_value": float(adf["pvalue"]),
        "regression": regression,
        "used_lag": int(adf["used_lag"]),
        "schwert_bound": int(adf["schwert_bound"]),
        "n_obs": int(adf["nobs"]),
        "crit_1pct": cv_1,
        "crit_5pct": cv_5,
        "significance_level": float(significance),
        "trending": bool(trending),
        "t_stat_trend": float(t_stat),
        "decision_rejected": bool(adf_rej),
        "kpss_stat": (float(kpss["stat"])
                      if kpss.get("error") is None else float("nan")),
        "kpss_pvalue": (float(kpss["pvalue"])
                        if kpss.get("error") is None and kpss["pvalue"] is not None
                        else float("nan")),
        "kpss_rejected": bool(kpss_rej),
        "pp_stat": (float(pp["stat"])
                    if pp.get("error") is None else float("nan")),
        "pp_pvalue": (float(pp["pvalue"])
                      if pp.get("error") is None else float("nan")),
        "pp_rejected": bool(pp_rej),
        "joint_verdict": str(verdict),
    }
