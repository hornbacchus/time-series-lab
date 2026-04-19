"""
Top-level orchestrator for the plain-language Interpretation layer
(Prompt A).

Public API: :func:`build_interpretation`. Takes a ``technique_id`` and a
``results`` dict (the shape each technique already assembles before
calling ``make_response``), looks up the registered
:class:`InterpretationSpec` for that technique, and returns the
three-tier output.

When the technique has no registered spec (the common case during
Prompt A — only ADF is wired), returns the exact placeholder
documented in P.6 of the plan. The C# writer detects that placeholder
and suppresses the Interpretation block header entirely, so unwired
techniques render the sheet exactly as before.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional, Tuple


PLACEHOLDER_TIER1 = (
    "Interpretation not yet available for this technique. "
    "See Results table for raw output."
)


@dataclass(frozen=True)
class InterpretationSpec:
    """Declarative spec for a technique's three-tier interpretation.

    Each builder is a pure ``Callable[[dict], str]``. Each Tier 3
    trigger is a pure ``Callable[[dict], Optional[str]]`` that returns
    None if the trigger does not fire, or the caveat string if it
    does. All callables must be deterministic (§4.5).

    Marking the dataclass ``frozen=True`` prevents accidental mutation
    at import time — specs are baked once at module load and should
    never change between runs.

    ``mode_aware`` is a hint to callers (and to the ADF spec itself):
    some techniques emit different interpretations in different modes
    (ADF in single-test vs triage). The builder does not branch on
    this field; the spec's own ``tier1_builder`` / ``tier2_builder``
    are expected to read ``results["mode"]`` (or equivalent) and
    compose accordingly. The field exists so future tooling (e.g., a
    "list all specs" dashboard) can flag which specs have mode
    branches.
    """

    technique_id: str
    tier1_builder: Callable[[dict], str]
    tier2_builder: Callable[[dict], str]
    tier3_triggers: Tuple[Callable[[dict], Optional[str]], ...] = field(
        default_factory=tuple
    )
    mode_aware: bool = False


def build_interpretation(technique_id: str, results: dict) -> dict:
    """Assemble the three-tier interpretation for a technique's results.

    Parameters
    ----------
    technique_id : str
        Registry key — matches the technique's entry in
        ``engine.interpretation.registry``.
    results : dict
        Technique-local facts the builders will consume. Shape is
        defined per-technique; there is no cross-technique schema.
        Typical keys for ADF include ``mode``, ``series_name``,
        ``adf_stat``, ``p_value``, ``regression``, ``used_lag``,
        ``schwert_bound``, ``n_obs``, ``critical_value_1pct``,
        ``trending``, ``t_stat_trend``, and (in triage) the KPSS / PP
        equivalents plus ``joint_verdict``.

    Returns
    -------
    dict with exactly three keys:
        ``tier1`` : non-empty plain-language Finding string (150-600
                   chars when the spec is registered).
        ``tier2`` : Technical Interpretation string.
        ``tier3`` : list of caveat strings (possibly empty).

    Fallback: if no spec is registered for ``technique_id``, returns
    ``{"tier1": PLACEHOLDER_TIER1, "tier2": "", "tier3": []}``. The C#
    writer recognizes the placeholder and suppresses the block. This
    means Prompts B/C can ship without gating on every technique being
    wired simultaneously.
    """
    # Imported inside the function to avoid a module-load cycle with
    # specs that register themselves on import.
    from interpretation.registry import get_spec

    spec = get_spec(technique_id)
    if spec is None:
        return {"tier1": PLACEHOLDER_TIER1, "tier2": "", "tier3": []}

    tier1 = spec.tier1_builder(results)
    tier2 = spec.tier2_builder(results)
    tier3 = []
    for trigger in spec.tier3_triggers:
        caveat = trigger(results)
        if caveat is not None and str(caveat).strip():
            tier3.append(str(caveat))
    return {"tier1": str(tier1), "tier2": str(tier2), "tier3": tier3}
