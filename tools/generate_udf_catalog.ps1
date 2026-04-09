# generate_udf_catalog.ps1 - Extract UDF metadata from C# source files to udf_catalog.json
# Parses ExcelFunction attributes from AutoFunctions.cs and ThoroughFunctions.cs

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path "$RepoRoot\TimeSeriesLab.sln")) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}

Write-Host "=== Generating UDF Catalog ===" -ForegroundColor Cyan

$outputPath = Join-Path $RepoRoot "resources\catalog\udf_catalog.json"

$sourceFiles = @(
    (Join-Path $RepoRoot "src\TSL.AddIn\Functions\AutoFunctions.cs"),
    (Join-Path $RepoRoot "src\TSL.AddIn\Functions\ThoroughFunctions.cs")
)

$udfs = @()

foreach ($file in $sourceFiles) {
    if (-not (Test-Path $file)) {
        Write-Warning "Source file not found: $file"
        continue
    }

    $content = Get-Content $file -Raw

    # Match ExcelFunction attributes and the following method signature
    # Anchor to )\s*{ so we capture the full parameter list (which contains nested parens in [ExcelArgument(...)])
    $pattern = '\[ExcelFunction\(([\s\S]*?)\)\]\s*public\s+static\s+object\s+(\w+)\s*\(([\s\S]*?)\)\s*\{'
    $matches = [regex]::Matches($content, $pattern)

    foreach ($match in $matches) {
        $attrBody = $match.Groups[1].Value
        $methodName = $match.Groups[2].Value
        $paramsBody = $match.Groups[3].Value

        # Extract Name
        $nameMatch = [regex]::Match($attrBody, 'Name\s*=\s*"([^"]+)"')
        $name = if ($nameMatch.Success) { $nameMatch.Groups[1].Value } else { $methodName }

        # Extract Category
        $catMatch = [regex]::Match($attrBody, 'Category\s*=\s*"([^"]+)"')
        $category = if ($catMatch.Success) { $catMatch.Groups[1].Value } else { "" }

        # Extract Description
        $descMatch = [regex]::Match($attrBody, 'Description\s*=\s*"([^"]+)"')
        $description = if ($descMatch.Success) { $descMatch.Groups[1].Value } else { "" }

        # Determine lane
        $lane = if ($category -match "THOROUGH") { "THOROUGH" } else { "AUTO" }

        # Parse parameters from ExcelArgument attributes
        $args = @()
        $argPattern = '\[ExcelArgument\(([\s\S]*?)\)\]\s*([\w\?\[\],<>]+)\s+(\w+)'
        $argMatches = [regex]::Matches($paramsBody, $argPattern)

        foreach ($argMatch in $argMatches) {
            $argAttrBody = $argMatch.Groups[1].Value
            $argType = $argMatch.Groups[2].Value
            $argName = $argMatch.Groups[3].Value

            $argNameAttr = [regex]::Match($argAttrBody, 'Name\s*=\s*"([^"]+)"')
            $argDescAttr = [regex]::Match($argAttrBody, 'Description\s*=\s*"([^"]+)"')

            $args += @{
                name = if ($argNameAttr.Success) { $argNameAttr.Groups[1].Value } else { $argName }
                type = $argType
                description = if ($argDescAttr.Success) { $argDescAttr.Groups[1].Value } else { "" }
            }
        }

        $udfs += @{
            name = $name
            category = $category
            lane = $lane
            description = $description
            arguments = $args
        }
    }
}

$catalog = @{
    version = "1.0.0"
    generated = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    udfs = $udfs
}

$json = $catalog | ConvertTo-Json -Depth 10
$outputDir = Split-Path -Parent $outputPath
if (-not (Test-Path $outputDir)) { New-Item -ItemType Directory -Path $outputDir -Force | Out-Null }
$json | Out-File -FilePath $outputPath -Encoding utf8

Write-Host "Generated UDF catalog: $outputPath ($($udfs.Count) UDFs)" -ForegroundColor Green
