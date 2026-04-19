"""
Technique-id → :class:`InterpretationSpec` lookup.

Specs self-register by calling :func:`register` at import time. The
:func:`get_spec` function is the canonical lookup and returns ``None``
for unregistered techniques (the builder's placeholder-fallback path).

This batch (Prompt A) registers exactly one spec: ``adf_test``. Prompts
B and C will add the other 66 via their own ``specs/*.py`` files,
each importing and calling ``register(...)`` at module load.
"""

from typing import Dict, Optional

from interpretation.builder import InterpretationSpec


_REGISTRY: Dict[str, InterpretationSpec] = {}


def register(spec: InterpretationSpec) -> None:
    """Register a spec under its ``technique_id``.

    Duplicate registration is a programmer error — it silently clobbers
    the earlier entry, which would make the user-visible voice
    non-deterministic across imports. Raise so the test suite catches
    it immediately.
    """
    if spec.technique_id in _REGISTRY:
        raise ValueError(
            f"InterpretationSpec for '{spec.technique_id}' is already "
            f"registered. Each technique must have exactly one spec."
        )
    _REGISTRY[spec.technique_id] = spec


def get_spec(technique_id: str) -> Optional[InterpretationSpec]:
    """Return the registered spec, or ``None`` if not registered."""
    return _REGISTRY.get(str(technique_id))


def list_registered() -> list:
    """Return a sorted list of registered technique ids. For tooling."""
    return sorted(_REGISTRY.keys())


# Import specs here so they self-register. Order-insensitive.
# Prompts B/C will add more lines to this block.
from interpretation.specs import adf_test as _adf  # noqa: F401, E402
