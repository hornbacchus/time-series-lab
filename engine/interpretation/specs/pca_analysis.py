"""
InterpretationSpec for pca_analysis.

Tier 1 reports PC1 variance-explained, dominance verdict, Kaiser
retention count, and a retention-action line. Tier 2 adds the
eigenvalue spectrum, cumulative-variance milestones, PC1 top-loader
with signed loading, and a PC2-dominant-variable citation with an
explicit "sign unpinned" parenthetical (Decision 3).

Results-dict keys consumed:

    n_series              : int
    n_obs                 : int
    eigenvalues           : list[float] (sorted descending)
    explained_variance_ratio : list[float]
    cumulative_variance_ratio : list[float]
    loadings              : list[list[float]]  (n_series × n_components)
    variable_names        : list[str]
    kaiser_components     : int
    n_80                  : int  (cumulative-variance 80% threshold index+1)
    top_pc1_loader        : str  (variable name; provided by wrapper)
    top_pc1_loading_value : float  (signed, PC1 is svd_flip'd)
    top_pc2_loader        : str  (variable name of the max-|loading| on PC2)
    top_pc2_loading_abs   : float  (unsigned — PC2 sign is not pinned)
    mean_off_diag_abs_rho : float  (for near-identity-correlation trigger)
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    format_stat_technical,
    FMT_COEF_SIGNED,
    FMT_COEF_UNSIGNED,
    FMT_EIGENVALUE,
    FMT_RHO,
)
from interpretation.registry import register

# Preset-gated input-dict keys (T11 invariant). Empty tuple means no
# input keys are conditioned on the preset; Tier 1 has no preset-
# dependent assertions to guard.
PRESET_GATED_KEYS = ()


def _format_eigvec(eigenvalues) -> str:
    """Render eigenvalue spectrum as '[0.62, 0.21, 0.11, 0.06]'."""
    vals = [FMT_EIGENVALUE.format(float(e)) for e in eigenvalues]
    return "[" + ", ".join(vals) + "]"


def _pct(ratio: float) -> str:
    """Render a variance ratio as an integer percent, e.g. 0.623 -> '62%'."""
    return f"{int(round(float(ratio) * 100))}%"


# ---------------------------------------------------------------------
# Tier 1
# ---------------------------------------------------------------------

def _tier1(results: dict) -> str:
    n_series = int(results.get("n_series", 0))
    evr = list(results.get("explained_variance_ratio") or [])
    cum = list(results.get("cumulative_variance_ratio") or [])
    kaiser = int(results.get("kaiser_components", 0))

    pc1_pct = _pct(evr[0]) if evr else "0%"

    if kaiser >= 1:
        # Strong-dominance phrasing keyed to PC1 ratio
        return (
            f"The first principal component explains {pc1_pct} of the "
            f"variance across {n_series} series — one dominant common "
            f"factor drives most of the co-movement. Kaiser's criterion "
            f"retains {kaiser} component{'s' if kaiser != 1 else ''}; "
            f"PC1 serves as the single common factor for dimensionality "
            f"reduction, with PC2 onward carrying residual variance."
            if kaiser == 1 else
            f"The first principal component explains {pc1_pct} of the "
            f"variance across {n_series} series, with Kaiser's criterion "
            f"retaining {kaiser} components in total; these together "
            f"capture {_pct(cum[kaiser - 1]) if cum and kaiser <= len(cum) else 'most'} "
            f"of the variance. Use the retained components as the "
            f"reduced representation."
        )

    # Kaiser retains 0 components
    # Find the lowest k such that cumulative >= 0.80 (if any)
    k80 = None
    for k, c in enumerate(cum):
        if float(c) >= 0.80:
            k80 = k + 1
            break
    k80_phrase = f" only at PC{k80}" if k80 is not None else " only at the final component"
    return (
        f"No single principal component dominates — the {n_series} "
        f"series contribute roughly independent variance, with PC1 "
        f"explaining only {pc1_pct}. Kaiser's criterion retains 0 "
        f"components and cumulative variance reaches 80%{k80_phrase}. "
        f"Dimensionality reduction is not warranted for this dataset; "
        f"model the series in their original basis."
    )


# ---------------------------------------------------------------------
# Tier 2
# ---------------------------------------------------------------------

def _tier2(results: dict) -> str:
    n_series = int(results.get("n_series", 0))
    n_obs = int(results.get("n_obs", 0))
    eigs = list(results.get("eigenvalues") or [])
    cum = list(results.get("cumulative_variance_ratio") or [])
    kaiser = int(results.get("kaiser_components", 0))
    top_pc1 = str(results.get("top_pc1_loader", ""))
    top_pc1_val = results.get("top_pc1_loading_value")
    top_pc2 = str(results.get("top_pc2_loader", ""))
    top_pc2_abs = results.get("top_pc2_loading_abs")

    header = f"PCA was fit on {n_series} series over {n_obs} observations."

    # Eigenvalue spectrum + cumulative-variance milestones
    spectrum = (
        f"Eigenvalue spectrum on the correlation matrix: "
        f"{_format_eigvec(eigs)}"
    )
    if len(cum) >= 3:
        spectrum += (
            f"; cumulative variance reaches {_pct(cum[1])} at PC2 and "
            f"{_pct(cum[2])} at PC3."
        )
    else:
        spectrum += "."

    kaiser_sentence = (
        f"Kaiser's criterion (eigenvalue > 1 on standardized data) "
        f"retains {kaiser} component{'s' if kaiser != 1 else ''}."
    )

    # PC1 top loader (signed)
    if top_pc1 and top_pc1_val is not None:
        pc1_sentence = (
            f"The strongest PC1 loading is '{top_pc1}' at "
            f"{FMT_COEF_SIGNED.format(float(top_pc1_val))}."
        )
    else:
        pc1_sentence = ""

    # PC2 dominant variable (unsigned, with the explicit caveat)
    if top_pc2 and top_pc2_abs is not None:
        pc2_sentence = (
            f"PC2 is dominated by '{top_pc2}' with loading magnitude "
            f"{FMT_COEF_UNSIGNED.format(float(top_pc2_abs))} (sign "
            "unpinned per the PC1-only normalization)."
        )
    else:
        pc2_sentence = ""

    # Flat-spectrum caveat if kaiser == 0
    if kaiser == 0 and pc1_sentence:
        pc1_sentence = (
            f"The strongest PC1 loading is '{top_pc1}' at "
            f"{FMT_COEF_SIGNED.format(float(top_pc1_val))}, but its "
            "dominance is marginal given the flat spectrum."
        )

    return " ".join(filter(None, [
        header, spectrum, kaiser_sentence, pc1_sentence, pc2_sentence
    ]))


# ---------------------------------------------------------------------
# Tier 3 triggers
# ---------------------------------------------------------------------

def _trigger_borderline_first_eigenvalue(results: dict) -> Optional[str]:
    eigs = list(results.get("eigenvalues") or [])
    if not eigs:
        return None
    lambda1 = float(eigs[0])
    if not (0.95 < lambda1 < 1.05):
        return None
    return (
        f"The first eigenvalue ({lambda1:.3f}) sits close to the Kaiser "
        "threshold of 1.0. The retention decision is sensitive to the "
        "threshold choice — consider the parallel-analysis test or a "
        "variance-explained rule (typically 80%) as alternative criteria."
    )


def _trigger_near_identity_corr(results: dict) -> Optional[str]:
    rho_mean = results.get("mean_off_diag_abs_rho")
    if rho_mean is None or float(rho_mean) >= 0.10:
        return None
    return (
        f"The input variables are nearly uncorrelated on average (mean "
        f"|off-diagonal ρ|={FMT_RHO.format(float(rho_mean))}). PCA is "
        "not informative on weakly-related data; the component structure "
        "reflects noise rather than shared variation."
    )


def _trigger_pc1_single_var_echo(results: dict) -> Optional[str]:
    top_pc1 = str(results.get("top_pc1_loader", ""))
    top_pc1_val = results.get("top_pc1_loading_value")
    loadings = results.get("loadings")
    var_names = list(results.get("variable_names") or [])
    if not top_pc1 or top_pc1_val is None or loadings is None:
        return None
    if abs(float(top_pc1_val)) <= 0.95:
        return None
    # Check the next-highest |loading| on PC1 is < 0.30
    try:
        pc1_col = [abs(float(row[0])) for row in loadings]
    except (IndexError, TypeError, ValueError):
        return None
    # Find the max and second-max
    sorted_abs = sorted(pc1_col, reverse=True)
    if len(sorted_abs) < 2:
        return None
    second_max = sorted_abs[1]
    if second_max >= 0.30:
        return None
    return (
        f"PC1's loading on '{top_pc1}' is {FMT_COEF_UNSIGNED.format(abs(float(top_pc1_val)))} "
        "and no other variable loads above 0.30. The first component "
        f"effectively echoes '{top_pc1}'; consider whether PCA is "
        "adding analytical value over using that variable directly."
    )


# ---------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------

SPEC = InterpretationSpec(
    technique_id="pca_analysis",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_borderline_first_eigenvalue,
        _trigger_near_identity_corr,
        _trigger_pc1_single_var_echo,
    ),
    mode_aware=False,
)

register(SPEC)
