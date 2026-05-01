"""Tests for S0.1: package-relative config + explicit working_dir.

Verifies the path-handling helpers in src/bvar/_paths.py and the
CLI's path-resolution layer work regardless of the calling
process's cwd.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from techniques.bond_yield_forecast._paths import package_default_config, resolve_path


def test_package_default_config_resolves_independently_of_cwd(tmp_path, monkeypatch):
    """Changing cwd does not change the resolved config path."""
    expected = package_default_config()
    assert expected.exists(), (
        f"package_default_config() returned {expected!r} which does not "
        "exist; package layout assumption may be broken."
    )

    monkeypatch.chdir(tmp_path)
    same = package_default_config()
    assert same == expected
    assert same.exists()


def test_package_default_config_points_at_project_root_yaml():
    """The resolved path should be config/default.yaml under the project root."""
    p = package_default_config()
    assert p.name == "default.yaml"
    assert p.parent.name == "config"


def test_resolve_path_absolute_returns_unchanged(tmp_path):
    """Absolute paths pass through unchanged regardless of working_dir."""
    abs_path = tmp_path / "anywhere.txt"
    assert resolve_path(abs_path, working_dir=Path("/some/other/dir")) == abs_path
    assert resolve_path(str(abs_path), working_dir=None) == abs_path


def test_resolve_path_relative_uses_working_dir(tmp_path):
    """Relative paths resolve against an explicit working_dir."""
    result = resolve_path("data/sub/file.csv", working_dir=tmp_path)
    assert result == tmp_path / "data" / "sub" / "file.csv"
    assert result.is_absolute()


def test_resolve_path_relative_defaults_to_cwd(tmp_path, monkeypatch):
    """If working_dir is None, relative paths resolve against cwd."""
    monkeypatch.chdir(tmp_path)
    result = resolve_path("relative/path.txt", working_dir=None)
    assert result == tmp_path / "relative" / "path.txt"


@pytest.mark.skip(
    reason="CLI did not migrate to TSL (archived as _legacy_cli.py.archive); "
           "wrapper-friendly working_dir behavior is now exercised via the "
           "TSL Excel add-in dispatch path (Session 2+), not the BVAR CLI."
)
def test_smoke_list_scenarios_from_alternative_cwd(tmp_path, monkeypatch):
    """End-to-end: invoke main() from a tmp_path cwd with absolute paths.

    Uses --list-scenarios because it's fast (no estimation, no forecast).
    Verifies the CLI's path resolution layer works when cwd != project root.
    The bvar_inputs.xlsx workbook is referenced via absolute path.
    """
    from cli.run_forecast import main

    # Resolve the project root relative to this test file (works regardless
    # of cwd at test discovery time).
    project_root = Path(__file__).resolve().parent.parent
    workbook = project_root / "data" / "raw" / "bvar_inputs.xlsx"
    if not workbook.exists():
        pytest.skip(f"{workbook} not present; smoke skipped")

    monkeypatch.chdir(tmp_path)
    rc = main([
        "--list-scenarios",
        "--input", str(workbook),
    ])
    assert rc == 0


@pytest.mark.skip(
    reason="CLI did not migrate to TSL (archived as _legacy_cli.py.archive); "
           "the --working-dir flag behavior is now exercised via the TSL "
           "engine_worker dispatch, not the BVAR CLI."
)
def test_smoke_list_scenarios_with_explicit_working_dir(tmp_path, monkeypatch):
    """Same smoke but using --working-dir to specify the project root.

    Demonstrates the wrapper-friendly invocation: cwd is some unrelated
    directory, --working-dir points at the BVAR project root, and a
    relative --input resolves correctly.
    """
    from cli.run_forecast import main

    project_root = Path(__file__).resolve().parent.parent
    workbook_rel = "data/raw/bvar_inputs.xlsx"
    workbook_abs = project_root / workbook_rel
    if not workbook_abs.exists():
        pytest.skip(f"{workbook_abs} not present; smoke skipped")

    monkeypatch.chdir(tmp_path)
    rc = main([
        "--list-scenarios",
        "--working-dir", str(project_root),
        "--input", workbook_rel,
    ])
    assert rc == 0
