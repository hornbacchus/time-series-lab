"""
InterpretationSpec for var_model (vector autoregression).

Tier 1 leads with stability verdict (max-companion-root modulus), then
lag order + series count, then the single strongest Granger-within-VAR
pair. Tier 2 describes the same plus FEVD/IRF pointers.

Results-dict keys consumed:

    variable_names       : list[str]
    var_order            : int (p)
    n_variables          : int (k)
    aic / bic            : float
    ic_used              : str ("aic" / "bic" / "hqic" / "fpe")
    max_root_modulus     : float or None (from wrapper edit per Decision 1)
    granger_within_var   : list of [cause, caused, f, p, significant?]
    fevd                 : optional list of FEVD entries (for trigger)
    n_obs                : int (effective)
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    interpret_pvalue,
    format_stat_technical,
    FMT_F_STAT,
    FMT_P_VALUE,
)
from interpretation.registry import register

# Preset-gated input-dict keys (T11 invariant). Empty tuple means no
# input keys are conditioned on the preset; Tier 1 has no preset-
# dependent assertions to guard.
PRESET_GATED_KEYS = ()


def _strongest_granger(results: dict) -> Optional[dict]:
    """Return {cause, caused, f, p} for the lowest-p Granger pair, or
    None if the wrapper didn't compute Granger-within-VAR (Fast preset)."""
    rows = results.get("granger_within_var") or []
    if not rows:
        return None
    best = None
    best_p = 1.0
    for row in rows:
        # Row layout per var_model.py: [caused, causing, lag, f_stat, p_value, significant?]
        try:
            caused = row[0]
            causing = row[1]
            f_stat = float(row[3])
            p_value = float(row[4])
        except (IndexError, TypeError, ValueError):
            continue
        if p_value < best_p:
            best_p = p_value
            best = {"cause": str(causing), "caused": str(caused),
                    "f": f_stat, "p": p_value}
    return best


# ---------------------------------------------------------------------
# Tier 1
# ---------------------------------------------------------------------

def _tier1(results: dict) -> str:
    names = list(results.get("variable_names") or [])
    k = int(results.get("n_variables", len(names)))
    p = int(results.get("var_order", 0))
    mrm = results.get("max_root_modulus")

    names_quoted = ", ".join(f"'{n}'" for n in names) if names else f"{k} series"

    if mrm is None:
        stability_lead = (
            f"VAR({p}) fit on {names_quoted}. "
            "Companion-matrix stability was not computed for this run."
        )
    elif float(mrm) >= 0.95:
        stability_lead = (
            f"{k}-variable VAR({p}) on {names_quoted}: the largest "
            f"companion-matrix root modulus is {float(mrm):.2f}, close "
            "to the unit-circle boundary. Forecasts will be slow to "
            "revert and long-horizon prediction intervals will be wide."
        )
    else:
        stability_lead = (
            f"Stable {k}-variable VAR({p}) on {names_quoted}: the largest "
            f"companion-matrix root modulus is {float(mrm):.2f}, well "
            "inside the unit circle, so forecasts decay to the "
            "unconditional mean."
        )

    # Strongest Granger relationship
    sg = _strongest_granger(results)
    if sg is not None and sg["p"] < 0.05:
        granger_clause = (
            f" The strongest within-system Granger relationship is "
            f"'{sg['cause']}' causing '{sg['caused']}' "
            f"(F={FMT_F_STAT.format(sg['f'])}, "
            f"p={sg['p']:.3f})."
        )
    elif sg is not None:
        granger_clause = (
            " No within-system Granger relationship reaches the 5% "
            "threshold."
        )
    else:
        granger_clause = ""

    # Closing — stability-dependent action
    if mrm is None:
        closer = (
            " Inspect the companion-matrix eigenvalues in the data tables "
            "before committing to long-horizon forecasts."
        )
    elif float(mrm) >= 0.95:
        closer = (
            " A VECM refit would be appropriate if a cointegrating "
            "relationship is plausible; otherwise, first-differencing "
            "any variable that retains a near-unit-root signature will "
            "move the system away from the boundary."
        )
    else:
        closer = (
            " Use the model for short- to medium-horizon forecasts with "
            "standard confidence intervals."
        )

    return stability_lead + granger_clause + closer


# ---------------------------------------------------------------------
# Tier 2
# ---------------------------------------------------------------------

def _tier2(results: dict) -> str:
    k = int(results.get("n_variables", 0))
    p = int(results.get("var_order", 0))
    ic_used = str(results.get("ic_used", "AIC")).upper()
    mrm = results.get("max_root_modulus")

    header = (
        f"VAR({p}) fit on {k} series with {ic_used}-selected lag order."
    )

    # Stability sentence
    if mrm is None:
        stability = "Companion-matrix stability diagnostic was not emitted."
    elif float(mrm) >= 0.95:
        stability = (
            f"The companion-matrix max root modulus is {float(mrm):.3f}; "
            "eigenvalues this close to 1 leave the system technically "
            "stable but within the near-non-stationarity band, where "
            "small specification errors can flip the verdict."
        )
    else:
        stability = (
            f"The companion-matrix max root modulus is {float(mrm):.3f}, "
            "comfortably below the 1.0 stability threshold."
        )

    # Granger summary
    sg = _strongest_granger(results)
    if sg is not None and sg["p"] < 0.05:
        granger_sentence = (
            f"Granger-within-VAR rejects the no-causality null for "
            f"'{sg['cause']}' → '{sg['caused']}' "
            f"({format_stat_technical('F', sg['f'], p_value=sg['p'])})."
        )
        # Additional color for the stable case: mention whether others
        # also reject, in a short trailing clause
        other_sig = 0
        for row in results.get("granger_within_var") or []:
            try:
                pv = float(row[4])
                if pv < 0.05:
                    other_sig += 1
            except (IndexError, TypeError, ValueError):
                pass
        if other_sig <= 1:
            granger_sentence += (
                " Other pairs are not significant at the 5% level."
            )
    elif sg is not None:
        granger_sentence = (
            "Granger-within-VAR does not reject the no-causality null at "
            "the 5% level for any within-system pair."
        )
    else:
        granger_sentence = (
            "Granger-within-VAR was not computed at this preset (Fast); "
            "the Balanced or Thorough presets include it."
        )

    # Closer: stability-dependent
    if mrm is None:
        closer = (
            "Orthogonalized impulse-response paths and forecast-error "
            "variance decomposition appear in the data tables."
        )
    elif float(mrm) >= 0.95:
        closer = (
            f"At max root modulus {float(mrm):.2f}, prediction intervals "
            "widen sharply with horizon; a per-variable stationarity "
            "triage identifies which series drive the near-unit-root "
            "behavior."
        )
    else:
        closer = (
            "Orthogonalized impulse-response paths and forecast-error "
            "variance decomposition appear in the data tables."
        )

    return f"{header} {stability} {granger_sentence} {closer}"


# ---------------------------------------------------------------------
# Tier 3 triggers
# ---------------------------------------------------------------------

def _trigger_near_unstable(results: dict) -> Optional[str]:
    mrm = results.get("max_root_modulus")
    if mrm is None or float(mrm) < 0.95:
        return None
    return (
        f"The largest companion-matrix root is {float(mrm):.3f}, inside "
        "but close to the unit-circle boundary. Long-horizon forecasts "
        "will be slow to revert and prediction intervals will widen "
        "sharply; refit as a cointegrated VECM if a stationary long-run "
        "relationship is plausible."
    )


def _trigger_borderline_granger_p(results: dict) -> Optional[str]:
    sg = _strongest_granger(results)
    if sg is None:
        return None
    p = float(sg["p"])
    if not (0.04 < p < 0.06):
        return None
    return (
        f"The strongest Granger-within-VAR p-value ({p:.3f}) sits near "
        "the 5% threshold — the causality claim is sensitive to the "
        "chosen significance level."
    )


def _trigger_fevd_dominance(results: dict) -> Optional[str]:
    """Fires when any (target, source) pair has FEVD share > 0.80 at
    horizon >= 4. Expects results['fevd'] as a list of dicts or tuples
    with (target, source, horizon, share) — optional input; returns None
    when not available."""
    fevd = results.get("fevd") or []
    for entry in fevd:
        try:
            if isinstance(entry, dict):
                target = entry.get("target")
                source = entry.get("source")
                horizon = int(entry.get("horizon", 0))
                share = float(entry.get("share", 0.0))
            else:
                target, source, horizon, share = entry[0], entry[1], int(entry[2]), float(entry[3])
        except (IndexError, TypeError, ValueError):
            continue
        if horizon < 4 or share <= 0.80:
            continue
        if target == source:
            continue  # self-variance dominance isn't informative
        pct = int(round(share * 100))
        return (
            f"'{target}' variance is {pct}% explained by '{source}' at "
            f"horizon {horizon}. This is close to a one-way-driver "
            "regime; treat the multivariate model as informationally "
            "dominated by that channel."
        )
    return None


# ---------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------

SPEC = InterpretationSpec(
    technique_id="var_model",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_near_unstable,
        _trigger_borderline_granger_p,
        _trigger_fevd_dominance,
    ),
    mode_aware=False,
)

register(SPEC)
