"""
Reco — record microphone + system audio (WASAPI loopback) and transcribe.

Audio capture uses the `soundcard` library (WASAPI):
  • Lists each physical device once (no per-host-API duplicates).
  • Separates microphones from speakers correctly.
  • Records system audio via real WASAPI loopback — does NOT depend on
    "Stereo Mix" being enabled.

Recordings are encoded to MP3 (lameenc) — ~6-12x smaller than WAV, plenty for
speech/meetings and transcription. Transcription runs locally with
faster-whisper. UI is bilingual (PT/EN), auto-detected from the system.
"""

import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import threading
import queue
import time
import datetime
import json
import os
import math
import ctypes
import subprocess
from pathlib import Path

IS_FROZEN = getattr(sys, "frozen", False)   # running as a PyInstaller .exe?
APP_NAME    = "Reco"
APP_TITLE   = "Reco"
APP_VERSION = "0.1.1"
GITHUB_REPO = "dosxnjos/reco"

# ── Theme ─────────────────────────────────────────────────────────────────────
# GREEN/AMBER/RED are fixed (VU meter); everything else derives from the chosen
# background + accent via apply_theme(), which auto-picks readable text colors.
GREEN  = "#30A46C"
AMBER  = "#F5A623"
RED_C  = "#E5484D"

DEFAULT_BG     = "#181A1B"
DEFAULT_ACCENT = "#E0825F"

BG = CARD = CARD_H = CARD_A = ACCENT = ACCENT_FG = TEXT = MUTED = SUBTLE = BORDER = ""


def _hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def _rgb_to_hex(rgb):
    return "#%02X%02X%02X" % tuple(max(0, min(255, int(round(c)))) for c in rgb)

def _lum(h):
    r, g, b = _hex_to_rgb(h)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255

def _mix(h, target, amt):
    a, b = _hex_to_rgb(h), _hex_to_rgb(target)
    return _rgb_to_hex(tuple(a[i] + (b[i] - a[i]) * amt for i in range(3)))

def _best_fg(bg_hex):
    """Readable text on bg_hex: dark-gray on light colors, white on dark ones."""
    return "#1A1A1C" if _lum(bg_hex) > 0.62 else "#FFFFFF"


def apply_theme(bg_color, accent_color):
    global BG, CARD, CARD_H, CARD_A, ACCENT, ACCENT_FG, TEXT, MUTED, SUBTLE, BORDER
    BG = bg_color
    ACCENT = accent_color
    ACCENT_FG = _best_fg(accent_color)
    if _lum(bg_color) < 0.5:                       # dark background
        TEXT, MUTED, SUBTLE = "#F5F5F7", "#B8BAC6", "#969CA4"
        CARD   = _mix(bg_color, "#FFFFFF", 0.06)
        CARD_H = _mix(bg_color, "#FFFFFF", 0.13)
        BORDER = _mix(bg_color, "#FFFFFF", 0.20)
    else:                                          # light background
        TEXT, MUTED, SUBTLE = "#1A1A1C", "#3C3C44", "#5C5C66"
        CARD   = _mix(bg_color, "#000000", 0.05)
        CARD_H = _mix(bg_color, "#000000", 0.11)
        BORDER = _mix(bg_color, "#000000", 0.18)
    CARD_A = _mix(bg_color, accent_color, 0.22)    # accent-tinted selection


apply_theme(DEFAULT_BG, DEFAULT_ACCENT)

SEG    = ("Segoe UI", 10)
SEG_SM = ("Segoe UI", 9)
SEG_XS = ("Segoe UI", 8)
SEG_SB = ("Segoe UI Semibold", 10)
SEG_LG = ("Segoe UI Semibold", 13)

def default_output_dir() -> Path:
    return Path.home() / "Documents" / "Reco"

# Default save location (overridable in Options). Resolved from config at runtime.
OUTPUT_DIR = default_output_dir()

# ── Config persistence ─────────────────────────────────────────────────────────
CONFIG_PATH = Path.home() / ".reco_config.json"

_CFG_DEFAULTS: dict = {
    "language":    None,      # "pt" | "en" | None -> auto-detect from system
    "bg_color":    DEFAULT_BG,
    "accent_color": DEFAULT_ACCENT,
    "model":       "small",
    "device":      "AUTO",    # OpenVINO device pref: AUTO | NPU | GPU | CPU
    "diarize":     True,      # channel-based diarization (mic = "Eu", system = others)
    "aec":         True,      # cancel PC-audio echo bleeding into the mic
    "output_dir":  None,      # save folder; None -> Documents\Reco
    "mic_device":  None,      # soundcard device id (str)
    "sys_device":  None,      # soundcard speaker id (str)
}

# Filename marker identifying a Reco dual-channel (mic + system) recording, so the
# transcribe screen only channel-diarizes / echo-cancels these — never arbitrary
# files. Travels with the file (survives moving); only lost on a manual rename.
RECO_TAG = "reco"

def is_reco_recording(path) -> bool:
    toks = Path(path).stem.lower().replace("-", "_").split("_")
    return RECO_TAG in toks

# Recording format is fixed (not user-configurable): 16 kHz stereo (L=mic,
# R=system) is exactly what transcription + channel diarization + echo
# cancellation need; 128 kbps VBR ≈ 64 kbps/channel keeps files small.
OUT_SR = 16000
OUT_CH = 2
MP3_BR = 128

def load_config() -> dict:
    cfg = dict(_CFG_DEFAULTS)
    try:
        if CONFIG_PATH.exists():
            cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    except json.JSONDecodeError:
        try:
            CONFIG_PATH.replace(CONFIG_PATH.with_suffix(".corrupt"))
        except Exception:
            pass
    except Exception:
        pass
    return cfg

def save_config(cfg: dict):
    # Atomic write: temp file + replace, so a crash mid-write can't truncate it.
    try:
        tmp = CONFIG_PATH.with_suffix(CONFIG_PATH.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(json.dumps(cfg, indent=2, ensure_ascii=False))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, CONFIG_PATH)
    except Exception:
        pass


def _icon_file() -> Path | None:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    p = base / "logo" / "logo_symbol_1x1.ico"
    return p if p.exists() else None


def set_dark_titlebar(win):
    try:
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        val = ctypes.c_int(2)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 20, ctypes.byref(val), ctypes.sizeof(val))
    except Exception:
        pass


# ── i18n (PT default; EN translations keyed by the PT string) ──────────────────
def _system_lang() -> str:
    """Best-effort: 'pt' if the system UI/locale is Portuguese, else 'en'."""
    try:
        lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        if (lcid & 0x3ff) == 0x16:          # LANG_PORTUGUESE
            return "pt"
        return "en"
    except Exception:
        pass
    try:
        import locale
        loc = (locale.getlocale()[0] or "")
        if loc.lower().startswith(("pt", "portug")):
            return "pt"
    except Exception:
        pass
    return "en"


LANG = "pt"

_TR_EN = {
    # header / meters
    "mic + sistema  ·  MP3 + transcrição": "mic + system  ·  MP3 + transcription",
    "MIC": "MIC",
    "SISTEMA": "SYSTEM",
    # buttons
    "⬤  Gravar": "⬤  Record",
    "⬛  Parar": "⬛  Stop",
    "✓  Salvar": "✓  Save",
    "⚡  Transcrever": "⚡  Transcribe",
    "✕  Excluir": "✕  Delete",
    "⚡  Transcrever + excluir": "⚡  Transcribe + delete",
    "▶  Reproduzir": "▶  Play",
    "⚡  Salvar + Transcrever": "⚡  Save + Transcribe",
    "🔤  Transcrever": "🔤  Transcribe",
    "Salvar + Transcrever": "Save + Transcribe",
    "Tema:": "Theme:",
    "Fundo": "Background",
    "Destaque": "Accent",
    "Padrão": "Default",
    "Cor de fundo": "Background color",
    "Cor de destaque": "Accent color",
    # links
    "⚙ Opções": "⚙ Options",
    "⚙ Ocultar opções": "⚙ Hide options",
    "Transcrever…": "Transcribe…",
    "← Gravar": "← Record",
    "Ocultar transcrição": "Hide transcription",
    # advanced labels
    "Entrada:": "Input:",
    "Saída:": "Output:",
    "Pasta:": "Folder:",
    "Alterar…": "Change…",
    "Pasta de gravações": "Recordings folder",
    "↺ Atualizar dispositivos": "↺ Refresh devices",
    "Canais:": "Channels:",
    "Taxa:": "Rate:",
    "MP3:": "MP3:",
    "Modelo:": "Model:",
    "Processar em:": "Run on:",
    "☐ Diarização (uma fala por canal)": "☐ Diarization (one speaker per channel)",
    "☑ Diarização (uma fala por canal)": "☑ Diarization (one speaker per channel)",
    "☐ Cancelar eco do PC no microfone": "☐ Cancel PC echo in the microphone",
    "☑ Cancelar eco do PC no microfone": "☑ Cancel PC echo in the microphone",
    "Idioma:": "Language:",
    "⌨ Criar atalho (Ctrl+Shift+R)": "⌨ Create shortcut (Ctrl+Shift+R)",
    "⌨ Remover atalho": "⌨ Remove shortcut",
    "Atalho criado — abra pelo Menu Iniciar ou com Ctrl+Shift+R.":
        "Shortcut created — open from the Start Menu or with Ctrl+Shift+R.",
    "Atalho removido.": "Shortcut removed.",
    "Não foi possível criar o atalho: {e}":
        "Couldn't create the shortcut: {e}",
    "tiny · small (padrão) · medium · large-v3-turbo":
        "tiny · small (default) · medium · large-v3-turbo",
    "Mono": "Mono",
    "Estéreo": "Stereo",
    "16.000 Hz": "16,000 Hz",
    "22.050 Hz": "22,050 Hz",
    "44.100 Hz": "44,100 Hz",
    "48.000 Hz": "48,000 Hz",
    # status — devices
    "Pronto para gravar.": "Ready to record.",
    "Buscando dispositivos…": "Searching for devices…",
    "Erro ao listar dispositivos: {m}": "Error listing devices: {m}",
    "Nenhum dispositivo de áudio encontrado.": "No audio devices found.",
    "Atenção: nenhuma saída de áudio para loopback.":
        "Warning: no audio output available for loopback.",
    "Não é possível atualizar dispositivos durante a gravação.":
        "Can't refresh devices while recording.",
    "Captura indisponível — instale soundcard, numpy e lameenc.":
        "Capture unavailable — install soundcard, numpy and lameenc.",
    "Nenhuma fonte de áudio — abra Opções.":
        "No audio source — open Options.",
    # status — recording
    "Gravando…  (mic + sistema)": "Recording…  (mic + system)",
    "microfone": "microphone",
    "áudio do sistema": "system audio",
    "Nenhuma fonte pôde ser capturada ({which}): {m}":
        "No source could be captured ({which}): {m}",
    "Falha ao capturar {which} (a outra fonte continua).":
        "Failed to capture {which} (the other source continues).",
    "Salvando…": "Saving…",
    "Codificando MP3 e salvando…": "Encoding MP3 and saving…",
    "Erro ao salvar: {m}": "Error saving: {m}",
    "Nenhum áudio capturado — verifique as fontes selecionadas.":
        "No audio captured — check the selected sources.",
    "Salvo: {n}  —  Escolha o que fazer:": "Saved: {n}  —  Choose what to do:",
    "Gravação salva: {n}": "Recording saved: {n}",
    "Gravação descartada.": "Recording discarded.",
    "Não foi possível excluir: {e}": "Couldn't delete: {e}",
    # status — transcription
    "Nada para transcrever.": "Nothing to transcribe.",
    "Nada para reproduzir.": "Nothing to play.",
    "Arquivo não encontrado.": "File not found.",
    "Já há uma transcrição em andamento.": "A transcription is already running.",
    "Transcrição indisponível — instale openvino-genai.":
        "Transcription unavailable — install openvino-genai.",
    "Transcrevendo {n}…": "Transcribing {n}…",
    "Transcrevendo…": "Transcribing…",
    "Transcrevendo… {p}%": "Transcribing… {p}%",
    "Baixando modelo '{size}' (primeira vez)…":
        "Downloading model '{size}' (first time)…",
    "Preparando modelo no {dev}…": "Preparing model on {dev}…",
    "Carregando áudio…": "Loading audio…",
    "Atualizando modelo…": "Updating model…",
    "Modelo atualizado.": "Model updated.",
    "⬆ Nova versão {tag}": "⬆ New version {tag}",
    "a transcrição falhou (código {c})": "transcription failed (code {c})",
    "Erro na transcrição: {e}": "Transcription error: {e}",
    "Transcrito, mas falha ao salvar o .txt.":
        "Transcribed, but failed to save the .txt.",
    "Transcrição salva: {n}. Áudio excluído.":
        "Transcription saved: {n}. Audio deleted.",
    "Transcrição salva: {n}": "Transcription saved: {n}",
    "Python não encontrado — instale o Python {v} (python.org).":
        "Python not found — install Python {v} (python.org).",
    # transcribe section
    "TRANSCRIÇÃO": "TRANSCRIPTION",
    "＋ Escolher arquivo…": "＋ Choose a file…",
    "⬛  Parar": "⬛  Stop",
    "Transcrição cancelada.": "Transcription cancelled.",
    "Salvo: {n}": "Saved: {n}",
    "Transcrever arquivo": "Transcribe file",
    "ESCOLHA O ÁUDIO (MP3, WAV…)": "CHOOSE AUDIO (MP3, WAV…)",
    "Arquivo": "File", "Data": "Date", "Duração": "Length", "Tamanho": "Size",
    "＋ Escolher outro arquivo…": "＋ Choose another file…",
    "↺ Atualizar": "↺ Refresh",
    "⚡ Transcrever e salvar .txt": "⚡ Transcribe and save .txt",
    "Abrir pasta": "Open folder",
    "Selecione um arquivo e clique em Transcrever.":
        "Select a file and click Transcribe.",
    "Nenhum áudio encontrado": "No audio found",
    "Selecione um arquivo válido.": "Select a valid file.",
    "Salvo: {n}  (na pasta {d})": "Saved: {n}  (in the {d} folder)",
    "Erro: {e}": "Error: {e}",
    "Selecionar áudio": "Select audio",
    "Áudio": "Audio", "Todos": "All files",
    # installer
    "Instalar transcrição": "Install transcription",
    "Componentes de transcrição": "Transcription components",
    "O faster-whisper e suas dependências serão baixados e instalados\n"
    "numa pasta do seu usuário (~0,5 GB, alguns minutos).":
        "faster-whisper and its dependencies will be downloaded and installed\n"
        "into your user folder (~0.5 GB, a few minutes).",
    "Pronto para instalar.": "Ready to install.",
    "Instalar agora": "Install now",
    "Iniciando instalação…": "Starting installation…",
    "Baixando {pkg}…": "Downloading {pkg}…",
    "Baixando {pkg}… {mb} MB": "Downloading {pkg}… {mb} MB",
    "Instalando pacotes…": "Installing packages…",
    "Concluído!": "Done!",
    "Pronto! Componentes instalados. Pode transcrever agora.":
        "Done! Components installed. You can transcribe now.",
    "Falha na instalação (código {c}). Verifique a conexão e tente de novo.":
        "Installation failed (code {c}). Check your connection and try again.",
    "Python não encontrado no sistema. Instale o Python {v} (python.org) "
    "e tente de novo — ou rode pelo código-fonte.":
        "Python not found on the system. Install Python {v} (python.org) "
        "and try again — or run from source.",
    # dependency messagebox
    "Dependências ausentes": "Missing dependencies",
    "Para gravar áudio, instale as dependências:\n\n  pip install {pkgs}\n\n"
    "Abra um terminal e rode o comando acima. Depois, reinicie o {app}.":
        "To record audio, install the dependencies:\n\n  pip install {pkgs}\n\n"
        "Open a terminal and run the command above. Then restart {app}.",
}


def t(s: str) -> str:
    """Translate a PT string to the current language (PT = identity)."""
    if LANG == "pt":
        return s
    return _TR_EN.get(s, s)


def tf(s: str, **kw) -> str:
    return t(s).format(**kw)


def _init_lang():
    global LANG
    try:
        LANG = load_config().get("language") or _system_lang()
    except Exception:
        LANG = _system_lang()

_init_lang()


# ── Optional deps ─────────────────────────────────────────────────────────────
try:
    import numpy as np
    HAS_NP = True
except ImportError:
    np = None; HAS_NP = False

try:
    import soundcard as sc
    import warnings
    warnings.filterwarnings("ignore", category=sc.SoundcardRuntimeWarning)
    HAS_SC = True
except Exception:
    sc = None; HAS_SC = False

try:
    import lameenc
    HAS_LAME = True
except ImportError:
    lameenc = None; HAS_LAME = False


# ── Transcription backend: OpenVINO GenAI (in-process, NPU / iGPU / CPU) ───────
# One backend for everything. OpenVINO runs the whole Whisper model natively on
# the Intel NPU ("AI Boost"), the iGPU (Arc), or any x86-64 CPU — so the .exe is
# fully plug-n-play (no Python, no ffmpeg) once the runtime is bundled. The model
# (pre-converted INT8 IR) is downloaded from Hugging Face on first use.
import importlib.util as _ilu


def _no_window_kwargs() -> dict:
    return {"creationflags": 0x08000000} if os.name == "nt" else {}


def _ps_quote(s: str) -> str:
    """Quote a string as a PowerShell single-quoted literal."""
    return "'" + s.replace("'", "''") + "'"


# Cheap availability probes (don't import the heavy runtime at startup).
import platform as _platform
HAS_OV = _ilu.find_spec("openvino_genai") is not None
HAS_AV = _ilu.find_spec("av") is not None
# macOS on Apple Silicon → MLX backend (uses the Apple GPU; OpenVINO would be
# CPU-only there). Everything else (Windows/Linux x86) → OpenVINO.
HAS_MLX = (sys.platform == "darwin"
           and _platform.machine() in ("arm64", "aarch64")
           and _ilu.find_spec("mlx_whisper") is not None)


def _user_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / APP_NAME


def _bundled_models_dir() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / "models"


# ── Audio decoding (PyAV → 16 kHz float32; no external ffmpeg binary) ───────────
def decode_16k(path: Path, split: bool = False) -> list:
    """Decode any audio file to 16 kHz float32 channels.

    Returns [mono] normally, or [left, right] when split=True and the source is
    stereo (channel-based diarization: L = mic = "Eu", R = system = others)."""
    import av
    with av.open(str(path)) as cont:
        st = cont.streams.audio[0]
        nch = getattr(st, "channels", 1) or 1
        stereo = bool(split and nch >= 2)
        rs = av.audio.resampler.AudioResampler(
            format="fltp", layout="stereo" if stereo else "mono", rate=16000)
        buf = []
        for frame in cont.decode(audio=0):
            for r in rs.resample(frame):
                buf.append(r.to_ndarray())          # planar: (layout_ch, n)
        for r in rs.resample(None):                 # flush
            buf.append(r.to_ndarray())
    if not buf:
        return [np.zeros(0, np.float32)] * (2 if stereo else 1)
    arr = np.concatenate(buf, axis=1).astype(np.float32)
    if stereo and arr.shape[0] >= 2:
        return [np.ascontiguousarray(arr[0]), np.ascontiguousarray(arr[1])]
    return [np.ascontiguousarray(arr[0])]


# ── Acoustic echo cancellation (offline NLMS-style, frequency domain) ───────────
def cancel_echo(mic: "np.ndarray", ref: "np.ndarray",
                sr: int = 16000, nfft: int = 1024, hop: int = 256) -> "np.ndarray":
    """Remove the echo of `ref` (system loopback) bleeding into `mic`.

    For users on speakers, the PC audio leaks acoustically into the microphone,
    duplicating the other party's voice across both channels and confusing the
    channel diarization. We have a perfect far-end reference (the loopback), so we
    estimate the (time-invariant) echo path per frequency bin by least squares and
    subtract it. Offline, pure numpy/scipy. Validated ~37 dB ERLE on synthetic
    echo. If `ref` carries no energy this is a near no-op."""
    if mic.size == 0 or ref.size == 0:
        return mic
    try:
        from scipy.signal import stft, istft, correlate
    except Exception:
        return mic
    n = max(len(mic), len(ref))
    mic = np.pad(mic, (0, n - len(mic)))
    ref = np.pad(ref, (0, n - len(ref)))
    # bulk delay of ref inside mic (search ±200 ms)
    maxlag = int(0.2 * sr)
    c = correlate(mic, ref, mode="full", method="fft")
    lags = np.arange(-len(ref) + 1, len(mic))
    win = np.abs(lags) <= maxlag
    d = int(lags[win][np.argmax(np.abs(c[win]))])
    ref_al = np.roll(ref, d)
    if d > 0:
        ref_al[:d] = 0
    elif d < 0:
        ref_al[d:] = 0
    _, _, M = stft(mic, fs=sr, nperseg=nfft, noverlap=nfft - hop)
    _, _, S = stft(ref_al, fs=sr, nperseg=nfft, noverlap=nfft - hop)
    H = (np.sum(M * np.conj(S), axis=1) / (np.sum(np.abs(S) ** 2, axis=1) + 1e-8))[:, None]
    _, mic_c = istft(M - H * S, fs=sr, nperseg=nfft, noverlap=nfft - hop)
    return mic_c[:len(mic)].astype(np.float32)


# ── OpenVINO device + model management ──────────────────────────────────────────
def ov_available_devices() -> list:
    try:
        import openvino as ov
        return list(ov.Core().available_devices)
    except Exception:
        return ["CPU"]


def resolve_device(pref: str) -> str:
    """Map a preferred device to one that exists (pref → NPU → GPU → CPU)."""
    avail = ov_available_devices()
    def has(d):                       # available_devices may report 'GPU.0' etc.
        return any(a == d or a.startswith(d + ".") for a in avail)
    if pref and has(pref):
        return pref
    for d in ("NPU", "GPU", "CPU"):
        if has(d):
            return d
    return "CPU"


MODEL_SENTINEL = "openvino_encoder_model.xml"


def ov_model_repo(size: str) -> str:
    return f"OpenVINO/whisper-{size}-int8-ov"


def _repo_for_dir(d: Path) -> str:
    """The HF repo a local model folder came from (folder name is the repo name)."""
    return f"OpenVINO/{d.name}"


def _find_model_dir(size: str | None = None) -> Path | None:
    """Locate the active OV model folder dynamically (the one holding the encoder
    XML). A downloaded update in the user-data dir wins over the bundled copy."""
    cands = []
    user = _user_data_dir() / "models"
    if user.is_dir():
        cands += sorted(p for p in user.iterdir() if p.is_dir())
    bundled = _bundled_models_dir()
    if bundled.is_dir():
        cands += sorted(p for p in bundled.iterdir() if p.is_dir())
    valid = [d for d in cands if (d / MODEL_SENTINEL).exists()]
    if size:
        for d in valid:
            if f"whisper-{size}-" in d.name:
                return d
    return valid[0] if valid else None


def _write_revision(d: Path, repo: str):
    try:
        from huggingface_hub import HfApi
        sha = HfApi().model_info(repo).sha
        if sha:
            (d / ".hf_revision").write_text(sha, encoding="utf-8")
    except Exception:
        pass


def ensure_ov_model(size: str, progress=None) -> Path:
    """Local dir with the OV IR model; bundled, updated, or downloaded on demand."""
    d = _find_model_dir(size)
    if d is not None:
        return d
    if progress:
        progress(tf("Baixando modelo '{size}' (primeira vez)…", size=size))
    from huggingface_hub import snapshot_download
    repo = ov_model_repo(size)
    dest = _user_data_dir() / "models" / f"whisper-{size}-int8-ov"
    dest.parent.mkdir(parents=True, exist_ok=True)
    snapshot_download(repo, local_dir=str(dest))
    _write_revision(dest, repo)
    return dest


def _dir_writable(d: Path) -> bool:
    try:
        t = d / ".w_test"
        t.write_text("x", encoding="utf-8"); t.unlink()
        return True
    except Exception:
        return False


def update_model_if_newer(status_cb=None):
    """Check HF for a newer revision of the active model and replace it in place
    (atomic-ish), or in the user-data dir if the install folder is read-only.
    Fail-safe: any error (offline, API down…) leaves the current model intact."""
    try:
        d = _find_model_dir()
        if d is None:
            return
        repo = _repo_for_dir(d)
        from huggingface_hub import HfApi, snapshot_download
        latest = HfApi().model_info(repo).sha
        rev_file = d / ".hf_revision"
        local = rev_file.read_text(encoding="utf-8").strip() if rev_file.exists() else None
        if not latest or latest == local:
            return
        if status_cb:
            status_cb(t("Atualizando modelo…"))
        import tempfile, shutil
        tmp = Path(tempfile.mkdtemp(prefix="reco_model_"))
        snapshot_download(repo, revision=latest, local_dir=str(tmp))
        target = d if _dir_writable(d.parent) else _user_data_dir() / "models" / d.name
        target.parent.mkdir(parents=True, exist_ok=True)
        bak = target.with_name(target.name + ".old")
        if bak.exists():
            shutil.rmtree(bak, ignore_errors=True)
        if target.exists():
            target.rename(bak)
        shutil.move(str(tmp), str(target))
        (target / ".hf_revision").write_text(latest, encoding="utf-8")
        if bak.exists():
            shutil.rmtree(bak, ignore_errors=True)
        if status_cb:
            status_cb(t("Modelo atualizado."))
    except Exception:
        pass


# ── App update check (notify only — opens the download page) ────────────────────
def _ver_tuple(s: str) -> tuple:
    import re
    nums = re.findall(r"\d+", s or "")
    return tuple(int(x) for x in nums[:3]) if nums else (0,)


def check_app_update():
    """Return (tag, url) if a newer GitHub release exists, else None. Fail-safe."""
    try:
        import urllib.request, json
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json", "User-Agent": "Reco"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
        tag = data.get("tag_name") or ""
        if _ver_tuple(tag) > _ver_tuple(APP_VERSION):
            return tag, (data.get("html_url")
                         or f"https://github.com/{GITHUB_REPO}/releases/latest")
    except Exception:
        pass
    return None


CANCELLED = "__cancelled__"   # sentinel: transcription stopped by the user


PROMPTS = {
    "pt": ("Reunião de trabalho em português brasileiro com alguns termos "
           "técnicos em inglês. Nomes de marcas e siglas em inglês são comuns."),
    "en": ("Work meeting in English with some product names and acronyms."),
}

# Speaker labels for channel-based diarization (mic = you; system loopback = who-
# ever is on the call — count unknown, hence the plural).
def _spk_me() -> str:
    return "Eu" if LANG == "pt" else "Me"

def _spk_them() -> str:
    return "Interlocutor(es)" if LANG == "pt" else "Speaker(s)"


# ── Settings ──────────────────────────────────────────────────────────────────
# Model (small), device (AUTO → NPU→iGPU→CPU), diarization and echo cancellation
# are all automatic — config keys still exist for power-user overrides, but there
# are no UI controls for them.


def write_mp3(path: Path, data: "np.ndarray", sr: int, channels: int,
              bitrate: int, vbr: bool = True):
    """Encode float32 [-1,1] (mono (n,) or stereo (n,2)) to MP3 (VBR by default)."""
    inter = np.ascontiguousarray(data, dtype=np.float32).reshape(-1)
    if inter.size == 0:
        raise ValueError("no audio to encode")
    pcm16 = np.clip(np.round(inter * 32767), -32768, 32767).astype("<i2")
    enc = lameenc.Encoder()
    if vbr:
        enc.set_vbr(4)                          # 4 = MTRH (standard VBR)
        enc.set_vbr_mean_bitrate_kbps(bitrate)
    else:
        enc.set_bit_rate(bitrate)
    enc.set_in_sample_rate(sr)
    enc.set_channels(channels)
    enc.set_quality(2)
    mp3 = enc.encode(pcm16.tobytes())
    mp3 += enc.flush()
    path.write_bytes(mp3)


# ── Device helpers (soundcard / WASAPI) ────────────────────────────────────────
def list_capture_devices():
    if not HAS_SC:
        return [], []
    mics, spks = [], []
    try:
        for m in sc.all_microphones(include_loopback=False):
            if getattr(m, "isloopback", False):
                continue
            mics.append((m.id, m.name))
    except Exception as e:
        print(f"[scan mic] {e}")
    try:
        for s in sc.all_speakers():
            spks.append((s.id, s.name))
    except Exception as e:
        print(f"[scan spk] {e}")
    return mics, spks


def default_mic_id() -> str | None:
    if not HAS_SC:
        return None
    try:
        return sc.default_microphone().id
    except Exception:
        return None


def default_speaker_id() -> str | None:
    if not HAS_SC:
        return None
    try:
        return sc.default_speaker().id
    except Exception:
        return None


def pick_device(devs: list, saved_id: str | None, default_id: str | None) -> str | None:
    ids = [d[0] for d in devs]
    if saved_id and saved_id in ids:
        return saved_id
    if default_id and default_id in ids:
        return default_id
    return devs[0][0] if devs else None


def name_for_id(devs: list, dev_id: str | None) -> str | None:
    return next((n for i, n in devs if i == dev_id), None)


def id_for_name(devs: list, name: str | None) -> str | None:
    return next((i for i, n in devs if n == name), None)


# ── Dual Recorder ─────────────────────────────────────────────────────────────
CAPTURE_SR = 48000
CHUNK = 1024


class NoAudioCaptured(Exception):
    pass


class DualRecorder:
    def __init__(self):
        self._stop_ev    = threading.Event()
        self._mic_chunks = []
        self._sys_chunks = []
        self._lk_mic     = threading.Lock()
        self._lk_sys     = threading.Lock()
        self._lk_state   = threading.Lock()
        self._on_level   = None
        self._on_error   = None
        self._threads    = []
        self._barrier    = None
        self._n_requested = 0
        self._n_errors    = 0
        self.recording   = False
        self.mic_ok      = False
        self.sys_ok      = False

    def start(self, mic_id, sys_id, on_level=None, on_error=None):
        if self.recording:
            return
        # Reap any leftover threads from a previous session before touching state.
        self._stop_ev.set()
        if self._barrier is not None:
            try: self._barrier.abort()
            except Exception: pass
        for t_ in self._threads:
            t_.join(timeout=3.0)
        self._threads = []

        # Fresh per-session lists: a leaked thread can only append to the old
        # list, never pollute the current recording.
        mic_chunks, sys_chunks = [], []
        with self._lk_mic:
            self._mic_chunks = mic_chunks
        with self._lk_sys:
            self._sys_chunks = sys_chunks

        self._on_level    = on_level
        self._on_error    = on_error
        self.mic_ok       = False
        self.sys_ok       = False
        self._n_errors    = 0
        self._n_requested = (mic_id is not None) + (sys_id is not None)
        self._barrier     = threading.Barrier(max(1, self._n_requested))
        self._stop_ev.clear()
        self.recording    = True

        if mic_id is not None:
            th = threading.Thread(target=self._rec_mic,
                                  args=(mic_id, mic_chunks, self._lk_mic),
                                  daemon=True)
            th.start(); self._threads.append(th)
        if sys_id is not None:
            th = threading.Thread(target=self._rec_sys,
                                  args=(sys_id, sys_chunks, self._lk_sys),
                                  daemon=True)
            th.start(); self._threads.append(th)

    def all_failed(self) -> bool:
        return self._n_requested > 0 and self._n_errors >= self._n_requested

    def _await_peer(self):
        if self._barrier is None:
            return
        try:
            self._barrier.wait(timeout=3.0)
        except Exception:
            pass

    def _fail(self, kind, msg):
        with self._lk_state:
            self._n_errors += 1
        if self._barrier is not None:
            try: self._barrier.abort()
            except Exception: pass
        print(f"[{kind}] {msg}")
        if self._on_error:
            self._on_error(kind, msg)

    def stop(self, progress=None, out_sr=48000, out_channels=1, bitrate=128,
             out_dir=None) -> Path:
        self._stop_ev.set()
        if self._barrier is not None:
            try: self._barrier.abort()
            except Exception: pass
        for t_ in self._threads:
            t_.join(timeout=3.0)
        self.recording = False
        with self._lk_mic:
            have_mic = bool(self._mic_chunks)
        with self._lk_sys:
            have_sys = bool(self._sys_chunks)
        if not have_mic and not have_sys:
            raise NoAudioCaptured()
        if progress:
            progress(t("Codificando MP3 e salvando…"))
        return self._save(out_sr, out_channels, bitrate, out_dir)

    def abort(self):
        self._stop_ev.set()
        if self._barrier is not None:
            try: self._barrier.abort()
            except Exception: pass
        for t_ in self._threads:
            t_.join(timeout=2.0)
        self.recording = False

    def _rec_mic(self, dev_id, chunks, lock):
        # WASAPI capture starts at __enter__ (Start); the barrier comes BEFORE it
        # so both streams start as synchronized as possible.
        try:
            rec = sc.get_microphone(dev_id, include_loopback=False).recorder(
                samplerate=CAPTURE_SR, channels=1, blocksize=CHUNK)
        except Exception as e:
            self._fail("mic", str(e)); return
        self._await_peer()
        try:
            with rec as r:
                self.mic_ok = True
                while not self._stop_ev.is_set():
                    data = r.record(numframes=CHUNK)
                    arr = data[:, 0] if data.ndim > 1 else data
                    arr = np.ascontiguousarray(arr, dtype=np.float32)
                    with lock:
                        chunks.append(arr)
                    if self._on_level and arr.size:
                        self._on_level("mic", float(np.sqrt(np.mean(arr ** 2))))
        except Exception as e:
            self._fail("mic", str(e))

    def _rec_sys(self, dev_id, chunks, lock):
        try:
            rec = sc.get_microphone(dev_id, include_loopback=True).recorder(
                samplerate=CAPTURE_SR, channels=2, blocksize=CHUNK)
        except Exception as e:
            self._fail("sys", str(e)); return
        self._await_peer()
        try:
            with rec as r:
                self.sys_ok = True
                while not self._stop_ev.is_set():
                    data = r.record(numframes=CHUNK)
                    mono = data.mean(axis=1) if data.ndim > 1 else data
                    mono = np.ascontiguousarray(mono, dtype=np.float32)
                    with lock:
                        chunks.append(mono)
                    if self._on_level and mono.size:
                        self._on_level("sys", float(np.sqrt(np.mean(mono ** 2))))
        except Exception as e:
            self._fail("sys", str(e))

    @staticmethod
    def _resample(arr: "np.ndarray", orig: int, target: int) -> "np.ndarray":
        if orig == target or arr.size == 0:
            return arr
        try:
            from scipy.signal import resample_poly
            g = math.gcd(int(orig), int(target))
            return resample_poly(arr.astype(np.float32), target // g, orig // g)
        except ImportError:
            new_len = max(1, -(-len(arr) * target // orig))
            x_old = np.arange(len(arr))
            x_new = np.linspace(0, len(arr) - 1, new_len)
            return np.interp(x_new, x_old, arr.astype(np.float32)).astype(np.float32)

    def _save(self, out_sr: int, out_channels: int, bitrate: int, out_dir=None) -> Path:
        with self._lk_mic:
            mic_raw = (np.concatenate(self._mic_chunks)
                       if self._mic_chunks else np.zeros(0, np.float32))
        with self._lk_sys:
            sys_raw = (np.concatenate(self._sys_chunks)
                       if self._sys_chunks else np.zeros(0, np.float32))

        mic_f = self._resample(mic_raw.astype(np.float32), CAPTURE_SR, out_sr)
        sys_f = self._resample(sys_raw.astype(np.float32), CAPTURE_SR, out_sr)

        n = max(len(mic_f), len(sys_f))
        mic_f = np.pad(mic_f, (0, max(0, n - len(mic_f))))[:n]
        sys_f = np.pad(sys_f, (0, max(0, n - len(sys_f))))[:n]

        if out_channels == 2:
            data = np.column_stack([
                np.clip(mic_f, -1.0, 1.0),
                np.clip(sys_f, -1.0, 1.0),
            ])
        else:
            mixed = mic_f + sys_f
            peak = float(np.abs(mixed).max()) if len(mixed) else 1.0
            if peak > 0.95:
                mixed = mixed * (0.95 / peak)
            data = mixed

        folder = Path(out_dir) if out_dir else OUTPUT_DIR
        folder.mkdir(parents=True, exist_ok=True)
        # 'reco' marks this as a dual-channel (mic+system) recording (see RECO_TAG).
        prefix = "gravacao_reco" if LANG == "pt" else "recording_reco"
        ts   = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = folder / f"{prefix}_{ts}.mp3"
        write_mp3(path, data, out_sr, out_channels, bitrate)
        return path


# ── Transcriber: OpenVINO GenAI, in-process (NPU / iGPU / CPU) ──────────────────
class OVTranscriber:
    WIN = 30.0      # seconds per window — Whisper's native frame; also our
                    # progress + cancellation granularity for long audio.

    def __init__(self):
        self._pipe    = None
        self._key     = None        # (size, device) the live pipeline was built for
        self._size    = "small"
        self._devpref = "AUTO"
        self._lock    = threading.Lock()
        self._cancel  = threading.Event()

    def set_model(self, size: str):
        with self._lock:
            self._size = size

    def set_device(self, pref: str):
        with self._lock:
            self._devpref = pref

    def cancel(self):
        self._cancel.set()

    def _pipeline(self, progress_cb):
        with self._lock:
            size, devpref = self._size, self._devpref
        device = resolve_device(devpref)
        key = (size, device)
        if self._pipe is not None and self._key == key:
            return self._pipe
        model_dir = ensure_ov_model(size, progress=progress_cb)
        if progress_cb:
            progress_cb(tf("Preparando modelo no {dev}…", dev=device))
        import openvino_genai as og
        cache = _user_data_dir() / "ovcache"
        cache.mkdir(parents=True, exist_ok=True)
        # CACHE_DIR persists the compiled blob so the NPU's first-run compile (~40 s)
        # happens only once, ever; later loads are near-instant.
        pipe = og.WhisperPipeline(str(model_dir), device, CACHE_DIR=str(cache))
        self._pipe, self._key = pipe, key
        return pipe

    # Near-silent 30 s windows are skipped: Whisper has no built-in VAD and tends
    # to hallucinate repeated tokens ("BUSH BUSH BUSH…") on silence/noise.
    SILENCE_RMS = 0.0035

    def _gen_cfg(self, pipe, lang):
        cfg = pipe.get_generation_config()
        cfg.language = "<|%s|>" % lang
        cfg.task = "transcribe"
        cfg.return_timestamps = True
        # Break runaway repetition loops (a common Whisper failure on noise).
        try:
            cfg.no_repeat_ngram_size = 4
        except Exception:
            pass
        # NOTE: initial_prompt / hotwords overflow the NPU's static decoder
        # ("roi_end <= max_dim"), so we deliberately don't set them — language is
        # already forced, and channel diarization keeps each voice clean.
        return cfg

    def _transcribe_channel(self, pipe, cfg, audio, win_done, win_total,
                            progress_cb, ref=None):
        """Return ([(abs_start, text), …], windows_done); report progress per window.

        If `ref` is given (the system channel), the echo of `ref` is cancelled from
        each window before transcription — done per-window so memory stays bounded
        even on multi-hour files (a whole-file FFT would blow up to many GB)."""
        segs = []
        step = int(self.WIN * 16000)
        n = len(audio)
        i = 0
        while i < n:
            if self._cancel.is_set():
                return segs, win_done
            window = audio[i:i + step]
            if ref is not None:
                window = cancel_echo(window, ref[i:i + step])
            off = i / 16000.0
            rms = float(np.sqrt(np.mean(window ** 2))) if window.size else 0.0
            if rms >= self.SILENCE_RMS:        # skip near-silence (no hallucinations)
                res = pipe.generate(window, cfg)
                chunks = getattr(res, "chunks", None)
                if chunks:
                    for c in chunks:
                        txt = (c.text or "").strip()
                        if txt:
                            segs.append((off + float(c.start_ts), txt))
                else:
                    txt = (" ".join(res.texts).strip()
                           if getattr(res, "texts", None) else "")
                    if txt:
                        segs.append((off, txt))
            win_done += 1
            if progress_cb and win_total:
                progress_cb(tf("Transcrevendo… {p}%",
                               p=min(99, int(win_done / win_total * 100))))
            i += step
        return segs, win_done

    def transcribe(self, path, lang="pt", diarize=False, aec=False,
                   progress_cb=None, done_cb=None):
        self._cancel.clear()

        def run():
            try:
                pipe = self._pipeline(progress_cb)
                cfg  = self._gen_cfg(pipe, lang)
                if progress_cb:
                    progress_cb(t("Carregando áudio…"))
                chans = decode_16k(path, split=diarize)

                step = int(self.WIN * 16000)
                win_total = max(1, sum(max(1, -(-len(c) // step))
                                       for c in chans if len(c)))

                # Echo of the system (R) is cancelled from the mic (L) per-window
                # inside _transcribe_channel — keeps diarization honest without a
                # whole-file FFT (which would use many GB on long recordings).
                ref = chans[1] if (diarize and aec and len(chans) >= 2) else None

                if diarize and len(chans) >= 2:
                    me, done = self._transcribe_channel(
                        pipe, cfg, chans[0], 0, win_total, progress_cb, ref=ref)
                    if self._cancel.is_set():
                        if done_cb: done_cb(None, CANCELLED)
                        return
                    them, done = self._transcribe_channel(
                        pipe, cfg, chans[1], done, win_total, progress_cb)
                    if self._cancel.is_set():
                        if done_cb: done_cb(None, CANCELLED)
                        return
                    text = self._merge(me, them)
                else:
                    segs, _ = self._transcribe_channel(
                        pipe, cfg, chans[0], 0, win_total, progress_cb)
                    if self._cancel.is_set():
                        if done_cb: done_cb(None, CANCELLED)
                        return
                    text = "\n".join(tx for _, tx in segs)

                if done_cb:
                    done_cb(text or "(no content recognized)", None)
            except Exception as e:
                if done_cb:
                    done_cb(None, str(e))

        threading.Thread(target=run, daemon=True).start()

    @staticmethod
    def _merge(me_segs, them_segs):
        """Interleave two channels by time; group consecutive same-speaker lines."""
        me, them = _spk_me(), _spk_them()
        tagged = ([(t0, me, tx) for t0, tx in me_segs] +
                  [(t0, them, tx) for t0, tx in them_segs])
        tagged.sort(key=lambda x: x[0])
        lines, cur, buf = [], None, []
        for _, spk, tx in tagged:
            if spk != cur:
                if buf:
                    lines.append(f"{cur}: " + " ".join(buf))
                cur, buf = spk, [tx]
            else:
                buf.append(tx)
        if buf:
            lines.append(f"{cur}: " + " ".join(buf))
        return "\n".join(lines)


# ── Transcriber: MLX (Apple Silicon GPU) — macOS only ──────────────────────────
# Same interface as OVTranscriber so the App is backend-agnostic. mlx-whisper runs
# the model on the Apple GPU via Apple's MLX framework; the device selector and
# CACHE_DIR don't apply. NOTE: this path is only exercised on macOS arm64 — the
# mlx_whisper import lives inside the methods so the module still loads on Windows.
class MLXTranscriber:
    WIN = 30.0

    def __init__(self):
        self._size   = "small"
        self._lock   = threading.Lock()
        self._cancel = threading.Event()

    def set_model(self, size: str):
        with self._lock:
            self._size = size

    def set_device(self, pref: str):
        pass                         # MLX always uses the Apple GPU

    def cancel(self):
        self._cancel.set()

    @staticmethod
    def _repo(size: str) -> str:
        # large-v3-turbo keeps its name; the rest are whisper-<size>-mlx.
        return f"mlx-community/whisper-{size}-mlx"

    def _transcribe_channel(self, repo, audio, lang, win_done, win_total,
                            progress_cb, ref=None):
        import mlx_whisper
        segs = []
        step = int(self.WIN * 16000)
        n = len(audio)
        i = 0
        while i < n:
            if self._cancel.is_set():
                return segs, win_done
            window = audio[i:i + step]
            if ref is not None:                       # per-window echo cancel
                window = cancel_echo(window, ref[i:i + step])
            off = i / 16000.0
            rms = float(np.sqrt(np.mean(window ** 2))) if window.size else 0.0
            if rms >= OVTranscriber.SILENCE_RMS:
                r = mlx_whisper.transcribe(
                    window, path_or_hf_repo=repo, language=lang,
                    task="transcribe", verbose=None)
                chunks = r.get("segments") or []
                if chunks:
                    for s in chunks:
                        txt = (s.get("text") or "").strip()
                        if txt:
                            segs.append((off + float(s.get("start", 0.0)), txt))
                else:
                    txt = (r.get("text") or "").strip()
                    if txt:
                        segs.append((off, txt))
            win_done += 1
            if progress_cb and win_total:
                progress_cb(tf("Transcrevendo… {p}%",
                               p=min(99, int(win_done / win_total * 100))))
            i += step
        return segs, win_done

    def transcribe(self, path, lang="pt", diarize=False, aec=False,
                   progress_cb=None, done_cb=None):
        self._cancel.clear()

        def run():
            try:
                with self._lock:
                    repo = self._repo(self._size)
                if progress_cb:
                    progress_cb(tf("Preparando modelo no {dev}…", dev="Apple GPU"))
                if progress_cb:
                    progress_cb(t("Carregando áudio…"))
                chans = decode_16k(path, split=diarize)
                step = int(self.WIN * 16000)
                win_total = max(1, sum(max(1, -(-len(c) // step))
                                       for c in chans if len(c)))
                ref = chans[1] if (diarize and aec and len(chans) >= 2) else None

                if diarize and len(chans) >= 2:
                    me, done = self._transcribe_channel(
                        repo, chans[0], lang, 0, win_total, progress_cb, ref=ref)
                    if self._cancel.is_set():
                        if done_cb: done_cb(None, CANCELLED)
                        return
                    them, done = self._transcribe_channel(
                        repo, chans[1], lang, done, win_total, progress_cb)
                    if self._cancel.is_set():
                        if done_cb: done_cb(None, CANCELLED)
                        return
                    text = OVTranscriber._merge(me, them)
                else:
                    segs, _ = self._transcribe_channel(
                        repo, chans[0], lang, 0, win_total, progress_cb)
                    if self._cancel.is_set():
                        if done_cb: done_cb(None, CANCELLED)
                        return
                    text = "\n".join(tx for _, tx in segs)

                if done_cb:
                    done_cb(text or "(no content recognized)", None)
            except Exception as e:
                if done_cb:
                    done_cb(None, str(e))

        threading.Thread(target=run, daemon=True).start()


def make_transcriber():
    """Pick the transcription backend for this platform."""
    if HAS_MLX:
        return MLXTranscriber()        # macOS arm64 → Apple GPU
    if HAS_OV:
        return OVTranscriber()         # Windows/Linux x86 → NPU/iGPU/CPU
    return None


# ── VU Meter ──────────────────────────────────────────────────────────────────
class VuMeter(tk.Canvas):
    DECAY = 0.82
    H = 4

    def __init__(self, parent, **kw):
        kw.setdefault("width", 90)
        super().__init__(parent, height=self.H, bg=CARD, bd=0,
                         highlightthickness=0, **kw)
        self._bar  = self.create_rectangle(0, 0, 0, self.H, fill=GREEN, outline="")
        self._peak = 0.0
        self.bind("<Configure>", lambda _: self._draw())

    def update_level(self, rms):
        self._peak = max(self._peak * self.DECAY, min(rms * 3.0, 1.0))
        self._draw()

    def reset(self):
        self._peak = 0.0
        self._draw()

    def _draw(self):
        w = max(self.winfo_width(), 1)
        bw = int(self._peak * w)
        color = (GREEN if self._peak < 0.45
                 else AMBER if self._peak < 0.75
                 else RED_C)
        self.coords(self._bar, 0, 0, bw, self.H)
        self.itemconfig(self._bar, fill=color)


# ── App states ────────────────────────────────────────────────────────────────
IDLE, RECORDING, STOPPED, BUSY = "idle", "recording", "stopped", "busy"

LANG_LABELS = {"pt": "Português", "en": "English"}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.configure(bg=BG)
        self.resizable(False, False)
        self.overrideredirect(True)            # frameless — the header is the title bar
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        _ico = _icon_file()
        if _ico:
            try:
                self.iconbitmap(default=str(_ico))
            except Exception:
                pass

        self._cfg          = load_config()
        self._out_dir      = (Path(self._cfg["output_dir"])
                              if self._cfg.get("output_dir") else default_output_dir())
        apply_theme(self._cfg.get("bg_color") or DEFAULT_BG,
                    self._cfg.get("accent_color") or DEFAULT_ACCENT)
        self.configure(bg=BG)
        self._state        = IDLE
        self._recorder     = DualRecorder() if (HAS_SC and HAS_NP and HAS_LAME) else None
        self._transcriber  = make_transcriber()
        if self._transcriber:
            self._transcriber.set_model(self._cfg.get("model", "small"))
            self._transcriber.set_device(self._cfg.get("device", "AUTO"))
        self._transcribing = False
        self._last_rec     = None
        self._mic_devs     = []
        self._sys_devs     = []
        self._start_ts     = 0.0
        self._final_dur    = "00:00:00"
        self._adv_shown    = False
        self._tr_win       = None
        self._tr_sel       = None
        self._tr_shown     = False
        self._pop          = None     # floating hover popup (STOPPED actions)
        self._pop_after    = None
        self._pop_anchor   = None
        self._ui_q         = queue.Queue()
        self._closing      = False

        self._apply_style()
        self._build()
        self.bind("<Map>", self._on_restore)

        # center on screen
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 3
        self.geometry(f"+{x}+{y}")

        self.wm_attributes("-alpha", 0.0)
        self.after(30, lambda: self._fade(0.0))
        self.after(40, self._drain_ui)
        self.after(100, self._scan_devices)
        self._update_shown = False
        self.after(1500, self._kick_update_checks)

    # ── update checks (model: auto; app: notify only) ───────────────────────────
    def _kick_update_checks(self):
        if not HAS_OV and not HAS_MLX:
            pass
        else:
            threading.Thread(target=lambda: update_model_if_newer(
                status_cb=lambda m: self._post(lambda: self._status(m))),
                daemon=True).start()
        def _app():
            res = check_app_update()
            if res:
                self._post(lambda: self._show_app_update(*res))
        threading.Thread(target=_app, daemon=True).start()

    def _show_app_update(self, tag, url):
        if self._update_shown:
            return
        self._update_shown = True
        try:
            lk = self._link(self._links_row,
                            tf("⬆ Nova versão {tag}", tag=tag),
                            lambda: self._open_url(url), fg=ACCENT, font=SEG_XS)
            lk.pack(side="left", padx=(12, 0))
        except Exception:
            pass

    def _open_url(self, url):
        try:
            os.startfile(url)
        except Exception:
            try:
                import webbrowser
                webbrowser.open(url)
            except Exception:
                pass

    # ── frameless window: drag + minimize ───────────────────────────────────────
    def _drag_start(self, e):
        self._dx = e.x_root - self.winfo_x()
        self._dy = e.y_root - self.winfo_y()

    def _drag_move(self, e):
        self.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    def _minimize(self):
        # overrideredirect breaks iconify on Windows — drop the frame momentarily,
        # iconify, and restore the frameless state when the window maps again.
        self.overrideredirect(False)
        self.update_idletasks()
        self.iconify()

    def _on_restore(self, e=None):
        if (e is None or e.widget is self) and self.state() == "normal":
            self.overrideredirect(True)

    def _winbtn(self, parent, glyph, cmd, hover):
        hf = _best_fg(hover)
        b = tk.Label(parent, text=glyph, font=("Segoe MDL2 Assets", 10),
                     bg=BG, fg=MUTED, cursor="hand2", padx=13)
        b.bind("<Button-1>", lambda e: cmd())
        b.bind("<Enter>", lambda e, b=b, h=hover, f=hf: b.config(bg=h, fg=f))
        b.bind("<Leave>", lambda e, b=b: b.config(bg=BG, fg=MUTED))
        return b

    # ── thread → UI marshalling (tkinter is not thread-safe) ───────────────────
    def _post(self, fn):
        self._ui_q.put(fn)

    def _drain_ui(self):
        if self._closing:
            return
        try:
            while True:
                fn = self._ui_q.get_nowait()
                try:
                    fn()
                except Exception:
                    pass
        except queue.Empty:
            pass
        self.after(40, self._drain_ui)

    def _fade(self, a=0.0):
        a = min(a + 0.07, 1.0)
        self.wm_attributes("-alpha", a)
        if a < 1.0:
            self.after(14, lambda: self._fade(a))

    # ── style ────────────────────────────────────────────────────────────────
    def _apply_style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        for name in ("D.TCombobox", "Sm.TCombobox", "XS.TCombobox"):
            s.configure(name,
                fieldbackground=CARD, background=CARD_H, foreground=TEXT,
                arrowcolor=MUTED, selectbackground=CARD_A, selectforeground=TEXT,
                borderwidth=0, relief="flat")
            s.map(name,
                fieldbackground=[("readonly", CARD), ("disabled", BG)],
                foreground=[("disabled", SUBTLE)])
        s.configure("D.TCombobox",  font=SEG_SM)
        s.configure("Sm.TCombobox", font=SEG_SM)
        s.configure("XS.TCombobox", font=SEG_XS)
        s.configure("D.Treeview",
            background=CARD, foreground=TEXT, fieldbackground=CARD,
            borderwidth=0, relief="flat", rowheight=26, font=SEG_SM)
        s.configure("D.Treeview.Heading",
            background=BG, foreground=MUTED, relief="flat",
            font=SEG_XS, borderwidth=0, padding=(6, 4))
        s.map("D.Treeview",
            background=[("selected", CARD_A)],
            foreground=[("selected", TEXT)])
        s.map("D.Treeview.Heading",
            background=[("active", CARD)], relief=[("active", "flat")])
        s.configure("D.Vertical.TScrollbar",
            background=CARD_H, troughcolor=CARD, arrowcolor=SUBTLE,
            borderwidth=0, gripcount=0)

    # ── widget factories ───────────────────────────────────────────────────────
    def _btn(self, parent, text, cmd, primary=False, danger=False, **kw):
        if danger:
            bg, abg, fg = RED_C, _mix(RED_C, "#000000", 0.18), "#FFFFFF"
        elif primary:
            bg, abg, fg = ACCENT, _mix(ACCENT, "#000000", 0.14), ACCENT_FG
        else:
            bg, abg, fg = CARD, CARD_H, TEXT
        b = tk.Button(
            parent, text=text, command=cmd,
            bg=bg, fg=fg, activebackground=abg, activeforeground=fg,
            relief="flat", bd=0, cursor="hand2",
            font=SEG_SB if (primary or danger) else SEG,
            padx=12, pady=7, **kw)
        b._bg, b._abg = bg, abg
        b.bind("<Enter>", lambda e, b=b: b.config(bg=b._abg)
               if str(b.cget("state")) != "disabled" else None)
        b.bind("<Leave>", lambda e, b=b: b.config(bg=b._bg)
               if str(b.cget("state")) != "disabled" else None)
        return b

    def _link(self, parent, text, cmd, fg=SUBTLE, font=SEG_XS):
        lb = tk.Label(parent, text=text, bg=BG, fg=fg, cursor="hand2", font=font)
        lb.bind("<Button-1>", lambda e: cmd())
        return lb

    # ── build ────────────────────────────────────────────────────────────────
    def _build(self):
        # Header doubles as the (custom) title bar: drag to move, controls at right.
        hdr = tk.Frame(self, bg=BG, height=42)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Frame(hdr, bg=ACCENT, width=4).pack(side="left", fill="y")
        title = tk.Label(hdr, text=APP_TITLE, bg=BG, fg=TEXT, font=SEG_LG)
        title.pack(side="left", padx=12)

        self._winbtn(hdr, "", self._on_close, RED_C).pack(side="right", fill="y")
        self._winbtn(hdr, "", self._minimize, CARD_H).pack(side="right", fill="y")

        for w in (hdr, title):
            w.bind("<Button-1>", self._drag_start)
            w.bind("<B1-Motion>", self._drag_move)

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)
        self._body = body

        # Recording and transcription are mutually exclusive views — you do one or
        # the other, so the transcribe view replaces the recording view in place.
        self._rec_section = tk.Frame(body, bg=BG)
        self._rec_section.pack(fill="x")
        self._build_meters(self._rec_section)
        self._build_recording(self._rec_section)
        self._build_links(body)
        self._build_advanced(body)
        self._build_transcribe_section(body)

    def _build_meters(self, body):
        vu_row = tk.Frame(body, bg=BG)
        vu_row.pack(fill="x", pady=(0, 10))
        for lbl, attr in [("MIC", "_vu_mic"), ("SISTEMA", "_vu_sys")]:
            col = tk.Frame(vu_row, bg=BG)
            col.pack(side="left", fill="x", expand=True,
                     padx=(0, 5) if attr == "_vu_mic" else (5, 0))
            tk.Label(col, text=t(lbl), bg=BG, fg=SUBTLE, font=SEG_XS).pack(anchor="w")
            vu = VuMeter(col)
            vu.pack(fill="x")
            setattr(self, attr, vu)

    def _build_recording(self, body):
        self._btn_row = tk.Frame(body, bg=BG)
        self._btn_row.pack(fill="x")
        self._btn_row2 = tk.Frame(body, bg=BG)
        self._btn_row2.pack(fill="x", pady=(4, 0))

        self._btn_gravar   = self._btn(self._btn_row, t("⬤  Gravar"),
                                        self._start_rec, primary=True)
        self._btn_parar    = self._btn(self._btn_row, t("⬛  Parar"),
                                        self._stop_rec, danger=True)

        # STOPPED state: compact icons. The icon itself performs the action;
        # hovering reveals a floating menu/caption over the interface (the window
        # never grows).
        self._ic_save = self._btn(self._btn_row, "⚡", self._conclude_and_transcribe,
                                  primary=True)
        self._ic_del  = self._btn(self._btn_row, "✕", self._conclude_delete, danger=True)
        self._ic_play = self._btn(self._btn_row, "▶", self._play_recording)
        # ⚡ : clickable menu (debounced hide so the mouse can move into it)
        self._ic_save.bind("<Enter>", lambda e: self._show_menu(self._ic_save, [
            ("⚡  Salvar + Transcrever", self._conclude_and_transcribe),
            ("✓  Salvar", self._conclude_save),
            ("🔤  Transcrever", self._conclude_and_transcribe)]), add="+")
        self._ic_save.bind("<Leave>", lambda e: self._schedule_hide_pop(), add="+")
        # ✕ / ▶ : the icon acts on click; hover shows a non-clickable caption
        self._ic_del.bind("<Enter>", lambda e: self._show_tip(self._ic_del,
                                                              "✕  Excluir"), add="+")
        self._ic_del.bind("<Leave>", lambda e: self._hide_pop(), add="+")
        self._ic_play.bind("<Enter>", lambda e: self._show_tip(self._ic_play,
                                                               "▶  Reproduzir"), add="+")
        self._ic_play.bind("<Leave>", lambda e: self._hide_pop(), add="+")

        self._timer_var = tk.StringVar(value="00:00:00")
        self._timer_lbl = tk.Label(self._btn_row, textvariable=self._timer_var,
                                    bg=BG, fg=TEXT, font=("Segoe UI Semibold", 20))
        self._dot = tk.Label(self._btn_row, text=" ●",
                             bg=BG, fg=RED_C, font=("Segoe UI", 12))

        self._status_var = tk.StringVar(value=t("Pronto para gravar."))
        tk.Label(body, textvariable=self._status_var, bg=BG, fg=SUBTLE,
                 font=SEG_XS, wraplength=300, justify="left").pack(
                     anchor="w", pady=(6, 0))

        self._set_rec_state(IDLE)

    def _build_links(self, body):
        row = tk.Frame(body, bg=BG)
        row.pack(fill="x", pady=(10, 0))
        self._links_row = row
        self._adv_link = self._link(row, t("⚙ Opções"), self._toggle_advanced)
        self._adv_link.pack(side="left")
        self._tr_link = self._link(row, t("Transcrever…"),
                                   self._toggle_transcribe_section,
                                   fg=ACCENT, font=SEG_SM)
        self._tr_link.pack(side="right")

    def _build_advanced(self, body):
        self._adv = tk.Frame(body, bg=BG)

        tk.Frame(self._adv, bg=BORDER, height=1).pack(fill="x", pady=(10, 8))

        for label, var_attr, cb_attr, cfg_key in [
            ("Entrada:", "_mic_var", "_mic_cb", "mic_device"),
            ("Saída:", "_sys_var", "_sys_cb", "sys_device"),
        ]:
            r = tk.Frame(self._adv, bg=BG)
            r.pack(fill="x", pady=2)
            tk.Label(r, text=t(label), bg=BG, fg=MUTED, font=SEG_SM,
                     width=9, anchor="w").pack(side="left")
            var = tk.StringVar()
            setattr(self, var_attr, var)
            cb = ttk.Combobox(r, textvariable=var, state="readonly",
                              style="D.TCombobox", font=SEG_SM, width=24)
            cb.pack(side="left")
            setattr(self, cb_attr, cb)
            var.trace_add("write",
                lambda *_, v=var, k=cfg_key: self._on_device_change(v, k))

        self._link(self._adv, t("↺ Atualizar dispositivos"),
                   self._scan_devices).pack(anchor="w", pady=(2, 6))

        # Auto-save folder (defaults to Documents\Reco; changeable)
        frow = tk.Frame(self._adv, bg=BG)
        frow.pack(fill="x", pady=(0, 2))
        tk.Label(frow, text=t("Pasta:"), bg=BG, fg=SUBTLE,
                 font=SEG_XS).pack(side="left", padx=(0, 4))
        self._link(frow, t("Alterar…"), self._pick_output_dir,
                   fg=ACCENT, font=SEG_XS).pack(side="right")
        self._dir_var = tk.StringVar(value=str(self._out_dir))
        tk.Label(frow, textvariable=self._dir_var, bg=BG, fg=MUTED, font=SEG_XS,
                 anchor="w").pack(side="left", fill="x", expand=True)

        # Model (small), device (Auto: NPU→iGPU→CPU), channel diarization and echo
        # cancellation are all automatic now — no controls here on purpose.

        # language selector
        lrow = tk.Frame(self._adv, bg=BG)
        lrow.pack(fill="x", pady=(8, 0))
        tk.Label(lrow, text=t("Idioma:"), bg=BG, fg=SUBTLE,
                 font=SEG_XS).pack(side="left", padx=(0, 4))
        self._lang_var = tk.StringVar(value=LANG_LABELS.get(LANG, "English"))
        self._lang_cb = ttk.Combobox(lrow, textvariable=self._lang_var,
                                     values=list(LANG_LABELS.values()),
                                     state="readonly", style="XS.TCombobox",
                                     font=SEG_XS, width=12)
        self._lang_cb.pack(side="left")
        self._lang_var.trace_add("write", lambda *_: self._on_lang_change())

        # Theme: pick background + accent (text colors auto-adjust for contrast)
        trow = tk.Frame(self._adv, bg=BG)
        trow.pack(fill="x", pady=(8, 0))
        tk.Label(trow, text=t("Tema:"), bg=BG, fg=SUBTLE,
                 font=SEG_XS).pack(side="left", padx=(0, 6))
        self._link(trow, t("Fundo"), self._pick_bg, fg=ACCENT,
                   font=SEG_XS).pack(side="left", padx=(0, 10))
        self._link(trow, t("Destaque"), self._pick_accent, fg=ACCENT,
                   font=SEG_XS).pack(side="left", padx=(0, 10))
        self._link(trow, t("Padrão"), self._reset_theme, fg=SUBTLE,
                   font=SEG_XS).pack(side="left")

        # Keyboard shortcut — opt-in (NOT created automatically by setup)
        self._sc_link = self._link(self._adv, "", self._toggle_shortcut)
        self._sc_link.pack(anchor="w", pady=(8, 0))
        self._update_shortcut_link()

        if not (HAS_SC and HAS_NP and HAS_LAME):
            self._status(t("Captura indisponível — instale soundcard, numpy e lameenc."))

    def _toggle_advanced(self):
        self._adv_shown = not self._adv_shown
        if self._adv_shown:
            self._adv.pack(fill="x")
            self._adv_link.config(text=t("⚙ Ocultar opções"), fg=ACCENT)
        else:
            self._adv.pack_forget()
            self._adv_link.config(text=t("⚙ Opções"), fg=SUBTLE)
        self.update_idletasks()
        self.geometry("")

    # ── config callbacks ─────────────────────────────────────────────────────
    def _on_device_change(self, var: tk.StringVar, cfg_key: str):
        devs = self._mic_devs if cfg_key == "mic_device" else self._sys_devs
        dev_id = id_for_name(devs, var.get())
        if dev_id:
            self._cfg[cfg_key] = dev_id
            save_config(self._cfg)

    def _on_lang_change(self):
        label = self._lang_var.get()
        code = next((c for c, lbl in LANG_LABELS.items() if lbl == label), None)
        if code:
            self._set_language(code)

    def _set_language(self, code):
        global LANG
        if code == LANG or self._state in (RECORDING, BUSY) or self._transcribing:
            return
        LANG = code
        self._cfg["language"] = code
        save_config(self._cfg)
        self._rebuild_ui()

    def _pick_output_dir(self):
        if self._state in (RECORDING, BUSY):
            return
        init = self._out_dir if self._out_dir.exists() else Path.home()
        d = filedialog.askdirectory(parent=self, title=t("Pasta de gravações"),
                                    initialdir=str(init))
        if d:
            self._out_dir = Path(d)
            self._cfg["output_dir"] = d
            save_config(self._cfg)
            self._dir_var.set(d)

    def _pick_bg(self):
        _, hx = colorchooser.askcolor(color=BG, parent=self, title=t("Cor de fundo"))
        if hx:
            self._set_theme(hx, ACCENT)

    def _pick_accent(self):
        _, hx = colorchooser.askcolor(color=ACCENT, parent=self,
                                      title=t("Cor de destaque"))
        if hx:
            self._set_theme(BG, hx)

    def _reset_theme(self):
        self._set_theme(DEFAULT_BG, DEFAULT_ACCENT)

    def _set_theme(self, bg, accent):
        if self._state in (RECORDING, BUSY) or self._transcribing:
            return
        apply_theme(bg, accent)
        self._cfg["bg_color"] = BG
        self._cfg["accent_color"] = ACCENT
        save_config(self._cfg)
        self.configure(bg=BG)
        self._rebuild_ui()

    def _rebuild_ui(self):
        # Rebuild the whole UI (used on language/theme change). Aux windows were
        # built with the old language/theme, so close them.
        try:
            if self._tr_win is not None and self._tr_win.winfo_exists():
                self._tr_win.destroy()
        except Exception:
            pass
        self._tr_win = None
        for c in self.winfo_children():
            c.destroy()
        self._adv_shown = False
        self._tr_shown = False
        self._apply_style()
        self._build()
        self._toggle_advanced()       # keep Options open (where the controls live)
        self._scan_devices()
        self.update_idletasks()
        self.geometry("")

    # ── recording state machine ───────────────────────────────────────────────
    def _set_rec_state(self, state):
        self._hide_pop()
        for w in self._btn_row.winfo_children():
            w.pack_forget()
        for w in self._btn_row2.winfo_children():
            w.pack_forget()

        if state == IDLE:
            self._btn_gravar.pack(side="left", padx=(0, 16))
            self._timer_lbl.pack(side="left")
        elif state == RECORDING:
            self._btn_parar.pack(side="left", padx=(0, 16))
            self._timer_lbl.pack(side="left")
            self._dot.pack(side="left")
        elif state == STOPPED:
            self._ic_save.pack(side="left", padx=(0, 8))
            self._ic_del.pack(side="left", padx=(0, 8))
            self._ic_play.pack(side="left")
            self._timer_var.set(self._final_dur)
            self._timer_lbl.pack(side="left", padx=(16, 0))
        elif state == BUSY:
            self._timer_lbl.pack(side="left")

        # Refit so the window shrinks back when a row empties out. Tk quirk: an
        # emptied frame keeps its old requested size, so force it small first.
        try:
            for fr in (self._btn_row, self._btn_row2):
                if not any(w.winfo_manager() for w in fr.winfo_children()):
                    fr.configure(width=1, height=1)
            self.update_idletasks()
            self.geometry("")
        except Exception:
            pass

    # ── hover popups for the compact STOPPED icons ──────────────────────────────
    def _make_pop(self, anchor):
        self._hide_pop()
        self._pop_anchor = anchor
        pop = tk.Toplevel(self, bg=BORDER)
        self._pop = pop
        pop.overrideredirect(True)
        try:
            pop.attributes("-topmost", True)
        except Exception:
            pass
        return pop

    def _place_pop(self, pop, anchor):
        pop.update_idletasks()
        x = anchor.winfo_rootx()
        y = anchor.winfo_rooty() + anchor.winfo_height() + 2
        pw = pop.winfo_reqwidth()
        sw = self.winfo_screenwidth()
        if x + pw > sw:
            x = max(0, sw - pw - 4)
        pop.geometry(f"+{x}+{y}")
        pop.lift()

    def _show_menu(self, anchor, items):
        # clickable menu (for the ⚡ icon); debounced hide so the mouse can move in
        self._cancel_hide_pop()
        if self._pop is not None and self._pop_anchor is anchor:
            return
        pop = self._make_pop(anchor)
        inner = tk.Frame(pop, bg=CARD)
        inner.pack(padx=1, pady=1)
        for label_key, cmd in items:
            row = tk.Label(inner, text=t(label_key), bg=CARD, fg=TEXT, font=SEG_SM,
                           anchor="w", cursor="hand2", padx=12, pady=7)
            row.pack(fill="x")
            row.bind("<Enter>", lambda e, r=row: r.config(bg=CARD_H))
            row.bind("<Leave>", lambda e, r=row: r.config(bg=CARD))
            row.bind("<Button-1>", lambda e, c=cmd: self._pop_action(c))
        pop.bind("<Enter>", lambda e: self._cancel_hide_pop())
        pop.bind("<Leave>", lambda e: self._schedule_hide_pop())
        self._place_pop(pop, anchor)

    def _show_tip(self, anchor, text_key):
        # non-clickable caption (for the ✕ / ▶ icons, which act on click)
        self._cancel_hide_pop()
        if self._pop is not None and self._pop_anchor is anchor:
            return
        pop = self._make_pop(anchor)
        tk.Label(pop, text=t(text_key), bg=CARD, fg=TEXT, font=SEG_SM,
                 padx=10, pady=5).pack(padx=1, pady=1)
        self._place_pop(pop, anchor)

    def _pop_action(self, cmd):
        self._hide_pop()
        self.after(1, cmd)               # defer so the popup is gone first

    def _hide_pop(self):
        self._pop_after = None
        self._pop_anchor = None
        if self._pop is not None:
            try:
                self._pop.destroy()
            except Exception:
                pass
            self._pop = None

    def _schedule_hide_pop(self):
        self._cancel_hide_pop()
        self._pop_after = self.after(220, self._hide_pop)

    def _cancel_hide_pop(self):
        if self._pop_after:
            try:
                self.after_cancel(self._pop_after)
            except Exception:
                pass
            self._pop_after = None

    # ── device scan ───────────────────────────────────────────────────────────
    def _scan_devices(self):
        if not (HAS_SC and HAS_NP):
            return
        if self._state in (RECORDING, BUSY):
            self._status(t("Não é possível atualizar dispositivos durante a gravação."))
            return
        self._status(t("Buscando dispositivos…"))
        threading.Thread(target=self._scan_thread, daemon=True).start()

    def _scan_thread(self):
        try:
            mics, spks = list_capture_devices()
            def_mic = default_mic_id()
            def_spk = default_speaker_id()
        except Exception as e:
            self._post(lambda msg=str(e):
                       self._status(tf("Erro ao listar dispositivos: {m}", m=msg)))
            return
        self._post(lambda: self._populate_devices(mics, spks, def_mic, def_spk))

    def _populate_devices(self, mics, spks, def_mic, def_spk):
        self._mic_devs = mics
        self._sys_devs = spks
        self._mic_cb["values"] = [n for _, n in mics]
        self._sys_cb["values"] = [n for _, n in spks]

        if mics:
            chosen = pick_device(mics, self._cfg.get("mic_device"), def_mic)
            self._mic_var.set(name_for_id(mics, chosen) or mics[0][1])
        else:
            self._mic_var.set("")

        if spks:
            chosen = pick_device(spks, self._cfg.get("sys_device"), def_spk)
            self._sys_var.set(name_for_id(spks, chosen) or spks[0][1])
        else:
            self._sys_var.set("")

        if not mics and not spks:
            self._status(t("Nenhum dispositivo de áudio encontrado."))
        elif not spks:
            self._status(t("Atenção: nenhuma saída de áudio para loopback."))
        else:
            self._status(t("Pronto para gravar."))

    # ── recording actions ──────────────────────────────────────────────────────
    def _out_settings(self) -> tuple:
        # Fixed format: 16 kHz stereo (L=mic, R=system) 128 kbps VBR — what
        # transcription, channel diarization and echo cancellation all need.
        return OUT_SR, OUT_CH, MP3_BR

    def _whisper_lang(self) -> str:
        return "pt" if LANG == "pt" else "en"

    def _start_rec(self):
        if not self._recorder:
            self._status(t("Captura indisponível — instale soundcard, numpy e lameenc."))
            return
        mic_id = id_for_name(self._mic_devs, self._mic_var.get())
        sys_id = id_for_name(self._sys_devs, self._sys_var.get())
        if mic_id is None and sys_id is None:
            self._status(t("Nenhuma fonte de áudio — abra Opções."))
            return

        self._state    = RECORDING
        self._start_ts = time.time()
        self._set_rec_state(RECORDING)
        self._vu_mic.reset()
        self._vu_sys.reset()
        self._set_combos_enabled(False)

        self._recorder.start(
            mic_id, sys_id,
            on_level=lambda src, rms: self._post(
                lambda s=src, r=rms: self._on_level(s, r)),
            on_error=lambda src, msg: self._post(
                lambda s=src, m=msg: self._on_stream_error(s, m)))

        self._tick_timer()
        self._blink_dot()
        self._status(t("Gravando…  (mic + sistema)"))

    def _set_combos_enabled(self, enabled):
        st = "readonly" if enabled else "disabled"
        for cb in (self._mic_cb, self._sys_cb, self._lang_cb):
            cb.config(state=st)

    def _on_stream_error(self, src, msg):
        if self._state != RECORDING:
            return
        which = t("microfone") if src == "mic" else t("áudio do sistema")
        if self._recorder and self._recorder.all_failed():
            self._abort_to_idle(tf("Nenhuma fonte pôde ser capturada ({which}): {m}",
                                   which=which, m=msg[:60]))
        else:
            self._status(tf("Falha ao capturar {which} (a outra fonte continua).",
                            which=which))

    def _abort_to_idle(self, msg):
        if self._recorder and self._recorder.recording:
            self._recorder.abort()
        self._vu_mic.reset()
        self._vu_sys.reset()
        self._set_combos_enabled(True)
        self._state = IDLE
        self._set_rec_state(IDLE)
        self._timer_var.set("00:00:00")
        self._status(msg)

    def _stop_rec(self):
        self._state = BUSY
        self._set_rec_state(BUSY)
        self._status(t("Salvando…"))
        sr, ch, br = self._out_settings()

        out_dir = self._out_dir

        def do_stop():
            try:
                path = self._recorder.stop(
                    progress=lambda m: self._post(lambda: self._status(m)),
                    out_sr=sr, out_channels=ch, bitrate=br, out_dir=out_dir)
                self._post(lambda: self._after_stop(path))
            except NoAudioCaptured:
                self._post(lambda: self._after_stop_error(
                    t("Nenhum áudio capturado — verifique as fontes selecionadas.")))
            except Exception as e:
                self._post(lambda msg=str(e): self._after_stop_error(
                    tf("Erro ao salvar: {m}", m=msg)))

        threading.Thread(target=do_stop, daemon=True).start()

    def _after_stop_error(self, msg):
        self._set_combos_enabled(True)
        self._vu_mic.reset()
        self._vu_sys.reset()
        self._state = IDLE
        self._set_rec_state(IDLE)
        self._timer_var.set("00:00:00")
        self._status(msg[:110])

    def _after_stop(self, path: Path):
        self._last_rec = path
        elapsed = int(time.time() - self._start_ts)
        h, r = divmod(elapsed, 3600)
        m, s = divmod(r, 60)
        self._final_dur = f"{h:02d}:{m:02d}:{s:02d}"
        self._vu_mic.reset()
        self._vu_sys.reset()
        self._set_combos_enabled(True)
        self._state = STOPPED
        self._set_rec_state(STOPPED)
        self._status(tf("Salvo: {n}  —  Escolha o que fazer:", n=path.name))

    def _conclude_save(self):
        self._state = IDLE
        self._set_rec_state(IDLE)
        self._timer_var.set("00:00:00")
        if self._last_rec:
            self._status(tf("Gravação salva: {n}", n=self._last_rec.name))
        else:
            self._status(t("Pronto para gravar."))

    def _conclude_and_transcribe(self):
        if self._transcribe_recording(delete_after=False):
            self._state = IDLE
            self._set_rec_state(IDLE)
            self._timer_var.set("00:00:00")

    def _conclude_delete(self):
        if self._last_rec and self._last_rec.exists():
            try:
                self._last_rec.unlink()
            except Exception as e:
                self._status(tf("Não foi possível excluir: {e}", e=e)); return
        self._last_rec = None
        self._state = IDLE
        self._set_rec_state(IDLE)
        self._timer_var.set("00:00:00")
        self._status(t("Gravação descartada."))

    def _conclude_transcribe_and_delete(self):
        if self._transcribe_recording(delete_after=True):
            self._state = IDLE
            self._set_rec_state(IDLE)
            self._timer_var.set("00:00:00")

    # ── timer / VU ──────────────────────────────────────────────────────────────
    def _tick_timer(self):
        if self._state != RECORDING:
            return
        e = int(time.time() - self._start_ts)
        h, r = divmod(e, 3600)
        m, s = divmod(r, 60)
        self._timer_var.set(f"{h:02d}:{m:02d}:{s:02d}")
        self.after(1000, self._tick_timer)

    def _blink_dot(self):
        if self._state != RECORDING:
            return
        fg = self._dot.cget("fg")
        self._dot.config(fg=BG if fg == RED_C else RED_C)
        self.after(600, self._blink_dot)

    def _on_level(self, src, rms):
        if src == "mic":
            self._vu_mic.update_level(rms)
        else:
            self._vu_sys.update_level(rms)

    # ── transcription core (auto-saves .txt next to the audio file) ─────────────
    def _autosave_txt(self, audio_path: Path, text: str):
        try:
            txt = audio_path.with_suffix(".txt")
            txt.write_text(text or "(no content recognized)", encoding="utf-8")
            return txt
        except Exception as e:
            print(f"[txt] {e}")
            return None

    def _stop_transcription(self):
        if not self._transcribing:
            return
        if self._transcriber:
            self._transcriber.cancel()

    def _run_transcriber(self, path: Path, status_cb, done_cb) -> bool:
        if not path or not path.exists():
            status_cb(t("Arquivo não encontrado."))
            return False
        if self._transcribing:
            status_cb(t("Já há uma transcrição em andamento."))
            return False
        if not self._transcriber:
            status_cb(t("Transcrição indisponível — instale openvino-genai."))
            return False

        self._transcribing = True
        status_cb(tf("Transcrevendo {n}…", n=path.name))
        self._transcriber.set_model(self._cfg.get("model", "small"))
        self._transcriber.set_device(self._cfg.get("device", "AUTO"))

        # Channel diarization + echo cancellation only apply to Reco's own
        # mic+system recordings; any other file is transcribed plainly.
        reco_rec = is_reco_recording(path)
        diarize = bool(self._cfg.get("diarize")) and reco_rec
        aec     = bool(self._cfg.get("aec")) and reco_rec

        def _done(text, err):
            self._transcribing = False
            done_cb(text, err)

        self._transcriber.transcribe(
            path, lang=self._whisper_lang(),
            diarize=diarize, aec=aec,
            progress_cb=lambda m: self._post(lambda: status_cb(m)),
            done_cb=lambda t_, e: self._post(lambda: _done(t_, e)))
        return True

    def _transcribe_recording(self, delete_after=False) -> bool:
        path = self._last_rec
        if not path or not path.exists():
            self._status(t("Nada para transcrever."))
            return False

        def done(text, err):
            if err == CANCELLED:
                self._status(t("Transcrição cancelada."))
                return
            if err:
                self._status(tf("Erro na transcrição: {e}", e=err))
                return
            txt = self._autosave_txt(path, text)
            if not txt:
                self._status(t("Transcrito, mas falha ao salvar o .txt."))
                return
            if delete_after:
                try:
                    path.unlink()
                except Exception:
                    pass
                self._status(tf("Transcrição salva: {n}. Áudio excluído.", n=txt.name))
            else:
                self._status(tf("Transcrição salva: {n}", n=txt.name))

        return self._run_transcriber(path, self._status, done)

    # ── inline transcribe section (expands the window; no separate window) ───────
    def _build_transcribe_section(self, body):
        sec = tk.Frame(body, bg=BG)
        self._tr_section = sec
        tk.Label(sec, text=t("TRANSCRIÇÃO"), bg=BG, fg=SUBTLE,
                 font=SEG_XS).pack(anchor="w", pady=(0, 6))

        nav = tk.Frame(sec, bg=BG)
        nav.pack(fill="x")
        self._link(nav, t("＋ Escolher arquivo…"), self._tr_browse,
                   fg=ACCENT, font=SEG_SM).pack(side="left")
        self._link(nav, t("Abrir pasta"), self._open_tr_folder,
                   font=SEG_SM).pack(side="right")

        self._tr_path_var = tk.StringVar(value=str(self._tr_sel) if self._tr_sel else "")
        tk.Label(sec, textvariable=self._tr_path_var, bg=BG, fg=SUBTLE,
                 font=SEG_XS, wraplength=300, justify="left").pack(
                     anchor="w", pady=(4, 0))

        arow = tk.Frame(sec, bg=BG)
        arow.pack(fill="x", pady=(8, 0))
        self._tr_btn = self._btn(arow, t("⚡  Transcrever"),
                                 self._tr_transcribe, primary=True)
        self._tr_btn.pack(side="left", padx=(0, 8))
        self._tr_stop = self._btn(arow, t("⬛  Parar"),
                                  self._stop_transcription, danger=True)
        # _tr_stop is packed only while transcribing

        self._tr_status_var = tk.StringVar(
            value=t("Selecione um arquivo e clique em Transcrever."))
        tk.Label(sec, textvariable=self._tr_status_var, bg=BG, fg=SUBTLE,
                 font=SEG_XS, wraplength=300, justify="left").pack(
                     anchor="w", pady=(8, 0))

    def _toggle_transcribe_section(self):
        # Recording ⇄ transcribe are exclusive views — swap one for the other.
        if self._state in (RECORDING, BUSY) or self._transcribing:
            return
        self._tr_shown = not self._tr_shown
        if self._tr_shown:
            if not self._tr_sel and self._last_rec and self._last_rec.exists():
                self._tr_sel = self._last_rec
                self._tr_path_var.set(str(self._tr_sel))
            self._rec_section.pack_forget()
            self._tr_section.pack(fill="x", before=self._links_row)
            self._tr_link.config(text=t("← Gravar"))
        else:
            self._tr_section.pack_forget()
            self._rec_section.pack(fill="x", before=self._links_row)
            self._tr_link.config(text=t("Transcrever…"))
        self.update_idletasks()
        self.geometry("")

    def _tr_set_status(self, msg):
        self._tr_status_var.set(msg)

    def _tr_show_stop(self, on):
        if on:
            self._tr_btn.config(state="disabled")
            self._tr_stop.pack(side="left")
        else:
            self._tr_stop.pack_forget()
            self._tr_btn.config(state="normal")

    def _tr_browse(self):
        p = filedialog.askopenfilename(
            title=t("Selecionar áudio"),
            filetypes=[(t("Áudio"), "*.mp3 *.wav *.m4a *.ogg *.flac"),
                       (t("Todos"), "*.*")])
        if not p:
            return
        self._tr_sel = Path(p)
        self._tr_path_var.set(str(self._tr_sel))
        self._tr_set_status(t("Selecione um arquivo e clique em Transcrever."))

    def _tr_transcribe(self):
        path = self._tr_sel
        if not path or not path.exists():
            self._tr_set_status(t("Selecione um arquivo válido."))
            return

        def done(text, err):
            self._tr_show_stop(False)
            if err == CANCELLED:
                self._tr_set_status(t("Transcrição cancelada."))
                return
            if err:
                self._tr_set_status(tf("Erro: {e}", e=err))
                return
            txt = self._autosave_txt(path, text)
            self._tr_set_status(tf("Salvo: {n}", n=txt.name) if txt
                                else t("Transcrito, mas falha ao salvar o .txt."))

        if self._run_transcriber(path, self._tr_set_status, done):
            self._tr_show_stop(True)

    def _open_tr_folder(self):
        folder = self._tr_sel.parent if self._tr_sel else self._out_dir
        try:
            folder.mkdir(parents=True, exist_ok=True)
            os.startfile(str(folder))
        except Exception:
            pass

    def _play_recording(self):
        if self._last_rec and self._last_rec.exists():
            try:
                os.startfile(str(self._last_rec))   # default audio player
            except Exception as e:
                self._status(tf("Erro: {e}", e=e))
        else:
            self._status(t("Nada para reproduzir."))

    # ── keyboard shortcut (opt-in, created from here — never automatically) ──────
    def _shortcut_path(self) -> Path:
        base = os.environ.get("APPDATA") or str(Path.home())
        return (Path(base) / "Microsoft" / "Windows" / "Start Menu" /
                "Programs" / f"{APP_NAME}.lnk")

    def _update_shortcut_link(self):
        exists = self._shortcut_path().exists()
        self._sc_link.config(
            text=t("⌨ Remover atalho") if exists
                 else t("⌨ Criar atalho (Ctrl+Shift+R)"),
            fg=ACCENT if exists else SUBTLE)

    def _toggle_shortcut(self):
        lnk = self._shortcut_path()
        try:
            if lnk.exists():
                lnk.unlink()
                self._status(t("Atalho removido."))
            else:
                self._create_shortcut(lnk)
                self._status(t("Atalho criado — abra pelo Menu Iniciar ou com Ctrl+Shift+R."))
        except Exception as e:
            self._status(tf("Não foi possível criar o atalho: {e}", e=e))
        self._update_shortcut_link()

    def _create_shortcut(self, lnk: Path):
        if IS_FROZEN:
            target, args = sys.executable, ""
            wd = str(Path(sys.executable).parent)
        else:
            exe = Path(sys.executable)
            pyw = exe.with_name("pythonw.exe")
            target = str(pyw if pyw.exists() else exe)
            script = str(Path(__file__).resolve())
            args = f'"{script}"'
            wd = str(Path(script).parent)
        lnk.parent.mkdir(parents=True, exist_ok=True)
        ps = (
            f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut({_ps_quote(str(lnk))});"
            f"$s.TargetPath={_ps_quote(target)};$s.Arguments={_ps_quote(args)};"
            f"$s.HotKey='CTRL+SHIFT+R';$s.WorkingDirectory={_ps_quote(wd)};"
            f"$s.IconLocation='shell32.dll,168';$s.Description='Reco';$s.Save()"
        )
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                       check=True, capture_output=True, **_no_window_kwargs())

    # ── helpers ──────────────────────────────────────────────────────────────
    def _status(self, msg):
        self._status_var.set(msg)

    def _on_close(self):
        self._closing = True
        if self._recorder and self._recorder.recording:
            self._recorder.abort()
        try:
            while True:
                fn = self._ui_q.get_nowait()
                try:
                    fn()
                except Exception:
                    pass
        except queue.Empty:
            pass
        self._transcribing = False
        self.destroy()


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        import tempfile
        devs = ov_available_devices() if HAS_OV else []
        backend = ("mlx-whisper" if HAS_MLX else "openvino" if HAS_OV else "none")
        lines = [
            f"frozen={IS_FROZEN} lang={LANG} HAS_SC={HAS_SC} HAS_NP={HAS_NP} "
            f"HAS_LAME={HAS_LAME} HAS_OV={HAS_OV} HAS_AV={HAS_AV} HAS_MLX={HAS_MLX}",
            f"backend={backend}",
            f"ov_devices={devs}",
            f"resolved(AUTO)={resolve_device('AUTO') if HAS_OV else 'n/a'}",
            f"transcription_available={(HAS_OV or HAS_MLX) and HAS_AV}",
        ]
        Path(tempfile.gettempdir(), "reco_selftest.txt").write_text(
            "\n".join(lines) + "\n", encoding="utf-8")
        sys.exit(0)

    if "--transcribe" in sys.argv:
        # Headless transcription:  Reco.exe --transcribe <audio> [--diarize]
        # Saves <audio>.txt next to the file. Status/errors go to the log file
        # below (the windowed .exe has no console).
        import tempfile
        i = sys.argv.index("--transcribe")
        audio = Path(sys.argv[i + 1])
        diar = "--diarize" in sys.argv
        log = Path(tempfile.gettempdir()) / "reco_transcribe_log.txt"
        log.write_text("starting\n", encoding="utf-8")
        tr = make_transcriber()
        if tr is None or not HAS_AV:
            log.write_text("ERROR: transcription backend/PyAV unavailable\n",
                           encoding="utf-8")
            sys.exit(2)
        cfg = load_config()
        tr.set_model(cfg.get("model", "small"))
        tr.set_device(cfg.get("device", "AUTO"))
        ev = threading.Event(); out = {}
        tr.transcribe(
            audio, lang=("pt" if LANG == "pt" else "en"), diarize=diar,
            aec=bool(cfg.get("aec")) and diar,
            progress_cb=lambda m: log.write_text(m + "\n", encoding="utf-8"),
            done_cb=lambda t_, e: (out.update(t=t_, e=e), ev.set()))
        ev.wait(36000)
        if out.get("e"):
            log.write_text(f"ERROR: {out['e']}\n", encoding="utf-8")
            sys.exit(2)
        txt = audio.with_suffix(".txt")
        txt.write_text(out.get("t") or "", encoding="utf-8")
        log.write_text(f"OK -> {txt}\n", encoding="utf-8")
        sys.exit(0)

    if not (HAS_SC and HAS_NP and HAS_LAME):
        _root = tk.Tk()
        _root.withdraw()
        missing = []
        if not HAS_NP:   missing.append("numpy")
        if not HAS_SC:   missing.append("soundcard")
        if not HAS_LAME: missing.append("lameenc")
        messagebox.showerror(
            t("Dependências ausentes"),
            tf("Para gravar áudio, instale as dependências:\n\n  pip install {pkgs}\n\n"
               "Abra um terminal e rode o comando acima. Depois, reinicie o {app}.",
               pkgs=" ".join(missing), app=APP_TITLE))
        _root.destroy()
        sys.exit(1)
    App().mainloop()
