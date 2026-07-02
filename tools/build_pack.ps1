# build_pack.ps1 - Build + pack XLL + engine assets + docs for installer
# Run from repo root: .\tools\build_pack.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path "$RepoRoot\TimeSeriesLab.sln")) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}

Write-Host "=== Time Series Lab Build & Pack ===" -ForegroundColor Cyan
Write-Host "Repo root: $RepoRoot"

# 1) Build the solution (prefer VS MSBuild for WPF/WinFX targets)
Write-Host "`n--- Building solution (Release|x64) ---" -ForegroundColor Yellow
$slnPath = Join-Path $RepoRoot "TimeSeriesLab.sln"

$msbuild = $null
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path $vswhere)) { $vswhere = "$env:ProgramFiles\Microsoft Visual Studio\Installer\vswhere.exe" }
if (Test-Path $vswhere) {
    $vsPath = & $vswhere -latest -requires Microsoft.Component.MSBuild -property installationPath 2>$null
    if ($vsPath) {
        $msbuild = Join-Path $vsPath "MSBuild\Current\Bin\MSBuild.exe"
        if (-not (Test-Path $msbuild)) { $msbuild = $null }
    }
}

if ($msbuild) {
    Write-Host "Using VS MSBuild: $msbuild"
    & $msbuild $slnPath -p:Configuration=Release -p:Platform=x64 -t:Build -v:minimal -restore
} else {
    Write-Host "VS MSBuild not found, falling back to dotnet build"
    & dotnet build $slnPath -c Release -p:Platform=x64
}
if ($LASTEXITCODE -ne 0) {
    Write-Error "Build failed!"
    exit 1
}
Write-Host "Build succeeded." -ForegroundColor Green

# 2) Generate UDF catalog from C# metadata
Write-Host "`n--- Generating UDF catalog ---" -ForegroundColor Yellow
$generateUdf = Join-Path $RepoRoot "tools\generate_udf_catalog.ps1"
if (Test-Path $generateUdf) {
    & $generateUdf
}

# 3) Generate User Guide
Write-Host "`n--- Generating User Guide ---" -ForegroundColor Yellow
$generateGuide = Join-Path $RepoRoot "tools\generate_user_guide.py"
if (Test-Path $generateGuide) {
    python $generateGuide
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "User guide generation failed (non-fatal)"
    }
}

# 4) Pack output for installer
Write-Host "`n--- Packing installer assets ---" -ForegroundColor Yellow
$packDir = Join-Path $RepoRoot "build\pack"
if (Test-Path $packDir) { Remove-Item $packDir -Recurse -Force }
New-Item -ItemType Directory -Path $packDir -Force | Out-Null

# Add-in output
$addinOutput = Join-Path $RepoRoot "src\TSL.AddIn\bin\x64\Release\net48"
$addinPack = Join-Path $packDir "addin"
New-Item -ItemType Directory -Path $addinPack -Force | Out-Null
if (Test-Path $addinOutput) {
    Copy-Item "$addinOutput\*" $addinPack -Recurse -Force
}

# Engine
$engineSource = Join-Path $RepoRoot "engine"
$enginePack = Join-Path $packDir "engine"
New-Item -ItemType Directory -Path $enginePack -Force | Out-Null
Copy-Item "$engineSource\*.py" $enginePack -Force
Copy-Item "$engineSource\*.txt" $enginePack -Force
$techSource = Join-Path $engineSource "techniques"
$techPack = Join-Path $enginePack "techniques"
New-Item -ItemType Directory -Path $techPack -Force | Out-Null
if (Test-Path $techSource) {
    # Exclude __pycache__ (dev-interpreter bytecode + numba .nbc caches are
    # useless/invalid under the packed runtime; size + noise)
    robocopy $techSource $techPack /E /XD __pycache__ /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { Write-Error "Engine techniques copy failed (robocopy $LASTEXITCODE)"; exit 1 }
    $global:LASTEXITCODE = 0
}
# interpretation/ is a PACKAGE DIRECTORY at engine root (the plain-language
# layer feeding the C# writer) - the old root-*.py-only copy silently
# omitted it from every pack (caught by the verify_pack gate, P-D6)
$interpSource = Join-Path $engineSource "interpretation"
if (Test-Path $interpSource) {
    robocopy $interpSource (Join-Path $enginePack "interpretation") /E /XD __pycache__ /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { Write-Error "Engine interpretation copy failed (robocopy $LASTEXITCODE)"; exit 1 }
    $global:LASTEXITCODE = 0
}
# Engine unit tests ride the pack so the verify_pack gate runs them against
# the PACKED tree (never the dev tree)
$testsSource = Join-Path $engineSource "tests"
if (Test-Path $testsSource) {
    # test_harness.py excluded: it imports the reference_parity harness
    # (dev-tree tooling under tools/, deliberately NOT shipped) - it tests
    # the dev harness integration, not the shipped engine.
    robocopy $testsSource (Join-Path $enginePack "tests") /E /XD __pycache__ /XF test_harness.py /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { Write-Error "Engine tests copy failed (robocopy $LASTEXITCODE)"; exit 1 }
    $global:LASTEXITCODE = 0
}

# Resources
$resSource = Join-Path $RepoRoot "resources"
$resPack = Join-Path $packDir "resources"
if (Test-Path $resSource) {
    Copy-Item $resSource $resPack -Recurse -Force
}

# Docs
$docsSource = Join-Path $RepoRoot "docs"
$docsPack = Join-Path $packDir "docs"
New-Item -ItemType Directory -Path $docsPack -Force | Out-Null
$guideDoc = Join-Path $docsSource "TimeSeriesLab_UserGuide.docx"
if (Test-Path $guideDoc) {
    Copy-Item $guideDoc $docsPack -Force
}
$deployDoc = Join-Path $docsSource "DEPLOYMENT.md"
if (Test-Path $deployDoc) {
    Copy-Item $deployDoc $docsPack -Force
}

# Installer executable
$installerOutput = Join-Path $RepoRoot "src\TSL.Installer\bin\x64\Release\net48"
if (Test-Path $installerOutput) {
    Copy-Item "$installerOutput\TSL.Installer.exe" $packDir -Force
}

# install.ps1 (the work-PC primary install path) at pack root
$installPs1 = Join-Path $RepoRoot "tools\install.ps1"
if (Test-Path $installPs1) {
    Copy-Item $installPs1 $packDir -Force
}

# 5) Prepare embedded Python runtime
Write-Host "`n--- Preparing Python runtime ---" -ForegroundColor Yellow
$pythonDir = Join-Path $packDir "python_runtime"
$pythonZip = Join-Path $packDir "python_runtime.zip"
# 3.14.3 = the DEV/CI-validated interpreter (the whole parity + correctness
# campaign ran the engine under 3.14 + the versions in requirements.lock.txt;
# shipped == validated). Do NOT bump without re-pinning the locks from the
# validated env.
$pyVersion = "3.14.3"
$pyUrl = "https://www.python.org/ftp/python/$pyVersion/python-$pyVersion-embed-amd64.zip"
# VERSION-KEYED download cache: a bare "python-embed.zip" once served a stale
# 3.11.9 embeddable under a 3.14.3 label (caught by the verify_pack
# interpreter-version sub-check). The version in the filename invalidates the
# cache on every bump.
$pyDownload = Join-Path $RepoRoot "build\python-embed-$pyVersion.zip"

# Dev-built wheelhouse for sdist-only pins: hmmlearn==0.3.3 publishes no
# cp314 wheel, and pip build isolation is STRUCTURALLY broken under an
# embeddable ._pth (PYTHONPATH ignored -> setuptools.build_meta unavailable).
# The DEV interpreter (same 3.14.3/amd64 ABI, has the MSVC toolchain, and IS
# the validated environment) builds the wheel once; provisioning installs it
# via --find-links. Shipped == validated preserved at the BINARY level.
$wheelsDir = Join-Path $RepoRoot "build\wheels"
New-Item -ItemType Directory -Path $wheelsDir -Force | Out-Null
$sdistOnlyPins = @("hmmlearn==0.3.3", "ruptures==1.1.9")
foreach ($pin in $sdistOnlyPins) {
    $stem = ($pin -replace "==", "-") + "-cp314-*.whl"
    if (-not (Get-ChildItem $wheelsDir -Filter $stem -ErrorAction SilentlyContinue)) {
        Write-Host "Building dev wheel for sdist-only pin: $pin ..."
        python -m pip wheel $pin --no-deps -w $wheelsDir
        if ($LASTEXITCODE -ne 0) { Write-Error "Dev wheel build for $pin failed"; exit 1 }
    }
}

if (-not (Test-Path $pythonZip)) {
    # Download embeddable Python
    if (-not (Test-Path $pyDownload)) {
        Write-Host "Downloading Python $pyVersion embeddable (amd64)..."
        New-Item -ItemType Directory -Path (Split-Path $pyDownload) -Force | Out-Null
        Invoke-WebRequest -Uri $pyUrl -OutFile $pyDownload -UseBasicParsing
    }

    # Extract
    Write-Host "Extracting Python embeddable..."
    if (Test-Path $pythonDir) { Remove-Item $pythonDir -Recurse -Force }
    Expand-Archive -Path $pyDownload -DestinationPath $pythonDir -Force

    # Make site-packages importable WITHOUT site processing: a literal
    # "Lib\site-packages" path line instead of "import site". `import site`
    # re-enables the USER site dir (%APPDATA%\Python\PythonXY) when the
    # version matches the dev interpreter - the verify_pack gate caught the
    # dev user-site (and a foreign project's .pth) leaking into the packed
    # runtime's sys.path. The path-line keeps sys.path fully self-contained.
    $pthFile = Get-ChildItem $pythonDir -Filter "python*._pth" | Select-Object -First 1
    if ($pthFile) {
        $content = Get-Content $pthFile.FullName -Raw
        $content = $content -replace '#\s*import site', 'Lib\site-packages'
        Set-Content $pthFile.FullName $content -NoNewline
        Write-Host "Self-contained sys.path in $($pthFile.Name) (Lib\site-packages path line; no site processing)"
    }

    # Install pip via get-pip.py
    $getPip = Join-Path $RepoRoot "build\get-pip.py"
    if (-not (Test-Path $getPip)) {
        Write-Host "Downloading get-pip.py..."
        Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getPip -UseBasicParsing
    }

    $pythonExe = Join-Path $pythonDir "python.exe"
    Write-Host "Installing pip..."
    & $pythonExe $getPip --no-warn-script-location 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Error "pip bootstrap FAILED (exit $LASTEXITCODE)"; exit 1 }

    # Install locked dependencies (FAIL-LOUD: a swallowed core-install failure
    # once let the optional step fresh-resolve numpy/pandas/scipy - the
    # DP1-banned class occurring inside the provisioning script itself)
    $lockFile = Join-Path $RepoRoot "engine\requirements.lock.txt"
    if (Test-Path $lockFile) {
        Write-Host "Installing dependencies from requirements.lock.txt..."
        & $pythonExe -m pip install --no-warn-script-location --find-links $wheelsDir -r $lockFile 2>&1 | ForEach-Object {
            if ($_ -match "Successfully installed|ERROR|error:") { Write-Host "  $_" -ForegroundColor Gray }
        }
        if ($LASTEXITCODE -ne 0) { Write-Error "Core lock install FAILED (exit $LASTEXITCODE)"; exit 1 }
    }

    # Install optional dependencies (best-effort, PINNED at the dev-validated
    # versions via requirements.optional.lock.txt — DP2 set: lightgbm/xgboost/
    # prophet; torch+pymc excluded by ruling; emd dropped because the engine's
    # numpy fallback IS the validated path)
    $optLockFile = Join-Path $RepoRoot "engine\requirements.optional.lock.txt"
    if (Test-Path $optLockFile) {
        Write-Host "Installing optional dependencies from requirements.optional.lock.txt..."
        & $pythonExe -m pip install --no-warn-script-location --find-links $wheelsDir -r $optLockFile 2>&1 | ForEach-Object {
            if ($_ -match "Successfully installed|ERROR|error:") { Write-Host "  $_" -ForegroundColor Gray }
        }
        if ($LASTEXITCODE -ne 0) { Write-Error "Optional lock install FAILED (exit $LASTEXITCODE) - would leave the runtime in a partial state"; exit 1 }
    }

    # Clean up pip cache and unnecessary files to reduce size
    & $pythonExe -m pip cache purge 2>&1 | Out-Null
    Get-ChildItem $pythonDir -Recurse -Include "__pycache__", "*.pyc" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem $pythonDir -Recurse -Include "tests", "test" -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

    # Zip the runtime
    Write-Host "Creating python_runtime.zip..."
    Compress-Archive -Path "$pythonDir\*" -DestinationPath $pythonZip -Force

    # Remove unzipped directory (installer will extract from zip)
    Remove-Item $pythonDir -Recurse -Force
}
Write-Host "Python runtime ready: $pythonZip" -ForegroundColor Green

# 6) VERSION.txt at pack root — the bundle's traceability record
# (artifact -> validated commit lineage) AND the installer's runtime-refresh
# marker (both TSL.Installer.exe and install.ps1 re-extract the runtime when
# the installed marker differs from the pack marker).
$headHash = (& git -C $RepoRoot rev-parse --short HEAD 2>$null)
if (-not $headHash) { $headHash = "unknown" }
$versionLines = @(
    "commit=$headHash",
    "built=$(Get-Date -Format 'yyyy-MM-dd HH:mm')",
    "python=$pyVersion"
)
Set-Content -Path (Join-Path $packDir "VERSION.txt") -Value $versionLines -Encoding ASCII
Write-Host "VERSION.txt: commit=$headHash python=$pyVersion" -ForegroundColor Green

# 7) MANDATORY packed-runtime verification gate (the deployment analog of the
# GMC B.7 gates): runs the PACKED python against the PACKED engine tree.
# Red => the pack FAILS; no artifact ships without a green gate.
Write-Host "`n--- Packed-runtime verification gate (verify_pack.ps1) ---" -ForegroundColor Yellow
$verifyScript = Join-Path $RepoRoot "tools\verify_pack.ps1"
& $verifyScript -PackDir $packDir
if ($LASTEXITCODE -ne 0) {
    Write-Error "PACKED-RUNTIME GATE FAILED (exit $LASTEXITCODE) - the pack is NOT distributable. No transfer artifact was produced."
    exit 1
}
Write-Host "Packed-runtime gate GREEN." -ForegroundColor Green

# The gate ran the packed engine in place: sweep the bytecode/JIT caches it
# created (path-keyed numba caches are dead weight on the target anyway).
Get-ChildItem (Join-Path $packDir "engine") -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# 8) Transfer artifact: single outer ZIP + SHA-256 sidecar.
# Runbook (docs/DEPLOYMENT.md): UNBLOCK THIS ZIP BEFORE EXTRACTING on the
# target machine - extraction propagates Zone.Identifier to every file.
Write-Host "`n--- Creating transfer artifact ---" -ForegroundColor Yellow
$bundleZip = Join-Path $RepoRoot "build\TSL_Install_$headHash.zip"
if (Test-Path $bundleZip) { Remove-Item $bundleZip -Force }
Compress-Archive -Path "$packDir\*" -DestinationPath $bundleZip -Force
$sha = (Get-FileHash $bundleZip -Algorithm SHA256).Hash
Set-Content -Path "$bundleZip.sha256" -Value "$sha  $(Split-Path $bundleZip -Leaf)" -Encoding ASCII
$bundleSize = [math]::Round((Get-Item $bundleZip).Length / 1MB, 1)

# Summary
$zipSize = if (Test-Path $pythonZip) { [math]::Round((Get-Item $pythonZip).Length / 1MB, 1) } else { "?" }
$totalSize = [math]::Round((Get-ChildItem $packDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
Write-Host "`n=== Summary ===" -ForegroundColor Cyan
Write-Host "  Python runtime zip: ${zipSize} MB"
Write-Host "  Total pack size:    ${totalSize} MB"
Write-Host "  Transfer artifact:  $bundleZip (${bundleSize} MB)"
Write-Host "  SHA-256:            $sha"
Write-Host "  To distribute: transfer the ZIP, follow docs/DEPLOYMENT.md (unblock-at-ZIP first)."
