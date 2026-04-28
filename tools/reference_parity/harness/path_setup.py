"""Shared path-setup helper for parity checks.

Phase 3 Session 5 abstraction: lifted verbatim from the
inline copies in ``harness/checks/p3_*.py`` (Batch 1
Sessions 2–4). Per the Session 5 design exploration agent,
all 70 Phase 3 wrappers follow uniform import patterns and
require only this single sys.path manipulation; no batch-
specific variation is needed.

Pre-Phase-3 checks (smoke, 1c..3f) retain inline copies
for backward compatibility; this module is import-on-
demand and does not force migration.
"""

from __future__ import annotations

import pathlib
import sys


def _ensure_engine_on_path() -> None:
    """Add ``engine/`` to sys.path so checks can ``from techniques.X import ...``.

    Walks up from this module's location until a directory
    containing ``engine/`` is found, then prepends
    ``<repo_root>/engine`` to ``sys.path`` if absent.

    Raises
    ------
    RuntimeError
        If no parent directory contains ``engine/``. Indicates
        the harness was relocated outside the TSL repo without
        accompanying engine/ tree; check author should run from
        the standard repo layout.
    """
    p = pathlib.Path(__file__).resolve()
    repo_root = None
    for parent in p.parents:
        if (parent / "engine").is_dir():
            repo_root = parent
            break
    if repo_root is None:
        raise RuntimeError(
            "Cannot locate engine/ from harness module; "
            "expected repo layout has tools/reference_parity/ "
            "and engine/ as siblings."
        )
    eng_path = str(repo_root / "engine")
    if eng_path not in sys.path:
        sys.path.insert(0, eng_path)


__all__ = ["_ensure_engine_on_path"]
