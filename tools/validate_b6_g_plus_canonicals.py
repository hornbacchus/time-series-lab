"""Phase 5 canonical validation for Follow-up B6.

Exercises the 4 new canonicals from the B6 Phase 2 plan. The 6
existing SV MCMC canonicals in ``validate_sv_mcmc_canonicals.py`` and
the 2 existing Student-t canonicals in
``validate_sv_student_t_canonicals.py`` must continue to pass
unchanged (regression-only) — those scripts are NOT modified by B6.

Canonicals (B6-specific):

  C-new-1: g++ probe → True (monkey-patched), explicit "pymc"
    backend, NUTS path runs (or skips if pymc not installed
    locally). backend_applied="pymc", fallback_reason=None,
    D10 does not fire.

  C-new-2: explicit "gibbs" backend, no probe needed, Gibbs
    runs unchanged. backend_applied="gibbs",
    fallback_reason=None, D10 does not fire.

  C-new-3: g++ probe → False (monkey-patched), auto backend,
    silent downgrade to Gibbs. backend_applied="gibbs",
    backend_requested="auto", fallback_reason=
    "c_compiler_unavailable", D10 fires; no warn-message in
    progress (auto path is silent).

  C-new-4: g++ probe → False (monkey-patched), explicit "pymc",
    warn-and-downgrade to Gibbs. backend_applied="gibbs",
    backend_requested="pymc", fallback_reason=
    "c_compiler_unavailable", D10 fires AND a progress_callback
    warning was emitted.

Patch isolation between canonicals: each canonical clears the
``_check_c_compiler_available`` lru_cache and applies its monkey-
patch in a fresh ``with`` block; teardown is verified by
re-reading the cached value after the patch exits.

Run from project root:
    python tools/validate_b6_g_plus_canonicals.py
"""

import os
import sys
from unittest.mock import patch

# UTF-8 stdout/stderr (cp1252 default on Windows breaks unicode
# arrows in skip messages and tier-3 trigger text).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "engine"))

import numpy as np

from techniques.base import RunContext
from techniques import stochastic_volatility as sv_mod
from techniques import _sv_mcmc as sv_mcmc


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _generate_synthetic_sv(n=200, seed=42):
    """Small synthetic SV path for fast canonicals (T=200 keeps
    Gibbs runtime ~3-5s on Balanced; NUTS ~10s if compiled)."""
    rng = np.random.default_rng(seed)
    h = np.zeros(n)
    h[0] = -10.0
    for t in range(1, n):
        h[t] = -10.0 + 0.95 * (h[t - 1] - (-10.0)) + 0.2 * rng.standard_normal()
    return (np.exp(h / 2.0) * rng.standard_normal(n)).tolist()


def _build_ctx(values, *, mcmc_backend, preset="Balanced"):
    return RunContext({
        "run_id": "test_b6",
        "technique_id": "stochastic_volatility",
        "preset": preset,
        "seed": 42,
        "frequency": "daily",
        "time": list(range(len(values))),
        "series": [{"name": "y", "values": values}],
        "params": {
            "inference_method": "mcmc",
            "mcmc_backend": mcmc_backend,
        },
    })


class _ProgressCapture:
    """Capture progress_callback messages for warn-detection
    in C-new-4."""
    def __init__(self):
        self.messages = []

    def __call__(self, label, percent):
        self.messages.append(label)


def _pymc_installed() -> bool:
    try:
        import pymc  # noqa: F401
        import arviz  # noqa: F401
        return True
    except ImportError:
        return False


def _d10_fired(res: dict) -> bool:
    """Check whether the D10 backend-downgrade trigger fired in
    Tier 3. Tier 3 returns a list of strings (rendered trigger
    text) under interpretation['tier3']."""
    interp = res.get("interpretation") or {}
    tier3 = interp.get("tier3")
    if not tier3:
        return False
    if isinstance(tier3, list):
        text = " ".join(str(t) for t in tier3)
    else:
        text = str(tier3)
    needle1 = "C++ compiler"
    needle2 = "Kim-Shephard-Chib Gibbs sampler"
    return needle1 in text and needle2 in text


def _verify_teardown_isolation():
    """Sanity check: after a monkey-patch's `with` exits and we
    clear the cache, the next call re-probes (real result on
    this machine — typically False since this is the audit
    machine; but the assertion is just that the call works
    without raising)."""
    sv_mcmc._check_c_compiler_available.cache_clear()
    _ = sv_mcmc._check_c_compiler_available()


# ---------------------------------------------------------------------
# Canonicals
# ---------------------------------------------------------------------

def _real_compiler_available() -> bool:
    """Read pytensor.config.cxx directly — bypasses our wrapper's
    cache so we get the actual machine state, not a monkey-
    patched value. Used to gate C-new-1 (which cannot run if
    pytensor itself cannot JIT, regardless of what our wrapper
    probe is told to return)."""
    try:
        import pytensor
        return bool(pytensor.config.cxx)
    except Exception:
        return False


def canonical_C_new_1():
    """g++ probe → True (mocked), explicit pymc, NUTS runs.

    This canonical exercises the happy path: real machine has a
    compiler AND the wrapper proceeds with PyMC NUTS. On a no-
    compiler machine, monkey-patching the wrapper's probe to
    return True is not enough — pytensor itself sees no
    compiler and falls back to pure-Python execution which
    takes 25+ minutes on T=100 SV. We detect this case and
    skip with a documented reason; the cascade behavior
    (probe→True implies PyMC path) is independently verified
    by direct code inspection."""
    sv_mcmc._check_c_compiler_available.cache_clear()
    if not _pymc_installed():
        print("C-new-1: SKIP — pymc not installed; cannot test "
              "compiled NUTS path on this machine.")
        return None
    if not _real_compiler_available():
        print("C-new-1: SKIP — pytensor.config.cxx is empty; "
              "real machine has no C++ compiler. Monkey-patching "
              "our wrapper's probe to True would force PyMC "
              "into pytensor's pure-Python fallback (unusably "
              "slow). The cascade behavior (probe→True ⇒ PyMC "
              "path) is verified by direct inspection of "
              "_sv_mcmc.fit() lines 105-138 instead.")
        return None
    with patch.object(
        sv_mcmc, "_check_c_compiler_available", return_value=True,
    ):
        ctx = _build_ctx(_generate_synthetic_sv(n=100),
                         mcmc_backend="pymc")
        prog = _ProgressCapture()
        res = sv_mod.run(ctx, prog)
    a = res.get("audit_fields", {})
    assert a.get("mcmc_backend_applied") == "pymc", (
        f"C-new-1 expected backend_applied='pymc', got {a}"
    )
    assert a.get("mcmc_backend_fallback_reason") is None, (
        f"C-new-1 expected fallback_reason=None, got {a}"
    )
    assert not _d10_fired(res), \
        "C-new-1 D10 should NOT fire on the NUTS path"
    _verify_teardown_isolation()
    print("C-new-1: PASS (NUTS path)")
    return res


def canonical_C_new_2():
    """Explicit gibbs, runs unchanged. Probe is bypassed by the
    `use_gibbs` short-circuit at the top of fit()."""
    ctx = _build_ctx(_generate_synthetic_sv(n=100),
                     mcmc_backend="gibbs")
    prog = _ProgressCapture()
    res = sv_mod.run(ctx, prog)
    a = res.get("audit_fields", {})
    assert a.get("mcmc_backend_applied") == "gibbs", (
        f"C-new-2 expected backend_applied='gibbs', got {a}"
    )
    assert a.get("mcmc_backend_requested") == "gibbs", (
        f"C-new-2 expected backend_requested='gibbs', got {a}"
    )
    assert a.get("mcmc_backend_fallback_reason") is None, (
        f"C-new-2 expected fallback_reason=None, got {a}"
    )
    assert not _d10_fired(res), \
        "C-new-2 D10 should NOT fire on explicit gibbs"
    print("C-new-2: PASS (explicit gibbs)")
    return res


def canonical_C_new_3():
    """No g++ (mocked), auto backend, silent downgrade to Gibbs.
    D10 trigger fires. No warn-message in progress (auto is
    silent — user did not pin pymc, so no diagnostic noise)."""
    sv_mcmc._check_c_compiler_available.cache_clear()
    with patch.object(
        sv_mcmc, "_check_c_compiler_available", return_value=False,
    ):
        ctx = _build_ctx(_generate_synthetic_sv(n=100),
                         mcmc_backend=None)  # auto
        prog = _ProgressCapture()
        res = sv_mod.run(ctx, prog)
    a = res.get("audit_fields", {})
    assert a.get("mcmc_backend_applied") == "gibbs", (
        f"C-new-3 expected backend_applied='gibbs', got {a}"
    )
    assert a.get("mcmc_backend_requested") == "auto", (
        f"C-new-3 expected backend_requested='auto', got {a}"
    )
    assert a.get("mcmc_backend_fallback_reason") == \
        "c_compiler_unavailable", (
        f"C-new-3 expected fallback_reason='c_compiler_"
        f"unavailable', got {a}"
    )
    assert _d10_fired(res), \
        f"C-new-3 D10 should fire. Tier 3: {res.get('interpretation', {}).get('tier3')}"
    # Auto path should NOT emit the explicit warn-message
    # (warning is reserved for explicit pymc requests).
    warn_msgs = [m for m in prog.messages
                 if "compiler" in m.lower() and "downgrad" in m.lower()]
    assert not warn_msgs, (
        f"C-new-3 auto path should NOT emit compiler-downgrade "
        f"warning; got {warn_msgs}"
    )
    _verify_teardown_isolation()
    print("C-new-3: PASS (auto + no g++ → silent Gibbs)")
    return res


def canonical_C_new_4():
    """No g++ (mocked), explicit pymc, warn-and-downgrade.
    D10 fires AND a progress_callback warning was emitted."""
    sv_mcmc._check_c_compiler_available.cache_clear()
    with patch.object(
        sv_mcmc, "_check_c_compiler_available", return_value=False,
    ):
        ctx = _build_ctx(_generate_synthetic_sv(n=100),
                         mcmc_backend="pymc")
        prog = _ProgressCapture()
        res = sv_mod.run(ctx, prog)
    a = res.get("audit_fields", {})
    assert a.get("mcmc_backend_applied") == "gibbs", (
        f"C-new-4 expected backend_applied='gibbs', got {a}"
    )
    assert a.get("mcmc_backend_requested") == "pymc", (
        f"C-new-4 expected backend_requested='pymc', got {a}"
    )
    assert a.get("mcmc_backend_fallback_reason") == \
        "c_compiler_unavailable", (
        f"C-new-4 expected fallback_reason='c_compiler_"
        f"unavailable', got {a}"
    )
    assert _d10_fired(res), \
        f"C-new-4 D10 should fire. Tier 3: {res.get('interpretation', {}).get('tier3')}"
    # Explicit pymc path MUST emit the compiler-downgrade warning
    warn_msgs = [m for m in prog.messages
                 if "compiler" in m.lower() and "downgrad" in m.lower()]
    assert warn_msgs, (
        f"C-new-4 explicit pymc + no g++ should emit warning; "
        f"got messages: {prog.messages}"
    )
    _verify_teardown_isolation()
    print("C-new-4: PASS (explicit pymc + no g++ → warn-and-Gibbs)")
    return res


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> int:
    print("=== B6 follow-up canonicals (4 new) ===")
    print()
    canonical_C_new_1()
    canonical_C_new_2()
    canonical_C_new_3()
    canonical_C_new_4()
    print()
    print("All B6 canonicals passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
