"""
InterpretationSpec for emd_hht (Empirical Mode Decomposition +
Hilbert-Huang Transform).

Class 4 (component decomposition via sifting) with Class 2 proxy
(per-IMF Hilbert instantaneous frequency). Distinct from ssa_model's
Tier 1 because EMD's nonlinear / non-stationary / non-orthogonal
framing conveys different caveats than SSA's linear SVD.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    format_scale_aware,
    format_series_reference,
)
from interpretation.registry import register

PRESET_GATED_KEYS = ()


def _concentration_band(pct):
    """Reuse power-concentration band for IMF variance shares."""
    if pct is None:
        return "unknown"
    s = float(pct)
    if s < 10.0:
        return "weak"
    if s < 30.0:
        return "moderate"
    if s < 60.0:
        return "strong"
    return "dominant"


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    method = str(results.get("method", "EMD")).upper()
    backend = str(results.get("backend", "emd"))
    n_imfs = int(results.get("n_imfs", 0))
    dominant_imf = results.get("dominant_imf")
    dominant_pct = results.get("dominant_imf_variance_pct")
    dominant_period = results.get("dominant_imf_period")
    per_imf_periods = results.get("per_imf_periods") or []
    residual_pct = results.get("residual_variance_pct")

    backend_label = (
        "numpy backend" if "numpy" in str(backend).lower() else
        "emd library backend"
    )
    dom_str = (
        f"{float(dominant_pct):.1f}" if dominant_pct is not None else "(not reported)"
    )
    dom_period_str = (
        f"{format_scale_aware(float(dominant_period))} observations"
        if dominant_period is not None else
        "(period not reported)"
    )
    dom_descriptor = ""
    if dominant_period is not None and float(dominant_period) < 5:
        dom_descriptor = " (high-frequency noise)"
    elif dominant_period is not None and float(dominant_period) < 20:
        dom_descriptor = " (short-cycle oscillation)"

    # Additional IMF periods for Tier 1 context
    additional_clause = ""
    if per_imf_periods and len(per_imf_periods) > 1 and n_imfs > 1:
        additional = [float(p) for p in per_imf_periods[1:] if p is not None]
        if additional:
            periods_str = ", ".join(
                format_scale_aware(p) for p in additional[:3]
            )
            additional_clause = (
                f"; IMFs 2-{n_imfs} capture progressively longer "
                f"oscillations (periods {periods_str} observations)"
            )

    # REVISION 1 (D12 refined): Tier 1 states the finding briefly,
    # defers mechanistic explanation to Tier 2.
    residual_clause = ""
    if residual_pct is not None:
        residual_clause = (
            f" Residual trend carries substantial variance "
            f"({float(residual_pct):.1f}% of input variance — non-orthogonal "
            f"overlap with IMFs is expected for sifting-based "
            f"decomposition; see Tier 2)."
        )

    return (
        f"Empirical Mode Decomposition ({method}, {backend_label}) of "
        f"{format_series_reference(name)} ({n} observations) extracted "
        f"{n_imfs} Intrinsic Mode Functions. IMF "
        f"{int(dominant_imf) if dominant_imf is not None else '?'} "
        f"dominates at {dom_str}% of total variance with mean period "
        f"{dom_period_str}{dom_descriptor}{additional_clause}."
        f"{residual_clause}"
    )


def _tier2(results: dict) -> str:
    method = str(results.get("method", "EMD")).upper()
    backend = str(results.get("backend", "emd"))
    n_imfs = int(results.get("n_imfs", 0))
    residual_pct = results.get("residual_variance_pct")

    backend_desc = (
        "numpy fallback — the ``emd`` library path is not in use for "
        "this run"
        if "numpy" in str(backend).lower() else
        "via the ``emd`` Python library"
    )
    ensemble_clause = ""
    if method == "EEMD":
        ensemble_clause = (
            " Under EEMD, Gaussian noise is added to the signal across "
            "an ensemble of realizations, and IMFs are averaged — this "
            "reduces mode mixing at the cost of reproducibility (the "
            "ensemble-averaged IMFs depend on the noise realization "
            "sequence)."
        )

    non_orth_clause = ""
    if residual_pct is not None and float(residual_pct) > 100:
        non_orth_clause = (
            f" The residual-variance share exceeding 100% "
            f"({float(residual_pct):.1f}%) reflects IMF non-orthogonality "
            f"— IMFs overlap in variance, so their shares do not sum to "
            f"100% of total. This is expected behavior for sifting-based "
            f"decompositions and does not indicate a wrapper fault."
        )

    return (
        f"EMD via iterative envelope-based sifting ({backend_desc}). "
        f"{n_imfs} IMFs extracted at maximum depth; sifting terminates "
        f"at the standard Cauchy stopping criterion (SD threshold "
        f"0.001).{ensemble_clause} Per-IMF instantaneous frequency and "
        f"amplitude are computed via the Hilbert transform — a time-"
        f"frequency proxy rather than a unified 2D Hilbert-Huang "
        f"spectrum. EMD is a data-driven nonlinear decomposition with no "
        f"formal orthogonality between IMFs; mode mixing (two distinct "
        f"oscillations blending into one IMF, or one oscillation "
        f"splitting across adjacent IMFs) is a known limitation. "
        f"Instantaneous frequency is meaningfully interpretable only "
        f"for mono-component IMFs; multi-modal IMFs produce ambiguous "
        f"frequency tracks.{non_orth_clause}"
    )


def _trigger_residual_exceeds_input_variance(results: dict) -> Optional[str]:
    residual_pct = results.get("residual_variance_pct")
    if residual_pct is None or float(residual_pct) <= 100.0:
        return None
    return (
        f"Residual variance ({float(residual_pct):.1f}% of input variance) "
        f"exceeds the total input variance, indicating substantial non-"
        f"orthogonality between the extracted IMFs. The decomposition is "
        f"valid as a signal summary but should not be treated as a "
        f"variance-additive decomposition; individual IMF shares are not "
        f"comparable to orthogonal decompositions like SSA or PCA."
    )


def _trigger_numpy_fallback_backend(results: dict) -> Optional[str]:
    backend = str(results.get("backend", ""))
    if "numpy" not in backend.lower():
        return None
    return (
        f"Running on the numpy-only EMD implementation; the dedicated "
        f"``emd`` library (preferred for stability and sifting "
        f"convergence) is not available in the current environment. "
        f"Results are valid but may differ slightly from reference EMD "
        f"outputs — if exact reproducibility is required, install the "
        f"``emd`` Python package."
    )


SPEC = InterpretationSpec(
    technique_id="emd_hht",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_residual_exceeds_input_variance,
        _trigger_numpy_fallback_backend,
    ),
    mode_aware=False,
)

register(SPEC)
