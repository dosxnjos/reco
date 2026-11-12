# Reco em Rust: Fase 2 — Motor Python como servidor

> Índice: [2026-11-11-melhoria-reco-em-rust.md](2026-11-11-melhoria-reco-em-rust.md) · anterior: [fase-1](2026-11-11-melhoria-reco-em-rust-fase-1.md) · seguinte: [fase-3](2026-11-11-melhoria-reco-em-rust-fase-3.md) · Base: Reco `7c5c1a1` (2026-11-11)

## Por que esta fase

- O casco Tauri da Fase 3 precisa de um motor que grave, transcreva e cuide da biblioteca sem janela Tk (D1).
- O motor é o `reco.py` de hoje, importado sem mudar uma linha, embrulhado num servidor JSON Lines no molde do Lacre.
- Ele vira o dono do config e dos contratos (D6): o casco Rust nunca grava `~/.reco_config.json`.
- O app velho continua sendo o que o Gabriel usa; nada aqui mexe no `reco.py`, no `tray.py`, no `tools/transcrever.py` nem no `dist/Reco`.
- A fase fecha com o protocolo escrito, um teste headless versionado e o motor congelado medido (tempo até `hello`, tamanho sem pyarrow/duckdb).
- Depende só da Fase 0 e anda em paralelo com a Fase 1 (índice); a Fase 3 começa pelo protocolo daqui.

## O que ler antes

- `C:\Dev\cerebro\projetos\reco.md` (hub; o hook `guarda-escrita` cobra) e `C:\Dev\Reco\CLAUDE.md`.
- `C:\Dev\Reco\docs\ARMADILHAS.md` inteira (gerada), com atenção a "Migração de config persistida antes do exe novo" (linha ~773).
- O índice inteiro: `C:\Dev\Reco\roadmap\2026-11-11-melhoria-reco-em-rust.md` (D1–D12 e "O que NÃO fazer" valem aqui; a D11, contrato de falha, começa nesta fase).
- `C:\Dev\Reco\roadmap\2026-11-11-melhoria-reco-em-rust.d\diagnostico\1-mapa-do-reco-atual.md` (§1, §2, §5, §6).
- `C:\Dev\Reco\roadmap\2026-11-11-melhoria-reco-em-rust.d\diagnostico\2-restricoes-do-porte.md` (§A, §B, §5).
- `C:\Dev\Reco\roadmap\2026-11-11-melhoria-reco-em-rust.d\diagnostico\3-lacre-como-molde.md` (§1, §3, §4).
- `C:\Dev\Reco\roadmap\2026-11-11-melhoria-reco-em-rust.d\diagnostico\6-critica-de-completude.md` (§1.4, §2, §4.6).
- Molde: `C:\Dev\lacre\engine\lacre_engine\server.py` (inteiro, 350 linhas), `C:\Dev\lacre\engine\build.py`, `C:\Dev\lacre\docs\PROTOCOL.md`.
- Casco que vai consumir o protocolo: `C:\Dev\lacre\src-tauri\src\engine.rs:60-131` (Router) e `:525-541` (timeouts).
- `C:\Dev\Reco\reco.py` nos trechos citados em cada passo, e `C:\Dev\Reco\tools\transcrever.py:87-96` (as duas convenções de `.txt`).
- Conferir o frescor: `git -C C:/Dev/Reco log --oneline 7c5c1a1..HEAD -- reco.py tray.py tools/transcrever.py`; se mudou, reler as linhas citadas.
- Ao começar, anotar no relatório o SHA do HEAD (`git rev-parse --short HEAD`): ele é o `<SHA-INICIO>` das provas do passo 16 e do gatilho.

## Fase 2 — Motor Python como servidor

**Critério de aceite:**

- Uma gravação curta feita pelo motor, sem abrir a janela do Reco, aparece na biblioteca do app velho, toca com a duração certa e tem voz no canal esquerdo e som do PC no direito.
  Se a fase falhar: o arquivo não aparece, dura 0 s ou mente a duração, ou toca mudo num dos lados.
- Se o programa que comanda o motor cair no meio de uma gravação (como se o app novo travasse), o motor termina o arquivo sozinho: o áudio gravado até ali continua no disco, toca inteiro e o player mostra a duração certa.
  Se a fase falhar: o arquivo some, fica com 0 s, mostra duração errada ou não abre no player.
- Depois de todos os testes, o app velho abre com as mesmas preferências de antes (pasta, dispositivo, ganho, idioma, tema).
  Se a fase falhar: o app velho abre com outro dispositivo, outro ganho ou outro idioma.

Convenções dos passos:

- Comandos rodam no Git Bash a partir de `C:/Dev/Reco`, com o Python global (`/c/Python314/python`, o mesmo do `build.ps1`).
- Cada passo verde vira um commit por pathspec (`git add <arquivos do passo>`; nunca `-A`, nunca `--no-verify`).
- Todo arquivo novo de código fica com até 500 linhas e funções dentro da trava de complexidade (`tools/tamanho.json`: C901 ≤ 10, ramos ≤ 12, instruções ≤ 50).
- O teste cresce a cada passo: `tools/test_engine_protocol.py` fica só com as flags e o despacho.
  As checagens de cada área vão em módulos ao lado (ex.: `tools/engine_checks_rec.py`), cada um até 500 linhas.
- Prova da trava em qualquer passo: `git add <arquivos do passo> && pre-commit run --files <arquivos do passo>` → nenhuma linha `Failed`.
  `Skipped` vale (hook sem arquivo que case). A trava-tamanho e a trava-complexidade leem o que está no índice do git: sem o `git add`, passam em falso.
- `reco.py`, `tray.py` e `tools/transcrever.py` não mudam. O `build.ps1` do app velho não roda nesta fase: nada que entra no `Reco.exe` muda.
- O motor reimplementa a orquestração que hoje mora em métodos do `App` (não importáveis); cada passo diz qual método e quais linhas espelha.

1. [x] Criar o esqueleto `engine/reco_engine/` (`__init__.py`, `errors.py`, `__main__.py`) — **prova:** `(cd engine && python -c "import reco_engine, reco_engine.errors as e; print(reco_engine.__version__, sorted(e.CODES)[:3])")` → `0.1.0 ['bad_args', 'busy', 'cancelled']`
   **reprova se:** `ModuleNotFoundError: reco_engine` ou versão diferente de `0.1.0`.
   - `__init__.py` com `__version__ = "0.1.0"`; `errors.py` com a classe `EngineError(code, detail)` e o conjunto `CODES`.
   - `__main__.py`: fora do PyInstaller (`not getattr(sys, "frozen", False)`), põe a raiz do repo (pai de `engine/`) no `sys.path` antes de importar `reco`.
   - Despacho do `argv`: `--transcribe` e `--selftest` vão para `cli.py` (passo 12); o resto chama `server.main()`.
   - Códigos de erro: `bad_args`, `busy`, `cancelled`, `claude_missing`, `internal`, `no_audio`, `no_audio_stream`, `no_device`, `not_found`, `refused`, `save_failed`, `unavailable`.
2. [x] Escrever `engine/reco_engine/server.py` (laço do protocolo) e criar `tools/test_engine_protocol.py` já com as checagens de protocolo — **prova:** `python tools/test_engine_protocol.py` → `OK protocolo: hello, linha inválida, cmd desconhecido, id não-string, shutdown (exit 0)`
   **reprova se:** o teste trava esperando linha, recebe texto que não é JSON no stdout, ou o processo não sai em até 10 s após `shutdown`.
   - Protocolo do Lacre (`lacre/docs/PROTOCOL.md:14-40`): pedido `{"v":1,"id","cmd","args"}`, resposta `{"v":1,"id","ok","data"|"error":{code,detail}}`.
   - Evento: `{"v":1,"event":...}`; leva `"id"` só quando nasce de um pedido (progresso); os globais (`level`, `state`, `timer`, `live.text`, `ready`) vão sem `id`.
   - O Router do casco aceita evento sem `id`, porque testa `event` antes de `id` (`lacre/src-tauri/src/engine.rs:99-101`).
   - O `id` tem de ser string, porque o Router lê `as_str` (`engine.rs:102`); `id` numérico responde `internal`. Linha ilegível responde `"id": null` com `internal` (como `server.py:73-75` do Lacre).
   - Registro explícito `COMMANDS = {"hello": fn, "config.get": fn, ...}`: nome com ponto não serve para `getattr(self, "cmd_" + cmd)`.
   - `id` repetido em andamento responde `internal` (Lacre `server.py:86-89`). Só dá para provar com um pedido lento: a checagem entra no passo 8 (dois `transcribe.file` com o mesmo `id`).
   - Modelo de concorrência (F2-D1): uma thread lê o stdin; cada pedido roda numa thread própria; a escrita no stdout passa por um `threading.Lock`.
   - Isolamento do stdout em nível de descritor (F2-D7): no `main()`, `fd = os.dup(1)` vira o canal do protocolo; depois `os.dup2(2, 1)` e `sys.stdout = sys.stderr`.
     O `dup2` existe porque `sys.stdout = sys.stderr` (Lacre `server.py:324`) não pega escrita nativa (OpenVINO, ffmpeg) no fd 1.
     O mesmo vale para os `print` do `reco.py` (ex.: `reco.py:1349`, `:1738`).
   - `hello` responde antes de `import reco` (F2-D3): `{engine_version, reco_version:null, protocol:1, platform, ready:false, uptime_s}`.
   - `shutdown` e EOF no stdin encerram; saída final com `os._exit` (como Lacre `server.py:343-350` e `reco.py:5124-5128`: threads nativas seguram o processo).
   - O teste sobe `[sys.executable, "-m", "reco_engine"]` com `cwd=engine/`, `creationflags=0x08000000` (CREATE_NO_WINDOW, como o casco) e as variáveis `PYTHONUNBUFFERED=1`, `PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1` (`engine.rs:182-200`).
   - O teste aceita `--exe <caminho>` para rodar contra o motor congelado (passo 15) e sempre drena o stderr numa thread (senão o pipe enche e trava, Lacre `engine.rs:315`).
3. [x] Criar `engine/reco_engine/boot.py` (import de `reco` em segundo plano, evento `ready`, aquecimento) — **prova:** `python tools/test_engine_protocol.py` → linha extra `OK ready: import_s=<n> has={sc:True,np:True,av:True,ov:True} lang=pt` e `hello` em menos de 1 s
   **reprova se:** `hello` leva o tempo do `import reco` (≈2,2 s medidos do fonte em 11/11), ou `ready` não chega em 60 s.
   - `boot.reco()` devolve o módulo esperando o `threading.Event` do import (teto de 60 s, senão `unavailable`); todo comando que usa `reco` passa por ele.
   - Medido nesta arquitetura (11/11): `import reco` não cria janela (`tkinter._default_root` fica `None`) e não carrega `openvino` nem `scipy`; só `soundcard` e `PIL` entram.
   - **A thread que faz o `import reco` não pode terminar** enquanto o motor vive (medido na auditoria, 11/11).
     O `soundcard` liga o COM do Windows na thread que o importa. Se ela acaba, toda enumeração em outra thread falha.
     O erro é `Error 0x800401f0` e vem com listas vazias, não com exceção. Com a thread viva, a mesma chamada lista os dispositivos.
     Molde: a thread do import termina o import, sinaliza o `Event` e fica parada num `threading.Event().wait()` (daemon).
     Registrar como pegadinha no passo 16 (`python tools/visoes.py novo`).
   - Evento `ready`: `{import_s, has:{sc,np,av,ov} (reco.py:522-570), lang (reco.LANG), reco_version (reco.APP_VERSION)}`. O `hello` seguinte passa a dizer `ready:true`.
   - Aquecimento depois do `ready`, numa thread daemon (molde `_warm_imports`, Lacre `server.py:222-228`): `scipy.signal`, `av`, `openvino`, `openvino_genai`.
   - **Não** cria o `WhisperPipeline` (F2-D4): custa 14,6 s e 1,35 GB por processo (ARMADILHAS, citado em 2-restricoes §A) e ficaria preso num app que mora na bandeja.
   - Logar no stderr `aquecimento pronto em <n> s`; o executor anota o número no relatório da fase.
4. [x] Criar `engine/reco_engine/config_cmd.py` com `config.get` e `config.set`, e estender o teste com o roundtrip isolado — **prova:** `python tools/test_engine_protocol.py` → `OK config: get, set mic_gain=2.5, chave legada preservada, migração não persistida, config real intocado (sha256 igual)`
   **reprova se:** o sha256 do `~/.reco_config.json` real muda, a chave legada some do arquivo temporário, ou `set` responde `ok` sem o valor estar no disco.
   - Isolamento: o teste põe `USERPROFILE=<pasta temporária>` no ambiente do filho. Provado nesta arquitetura: `reco.CONFIG_PATH` (`reco.py:102`) e `default_output_dir()` (`reco.py:98-99`) passam a apontar para lá.
   - O `_user_data_dir()` continua no `LOCALAPPDATA` real (`reco.py:578-582`): o modelo é achado normalmente, e isso é desejado.
   - O teste semeia o config temporário com `_migracao: 2` e as chaves legadas que o config real tem (`channels`, `mp3_bitrate`, `sample_rate`).
   - Também grava `casco_teste: true` (aceito), tenta `chave_inventada: 1` (espera `bad_args`) e confere que nada mais mudou no arquivo.
   - Segundo caso, que pega o merge feito sobre `load_config()`: config semeado com `_migracao: 1` e sem a chave `live`.
     Depois do `set mic_gain`, o arquivo tem de continuar com `_migracao: 1` e sem `live`.
   - Antes de subir o filho, o teste guarda os bytes do config real e confere no fim (o mesmo padrão de `tools/test_dispositivo_auto.py:25-26`).
   - `config.get`: `reco.load_config()` com `persist=False` (`reco.py:210-231`), mais os derivados `output_dir_efetivo` e `lang_efetivo`.
   - O motor nunca chama `load_config(persist=True)` (F2-D6; ARMADILHAS § migração; `reco.py:212-216`).
   - `config.set {changes}`: relê o arquivo **cru** (`json.loads` de `reco.CONFIG_PATH`, não `load_config()`), faz merge e aceita só chaves de `_CFG_DEFAULTS` (`reco.py:103-129`) ou com o prefixo `casco_`, senão `bad_args`.
     Cru porque o `load_config()` devolve defaults e migração em memória: gravar isso seria persistir a migração, o que a F2-D6 proíbe. Merge nunca substitui: chave desconhecida do arquivo fica.
   - O prefixo `casco_` (F2-D16) guarda preferência do casco que o `reco.py` não conhece (`casco_atalho` e `casco_tema`, F3-D5 da Fase 3).
     O `load_config` preserva chave desconhecida (`cfg.update`, `reco.py:216-219`), e o app velho as ignora.
   - Depois grava com `reco.save_config` e relê para conferir, porque `save_config` engole toda exceção (`reco.py:234-244`); divergência vira `save_failed`.
   - Efeitos colaterais que o `App` aplica:
     - `language` muda `reco.LANG`, como `_set_language` (`reco.py:3502-3509`), e é recusada com `busy` durante gravação ou transcrição. O `LANG` decide `_spk_me` (`reco.py:1325-1329`) e o prefixo do arquivo (`reco.py:1695`).
     - `mic_gain` e `sys_gain` vão ao gravador ativo por `set_gain` (`reco.py:1605-1609`), como `_on_gain` (`reco.py:3206-3212`), com `round(g, 4)` como `_on_gain_release` (`reco.py:3214-3216`).
   - `config.set` com `mic_device`/`sys_device` só grava; a resolução acontece no `rec.start` (o config é a única fonte, `reco.py:1377-1380`).
5. [x] Criar `engine/reco_engine/devices.py` com `devices.list` e `devices.refresh` (Auto incluído) e estender o teste — **prova:** `python tools/test_engine_protocol.py` → `OK dispositivos: <n> mics, <m> saídas, console mic=<nome>, console saída=<nome>`
   **reprova se:** listas vazias numa máquina com mic e saída, `console` nulo com dispositivo padrão no Windows, ou nome com `?` no lugar de acento (encoding).
   - Fonte: `reco.scan_device_state()` (`reco.py:1440-1448`), que já roda fora da thread da interface no app (`_scan_thread`, `reco.py:3702-3709`); no motor, roda na thread do pedido.
     Só funciona com a thread do import viva (passo 3): é este passo que reprova se ela morrer (listas vazias).
   - Formato: `{microphone:{devs:[{id,name}],console,comm}, speaker:{...}, selected:{mic_device, sys_device}, missing:{mic:bool, sys:bool}}`.
   - `missing` usa a mesma regra de `device_options` (`reco.py:1451-1468`): id salvo fora da lista = ausente. O motor não monta rótulos traduzidos: quem rotula é a interface.
   - `devices.refresh` é sinônimo de `devices.list` (F2-D11): a enumeração do `soundcard` já é fresca a cada chamada (`reco.py:1408-1414`).
6. [x] Criar `engine/reco_engine/recording.py` (`rec.*`, `state`, eventos de nível, estado, tempo e erro) — **prova:** `python tools/test_engine_protocol.py --gravar 5` → `OK gravação: 5,0±0,5 s, 2 canais, 16000 Hz, level <=20/s, timer 1/s, L e R com sinal`
   **reprova se:** arquivo ausente, duração fora da faixa, 1 canal, mais de 20 eventos `level` por segundo, ou um canal com RMS zero tendo som.
   - Grava dos dispositivos reais, então todo modo que grava (`--gravar`, `--eof`, `--concluir`) começa por duas guardas:
     - aborta com mensagem clara se o mutex `Local\Reco.SingleInstance` existe (app velho aberto; D7, protege uma reunião em curso).
       Checagem: `ctypes.windll.kernel32.OpenMutexW(0x00100000, False, "Local\\Reco.SingleInstance")` diferente de 0.
     - toca `temp/bench-voz/clip10.wav` (fala, local, fora do git) no alto-falante padrão pelo `soundcard` durante a gravação (em laço; o clipe tem 10 s).
       Assim o canal R tem fala sem ninguém por perto; o L tem pelo menos o ruído do mic (RMS > 0). Sem o clipe, o teste para e diz onde ele falta.
   - A gravação vai para a pasta temporária do teste (`USERPROFILE` temporário → `Documents/Reco`).
   - Flag `--saida-real` (usada no passo 15): o teste lê o `output_dir` do config real (ou `Documents\Reco` do usuário) e o semeia no config temporário.
     A gravação cai na pasta que a biblioteca do app velho lista, e o config real continua sem escrita.
   - O teste confere com `av` a duração do container, os canais e a taxa, e o RMS por canal.
   - `rec.start {mode:"rec"|"nota"}` espelha `_start_rec` (`reco.py:3746-3811`) e `_start_nota` (`reco.py:3813-3858`).
     Recusa com `busy` se o estado não for `idle`; `nota` também se houver transcrição (`reco.py:3820`).
   - Resolução dos dispositivos como `_resolve_devices` (`reco.py:3860-3875`), síncrona: `reco.resolve_audio_device(cfg[...], "microphone"|"speaker")`; os dois nulos dão `no_device`.
   - Pasta de saída como `App.__init__`: `cfg["output_dir"]` ou `default_output_dir()` (`reco.py:2869-2870`). Gravador: um `reco.DualRecorder()` (`reco.py:1550`).
   - Formato do `rec` como `_out_settings` (`reco.py:3738-3741`): `reco.OUT_SR, reco.OUT_CH, reco.MP3_BR`, passados ao `start` como `out_sr`, `out_channels`, `bitrate`, `out_dir` (`reco.py:3789-3797`).
   - O ganho do config vai ao gravador antes do `start` (`reco.py:2876-2878`). `nota` usa `out_channels=1`, prefixo `nota`/`note` e nunca liga o ao vivo (`reco.py:3836-3856`).
   - Resposta: `{mic:{id,name,via}, sys:{id,name,via}, live:bool, live_suprimido:bool}`. O aviso de "ausente" sai de `via == "ausente"` (`reco.py:3887-3901`).
   - Se o `start` não abriu o arquivo (`recording` falso, `reco.py:3799`), responde `save_failed`.
   - `level` (F2-D13): o `on_level` dispara a cada bloco de 1024 amostras a 48 kHz (≈47 Hz por canal), dentro das threads de captura (`reco.py:1803-1805`, `:1827-1829`).
     O callback só guarda o maior RMS da janela por canal (o valor já sai multiplicado pelo ganho).
     Uma thread do motor emite a cada 50 ms um evento `{"event":"level","mic":x|null,"sys":y|null}`, e só em `recording`.
   - Comandos: `rec.start`, `rec.pause`, `rec.resume`, `rec.stop`, `rec.set_gain` e `state`.
   - `rec.set_gain {mic?, sys?}` muda o ganho ao vivo sem gravar config, como `_on_gain` durante o arrasto (`reco.py:3206-3212`).
     A interface manda `config.set` só ao soltar, como `_on_gain_release` (`reco.py:3214-3216`); assim o arquivo não é regravado a 20 Hz.
   - `state` devolve o retrato inteiro para a interface se ressincronizar depois de reiniciar: `{ready, rec_state, elapsed_s, transcribing, live, last_rec}`.
   - `pause`/`resume` espelham `_pause_rec`/`_resume_rec` (`reco.py:4150-4172`): o tempo pausado não conta, como `_elapsed` (`reco.py:4113-4117`).
   - `timer`: `{"event":"timer","elapsed_s":n}` uma vez por segundo enquanto grava. `state`: `{"event":"state","state":"idle|recording|paused|stopping|stopped","elapsed_s":n}` a cada troca.
   - `rec.error` espelha `_on_stream_error` (`reco.py:3903-3919`): `{"event":"rec.error","channel":"mic|sys|save","detail":...,"fatal":bool}`.
     Com `save` ou `all_failed()` (`reco.py:1700-1701`), aborta como `_abort_to_idle` (`reco.py:3921-3931`) e vai a `idle`.
   - `rec.stop` espelha `_stop_rec` (`reco.py:3933-3963`): `recorder.stop()`; `NoAudioCaptured` vira `no_audio`.
   - Com ao vivo, `live.stop(wait=True, timeout=15.0, discard=True)` depois do `stop` e antes de responder (drenar e só então começar, `reco.py:3944-3951`).
   - Resposta: `{path, duration_s, auto:null|"final_pass"|"nota"}`; estado `stopped`; o motor guarda o `last_rec`.
     `auto` segue `_after_stop` (`reco.py:3973-3996`): `"nota"` se o modo era nota, `"final_pass"` se o ao vivo ligou no `start`, senão `null`.
7. [x] Gravação nunca se perde quando o casco some (D11): `shutdown` ou EOF no stdin durante gravação fecha o MP3 antes do `os._exit` — **prova:** `python tools/test_engine_protocol.py --eof 25` → `OK eof: duração declarada 25±1 s, decodificada igual (±1 s); OK shutdown no meio: idem`
   **reprova se:** o MP3 não existe, a duração declarada no header difere da decodificada em mais de 1 s (o `close()` não escreveu o header), a decodificada sai de 25±1 s, ou o processo não sai em 8 s.
   - Mesmas guardas do passo 6 (mutex e clipe). São 25 s, e não menos, para passar dos ≈10 s em que o `_pump` retém o áudio antes de alinhar (`ALIGN_COLETA_S`, `reco.py:1491`).
     Com menos tempo o teste nunca pega um arquivo que já está crescendo.
   - Declarada × decodificada é a régua de `declared_and_real` em `tools/reparar_duracao.py`: sem o `close()`, o header fica sem a contagem e o player estima pelo bitrate.
     Só conferir "25±1 s" pela duração do container não basta, porque a estimativa pode cair perto por acaso.
   - Espelha `_quit` (`reco.py:5088-5113`): gravando, chama `recorder.stop()` numa thread e só então sai.
     O ao vivo para com `wait=False`, porque o casco mata o motor 8 s depois do `shutdown` (Lacre `src-tauri/src/lib.rs:82`; o laço de espera é `engine.rs:492-522`).
   - O teste grava 25 s, fecha o stdin do filho sem mandar `shutdown` e confere o arquivo; um segundo caso manda `shutdown` no meio da gravação.
   - Transcrição em andamento no `shutdown` é cancelada (`transcriber.cancel()`, `reco.py:2051-2052`); o `.txt` não nasce, e é o mesmo comportamento do app velho ao sair.
8. [x] Criar `engine/reco_engine/transcribe.py` (`transcribe.file` e `transcribe.cancel`) — **prova:** `python tools/test_engine_protocol.py --transcrever <mp3 do Reco>` → `OK transcrição: .txt igual ao do app, <n> progressos, pct crescente; cancel → cancelled; id repetido → internal`
   **reprova se:** o `.txt` difere do gerado pelo app velho no mesmo arquivo, nenhum evento traz `pct`, ou `transcribe.cancel` não faz o pedido responder `cancelled`.
   - O teste trabalha em cópias do MP3 numa pasta temporária. A referência é o `.txt` que `python reco.py --transcribe <cópia> --diarize` gera numa segunda cópia (`reco.py:5148-5179`; mesma pipeline do app para gravação do Reco).
   - A referência roda com o mesmo `USERPROFILE` temporário do motor: modelo, device, `aec` e idioma saem do mesmo config, e a comparação não falha por config.
   - O MP3 tem de ter fala: com texto vazio a CLI grava `""` e o app grava o literal `"(no content recognized)"`, e os dois diferem por desenho.
   - Antes de comparar motor × app, a referência roda duas vezes. Se as duas já diferirem (GPU não determinística), a régua vira "motor × app não difere mais que referência × referência", anotada no relatório.
   - Na mesma rodada: um segundo `transcribe.file` com o `id` do primeiro, ainda em andamento, responde `internal`; depois um `transcribe.cancel` faz o primeiro responder `cancelled`.
   - Um só `reco.make_transcriber()` (`reco.py:2729-2735`) por processo, compartilhado com o ao vivo e as passadas finais, como o `App` (`reco.py:2879-2882`, `:3776`).
   - Espelha `_run_transcriber` (`reco.py:4196-4227`): recusa com `busy` se já há transcrição, porque é um `pipe.generate` por vez.
     Aplica `set_model`/`set_device` do config a cada pedido; `diarize` = `cfg["diarize"]` e `aec` = `cfg["aec"]`, ambos só se `is_reco_recording(path)` (`reco.py:136-138`, `:4214-4216`).
     `lang` é `"pt" if reco.LANG == "pt" else "en"`, como `_whisper_lang` (`reco.py:3743-3744`).
   - Grava o `.txt` como `_autosave_txt` (`reco.py:4181-4188`): `path.with_suffix(".txt")` com o literal `"(no content recognized)"` quando vazio. Resposta `{txt}`.
   - Progresso (F2-D5): o `OVTranscriber` calcula a fração por grupo de VAD ponderado pela duração e entrega só texto traduzido, `tf("Transcrevendo… {p}%")`, com teto 99 (`reco.py:2211`, `:2225`, `:2296`, `:2328`; EN em `reco.py:414`).
     O motor extrai o número com `(\d+)%` só no texto de `tf("Transcrevendo… {p}%")` (comparar com o prefixo traduzido) e emite `{"id","event":"progress","pct":n|null,"text":...}`. As outras mensagens (modelo, "Carregando áudio…", `reco.py:2061-2078`, `:2341`) vão com `pct:null`.
   - Cancelamento: `transcribe.cancel {}` chama `transcriber.cancel()`; o pedido em curso recebe `CANCELLED` (`reco.py:1292`) e responde `cancelled`.
     O corte acontece na fronteira do próximo grupo de VAD (`reco.py:2286-2287`), não no meio de um `generate`.
   - O teste fica de fora da rodada padrão (precisa da GPU e de minutos); entra com a flag.
9. [x] Criar `engine/reco_engine/conclude.py` (`rec.conclude`, passadas finais, ao vivo) — **prova:** `python tools/test_engine_protocol.py --gravar 5 --concluir` → `OK conclusões: save, delete (Lixeira), transcribe, transcribe_delete, nota, final_pass, 2 cancelados com mp3`
   **reprova se:** o arquivo de `delete` não está na Lixeira, `transcribe_delete` ou `nota` cancelados removem o áudio, nenhum `live.text` chega, ou o estado não volta a `idle`.
   - Mesmas guardas do passo 6 (mutex e clipe tocando durante cada gravação).
   - Pedido: `rec.conclude {action:"save"|"delete"|"transcribe"|"transcribe_delete"|"final_pass"|"nota"}` sobre o `last_rec`; sem `last_rec` no disco responde `not_found`.
   - O teste grava oito vezes e conclui cada uma de um jeito. Para `final_pass`, liga `live: true` no config temporário antes do `rec.start`; para `nota`, usa `mode:"nota"`.
   - O caso `final_pass` grava **30 s**, não 5, e roda depois de um caso `transcribe` (pipeline já quente).
     O ao vivo só recebe áudio depois que o `_pump` alinha (≈10 s, `reco.py:1975-1977` antes do `on_pair` em `:2006-2010`).
     O que chega no fim é descartado pelo `live.stop(discard=True)`: com 5 s, nenhum `live.text` nasceria mesmo com o motor certo.
   - Os dois casos de falha: um `transcribe_delete` e uma `nota` recebem `transcribe.cancel` logo depois do primeiro evento `progress`.
     Os dois respondem `cancelled` e o mp3 tem de continuar no disco (`reco.py:4237-4242`; erro preserva o mp3 em `reco.py:4033-4038`).
   - "Na Lixeira" se confere por comando, não a olho: `powershell -NoProfile -Command "(New-Object -ComObject Shell.Application).NameSpace(10).Items() | ForEach-Object Name"`.
     O nome do arquivo de `delete` tem de aparecer na lista (comparar sem a extensão: o Explorer pode escondê-la).
   - `save`: vai a `idle` e responde `{path}`. O casco copia `"<path>"` entre aspas duplas (`_conclude_save_and_copy`, `reco.py:4086-4092`); o clipboard é do casco.
   - `delete`: `reco._excluir_gravacao` (Lixeira, `reco.py:599-631`), como `_conclude_delete` (`reco.py:4098-4106`).
   - `transcribe` e `transcribe_delete` espelham `_transcribe_recording` (`reco.py:4229-4262`). O estado vai a `idle` na hora (`reco.py:4094-4096`) e o pedido segue longo com progresso; responde `{txt, deleted}`.
     O áudio só sai depois do `.txt` salvo.
   - `final_pass` (ao vivo ligado) espelha `_run_live_final_pass` (`reco.py:4005-4026`) e responde `{txt, text}`.
   - `nota` espelha `_run_nota_final_pass` (`reco.py:4028-4064`): sucesso grava `.md` em `nota_dir` ou na pasta de saída, com o literal se vazio, e manda o mp3 à Lixeira; responde `{md}`.
     Erro preserva o mp3. O casco copia o caminho.
   - O casco chama `final_pass`/`nota` logo depois do `rec.stop` quando `auto` vier preenchido (F2-D12); se não chamar, nada se perde: o mp3 fica.
   - Ao vivo no `rec.start`: liga se `cfg["live"]` e não há transcrição (`reco.py:3766-3772`).
     `reco.LiveTranscriber(transcriber, lang)` com `start(on_text, on_warn)` e `on_pair=live.feed_pair` (`reco.py:2442-2471`, `:3776-3783`).
   - `live.text`: `{"event":"live.text","channel":"mic|sys","speaker":<rótulo>,"text":...}`. O `on_text` entrega o rótulo traduzido (`reco.py:2614-2615`); o canal sai da comparação com `reco._spk_me()`.
   - O `on_warn` vira `{"event":"live.warn","text":...}`. A prova do ao vivo de verdade (GPU, 20 min) não é desta fase: fica para a Fase 5, como diz o índice.
   - O `final_pass` e o `live.text` precisam da GPU livre: rodar com o app velho fechado e sem outra transcrição.
10. [x] Criar `engine/reco_engine/library.py` (`library.list/search/delete`) com fixtures no teste — **prova:** `python tools/test_engine_protocol.py` → `OK biblioteca: 3 itens, duração 1 s, x.txt e x.mp3.txt achados, busca por conteúdo nas duas convenções, delete fora da pasta recusado`
   **reprova se:** o item com `x.mp3.txt` aparece sem transcrição, a busca por palavra que só existe no `.mp3.txt` não acha, ou `library.delete` aceita caminho fora da pasta.
    - O teste cria na pasta temporária três MP3 de 1 s com `reco.MP3Writer` (`reco.py:749-830`; `feed` e `close`), um `x.txt` e um `y.mp3.txt` com palavras distintas.
    - `list` espelha `_lib_scan_thread` (`reco.py:4492-4512`): `AUDIO_EXTS`, ordem por `mtime` decrescente, duração do container com cache por `(path, mtime)` (`reco.py:4514-4529`).
    - Correção sobre o app: o app só olha `with_suffix(".txt")` (`reco.py:4510`) e deixa 14 de 47 transcrições invisíveis (2-restricoes §B).
      O motor procura `x.txt` e, se faltar, `x.mp3.txt` (`name + ".txt"`, a regra de `tools/transcrever.py:87-96`).
    - Cada item: `{name, path, mtime, bytes, duration_s|null, txt|null, resumo|null}`; `resumo` é `with_suffix(".resumo.md")` (`reco.py:4668`).
    - `search {q}`: nome ou conteúdo do `.txt` (as duas convenções), em `casefold`, como `_lib_refilter` (`reco.py:4557-4578`; o texto vem de `_lib_txt_content`, `:4545`), com cache de texto por `(path, mtime)`.
    - `delete {path}` (F2-D15): só aceita arquivo de `AUDIO_EXTS` dentro da pasta da biblioteca, senão `refused`. Manda só o áudio à Lixeira; o `.txt` e o `.resumo.md` ficam (`reco.py:4638-4660`).
    - A exclusão real só roda no teste com `--lixeira`, para não encher a Lixeira a cada rodada.
11. [x] Criar `engine/reco_engine/extras.py` (conversão, resumo IA, checagens de atualização) — **prova:** `python tools/test_engine_protocol.py` → `OK extras: convert 16 kHz mono, sem trilha = no_audio_stream, app.update_check, claude_missing, claude falso recebeu --model sonnet`
   **reprova se:** o MP3 convertido não é 16 kHz mono, o vídeo sem som derruba o motor em vez de responder `no_audio_stream`, ou o argv gravado pelo `claude` falso não tem `--model sonnet`.
    - Comandos: `convert.extract_mp3`, `resumo.ia`, `model.update_check`, `app.update_check`.
    - `convert.extract_mp3 {path}` espelha `_cv_convert` (`reco.py:4783-4824`) sobre `reco.extract_mp3` (`reco.py:836-882`): progresso inteiro, `NoAudioStream` vira `no_audio_stream`, resposta `{path, src_bytes, dst_bytes}`.
    - O teste gera a entrada com `av` (1 s de tom num `.wav`) e um `.mp4` só com vídeo para o caso sem trilha.
    - `resumo.ia {path}` espelha `_lib_resumo` (`reco.py:4663-4711`): se o `.resumo.md` existe, responde `{path, existia:true}` (o casco abre).
      Sem `claude` no PATH responde `claude_missing`; um resumo por vez (`busy`). Roda `[claude, "-p", PROMPT_RESUMO[lang], "--model", "sonnet"]` com o texto no stdin e timeout de 900 s.
      A flag `--model sonnet` é cravada (`reco.py:4690-4697`); o `.txt` usa a mesma regra das duas convenções do passo 10.
      Sem `.txt` em nenhuma das duas convenções responde `not_found` (o app só não faz nada, `reco.py:4666-4667`).
    - O teste prova `claude_missing` com `PATH` sem o `claude`.
    - Em seguida põe na frente do `PATH` uma pasta temporária com um `claude.cmd` falso, que chama um script Python do teste.
      O script grava o próprio argv num `.json` e imprime `## Resumo` no stdout. O teste confere o argv e o `.resumo.md` escrito, sem gastar o plano do Gabriel.
    - A geração real com o `claude` de verdade é opcional e manual: uma vez, num `.txt` curto, anotada no relatório.
    - `model.update_check` chama `reco.update_model_if_newer(status_cb)` (`reco.py:1230-1266`), com o status como evento `{"id","event":"progress","pct":null,"text"}`.
      Recusa com `busy` durante transcrição, porque troca a pasta do modelo no lugar.
    - `app.update_check` responde `reco.check_app_update()` como `{tag, url}` ou `null` (`reco.py:1274-1289`). O casco abre a URL.
12. [x] Manter `--transcribe` e `--selftest` no motor (`engine/reco_engine/cli.py`, iguais a `reco.py:5148-5179` e `:5132-5146`) — **prova:** `python tools/test_engine_protocol.py --cli <mp3 curto do Reco, com fala>` → `OK cli: exit 0, stdout vazio, log OK, .txt igual; OK selftest igual`
   **reprova se:** o motor sai com código diferente de 0, escreve no stdout, o log não termina em `OK -> <caminho>`, o `.txt` difere do gerado pelo `reco.py`, ou o `reco_selftest.txt` do motor difere do gerado pelo `reco.py`.
    - A flag copia o MP3 duas vezes numa pasta temporária (`a_reco.mp3`, `b_reco.mp3`; nome com `reco`, para diarizar).
    - Roda `[sys.executable, "-m", "reco_engine", "--transcribe", a, "--diarize"]` com `cwd=engine/`, guarda o stdout e lê o log logo em seguida.
      O log é `%TEMP%\reco_transcribe_log.txt` (`tempfile.gettempdir()`), o mesmo dos dois: por isso se confere antes de rodar o velho.
    - Depois roda `[sys.executable, "reco.py", "--transcribe", b, "--diarize"]` na raiz e compara os bytes de `a_reco.txt` e `b_reco.txt`.
      O `.txt` é `with_suffix(".txt")`, não `a_reco.mp3.txt`. Se a GPU não for determinística, vale a régua do passo 8 (duas referências).
    - Mesmo comportamento do velho: log em `%TEMP%\reco_transcribe_log.txt`, `.txt` em `with_suffix(".txt")` com o texto ou vazio, exit 2 em erro, `aec` só com `--diarize`.
    - Não abre servidor, não cria mutex e sai pelo `sys.exit`.
    - `--selftest` (F2-D17) espelha `reco.py:5132-5146`: grava em `%TEMP%\reco_selftest.txt` as 5 linhas (`frozen= lang= HAS_*`, `backend=`, `ov_devices=`, `resolved(AUTO)=`, `transcription_available=`) e sai com 0.
      Usa `reco.ov_available_devices`, `reco.resolve_device` e os `HAS_*` do módulo; não carrega o `WhisperPipeline`.
    - A flag `--cli` também roda `--selftest` no motor e no `reco.py` (os dois do fonte) e compara os bytes do arquivo; o mesmo arquivo serve aos dois, então lê-se logo depois de cada um.
    - Rio abaixo (D6): `Reco.exe --transcribe` segue no `dist\Reco` velho enquanto ele existir. Na Fase 3 o casco se chama "Reco Novo" (F3-D3) e a Fase 4 o renomeia para "Reco".
      Quem repassa `--transcribe` ao motor é o casco, num passo da Fase 3; o PROTOCOL.md registra o repasse. O `--selftest` se chama direto no motor (`reco-engine.exe --selftest`).
13. [x] Escrever `docs/PROTOCOL.md` do Reco (próprio, não cópia do Lacre) com todos os comandos, eventos, códigos e timeouts sugeridos — **prova:** `python tools/test_engine_protocol.py --conferir-doc` → `OK doc: <n> comandos no registro, <n> na tabela do PROTOCOL.md, nenhum faltando`
   **reprova se:** algum comando do registro `COMMANDS` não aparece na tabela do doc, ou o doc cita comando que o motor não tem.
    - Conteúdo: regras invariáveis (stdout só protocolo, `"v":1`, `id` string, o motor é dono do config, o casco nunca grava `~/.reco_config.json`).
    - Tabela `cmd | args | data | eventos | timeout sugerido para o casco`, os eventos globais, os códigos de erro e a sequência `rec.stop` → `auto` → `rec.conclude`.
    - O que fica no casco Rust (F2-D9): clipboard (copiar caminho entre aspas), abrir arquivo, pasta e URL, mutex de instância única (D7), bandeja e diálogo de escolher arquivo.
    - Timeouts sugeridos (F2-D2), porque o Lacre usa 60 s como padrão (`engine.rs:526-540`):
      - `transcribe.file` e `rec.conclude` com transcrição: 12 h;
      - `convert.extract_mp3`: 2 h;
      - `resumo.ia`: 960 s;
      - `rec.stop`: 30 s, porque inclui drenar o ao vivo;
      - o resto: 60 s.
    - Seção das CLIs do motor (passo 12): `--transcribe <áudio> [--diarize]` e `--selftest`, os arquivos em `%TEMP%`, os códigos de saída (0 e 2) e a frase de que o casco repassa `--transcribe` ao motor.
    - Dívida declarada: o texto de progresso vem traduzido do `reco.py`; o motor emite códigos só no que ele mesmo cria.
    - `--conferir-doc` compara o registro `COMMANDS` (importado do pacote) com as linhas da tabela.
14. [x] Criar `engine/reco-engine.spec` (PyInstaller onedir) e `engine/build.py` (`build` e `--smoke`, no molde de `lacre/engine/build.py`) — **prova:** `python engine/build.py && ! ls engine/dist/reco-engine/_internal | grep -qiE 'pyarrow|duckdb' && echo LIMPO` → `built ... (<n> MB)` e `LIMPO`
   **reprova se:** o build falha, o tamanho passa de 700 MB, ou `LIMPO` não aparece (pyarrow ou duckdb entraram no bundle).
    - Spec: entrada `reco_engine/__main__.py`; `pathex` com a raiz do repo e `engine/`, para que `reco` e `tray` entrem.
    - Mesmo `collect_all` do `reco.spec` (soundcard, openvino, openvino_genai, openvino_tokenizers, av, huggingface_hub), mais `libs/cache.json` do openvino.
    - Os mesmos `hiddenimports` do `reco.spec`, inclusive `PIL.ImageTk` e `PIL._tkinter_finder`: o `import reco` puxa os dois (F2-D9).
    - **Não** copiar os `EXCLUDES` do Lacre (`build.py:24-25`): ele tira `tkinter`, `av` e `PIL`, e o `reco.py:17-18` importa `tkinter` sem guarda (F2-D9).
      O `av` é obrigatório; `PIL.ImageTk` (`reco.py:544`) pede `tkinter`.
    - Excludes: `pyarrow`, `duckdb` (os ~116 MB medidos no mapa §6), mais os do `reco.spec` (`faster_whisper`, `ctranslate2`, `tokenizers`, `onnxruntime`, `matplotlib`, `cv2`, `pandas`, `IPython`, `PyQt5`, `PyQt6`, `wx`).
    - Sem o modelo `small` bundlado (F2-D8); sem ícones nem `assets/`.
    - `console=True` (F2-D10): é o que o Lacre provou com o casco usando `CREATE_NO_WINDOW` (`build.py:39`); nenhuma janela aparece quando sobe pelo casco ou pelo teste.
    - O build sai em `engine/dist/` e `engine/build/` (já ignorados pelo `.gitignore`: `dist/` e `build/` sem barra inicial) e não briga com o `Reco.exe` aberto em `dist/Reco`.
15. [x] Medir o motor congelado (smoke e teste contra o exe) — **prova:** `python engine/build.py --smoke && python tools/test_engine_protocol.py --exe engine/dist/reco-engine/reco-engine.exe` → 3 linhas `run i: hello ok em <x> s; ready em <y> s; devices ok; exit=0` e os `OK` padrão
   **reprova se:** `hello` passa de 3 s em alguma rodada, `ready` não chega, aparece janela de console na tela, ou alguma checagem que passou do fonte falha no exe.
    - O `--smoke` espelha `lacre/engine/build.py:60-85`: sobe com `CREATE_NO_WINDOW` e mede `spawn → hello` e `spawn → ready`.
      Na última rodada espera o aquecimento e mede o `devices.list`; manda `shutdown` e confere o exit 0.
    - Anotar no relatório da fase: os três tempos, o tamanho da pasta e a memória do processo depois do aquecimento (Gerenciador de Tarefas ou `tasklist /fi "imagename eq reco-engine.exe"`).
    - Comparar com a medição da Fase 0 (tempo de abrir o app velho).
    - Rodar `engine/dist/reco-engine/reco-engine.exe --selftest`: exit 0 e `%TEMP%\reco_selftest.txt` com `frozen=True`. Anotar o tempo, comparável ao `exe_selftest` da Fase 0.
    - Fazer também uma gravação de 30 s pelo exe congelado (`--gravar 30 --saida-real --exe ...`), com as guardas do passo 6.
      O executor prova por dado: arquivo na pasta que a biblioteca lista, duração declarada = decodificada, RMS > 0 nos dois canais.
      Ouvir no app velho (Gravações…, tocar, conferir duração e os dois lados) é do Gabriel: ver "Pendente".
    - `+` Lados por dado, não por escuta (regra da casa de 11/11: teste real é da sessão): o envelope do canal R
      correlaciona com o do clipe tocado acima de 0,5 e o do L fica abaixo do R. Com isso a escuta vira opcional.
    - Depois que o Gabriel disser que ouviu, o executor manda a gravação de teste à Lixeira, para não ficar na biblioteca real:
      `python -c "import sys, reco; sys.exit(0 if reco._excluir_gravacao(sys.argv[1]) else 1)" "<caminho>"` na raiz (`reco.py:599-631`), conferido pelo comando da Lixeira do passo 9.
    - O app velho regrava o próprio config ao abrir (`load_config(persist=True)`, `reco.py:2868`); o teste já terminou e conferiu o sha256 antes disso.
16. [x] Fechar a fase — **prova:** `git diff --quiet <SHA-INICIO> -- reco.py tray.py tools/transcrever.py reco.spec build.ps1 && grep -lE 'engine/|engine_protocol|PROTOCOL\.md|reco-em-rust' docs/{ARQUITETURA,TOOLS,_INDICE}.md CLAUDE.md ../cerebro/projetos/reco.md | wc -l` → `5`
   **reprova se:** sai erro do git (SHA errado ou vazio), o diff dos arquivos do app velho não é vazio (nada é impresso), ou o número fica abaixo de 5 (falta a linha nova em algum doc ou no hub).
    - O que fecha: docs, hub e o app velho intacto.
    - Rodado com `HEAD` na auditoria de 11/11, antes das docs: imprimiu `0`; com SHA vazio, o git sai com erro 128 e nada é impresso.
    - `<SHA-INICIO>` é o SHA anotado ao começar a fase ("O que ler antes"), não o `7c5c1a1`: o `reco.py` pode ter mudado legitimamente antes da execução.
    - `docs/ARQUITETURA.md`: seção nova "Motor (`engine/`)" com o desenho (servidor, `boot`, transcritor único, quem é dono do config) e o build do motor (`engine/build.py`, onde sai, o que exclui).
    - `docs/TOOLS.md`: linha do `test_engine_protocol.py` com as flags e o que é manual. `docs/_INDICE.md`: linha do `PROTOCOL.md`.
    - `README.md` (as duas línguas): uma linha em "How it works"/"Como funciona" dizendo que existe um motor sem janela, em preparação para a interface nova.
    - `CLAUDE.md` do Reco, em até 3 linhas: o motor `engine/` importa o `reco.py` sem mudá-lo, é dono do config, contrato em `docs/PROTOCOL.md`, e `python tools/test_engine_protocol.py` antes de commitar mudança no motor.
      Conferir o teto de 6 KB do `gate-claude-md`.
    - Pegadinhas entram por `python tools/visoes.py novo "título"`; nunca editar `docs/ARMADILHAS.md`.
      Entra pelo menos a do COM (passo 3: a thread que importa o `soundcard` tem de viver), mais o que a execução achar (ex.: `dup2` no PyInstaller).
    - Hub `C:\Dev\cerebro\projetos\reco.md`: uma linha em "Estado agora" e o roadmap em "Roadmaps em voo" com 1/8 ou 2/8 fases, por `Edit` ancorado.
    - Relatório curto em `2026-11-11-melhoria-reco-em-rust.d/` com os números dos passos 3 e 15.
    - Fragmento do diário do cérebro (`cerebro/pessoal/diario/2026-11-11/` ou o dia da execução) e `compilar_fragmentos.py`.

## Decisões da fase

| id | decisão | motivo | confiança | reverte se |
| --- | --- | --- | --- | --- |
| F2-D1 | Threads, não asyncio: uma leitora do stdin, uma thread por pedido, lock na escrita | o núcleo do `reco.py` é de threads e callbacks (`DualRecorder`, `OVTranscriber`); asyncio só acrescentaria ponte | alta | precisar cancelar muitos pedidos curtos (aí asyncio com `to_thread`) |
| F2-D2 | Comando longo responde só no fim, com progresso que leva o `id` (o `fdr` do Lacre); o casco ajusta o timeout por comando | o Router do Lacre já faz isso; um `job id` separado dobraria o protocolo | alta | a Fase 3 precisar reconectar a um trabalho depois de o casco reiniciar |
| F2-D3 | `hello` responde antes do `import reco`; o resto espera o evento `ready` | o import custou ≈2,2 s do fonte (medido 11/11) e o casco mostra a janela antes | alta | a Fase 0 mostrar que o import congelado é desprezível |
| F2-D4 | Aquecer só imports (`scipy.signal`, `av`, `openvino`, `openvino_genai`), nunca o `WhisperPipeline` | o pipeline custa 14,6 s e 1,35 GB por processo num app de bandeja; gravar não depende da GPU | média | o Gabriel pedir transcrição instantânea ao parar, ou a Fase 0 medir RAM sobrando |
| F2-D5 | `pct` extraído do texto traduzido com `(\d+)%`; texto repassado como veio | o `reco.py` não muda e só entrega o número dentro de `tf(...)` (`reco.py:2211`, `:2225`, `:2296`, `:2328`) | média | a frase mudar no `reco.py`, ou a Fase 6 trazer progresso numérico de verdade |
| F2-D6 | `config.set` relê, faz merge, aceita só chaves de `_CFG_DEFAULTS` (e `casco_*`), grava e relê para conferir; o motor nunca chama `load_config(persist=True)` | `save_config` engole exceção; o config real tem chaves legadas; a ARMADILHA da migração | alta | — |
| F2-D7 | stdout isolado no descritor (`os.dup(1)` para o protocolo, `os.dup2(2, 1)`), além de `sys.stdout = sys.stderr` | escrita nativa (OpenVINO, ffmpeg) iria ao fd 1 e quebraria o parse | média | o `dup2` falhar no exe congelado (aí só o desvio do Lacre, com a premissa registrada) |
| F2-D8 | O motor congelado não leva o modelo `small` (245 MB) | ele é só reserva offline; o modelo usado (turbo) mora em `%LOCALAPPDATA%` | média | a Fase 4 exigir primeira abertura sem internet |
| F2-D9 | `tkinter` e `PIL` ficam no bundle; clipboard, abrir arquivo/pasta/URL, mutex e diálogos ficam no casco Rust | `import reco` precisa deles sem guarda (`reco.py:17-18`, `:544`); a interface é do casco | alta | o `reco.py` sair de cena (Fase 7) |
| F2-D10 | Motor congelado com `console=True`, escondido pelo `CREATE_NO_WINDOW` de quem o sobe | combinação provada no Lacre (`build.py:39`, `engine.rs:194-199`) | alta | o casco provar janela escondida com `console=False` e pipes |
| F2-D11 | `devices.refresh` é sinônimo de `devices.list` | a enumeração já é fresca a cada chamada (`reco.py:1408-1414`) | alta | aparecer cache no motor |
| F2-D12 | `rec.stop` diz em `auto` se vem `final_pass` ou `nota`, e o casco chama `rec.conclude`; o motor não encadeia sozinho | trabalho longo fica preso a um pedido com `id`, progresso e cancelamento; se o casco falhar, o mp3 fica | média | a Fase 3 achar frágil (aí o motor encadeia) |
| F2-D13 | `level`: um evento a cada 50 ms com os dois canais (maior RMS da janela, já com ganho) e só gravando | o callback roda a ≈47 Hz por canal dentro da captura; nada pesado pode ficar ali | alta | a vitrine da Fase 1 pedir pico separado do RMS |
| F2-D14 | Python global 3.14 (o do `build.ps1`), sem venv nem uv nesta fase | é onde as dependências do Reco já estão instaladas e medidas | média | o bundle puxar lixo do ambiente global além de pyarrow/duckdb (aí venv dedicado em `engine/`) |
| F2-D15 | `library.delete` só aceita áudio (`AUDIO_EXTS`) dentro da pasta da biblioteca | exclusão por caminho arbitrário vindo da interface é risco de dado; a Lixeira não cobre caminho de rede | alta | a interface precisar excluir fora da pasta (aí lista explícita de pastas) |
| F2-D16 | Preferência do casco mora no mesmo config, com o prefixo `casco_` | D6 (um dono só); o `reco.py` preserva chave desconhecida e o app velho a ignora | média | o app velho passar a reescrever o config sem as chaves extras (aí arquivo próprio do casco, gravado pelo motor) |
| F2-D17 | `--selftest` vive no `cli.py` do motor, com a mesma saída do `reco.py:5132-5146` | smoke sem janela das Fases 0 e 4 e régua da partida congelada; sem ele, o diagnóstico some com o build velho (Fase 7) | alta | o casco ganhar diagnóstico próprio de backend e dispositivos |

## Premissas não verificadas

- O exe congelado com `console=True`, pipes e `CREATE_NO_WINDOW` não mostra janela. Provado no Lacre, não no Reco; o passo 15 confere.
- O `os.dup2(2, 1)` no exe congelado leva a saída nativa do OpenVINO ao stderr sem quebrar o PyInstaller. Não testado; o passo 2 prova do fonte e o 15 do exe.
- O `tkinter` congelado em modo console importa sem erro de Tcl/Tk (o `reco.spec` só provou em modo janela).
- O `soundcard` funciona em threads criadas pelo motor como funciona nas do app (`reco.py:3700-3709`, `:1784-1830`).
  Enumerar foi rodado na auditoria e só funciona com a thread do import viva (passo 3); gravar nessas threads não foi rodado.
- Tocar `clip10.wav` (16 kHz) pelo `soundcard` no alto-falante padrão e capturá-lo pelo loopback no mesmo processo funciona. Não rodado; se falhar, tocar o clipe com o `winsound` do próprio Python.
- O `.txt` sai igual byte a byte em duas rodadas do mesmo MP3. Não medido; se não sair, vale a régua de duas referências do passo 8.
- O `claude` está no PATH quando o casco Tauri sobe o motor (o PATH é herdado). Vale para a Fase 3 conferir.
- Ninguém chama `Reco.exe --transcribe` hoje: o grep em `central/canais/whatsapp/coletor/src` e `cerebro/scripts` não achou chamador, mas a varredura não cobriu `C:\Dev` inteiro.
- O `subprocess.run` do resumo acha e roda um `claude.cmd` falso pelo `shutil.which` (o Windows executa `.cmd` pelo PATHEXT). Não testado; se falhar, o falso vira um `.exe` mínimo ou o teste chama a função do motor direto.
- O tamanho do motor congelado (meta de até 700 MB sem o `small`) e a memória depois do aquecimento não foram medidos.
- Os números da Fase 0 (tempo de abrir o app velho, `import_reco`, `exe_selftest`) ainda não foram medidos: o md da Fase 0 os define, a execução dela traz.
- A Fase 3 foi escrita com nomes provisórios (`record_start`, `conclude`, `live_text`...); o passo 1 dela troca pelos nomes do `docs/PROTOCOL.md` daqui.
  Os nomes desta fase são a fonte da verdade: o comando de retrato é `state` (não `rec.state`), e o ganho no arrasto vai por `rec.set_gain`, com `config.set` só ao soltar.

## Pendente (dono: gabriel)

- **Fechar o Reco pela bandeja (Sair) antes dos passos 6, 7, 9 e 15**, e não estar em chamada: o clipe sai no alto-falante. `dono: gabriel`.
  O app velho fica aberto na bandeja o dia todo (na auditoria de 11/11 o `Reco.exe` estava rodando), e com ele aberto o teste aborta de propósito.
  O executor **nunca** mata o `Reco.exe` (`taskkill /F` perde uma gravação em curso): sem o app fechado, faz os passos sem gravação e deixa estes para depois.
  Com o app fechado, as gravações rodam sem ninguém por perto (o teste toca o clipe).
- Ouvir a gravação de 30 s do passo 15 no app velho e dizer se a voz e o som do PC estão nos lados certos. `dono: gabriel`.
  É a única prova de que mic e sistema não saíram trocados (RMS > 0 nos dois lados não distingue): fecha o primeiro critério de aceite, mas não bloqueia o começo da Fase 3.
  Depois da escuta, a gravação de teste vai à Lixeira (passo 15); se ele quiser guardá-la, basta dizer.
  Se a escuta vier depois do fim da sessão, o relatório anota o caminho e a pendência, e a sessão seguinte roda o comando do passo 15.

## O que esta fase NÃO faz

- Não toca em `reco.py`, `tray.py`, `tools/transcrever.py`, `reco.spec` nem `build.ps1`. Também não recompila o app velho, porque nada que entra nele muda.
- Não cria o casco Tauri, a bandeja, o mutex `Local\Reco.SingleInstance` nem interface: é a Fase 3.
- Não decide visual nem textos de interface: a interface traduz códigos e monta rótulos (Fase 1 e 3).
- Não muda captura, MP3, alinhamento, AEC nem transcrição: o motor chama o código medido como está. O buffer de 22 ms e o salto seguem (Fase 5).
- Não aquece o pipeline da GPU nem promete transcrição mais rápida.
- Não implementa a vigia de zero do dispositivo Auto (Fase 2 daquele roadmap, absorvida pela Fase 5 daqui).
- Não faz o teste de 20 min do ao vivo (reabre na Fase 5).
- Não faz instalador, CI nem atualização automática do motor.

## Gatilho que fecha

- `python tools/test_engine_protocol.py` verde do fonte e com `--exe` (checagens padrão), com o config real igual byte a byte.
- As provas com gravação dos passos 6, 7, 9 e 15 anotadas no relatório, com o caminho da gravação de 30 s para o Gabriel ouvir.
- O `.txt` do motor igual byte a byte ao do app velho no mesmo MP3 (passos 8 e 12), e o `--selftest` do motor igual ao do `reco.py` (passo 12).
- `docs/PROTOCOL.md` commitado e conferido contra o registro (passo 13); a Fase 3 começa por ele.
- Smoke com `hello` abaixo de 3 s nas 3 rodadas, pasta sem pyarrow/duckdb e tamanho anotado (passo 15).
- `git diff <SHA-INICIO> -- reco.py tray.py tools/transcrever.py reco.spec build.ps1` vazio, docs e hub atualizados (passo 16).
