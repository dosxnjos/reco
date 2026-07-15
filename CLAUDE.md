# Reco — instruções do projeto

App de desktop (Windows, Tkinter) que grava **microfone + áudio do sistema**
(WASAPI loopback) num MP3 estéreo (L=mic, R=sistema) e transcreve localmente via
OpenVINO GenAI (Whisper), com diarização por canal e cancelamento de eco.
Todo o código vive em `reco.py` (um arquivo só) + `tray.py` (bandeja).

## REGRA: sempre compilar após alterar o código

**Toda vez que mexer em `reco.py`/`tray.py` (ou qualquer coisa que entre no
executável), recompilar ao final** rodando:

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Dev\Reco\build.ps1"
```

O executável distribuído é `dist\Reco\Reco.exe` (PyInstaller, via `reco.spec`).
Sem recompilar, a mudança fica só no fonte e não chega ao app que o Gabriel usa.

- Build normal reaproveita `dist/`/`build/`; use `-Clean` para do zero.
- O modelo Whisper fica em `models\whisper-small-int8-ov` (bundlado, offline);
  se já existir, o build não rebaixa nem rebaixa.
- Warnings esperados e **inofensivos**: `openvino.torch`/`No module named 'torch'`
  (não usamos o frontend PyTorch). Não são erro de build.
- Ship: a pasta `dist\Reco\` inteira; rodar o `Reco.exe` de dentro dela.

## Arquitetura essencial (antes de mexer)

- **Formato fixo, não configurável:** 16 kHz estéreo (L=mic, R=sistema), 128 kbps
  VBR. É exatamente o que transcrição + diarização por canal + AEC precisam
  (`OUT_SR`/`OUT_CH`/`MP3_BR`). Não "melhorar" para mono/44.1k sem entender isso.
- **Captura:** `soundcard` (WASAPI). `DualRecorder` roda um thread por canal,
  sincronizados por um `threading.Barrier` antes do `__enter__` dos streams.
  Pausar **continua lendo e descarta** os frames (não para o stream) para os dois
  canais caírem em lockstep e L/R não dessincronizarem.
- **`RECO_TAG`** ("reco" no nome do arquivo) marca gravações dual-channel; só
  essas recebem diarização/AEC na tela de transcrever. Renomear o arquivo perde a marca.
- **Ganho por canal (mic/sys):** multiplicador linear por canal, ajustável ao vivo
  pelo slider arrastável sobre cada VU meter. Escala **bi-linear** com unity (1,0×)
  no centro: metade esquerda 0×..1× (atenua/muta), metade direita 1×..10× (amplifica);
  arrasto snapa em `GAIN_STEP` (0,5). Baked em `DualRecorder._save` (após resample,
  antes do clip); o VU meter reflete o nível já ganhado e o multiplicador aparece
  embaixo da barra (`fmt_gain`, ex. "1,0x"). Persistido em `~/.reco_config.json`
  (`mic_gain`/`sys_gain`). Helpers `gain_to_frac`/`frac_to_gain`/`fmt_gain` e
  constantes `GAIN_MIN/UNITY/MAX/STEP`. Ver `docs/CONSOLIDADO-2026-07-15.md`.
- **Transcrição:** `OVTranscriber`, in-process, device `AUTO` (NPU/iGPU/CPU). Pula
  janelas de 30 s quase-silenciosas (`SILENCE_RMS`) p/ Whisper não alucinar.

## Config e persistência

`~/.reco_config.json` via `load_config`/`save_config` (escrita atômica). Defaults
em `_CFG_DEFAULTS`. Ao adicionar uma opção nova, incluir o default lá.

## Ritual

Segue o ritual da raiz `C:\Dev` (plano em `roadmap/`, docs atualizadas,
consolidado datado em `docs/CONSOLIDADO-<data>.md` ao fim). A regra de compilar
acima é específica deste projeto e **não** é opcional.
