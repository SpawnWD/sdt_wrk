$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$buildPath = Join-Path $projectRoot "build_1.88.2"
$releasePath = Join-Path $projectRoot "release_1.88.2"
$panelPath = Join-Path $projectRoot "panel.py"
$templatesPath = Join-Path $projectRoot "templates"
$toolsPath = Join-Path $projectRoot "herramientas"
$assetsPath = Join-Path $projectRoot "assets"
$iconPath = Join-Path $assetsPath "app_icon.ico"

foreach ($target in @($buildPath, $releasePath)) {
    $fullTarget = [IO.Path]::GetFullPath($target)
    if (-not $fullTarget.StartsWith($projectRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Ruta de construcción fuera del proyecto: $fullTarget"
    }
    if (Test-Path -LiteralPath $fullTarget) {
        Remove-Item -LiteralPath $fullTarget -Recurse -Force
    }
}

if (-not (Test-Path -LiteralPath $panelPath -PathType Leaf)) { throw "No se encontró panel.py" }
if (-not (Test-Path -LiteralPath $templatesPath -PathType Container)) { throw "No se encontró templates" }
if (-not (Test-Path -LiteralPath $toolsPath -PathType Container)) { throw "No se encontró herramientas" }
if (-not (Test-Path -LiteralPath $iconPath -PathType Leaf)) { throw "No se encontró assets/app_icon.ico" }

New-Item -ItemType Directory -Path $buildPath, $releasePath -Force | Out-Null

python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller no está instalado. Ejecuta: python -m pip install pyinstaller"
}

python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name "AdministracionDeMoviles" `
    --icon $iconPath `
    --distpath $releasePath `
    --workpath $buildPath `
    --specpath $buildPath `
    --add-data "$templatesPath;templates" `
    --add-data "$toolsPath;herramientas" `
    --add-data "$assetsPath;assets" `
    --hidden-import "license_guard" `
    $panelPath

if ($LASTEXITCODE -ne 0) { throw "PyInstaller terminó con código $LASTEXITCODE" }

$executable = Join-Path $releasePath "AdministracionDeMoviles.exe"
if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
    throw "No se generó el ejecutable esperado."
}

$hash = (Get-FileHash -LiteralPath $executable -Algorithm SHA256).Hash
Set-Content -LiteralPath (Join-Path $releasePath "SHA256.txt") -Encoding UTF8 -Value "AdministracionDeMoviles.exe  SHA256  $hash"

Write-Host "Ejecutable generado: $executable"
Write-Host "SHA256: $hash"
