"""Fixture loader with SHA-256 hash verification + format dispatch.

Every on-disk fixture has a sidecar ``fixtures/<id>.sha256`` file
containing the SHA-256 hex digest of the fixture file's contents.
``FixtureLoader.load`` verifies the hash on read and raises
``FixtureHashMismatchError`` if the file has drifted — preventing
silent corruption from breaking parity audits in subtle ways.

Format dispatch (Phase 3.3):

  - ``<id>.npz`` — numpy archive (default; loaded via np.load).
  - ``<id>.pt``  — PyTorch saved object (loaded via torch.load).

Exactly one format file must exist for each fixture_id. If both
exist, ``FixtureFormatAmbiguityError`` is raised — each fixture
must correspond to one format.

Canonical seed metadata (Phase 3.3):

  An ``.npz`` fixture may include a ``_canonical_seed`` array
  containing a single integer. ``FixtureLoader.load`` extracts
  it into the metadata dict. The runner uses the canonical seed
  (when present) instead of the runner-supplied ``--seed`` for
  the first attempt; CAVEAT-reroll then bumps the canonical
  seed by +1.

  This replaces the per-check ``SEED_OFFSET`` workaround used by
  Session 4's ``mcmc_sv_student_t`` check.

``write_with_sha`` is the canonical way to emit a fixture: it
writes the fixture file, computes the digest, and writes the
.sha256 sidecar atomically so future reads are guaranteed to
verify. Pass ``fmt="pt"`` to write a PyTorch fixture instead of
the default numpy archive.
"""

from __future__ import annotations

import hashlib
import pathlib
from typing import Any

import numpy as np


_FIXTURE_ROOT = (
    pathlib.Path(__file__).resolve().parent.parent / "fixtures"
)

_SUPPORTED_FORMATS: tuple[str, ...] = ("npz", "pt")


class FixtureHashMismatchError(RuntimeError):
    """Raised when a fixture file's SHA-256 differs from the
    sidecar .sha256 file. Indicates the fixture has been
    modified out-of-band and parity-audit results would be
    untrustworthy."""

    def __init__(
        self,
        fixture_path: pathlib.Path,
        expected: str,
        actual: str,
    ) -> None:
        super().__init__(
            f"Fixture hash mismatch at {fixture_path}: "
            f"expected {expected!r}, got {actual!r}. The fixture "
            f"file has changed since the .sha256 sidecar was "
            f"written. Either revert the fixture or regenerate "
            f"the sidecar via FixtureLoader.write_with_sha()."
        )
        self.fixture_path = fixture_path
        self.expected = expected
        self.actual = actual


class FixtureFormatAmbiguityError(RuntimeError):
    """Raised when multiple format files exist for the same
    fixture_id (e.g. both ``foo.npz`` and ``foo.pt``). Each
    fixture must correspond to exactly one format file —
    ambiguity would silently let the loader pick one in an
    implementation-defined order. Fail loudly instead."""


class FixtureLoader:
    """Load + verify fixtures by id with format dispatch.

    Parameters
    ----------
    root : pathlib.Path or None
        Override the default fixture directory
        (``tools/reference_parity/fixtures/``). Tests use this
        to point at temp directories.
    """

    def __init__(self, root: pathlib.Path | None = None) -> None:
        self.root = pathlib.Path(root) if root else _FIXTURE_ROOT

    def _candidate_paths(
        self, fixture_id: str,
    ) -> list[tuple[pathlib.Path, str]]:
        """Return ``(path, format)`` for every supported format
        whose file MIGHT exist (existence not yet checked)."""
        return [
            (self.root / f"{fixture_id}.{fmt}", fmt)
            for fmt in _SUPPORTED_FORMATS
        ]

    def _resolve_path(
        self, fixture_id: str,
    ) -> tuple[pathlib.Path, str]:
        """Find the single existing format file for a fixture_id.
        Raises FileNotFoundError if none exist;
        FixtureFormatAmbiguityError if multiple exist."""
        existing = [
            (p, fmt) for p, fmt in self._candidate_paths(fixture_id)
            if p.exists()
        ]
        if not existing:
            tried = [
                str(p) for p, _ in self._candidate_paths(fixture_id)
            ]
            raise FileNotFoundError(
                f"Fixture not found for id {fixture_id!r}; tried: "
                f"{tried}"
            )
        if len(existing) > 1:
            paths = [str(p) for p, _ in existing]
            raise FixtureFormatAmbiguityError(
                f"Multiple format files found for fixture_id "
                f"{fixture_id!r}: {paths}. Each fixture_id must "
                f"correspond to exactly one format file."
            )
        return existing[0]

    def load(
        self, fixture_id: str,
    ) -> tuple[dict[str, Any], dict[str, Any], str]:
        """Load a fixture by id, verifying its SHA-256 hash.

        Returns
        -------
        (data, metadata, sha) : tuple
            - ``data`` is a dict of fixture contents (npz arrays
              materialised, OR the dict returned by torch.load
              for .pt files).
            - ``metadata`` carries harness-level fields extracted
              from the data: currently ``canonical_seed`` (int or
              missing) and ``format`` ("npz" or "pt"). The
              ``_canonical_seed`` array is removed from ``data``
              before return so check code doesn't need to ignore
              it.
            - ``sha`` is the verified hex digest.

        Raises
        ------
        FileNotFoundError
            If the fixture or its sidecar is missing, or if no
            supported format file exists for the id.
        FixtureFormatAmbiguityError
            If multiple format files exist for the id.
        FixtureHashMismatchError
            If the on-disk hash differs from the sidecar.
        """
        fixture_path, fmt = self._resolve_path(fixture_id)
        sha_path = self.root / f"{fixture_id}.sha256"
        if not sha_path.exists():
            raise FileNotFoundError(
                f"Fixture sidecar SHA file not found: {sha_path}. "
                f"Run FixtureLoader.write_with_sha() to regenerate."
            )

        expected = sha_path.read_text(encoding="utf-8").strip()
        actual = self._compute_sha(fixture_path)
        if actual != expected:
            raise FixtureHashMismatchError(
                fixture_path, expected, actual,
            )

        if fmt == "npz":
            data = self._load_npz(fixture_path)
        elif fmt == "pt":
            data = self._load_pt(fixture_path)
        else:
            raise ValueError(
                f"Unsupported fixture format {fmt!r}; "
                f"supported: {_SUPPORTED_FORMATS}"
            )

        metadata: dict[str, Any] = {"format": fmt}
        # Extract canonical_seed from data if present; remove
        # from data dict so check code doesn't need to ignore it.
        if "_canonical_seed" in data:
            cs_arr = np.asarray(data.pop("_canonical_seed"))
            try:
                metadata["canonical_seed"] = int(cs_arr.flat[0])
            except (IndexError, ValueError, TypeError):
                # Defensive: malformed canonical_seed → ignore
                # rather than fail the load.
                pass
        return data, metadata, actual

    @staticmethod
    def _load_npz(path: pathlib.Path) -> dict[str, Any]:
        with np.load(path, allow_pickle=False) as npz:
            return {k: npz[k] for k in npz.files}

    @staticmethod
    def _load_pt(path: pathlib.Path) -> dict[str, Any]:
        """Load a .pt fixture via torch.load. Imports torch
        lazily so callers that only use .npz fixtures don't pay
        the import cost / requirement."""
        try:
            import torch
        except ImportError as e:
            raise ImportError(
                f"Loading .pt fixture {path} requires torch; "
                f"install via the harness MANIFEST.toml's "
                f"[python.packages] torch entry."
            ) from e
        # weights_only=False matches the prior bespoke loader
        # behavior in transformer_attention.py (the .pt fixture
        # bundles a state_dict + a model_config dict + an input
        # tensor, not a single weights blob).
        loaded = torch.load(path, weights_only=False)
        if not isinstance(loaded, dict):
            return {"_pt_payload": loaded}
        return loaded

    def write_with_sha(
        self,
        fixture_id: str,
        data: dict[str, Any],
        *,
        fmt: str = "npz",
    ) -> tuple[pathlib.Path, pathlib.Path, str]:
        """Write a fixture file (in the requested format) plus
        its .sha256 sidecar.

        Parameters
        ----------
        fixture_id : str
            Stem of the fixture filename (no extension).
        data : dict
            Contents to write. For ``.npz``: dict of numpy
            arrays. For ``.pt``: dict (or any torch-savable
            object) — written via ``torch.save``.
        fmt : str, default "npz"
            Format to write; one of ``_SUPPORTED_FORMATS``.

        Returns
        -------
        (fixture_path, sha_path, sha) : tuple
            Paths written + the recorded hex digest.
        """
        if fmt not in _SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported format {fmt!r}; supported: "
                f"{_SUPPORTED_FORMATS}"
            )
        self.root.mkdir(parents=True, exist_ok=True)
        fixture_path = self.root / f"{fixture_id}.{fmt}"
        sha_path = self.root / f"{fixture_id}.sha256"
        # Write the fixture first so the SHA we record matches
        # what's actually on disk.
        if fmt == "npz":
            np.savez(fixture_path, **data)
        elif fmt == "pt":
            import torch
            torch.save(data, fixture_path)
        sha = self._compute_sha(fixture_path)
        sha_path.write_text(sha + "\n", encoding="utf-8")
        return fixture_path, sha_path, sha

    @staticmethod
    def _compute_sha(path: pathlib.Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(64 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()


__all__ = [
    "FixtureLoader",
    "FixtureHashMismatchError",
    "FixtureFormatAmbiguityError",
]
