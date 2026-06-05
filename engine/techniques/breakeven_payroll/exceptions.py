"""Custom exceptions and warnings for breakeven-payrolls."""

from __future__ import annotations


class InputValidationError(ValueError):
    """Raised when config or input data fails validation.

    Mirrors the house pattern.

    Attributes
    ----------
    rule : str
        Short identifier for the failed rule (e.g. ``"config_missing_key"``).
    detail : str
        Human-readable description of what was wrong.
    location : str | None
        File / section / column where the failure was detected.
    """

    def __init__(self, rule: str, detail: str, *, location: str | None = None) -> None:
        self.rule = rule
        self.detail = detail
        self.location = location
        msg = f"[{rule}] {detail}"
        if location:
            msg += f" (at {location})"
        super().__init__(msg)


class AcquisitionError(RuntimeError):
    """Raised when a data source cannot be fetched and no fallback applies."""

    def __init__(
        self,
        message: str,
        *,
        url: str | None = None,
        status: int | None = None,
        source_id: str | None = None,
        transient: bool = False,
    ) -> None:
        self.url = url
        self.status = status
        self.source_id = source_id
        self.transient = transient
        super().__init__(message)


class BreakevenWarning(UserWarning):
    """Base class for soft, non-fatal conditions."""


class FallbackUsedWarning(BreakevenWarning):
    """Emitted when a hand-keyed fallback is used instead of a live source."""


class ReconciliationWarning(BreakevenWarning):
    """Emitted when a reconciliation anchor is CAVEAT / partial."""
