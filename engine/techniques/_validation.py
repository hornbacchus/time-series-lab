"""Shared parameter-validation helpers for technique wrappers (Fix B Tier 1+).

Reusable, fail-fast, NO input mutation (the BYF n_draws>n_burn lesson: surface
a clear named-values error at validation, never silently coerce the user's
value). Exception-based — a wrapper wraps its param block in one try/except and
maps ParamError -> make_error_response (mirrors bond_yield_forecast's
_PreflightFailure precedent).

Primitives (reusable across ALL Tier 1+):
    ParamError          - user-facing message + fix hints
    parse_int_tuple     - "a,b,c" | [a,b,c] | (a,b,c) -> tuple[int]; absent/empty
                          /auto -> default (the F2+F3 string-parse lesson)
    require             - the fail-fast primitive

Family-level checks (ARIMA family + any order/seasonal model):
    check_order_bounds  - max_* >= component, max_* <= cap
    check_seasonal      - seasonal OR any(P,D,Q)>0  =>  m > 1
"""
from __future__ import annotations


class ParamError(Exception):
    """A user-facing parameter-validation failure.

    Caught once per wrapper and mapped to ``make_error_response(ctx, str(e),
    error_fixes=e.fixes)``.
    """

    def __init__(self, message: str, fixes: list | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.fixes = fixes or []


def require(condition, message: str, fixes: list | None = None) -> None:
    """Raise ParamError(message, fixes) unless ``condition`` is truthy."""
    if not condition:
        raise ParamError(message, fixes)


def parse_int_tuple(value, n: int, label: str, *, allow_auto: bool = False,
                    default=None):
    """Parse ``value`` into a tuple of exactly ``n`` ints.

    Accepts a comma/space/semicolon-separated string ("2,1,2"), a list, or a
    tuple. Absent (None) and an empty/cleared string ("") ALWAYS route to
    ``default`` (F1-consistent: a cleared dialog box == key absent == the
    engine default). When ``allow_auto`` is set, the sentinels "auto"/"none"
    also route to ``default`` (the F2+F3 lesson: both the 'auto' and the
    explicit forms parse). Malformed / wrong-length / non-integer input raises
    ParamError with a named-values message — never a silent default.
    """
    if value is None:
        return default
    if isinstance(value, str):
        s = value.strip()
        if s == "":
            return default
        if allow_auto and s.lower() in ("auto", "none"):
            return default
        parts = [p for p in s.replace(";", ",").replace(" ", ",").split(",") if p.strip()]
        try:
            ints = [int(p) for p in parts]
        except ValueError:
            raise ParamError(
                f"{label} must be {n} comma-separated integers "
                f"(e.g. '{','.join(['1'] * n)}'), got '{value}'.",
                fixes=[f"Enter {n} integers separated by commas, or leave blank for the default."],
            )
    elif isinstance(value, (list, tuple)):
        try:
            ints = [int(x) for x in value]
        except (ValueError, TypeError):
            raise ParamError(
                f"{label} must be {n} integers, got {value!r}.",
                fixes=[f"Provide {n} integers (e.g. '{','.join(['1'] * n)}')."],
            )
    else:
        raise ParamError(
            f"{label} must be {n} comma-separated integers or a list, "
            f"got {type(value).__name__}.",
            fixes=[f"Enter {n} integers separated by commas (e.g. '{','.join(['1'] * n)}')."],
        )
    if len(ints) != n:
        raise ParamError(
            f"{label} must have exactly {n} integers, got {len(ints)} ('{value}').",
            fixes=[f"Provide exactly {n} integers (e.g. '{','.join(['1'] * n)}')."],
        )
    return tuple(ints)


def parse_int_list(value, label, *, allow_auto=False, default=None):
    """Parse a VARIABLE-length list of ints: 'a,b,c' | [a,b,c] | (a,b,c) -> tuple.
    Absent (None) / empty ('') -> default (F1 cleared-box rule); with allow_auto,
    'auto'/'none' -> default too. Malformed / non-integer -> ParamError (named).
    The list-valued sibling of parse_int_tuple (no fixed length)."""
    if value is None:
        return default
    if isinstance(value, str):
        s = value.strip()
        if s == "":
            return default
        if allow_auto and s.lower() in ("auto", "none"):
            return default
        parts = [p for p in s.replace(";", ",").replace(" ", ",").split(",") if p.strip()]
        try:
            return tuple(int(p) for p in parts)
        except ValueError:
            raise ParamError(
                f"{label} must be comma-separated integers (e.g. '4,2,1'), got '{value}'.",
                fixes=["Enter integers separated by commas, or leave blank for the default."],
            )
    if isinstance(value, (list, tuple)):
        try:
            return tuple(int(x) for x in value)
        except (ValueError, TypeError):
            raise ParamError(
                f"{label} must be a list of integers, got {value!r}.",
                fixes=["Provide integers separated by commas (e.g. '4,2,1')."],
            )
    raise ParamError(
        f"{label} must be comma-separated integers or a list, got {type(value).__name__}.",
        fixes=["Enter integers separated by commas (e.g. '4,2,1')."],
    )


def parse_float_list(value, label, *, allow_auto=False, default=None):
    """Parse a VARIABLE-length list of floats: '0.1,0.5,0.9' | [...] | (...) ->
    tuple[float]. Absent (None) / empty ('') -> default (F1 cleared-box rule);
    with allow_auto, 'auto'/'none' -> default too. Malformed / non-numeric ->
    ParamError (named). The float-valued sibling of parse_int_list (Tier 1b-bis:
    quantile_regression levels)."""
    if value is None:
        return default
    if isinstance(value, str):
        s = value.strip()
        if s == "":
            return default
        if allow_auto and s.lower() in ("auto", "none"):
            return default
        parts = [p for p in s.replace(";", ",").replace(" ", ",").split(",") if p.strip()]
        try:
            return tuple(float(p) for p in parts)
        except ValueError:
            raise ParamError(
                f"{label} must be comma-separated numbers (e.g. '0.1,0.5,0.9'), got '{value}'.",
                fixes=["Enter numbers separated by commas, or leave blank for the default."],
            )
    if isinstance(value, (list, tuple)):
        try:
            return tuple(float(x) for x in value)
        except (ValueError, TypeError):
            raise ParamError(
                f"{label} must be a list of numbers, got {value!r}.",
                fixes=["Provide numbers separated by commas (e.g. '0.1,0.5,0.9')."],
            )
    raise ParamError(
        f"{label} must be comma-separated numbers or a list, got {type(value).__name__}.",
        fixes=["Enter numbers separated by commas (e.g. '0.1,0.5,0.9')."],
    )


def check_order_bounds(*, p=None, q=None, d=None,
                       max_p=None, max_q=None, max_d=None,
                       cap_p=None, cap_q=None, cap_d=None) -> None:
    """Validate search bounds: each max_* >= its component (when both given)
    AND each max_* <= its cap (when a cap is given). Fail-fast, named values.
    (The auto_arima / search-knob consumer — reusable for Tier 1a-bis.)"""
    for comp, mx, cap, lab in (
        (p, max_p, cap_p, "p"), (q, max_q, cap_q, "q"), (d, max_d, cap_d, "d"),
    ):
        if mx is not None and comp is not None:
            require(
                int(mx) >= int(comp),
                f"max_{lab} ({mx}) must be >= {lab} ({comp}).",
                fixes=[f"Raise max_{lab} to at least {comp}, or lower {lab}."],
            )
        if mx is not None and cap is not None:
            require(
                int(mx) <= int(cap),
                f"max_{lab} ({mx}) exceeds the maximum {cap} (pathological-search guard).",
                fixes=[f"Use max_{lab} <= {cap}."],
            )


def check_seasonal(*, seasonal=None, P=None, D=None, Q=None, m) -> None:
    """A seasonal model requires m > 1: if ``seasonal`` is True OR any of the
    seasonal orders P/D/Q is > 0, then the seasonal period m must exceed 1
    (m=1 means non-seasonal — a seasonal spec with m<=1 is contradictory)."""
    wants_seasonal = bool(seasonal) or any(
        (x is not None and int(x) > 0) for x in (P, D, Q)
    )
    if wants_seasonal:
        require(
            m is not None and int(m) > 1,
            f"A seasonal model needs a seasonal period m > 1, got m={m}. "
            f"(seasonal=True or a non-zero P/D/Q requires m>1.)",
            fixes=["Set the seasonal period m > 1 (e.g. 12 for monthly, 4 for quarterly), "
                   "or use a non-seasonal order (P=D=Q=0)."],
        )
