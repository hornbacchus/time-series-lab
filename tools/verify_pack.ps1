# verify_pack.ps1 - Packed-runtime verification gate (F4).
# Runs the PACKED python.exe against the PACKED engine tree (never the dev
# tree). Wired as the MANDATORY final step of build_pack.ps1; red => the pack
# fails and no transfer artifact is produced. Can also be run standalone:
#   .\tools\verify_pack.ps1 -PackDir .\build\pack
#
# Sub-checks (a-g, per the Phase-2 deployment dispatch):
#   a. engine unit suite (unittest discover, packed tree)
#   b. one classical technique end-to-end (adf via dispatch)
#   c. workbook-input read (openpyxl -> pandas.read_excel roundtrip)
#   d. numba imports AND the BYF JIT warmer actually compiles
#   e. one Prophet fit, or its honest-degrade path confirmed
#   f. torch-absent DL technique: sklearn fallback VISIBLY disclosed
#   g. pipe-protocol smoke: engine_worker serves one framed request
param(
    [Parameter(Mandatory = $true)][string]$PackDir
)
$ErrorActionPreference = "Stop"

$PackDir = (Resolve-Path $PackDir).Path
$engineDir = Join-Path $PackDir "engine"
$runtimeZip = Join-Path $PackDir "python_runtime.zip"
$driver = Join-Path $PSScriptRoot "verify_pack_driver.py"

Write-Host "=== verify_pack: packed-runtime gate ===" -ForegroundColor Cyan
Write-Host "Pack: $PackDir"

# The pack holds the runtime as a zip (the installer extracts it on the
# target). Extract a scratch copy to exercise it - per-user + per-invocation
# temp (GMC B.3 pattern), swept afterwards.
$scratch = Join-Path $env:TEMP ("TSL_VerifyPack\" + [Guid]::NewGuid().ToString().Substring(0, 8))
$sweepRoot = Join-Path $env:TEMP "TSL_VerifyPack"
if (Test-Path $sweepRoot) {
    Get-ChildItem $sweepRoot -Directory | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-1) } |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Path $scratch -Force | Out-Null
$runtimeDir = Join-Path $scratch "runtime"
Write-Host "Extracting runtime scratch copy to $runtimeDir ..."
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::ExtractToDirectory($runtimeZip, $runtimeDir)
$py = Join-Path $runtimeDir "python.exe"
if (-not (Test-Path $py)) { Write-Error "python.exe not found in runtime zip"; exit 1 }

$failed = @()
$results = @()

function Invoke-SubCheck {
    param([string]$Name, [scriptblock]$Body)
    Write-Host "`n--- [$Name] ---" -ForegroundColor Yellow
    & $Body
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[$Name] PASS" -ForegroundColor Green
        $script:results += "PASS  $Name"
    } else {
        Write-Host "[$Name] FAIL (exit $LASTEXITCODE)" -ForegroundColor Red
        $script:results += "FAIL  $Name"
        $script:failed += $Name
    }
}

Push-Location $PackDir
try {
    # 0) the packed interpreter version must MATCH the VERSION.txt marker
    # (added after a stale download cache shipped a 3.11.9 runtime under a
    # 3.14.3 label - the gate must catch exactly that class)
    Invoke-SubCheck "0: interpreter == VERSION.txt marker" {
        $actual = (& $py --version) -replace "^Python\s+", ""
        $marker = ""
        $vt = Join-Path $PackDir "VERSION.txt"
        if (Test-Path $vt) {
            foreach ($line in Get-Content $vt) {
                if ($line -like "python=*") { $marker = $line.Substring(7) }
            }
        }
        Write-Host "  packed python: $actual / marker: $marker"
        $versionOk = ($actual -eq $marker -and $marker -ne "")
        # containment: every sys.path entry must live INSIDE the runtime
        # (catches user-site / foreign-.pth leakage into the artifact)
        $paths = & $py -c "import sys; [print(p) for p in sys.path if p]"
        $leaks = @()
        foreach ($p in $paths) {
            if (-not $p.StartsWith($runtimeDir, [System.StringComparison]::OrdinalIgnoreCase)) { $leaks += $p }
        }
        if ($leaks.Count -gt 0) {
            Write-Host "  sys.path LEAKS outside the runtime:" -ForegroundColor Red
            $leaks | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
        } else {
            Write-Host "  sys.path fully contained in the runtime"
        }
        if ($versionOk -and $leaks.Count -eq 0) { $global:LASTEXITCODE = 0 }
        else { $global:LASTEXITCODE = 1 }
    }
    # a) engine unit suite against the PACKED tree (unittest, no extra deps;
    #    -t engine makes engine/ the import root: `interpretation`,
    #    `techniques` resolve against the PACKED tree)
    Invoke-SubCheck "a: engine unit suite" {
        & $py -m unittest discover -s engine/tests -p "test_*.py" -t engine
    }
    # b-g) driver sub-checks (cwd = packed engine dir so `techniques` resolves)
    Push-Location $engineDir
    try {
        Invoke-SubCheck "b: classical technique end-to-end" { & $py $driver classical }
        Invoke-SubCheck "c: workbook-input read (openpyxl)" { & $py $driver workbook }
        Invoke-SubCheck "d: numba + BYF JIT warmer"         { & $py $driver numba }
        Invoke-SubCheck "e: prophet fit / honest degrade"   { & $py $driver prophet }
        Invoke-SubCheck "f: DL sklearn-fallback disclosure" { & $py $driver dl }
        Invoke-SubCheck "g: pipe-protocol smoke"            { & $py $driver pipe }
    } finally { Pop-Location }

    # h) LOCK FIDELITY: the installed set inside the PACKED runtime must equal
    # the two lock files EXACTLY (names + versions). The install step's
    # success-signaling once lied (swallowed failure -> fresh-resolve); the
    # gate asserts the OUTCOME, never the installer's claim (the Flag A
    # recompute-don't-trust-the-self-report principle applied to packaging).
    # Exclusions: pip (get-pip bootstrap, unpinned by design) + wheel (get-pip
    # side-install when present).
    Invoke-SubCheck "h: lock fidelity (freeze == locks)" {
        $excluded = @("pip", "wheel")
        function NormName([string]$n) { return $n.ToLower().Replace("_", "-") }
        $expected = @{}
        foreach ($lf in @("engine\requirements.lock.txt", "engine\requirements.optional.lock.txt")) {
            $lfPath = Join-Path $PackDir $lf
            if (Test-Path $lfPath) {
                foreach ($line in Get-Content $lfPath) {
                    $line = $line.Trim()
                    if ($line -and -not $line.StartsWith("#")) {
                        $parts = $line -split "=="
                        $expected[(NormName $parts[0])] = $parts[1]
                    }
                }
            }
        }
        $mismatch = @()
        $seen = @{}
        foreach ($line in (& $py -m pip freeze 2>$null)) {
            if ($line -notmatch "==") { continue }
            $parts = $line -split "=="
            $name = NormName $parts[0]
            if ($excluded -contains $name) { continue }
            $seen[$name] = $true
            if (-not $expected.ContainsKey($name)) { $mismatch += "EXTRA: $line" }
            elseif ($expected[$name] -ne $parts[1]) { $mismatch += "DRIFT: $name installed $($parts[1]) != locked $($expected[$name])" }
        }
        foreach ($name in $expected.Keys) {
            if (-not $seen.ContainsKey($name)) { $mismatch += "MISSING: $name==$($expected[$name])" }
        }
        if ($mismatch.Count -gt 0) {
            $mismatch | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
            $global:LASTEXITCODE = 1
        } else {
            Write-Host "  freeze == locks exactly ($($expected.Count) pins; excluded: $($excluded -join ', '))"
            $global:LASTEXITCODE = 0
        }
    }
} finally {
    Pop-Location
    Remove-Item $scratch -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "`n=== verify_pack summary ===" -ForegroundColor Cyan
$results | ForEach-Object { Write-Host "  $_" }
if ($failed.Count -gt 0) {
    Write-Host "GATE RED: $($failed -join '; ')" -ForegroundColor Red
    exit 1
}
Write-Host "GATE GREEN (9/9)." -ForegroundColor Green
exit 0
