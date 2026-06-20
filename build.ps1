param(
    [switch]$Clean,
    [string]$Icon = ""
)

Write-Host ""
Write-Host "=== Reco - Build executable ===" -ForegroundColor Cyan
Write-Host ""

$python = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $python) {
    Write-Host "ERROR: Python not found on PATH. Install from https://python.org" -ForegroundColor Red
    exit 1
}
$pythonExe = $python.Source
Write-Host "Python: $pythonExe" -ForegroundColor Green

Write-Host ""
Write-Host "Installing PyInstaller..." -ForegroundColor Yellow
& $pythonExe -m pip install "pyinstaller>=6.0" --quiet --upgrade
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: failed to install PyInstaller." -ForegroundColor Red; exit 1 }

Write-Host "Installing dependencies..." -ForegroundColor Yellow
& $pythonExe -m pip install soundcard lameenc numpy scipy --quiet
if ($LASTEXITCODE -ne 0) { Write-Host "WARNING: a dependency failed to install." -ForegroundColor Yellow }

if ($Clean) {
    foreach ($d in @("dist", "build")) {
        if (Test-Path $d) { Remove-Item $d -Recurse -Force; Write-Host "Cleaned: $d" }
    }
}

$spec = "$PSScriptRoot\reco.spec"
$specToUse = $spec
if ($Icon -and (Test-Path $Icon)) {
    $iconAbs = (Resolve-Path $Icon).Path
    $content = Get-Content $spec -Raw -Encoding utf8
    $content = $content -replace "# icon='reco.ico'", "icon='$iconAbs'"
    $specToUse = "$PSScriptRoot\reco_build.spec"
    Set-Content $specToUse $content -Encoding utf8
}

Write-Host ""
Write-Host "Building... (1-3 min the first time)" -ForegroundColor Yellow
& $pythonExe -m PyInstaller $specToUse --noconfirm
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: build failed." -ForegroundColor Red
    exit 1
}

$exe = "$PSScriptRoot\dist\Reco.exe"
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host " Build complete!" -ForegroundColor Green
Write-Host " $exe"
if (Test-Path $exe) {
    $mb = [math]::Round((Get-Item $exe).Length / 1MB, 1)
    Write-Host " Size: $mb MB"
}
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "NOTE: faster-whisper is NOT bundled. The .exe records on its own;"
Write-Host "      for transcription it uses the system Python (auto-installs on demand)."
