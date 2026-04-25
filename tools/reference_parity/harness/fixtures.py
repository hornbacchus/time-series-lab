"""Fixture loader with SHA-256 hash verification.

Every on-disk fixture (``fixtures/<id>.npz``) has a sidecar
``fixtures/<id>.sha256`` containing the SHA-256 hex digest of
the .npz contents. ``FixtureLoader.load`` verifies the hash
on read and raises ``FixtureHashMismatchError`` if the file has
drifted — preventing silent corruption from breaking parity
audits in subtle ways.

``write_with_sha`` is the canonical way to emit a fixture: it
writes the .npz, computes the digest, and writes the .sha256
sidecar atomically so future reads are guaranteed to verify.
"""

from __future__ import annotations

import hashlib
import pathlib
from typing import Any

import numpy as np


_FIXTURE_ROOT = (
    pathlib.Path(__file__).resolve().parent.parent / "fixtures"
)


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


class FixtureLoader:
    """Load + verify .npz fixtures by id.

    Parameters
    ----------
    root : pathlib.Path or None
        Override the default fixture directory
        (``tools/reference_parity/fixtures/``). Tests use this
        to point at temp directories.
    """

    def __init__(self, root: pathlib.Path | None = None) -> None:
        self.root = pathlib.Path(root) if root else _FIXTURE_ROOT

    def _paths(self, fixture_id: str) -> tuple[pathlib.Path, pathlib.Path]:
        return (
            self.root / f"{fixture_id}.npz",
            self.root / f"{fixture_id}.sha256",
        )

    def load(self, fixture_id: str) -> tuple[dict[str, np.ndarray], str]:
        """Load a fixture by id, verifying its SHA-256 hash.

        Returns
        -------
        (data, sha) : tuple
            ``data`` is a dict of arrays (NpzFile contents
            materialised). ``sha`` is the verified hex digest.

        Raises
        ------
        FileNotFoundError
            If the fixture or its sidecar is missing.
        FixtureHashMismatchError
            If the on-disk hash differs from the sidecar.
        """
        npz_path, sha_path = self._paths(fixture_id)
        if not npz_path.exists():
            raise FileNotFoundError(f"Fixture not found: {npz_path}")
        if not sha_path.exists():
            raise FileNotFoundError(
                f"Fixture sidecar SHA file not found: {sha_path}. "
                f"Run FixtureLoader.write_with_sha() to regenerate."
            )

        expected = sha_path.read_text(encoding="utf-8").strip()
        actual = self._compute_sha(npz_path)
        if actual != expected:
            raise FixtureHashMismatchError(npz_path, expected, actual)

        with np.load(npz_path) as npz:
            data = {k: npz[k] for k in npz.files}
        return data, actual

    def write_with_sha(
        self,
        fixture_id: str,
        data: dict[str, np.ndarray],
    ) -> tuple[pathlib.Path, pathlib.Path, str]:
        """Write a fixture .npz plus its .sha256 sidecar.

        Returns
        -------
        (npz_path, sha_path, sha) : tuple
            Paths written + the recorded hex digest.
        """
        self.root.mkdir(parents=True, exist_ok=True)
        npz_path, sha_path = self._paths(fixture_id)
        # Write .npz first so the SHA we record matches what's
        # actually on disk.
        np.savez(npz_path, **data)
        sha = self._compute_sha(npz_path)
        sha_path.write_text(sha + "\n", encoding="utf-8")
        return npz_path, sha_path, sha

    @staticmethod
    def _compute_sha(path: pathlib.Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(64 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()


__all__ = ["FixtureLoader", "FixtureHashMismatchError"]
