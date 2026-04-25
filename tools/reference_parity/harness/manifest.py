"""Manifest loader for the reference-parity harness.

Reads ``MANIFEST.toml`` (sibling file) into a typed dataclass
exposing R + Python pinned versions plus refresh metadata.
"""

from __future__ import annotations

import dataclasses
import datetime
import pathlib
import tomllib
from typing import Any


_DEFAULT_PATH = pathlib.Path(__file__).resolve().parent / "MANIFEST.toml"


@dataclasses.dataclass(frozen=True)
class RConfig:
    version: str
    rscript_exe: str
    libs_user: str
    packages: dict[str, str]


@dataclasses.dataclass(frozen=True)
class PythonConfig:
    version: str
    packages: dict[str, str]


@dataclasses.dataclass(frozen=True)
class Manifest:
    """Pinned reference-implementation versions + refresh cadence."""

    last_review: datetime.date
    next_review: datetime.date
    notes: str
    r: RConfig
    python: PythonConfig
    tiers: dict[str, dict[str, Any]]
    source_path: pathlib.Path

    @classmethod
    def load(cls, path: pathlib.Path | str | None = None) -> "Manifest":
        """Parse ``MANIFEST.toml`` from disk.

        Parameters
        ----------
        path : path-like or None
            Override the default location (sibling MANIFEST.toml).

        Returns
        -------
        Manifest

        Raises
        ------
        FileNotFoundError
            If the manifest file does not exist.
        tomllib.TOMLDecodeError
            If the file is not valid TOML.
        KeyError
            If required sections are missing.
        """
        p = pathlib.Path(path) if path is not None else _DEFAULT_PATH
        if not p.exists():
            raise FileNotFoundError(f"Manifest not found at {p}")
        with open(p, "rb") as f:
            data = tomllib.load(f)

        refresh = data["refresh"]
        r_section = data["r"]
        py_section = data["python"]
        return cls(
            last_review=_parse_date(refresh["last_review"]),
            next_review=_parse_date(refresh["next_review"]),
            notes=str(refresh.get("notes", "")).strip(),
            r=RConfig(
                version=str(r_section["version"]),
                rscript_exe=str(r_section["rscript_exe"]),
                libs_user=str(r_section["libs_user"]),
                packages=dict(r_section.get("packages", {})),
            ),
            python=PythonConfig(
                version=str(py_section["version"]),
                packages=dict(py_section.get("packages", {})),
            ),
            tiers=dict(data.get("tiers", {})),
            source_path=p.resolve(),
        )

    def is_stale(self, today: datetime.date | None = None) -> bool:
        """True when ``today`` (default: real today) is past the
        next-review date — signalling the harness owner should
        re-confirm pins."""
        d = today if today is not None else datetime.date.today()
        return d > self.next_review


def _parse_date(value: Any) -> datetime.date:
    """Permissive date parser. Accepts a ``date`` instance (from
    TOML's native date type) or an ISO string."""
    if isinstance(value, datetime.date):
        return value
    return datetime.date.fromisoformat(str(value))
