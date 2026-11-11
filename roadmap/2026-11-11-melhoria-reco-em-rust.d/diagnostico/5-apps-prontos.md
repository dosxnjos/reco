# Pronto antes de construir: o que já existe e faz o que o Reco faz (11/11/2026)

## Resumo

Nenhum app pronto junta as cinco coisas do Reco: Windows estável, mic e sistema gravados **separados** no arquivo, AEC, transcrição local acelerada por **OpenVINO (iGPU/NPU)** e uma CLI que os agentes usam. O mais perto é o **Anarlog** (o antigo Hyprnote, depois Char): é Tauri + Rust, MIT, mantém os dois fluxos separados e tem AEC. Só que no Windows ele ainda é beta, e não achei prova de transcrição local no Windows. O **Meetily** é o substituto direto mais maduro no Windows, mas mistura tudo em mono. Recomendo **construir**, na forma do Lacre, aproveitando o código de captura e as ideias desses dois.

---

## Tabela dos candidatos

Lido via GitHub API e README. A leitura de código veio por resumo do WebFetch, então trato como paráfrase, não citação literal.

| App | Stack / licença | Windows | Mic + sistema | Motor local / aceleração Intel | Quem falou | Maturidade |
|---|---|---|---|---|---|---|
| **Meetily** | Tauri + Rust + Next.js, MIT | Instalador nativo | Simultâneo, **somado em mono** | whisper.cpp **Vulkan** e Parakeet ONNX. OpenVINO não aparece | Prometida no "About", mas "speaker identification" é **PRO** (US$ 10/mês) | 32,6k estrelas, v0.4.1 (12/09/2026), 398 issues abertas |
| **Anarlog** (ex-Hyprnote/Char) | Tauri 2 + React + Rust, MIT (pasta `enterprise/` comercial) | **Beta** | **Separados** (`raw_mic`/`raw_speaker`) + AEC | whisper-local com features vulkan/cuda/…, pyannote-local com `directml`. OpenVINO não aparece | pyannote local + voiceprint | 9,9k estrelas, desktop_v1.4.34 (29/10/2026), issues desligadas |
| **Vibe** | Tauri + Rust (whisper.cpp), MIT | Sim, assinado | Grava os dois, depois **`amix`** (mistura) | Whisper/Parakeet/Nemotron, **Vulkan** (Intel incluída). OpenVINO não aparece | Sim | 8,1k estrelas, v3.3.0 (29/10/2026), 219 issues |
| **Handy** | Tauri 2 + Rust, MIT | Sim | **Só mic** (ditado aperta-e-fala) | Whisper GGUF (Vulkan provável), Parakeet | Não | 38,4k estrelas, v0.10.0 (02/11/2026) |
| **OpenWhispr** | **Electron 41**, MIT, nuvem paga opcional | Sim | Modo reunião. Não confirmei se capta o sistema | whisper.cpp CUDA/Vulkan, Parakeet sherpa-onnx | Diz ter, ao vivo | 11,3k estrelas, v1.11.0 (29/10/2026), **483 issues** |
| **Buzz** | Python, MIT | Sim, instalador sem assinatura | **Só mic** ao vivo | whisper.cpp Vulkan, CUDA, HF | Sim (`whisper_diarization`) | 22,7k estrelas, v1.4.5 (23/08/2026) |
| **noScribe** | Python, **GPL-3** | Sim | **Não grava**, só transcreve arquivo | faster-whisper + pyannote | Sim | 2,2k estrelas, v0.8 (06/10/2026) |
| **Scriberr** | Go + web, MIT, auto-hospedado | Via Docker/binário | Não grava | WhisperX/Parakeet/pyannote, foco CUDA | Sim | 3,1k estrelas, v1.2.0 (12/2025), parado desde 09/2026 |
| **Screenpipe** | Rust, **source-available comercial** | Sim | Mic + sistema. Não confirmei se separa | Whisper large-v3-turbo local | Diz ter | 22,3k estrelas. Licença impede fork |
| **Intel AI Playground** | Electron + Python, MIT | Sim, Core Ultra 2 H suportado | Não grava reunião | **Whisper (OV) em OpenVINO** | Não | 1k estrelas, v3.3.0-beta (30/10/2026) |
| **Plugins OpenVINO para Audacity** (Intel) | C++, GPL-3 | Sim | O Audacity grava um dispositivo por vez | **Whisper OpenVINO em GPU/NPU** | Não | 2,2k estrelas |
| **Whishper** | Web/Docker | — | Não grava | faster-whisper | — | A API do GitHub não achou `pluja/whishper` hoje. Fora do escopo |
| **Legenda ao vivo do Windows** | Nativo | Sim | Sistema, ou mic quando nada mais toca | Local | Não | **Não salva** transcrição |

Sobre Gravador de Voz e Clipchamp: **não verifiquei**. Que eu saiba, o Gravador grava só o mic e a legenda automática do Clipchamp roda na nuvem, mas é suspeita.

Fontes: [Meetily](https://github.com/Zackriya-Solutions/meetily), [release v0.4.1](https://github.com/Zackriya-Solutions/meetily/releases/tag/v0.4.1), [Anarlog](https://github.com/fastrepl/anarlog), [Vibe](https://github.com/thewh1teagle/vibe), [Handy](https://github.com/cjpais/Handy), [OpenWhispr](https://github.com/OpenWhispr/openwhispr), [Buzz](https://github.com/chidiwilliams/buzz), [noScribe](https://github.com/kaixxx/noScribe), [Scriberr](https://github.com/rishikanthc/Scriberr), [Screenpipe](https://github.com/screenpipe/screenpipe), [AI Playground](https://github.com/intel/AI-Playground), [plugins OpenVINO do Audacity](https://github.com/intel/openvino-plugins-ai-audacity), [Legenda ao vivo (Microsoft)](https://support.microsoft.com/windows/use-live-captions-to-better-understand-audio-b52da59c-14b8-4031-aeeb-f6a47e6055df), [Techlicious: não salva](https://www.techlicious.com/tip/how-to-use-windows-11-live-captions).

---

## O que li no código (via resumo)

**Meetily mistura tudo antes de transcrever e de gravar.** Em [`audio/pipeline.rs`](https://raw.githubusercontent.com/Zackriya-Solutions/meetily/main/frontend/src-tauri/src/audio/pipeline.rs), `ProfessionalAudioMixer::mix_window` soma mic e sistema. O resultado alimenta tanto o detector de voz (VAD) quanto o arquivo salvo, e cada trecho sai marcado como `DeviceType::Microphone // Mixed audio`.
- Não tem AEC. Para o mic há só um filtro passa-alta, RNNoise opcional e normalização EBU R128.
- O comentário fala em reduzir o sistema a 70%, mas o código multiplica por `1.0`.
- No Windows a captura passa pelo cpal: [`devices/speakers.rs`](https://raw.githubusercontent.com/Zackriya-Solutions/meetily/main/frontend/src-tauri/src/audio/devices/speakers.rs) pega a saída padrão via `cpal::host_from_id(HostId::Wasapi)`, e [`stream.rs`](https://raw.githubusercontent.com/Zackriya-Solutions/meetily/main/frontend/src-tauri/src/audio/stream.rs) chama `build_input_stream` nela. É o loopback WASAPI do cpal (input stream aberto num dispositivo de saída).
- Já [`capture/system.rs`](https://raw.githubusercontent.com/Zackriya-Solutions/meetily/main/frontend/src-tauri/src/audio/capture/system.rs) desiste com erro fora do macOS. Suspeita: é um caminho legado. O README e o instalador indicam que a captura funciona no Windows pelo cpal.

**Vibe grava os dois em WAVs separados e depois mistura.** Em [`cmd/audio.rs`](https://raw.githubusercontent.com/thewh1teagle/vibe/main/desktop/src-tauri/src/cmd/audio.rs), cpal + hound escrevem um WAV por dispositivo. Ao parar, [`ffmpeg.rs`](https://raw.githubusercontent.com/thewh1teagle/vibe/main/desktop/src-tauri/src/ffmpeg.rs) junta com `amix=inputs=2…,alimiter=limit=0.97`, ou seja, perde a separação por canal.

**Anarlog é o único com arquitetura parecida com a do Reco.**
- [`crates/audio/src/lib.rs`](https://raw.githubusercontent.com/fastrepl/anarlog/main/crates/audio/src/lib.rs) tem um `CaptureFrame` com `raw_mic`, `raw_speaker` e `aec_mic` opcional. `aec_dual()` devolve o mic limpo de eco junto com o sistema cru. Há ainda eventos de `Gap` com "clock padding" para não perder o alinhamento.
- [`crates/audio-actual/Cargo.toml`](https://raw.githubusercontent.com/fastrepl/anarlog/main/crates/audio-actual/Cargo.toml) usa a crate **`wasapi`** no Windows, mais cpal, ebur128 e ringbuf.
- [`crates/aec`](https://raw.githubusercontent.com/fastrepl/anarlog/main/crates/aec/Cargo.toml) é um AEC próprio (realfft + ONNX opcional) e tem benchmark.
- Diarização com `pyannote-local` (feature `directml`) e `voiceprint`.
- A transcrição local Whisper apareceu num changelog como "beta, Mac, só inglês" ([1.0.8](https://anarlog.so/changelog/desktop/1.0.8/)). O Windows segue beta, segundo a [busca](https://anarlog.so/blog/free-transcription-software-windows/).

---

## Para que cada um serve

**(a) Substituto direto para o Gabriel:** nenhum entrega o que o Reco já entrega.
- O Meetily é o único que dá para instalar e testar em 10 minutos. Mas "Eu × Interlocutor" vira uma diarização genérica (paga), não tem AEC, e no Arc ele roda por Vulkan.
- Suspeita: o Vulkan no Arc 130T deve ficar abaixo do OpenVINO GenAI que o Reco mediu (o iGPU saiu ~55% mais rápido que a NPU no large-v3-turbo, `C:\Dev\Reco\reco.py:180-186`). Não medi Vulkan contra OpenVINO nesta máquina.

**(b) Base para fork:** ruim nos dois casos.
- **Anarlog** é um monorepo enorme: mais de 150 crates, Supabase, calendário, CRM, Zoom. É o oposto de "rápido e simples", e as issues estão fechadas ao público.
- **Meetily** tem um pipeline mono no centro. Seria reescrever o coração (`pipeline.rs`), carregando 398 issues e um núcleo aberto com produto pago por cima.

**(c) Fonte de código e ideias:** ótimo.
1. **Loopback em Rust no Windows** tem dois caminhos já provados. Um é o cpal com `build_input_stream` num dispositivo de saída WASAPI (Meetily, Vibe). O outro é a crate `wasapi` direto (Anarlog), que dá mais controle de relógio e formato.
2. **O modelo de dados do Anarlog** (`CaptureFrame` com mic e sistema separados, eventos `Gap`/`ChannelFailed`, `with_retry` para reabrir o dispositivo) bate com o L/R do Reco e com o `estimar_offset` (`C:\Dev\Reco\CLAUDE.md`, "o que não é acidente" item 2).
3. **A crate `aec` do Anarlog** serve de comparação para o `cancel_echo` do Reco (`C:\Dev\Reco\reco.py:1026`). Só se aceitar medindo pelo par (ERLE, dano na voz) com `tools/medir_aec.py`, como a regra do projeto exige.
4. **A interface:** Handy e Vibe são referências de Tauri bonito e estável, com bandeja, onboarding e "não pula". Ideias, não código.

---

## O que só o Reco tem (lido no repo)

- **MP3 estéreo L=mic, R=sistema, de formato fixo** (`C:\Dev\Reco\reco.py:140-142`). A separação de quem falou sai do próprio arquivo, sem modelo e sem custo. Ninguém grava assim: Meetily e Vibe misturam, e o Anarlog separa só na memória e no banco.
- **AEC offline usando o loopback como referência** (`cancel_echo`, `reco.py:1026`) e **dominância** (`dominancia_sistema`, `reco.py:976`). Só o Anarlog tem AEC.
- **OpenVINO GenAI com seleção iGPU → NPU → CPU** (`reco.py:114`, `reco.py:569`, `reco.py:2062`). Entre os apps de reunião, nenhum usa OpenVINO. Só AI Playground e o plugin do Audacity, e nenhum dos dois grava reunião.
- **Defesa própria contra loop do Whisper** (`_degenerado`/`_generate_sem_loop`, `C:\Dev\Reco\CLAUDE.md` item 5).
- **`tools/transcrever.py`**: CLI que os agentes de `C:\Dev` usam, com `--diarizar`, `--aec`, `--device`, `--forcar` (`C:\Dev\Reco\tools\transcrever.py:164-179`, `import reco` na linha 37). Os outros têm CLI ou API (Vibe, Meetily PRO), mas não esse contrato.
- **A biblioteca é o filesystem** (mp3 + .txt + .resumo.md lado a lado, sem SQLite), contra o SQLite do Anarlog, Meetily e Screenpipe.

---

## Recomendação

**Construir, na forma do Lacre: Tauri 2 + Rust, com o motor Python atual embutido.**

O Lacre já faz isso: `C:\Dev\lacre\src-tauri\tauri.conf.json:45-47` empacota `engine/dist/lacre-engine/` como resource, e `C:\Dev\lacre\src-tauri\src\engine.rs:183` sobe o motor com `Command::new`. No Reco, o desenho fica assim:
- **Rust:** captura, encode e interface. A captura vem do caminho cpal/`wasapi`; o desenho dos frames, inspirado no Anarlog.
- **Motor Python congelado (PyInstaller):** transcrição OpenVINO, AEC e antiloop, que já estão medidos. Não reescrever.
- **CLI:** `tools/transcrever.py` continua igual.

Por que não usar pronto: perderia a separação L/R, o AEC e a aceleração OpenVINO, que hoje é a vantagem medida. Por que não forkar: os dois candidatos carregam produto, nuvem e escopo que o Gabriel não quer, e o defeito central (mistura mono, ou beta no Windows) fica no núcleo.

**Antes de construir (barato):**
1. Instalar o Meetily v0.4.1 e gravar uma reunião real de 10 min, para medir a velocidade do Vulkan no Arc 130T contra o Reco. Se o Vulkan empatar, a opção "Rust puro com whisper-rs" volta à mesa.
2. Conferir no `Cargo.toml` do whisper-rs se existe feature OpenVINO. Não verifiquei; até lá é suspeita.