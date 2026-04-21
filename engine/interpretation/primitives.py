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

Future-promotion convention (Prompt C1 Decision 4). Spec authors
routinely need small helper functions (adjective-band mappings,
format adapters, local rule renderers) that *might* eventually
generalize across specs. The convention: **promote a helper to
this module on the second distinct technique that needs it**, not
the first. A single-use helper lives privately in its spec; the
second distinct use promotes it here, with a docstring citing both
consumers. This keeps primitives.py focused on proven-general
utilities and avoids speculative API additions. Applies equally to
``engine/techniques/base.py`` helpers (e.g., ``stationary_distribution``
was promoted on its second consumer in Prompt C1).

Formatter selection guidance (Prompt C1 post-eval fix batch).
Specs ingest numeric values whose natural scale varies widely
(coefficients in (-1, 1); AIC in the 1000s; MSE in the 1000s or
higher; interval widths in whatever the series units are). Pick
the right formatter at the call site:

  - Coefficient magnitudes bounded in (-1, 1) (correlations,
    ensemble weights, β coefficients, ACF values): use
    ``FMT_COEF_UNSIGNED`` (``".3f"``, pinned).
  - p-values: use ``FMT_P_VALUE`` (``".4f"``, pinned).
  - Probabilities on [0, 1] (smoothed probs, posterior probs,
    ensemble weights): use ``FMT_PROBABILITY`` (``".2f"``, pinned).
  - Correlation coefficients ρ: use ``FMT_RHO`` (``".2f"``, pinned).
  - Any other arbitrary-scale statistic (AIC, MSE, RMSE, SE,
    interval widths, F, LM, Z-statistics, test statistics): use
    :func:`format_scale_aware` — it adapts decimal precision to
    the value's order of magnitude and avoids the misleading-
    precision failure mode (e.g., ``"AIC 17043.245"`` vs the
    readable ``"AIC 17043"``). For very-near-zero values
    (``|v| < 1e-3``), ``format_scale_aware`` switches to
    scientific notation (``"1.2e-10"``) to preserve the
    magnitude signal that a ``.4f`` rendering would collapse
    to ``"0.0000"``. This matters for State Space variance
    components that optimize to the floor.
  - **When in doubt, use format_scale_aware.** It reads at
    appropriate precision across scales and is the safe default
    for new specs. The pinned constants are for values whose
    scale is known a priori; if a value's scale depends on the
    series, route through format_scale_aware.

This convention applies to all future spec authoring (Prompts
C2-C7 and beyond).
"""

from typing import Tuple, Optional


# ---------------------------------------------------------------------
# Format-specifier constants (R6 — §4.5 determinism)
# ---------------------------------------------------------------------
#
# Pinned module-level format strings for every numeric value rendered
# in Tier 1 / Tier 2 / Tier 3 output across every spec. Rationale:
# bit-identical output across platforms, locales, and Python minor
# versions requires that EVERY f-string interpolating a number in a
# user-facing string route through one of these constants rather than
# picking an ad-hoc ``{:.3f}`` / ``{:.4f}`` at the call site. Ad-hoc
# formatting looks harmless in isolation but makes the T2 determinism
# invariant brittle — two specs writing the same α+β value with
# different specifiers produce non-identical rendered text even when
# the underlying math is identical.
#
# Each technique spec MUST use these constants (or the
# ``format_stat_technical`` helper which routes through them) for its
# user-facing numeric formatting. Internal log / audit values that do
# not appear in tier text are free to use any format.

FMT_P_VALUE       = "{:.4f}"   # p-values
FMT_RHO           = "{:.2f}"   # correlation coefficients
FMT_COEF_SIGNED   = "{:+.3f}"  # β, α, loadings — sign-preserving
FMT_COEF_UNSIGNED = "{:.3f}"   # magnitude-only coefficients
FMT_F_STAT        = "{:.2f}"   # F-statistics
FMT_PERSISTENCE   = "{:.3f}"   # α+β-style persistence sums
FMT_EIGENVALUE    = "{:.2f}"   # eigenvalues
FMT_PROBABILITY   = "{:.2f}"   # smoothed probabilities, posterior probs
FMT_HALF_LIFE     = "{:.1f}"   # half-lives in any unit

# Default format applied to any ``stat_name`` passed to
# ``format_stat_technical`` that is not explicitly keyed in
# ``FMT_STAT_BY_NAME``. Two-decimal convention matches the adjective
# bands' numerical resolution (see C.2 / C.5).
FMT_STAT_DEFAULT  = "{:.2f}"

# Per-stat format mapping for the ``format_stat_technical`` helper.
# Keyed on the stat name string the caller passes. Unknown names fall
# back to ``FMT_STAT_DEFAULT``. Extend as additional stats become live
# in later prompts (Prompt C will likely add "χ²", "LR", "Q", etc.).
FMT_STAT_BY_NAME = {
    "F":     FMT_F_STAT,
    "ADF":   FMT_STAT_DEFAULT,
    "KPSS":  FMT_STAT_DEFAULT,
    "PP":    FMT_STAT_DEFAULT,
    "trace": FMT_STAT_DEFAULT,
    "λ":     FMT_EIGENVALUE,
    "P":     FMT_PROBABILITY,
}


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


def format_scale_aware(value, sub_unit_specifier: str = "{:.4f}") -> str:
    """Render a numeric magnitude with precision adapted to scale.

    Used by specs that report statistics whose natural range spans
    multiple orders of magnitude across techniques and invocations
    (AIC, MSE, RMSE, SE, interval widths, etc.). Preserves
    ``FMT_COEF_UNSIGNED`` and its peers for values whose scale is
    known a priori.

    Precision rule:

        |v| >= 1000 : "{:.0f}"  (integer rounding, e.g. "17043")
         100 <= |v| < 1000 : "{:.1f}"  (e.g. "162.9")
          10 <= |v| < 100  : "{:.2f}"  (e.g. "21.24")
           1 <= |v| < 10   : "{:.3f}"  (e.g. "1.476")
          1e-3 <= |v| < 1  : sub_unit_specifier (default "{:.4f}")
          |v| < 1e-3       : "{:.1e}"  (scientific notation, e.g. "1.2e-10")

    The sub-``1e-3`` branch catches near-zero values where ``".4f"``
    would render as ``"0.0000"`` and lose all magnitude signal
    (e.g., a local-linear-trend model's slope variance at the
    optimizer floor — ``σ²_ζ = 1.2e-10`` must render as
    ``"1.2e-10"``, not ``"0.0000"``). ``abs(v)`` is used for the
    threshold check so negative near-zero values route through
    the same branch.

    The ``sub_unit_specifier`` argument lets callers pin higher
    precision for sub-unit magnitudes whose natural resolution is
    finer than ``".4f"`` (e.g., block-bootstrap return means where
    the meaningful precision is ``".5f"`` or finer).

    Parameters
    ----------
    value : float
        The numeric value to render.
    sub_unit_specifier : str, default "{:.4f}"
        Format specifier applied when ``|value| < 1``. Allows callers
        with higher-precision requirements to override.

    Returns
    -------
    str
        Formatted value.

    Cited Prompt C1 post-eval: the over-precision finding (AIC
    17043.245, MSE 6700.951, interval width 162.965, etc.) came from
    specs reaching for ``FMT_COEF_UNSIGNED = "{:.3f}"`` because it
    was the nearest pinned constant. That constant is for
    coefficient magnitudes in (-1, 1), not arbitrary-scale
    statistics. This helper serves the arbitrary-scale case.
    """
    v = float(value)
    av = abs(v)
    if av >= 1000:
        return f"{v:.0f}"
    if av >= 100:
        return f"{v:.1f}"
    if av >= 10:
        return f"{v:.2f}"
    if av >= 1:
        return f"{v:.3f}"
    if av >= 1e-3:
        return sub_unit_specifier.format(v)
    # Near-zero: scientific notation preserves the magnitude signal
    # that a .4f rendering would lose (0.0000).
    return f"{v:.1e}"


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

    The stat value is formatted via :data:`FMT_STAT_BY_NAME` (keyed on
    ``stat_name``) with :data:`FMT_STAT_DEFAULT` as the fallback. The
    critical value uses the same format. P-values route through
    :data:`FMT_P_VALUE` via :func:`_format_p_value_inline`. Per R6
    (§4.5 determinism), every numeric fragment this helper emits is
    pinned — callers never need to repeat a specifier at the call site.

    Returns
    -------
    str
        A ready-to-paste technical fragment.
    """
    stat_fmt = FMT_STAT_BY_NAME.get(stat_name, FMT_STAT_DEFAULT)
    head = f"{stat_name}={stat_fmt.format(float(value))}"
    if critical_value is not None and p_value is not None:
        p_fragment = _format_p_value_inline(p_value)
        return (
            f"{head} vs critical value of {stat_fmt.format(float(critical_value))} "
            f"({p_fragment})"
        )
    if critical_value is not None:
        return f"{head} vs critical value of {stat_fmt.format(float(critical_value))}"
    if p_value is not None:
        p_fragment = _format_p_value_inline(p_value)
        return f"{head}, {p_fragment}"
    return head


def _format_p_value_inline(p: float) -> str:
    """Render a p-value with sensible precision for inline prose.

    Routes through :data:`FMT_P_VALUE` per R6. P-values numerically
    below 0.0001 are rendered as ``p<0.0001`` rather than stringifying
    to a misleading ``p=0.0000``.
    """
    p_f = float(p)
    if p_f < 1e-4:
        return "p<0.0001"
    return f"p={FMT_P_VALUE.format(p_f)}"


# ---------------------------------------------------------------------
# R7 — Break-date formatting (§4.5 determinism)
# ---------------------------------------------------------------------

def format_break_date(date_value, frequency: str) -> str:
    """Render a changepoint / structural-break date deterministically.

    Used by specs whose Tier 1/Tier 2 text includes a break date drawn
    from a rolling / windowed fit. Frequency-keyed format to match how
    analysts quote dates at each sampling rate:

        "quarterly"  -> "YYYY-Qn"
        "monthly"    -> "YYYY-MM"
        "daily"      -> "YYYY-MM-DD"
        "annual"     -> "YYYY"

    Unknown frequency or parse failure falls back to the input's
    ``str()`` repr with any trailing whitespace stripped — deterministic
    in that the input determines the output, but the caller should
    ideally pass a recognized frequency.

    Pure function: no locale, no tzinfo, no current-time calls.

    Parameters
    ----------
    date_value
        A pandas ``Timestamp``, ``date``, or ISO-format string. The
        helper calls ``pd.Timestamp(date_value)`` internally.
    frequency : str
        One of ``"quarterly"``, ``"monthly"``, ``"daily"``, ``"annual"``.
        Case-insensitive; matched via ``str.strip().lower()``.

    Returns
    -------
    str
        Formatted date string.
    """
    key = str(frequency or "").strip().lower()
    # Accept pandas-style short codes as aliases for the long-form keys
    # (RunContext._normalize_frequency converts incoming labels to short
    # codes like "Q"/"M"/"D"/"Y" before wrappers see them). Spec callers
    # that pass ``ctx.frequency`` directly should still get sensible
    # output without needing to translate.
    _SHORT_CODE_ALIAS = {
        "q": "quarterly",
        "qs": "quarterly",
        "m": "monthly",
        "ms": "monthly",
        "d": "daily",
        "b": "daily",
        "y": "annual",
        "a": "annual",
    }
    key = _SHORT_CODE_ALIAS.get(key, key)
    try:
        import pandas as pd  # local import: primitives otherwise numpy-only
        ts = pd.Timestamp(date_value)
    except Exception:
        return str(date_value).strip()
    if key == "quarterly":
        # pandas quarters: month 1-3 -> Q1, 4-6 -> Q2, etc. Pin explicitly
        # rather than use pd.Period string rendering (which varies by
        # pandas version).
        q = (ts.month - 1) // 3 + 1
        return f"{ts.year:04d}-Q{q}"
    if key == "monthly":
        return f"{ts.year:04d}-{ts.month:02d}"
    if key == "daily":
        return f"{ts.year:04d}-{ts.month:02d}-{ts.day:02d}"
    if key == "annual":
        return f"{ts.year:04d}"
    # Fallback: ISO date only (no time component, no tzinfo)
    return f"{ts.year:04d}-{ts.month:02d}-{ts.day:02d}"
