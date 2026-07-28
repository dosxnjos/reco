# Reco — instruções do projeto

App de desktop (Windows, Tkinter) que grava **microfone + áudio do sistema**
(WASAPI loopback) num MP3 estéreo (L=mic, R=sistema) e transcreve localmente via
OpenVINO GenAI (Whisper), com diarização por canal e cancelamento de eco.
Todo o código vive em `reco.py` (um arquivo só) + `tray.py` (bandeja).

**Memória/decisões deste projeto:** `C:\Dev\cerebro\projetos\reco.md`
(local desta máquina — ler antes de decisão não-trivial: pendências abertas,
decisões recentes).

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

## REGRA: MP3 sempre por container (nunca encoder cru)

⚠️ **Todo MP3 gerado aqui passa por `_open_mp3()` / `MP3Writer` — nunca por bytes
concatenados de um encoder.** Um MP3 sem o header `Xing`/`Info` não declara a
duração, e todo player passa a *estimá-la* pelo bitrate dos primeiros frames.
Como a gravação começa em silêncio (8 kbps) e depois sobe para ~90, a estimativa
saía **até 9× maior** que o real e o VLC mostrava o tempo restante pulando em vez
de descer 1s por segundo. Foi o bug corrigido em 28/07/2026 — o header é escrito
pelo muxer no `close()` do container, então **fechar o container não é opcional**.

Consequências práticas, para não reintroduzir o problema:

- **Não voltar para `lameenc`** (removido em 28/07): a API do python-lameenc não
  expõe `lame_get_lametag_frame`, então não há como escrever o header por ela.
- **ABR, não qscale.** O caminho `global_quality` do PyAV aplica um lowpass que
  corta tudo acima de ~4 kHz (medido: −46 dB e −72 dB nas bandas de 4-6k e 6-8k).
  Para voz é inaceitável e o Whisper piora junto. Use `bit_rate` + `{"abr": "1"}`.
- **Arquivo antigo com duração errada** se conserta por remux, sem re-encodar:
  `tools/reparar_duracao.py <pasta> --aplicar` (valida antes de substituir; sem
  `--aplicar` só relata). Rodado em 28/07/2026 nos 16 arquivos de `Documents\Reco`.

Medições e alternativas descartadas:
`roadmap/2026-07-28-duracao-mp3-e-salvamento-instantaneo.md`.

## Arquitetura essencial (antes de mexer)

- **Formato fixo, não configurável:** 16 kHz estéreo (L=mic, R=sistema), 96 kbps
  ABR. É exatamente o que transcrição + diarização por canal + AEC precisam
  (`OUT_SR`/`OUT_CH`/`MP3_BR`). Não "melhorar" para mono/44.1k sem entender isso.
  (O `MP3_BR` era 128 e **não tinha efeito nenhum** — o LAME em `vbr_mtrh` ignora
  o mean bitrate; medido, os arquivos sempre saíram a ~92 kbps. 96 em ABR
  reproduz esse mesmo resultado, agora de propósito.)
- **Captura:** `soundcard` (WASAPI). `DualRecorder` roda um thread por canal,
  sincronizados por um `threading.Barrier` antes do `__enter__` dos streams.
  Pausar **continua lendo e descarta** os frames (não para o stream) para os dois
  canais caírem em lockstep e L/R não dessincronizarem.
- **Encode em streaming (desde 28/07/2026):** um terceiro thread (`_encode_loop`)
  drena os buffers dos dois canais a cada 200 ms, pareia **só o trecho que ambos
  já entregaram** (`_pump`) e alimenta o `MP3Writer`; a sobra de quem está à
  frente fica em `_buf_mic`/`_buf_sys` até o par chegar — é isso que mantém L/R
  em sincronia. Consequências que **não** são acidentes e não devem ser
  "consertadas":
  - o **arquivo nasce no `start()`**, então o timestamp do nome é o do *início*
    da gravação (era o do fim) e um crash no meio deixa um MP3 parcial válido;
  - o **ganho por canal deixou de ser retroativo** — vale do momento em que o
    slider é movido em diante (era aplicado ao arquivo inteiro no save, o que é
    impossível quando o áudio já foi encodado);
  - `stop()` **não encoda nada**, só drena e fecha (~450 ms, contra ~11 s para
    20 min de gravação antes — e crescendo linearmente). Encodar no thread de
    captura seria pior que o problema original: a leitura do WASAPI atrasaria e o
    buffer estouraria (áudio perdido).
  - canal que falhou (`_fail`) sai do pareamento (`_mic_live`/`_sys_live`) e
    passa a ser preenchido com silêncio — senão um dispositivo morto trava o
    outro canal para sempre.
- **`RECO_TAG`** ("reco" no nome do arquivo) marca gravações dual-channel; só
  essas recebem diarização/AEC na tela de transcrever. Renomear o arquivo perde a marca.
- **Ganho por canal (mic/sys):** multiplicador linear por canal, ajustável ao vivo
  pelo slider arrastável sobre cada VU meter. Escala **bi-linear** com unity (1,0×)
  no centro: metade esquerda 0×..1× (atenua/muta), metade direita 1×..10× (amplifica);
  arrasto snapa em `GAIN_STEP` (0,5). Aplicado em `MP3Writer.feed`, bloco a bloco
  (ver acima: vale dali em diante, não retroativamente);
  o VU meter reflete o nível já ganhado e o multiplicador aparece
  embaixo da barra (`fmt_gain`, ex. "1,0x"). Persistido em `~/.reco_config.json`
  (`mic_gain`/`sys_gain`). Helpers `gain_to_frac`/`frac_to_gain`/`fmt_gain` e
  constantes `GAIN_MIN/UNITY/MAX/STEP`. Ver `docs/CONSOLIDADO-2026-07-15.md`.
- **Transcrição:** `OVTranscriber`, in-process, device `AUTO` (NPU/iGPU/CPU). Pula
  janelas de 30 s quase-silenciosas (`SILENCE_RMS`) p/ Whisper não alucinar.

## Ferramentas de apoio (`tools/`)

Rodam pelo fonte, com o venv do projeto — não entram no executável.

| script | para quê |
| --- | --- |
| `test_encoder.py` | testa o encoder sem hardware: duração declarada == real, header Xing, L/R separados, pareamento dos canais e `close()` instantâneo. Rodar **sempre** que mexer em `MP3Writer`/`_pump` |
| `test_gravacao_real.py [seg]` | grava de verdade pelos dispositivos padrão, mede o tempo do `stop()` e apaga o MP3 no fim |
| `reparar_duracao.py <pasta> [--aplicar]` | conserta a duração de MP3 antigos por remux (ver a regra acima) |

## Config e persistência

`~/.reco_config.json` via `load_config`/`save_config` (escrita atômica). Defaults
em `_CFG_DEFAULTS`. Ao adicionar uma opção nova, incluir o default lá.

## Ritual

Segue o ritual da raiz `C:\Dev` (plano em `roadmap/`, docs atualizadas,
consolidado datado em `docs/CONSOLIDADO-<data>.md` ao fim). A regra de compilar
acima é específica deste projeto e **não** é opcional.
