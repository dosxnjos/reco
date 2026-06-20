# Reco

**Record your microphone *and* your computer's audio at the same time, then transcribe it locally.**

A small Windows desktop app that captures the mic and the system output together
(real WASAPI loopback — no "Stereo Mix" needed), saves a compact MP3, and
transcribes it on your machine with [faster-whisper](https://github.com/SYSTRAN/faster-whisper).
Everything runs locally — nothing is uploaded. The interface is bilingual
(Portuguese / English), auto-detected from your system language.

<p align="center">
  <img src="docs/screenshot.png" alt="Reco — main window" width="320">
</p>

---

## English

### Features
- 🎙️ **Mic + system audio together** — capture a call/meeting with both sides, via
  true WASAPI loopback (works even when "Stereo Mix" is disabled).
- 📊 Live level meters for mic and system.
- 🎧 Saves a compact **MP3** (~6–12× smaller than WAV; great for speech).
- 📝 **Local transcription** (faster-whisper) that auto-saves a `.txt` next to your
  recordings. No cloud, fully private.
- 🌐 **Bilingual UI** (PT/EN), auto-detected, switchable in Options.
- ⚙️ Compact window; advanced settings (devices, channels, sample rate, MP3
  bitrate, model, language) tucked behind a toggle.

> Windows 10/11 only (uses WASAPI). Recordings are saved to `Videos\Reco`.

### Run from source
```powershell
pip install -r requirements.txt
python reco.py
```
Or run `./setup.ps1` to install the dependencies and create a Start-Menu
shortcut (**Ctrl+Shift+R**).

Required: `soundcard`, `numpy`, `lameenc`. Optional: `scipy` (better resampling),
`faster-whisper` (transcription; downloads a model ~0.5 GB on first use).

### Build a standalone .exe
```powershell
./build.ps1 -Clean      # -> dist/Reco.exe  (~55 MB)
```
The `.exe` records on its own. For **transcription** it doesn't bundle
faster-whisper (it's huge) — instead it uses a Python found on your system, and
offers a one-click installer (with a progress bar) the first time you transcribe.

### How it works
- Capture uses `soundcard` (WASAPI): each physical device is listed once, mics and
  speakers are separated, and system audio is captured via real loopback.
- Audio is captured at 48 kHz and encoded to MP3 with `lameenc`.
- Transcription uses faster-whisper (CPU, int8). In the frozen `.exe` it runs in a
  subprocess against the system Python, because ctranslate2's native DLLs don't
  load inside a PyInstaller bundle.

### License
[MIT](LICENSE) © 2026 Gabriel dos Anjos

---

## Português

**Grave o microfone *e* o áudio do computador ao mesmo tempo e transcreva localmente.**

Aplicativo de desktop para Windows que captura o microfone e a saída do sistema
juntos (loopback WASAPI de verdade — não precisa de "Mixagem estéreo"), salva um
MP3 compacto e transcreve na sua máquina com faster-whisper. Tudo roda local —
nada é enviado para a nuvem. A interface é bilíngue (PT/EN), detectada pelo idioma
do sistema.

### Recursos
- 🎙️ **Mic + áudio do sistema juntos** — grave uma reunião/chamada com os dois
  lados, via loopback WASAPI real (funciona mesmo sem "Mixagem estéreo").
- 📊 Barras de nível ao vivo para mic e sistema.
- 🎧 Salva um **MP3** compacto (~6–12× menor que WAV; ótimo para fala).
- 📝 **Transcrição local** (faster-whisper) que salva um `.txt` automaticamente
  junto das gravações. Sem nuvem, 100% privado.
- 🌐 **Interface bilíngue** (PT/EN), detectada automaticamente, troca em Opções.
- ⚙️ Janela compacta; opções avançadas (dispositivos, canais, taxa, bitrate MP3,
  modelo, idioma) escondidas atrás de um link.

> Apenas Windows 10/11 (usa WASAPI). As gravações vão para `Videos\Reco`.

### Rodar pelo código-fonte
```powershell
pip install -r requirements.txt
python reco.py
```
Ou rode `./setup.ps1` para instalar as dependências e criar um atalho no Menu
Iniciar (**Ctrl+Shift+R**).

Obrigatórias: `soundcard`, `numpy`, `lameenc`. Opcionais: `scipy` (melhor
reamostragem), `faster-whisper` (transcrição; baixa um modelo ~0,5 GB no 1º uso).

### Gerar um .exe independente
```powershell
./build.ps1 -Clean      # -> dist/Reco.exe  (~55 MB)
```
O `.exe` grava sozinho. Para **transcrever** ele não embute o faster-whisper (é
enorme) — usa um Python do seu sistema e oferece um instalador de um clique (com
barra de progresso) na primeira transcrição.

### Licença
[MIT](LICENSE) © 2026 Gabriel dos Anjos
