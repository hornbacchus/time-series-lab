#Requires -Version 5.1
# install.ps1 - Time Series Lab per-user install (work-PC primary path).
# Windows PowerShell 5.1 grammar ONLY (no ternary, no ??, no ?.).
# Run from the EXTRACTED bundle root (next to python_runtime.zip):
#   powershell -ExecutionPolicy Bypass -File .\install.ps1
# (-ExecutionPolicy Bypass is process-scoped; it overrides machine policy
#  without touching it. Unblock the OUTER ZIP before extracting - see
#  docs\DEPLOYMENT.md.)
# No admin rights required: %LOCALAPPDATA% files + HKCU registry only.

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Outcome flags pre-initialized (GMC B.5: every terminal state must be
# nameable; variables read in catch/finally must exist).
$InstallOutcome  = "NotStarted"   # Copied | CopyFailed
$RegisterOutcome = "NotStarted"   # Registered | AlreadyRegistered | RegisterFailed
$FirstInstall    = $false
$RuntimeAction   = "None"         # Extracted | Refreshed | Kept
$FailReason      = ""

$SourceDir   = $PSScriptRoot
$InstallBase = Join-Path $env:LOCALAPPDATA "TimeSeriesLab"

# Per-user + per-invocation scratch (GMC B.3) + stale sweep
$ScratchRoot = Join-Path $env:TEMP "TSL_Install"
if (Test-Path $ScratchRoot) {
    Get-ChildItem $ScratchRoot -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-1) } |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}
$Scratch = Join-Path $ScratchRoot ([Guid]::NewGuid().ToString().Substring(0, 8))
New-Item -ItemType Directory -Path $Scratch -Force | Out-Null

function Get-OfficeBitness {
    # Returns 'x64' or 'x86'. Sources in order: ClickToRun Platform,
    # Outlook Bitness, default x64 (Excel 365 default).
    $c2r = "HKLM:\SOFTWARE\Microsoft\Office\ClickToRun\Configuration"
    if (Test-Path $c2r) {
        $plat = (Get-ItemProperty $c2r -ErrorAction SilentlyContinue).Platform
        if ($plat -eq "x86") { return "x86" }
        if ($plat -eq "x64") { return "x64" }
    }
    $ol = "HKLM:\SOFTWARE\Microsoft\Office\16.0\Outlook"
    if (Test-Path $ol) {
        $bit = (Get-ItemProperty $ol -ErrorAction SilentlyContinue).Bitness
        if ($bit -eq "x86") { return "x86" }
    }
    return "x64"
}

try {
    Write-Host "=== Time Series Lab install ===" -ForegroundColor Cyan
    Write-Host "Source: $SourceDir"
    Write-Host "Target: $InstallBase"
    $FirstInstall = -not (Test-Path (Join-Path $InstallBase "addin"))

    # 1) Copy the tree (addin / engine / resources / docs)
    foreach ($sub in @("addin", "engine", "resources", "docs")) {
        $src = Join-Path $SourceDir $sub
        if (Test-Path $src) {
            $dst = Join-Path $InstallBase $sub
            Write-Host "Copying $sub ..."
            robocopy $src $dst /E /XD runtime /NFL /NDL /NJH /NJS /NP | Out-Null
            if ($LASTEXITCODE -ge 8) { throw "robocopy $sub failed (code $LASTEXITCODE)" }
        }
    }
    New-Item -ItemType Directory -Path (Join-Path $InstallBase "logs") -Force | Out-Null

    # 2) Runtime: VERSION.txt-driven refresh (matches TSL.Installer semantics)
    $runtimeZip = Join-Path $SourceDir "python_runtime.zip"
    $runtimeDir = Join-Path $InstallBase "engine\runtime"
    $packMarker = Join-Path $SourceDir "VERSION.txt"
    $instMarker = Join-Path $InstallBase "VERSION.txt"
    if (Test-Path $runtimeZip) {
        $markerDiffers = $false
        if (Test-Path $packMarker) {
            if (-not (Test-Path $instMarker)) { $markerDiffers = $true }
            elseif ((Get-Content $packMarker -Raw) -ne (Get-Content $instMarker -Raw)) { $markerDiffers = $true }
        }
        $pyPresent = Test-Path (Join-Path $runtimeDir "python.exe")
        if (-not $pyPresent -or $markerDiffers) {
            if (Test-Path $runtimeDir) {
                Write-Host "Refreshing Python runtime (marker changed)..."
                Remove-Item $runtimeDir -Recurse -Force
                $RuntimeAction = "Refreshed"
            } else {
                Write-Host "Extracting Python runtime..."
                $RuntimeAction = "Extracted"
            }
            Add-Type -AssemblyName System.IO.Compression.FileSystem
            [System.IO.Compression.ZipFile]::ExtractToDirectory($runtimeZip, $runtimeDir)
        } else {
            $RuntimeAction = "Kept"
            Write-Host "Python runtime up to date (marker match)."
        }
        if (Test-Path $packMarker) { Copy-Item $packMarker $instMarker -Force }
    }

    # 3) DEFENSIVE unblock over the installed tree. File.Copy/robocopy
    # propagate Zone.Identifier; modern Excel HARD-BLOCKS MotW XLLs (silently
    # or with a policy banner), so this is load-bearing even after an
    # unblock-at-ZIP transfer.
    Write-Host "Unblocking installed files (MotW)..."
    Get-ChildItem $InstallBase -Recurse -File -ErrorAction SilentlyContinue |
        Unblock-File -ErrorAction SilentlyContinue
    $InstallOutcome = "Copied"

    # 4) Register the bitness-matching XLL (HKCU OPEN<n>, first free slot)
    $bitness = Get-OfficeBitness
    if ($bitness -eq "x64") { $xllName = "TimeSeriesLab-AddIn64.xll" }
    else { $xllName = "TimeSeriesLab-AddIn.xll" }
    $xllPath = Join-Path $InstallBase ("addin\" + $xllName)
    if (-not (Test-Path $xllPath)) { throw "XLL not found: $xllPath (Office bitness $bitness)" }
    $openValue = '/R "' + $xllPath + '"'

    $optKey = "HKCU:\Software\Microsoft\Office\16.0\Excel\Options"
    if (-not (Test-Path $optKey)) { New-Item -Path $optKey -Force | Out-Null }
    $props = Get-ItemProperty $optKey
    $slot = $null
    $already = $false
    foreach ($i in 0..19) {
        if ($i -eq 0) { $name = "OPEN" } else { $name = "OPEN$i" }
        $cur = $null
        if ($props.PSObject.Properties.Name -contains $name) { $cur = $props.$name }
        if ($cur -and ($cur -like "*TimeSeriesLab-AddIn*")) { $slot = $name; break }
        if (-not $cur -and -not $slot) { $slot = $name }
        if ($cur -and ($cur -eq $openValue)) { $already = $true }
    }
    if ($null -eq $slot) { throw "No free OPEN slot (OPEN..OPEN19 all used)" }
    Set-ItemProperty -Path $optKey -Name $slot -Value $openValue
    if ($already) { $RegisterOutcome = "AlreadyRegistered" } else { $RegisterOutcome = "Registered" }
    Write-Host "Registered $xllName ($bitness) at $slot"
}
catch {
    $FailReason = $_.Exception.Message
    if ($InstallOutcome -ne "Copied") { $InstallOutcome = "CopyFailed" }
    else { $RegisterOutcome = "RegisterFailed" }
}
finally {
    Remove-Item $Scratch -Recurse -Force -ErrorAction SilentlyContinue
}

# ── TWO-AXIS HONEST EPILOGUE (GMC B.5: never print green over a failure;
#    install outcome dominant) ─────────────────────────────────────────────
Write-Host ""
Write-Host "==================== INSTALL RESULT ====================" -ForegroundColor Cyan
if ($InstallOutcome -eq "CopyFailed") {
    Write-Host "INSTALL FAILED - NOTHING (OR ONLY PART) WAS COPIED" -ForegroundColor Red
    Write-Host "Reason: $FailReason" -ForegroundColor Red
    Write-Host "No registration was attempted. Fix the cause and re-run."
    exit 1
}
if ($RegisterOutcome -eq "RegisterFailed") {
    Write-Host "FILES INSTALLED - EXCEL REGISTRATION FAILED" -ForegroundColor Yellow
    Write-Host "Reason: $FailReason" -ForegroundColor Yellow
    Write-Host "Manual registration: Excel > File > Options > Add-ins >"
    Write-Host "  Manage: Excel Add-ins > Go... > Browse... >"
    Write-Host "  $InstallBase\addin\ > select the XLL > OK > restart Excel."
    exit 1
}
Write-Host "INSTALL COMPLETE (runtime: $RuntimeAction; registration: $RegisterOutcome)" -ForegroundColor Green
if ($FirstInstall) {
    Write-Host ""
    Write-Host "FIRST INSTALL:" -ForegroundColor Yellow
    Write-Host "  Restart Excel. The 'Time Series Lab' tab should appear."
    Write-Host "  If it does not: File > Options > Add-ins > Manage: Excel"
    Write-Host "  Add-ins > Go... > tick 'Time Series Lab' > OK > restart Excel."
    Write-Host "  Still absent? See docs\DEPLOYMENT.md symptom table (MotW/policy)."
} else {
    Write-Host "Upgrade: restart Excel to load the new build."
}
exit 0
