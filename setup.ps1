param([string]$ScriptPath = "$PSScriptRoot\reco.py")

Write-Host ""
Write-Host "=== Reco - Setup ===" -ForegroundColor Cyan
Write-Host ""

# Find a windowed Python launcher for the shortcut
$pythonExe = $null
foreach ($c in @("pyw.exe", "pythonw.exe", "python.exe")) {
    $f = Get-Command $c -ErrorAction SilentlyContinue
    if ($f) { $pythonExe = $f.Source; break }
}
if (-not $pythonExe) { Write-Host "Python not found." -ForegroundColor Red; exit 1 }
Write-Host "Python: $pythonExe" -ForegroundColor Green

if (-not (Get-Command pip -ErrorAction SilentlyContinue)) {
    Write-Host "pip not found." -ForegroundColor Red; exit 1
}

# Core deps
foreach ($p in @("soundcard", "lameenc", "numpy", "scipy")) {
    Write-Host "Installing $p..." -ForegroundColor Yellow
    pip install $p --quiet
}

# Optional: transcription
Write-Host ""
Write-Host "Installing faster-whisper (optional; downloads a model on first use)..." -ForegroundColor Yellow
pip install faster-whisper --quiet
if ($LASTEXITCODE -eq 0) { Write-Host "  faster-whisper: OK" -ForegroundColor Green }
else { Write-Host "  faster-whisper not installed (transcription disabled until installed)." -ForegroundColor Yellow }

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host "Run with:  python `"$ScriptPath`""
Write-Host "Tip: the Ctrl+Shift+R keyboard shortcut is opt-in — enable it inside"
Write-Host "     Reco under Options (it is NOT created automatically)."
