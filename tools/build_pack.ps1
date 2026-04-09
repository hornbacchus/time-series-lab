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
    Copy-Item "$techSource\*" $techPack -Recurse -Force
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

# Installer executable
$installerOutput = Join-Path $RepoRoot "src\TSL.Installer\bin\x64\Release\net48"
if (Test-Path $installerOutput) {
    Copy-Item "$installerOutput\TSL.Installer.exe" $packDir -Force
}

# 5) Prepare embedded Python runtime
Write-Host "`n--- Preparing Python runtime ---" -ForegroundColor Yellow
$pythonDir = Join-Path $packDir "python_runtime"
$pythonZip = Join-Path $packDir "python_runtime.zip"
$pyVersion = "3.11.9"
$pyUrl = "https://www.python.org/ftp/python/$pyVersion/python-$pyVersion-embed-amd64.zip"
$pyDownload = Join-Path $RepoRoot "build\python-embed.zip"

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

    # Enable pip: uncomment "import site" in python311._pth
    $pthFile = Get-ChildItem $pythonDir -Filter "python*._pth" | Select-Object -First 1
    if ($pthFile) {
        $content = Get-Content $pthFile.FullName -Raw
        $content = $content -replace '#\s*import site', 'import site'
        Set-Content $pthFile.FullName $content -NoNewline
        Write-Host "Enabled site-packages in $($pthFile.Name)"
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

    # Install locked dependencies
    $lockFile = Join-Path $RepoRoot "engine\requirements.lock.txt"
    if (Test-Path $lockFile) {
        Write-Host "Installing dependencies from requirements.lock.txt..."
        & $pythonExe -m pip install --no-warn-script-location -r $lockFile 2>&1 | ForEach-Object {
            if ($_ -match "Successfully installed") { Write-Host "  $_" -ForegroundColor Gray }
        }
    }

    # Install optional dependencies (best-effort)
    $optionalPkgs = @("lightgbm", "emd", "xgboost", "prophet")
    foreach ($pkg in $optionalPkgs) {
        Write-Host "  Installing optional: $pkg" -ForegroundColor Gray
        & $pythonExe -m pip install --no-warn-script-location $pkg 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "  Optional package '$pkg' failed to install (non-fatal)"
        }
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

Write-Host "`n=== Pack complete ===" -ForegroundColor Cyan
Write-Host "Output: $packDir"
Write-Host "Contents:"
Get-ChildItem $packDir -Recurse | ForEach-Object {
    $rel = $_.FullName.Replace($packDir, "")
    Write-Host "  $rel"
}

# Summary
$zipSize = if (Test-Path $pythonZip) { [math]::Round((Get-Item $pythonZip).Length / 1MB, 1) } else { "?" }
$totalSize = [math]::Round((Get-ChildItem $packDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
Write-Host "`n=== Summary ===" -ForegroundColor Cyan
Write-Host "  Python runtime zip: ${zipSize} MB"
Write-Host "  Total pack size:    ${totalSize} MB"
Write-Host "  To distribute: copy $packDir to target machine and run TSL.Installer.exe"
