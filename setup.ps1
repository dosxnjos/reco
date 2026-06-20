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

# Core deps (recording + audio decoding)
foreach ($p in @("soundcard", "lameenc", "numpy", "scipy", "av", "huggingface_hub")) {
    Write-Host "Installing $p..." -ForegroundColor Yellow
    pip install $p --quiet
}

# Transcription backend (downloads the Whisper model on first use)
Write-Host ""
if ($IsMacOS) {
    Write-Host "macOS detected — installing mlx-whisper (Apple GPU)..." -ForegroundColor Yellow
    pip install mlx-whisper --quiet
} else {
    Write-Host "Installing OpenVINO GenAI (NPU / iGPU / CPU)..." -ForegroundColor Yellow
    pip install openvino openvino-genai openvino-tokenizers --quiet
}
if ($LASTEXITCODE -eq 0) { Write-Host "  transcription backend: OK" -ForegroundColor Green }
else { Write-Host "  backend not installed (transcription disabled until installed)." -ForegroundColor Yellow }

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host "Run with:  python `"$ScriptPath`""
Write-Host "Tip: the Ctrl+Shift+R keyboard shortcut is opt-in — enable it inside"
Write-Host "     Reco under Options (it is NOT created automatically)."
