## Relatório de execução — Fase 2 (2026-11-11, sessão 4c65eb01)

Fase: [fase-2](../2026-11-11-melhoria-reco-em-rust-fase-2.md) (Motor Python como servidor) · índice:
[Reco em Rust](../2026-11-11-melhoria-reco-em-rust.md).

- **SHA-INICIO:** `c79b042` (`git rev-parse --short HEAD` ao começar). Frescor: `git log 7c5c1a1..HEAD --
  reco.py tray.py tools/transcrever.py` vazio.
- **Condição da execução:** o Reco do Gabriel estava aberto (mutex `Local\Reco.SingleInstance`). Os
  passos que gravam (6, 7, 9 e a gravação do 15) foram **escritos e não rodados**: a guarda aborta
  por desenho. Rodaram depois do Sair, em 12/11 (seção "Provas que gravam"), todos verdes.
- **Config real:** sha256 do `%USERPROFILE%\.reco_config.json` igual do começo ao fim
  (`4fd17883…5635a`), conferido pelo próprio teste em cada rodada e à mão no fim.
- **Commit:** nenhum nesta execução; o chamador commita no fim (desvio do "um commit por passo").

### Passos

| passo | estado | prova (comando → o que veio) |
| --- | --- | --- |
| 1 esqueleto | feito | `(cd engine && python -c "import reco_engine, reco_engine.errors as e; print(reco_engine.__version__, sorted(e.CODES)[:3])")` → `0.1.0 ['bad_args', 'busy', 'cancelled']` |
| 2 servidor + teste | feito | `python tools/test_engine_protocol.py` → `OK protocolo: hello, linha inválida, cmd desconhecido, id não-string, shutdown (exit 0)` |
| 3 boot | feito | idem → `OK ready: import_s=0.382 has={sc:True,np:True,av:True,ov:True} lang=pt (hello em 0.42 s; aquecimento 2.12 s)` |
| 4 config | feito | idem → `OK config: get, set mic_gain=2.5, chave legada preservada, migração não persistida, config real intocado (sha256 igual)` |
| 5 dispositivos | feito | idem → `OK dispositivos: 1 mics, 2 saídas, console mic=Grupo de microfones (Tecnologia Intel® Smart Sound…), console saída=Alto-falantes (Realtek(R) Audio)` |
| 6 gravação | feito (12/11, depois do Sair) | `--gravar 5` → `OK gravação: 4.9 s (decodificada 4.9), 2 canais, 16000 Hz, level 18.2/s, timer 1.19/s, L e R com sinal (RMS 0.0024/0.0780) (clipe via soundcard)` (antes do Sair: a guarda abortou, exit 1) |
| 7 D11 (EOF/shutdown) | feito (12/11) | `--eof 25` → `OK eof: declarada 24.9 s, decodificada 24.9 s, saiu em 0.5 s; OK shutdown no meio: declarada 24.8 s, decodificada 24.8 s, saiu em 0.6 s` |
| 8 transcrição | feito | `--transcrever <cópia de uma gravação de 87 s>` → `OK transcrição: .txt igual ao do app (igual byte a byte; refs iguais=True; 19.5 s), 11 progressos, pct crescente; cancel → cancelled; id repetido → internal` |
| 9 conclusões | feito (12/11) | `--gravar 5 --concluir` → `OK conclusões: save, delete (Lixeira), transcribe, transcribe_delete, nota, final_pass (1 live.text), 2 cancelados com mp3` (1 min 44 s) |
| 10 biblioteca | feito | `python tools/test_engine_protocol.py` → `OK biblioteca: 3 itens, duração 1 s, x.txt e x.mp3.txt achados, busca por conteúdo nas duas convenções, delete fora da pasta recusado`; com `--lixeira`: `… (delete real: na Lixeira)` |
| 11 extras | feito | idem → `OK extras: convert 16 kHz mono, sem trilha = no_audio_stream, app.update_check, claude_missing, claude falso recebeu --model sonnet` |
| 12 CLIs | feito | `--cli <a mesma cópia>` → `OK cli: exit 0, stdout vazio, log OK, .txt igual (igual byte a byte); OK selftest igual` |
| 13 PROTOCOL.md | feito | `--conferir-doc` → `OK doc: 22 comandos no registro, 22 na tabela do PROTOCOL.md, nenhum faltando` |
| 14 build | feito | `python engine/build.py && ! ls engine/dist/reco-engine/_internal \| grep -qiE 'pyarrow\|duckdb' && echo LIMPO` → `built …\engine\dist\reco-engine\reco-engine.exe (515 MB …)` e `LIMPO` (2 min 50 s de build) |
| 15 congelado | feito (gravação de 30 s em 12/11) | `python engine/build.py --smoke && python tools/test_engine_protocol.py --exe engine/dist/reco-engine/reco-engine.exe` → 3 linhas `run i` (abaixo) e os 7 `OK` padrão; `--gravar 30 --saida-real --exe …` → ver "Provas que gravam" abaixo |
| 16 fechar | feito (docs; prova rodada de novo em 12/11 → `5`), hub e diário com o chamador | `git diff --quiet c79b042 -- reco.py tray.py tools/transcrever.py reco.spec build.ps1 && grep -lE '…' docs/{ARQUITETURA,TOOLS,_INDICE}.md CLAUDE.md ../cerebro/projetos/reco.md \| wc -l` → `5` |

Ressalva do passo 16: o `5` sai **sem** a linha nova no hub, porque o hub já cita `reco-em-rust` (a
linha do roadmap de 11/11). A prova fica fraca para o hub; a linha da Fase 2 no hub e o fragmento do
diário são do chamador.

### Números (passos 3 e 15)

- **Do fonte (passo 3):** `import reco` 0,34 a 0,39 s; `hello` 0,17 a 0,50 s depois do spawn;
  aquecimento (`scipy.signal`, `av`, `openvino`, `openvino_genai`) 1,7 a 2,2 s.
- **Congelado (passo 15), smoke do build final** (o exe foi refeito depois das correções da revisão;
  a rodada `--exe` e a transcrição pelo exe rodaram de novo sobre ele):
  - `run 1: hello ok=True em 0.63 s; ready em 0.88 s; shutdown ok=True exit=0`
  - `run 2: hello ok=True em 0.51 s; ready em 0.84 s; shutdown ok=True exit=0`
  - `run 3: hello ok=True em 0.49 s; ready em 0.79 s; devices ok=True (1, 2) em 0.06 s; memória 149.760 K; shutdown ok=True exit=0`
  - Primeira partida logo depois de um build (cache frio): hello 0,7 a 1,9 s, ready 1,0 a 2,2 s.
    Rodadas anteriores, com a máquina menos ocupada: hello 0,36 a 0,44 s, ready 0,61 a 0,67 s.
  - Memória depois do aquecimento: **~150 MB** (conjunto de trabalho do `tasklist`), sem o pipeline.
  - Tamanho: **515 MB** (o `dist/Reco` velho tem 859 MB; saíram pyarrow, duckdb e o modelo `small`).
  - `reco-engine.exe --selftest`: exit 0 em **1,61 s**, `frozen=True lang=pt …`, `resolved(AUTO)=GPU`.
  - Janela: `MainWindowHandle` 0 no motor e no `conhost` filho, subindo com `CREATE_NO_WINDOW`.
  - Transcrição pelo exe (`--transcrever … --exe …`): igual byte a byte, 22,8 s para os 87 s (19,5 s do
    fonte). Prova a premissa do `dup2` e do OpenVINO no congelado.
- **Comparação com a Fase 0** ([fase-0-relatorio](fase-0-relatorio.md), passo 3): o `exe_selftest` do
  `Reco.exe` velho levou 5,4 s (mediana; 7,4 s na 1ª); o `reco-engine.exe --selftest` levou **1,6 s**.
  O motor congelado responde `hello` em 0,4 s e fica `ready` em 0,6 a 0,7 s. O `import_reco` da Fase 0
  (1,48 s) mede um processo novo inteiro; o `import_s` daqui (0,3 a 0,4 s) é só o import dentro do
  motor já de pé, então não são a mesma régua. O tempo de abrir o app velho até "pronto" (Bloco B da
  Fase 0) ainda não existe para comparar.

### Provas que gravam (12/11, 23:56 a 00:00, sessão religada depois do Sair)

- **Condição:** o `Reco.exe` do Gabriel fechado pelo Sair da bandeja desde ~23:18 de 11/11
  (`tasklist` vazio antes de cada prova; nenhum `reco-engine.exe` sobrando no fim). CPU total 61 a 86%
  (vitest e vite do `unclick`, MCP do Playwright), mas nenhum processo isolado acima de 30% do total
  (o maior, um `node` do vitest, a 9%); as provas rodaram assim, sem espera. O clipe tocou no
  alto-falante (aceito).
- **Exe:** o `engine/dist/reco-engine/reco-engine.exe` de 11/11 22:04 é mais novo que todo
  `engine/reco_engine/*.py` e o `.spec` (o commit `6871cf4` só mexeu no teste); não precisou de build.
- **Sem correção no motor:** as quatro provas passaram na primeira rodada.

| passo | comando | saída |
| --- | --- | --- |
| 6 | `python tools/test_engine_protocol.py --gravar 5` | `OK gravação: 4.9 s (decodificada 4.9), 2 canais, 16000 Hz, level 18.2/s, timer 1.19/s, L e R com sinal (RMS 0.0024/0.0780) (clipe via soundcard)` |
| 7 | `--eof 25` | `OK eof: declarada 24.9 s, decodificada 24.9 s, saiu em 0.5 s; OK shutdown no meio: declarada 24.8 s, decodificada 24.8 s, saiu em 0.6 s` |
| 9 | `--gravar 5 --concluir` | `OK conclusões: save, delete (Lixeira), transcribe, transcribe_delete, nota, final_pass (1 live.text), 2 cancelados com mp3` |
| 15 | `--gravar 30 --saida-real --exe engine/dist/reco-engine/reco-engine.exe` | `OK gravação: 29.9 s (decodificada 29.9), 2 canais, 16000 Hz, level 19.7/s, timer 1.00/s, L e R com sinal (RMS 0.0020/0.0907) (clipe via soundcard)` · `OK lados: clipe×R 0.96 > clipe×L 0.74 (voz do PC no canal direito)` |

- **Gravação de 30 s:** caiu em `Documents\Reco\gravacao_reco_2026-11-11_23-59-35.mp3` (a pasta que a
  biblioteca do app velho lista; 365.733 bytes). Lados provados por dado (`OK lados`), então a escuta
  do Gabriel virou opcional e não foi pedida. Mandada à Lixeira pelo comando do passo 15 (exit 0); o
  arquivo sumiu da pasta e `gravacao_reco_2026-11-11_23-59-35.mp3` aparece na lista da Lixeira
  (`Shell.Application`, `NameSpace(10)`). Se o Gabriel quiser ouvir, basta restaurar de lá.
- O `clipe×L 0.74` mostra que o mic pega o alto-falante pela sala (esperado sem fone); a régua é R ≥ 0,5
  e R > L, e o R ficou em 0,96.
- **Config real:** sha256 `4fd17883…5635a` igual antes e depois da gravação com `--saida-real`.
- **Passo 16:** `git diff --quiet c79b042 -- reco.py tray.py tools/transcrever.py reco.spec build.ps1 &&
  grep -lE … | wc -l` → `5`. A ressalva acima sobre o hub continua valendo.

### Pendente do Sair do Gabriel (passos 6, 7, 9 e a gravação do 15) — resolvido em 12/11 (acima)

Com o Reco fechado pela bandeja (Sair), fora de chamada (o clipe toca no alto-falante), na raiz do
repo:

1. `python tools/test_engine_protocol.py --gravar 5` → esperado `OK gravação: 5,0±0,5 s …, 2 canais,
   16000 Hz, level <=20/s, timer ~1/s, L e R com sinal`.
2. `python tools/test_engine_protocol.py --eof 25` → `OK eof: declarada ≈ decodificada (±1 s), 25±1 s;
   OK shutdown no meio: idem`, saindo em até 8 s.
3. `python tools/test_engine_protocol.py --gravar 5 --concluir` → `OK conclusões: save, delete
   (Lixeira), transcribe, transcribe_delete, nota, final_pass (<n> live.text), 2 cancelados com mp3`.
4. `python tools/test_engine_protocol.py --gravar 30 --saida-real --exe engine/dist/reco-engine/reco-engine.exe`
   → `OK gravação: …` e `PARA OUVIR (Gabriel): <caminho>`. O Gabriel ouve no app velho (Gravações…)
   e diz se a voz e o som do PC estão nos lados certos; depois a gravação vai à Lixeira com
   `python -c "import sys, reco; sys.exit(0 if reco._excluir_gravacao(sys.argv[1]) else 1)" "<caminho>"`.

O que já há a favor desses passos, sem dispositivo:

- A guarda do mutex aborta nos quatro modos antes de subir o motor ou tocar som (acima).
- A rodada padrão exercita os caminhos ociosos do `recording.py` e do `conclude.py` (`state`,
  `rec.stop`/`rec.pause` fora de gravação → `refused`, `rec.conclude` sem gravação → `not_found`,
  `rec.set_gain`, `mode` inválido).
- Ensaio a seco em processo, no scratchpad (fora do git), com um `DualRecorder` falso que escreve MP3
  pelo `reco.MP3Writer`: start → pausa → retoma → stop (estados `recording, paused, recording,
  stopping, stopped`; `level` e `timer` saindo), `busy` no segundo start, `save` → `idle`, `delete`,
  `nota` com `auto: "nota"`, erro de canal antes do `recording` repassado como `rec.error` não fatal e
  `close_for_exit` no meio da gravação fechando o arquivo (declarada 1,54 s = decodificada 1,54 s).
- Segundo ensaio a seco, todos os ramos do `conclude.py` com transcrição real na GPU sobre cópias da
  amostra (`last_rec` = cópia, estado `stopped`): arquivo sumido → `not_found` e `idle`;
  `transcribe` (`.txt`, mp3 fica, `idle`); `transcribe_delete` (`.txt`, mp3 sai); `final_pass` (`.txt`
  e texto, continua `stopped`, `save` leva a `idle`); `nota` (`.md`, mp3 sai, `idle`, `last_rec`
  esquecido); os dois cancelados respondem `cancelled` com o mp3 no disco e o estado em `idle`.

### completei:

- **Isolamento do stdin** (achado, não estava no md): com a leitora presa no `readline` do pipe, o
  `import reco` em outra thread levou 12 a 20 s (DLL do numpy esperando o `ReadFile`). O motor tira o
  pipe do fd 0 (`_isolate_stdin`); o import voltou a 0,4 s. Virou pegadinha nova e checagem na rodada
  padrão (espera `ready` e "aquecimento pronto" sem mandar linha).
- **Cancelamento pegajoso** no motor: o `OVTranscriber.transcribe()` limpa o próprio sinal ao começar;
  um `transcribe.cancel` que chega entre o `claim` e esse início é reaplicado. Sem isso o cancel da
  nota curta (passo 9) dependia de corrida.
- **Erro de canal antes do `recording`**: falha de abertura do mic/sistema chega antes de o estado
  virar `recording` (no App ela entra pela fila do Tk depois); o motor guarda e repassa como
  `rec.error` logo depois do start.
- **Abort fora da thread de captura**: o `rec.error` fatal aborta numa thread própria (abortar na
  thread de captura faria o `_wind_down` dar join nela mesma).
- **`library.delete` recusa o arquivo que está sendo gravado.**
- **Estado preso em `stopped`** (pego na crítica do advisor): se a última gravação some do disco
  (`library.delete`, Explorer), o `rec.conclude` responde `not_found` e o estado vai a `idle`; antes
  ficava `stopped` para sempre e o `rec.start` só respondia `busy` até reiniciar o motor.
- **`final_pass` mantém `stopped`** (como o App): o teste do passo 9 agora conclui com `save` depois
  dele (sem isso o caso seguinte daria `busy`), e o PROTOCOL.md diz que o casco ainda conclui.
- O `--gravar` confere também declarada × decodificada (±1 s), além da duração esperada.
- **Revisão independente** (subagente de contexto limpo, só leitura) do `recording.py`, `conclude.py`,
  `core.py`, `transcribe.py` e da saída do `server.py`. Sete achados; todos corrigidos e ensaiados a
  seco (gravador falso, sem som):
  1. estado preso em `stopped` com o arquivo sumido (já corrigido acima);
  2. o ao vivo usava modelo e device padrão, não os do config → `make_live` aplica `set_model` e
     `set_device` (ensaio: device `CPU` do config chegou ao transcritor);
  3. `transcribe.file` aceito durante o ao vivo (dois `pipe.generate` no mesmo pipeline) → reserva
     `live_active` sob o lock, liberada só depois do dreno do `rec.stop` (ensaio: `busy`);
  4. `rec.stop`/`pause`/`resume` checavam o estado sob o lock e trocavam fora dele → troca na mesma
     trava (ensaio: dois `rec.stop` juntos dão `ok` e `refused`);
  5. erro fatal não reservava o estado durante o `abort()` → vai a `stopping` sob o lock antes do
     aborto (ensaio: `rec.stop` logo depois dá `refused`; estado `stopping` → `idle`, arquivo
     descartado como no App);
  6. a saída não reservava o estado nem esperava um `rec.start` em curso → `_claim_exit` espera o
     `starting` e reserva `stopping` (ensaio: saída durante `starting` fechou a gravação que nasceu,
     0,48 s);
  7. a saída podia passar dos 8 s do casco (3 joins de 3 s no `stop()`) → wind-down com 1,5 s por
     join antes do `stop()`.
  Menores, também feitos: pedido depois do `shutdown`/EOF responde `refused` ("motor encerrando");
  `final_pass` com falha no `.txt` devolve `{txt: null, text}` em vez de perder o texto; `live.warn`
  sai numa thread própria, não na do codificador do MP3.
- Caminhos ociosos de gravação/conclusão na rodada padrão (ver acima); `--transcrever` também roda
  com `--exe`; `build.py --smoke` mede a memória depois do aquecimento; conferência de janela do exe.
- `config.set` valida tipo e faixa por chave (ganho 0 a 10, booleanos, idioma `pt`/`en`/`null`), além
  da lista de chaves.

### Decisões técnicas — Fase 2

| decisão | motivo | confiança | o que reverteria |
| --- | --- | --- | --- |
| Pipe do stdin fora do fd 0 (`os.dup(0)` + `dup2` do NUL), leitora no fd duplicado | medido: leitora presa no stdin travava o carregamento de DLL em outra thread (import 0,4 s → 12-20 s) | alta | o casco passar a falar por outro canal (named pipe, socket) |
| Estado transitório `starting` durante o `rec.start` (reserva contra dois starts paralelos) | o `rec.start` resolve dispositivos e abre arquivo fora do lock; sem reserva, dois pedidos gravariam juntos | média | a Fase 3 mostrar que o casco serializa os pedidos (aí some) |
| Erros de estado (`rec.pause`/`rec.stop` sem gravação, `rec.conclude` fora de `stopped`) respondem `refused` | o md não fixa o código; `busy` fica para "há trabalho em curso" | média | a interface preferir um código próprio (ex.: `bad_state`) |
| `rec.conclude` exige o estado `stopped` (além do `last_rec` no disco); arquivo sumido em `stopped` leva a `idle` antes do `not_found` | o App só mostra as saídas em STOPPED; evita concluir duas vezes e não prende o estado | média | a Fase 3 precisar concluir de `idle` (ex.: reabrir uma gravação) |
| Cancelamento pegajoso (`core.cancel_pending`) | o `OVTranscriber` limpa o sinal no início; sem isso o cancel cedo se perde | alta | o `reco.py` mudar o `transcribe()` |
| `config.get` responde `{config, output_dir_efetivo, lang_efetivo}`; `library.*` responde `{folder, items}` / `{q, items}` | objeto com campos nomeados cresce sem quebrar o casco | alta | — |
| Teste do cancel da conclusão (passo 9) manda `transcribe.cancel` em laço logo depois do `rec.conclude` até `found:true`, em vez de esperar o primeiro `progress` | nota de 5 s com mic só de ruído pode ter zero grupos de VAD e terminar antes de qualquer `progress` com `pct` | média | a prova do passo 9 rodar e o cancel por `progress` se mostrar estável |
| Teto do `hello` na checagem: 1 s do fonte, 3 s com `--exe` | passo 3 pede < 1 s do fonte; passo 15 aceita até 3 s congelado | alta | — |
| Ao vivo ligado reserva o pipeline (`live_active`): `transcribe.file`, `rec.conclude` com transcrição e `model.update_check` respondem `busy` até o dreno do `rec.stop` | um `pipe.generate` por vez; o App garante isso travando a tela durante a gravação | alta | a Fase 6 trazer pipeline separado para o ao vivo |
| Na saída, wind-down do `DualRecorder` com 1,5 s por join (chama o `_wind_down` privado antes do `stop()`) | o `stop()` espera até 3 s por thread e o casco mata em 8 s | média | o `reco.py` ganhar `stop(timeout=)` ou a captura ir para Rust (Fase 5) |
| Pedido que chega depois do `shutdown`/EOF responde `refused` | um `rec.start` durante a saída deixaria arquivo órfão | alta | — |

### Provas que reprovam (mutação em cópia no scratchpad, nunca no repo)

| mutação | resultado |
| --- | --- |
| `boot.py`: a thread do import termina (`return` no lugar do `Event().wait()`) | `FALHOU: listas vazias: 0 mics, 0 saídas (thread do COM?)` |
| `config_cmd.py`: merge sobre `reco.load_config()` em vez do arquivo cru | `FALHOU: config temporário diverge: {… defaults gravados …} != {…}` |
| `server.py`: sem `_isolate_stdin` | `FALHOU: evento ready não chegou em 60 s` |
| regex do `--conferir-doc` sem dígitos (erro real, pego na primeira rodada) | `FALHOU: comandos do motor fora da tabela do PROTOCOL.md: ['convert.extract_mp3']` |

O que **não** tem prova que reprove: o `os.dup2(2, 1)` do stdout (F2-D7). Nenhum comando do protocolo
provoca escrita nativa no fd 1, então remover o `dup2` não quebraria a rodada padrão; a transcrição
pelo exe sem nenhuma linha estranha no stdout é a evidência que há.

### Desvios do md

- Sem commit por passo (instrução do chamador: ele commita no fim). Trava rodada por `git add` +
  `pre-commit run --files` + `git restore --staged`, depois do passo 2 e no fim: nenhum `Failed`.
- Passo 16: hub do cérebro e fragmento do diário não editados (ficam com o chamador).
- Passo 15: a gravação de 30 s rodou em 12/11 depois do Sair; a escuta foi trocada pela prova dos
  lados por dado (regra de 11/11) e a gravação foi à Lixeira sem esperar o Gabriel ouvir.
- Uma edição de texto foi feita com um script Python (ajuste do `recording.py`, durante a escrita),
  contra a regra da casa; daqui em diante só `Edit`. O resultado foi revisto e testado.
- O ensaio a seco e o `--lixeira` mandaram MP3 de teste para a Lixeira: dois gerados (1 a 2 s) e três
  cópias da gravação de 87 s usada como amostra (o original na pasta do Reco não foi tocado).

### Arquivos tocados

Criados:

- `engine/reco_engine/__init__.py`, `__main__.py`, `errors.py`, `core.py`, `boot.py`, `server.py`,
  `config_cmd.py`, `devices.py`, `recording.py`, `conclude.py`, `transcribe.py`, `library.py`,
  `extras.py`, `cli.py`
- `engine/reco-engine.spec`, `engine/build.py`
- `tools/test_engine_protocol.py`, `tools/engine_harness.py`, `tools/engine_checks_proto.py`,
  `tools/engine_checks_config.py`, `tools/engine_checks_lib.py`, `tools/engine_checks_tr.py`,
  `tools/engine_checks_rec.py`, `tools/engine_checks_conclude.py`
- `docs/PROTOCOL.md`
- `docs/armadilhas.d/2026-11-11-2145-a-thread-que-importa-o-soundcard-tem-de-viver-senao-enumerar.md`
- `docs/armadilhas.d/2026-11-11-2145-thread-presa-no-readline-do-stdin-trava-o-carregamento-de-dl.md`
- este relatório

Alterados: `docs/ARQUITETURA.md` (seção "Motor (`engine/`)"), `docs/TOOLS.md` (linha do teste),
`docs/_INDICE.md` (linha do PROTOCOL.md), `README.md` (uma linha em cada língua), `CLAUDE.md` (seção de 2
linhas; 5432 B de 6144).

Fora do git (gerados): `engine/dist/`, `engine/build/`, `docs/ARMADILHAS.md`, `roadmap/README.md`.
Não tocados: `reco.py`, `tray.py`, `tools/transcrever.py`, `reco.spec`, `build.ps1`, `design/`, o md
da fase e o índice.
