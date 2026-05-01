"""Path-resolution helpers for BVAR (Session 0 hardening).

Replaces cwd-relative path resolution in the CLI with two explicit
helpers:

  - ``package_default_config()`` returns the path to ``config/default.yaml``
    relative to the bvar package install location, regardless of cwd.
  - ``resolve_path(path, working_dir)`` resolves a user-supplied path
    against an explicit ``working_dir`` (or cwd, if None) when relative;
    returns the path unchanged when absolute.

The Excel add-in's working directory is typically
``C:\\Users\\<user>\\Documents``, not the BVAR project root. Wrappers
that explicitly pass ``working_dir`` get explicit behavior; the CLI
preserves current implicit-cwd behavior by defaulting ``working_dir=None``.
"""

from __future__ import annotations

from pathlib import Path


def package_default_config() -> Path:
    """Resolve ``config/default.yaml`` relative to the bvar package install.

    Works for both editable (``pip install -e .``) and wheel installs:
    ``config/`` ships at the project root alongside ``src/``.

    Post-TSL-migration layout (Bond Yield Forecast Session 1)::

        <tsl_repo>/engine/techniques/bond_yield_forecast/
            config/default.yaml
            _paths.py             <-- this file
            __init__.py
            ...

    ``Path(__file__).parent`` is the subpackage root; ``config/`` is a
    direct sibling of this file. Pre-migration layout (BVAR standalone
    repo, retired post-Session-6) was
    ``<project_root>/{config, src/bvar}`` requiring ``parent.parent.parent``
    arithmetic; the migration consolidated config into the subpackage.
    """
    return Path(__file__).resolve().parent / "config" / "default.yaml"


def resolve_path(
    path: str | Path,
    working_dir: Path | None = None,
) -> Path:
    """Resolve ``path`` against ``working_dir`` if relative, else return absolute.

    Parameters
    ----------
    path
        The path to resolve. May be absolute or relative.
    working_dir
        Base directory for relative paths. If ``None``, defaults to
        ``Path.cwd()`` (preserves current implicit-cwd CLI behavior).

    Returns
    -------
    Path
        Absolute path. If ``path`` is already absolute, returned unchanged.
        Otherwise, returns ``working_dir / path`` (or ``Path.cwd() / path``
        if ``working_dir`` is None).

    Notes
    -----
    Wrappers (e.g., TSL's Excel add-in) should pass ``working_dir`` explicitly
    to avoid implicit-cwd surprises. The CLI defaults ``working_dir=None``
    so existing scripts keep working from the project root.
    """
    p = Path(path)
    if p.is_absolute():
        return p
    base = Path(working_dir) if working_dir is not None else Path.cwd()
    return base / p
