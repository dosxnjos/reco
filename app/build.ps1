# Builds the new Reco app (Tauri 2 shell + frozen Python engine) into an NSIS installer.
#
#   powershell -ExecutionPolicy Bypass -File app/build.ps1              # full build
#   powershell -ExecutionPolicy Bypass -File app/build.ps1 -SemCongelar # reuse engine/dist (smoke still runs)
#
# Stages (Fase 3, step 16 of roadmap/2026-11-11-melhoria-reco-em-rust-fase-3.md):
#   1. freeze the engine with PyInstaller (engine/build.py, Fase 2) and run its hello smoke
#   2. npm ci in app/ (needs app/package-lock.json)
#   3. build the interface (npm run ui:build)
#   4. tauri build (release + NSIS); the release build.rs also refuses to run without the frozen engine
#
# The installer stays in <CARGO_TARGET_DIR or app/src-tauri/target>\release\bundle\nsis, outside the repo.
# It is found by its exact name ("<productName>_<version>_x64-setup.exe" from tauri.conf.json) and must be
# newer than the start of this run, so an old installer (or another app's, same folder) never passes.
# The last line printed is "Instalador: <path>" (the step's proof reads it); nothing is printed after it.
#
# This file is ASCII on purpose: Windows PowerShell 5.1 reads a BOM-less script as ANSI.
# It never starts the built app: the release shell takes the same mutex as the old Reco.exe.
param(
    [switch]$SemCongelar,
    [int]$MinutosMotor = 30
)

$ErrorActionPreference = 'Stop'
$app = $PSScriptRoot
$repo = Split-Path -Parent $app
$engineDir = Join-Path $repo 'engine\dist\reco-engine'
$engineExe = Join-Path $engineDir 'reco-engine.exe'
$inicio = Get-Date
$tempos = [ordered]@{}

function Fail([string]$msg) {
    Write-Host ""
    Write-Host "ERROR: $msg" -ForegroundColor Red
    exit 1
}

function Stage([string]$name) {
    Write-Host ""
    Write-Host "=== $name ===" -ForegroundColor Cyan
}

function Note-Time([string]$name, [datetime]$t0) {
    $tempos[$name] = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
}

function Get-FolderMB([string]$path) {
    $sum = (Get-ChildItem -LiteralPath $path -Recurse -File | Measure-Object Length -Sum).Sum
    return [math]::Round($sum / 1MB, 1)
}

# Runs python engine/build.py with a deadline (the smoke inside it has none) and returns its stdout lines.
function Invoke-EngineBuild([string[]]$pyArgs) {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) { Fail "python not found on PATH (the engine is frozen with it, Fase 2)." }
    $log = Join-Path $env:TEMP ("reco-app-build-engine-{0}.txt" -f $PID)
    $argList = @('"' + (Join-Path $repo 'engine\build.py') + '"') + $pyArgs
    $p = Start-Process -FilePath $python.Source -ArgumentList $argList -WorkingDirectory $repo `
        -NoNewWindow -PassThru -RedirectStandardOutput $log
    $null = $p.Handle  # keeps the exit code readable after the process ends (PS 5.1)
    if (-not $p.WaitForExit($MinutosMotor * 60 * 1000)) {
        & taskkill.exe /T /F /PID $p.Id | Out-Null
        Fail "engine build/smoke did not finish in $MinutosMotor min (killed python and its engine child)."
    }
    $p.WaitForExit()
    $lines = @()
    if (Test-Path -LiteralPath $log) {
        $lines = @(Get-Content -LiteralPath $log -Encoding UTF8)
        Remove-Item -LiteralPath $log -Force
    }
    $lines | ForEach-Object { Write-Host "  $_" }
    if ($p.ExitCode -ne 0) { Fail "engine/build.py exited with $($p.ExitCode) (see the lines above)." }
    return ,$lines
}

# The smoke in engine/build.py exits 1 on its own failure (Invoke-EngineBuild stops on it); judge the lines here
# too. `hello` answers before `import reco`: an engine frozen without a hidden import says hello ok and sends
# `ready` with an error, and then answers `unavailable` to every rec.start. So every run needs `ready ok=True`
# and the last one `devices ok=True` (review finding, Fase 3).
function Assert-Smoke([string[]]$lines) {
    $runs = @($lines | Where-Object { $_ -match '^run \d+: hello ok=' })
    if ($runs.Count -lt 3) { Fail "engine smoke printed $($runs.Count) of 3 runs: the frozen engine did not answer hello." }
    foreach ($r in $runs) {
        if ($r -notmatch 'hello ok=True' -or $r -notmatch 'ready ok=True' -or $r -notmatch 'shutdown ok=True exit=0') {
            Fail "engine smoke failed: $r"
        }
    }
    if ($runs[-1] -notmatch 'devices ok=True') { Fail "engine smoke failed (devices.list on the last run): $($runs[-1])" }
    return $runs
}

function Invoke-Npm([string[]]$npmArgs, [string]$what) {
    # npm, cargo and tauri write progress to stderr; under 'Stop' a redirected PS 5.1 host turns that into a
    # terminating NativeCommandError. Judge by the exit code instead (this scope only).
    $ErrorActionPreference = 'Continue'
    Push-Location $app
    try {
        & npm @npmArgs
        $code = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    if ($code -ne 0) { Fail "$what failed (npm $($npmArgs -join ' ') exited with $code)." }
}

Write-Host ""
Write-Host "=== Reco - build (casco Tauri + motor congelado) ===" -ForegroundColor Cyan

# 1. engine
Stage "1/4 engine: freeze + hello smoke"
$t0 = Get-Date
if ($SemCongelar) {
    if (-not (Test-Path -LiteralPath $engineExe)) {
        Fail "frozen engine not found at $engineExe; run without -SemCongelar (or: python engine/build.py)."
    }
    $out = Invoke-EngineBuild @('--smoke')
} else {
    $out = Invoke-EngineBuild @()
}
if (-not (Test-Path -LiteralPath $engineExe)) { Fail "frozen engine not found at $engineExe after the freeze." }
$smoke = Assert-Smoke $out
Note-Time 'motor' $t0

# 2. npm ci
Stage "2/4 npm ci"
if (-not (Test-Path -LiteralPath (Join-Path $app 'package-lock.json'))) { Fail "app/package-lock.json missing (npm ci needs it)." }
$t0 = Get-Date
Invoke-Npm @('ci', '--no-audit', '--no-fund') 'npm ci'
Note-Time 'npm ci' $t0

# 3. interface
Stage "3/4 interface (ui:build)"
$t0 = Get-Date
Invoke-Npm @('run', 'ui:build') 'interface build'
if (-not (Test-Path -LiteralPath (Join-Path $app 'ui\dist\index.html'))) { Fail "app/ui/dist/index.html missing after ui:build." }
Note-Time 'interface' $t0

# 4. tauri build
Stage "4/4 tauri build (release + NSIS)"
$conf = Get-Content -LiteralPath (Join-Path $app 'src-tauri\tauri.conf.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$target = $env:CARGO_TARGET_DIR
if (-not $target) { $target = Join-Path $app 'src-tauri\target' }
$nsisDir = Join-Path $target 'release\bundle\nsis'
$installer = Join-Path $nsisDir ("{0}_{1}_x64-setup.exe" -f $conf.productName, $conf.version)
$t0 = Get-Date
Invoke-Npm @('run', 'tauri', '--', 'build', '--bundles', 'nsis') 'tauri build'
Note-Time 'tauri build' $t0

if (-not (Test-Path -LiteralPath $installer)) { Fail "installer not found: $installer" }
$item = Get-Item -LiteralPath $installer
if ($item.LastWriteTime -lt $inicio) { Fail "installer $installer is older than this run (stale build?)." }
$shellExe = Join-Path $target 'release\reco.exe'
if (-not (Test-Path -LiteralPath $shellExe)) { Fail "shell exe not found: $shellExe" }

# summary (the proof line must stay last)
$instMB = [math]::Round($item.Length / 1MB, 1)
$shellMB = [math]::Round((Get-Item -LiteralPath $shellExe).Length / 1MB, 1)
$engineMB = Get-FolderMB $engineDir
$total = [math]::Round(((Get-Date) - $inicio).TotalSeconds, 1)
Write-Host ""
Write-Host "=== done ===" -ForegroundColor Green
$smoke | ForEach-Object { Write-Host "smoke: $_" }
foreach ($k in $tempos.Keys) { Write-Host ("tempo {0}: {1} s" -f $k, $tempos[$k]) }
Write-Host "tempo total: $total s"
Write-Host "casco: $shellExe ($shellMB MB)"
Write-Host "motor: $engineDir ($engineMB MB)"
Write-Host ("pasta instalada (casco + motor, sem desinstalador): {0} MB" -f ($shellMB + $engineMB))
Write-Host "instalador: $instMB MB ($($item.Length) bytes)"
Write-Host "Instalador: $installer"
