"""Structured warnings for BVAR soft-fail conditions.

These are warnings, not exceptions: the forecast or estimation
completes, but produces a diagnostic that a wrapper should
inspect. Wrappers can capture them via ``warnings.catch_warnings()``.

S0.3 introduces the base class ``BVARWarning``. S0.5 extends with
specific subclasses (ConvergenceWarning, ProjectionAtBoundWarning,
ValidationDomainWarning) attached to converted stderr-print sites.
"""

from __future__ import annotations


class BVARWarning(UserWarning):
    """Base class for soft-fail conditions in BVAR forecasting."""
    pass


class ConvergenceWarning(BVARWarning):
    """Convergence diagnostics below acceptance threshold.

    Raised by ``_print_convergence_summary`` when overall pass rate
    < 90% or any parameter group < 80%.
    """
    pass


class ProjectionAtBoundWarning(BVARWarning):
    """Hyperparameter optimum at a configured bound.

    Raised by ``_print_optimization_summary`` for ``warnings_hard``
    entries from the GLP-2015 hyperparameter optimizer (a lambda
    landed within 1% of its configured upper or lower bound).
    """
    pass


class ValidationDomainWarning(BVARWarning):
    """Validation harness reports issues in one or more domains.

    Raised by ``_validate`` when economic-content checks fail (the
    'REVIEW REQUIRED' block).
    """
    pass
