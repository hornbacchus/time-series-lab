# Phase 4 Session 11b — install local git pre-commit hook for
# P-1 §8.5 install-matrix gate (B-Phase4-S5-4).
#
# Installs `tools/git_hooks/pre-commit` into `.git/hooks/`.
# Run once after cloning / pulling. Idempotent — safe to re-run.
#
# Usage:
#     pwsh tools/install_hooks.ps1
#
# CI fallback: even when the local hook is not installed, the
# `parity-fast.yml` workflow runs `tools/validate_install_matrix.py`
# as its first step (belt-and-suspenders pattern; see P-1 §13.5.4
# S5 self-validating-irony case study).

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$HooksSrc = Join-Path $RepoRoot "tools" "git_hooks"
$HooksDest = Join-Path $RepoRoot ".git" "hooks"

if (-not (Test-Path $HooksDest)) {
    Write-Error "No .git/hooks directory found at $HooksDest. Are you inside a git repo?"
    exit 1
}

if (-not (Test-Path $HooksSrc)) {
    Write-Error "No tools/git_hooks directory at $HooksSrc."
    exit 1
}

$installed = 0
$skipped = 0
foreach ($hook in Get-ChildItem -Path $HooksSrc -File) {
    $destPath = Join-Path $HooksDest $hook.Name
    $sourceContent = Get-Content -Path $hook.FullName -Raw

    if (Test-Path $destPath) {
        $existingContent = Get-Content -Path $destPath -Raw
        if ($existingContent -eq $sourceContent) {
            Write-Host "Skipped (already up-to-date): $($hook.Name)"
            $skipped++
            continue
        }
        Write-Warning ("Existing hook at $destPath differs from " +
            "tools/git_hooks/$($hook.Name).")
        Write-Warning ("To overwrite: rm `"$destPath`"; pwsh " +
            "tools/install_hooks.ps1")
        Write-Warning "NOT silently overwriting (per Phase 4 S11b-3 trigger)."
        $skipped++
        continue
    }

    Copy-Item -Path $hook.FullName -Destination $destPath
    Write-Host "Installed hook: $($hook.Name) -> $destPath"
    $installed++
}

Write-Host ""
Write-Host "Summary: $installed installed; $skipped skipped (existing or up-to-date)."
Write-Host "Linux/macOS contributors: equivalent install pattern is"
Write-Host "  cp tools/git_hooks/pre-commit .git/hooks/pre-commit"
Write-Host "  chmod +x .git/hooks/pre-commit"
Write-Host ""
Write-Host "To verify operationally:"
Write-Host "  1. Stage a MANIFEST.toml change (e.g., add a fake pkg)"
Write-Host "  2. Attempt git commit"
Write-Host "  3. Hook should refuse with a §8.5 install-matrix gap message"
