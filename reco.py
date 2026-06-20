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
import wave
import datetime
import json
import os
import re
import math
import ctypes
import subprocess
from pathlib import Path

IS_FROZEN = getattr(sys, "frozen", False)   # running as a PyInstaller .exe?
APP_NAME  = "Reco"
APP_TITLE = "Reco"

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

OUTPUT_DIR = Path.home() / "Videos" / "Reco"

AUDIO_SEARCH = [
    OUTPUT_DIR,
    Path.home() / "Videos",
    Path.home() / "Desktop",
    Path.home() / "Downloads",
]

# ── Config persistence ─────────────────────────────────────────────────────────
CONFIG_PATH = Path.home() / ".reco_config.json"

_CFG_DEFAULTS: dict = {
    "language":    None,      # "pt" | "en" | None -> auto-detect from system
    "bg_color":    DEFAULT_BG,
    "accent_color": DEFAULT_ACCENT,
    "channels":    1,
    "sample_rate": 48000,     # 48 kHz = native WASAPI rate, no resampling
    "mp3_bitrate": 64,        # 64 kbps = small files, fine for speech
    "model":       "small",
    "mic_device":  None,      # soundcard device id (str)
    "sys_device":  None,      # soundcard speaker id (str)
}

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
    # advanced labels
    "Entrada (mic):": "Input (mic):",
    "Sistema (loop):": "System (loop):",
    "↺ Atualizar dispositivos": "↺ Refresh devices",
    "Canais:": "Channels:",
    "Taxa:": "Rate:",
    "MP3:": "MP3:",
    "Modelo:": "Model:",
    "Idioma:": "Language:",
    "⌨ Criar atalho (Ctrl+Shift+R)": "⌨ Create shortcut (Ctrl+Shift+R)",
    "⌨ Remover atalho": "⌨ Remove shortcut",
    "Atalho criado — abra pelo Menu Iniciar ou com Ctrl+Shift+R.":
        "Shortcut created — open from the Start Menu or with Ctrl+Shift+R.",
    "Atalho removido.": "Shortcut removed.",
    "Não foi possível criar o atalho: {e}":
        "Couldn't create the shortcut: {e}",
    "tiny · small (padrão) · medium": "tiny · small (default) · medium",
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
    "faster-whisper não instalado — rode setup.ps1":
        "faster-whisper not installed — run setup.ps1",
    "Preparando transcrição…": "Preparing transcription…",
    "Verificando componentes…": "Checking components…",
    "componentes de transcrição não instalados — use o instalador que abriu":
        "transcription components not installed — use the installer that opened",
    "Transcrevendo {n}…": "Transcribing {n}…",
    "Carregando modelo…": "Loading model…",
    "Transcrevendo…": "Transcribing…",
    "Transcrevendo… {p}%": "Transcribing… {p}%",
    "Carregando modelo '{size}' (primeira vez faz download)…":
        "Loading model '{size}' (first time downloads it)…",
    "a transcrição falhou (código {c})": "transcription failed (code {c})",
    "Erro na transcrição: {e}": "Transcription error: {e}",
    "Transcrito, mas falha ao salvar o .txt.":
        "Transcribed, but failed to save the .txt.",
    "Transcrição salva: {n}. Áudio excluído.":
        "Transcription saved: {n}. Audio deleted.",
    "Transcrição salva: {n}": "Transcription saved: {n}",
    "Python não encontrado — instale o Python {v} (python.org).":
        "Python not found — install Python {v} (python.org).",
    # transcribe window
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


# ── Transcription (faster-whisper), delegated to system Python in the .exe ─────
def _user_deps_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / APP_NAME / "deps"


def _no_window_kwargs() -> dict:
    return {"creationflags": 0x08000000} if os.name == "nt" else {}


def _ps_quote(s: str) -> str:
    """Quote a string as a PowerShell single-quoted literal."""
    return "'" + s.replace("'", "''") + "'"


def _system_python_cmd() -> list | None:
    """A system Python matching this app's version (for transcription/install)."""
    import shutil
    py = shutil.which("py")
    if py:
        return [py, f"-{sys.version_info.major}.{sys.version_info.minor}"]
    for c in ("python", "python3"):
        p = shutil.which(c)
        if p:
            return [p]
    return None


def _system_has_whisper(cmd=None) -> bool:
    cmd = cmd or _system_python_cmd()
    if not cmd:
        return False
    try:
        r = subprocess.run(cmd + ["-c", "import faster_whisper"],
                           capture_output=True, text=True, timeout=60,
                           **_no_window_kwargs())
        return r.returncode == 0
    except Exception:
        return False


WhisperModel = None
HAS_WHISPER  = False

def _import_whisper() -> bool:
    global WhisperModel, HAS_WHISPER
    try:
        from faster_whisper import WhisperModel as _WM
        WhisperModel = _WM
        HAS_WHISPER = True
    except Exception:
        WhisperModel = None
        HAS_WHISPER = False
    return HAS_WHISPER

# In source we import in-process (model stays cached between transcriptions).
# In the frozen .exe we do NOT import: ctranslate2's native DLLs don't load in
# the frozen runtime — transcription is delegated to the system Python (subprocess).
if not IS_FROZEN:
    _import_whisper()


PROMPTS = {
    "pt": ("Reunião de trabalho em português brasileiro com alguns termos "
           "técnicos em inglês. Nomes de marcas e siglas em inglês são comuns."),
    "en": ("Work meeting in English with some product names and acronyms."),
}

# Worker run by the SYSTEM Python (where faster-whisper works): transcribes the
# audio and writes the text to out_txt. argv: audio model out_txt lang
_WORKER_SRC = (
    "import sys\n"
    "audio, model_size, out_txt, lang = sys.argv[1:5]\n"
    "print('STAGE loading', flush=True)\n"
    "from faster_whisper import WhisperModel\n"
    "m = WhisperModel(model_size, device='cpu', compute_type='int8')\n"
    "print('STAGE transcribing', flush=True)\n"
    "PROMPTS = {\n"
    "  'pt': ('Reuni\\u00e3o de trabalho em portugu\\u00eas brasileiro com alguns '\n"
    "         'termos t\\u00e9cnicos em ingl\\u00eas. Nomes de marcas e siglas em '\n"
    "         'ingl\\u00eas s\\u00e3o comuns.'),\n"
    "  'en': 'Work meeting in English with some product names and acronyms.',\n"
    "}\n"
    "segs, info = m.transcribe(audio, language=lang,\n"
    "                          initial_prompt=PROMPTS.get(lang),\n"
    "                          vad_filter=True,\n"
    "                          vad_parameters={'min_silence_duration_ms': 400})\n"
    "total = getattr(info, 'duration', 0) or 0\n"
    "parts = []\n"
    "for s in segs:\n"
    "    if s.text.strip():\n"
    "        parts.append(s.text.strip())\n"
    "    if total:\n"
    "        print('PROG ' + str(min(99, int(s.end / total * 100))), flush=True)\n"
    "text = '\\n'.join(parts) or '(no content recognized)'\n"
    "import io\n"
    "with io.open(out_txt, 'w', encoding='utf-8') as f:\n"
    "    f.write(text)\n"
    "print('DONE', flush=True)\n"
)


def _ensure_worker_script() -> Path:
    d = _user_deps_dir().parent
    d.mkdir(parents=True, exist_ok=True)
    wp = d / "transcribe_worker.py"
    try:
        if not wp.exists() or wp.read_text(encoding="utf-8") != _WORKER_SRC:
            wp.write_text(_WORKER_SRC, encoding="utf-8")
    except Exception:
        pass
    return wp


class PipProgress:
    """Estimate a % from pip's output (download/install)."""
    EST_MB = 220.0

    def __init__(self):
        self.done_mb = 0.0
        self.cur_mb  = 0.0
        self.pkg     = ""
        self.installing = False

    def feed(self, line: str):
        l = line.strip()
        if not l:
            return None, None
        m = re.search(r"Collecting ([\w\-\.\[\]]+)", l)
        if m:
            self.done_mb += self.cur_mb
            self.cur_mb = 0.0
            self.pkg = m.group(1)
            return self._pct(), tf("Baixando {pkg}…", pkg=self.pkg)
        m = re.search(r"([\d.]+)\s*/\s*([\d.]+)\s*MB", l)
        if m:
            try:
                self.cur_mb = float(m.group(1))
            except ValueError:
                pass
            return self._pct(), tf("Baixando {pkg}… {mb} MB",
                                   pkg=self.pkg, mb=f"{self.cur_mb:.0f}")
        if "Installing collected packages" in l:
            self.installing = True
            return 96, t("Instalando pacotes…")
        if "Successfully installed" in l:
            return 100, t("Concluído!")
        return None, None

    def _pct(self) -> int:
        if self.installing:
            return 96
        frac = (self.done_mb + self.cur_mb) / self.EST_MB
        return int(min(0.92, max(0.0, frac)) * 100)


# ── Audio settings ──────────────────────────────────────────────────────────
# 8000 Hz omitted on purpose: LAME ignores the chosen bitrate at that rate.
SR_OPTIONS  = [16000, 22050, 44100, 48000]
SR_LABELS   = ["16.000 Hz", "22.050 Hz", "44.100 Hz", "48.000 Hz"]
CH_OPTIONS  = [1, 2]
CH_LABELS   = ["Mono", "Estéreo"]
BR_OPTIONS  = [64, 96, 128, 192, 256]
BR_LABELS   = ["64 kbps", "96 kbps", "128 kbps", "192 kbps", "256 kbps"]


def write_mp3(path: Path, data: "np.ndarray", sr: int, channels: int, bitrate: int):
    """Encode float32 [-1,1] (mono (n,) or stereo (n,2)) to MP3."""
    inter = np.ascontiguousarray(data, dtype=np.float32).reshape(-1)
    if inter.size == 0:
        raise ValueError("no audio to encode")
    pcm16 = np.clip(np.round(inter * 32767), -32768, 32767).astype("<i2")
    enc = lameenc.Encoder()
    enc.set_bit_rate(bitrate)
    enc.set_in_sample_rate(sr)
    enc.set_channels(channels)
    enc.set_quality(2)
    mp3 = enc.encode(pcm16.tobytes())
    mp3 += enc.flush()
    path.write_bytes(mp3)


# ── Audio file helpers ──────────────────────────────────────────────────────
AUDIO_EXTS = ("*.mp3", "*.wav", "*.m4a", "*.ogg", "*.flac")


def audio_duration(path: Path) -> float:
    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as wf:
                return wf.getnframes() / wf.getframerate()
        except Exception:
            pass
    try:
        import av
        with av.open(str(path)) as c:
            if c.duration:
                return c.duration / 1_000_000
            st = c.streams.audio[0]
            if st.duration and st.time_base:
                return float(st.duration * st.time_base)
    except Exception:
        pass
    return 0.0


def fmt_dur(sec: float) -> str:
    sec = int(sec)
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def dur_label(path: Path) -> str:
    d = audio_duration(path)
    return fmt_dur(d) if d > 0 else "—"


def find_recent_audio(n=8) -> list:
    seen, files = set(), []
    for d in AUDIO_SEARCH:
        if not d.exists():
            continue
        for ext in AUDIO_EXTS:
            for pat in (ext, f"*/{ext}"):
                for p in d.glob(pat):
                    key = str(p).lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    try:
                        p.stat(); files.append(p)
                    except Exception:
                        pass
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:n]


def file_size_str(stat) -> str:
    mb = stat.st_size / 1_048_576
    return f"{mb:.0f} MB" if mb >= 1 else f"{stat.st_size // 1024} KB"


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

    def stop(self, progress=None, out_sr=48000, out_channels=1, bitrate=128) -> Path:
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
        return self._save(out_sr, out_channels, bitrate)

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

    def _save(self, out_sr: int, out_channels: int, bitrate: int) -> Path:
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

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ts   = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = OUTPUT_DIR / f"rec_{ts}.mp3"
        write_mp3(path, data, out_sr, out_channels, bitrate)
        return path


# ── Transcriber (in-process, source runs) ──────────────────────────────────────
class Transcriber:
    def __init__(self):
        self._model      = None
        self._model_size = "small"
        self._lock       = threading.Lock()

    def set_model(self, size: str):
        with self._lock:
            if size != self._model_size:
                self._model_size = size
                self._model = None

    def transcribe(self, path: Path, lang="pt", progress_cb=None, done_cb=None):
        def run():
            try:
                with self._lock:
                    size  = self._model_size
                    model = self._model
                if model is None:
                    if progress_cb:
                        progress_cb(tf(
                            "Carregando modelo '{size}' (primeira vez faz download)…",
                            size=size))
                    model = WhisperModel(size, device="cpu", compute_type="int8")
                    with self._lock:
                        if self._model_size == size:
                            self._model = model
                if progress_cb:
                    progress_cb(t("Transcrevendo…"))
                segs, info = model.transcribe(
                    str(path), language=lang,
                    initial_prompt=PROMPTS.get(lang),
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=400))
                total = getattr(info, "duration", 0) or 0
                parts = []
                for s in segs:
                    if s.text.strip():
                        parts.append(s.text.strip())
                    if progress_cb and total:
                        progress_cb(tf("Transcrevendo… {p}%",
                                       p=min(99, int(s.end / total * 100))))
                text = "\n".join(parts)
                if done_cb:
                    done_cb(text or "(no content recognized)", None)
            except Exception as e:
                if done_cb:
                    done_cb(None, str(e))
        threading.Thread(target=run, daemon=True).start()


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
        apply_theme(self._cfg.get("bg_color") or DEFAULT_BG,
                    self._cfg.get("accent_color") or DEFAULT_ACCENT)
        self.configure(bg=BG)
        self._state        = IDLE
        self._recorder     = DualRecorder() if (HAS_SC and HAS_NP and HAS_LAME) else None
        self._transcriber  = Transcriber()  if HAS_WHISPER else None
        self._transcribing = False
        self._last_rec     = None
        self._mic_devs     = []
        self._sys_devs     = []
        self._start_ts     = 0.0
        self._final_dur    = "00:00:00"
        self._adv_shown    = False
        self._tr_win       = None
        self._tr_sel       = None
        self._dep_win      = None
        self._installing   = False
        self._sys_whisper_ok = False
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

    def _combo(self, parent, labels, width, cfg_key, options, style="XS.TCombobox",
               font=SEG_XS):
        var = tk.StringVar()
        cb = ttk.Combobox(parent, textvariable=var, values=labels,
                          state="readonly", style=style, font=font, width=width)
        saved_val = self._cfg.get(cfg_key, _CFG_DEFAULTS.get(cfg_key))
        if saved_val in options:
            var.set(labels[options.index(saved_val)])
        else:
            var.set(labels[0])
        var.trace_add("write",
            lambda *_, v=var, k=cfg_key, o=options, lbs=labels:
                self._on_fmt_change(v, k, o, lbs))
        return var, cb

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

        self._build_meters(body)
        self._build_recording(body)
        self._build_links(body)
        self._build_advanced(body)

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
        self._adv_link = self._link(row, t("⚙ Opções"), self._toggle_advanced)
        self._adv_link.pack(side="left")
        self._link(row, t("Transcrever…"), self._open_transcribe_window,
                   fg=ACCENT, font=SEG_SM).pack(side="right")

    def _build_advanced(self, body):
        self._adv = tk.Frame(body, bg=BG)

        tk.Frame(self._adv, bg=BORDER, height=1).pack(fill="x", pady=(10, 8))

        for label, var_attr, cb_attr, cfg_key in [
            ("Entrada (mic):", "_mic_var", "_mic_cb", "mic_device"),
            ("Sistema (loop):", "_sys_var", "_sys_cb", "sys_device"),
        ]:
            r = tk.Frame(self._adv, bg=BG)
            r.pack(fill="x", pady=2)
            tk.Label(r, text=t(label), bg=BG, fg=MUTED, font=SEG_SM,
                     width=13, anchor="w").pack(side="left")
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

        self._ch_labels = [t(x) for x in CH_LABELS]
        self._sr_labels = [t(x) for x in SR_LABELS]
        self._br_labels = list(BR_LABELS)

        fmt1 = tk.Frame(self._adv, bg=BG)
        fmt1.pack(fill="x")
        tk.Label(fmt1, text=t("Canais:"), bg=BG, fg=SUBTLE,
                 font=SEG_XS).pack(side="left", padx=(0, 4))
        self._ch_var, self._ch_cb = self._combo(fmt1, self._ch_labels, 8,
                                                "channels", CH_OPTIONS)
        self._ch_cb.pack(side="left", padx=(0, 12))
        tk.Label(fmt1, text=t("Taxa:"), bg=BG, fg=SUBTLE,
                 font=SEG_XS).pack(side="left", padx=(0, 4))
        self._sr_var, self._sr_cb = self._combo(fmt1, self._sr_labels, 10,
                                                "sample_rate", SR_OPTIONS)
        self._sr_cb.pack(side="left")

        fmt2 = tk.Frame(self._adv, bg=BG)
        fmt2.pack(fill="x", pady=(6, 0))
        tk.Label(fmt2, text=t("MP3:"), bg=BG, fg=SUBTLE,
                 font=SEG_XS).pack(side="left", padx=(0, 4))
        self._br_var, self._br_cb = self._combo(fmt2, self._br_labels, 9,
                                                "mp3_bitrate", BR_OPTIONS)
        self._br_cb.pack(side="left", padx=(0, 12))
        tk.Label(fmt2, text=t("Modelo:"), bg=BG, fg=SUBTLE,
                 font=SEG_XS).pack(side="left", padx=(0, 4))
        self._model_var = tk.StringVar(value=self._cfg.get("model", "small"))
        self._model_cb = ttk.Combobox(fmt2, textvariable=self._model_var,
                                      values=["tiny", "small", "medium"],
                                      state="readonly", style="XS.TCombobox",
                                      font=SEG_XS, width=8)
        self._model_cb.pack(side="left")
        self._model_var.trace_add("write", lambda *_: self._on_model_change())

        tk.Label(self._adv, text=t("tiny · small (padrão) · medium"),
                 bg=BG, fg=SUBTLE, font=SEG_XS).pack(anchor="w", pady=(6, 0))

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

    def _on_fmt_change(self, var: tk.StringVar, cfg_key: str,
                       options: list, labels: list):
        label = var.get()
        if label in labels:
            self._cfg[cfg_key] = options[labels.index(label)]
            save_config(self._cfg)

    def _on_model_change(self):
        m = self._model_var.get()
        self._cfg["model"] = m
        save_config(self._cfg)
        if self._transcriber and not self._transcribing:
            self._transcriber.set_model(m)

    def _on_lang_change(self):
        label = self._lang_var.get()
        code = next((c for c, lbl in LANG_LABELS.items() if lbl == label), None)
        if code:
            self._set_language(code)

    def _set_language(self, code):
        global LANG
        if code == LANG or self._state in (RECORDING, BUSY):
            return
        LANG = code
        self._cfg["language"] = code
        save_config(self._cfg)
        self._rebuild_ui()

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
        if self._state in (RECORDING, BUSY):
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
        for w in (self._tr_win, self._dep_win):
            try:
                if w is not None and w.winfo_exists():
                    w.destroy()
            except Exception:
                pass
        self._tr_win = None
        self._dep_win = None
        for c in self.winfo_children():
            c.destroy()
        self._adv_shown = False
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
        sr = (SR_OPTIONS[self._sr_labels.index(self._sr_var.get())]
              if self._sr_var.get() in self._sr_labels else 48000)
        ch = (CH_OPTIONS[self._ch_labels.index(self._ch_var.get())]
              if self._ch_var.get() in self._ch_labels else 1)
        br = (BR_OPTIONS[self._br_labels.index(self._br_var.get())]
              if self._br_var.get() in self._br_labels else 128)
        return sr, ch, br

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
        for cb in (self._mic_cb, self._sys_cb, self._ch_cb, self._sr_cb,
                   self._br_cb, self._lang_cb):
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

        def do_stop():
            try:
                path = self._recorder.stop(
                    progress=lambda m: self._post(lambda: self._status(m)),
                    out_sr=sr, out_channels=ch, bitrate=br)
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

    # ── transcription core (auto-saves .txt to the output folder) ───────────────
    def _autosave_txt(self, audio_path: Path, text: str):
        try:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            txt = OUTPUT_DIR / (audio_path.stem + ".txt")
            txt.write_text(text or "(no content recognized)", encoding="utf-8")
            return txt
        except Exception as e:
            print(f"[txt] {e}")
            return None

    def _run_transcriber(self, path: Path, status_cb, done_cb) -> bool:
        if not path or not path.exists():
            status_cb(t("Arquivo não encontrado."))
            return False
        if self._transcribing:
            status_cb(t("Já há uma transcrição em andamento."))
            return False

        if IS_FROZEN:
            return self._run_transcriber_subprocess(path, status_cb, done_cb)

        if not HAS_WHISPER:
            status_cb(t("faster-whisper não instalado — rode setup.ps1"))
            return False

        self._transcribing = True
        status_cb(tf("Transcrevendo {n}…", n=path.name))
        self._transcriber.set_model(self._model_var.get())

        def _done(text, err):
            self._transcribing = False
            done_cb(text, err)

        self._transcriber.transcribe(
            path, lang=self._whisper_lang(),
            progress_cb=lambda m: self._post(lambda: status_cb(m)),
            done_cb=lambda t_, e: self._post(lambda: _done(t_, e)))
        return True

    def _run_transcriber_subprocess(self, path, status_cb, done_cb) -> bool:
        cmd = _system_python_cmd()
        if not cmd:
            status_cb(tf("Python não encontrado — instale o Python {v} (python.org).",
                         v=f"{sys.version_info.major}.{sys.version_info.minor}"))
            return False
        self._transcribing = True
        status_cb(t("Preparando transcrição…"))
        model = self._model_var.get()
        lang = self._whisper_lang()
        threading.Thread(target=self._subproc_worker,
                         args=(cmd, path, model, lang, status_cb, done_cb),
                         daemon=True).start()
        return True

    def _subproc_worker(self, cmd, path, model, lang, status_cb, done_cb):
        import tempfile
        out = Path(tempfile.gettempdir()) / "reco_tr_out.txt"

        def finish(text, err):
            self._transcribing = False
            done_cb(text, err)

        if not self._sys_whisper_ok:
            self._post(lambda: status_cb(t("Verificando componentes…")))
            if not _system_has_whisper(cmd):
                self._post(self._open_dep_installer)
                self._post(lambda: finish(None, t(
                    "componentes de transcrição não instalados "
                    "— use o instalador que abriu")))
                return
            self._sys_whisper_ok = True

        try:
            if out.exists():
                out.unlink()
        except Exception:
            pass

        try:
            self._post(lambda: status_cb(tf("Transcrevendo {n}…", n=path.name)))
            worker = _ensure_worker_script()
            full = cmd + [str(worker), str(path), model, str(out), lang]
            proc = subprocess.Popen(
                full, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                **_no_window_kwargs())
            for line in iter(proc.stdout.readline, ""):
                l = line.strip()
                if l == "STAGE loading":
                    self._post(lambda: status_cb(t("Carregando modelo…")))
                elif l == "STAGE transcribing":
                    self._post(lambda: status_cb(t("Transcrevendo…")))
                elif l.startswith("PROG "):
                    try:
                        pct = int(l[5:])
                    except ValueError:
                        pct = None
                    if pct is not None:
                        self._post(lambda p=pct:
                                   status_cb(tf("Transcrevendo… {p}%", p=p)))
            proc.stdout.close()
            rc = proc.wait()
            if rc == 0 and out.exists():
                text = out.read_text(encoding="utf-8")
                self._post(lambda tx=text: finish(tx, None))
            else:
                self._post(lambda c=rc: finish(
                    None, tf("a transcrição falhou (código {c})", c=c)))
        except Exception as e:
            self._post(lambda m=str(e): finish(None, m))
        finally:
            try:
                if out.exists():
                    out.unlink()
            except Exception:
                pass

    def _transcribe_recording(self, delete_after=False) -> bool:
        path = self._last_rec
        if not path or not path.exists():
            self._status(t("Nada para transcrever."))
            return False

        def done(text, err):
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

    # ── transcribe window ───────────────────────────────────────────────────────
    def _open_transcribe_window(self):
        if self._tr_win is not None and self._tr_win.winfo_exists():
            self._tr_win.deiconify(); self._tr_win.lift(); return

        win = tk.Toplevel(self, bg=BG)
        self._tr_win = win
        self._tr_sel = None
        win.title(t("Transcrever arquivo"))
        win.configure(bg=BG)
        win.resizable(False, False)

        def _close():
            self._tr_win = None
            win.destroy()
        win.protocol("WM_DELETE_WINDOW", _close)
        set_dark_titlebar(win)

        pad = tk.Frame(win, bg=BG)
        pad.pack(fill="both", expand=True, padx=16, pady=14)

        tk.Label(pad, text=t("ESCOLHA O ÁUDIO (MP3, WAV…)"), bg=BG, fg=SUBTLE,
                 font=SEG_XS).pack(anchor="w", pady=(0, 6))

        lc = tk.Frame(pad, bg=BORDER)
        lc.pack(fill="x")
        inner = tk.Frame(lc, bg=CARD)
        inner.pack(fill="x", padx=1, pady=1)
        cols = ("name", "date", "dur", "size")
        tree = ttk.Treeview(inner, columns=cols, show="headings", height=6,
                            selectmode="browse", style="D.Treeview")
        tree.heading("name", text=t("Arquivo"),  anchor="w")
        tree.heading("date", text=t("Data"),     anchor="center")
        tree.heading("dur",  text=t("Duração"),  anchor="center")
        tree.heading("size", text=t("Tamanho"),  anchor="e")
        tree.column("name", width=250, anchor="w",      stretch=True)
        tree.column("date", width=110, anchor="center", stretch=False)
        tree.column("dur",  width=70,  anchor="center", stretch=False)
        tree.column("size", width=70,  anchor="e",      stretch=False)
        tree.pack(fill="x")
        tree.bind("<<TreeviewSelect>>", self._tr_on_select)
        self._tr_tree = tree

        nav = tk.Frame(pad, bg=BG)
        nav.pack(fill="x", pady=(6, 0))
        self._link(nav, t("＋ Escolher outro arquivo…"), self._tr_browse,
                   fg=ACCENT, font=SEG_SM).pack(side="left")
        self._link(nav, t("↺ Atualizar"), self._tr_load, font=SEG_SM).pack(side="right")

        self._tr_path_var = tk.StringVar(value="—")
        tk.Label(pad, textvariable=self._tr_path_var, bg=BG, fg=SUBTLE,
                 font=SEG_XS, wraplength=520, justify="left").pack(
                     anchor="w", pady=(4, 0))

        actions = tk.Frame(pad, bg=BG)
        actions.pack(fill="x", pady=(10, 0))
        self._tr_btn = self._btn(actions, t("⚡ Transcrever e salvar .txt"),
                                 self._tr_transcribe, primary=True)
        self._tr_btn.pack(side="left")
        self._link(actions, t("Abrir pasta"), lambda: self._open_output_dir(),
                   font=SEG_SM).pack(side="right")

        self._tr_status_var = tk.StringVar(
            value=t("Selecione um arquivo e clique em Transcrever."))
        tk.Label(pad, textvariable=self._tr_status_var, bg=BG, fg=SUBTLE,
                 font=SEG_XS, wraplength=520, justify="left").pack(
                     anchor="w", pady=(8, 0))

        # In the .exe transcription runs in the system Python; only disable if
        # there is no Python at all.
        if IS_FROZEN:
            if _system_python_cmd() is None:
                self._tr_set_status(tf(
                    "Python não encontrado — instale o Python {v} (python.org).",
                    v=f"{sys.version_info.major}.{sys.version_info.minor}"))
                self._tr_btn.config(state="disabled")
        elif not HAS_WHISPER:
            self._tr_set_status(t("faster-whisper não instalado — rode setup.ps1"))
            self._tr_btn.config(state="disabled")

        win.update_idletasks()
        self._tr_load()

    def _tr_set_status(self, msg):
        if self._tr_win is not None and self._tr_win.winfo_exists():
            self._tr_status_var.set(msg)

    def _tr_load(self):
        def work():
            files = find_recent_audio()
            self._post(lambda: self._tr_populate(files))
        threading.Thread(target=work, daemon=True).start()

    def _tr_populate(self, files):
        if self._tr_win is None or not self._tr_win.winfo_exists():
            return
        tree = self._tr_tree
        for r in tree.get_children():
            tree.delete(r)
        if not files:
            tree.insert("", "end", tags=("placeholder",),
                        values=(t("Nenhum áudio encontrado"), "", "", ""))
            self._tr_sel = None
            self._tr_path_var.set("—")
            return
        for f in files:
            st = f.stat()
            dt = time.strftime("%d/%m  %H:%M", time.localtime(st.st_mtime))
            tree.insert("", "end", iid=str(f),
                        values=(f.name, dt, dur_label(f), file_size_str(st)))
        first = tree.get_children()[0]
        tree.selection_set(first)
        tree.focus(first)

    def _tr_on_select(self, _=None):
        sel = self._tr_tree.selection()
        if not sel:
            return
        if "placeholder" in self._tr_tree.item(sel[0], "tags"):
            self._tr_sel = None
            self._tr_path_var.set("—")
            return
        self._tr_sel = Path(sel[0])
        self._tr_path_var.set(str(self._tr_sel))

    def _tr_browse(self):
        p = filedialog.askopenfilename(
            parent=self._tr_win,
            title=t("Selecionar áudio"),
            filetypes=[(t("Áudio"), "*.mp3 *.wav *.m4a *.ogg *.flac"),
                       (t("Todos"), "*.*")])
        if not p:
            return
        path = Path(p)
        iid = str(path)
        if not self._tr_tree.exists(iid):
            try:
                st = path.stat()
                dt = time.strftime("%d/%m  %H:%M", time.localtime(st.st_mtime))
                self._tr_tree.insert("", 0, iid=iid,
                                     values=(path.name, dt, dur_label(path),
                                             file_size_str(st)))
            except Exception:
                pass
        self._tr_tree.selection_set(iid)
        self._tr_tree.focus(iid)
        self._tr_sel = path
        self._tr_path_var.set(str(path))

    def _tr_transcribe(self):
        path = self._tr_sel
        if not path or not path.exists():
            self._tr_set_status(t("Selecione um arquivo válido."))
            return
        win = self._tr_win
        btn = self._tr_btn
        setvar = self._tr_status_var

        def alive():
            return win is self._tr_win and win is not None and win.winfo_exists()

        btn.config(state="disabled")

        def status_cb(m):
            if alive():
                setvar.set(m)

        def done(text, err):
            if alive():
                btn.config(state="normal")
            if err:
                status_cb(tf("Erro: {e}", e=err))
                return
            txt = self._autosave_txt(path, text)
            status_cb(tf("Salvo: {n}  (na pasta {d})", n=txt.name, d=OUTPUT_DIR.name)
                      if txt else t("Transcrito, mas falha ao salvar o .txt."))

        if not self._run_transcriber(path, status_cb, done):
            if alive():
                btn.config(state="normal")

    def _open_output_dir(self):
        try:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            os.startfile(str(OUTPUT_DIR))
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

    # ── dependency installer (.exe only) ────────────────────────────────────────
    def _open_dep_installer(self):
        if self._dep_win is not None and self._dep_win.winfo_exists():
            self._dep_win.deiconify(); self._dep_win.lift(); return

        pycmd = _system_python_cmd()
        win = tk.Toplevel(self, bg=BG)
        self._dep_win = win
        win.title(t("Instalar transcrição"))
        win.configure(bg=BG)
        win.resizable(False, False)

        def _close():
            self._dep_win = None
            win.destroy()
        win.protocol("WM_DELETE_WINDOW", _close)
        set_dark_titlebar(win)

        pad = tk.Frame(win, bg=BG)
        pad.pack(fill="both", expand=True, padx=18, pady=16)
        tk.Label(pad, text=t("Componentes de transcrição"), bg=BG, fg=TEXT,
                 font=SEG_LG).pack(anchor="w")
        tk.Label(pad, text=t("O faster-whisper e suas dependências serão baixados e "
                             "instalados\numa pasta do seu usuário (~0,5 GB, alguns "
                             "minutos)."),
                 bg=BG, fg=SUBTLE, font=SEG_XS, justify="left").pack(
                     anchor="w", pady=(4, 12))

        barwrap = tk.Frame(pad, bg=BORDER)
        barwrap.pack(fill="x")
        inner = tk.Frame(barwrap, bg=CARD)
        inner.pack(fill="x", padx=1, pady=1)
        self._dep_bar = tk.Canvas(inner, height=14, bg=CARD, bd=0,
                                  highlightthickness=0)
        self._dep_bar.pack(fill="x")
        self._dep_barrect = self._dep_bar.create_rectangle(0, 0, 0, 14,
                                                           fill=ACCENT, outline="")

        prow = tk.Frame(pad, bg=BG)
        prow.pack(fill="x", pady=(6, 0))
        self._dep_pct = tk.StringVar(value="0%")
        tk.Label(prow, textvariable=self._dep_pct, bg=BG, fg=TEXT,
                 font=SEG_SB).pack(side="left")

        self._dep_status = tk.StringVar(value=t("Pronto para instalar."))
        tk.Label(pad, textvariable=self._dep_status, bg=BG, fg=SUBTLE,
                 font=SEG_XS, wraplength=380, justify="left").pack(
                     anchor="w", pady=(8, 0))

        btns = tk.Frame(pad, bg=BG)
        btns.pack(fill="x", pady=(12, 0))
        self._dep_btn = self._btn(btns, t("Instalar agora"),
                                  lambda: self._start_dep_install(pycmd), primary=True)
        self._dep_btn.pack(side="left")

        if not pycmd:
            self._dep_status.set(tf(
                "Python não encontrado no sistema. Instale o Python {v} (python.org) "
                "e tente de novo — ou rode pelo código-fonte.",
                v=f"{sys.version_info.major}.{sys.version_info.minor}"))
            self._dep_btn.config(state="disabled")
        win.update_idletasks()

    def _dep_set_progress(self, pct, msg=None):
        if self._dep_win is None or not self._dep_win.winfo_exists():
            return
        pct = max(0, min(100, int(pct)))
        w = max(self._dep_bar.winfo_width(), 1)
        self._dep_bar.coords(self._dep_barrect, 0, 0, int(w * pct / 100), 14)
        self._dep_pct.set(f"{pct}%")
        if msg is not None:
            self._dep_status.set(msg)

    def _start_dep_install(self, pycmd):
        if self._installing or not pycmd:
            return
        self._installing = True
        self._dep_btn.config(state="disabled")
        self._dep_set_progress(0, t("Iniciando instalação…"))
        threading.Thread(target=self._dep_install_worker,
                         args=(pycmd,), daemon=True).start()

    def _dep_install_worker(self, pycmd):
        try:
            cmd = pycmd + ["-m", "pip", "install", "--no-input", "--user",
                           "--upgrade", "faster-whisper"]
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                **_no_window_kwargs())
            parser = PipProgress()
            buf = ""
            while True:
                ch = proc.stdout.read(1)
                if not ch:
                    break
                if ch in "\r\n":
                    if buf.strip():
                        pct, msg = parser.feed(buf)
                        if pct is not None:
                            self._post(lambda p=pct, m=msg:
                                       self._dep_set_progress(p, m))
                    buf = ""
                else:
                    buf += ch
            proc.stdout.close()
            rc = proc.wait()
            if rc == 0:
                self._post(self._dep_done)
            else:
                self._post(lambda c=rc: self._dep_fail(tf(
                    "Falha na instalação (código {c}). "
                    "Verifique a conexão e tente de novo.", c=c)))
        except Exception as e:
            self._post(lambda m=str(e): self._dep_fail(tf("Erro: {e}", e=m[:140])))

    def _dep_done(self):
        self._installing = False
        self._sys_whisper_ok = True
        self._dep_set_progress(
            100, t("Pronto! Componentes instalados. Pode transcrever agora."))
        self.after(2500, lambda: (self._dep_win.destroy()
                                  if self._dep_win is not None
                                  and self._dep_win.winfo_exists() else None))

    def _dep_fail(self, msg):
        self._installing = False
        self._dep_set_progress(0, msg)
        if self._dep_win is not None and self._dep_win.winfo_exists():
            self._dep_btn.config(state="normal")

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
        cmd = _system_python_cmd()
        lines = [
            f"frozen={IS_FROZEN} lang={LANG} HAS_SC={HAS_SC} HAS_NP={HAS_NP} "
            f"HAS_LAME={HAS_LAME} HAS_WHISPER_inproc={HAS_WHISPER}",
            f"system_python={cmd}",
            f"system_has_whisper={_system_has_whisper(cmd)}",
            f"transcription_available={(HAS_WHISPER and not IS_FROZEN) or _system_has_whisper(cmd)}",
        ]
        Path(tempfile.gettempdir(), "reco_selftest.txt").write_text(
            "\n".join(lines) + "\n", encoding="utf-8")
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
