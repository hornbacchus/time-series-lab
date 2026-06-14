"""Regression guard: a present-but-null ``exog`` field must not crash a run.

The class bug (Station-A acceptance P1-18): the C# add-in always serializes
``"exog": null`` on every request (``RunRequest.Exog`` is never populated and
Newtonsoft includes nulls). ``RunContext`` did ``raw.get("exog", [])`` — whose
default only applies when the key is ABSENT — so a present-but-null value flowed
through as ``None``. Three techniques then did an unguarded ``for ex in ctx.exog``
and crashed with ``TypeError: 'NoneType' object is not iterable`` in 0.00s,
during "Validating inputs", before any model fit. Every dialog run of all three
failed; the parity harness stayed green because it OMITS the exog key (→ ``[]``)
and additionally swallows wrapper crashes — the engine-direct-vs-dialog blind
spot.

This guard has two halves:

  * STRUCTURAL — scan every technique module for an iteration over ``ctx.exog``
    that is not guarded with ``or []``. Future-proofs the whole class: a new
    technique that reintroduces the unguarded pattern fails here even if the
    root coercion is in place.
  * RUNTIME — run each exog-capable technique with the REAL dialog payload shape
    (``"exog": null``, NOT exog-omitted) and assert it does not crash with the
    NoneType-not-iterable error. This is precisely the shape the harness never
    exercised.

Run:
    pytest engine/tests/test_exog_null_handling.py -v
"""
import os
import re
import sys
import unittest

_ENGINE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)

import numpy as np  # noqa: E402

from techniques.base import RunContext  # noqa: E402

_TECH_DIR = os.path.join(_ENGINE_DIR, "techniques")

# Technique modules that consume ctx.exog (one column per series; the dialog
# passes additional regressors via the `series` array, but the explicit `exog`
# channel is what the C# client null-fills). Keep in sync if a new exog-capable
# technique ships — the structural test below is the backstop if this drifts.
_EXOG_TECHNIQUES = [
    ("techniques.arimax_sarimax", "arimax_sarimax"),
    ("techniques.nar_narx", "nar_narx"),
    ("techniques.structural_ts", "structural_ts"),
]

# Iteration over ctx.exog (the crash pattern). A `for ... in ctx.exog` without
# an `or []` guard is a violation.
_CTX_EXOG_FOR = re.compile(r"for\s+\w+\s+in\s+.*\bctx\.exog\b")


def _synthetic_series(n: int = 120) -> list:
    """Deterministic trend + seasonal + small ripple — well-behaved enough for
    SARIMAX / a small NAR MLP / a structural UCM to all fit and forecast."""
    t = np.arange(n, dtype=np.float64)
    y = 100.0 + 0.5 * t + 10.0 * np.sin(2.0 * np.pi * t / 12.0) + np.cos(t / 3.0)
    return y.tolist()


def _iso_monthly(n: int) -> list:
    yrs = 1990 + np.arange(n) // 12
    mos = (np.arange(n) % 12) + 1
    return [f"{int(y):04d}-{int(m):02d}-01" for y, m in zip(yrs, mos)]


class TestCtxExogIterationGuarded(unittest.TestCase):
    """STRUCTURAL — no technique may iterate ctx.exog without an `or []` guard.
    Fails (3 violations) before the per-site fix; passes after."""

    def test_no_unguarded_ctx_exog_iteration(self):
        violations = []
        for fn in sorted(os.listdir(_TECH_DIR)):
            if not fn.endswith(".py"):
                continue
            path = os.path.join(_TECH_DIR, fn)
            with open(path, encoding="utf-8") as fh:
                for i, line in enumerate(fh, 1):
                    if _CTX_EXOG_FOR.search(line) and "or []" not in line:
                        violations.append(f"{fn}:{i}: {line.strip()}")
        self.assertFalse(
            violations,
            "Unguarded `for ... in ctx.exog` (crashes when the client sends "
            "\"exog\": null). Use `for ex in (ctx.exog or []):`:\n  "
            + "\n  ".join(violations),
        )


class TestExogNullDoesNotCrash(unittest.TestCase):
    """RUNTIME — the real dialog payload shape (``"exog": null``) must run.
    Fails (NoneType-not-iterable, 0.00s) before the root coercion; passes after."""

    def _run(self, modname: str, tid: str) -> dict:
        import importlib
        mod = importlib.import_module(modname)
        n = 120
        raw = {
            "run_id": "exog_null_guard",
            "technique_id": tid,
            "preset": "Fast",
            "seed": 42,
            "frequency": "Monthly",
            "time": _iso_monthly(n),
            "series": [{"name": "y", "values": _synthetic_series(n)}],
            "exog": None,  # the exact shape the C# client always sends
            "params": {"horizon": 6},
        }
        return mod.run(RunContext(raw), lambda *a, **kw: None)

    def test_each_exog_technique_runs_with_null_exog(self):
        failures = []
        for modname, tid in _EXOG_TECHNIQUES:
            resp = self._run(modname, tid)
            status = resp.get("status")
            err = str(resp.get("error") or resp.get("error_message") or "")
            # The precise regression: it must never be the NoneType crash.
            if "not iterable" in err:
                failures.append(f"{tid}: NoneType-not-iterable -> {err}")
            elif status != "success":
                failures.append(f"{tid}: status={status} err={err}")
        self.assertFalse(
            failures,
            "exog:null must not crash exog-capable techniques:\n  "
            + "\n  ".join(failures),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
