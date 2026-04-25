"""Harness internals — runner, fixtures, R-bridge, tolerances.

Public surface kept minimal; tests and check modules import
specific names rather than relying on package-level exports.
"""

from reference_parity.harness.base import (
    ParityCheck,
    ParityResult,
    Outcome,
    Tier,
)

__all__ = ["ParityCheck", "ParityResult", "Outcome", "Tier"]
