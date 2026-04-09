# smoke_tests.ps1 - End-to-end smoke tests for Time Series Lab
# Run from repo root: .\tools\smoke_tests.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path "$RepoRoot\TimeSeriesLab.sln")) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}

$pass = 0
$fail = 0
$total = 0

function Test-Assert {
    param([string]$Name, [scriptblock]$Test)
    $script:total++
    try {
        $result = & $Test
        if ($result) {
            Write-Host "  PASS: $Name" -ForegroundColor Green
            $script:pass++
        } else {
            Write-Host "  FAIL: $Name" -ForegroundColor Red
            $script:fail++
        }
    } catch {
        Write-Host "  FAIL: $Name - $_" -ForegroundColor Red
        $script:fail++
    }
}

Write-Host "=== Time Series Lab Smoke Tests ===" -ForegroundColor Cyan
Write-Host ""

# ─── File Structure Tests ───────────────────────────────────────────

Write-Host "--- File Structure ---" -ForegroundColor Yellow

Test-Assert "Solution file exists" {
    Test-Path (Join-Path $RepoRoot "TimeSeriesLab.sln")
}

Test-Assert "TSL.AddIn project exists" {
    Test-Path (Join-Path $RepoRoot "src\TSL.AddIn\TSL.AddIn.csproj")
}

Test-Assert "TSL.UI project exists" {
    Test-Path (Join-Path $RepoRoot "src\TSL.UI\TSL.UI.csproj")
}

Test-Assert "TSL.Installer project exists" {
    Test-Path (Join-Path $RepoRoot "src\TSL.Installer\TSL.Installer.csproj")
}

Test-Assert "Engine worker exists" {
    Test-Path (Join-Path $RepoRoot "engine\engine_worker.py")
}

Test-Assert "Technique catalog exists" {
    Test-Path (Join-Path $RepoRoot "resources\catalog\techniques_catalog.json")
}

Test-Assert "Requirements lock exists" {
    Test-Path (Join-Path $RepoRoot "engine\requirements.lock.txt")
}

Test-Assert "Excel-DNA .dna file exists" {
    Test-Path (Join-Path $RepoRoot "src\TSL.AddIn\TimeSeriesLab-AddIn.dna")
}

# ─── Catalog Validation ─────────────────────────────────────────────

Write-Host "`n--- Catalog Validation ---" -ForegroundColor Yellow

Test-Assert "Technique catalog is valid JSON" {
    $json = Get-Content (Join-Path $RepoRoot "resources\catalog\techniques_catalog.json") -Raw
    $catalog = $json | ConvertFrom-Json
    $catalog.techniques.Count -gt 0
}

Test-Assert "Catalog has 60+ techniques" {
    $json = Get-Content (Join-Path $RepoRoot "resources\catalog\techniques_catalog.json") -Raw
    $catalog = $json | ConvertFrom-Json
    $catalog.techniques.Count -ge 60
}

Test-Assert "All techniques have required fields" {
    $json = Get-Content (Join-Path $RepoRoot "resources\catalog\techniques_catalog.json") -Raw
    $catalog = $json | ConvertFrom-Json
    $allValid = $true
    foreach ($t in $catalog.techniques) {
        if (-not $t.id -or -not $t.name -or -not $t.category) {
            Write-Host "    Missing fields in: $($t.id)" -ForegroundColor DarkYellow
            $allValid = $false
        }
    }
    $allValid
}

# ─── Engine Tests ────────────────────────────────────────────────────

Write-Host "`n--- Engine Tests ---" -ForegroundColor Yellow

Test-Assert "Python available" {
    $result = python --version 2>&1
    $result -match "Python 3"
}

Test-Assert "Engine worker has no syntax errors" {
    $workerPath = Join-Path $RepoRoot "engine\engine_worker.py"
    $result = python -c "import py_compile; py_compile.compile('$($workerPath.Replace('\','/'))', doraise=True)" 2>&1
    $LASTEXITCODE -eq 0
}

Test-Assert "Technique base module has no syntax errors" {
    $basePath = Join-Path $RepoRoot "engine\techniques\base.py"
    if (Test-Path $basePath) {
        $result = python -c "import py_compile; py_compile.compile('$($basePath.Replace('\','/'))', doraise=True)" 2>&1
        $LASTEXITCODE -eq 0
    } else {
        $false
    }
}

# Check each technique file for syntax errors
$techDir = Join-Path $RepoRoot "engine\techniques"
if (Test-Path $techDir) {
    $techFiles = Get-ChildItem $techDir -Filter "*.py" | Where-Object { $_.Name -ne "__init__.py" }
    foreach ($tf in $techFiles) {
        Test-Assert "Technique $($tf.BaseName) compiles" {
            $result = python -c "import py_compile; py_compile.compile('$($tf.FullName.Replace('\','/'))', doraise=True)" 2>&1
            $LASTEXITCODE -eq 0
        }
    }
}

# ─── C# Source Validation ────────────────────────────────────────────

Write-Host "`n--- C# Source Files ---" -ForegroundColor Yellow

$csharpFiles = @(
    "src\TSL.AddIn\AddIn.cs",
    "src\TSL.AddIn\Ribbon.cs",
    "src\TSL.AddIn\RibbonXml.cs",
    "src\TSL.AddIn\EngineClient.cs",
    "src\TSL.AddIn\ResultStore.cs",
    "src\TSL.AddIn\ExcelWriter.cs",
    "src\TSL.AddIn\SelectionService.cs",
    "src\TSL.AddIn\TimeIndexDetector.cs",
    "src\TSL.AddIn\TechniqueCatalogService.cs",
    "src\TSL.AddIn\SettingsManager.cs",
    "src\TSL.AddIn\TaskPaneManager.cs",
    "src\TSL.AddIn\TriggerManager.cs",
    "src\TSL.AddIn\Functions\AutoFunctions.cs",
    "src\TSL.AddIn\Functions\ThoroughFunctions.cs"
)

foreach ($cs in $csharpFiles) {
    Test-Assert "C# file exists: $cs" {
        Test-Path (Join-Path $RepoRoot $cs)
    }
}

# ─── UDF Helpers / Shared Code ───────────────────────────────────────

Write-Host "`n--- Shared Code ---" -ForegroundColor Yellow

Test-Assert "UdfHelpers.cs exists" {
    Test-Path (Join-Path $RepoRoot "src\TSL.AddIn\Functions\UdfHelpers.cs")
}

# ─── UDF Catalog ─────────────────────────────────────────────────────

Write-Host "`n--- UDF Catalog ---" -ForegroundColor Yellow

Test-Assert "UDF catalog exists" {
    Test-Path (Join-Path $RepoRoot "resources\catalog\udf_catalog.json")
}

Test-Assert "UDF catalog is valid JSON with 10+ UDFs" {
    $udfPath = Join-Path $RepoRoot "resources\catalog\udf_catalog.json"
    if (Test-Path $udfPath) {
        $json = Get-Content $udfPath -Raw -Encoding UTF8
        $catalog = $json | ConvertFrom-Json
        $catalog.udfs.Count -ge 10
    } else { $false }
}

Test-Assert "TSL_RUN_THR has data_range_2 param in UDF catalog" {
    $udfPath = Join-Path $RepoRoot "resources\catalog\udf_catalog.json"
    if (Test-Path $udfPath) {
        $content = Get-Content $udfPath -Raw
        $content -match "data_range_2"
    } else { $false }
}

# ─── User Guide ──────────────────────────────────────────────────────

Write-Host "`n--- User Guide ---" -ForegroundColor Yellow

Test-Assert "User Guide .docx exists" {
    Test-Path (Join-Path $RepoRoot "docs\TimeSeriesLab_UserGuide.docx")
}

Test-Assert "User Guide source .md exists" {
    Test-Path (Join-Path $RepoRoot "docs\UserGuide_Source.md")
}

Test-Assert "User Guide contains non-adjacent selection section" {
    $mdPath = Join-Path $RepoRoot "docs\UserGuide_Source.md"
    if (Test-Path $mdPath) {
        $content = Get-Content $mdPath -Raw
        $content -match "Non-Adjacent"
    } else { $false }
}

Test-Assert "User Guide contains UDF reference with TSL_RUN_THR" {
    $mdPath = Join-Path $RepoRoot "docs\UserGuide_Source.md"
    if (Test-Path $mdPath) {
        $content = Get-Content $mdPath -Raw
        $content -match "TSL_RUN_THR"
    } else { $false }
}

# ─── Build Test ──────────────────────────────────────────────────────

Write-Host "`n--- Build Test ---" -ForegroundColor Yellow

Test-Assert "Solution builds (Release|x64)" {
    $slnPath = Join-Path $RepoRoot "TimeSeriesLab.sln"
    # Use VS MSBuild for WPF XAML compilation (dotnet build lacks WinFX targets for net48)
    $vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    if (-not (Test-Path $vswhere)) { $vswhere = "$env:ProgramFiles\Microsoft Visual Studio\Installer\vswhere.exe" }
    if (Test-Path $vswhere) {
        $vsPath = & $vswhere -latest -requires Microsoft.Component.MSBuild -property installationPath 2>$null
        $msbuild = Join-Path $vsPath "MSBuild\Current\Bin\MSBuild.exe"
        if (Test-Path $msbuild) {
            $output = & $msbuild $slnPath -p:Configuration=Release -p:Platform=x64 -t:Build -v:minimal 2>&1
            $LASTEXITCODE -eq 0
        } else {
            $output = & dotnet build $slnPath -c Release -p:Platform=x64 2>&1
            $LASTEXITCODE -eq 0
        }
    } else {
        $output = & dotnet build $slnPath -c Release -p:Platform=x64 2>&1
        $LASTEXITCODE -eq 0
    }
}

# ─── Summary ─────────────────────────────────────────────────────────

Write-Host "`n=== Results ===" -ForegroundColor Cyan
Write-Host "Total: $total | Pass: $pass | Fail: $fail" -ForegroundColor $(if ($fail -eq 0) { "Green" } else { "Red" })

if ($fail -gt 0) {
    exit 1
}
