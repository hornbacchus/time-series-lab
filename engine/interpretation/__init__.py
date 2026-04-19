"""
Plain-language Interpretation layer for TSL technique output.

Top-level public API:

    from engine.interpretation import build_interpretation, get_spec

``build_interpretation(technique_id, results)`` is the canonical entry
point called from each technique wrapper just before ``make_response``.

See :mod:`engine.interpretation.builder` for the spec contract and
:mod:`engine.interpretation.primitives` for the shared phrase
generators (pure, deterministic, mandate §4.5).
"""

from interpretation.builder import (
    build_interpretation,
    InterpretationSpec,
    PLACEHOLDER_TIER1,
)
from interpretation.registry import get_spec, list_registered

__all__ = [
    "build_interpretation",
    "InterpretationSpec",
    "PLACEHOLDER_TIER1",
    "get_spec",
    "list_registered",
]
