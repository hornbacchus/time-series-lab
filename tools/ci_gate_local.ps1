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


The parity step is diagnosable (H1, after two RED runs that died with exit 1 and no
verdict): Python runs unbuffered with faulthandler on, the runner brackets every check
with "[parity] start/done" lines, and the whole output streams to a log under %TEMP%
whose path is printed. A RED parity step then names the failing checks, or the check
the process died in, plus any fatal traceback.

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

function Invoke-ParityStep {
    param([string] $Name, [string[]] $PyArgs)
    if ($script:failed) {
        $script:rows += [pscustomobject]@{ Step = $Name; Code = "-"; Result = "SKIPPED (fail-fast)" }
        return
    }
    $log = Join-Path $env:TEMP ("ci_gate_parity_{0:yyyyMMdd_HHmmss}.log" -f (Get-Date))
    Write-Host ""
    Write-Host "=== $Name ===" -ForegroundColor Cyan
    Write-Host "Full output: $log"
    # Stream every line to the log as it arrives (a crash keeps everything up to the
    # crash); echo only the per-check progress lines.
    & python @PyArgs 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log |
        Where-Object { $_ -match '^\[parity\] (start|done) ' } | ForEach-Object { Write-Host "  $_" }
    $code = $LASTEXITCODE
    $out = if (Test-Path $log) { Get-Content $log -Raw } else { "" }
    if ($null -eq $out) { $out = "" }

    $overall = [regex]::Match($out, '(?m)^overall:.*$').Value.Trim()
    $ok = (@(0, 2, 4) -contains $code) -and $overall
    $note = if ($overall) { "exit $code | $overall" } else { "exit $code, no 'overall:' line -> the run did not complete" }
    $script:rows += [pscustomobject]@{ Step = $Name; Code = $code; Result = $(if ($ok) { "OK ($note)" } else { "FAIL ($note)" }) }
    if ($ok) { return }

    $script:failed = $true
    Write-Host "--- diagnosis ---" -ForegroundColor Yellow
    $named = $false
    # Checks that finished with a failing outcome (from the progress lines; the result
    # lines only exist if the run completed).
    $bad = [regex]::Matches($out, '(?m)^\[parity\] done (\S+) (BLOCK|ERROR)\b') |
        ForEach-Object { "$($_.Groups[1].Value) $($_.Groups[2].Value)" }
    if ($bad) {
        $named = $true
        Write-Host "Failing checks:" -ForegroundColor Yellow
        $bad | ForEach-Object { Write-Host "  $_" }
    }
    if (-not $overall) {
        $started = [regex]::Matches($out, '(?m)^\[parity\] start (\S+)') | ForEach-Object { $_.Groups[1].Value }
        $finished = @([regex]::Matches($out, '(?m)^\[parity\] done (\S+)') | ForEach-Object { $_.Groups[1].Value })
        $open = @($started | Where-Object { $finished -notcontains $_ })
        if ($open) {
            $named = $true
            Write-Host "The process died (exit $code) while running: $($open[-1])" -ForegroundColor Yellow
        }
        elseif (-not $started) {
            $named = $true
            Write-Host "The process died (exit $code) before the first check started (discovery or import)." -ForegroundColor Yellow
        }
        else {
            $named = $true
            Write-Host "The process died (exit $code) after the last check finished ($($finished[-1])), while reporting results." -ForegroundColor Yellow
        }
    }
    $fatal = [regex]::Match($out, '(?s)(Fatal Python error|Windows fatal exception|Traceback \(most recent call last\)).*')
    if ($fatal.Success) {
        Write-Host "Fatal output (first 40 lines):" -ForegroundColor Yellow
        Write-Host (($fatal.Value -split "`n" | Where-Object { $_ -notmatch '^Extension modules:' } |
            Select-Object -First 40) -join "`n")
    }
    if (-not $named) {
        Write-Host "Exit $code with an 'overall:' line but no BLOCK/ERROR check recorded; see the log." -ForegroundColor Yellow
    }
    Write-Host "--- last 25 lines ($log) ---" -ForegroundColor Yellow
    Write-Host (($out -split "`n" | Select-Object -Last 25) -join "`n")
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
Invoke-ParityStep -Name "reference_parity --tier fast" `
    -PyArgs @("-u", "-X", "faulthandler", "-m", "reference_parity", "--tier", "fast", "--progress")

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
