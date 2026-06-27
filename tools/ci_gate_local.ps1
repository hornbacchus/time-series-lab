#requires -Version 5
<#
ci_gate_local.ps1 — local pre-commit gate mirroring .github/workflows/parity-fast.yml.

Runs the full CI verification step SET (NOT just --tier fast) to completion, captures
each exit code, applies the documented CI exit-code policy, and asserts the parity run
actually COMPLETED (printed an "overall:" line — the anti-truncation guard for the
classifier-outage class: a truncated run can leave a BLOCK-grep empty and look clean).
Refuses GREEN unless every step ran to completion with an acceptable exit code.

Built in Phase 4a-harden (finding #6) to close the Phase-3 gap: local verification ran
only `--tier fast`; CI failed at `validate_install_matrix` (an EARLIER step that local
checks never ran). Run this before EVERY commit.

CI exit-code policy (per parity-fast.yml + master plan §3.3 / P-1 §6.4):
  0 = PASS/SKIP -> green ; 1 = BLOCK -> red ; 2 = CAVEAT -> green ;
  3 = ERROR -> red ; 4 = DOCUMENTED-DIVERGENCE -> green.

Step order is fast-first (early failure feedback on a broken cheap step); the step SET
and the GREEN verdict are identical to CI. Fail-fast: stops at the first failing step.

Exit 0 = GREEN (every step acceptable). Exit 1 = RED (a step failed or ran incomplete).
#>

$ErrorActionPreference = "Continue"
$repo = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = (Join-Path $repo "tools")
Set-Location $repo

$script:rows = @()
$script:failed = $false

function Invoke-GateStep {
    param(
        [string]   $Name,
        [string[]] $PyArgs,
        [int[]]    $Accept,
        [string]   $MustContain = $null
    )
    if ($script:failed) {
        $script:rows += [pscustomobject]@{ Step = $Name; Code = "-"; Result = "SKIPPED (fail-fast)" }
        return
    }
    Write-Host ""
    Write-Host "=== $Name ===" -ForegroundColor Cyan
    $out = (& python @PyArgs 2>&1 | Out-String)
    $code = $LASTEXITCODE
    $ok = $Accept -contains $code
    $note = "exit $code"
    if ($ok -and $MustContain) {
        if ($out -notmatch [regex]::Escape($MustContain)) {
            $ok = $false
            $note = "exit $code but '$MustContain' NOT printed -> incomplete/crashed run"
        }
        else {
            $line = ($out | Select-String -Pattern 'overall:.*' | Select-Object -Last 1)
            if ($line) { $note = "exit $code | $($line.Matches.Value.Trim())" }
        }
    }
    $script:rows += [pscustomobject]@{ Step = $Name; Code = $code; Result = $(if ($ok) { "OK ($note)" } else { "FAIL ($note)" }) }
    if (-not $ok) {
        $script:failed = $true
        Write-Host "--- last 25 lines of failing step ---" -ForegroundColor Yellow
        Write-Host (($out -split "`n" | Select-Object -Last 25) -join "`n")
    }
}

Write-Host "ci_gate_local — mirroring parity-fast.yml (repo: $repo)" -ForegroundColor White

# Fast gates first (cheap, early failure feedback) ...
Invoke-GateStep -Name "validate_install_matrix" `
    -PyArgs @("tools/validate_install_matrix.py") -Accept @(0)
Invoke-GateStep -Name "catalog_key_alignment guard" `
    -PyArgs @("tools/reference_parity/catalog_key_alignment.py") -Accept @(0)
Invoke-GateStep -Name "engine unit tests" `
    -PyArgs @("-m", "unittest", "discover", "-s", "engine/tests", "-p", "test_*.py", "-t", ".") -Accept @(0)
# ... then the slow parity suite (with the completion / anti-truncation guard).
Invoke-GateStep -Name "reference_parity --tier fast" `
    -PyArgs @("-m", "reference_parity", "--tier", "fast") -Accept @(0, 2, 4) -MustContain "overall:"

Write-Host ""
Write-Host "================ ci_gate_local summary ================" -ForegroundColor White
$script:rows | Format-Table -AutoSize | Out-String | Write-Host
if ($script:failed) {
    Write-Host "RESULT: RED — fix the failing step before committing." -ForegroundColor Red
    exit 1
}
else {
    Write-Host "RESULT: GREEN — all CI steps passed to completion." -ForegroundColor Green
    exit 0
}
