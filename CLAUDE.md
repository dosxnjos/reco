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
- O modelo Whisper fica em `models\whisper-small-int8-ov`
  ([README do modelo](models/whisper-small-int8-ov/README.md), bundlado, offline);
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
  constantes `GAIN_MIN/UNITY/MAX/STEP`. Decisão e medições:
  [`roadmap/2026-07-15-ganho-por-canal.md`](roadmap/2026-07-15-ganho-por-canal.md).
- **Transcrição:** `OVTranscriber`, in-process. Modelo padrão **`large-v3-turbo`**
  e device `AUTO` → **iGPU** (`resolve_device`, ordem `GPU → NPU → CPU`). As duas
  coisas foram **medidas em 29/07/2026**, não escolhidas por intuição — antes eram
  `small` e NPU-first. Segmenta por VAD (`segmentar_por_vad`/`agrupar_segmentos`,
  não janela cega de 30 s — fallback só se o VAD não achar fala), agrupa até
  `ALVO_ACUMULO_S=3.0` de fala e passa contexto via `initial_prompt` (últimas
  ~30 palavras por canal, desligado na NPU). Diarização usa `dominancia_sistema`
  para descartar trechos do mic dominados pelo sistema (eco/interlocutor), com
  `k_db=15` calibrado em `tools/calibrar_dominancia.py` — **⚠️ calibrar só contra
  "só o mic fala" já apagou fala real uma vez** (29/07), sempre confira também a
  população de double-talk (`ambos`) e valide por diff de transcrição real, não
  só por métrica de bloco. Ver `roadmap/2026-07-29-transcricao-precisa-rapida-e-aec.md`
  e `roadmap/2026-07-29-melhoria-transcricao-ao-vivo-vad-diarizacao.md`.
- **Transcrição ao vivo (`LiveTranscriber`, config `"live"`, default `False`):**
  rascunho durante a gravação, thread própria + `queue.Queue`, alimentada pelo
  `on_pair` do `DualRecorder._pump` (callback só enfileira — nenhum trabalho real
  ali). Segmento fechado (VAD), não janela deslizante — o texto nunca se
  reescreve. Reusa o pipeline já carregado do `OVTranscriber` (nunca uma 2ª
  instância, 828 MB). Ao parar: `LiveTranscriber.stop(wait=True)` **drena a fila
  antes de** disparar a passada final (`_run_live_final_pass` → `_run_transcriber`,
  o mesmo caminho da transcrição manual) — nunca duas chamadas a `pipe.generate`
  no mesmo `WhisperPipeline` ao mesmo tempo. ⚠️ **O teste de estresse de 20 min
  real continua pendente do Gabriel** (memória acumulando, cliques na UI e
  pausa/retomada em prazo longo) — rodado até aqui só um teste automatizado de
  170s (2m50) com WASAPI real (fala tocada pelos alto-falantes, não MP3
  simulado): duração bateu (erro −0,06s), drain em 0,8s, passada final sem
  conflito. Reduz o risco mas **não substitui** os 20 min; não tratar como
  "pronto pra uso diário" até isso acontecer.
- **Defesa anti-loop (`_degenerado` / `_generate_sem_loop`):** o Whisper trava em
  repetição (caso real: `"o que é"` 147× seguidas). ⚠️ **`no_repeat_ngram_size`
  NÃO resolve — o `WhisperPipeline` o ignora em silêncio**, e o GenAI não expõe
  `compression_factor_threshold`/`logprob_threshold`. A defesa é nossa: detecta
  por compressão zlib (> 2,4) e n-grama repetido (> 3×), refaz com temperatura
  0,2/0,4/0,6 e **descarta a janela** se tudo degenerar. Não substituir por
  parâmetro de config achando que existe um.
- **Modelo pedido sem match não cai em silêncio no bundlado (12/08/2026):**
  `_find_model_dir(size)` devolve `None` (não mais o primeiro modelo válido)
  quando o `size` pedido não existe no disco — `ensure_ov_model` baixa de
  verdade nesse caso; só usa o modelo bundlado (`small`) como fallback se o
  download falhar (offline), com status explícito. Antes, máquina nova
  transcrevia para sempre com `small` achando que usava `large-v3-turbo`.
- **Exclusão de gravação vai pra Lixeira (12/08/2026):** `_excluir_gravacao()`
  usa `SHFileOperationW` com `FOF_ALLOWUNDO` (ctypes, sem dependência nova);
  fallback `unlink()` fora do Windows ou se o shell recusar.
- **Instância única (12/08/2026):** mutex `Local\Reco.SingleInstance`
  (`CreateMutexW`) no `__main__`; uma 2ª instância detecta
  `ERROR_ALREADY_EXISTS`, manda a mensagem registrada `Reco.Show` pro
  `HWND_BROADCAST` e sai — `tray._wnd_proc` trata isso como um clique no
  ícone (mostra/ativa a janela da 1ª). `--selftest`/`--transcribe` saem antes
  desse ponto e nunca criam o mutex.
- **Cancelamento de eco (`cancel_echo`):** mínimos quadrados em blocos de 2 s com
  6 taps + pós-supressão residual. Entrega **~7 dB** de ERLE no áudio real (a
  versão anterior entregava ~3, apesar de "37 dB validados" — em eco sintético).
  ⚠️ **O teto não é o filtro, é a deriva de clock** entre mic e loopback
  (−65,8 ppm medidos, ~237 ms/hora). Não alongar o filtro esperando 20 dB.

## Ferramentas de apoio (`tools/`)

Rodam pelo fonte, com o venv do projeto — não entram no executável.

| script | para quê |
| --- | --- |
| `test_encoder.py` | testa o encoder sem hardware: duração declarada == real, header Xing, L/R separados, pareamento dos canais e `close()` instantâneo. Rodar **sempre** que mexer em `MP3Writer`/`_pump` |
| `test_gravacao_real.py [seg]` | grava de verdade pelos dispositivos padrão, mede o tempo do `stop()` e apaga o MP3 no fim |
| `reparar_duracao.py <pasta> [--aplicar]` | conserta a duração de MP3 antigos por remux (ver a regra acima) |
| `test_antiloop.py <mp3> [modelo] [device]` | roda as janelas mais fracas com e sem a defesa anti-loop. Rodar **sempre** que mexer em `_degenerado`/`_generate_sem_loop`. Critério: nenhum n-grama > 3× |
| `test_e2e.py <mp3>` | transcrição ponta a ponta pelo caminho real do app (decode + diarização + AEC + anti-loop), com tempo e extrapolação para 2 h |
| `medir_eco.py <mp3>` | acoplamento caixa→mic e ERLE do `cancel_echo` **em áudio real**. Rodar **sempre** que mexer no AEC — validar em eco sintético já mascarou uma implementação que entregava 3 dB |
| `bench_final.py <mp3> [n]` | device × modelo: velocidade, extrapolação p/ 2 h, e qualidade por divergência (WER) contra o melhor modelo disponível. `BENCH_MODELOS`/`BENCH_DEVICES`/`BENCH_MODO=fracas` filtram |
| `bench_convivencia.py <mp3> [n]` + `vizinho.py` | quanto a transcrição atrasa **outro app** (latência de um vizinho single-thread em processo separado). É o que decide iGPU × NPU |
| `bench_convivencia_pipeline.py <mp3>` | igual acima, mas com o pipeline REAL (`OVTranscriber.transcribe`, VAD+contexto+dominância) em vez de `pipe.generate()` cru — o que decide o orçamento de device do modo ao vivo |
| `calibrar_dominancia.py <mp3...>` | calibra `k_db` de `dominancia_sistema` contra `so_sys`/`so_mic`/`ambos` (double-talk) — rodar de novo com mais gravações se mexer no limiar; **sempre conferir por diff de transcrição real depois**, métrica de bloco sozinha já mascarou perda de fala real |
| `test_live.py <mp3> [seg]` | alimenta `LiveTranscriber` com um MP3 real em tempo real simulado (resample 16k→48k→16k), mede latência mediana do rascunho |
| `test_live_integration.py [seg]` | grava de verdade com `DualRecorder`+`LiveTranscriber` ligados, confere duração do MP3, tempo de drain e a passada final rodando sem conflito depois |
| `transcrever.py <arquivo...>` | transcreve **qualquer áudio/vídeo** para `<arquivo>.txt` pelo pipeline real (decode PyAV → VAD → anti-loop), sem UI — feito para **agentes** (Claude Code) lerem áudio que o Gabriel manda no chat. Pula `.txt` existente (`--forcar` refaz); `--diarizar`/`--aec` só para gravações estéreo do próprio Reco |

## Config e persistência

`~/.reco_config.json` via `load_config`/`save_config` (escrita atômica). Defaults
em `_CFG_DEFAULTS`. Ao adicionar uma opção nova, incluir o default lá.

⚠️ **Mudar um default NÃO alcança quem já usou o app.** `load_config()` deixa o
arquivo salvo sobrescrever os defaults — o que é correto (a escolha do usuário
tem de ganhar), mas significa que trocar `_CFG_DEFAULTS` é inócuo para qualquer
config existente. Se a mudança **precisa** chegar aos usuários atuais, suba
`CFG_MIGRACAO` e trate o caso em `_migra_config()`: ela roda uma vez (marcada em
`_migracao` dentro do próprio JSON) e só promove valores que eram o **default
antigo**, preservando escolha deliberada. Foi assim que `small` → `large-v3-turbo`
e `NPU` → `AUTO` chegaram na máquina do Gabriel em 29/07/2026.

## Armadilhas

[`docs/ARMADILHAS.md`](docs/ARMADILHAS.md) — o que **parece** funcionar e não
funciona, com sintoma e causa. Ler antes de mexer em transcrição, AEC ou
benchmark; várias entradas já custaram tempo uma vez.

## Ritual

Segue o ritual da raiz `C:\Dev` (plano em `roadmap/`, docs atualizadas,
consolidado datado em `docs/CONSOLIDADO-<data>.md` ao fim). A regra de compilar
acima é específica deste projeto e **não** é opcional.
