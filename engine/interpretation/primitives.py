"""
Pure phrase-generator primitives for the plain-language Interpretation
layer (Prompt A, §4.2).

Contract (cited mandate sections on each function):

  - All primitives are pure: no I/O, no time, no RNG, no globals.
  - All primitives use explicit format specifiers (``f"{x:.4f}"``, etc.)
    so output is bit-identical across platforms, locales, and Python
    minor versions.
  - Dict iteration order is normalized (``sorted(items)``) wherever it
    would affect output.
  - Each primitive returns a dict of named fragments, not a finished
    sentence — the callers (technique specs) compose these fragments
    into Tier 1 / Tier 2 / Tier 3 strings per the Register C voice.

This batch (Prompt A) exercises only :func:`interpret_pvalue` in the
ADF reference implementation. The other four primitives ship with unit
tests but are not wired into any technique yet; Prompts B and C will
wire them as they reach target techniques.

Do NOT expand this module with imperative rendering code. All sentence
assembly happens in ``engine/interpretation/specs/*.py``.
"""

from typing import Tuple, Optional


# ---------------------------------------------------------------------
# C.1 — P-value bands (§4.4)
# ---------------------------------------------------------------------


def interpret_pvalue(
    p: float,
    thresholds: Tuple[float, float, float] = (0.01, 0.05, 0.10),
) -> dict:
    """Classify a p-value into one of four strength bands.

    Bands (cumulative, using the default thresholds):

        p < 0.01         -> strength="strong",    phrase="strongly rejects"
        0.01 <= p < 0.05 -> strength="standard",  phrase="rejects"
        0.05 <= p < 0.10 -> strength="marginal",  phrase="marginally rejects"
        p >= 0.10        -> strength="none",      phrase="does not reject"

    The phrase is the rejection/fail-to-reject verb that the caller
    fills with the specific null hypothesis (e.g., "strongly rejects
    the unit-root null"). Band widths are configurable so the
    convention scales to tests that use non-standard significance
    levels, but callers should strongly prefer the defaults.

    Parameters
    ----------
    p : float
        Observed p-value. Not required to be in [0, 1] — callers may
        pass clipped values like ``p=0.0`` for numerically zero
        p-values and the helper will treat them as the strongest band.
    thresholds : tuple of three floats, ascending
        The three cutoffs (``alpha_strong, alpha_std, alpha_marginal``)
        separating the four bands.

    Returns
    -------
    dict
        Keys: ``strength`` ("strong" | "standard" | "marginal" | "none"),
        ``phrase`` (the rejection verb), ``band_upper`` (the upper
        bound of the band that p falls into — 0.01, 0.05, 0.10, or 1.0).

    See §4.4 (honest disclosure) — this primitive is the canonical
    translation from a numeric p to a plain-language strength word.
    Every technique that reports p-values routes through it so the
    voice is identical across 67 techniques.
    """
    a_strong, a_std, a_marginal = thresholds
    if not (a_strong < a_std < a_marginal):
        raise ValueError(
            f"thresholds must be strictly ascending; got {thresholds!r}"
        )
    if p < a_strong:
        return {
            "strength": "strong",
            "phrase": "strongly rejects",
            "band_upper": float(a_strong),
        }
    if p < a_std:
        return {
            "strength": "standard",
            "phrase": "rejects",
            "band_upper": float(a_std),
        }
    if p < a_marginal:
        return {
            "strength": "marginal",
            "phrase": "marginally rejects",
            "band_upper": float(a_marginal),
        }
    return {
        "strength": "none",
        "phrase": "does not reject",
        "band_upper": 1.0,
    }


# ---------------------------------------------------------------------
# C.2 — Correlation-strength adjectives (§4.4)
# ---------------------------------------------------------------------

_CORRELATION_BANDS = (
    (0.1, "negligible"),
    (0.3, "weak"),
    (0.5, "moderate"),
    (0.7, "strong"),
    (0.9, "very strong"),
    (float("inf"), "near-perfect"),
)


def interpret_correlation_strength(rho: float) -> dict:
    """Map a correlation coefficient to a plain-language adjective.

    Standard econometric / psychometric convention:

        |rho| < 0.1  -> "negligible"
        0.1 <= |rho| < 0.3 -> "weak"
        0.3 <= |rho| < 0.5 -> "moderate"
        0.5 <= |rho| < 0.7 -> "strong"
        0.7 <= |rho| < 0.9 -> "very strong"
        |rho| >= 0.9       -> "near-perfect"

    Callers pass the signed correlation; the adjective is based on
    absolute value. Sign is a separate dimension (see
    :func:`interpret_direction`).

    Returns
    -------
    dict
        Keys: ``band`` (one of "negligible" | "weak" | "moderate" |
        "strong" | "very strong" | "near-perfect"), ``adjective`` (same
        — convenience alias used by callers that prefer that word),
        ``abs_rho`` (``abs(rho)`` as a float).

    Cited §4.4 — shared vocabulary across 23 pairwise/multivariate
    techniques that emit a correlation or equivalent.
    """
    abs_rho = abs(float(rho))
    for upper, label in _CORRELATION_BANDS:
        if abs_rho < upper:
            return {"band": label, "adjective": label, "abs_rho": abs_rho}
    # Unreachable given the ``float('inf')`` sentinel above, but keeps
    # the type checker happy.
    return {"band": "near-perfect", "adjective": "near-perfect", "abs_rho": abs_rho}


# ---------------------------------------------------------------------
# C.3 — Direction labels (§4.1)
# ---------------------------------------------------------------------


def interpret_direction(
    lag: int,
    x_name: str,
    y_name: str,
    unit: str = "period",
) -> dict:
    """Build a plain-language lead/lag/contemporaneous description.

    Sign convention: ``lag > 0`` means X leads Y (past X predicts future
    Y), matching every pairwise-CCF wrapper in the codebase.

    Parameters
    ----------
    lag : int
        Signed lag in ``unit`` units.
    x_name, y_name : str
        Series names. The helper does NOT add quotes — callers decide.
    unit : str, default "period"
        Singular time unit. The helper pluralizes to ``{unit}(s)``.

    Returns
    -------
    dict
        Keys: ``verb`` ("leads" | "lags" | "co-moves with"),
        ``leader`` (whichever name comes first in the sentence),
        ``follower`` (the other), ``phrase`` (a complete fragment
        like ``"'GDP' leads 'CPI' by 3 period(s)"``).

    Cited §4.1 — direction is a statistical fact the wrapper can own;
    interpretation of *why* the direction holds is user-supplied.
    """
    lag_int = int(lag)
    if lag_int > 0:
        return {
            "verb": "leads",
            "leader": x_name,
            "follower": y_name,
            "phrase": f"'{x_name}' leads '{y_name}' by {lag_int} {unit}(s)",
        }
    if lag_int < 0:
        abs_lag = -lag_int
        return {
            "verb": "leads",
            "leader": y_name,
            "follower": x_name,
            "phrase": f"'{y_name}' leads '{x_name}' by {abs_lag} {unit}(s)",
        }
    return {
        "verb": "co-moves with",
        "leader": x_name,
        "follower": y_name,
        "phrase": f"'{x_name}' co-moves with '{y_name}' contemporaneously",
    }


# ---------------------------------------------------------------------
# C.5 — Coefficient magnitude (§4.4, explicit-unit per user decision)
# ---------------------------------------------------------------------

_COEFFICIENT_BANDS = (
    (0.01, "near zero"),
    (0.1,  "small"),
    (0.5,  "moderate"),
    (1.0,  "large"),
    (float("inf"), "extreme"),
)


def interpret_coefficient_magnitude(coef: float, unit: str) -> dict:
    """Map a raw coefficient to a plain-language size adjective.

    ``unit`` is REQUIRED — no auto-detection in this batch (user
    decision for Prompt A). Callers must pass the natural unit string
    ("bps", "%", "raw", "pp", etc.) so the formatted output is
    unambiguous. A missing unit would force the helper to guess, which
    is exactly the silent-misinterpretation failure mode §4.4 bans.

    Bands on ``|coef|`` (unit-agnostic):

        |c| < 0.01 -> "near zero"
        0.01 <= |c| < 0.1  -> "small"
        0.1  <= |c| < 0.5  -> "moderate"
        0.5  <= |c| < 1.0  -> "large"
        |c| >= 1.0         -> "extreme"

    Returns
    -------
    dict
        Keys: ``band``, ``adjective`` (alias of band), ``formatted``
        (``f"{coef:+.4f} {unit}"``, e.g. ``"+0.3200 %"``).

    Cited §4.4 — prevents the "silently wrong unit" failure mode
    (e.g., reporting a basis-point rate change as a percentage change
    in user-facing output).
    """
    if not isinstance(unit, str) or not unit.strip():
        raise ValueError("unit must be a non-empty string (e.g., 'bps', '%', 'raw')")
    abs_c = abs(float(coef))
    band = "extreme"
    for upper, label in _COEFFICIENT_BANDS:
        if abs_c < upper:
            band = label
            break
    return {
        "band": band,
        "adjective": band,
        "formatted": f"{float(coef):+.4f} {unit.strip()}",
    }


# ---------------------------------------------------------------------
# C.6 — Regime / state labels (§4.2)
# ---------------------------------------------------------------------


def interpret_regime_label(
    regime_index: int,
    n_regimes: int,
    axis: str = "mean",
) -> dict:
    """Label a hidden-state/regime index with a plain-language descriptor.

    Assumes the caller has already sorted regimes ascending by the
    chosen axis (``mean`` or ``variance``) via
    ``engine.techniques.base.sort_states_by_mean``. Under that
    convention, regime 0 is the lowest-axis regime, regime
    ``n_regimes - 1`` is the highest.

    Two-regime conventions:

        regime 0 -> "low-{axis} regime"
        regime 1 -> "high-{axis} regime"

    Three-or-more-regime conventions:

        regime 0              -> "lowest-{axis} regime"
        regime n_regimes - 1  -> "highest-{axis} regime"
        middle regimes        -> "mid-{axis} regime #{k}" where k is the
                                 1-indexed rank among middle regimes.

    Parameters
    ----------
    regime_index : int
        Zero-indexed regime number after sort.
    n_regimes : int
        Total regimes in the model.
    axis : {"mean", "variance"}, default "mean"
        Which axis the caller sorted on. Any other string is accepted
        literally (so a future caller can pass a custom axis name).

    Returns
    -------
    dict
        Keys: ``label`` (e.g., "low-mean regime"),
        ``adjective`` (just the size word, e.g., "low"),
        ``ordinal_phrase`` (e.g., "Regime 0 (low-mean)").

    Cited §4.2 — state-label permutation was the HMM/Markov-Switching
    identification bug; this helper now formalizes the post-sort
    vocabulary so every latent-variable technique speaks in the same
    voice.
    """
    if n_regimes < 1:
        raise ValueError(f"n_regimes must be >= 1, got {n_regimes}")
    if not (0 <= regime_index < n_regimes):
        raise ValueError(
            f"regime_index {regime_index} out of range [0, {n_regimes})"
        )
    axis_str = str(axis).strip()
    if n_regimes == 1:
        label = f"single-{axis_str} regime"
        adjective = "single"
    elif n_regimes == 2:
        if regime_index == 0:
            label = f"low-{axis_str} regime"
            adjective = "low"
        else:
            label = f"high-{axis_str} regime"
            adjective = "high"
    else:
        if regime_index == 0:
            label = f"lowest-{axis_str} regime"
            adjective = "lowest"
        elif regime_index == n_regimes - 1:
            label = f"highest-{axis_str} regime"
            adjective = "highest"
        else:
            label = f"mid-{axis_str} regime #{regime_index}"
            adjective = "mid"
    return {
        "label": label,
        "adjective": adjective,
        "ordinal_phrase": f"Regime {int(regime_index)} ({label})",
    }


# ---------------------------------------------------------------------
# Tier 2 formatting helpers (not primitives per se — but shared)
# ---------------------------------------------------------------------


def format_series_reference(name: str, with_quotes: bool = True) -> str:
    """Render a series name consistently across techniques.

    When ``with_quotes`` is True (default), returns ``"'{name}'"``.
    When False, returns ``name`` unchanged. Callers should prefer
    quoted form in sentences ("'Real GDP'") and bare form in technical
    tables ("Real GDP").

    Cited §4.2 — shared citation convention for series naming.
    """
    return f"'{name}'" if with_quotes else str(name)


def format_stat_technical(
    stat_name: str,
    value: float,
    critical_value: Optional[float] = None,
    p_value: Optional[float] = None,
) -> str:
    """Build a Tier 2 technical statistic fragment with fixed format.

    Output shapes (by input combination):

        stat only                -> "ADF=-10.55"
        stat + critical          -> "ADF=-10.55 vs critical value of -3.45"
        stat + p                 -> "ADF=-10.55, p=0.0000"
        stat + critical + p      -> "ADF=-10.55 vs critical value of -3.45 (p=0.0000)"

    P-values below 0.0001 render as ``p<0.0001`` to avoid misleading
    precision. Critical-value output omits the band label (1% / 5% /
    10%) — callers should pass the critical value at whichever level
    they cite and name the level themselves in the surrounding prose.

    Returns
    -------
    str
        A ready-to-paste technical fragment.
    """
    head = f"{stat_name}={float(value):.4f}"
    if critical_value is not None and p_value is not None:
        p_fragment = _format_p_value_inline(p_value)
        return (
            f"{head} vs critical value of {float(critical_value):.4f} "
            f"({p_fragment})"
        )
    if critical_value is not None:
        return f"{head} vs critical value of {float(critical_value):.4f}"
    if p_value is not None:
        p_fragment = _format_p_value_inline(p_value)
        return f"{head}, {p_fragment}"
    return head


def _format_p_value_inline(p: float) -> str:
    """Render a p-value with sensible precision for inline prose."""
    p_f = float(p)
    if p_f < 1e-4:
        return "p<0.0001"
    return f"p={p_f:.4f}"
