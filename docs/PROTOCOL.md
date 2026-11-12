# Reco — contrato entre o motor (Python) e o casco (Tauri)

O **motor** (`engine/reco_engine`, Python 3.14, congelado com PyInstaller em `engine/dist/reco-engine/`)
é um processo de longa duração que fala **JSON Lines** em stdin/stdout. Ele importa o `reco.py` sem
mudar uma linha e reimplementa a orquestração que mora nos métodos do `App` Tk. O **casco** (Fase 3:
Rust + interface) sobe o motor uma vez, manda pedidos e recebe respostas e eventos.

Fonte da verdade dos nomes: este arquivo e o registro `COMMANDS` de `engine/reco_engine/server.py`
(`python tools/test_engine_protocol.py --conferir-doc` confere os dois). Os nomes provisórios da
Fase 3 (`record_start`, `conclude`, `live_text`…) são substituídos por estes.

## Regras invariáveis

- **stdout só carrega o protocolo**: uma mensagem JSON por linha, UTF-8. Log e qualquer `print` vão
  para o stderr. O motor isola o fd 1 (`os.dup(1)` vira o canal; o fd 1 passa a ser o stderr), então
  nem escrita nativa (OpenVINO, ffmpeg) quebra o parse. O casco **drena o stderr** sempre.
- O stdin também é isolado: o pipe sai do fd 0, que vira NUL (com uma thread presa no `readline`, o
  carregamento de DLL em outra thread travaria; ver ARMADILHAS).
- Toda mensagem tem `"v": 1`. O `id` do pedido é **texto não vazio**; `id` numérico, linha que não é
  JSON, `cmd` desconhecido ou `id` repetido ainda em andamento respondem `internal` (linha ilegível
  responde com `"id": null`).
- **O motor é o dono do config** (`~/.reco_config.json`, D6): o casco nunca grava esse arquivo; pede
  `config.set`. O motor nunca persiste a migração (`load_config(persist=False)` sempre).
- O motor emite **códigos e dados**; a interface traduz e monta os rótulos. Dívida declarada: o texto
  de progresso da transcrição e os avisos do ao vivo vêm traduzidos do `reco.py` (campo `text`); o
  número vem à parte (`pct`).
- Subir com `CREATE_NO_WINDOW` (o exe é `console=True`) e as variáveis `PYTHONUNBUFFERED=1`,
  `PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1`.

## Mensagens

```json
{"v":1,"id":"<texto único>","cmd":"<comando>","args":{...}}
{"v":1,"id":"<id do pedido>","ok":true,"data":...}
{"v":1,"id":"<id do pedido>","ok":false,"error":{"code":"<código>","detail":"<texto técnico curto>"}}
{"v":1,"id":"<id do pedido>","event":"progress","pct":42,"text":"Transcrevendo… 42%"}
{"v":1,"event":"level","mic":0.031,"sys":null}
```

Comando longo responde **só no fim**, com eventos `progress` que levam o `id` no meio (F2-D2). Evento
global (sem pedido) vai **sem** `id`; o casco testa `event` antes de `id`.

## Comandos

| cmd | args | data | eventos | timeout sugerido |
| --- | --- | --- | --- | --- |
| `hello` | `{}` | `{engine_version, reco_version\|null, protocol:1, platform, ready, uptime_s}`; responde antes do `import reco` | — | 10 s |
| `shutdown` | `{}` | `{}` e o processo sai (fecha o MP3 se estiver gravando) | — | 60 s |
| `state` | `{}` | `{ready, rec_state, elapsed_s, transcribing, live, last_rec\|null, auto\|null}`: retrato para ressincronizar | — | 60 s |
| `config.get` | `{}` | `{config:{…com defaults e migração em memória}, output_dir_efetivo, lang_efetivo}` | — | 60 s |
| `config.set` | `{changes:{chave:valor}}` | o mesmo de `config.get`, depois de gravar e reler | — | 60 s |
| `devices.list` | `{}` | `{microphone:{devs:[{id,name}],console,comm}, speaker:{…}, selected:{mic_device,sys_device}, missing:{mic,sys}}` | — | 60 s |
| `devices.refresh` | `{}` | igual a `devices.list` (a enumeração já é fresca, F2-D11) | — | 60 s |
| `rec.start` | `{mode:"rec"\|"nota"}` | `{mic:{id,name,via}, sys:{id,name,via}, live, live_suprimido}`; `via:"ausente"` = o salvo sumiu e caiu no padrão | `state`, `level`, `timer`, `rec.error`, `live.text`, `live.warn` | 60 s |
| `rec.pause` | `{}` | `{elapsed_s}` | `state` | 60 s |
| `rec.resume` | `{}` | `{elapsed_s}` | `state` | 60 s |
| `rec.stop` | `{}` | `{path, duration_s, auto:null\|"final_pass"\|"nota"}` (estado `stopped`) | `state` | 30 s (drena o ao vivo) |
| `rec.set_gain` | `{mic?, sys?}` (0 a 10) | `{applied}`: só o gravador, sem gravar config (arrasto) | — | 60 s |
| `rec.conclude` | `{action}`: `save`, `delete`, `transcribe`, `transcribe_delete`, `final_pass`, `nota` | `save`: `{path}`; `delete`: `{path, deleted}`; `transcribe*`: `{txt, deleted}`; `final_pass`: `{txt, text}`; `nota`: `{md}` | `progress` (com `id`), `state` | 12 h com transcrição; 60 s em `save`/`delete` |
| `transcribe.file` | `{path}` | `{txt}` (`with_suffix(".txt")`, literal `(no content recognized)` se vazio) | `progress` | 12 h |
| `transcribe.cancel` | `{}` | `{found}`; o pedido em curso responde `cancelled` na fronteira do próximo grupo de VAD | — | 60 s |
| `library.list` | `{}` | `{folder, items:[{name, path, mtime, bytes, duration_s\|null, txt\|null, resumo\|null}]}` (mais novo primeiro) | — | 60 s |
| `library.search` | `{q}` | `{q, items}`: nome ou conteúdo do `.txt` (`x.txt` ou `x.mp3.txt`), `casefold` | — | 60 s |
| `library.delete` | `{path}` | `{path, deleted}`: só áudio da pasta da biblioteca, à Lixeira; `.txt` e `.resumo.md` ficam | — | 60 s |
| `convert.extract_mp3` | `{path}` | `{path, src_bytes, dst_bytes}` (MP3 16 kHz mono) | `progress` (`pct` inteiro, `text:null`) | 2 h |
| `resumo.ia` | `{path}` (o áudio) | `{path (.resumo.md), existia}`; `existia:true` = já havia, o casco abre | `progress` | 960 s |
| `model.update_check` | `{}` | `{}`; troca a pasta do modelo se houver revisão nova (ocupa o lugar da transcrição) | `progress` (`pct:null`) | 2 h |
| `app.update_check` | `{}` | `{tag, url}` ou `null`; o casco abre a URL | — | 60 s |

Notas por comando:

- `config.set` aceita só chaves de `_CFG_DEFAULTS` ou com o prefixo `casco_` (preferência do casco que
  o `reco.py` não conhece, F2-D16), senão `bad_args`. Relê o arquivo **cru**, faz merge (chave
  desconhecida do arquivo fica), grava e relê para conferir (`save_failed` se divergir). `language`
  muda o idioma do motor e é recusada com `busy` durante gravação ou transcrição; `mic_gain`/`sys_gain`
  vão também ao gravador ativo. A interface manda `rec.set_gain` no arrasto e `config.set` só ao soltar.
- `rec.start` recusa com `busy` fora de `idle` (inclusive `stopped`: concluir antes), e `nota` também
  com transcrição em curso. Dispositivos: resolvidos pelo config na hora (`no_device` se nenhum).
  Ao vivo liga se `config.live` e não há transcrição (`live_suprimido:true` se havia). `nota` grava só
  o mic, mono, prefixo `nota`/`note`, nunca ao vivo.
- `rec.stop` sem áudio capturado responde `no_audio` e volta a `idle`.
- `rec.conclude` age sobre o `last_rec` no estado `stopped` (`refused` em outro estado). Se a
  gravação sumiu do disco (ex.: `library.delete`), responde `not_found` e o estado vai a `idle`.
  `final_pass` mantém `stopped`, como o App: depois dele o casco ainda conclui com `save` ou `delete`.
  `transcribe`/`transcribe_delete` levam o estado a `idle` na hora e seguem longos; o áudio só sai
  depois do `.txt` salvo, e cancelado ou erro preserva o mp3. `nota` grava `<nome>.md` em `nota_dir`
  (ou na pasta de saída) e manda o mp3 à Lixeira; erro preserva o mp3.
- `transcribe.file`: `busy` se já há transcrição (um `pipe.generate` por vez); diarização e AEC só em
  gravação do Reco (etiqueta `reco` no nome) e conforme o config.
- `resumo.ia`: `claude -p <prompt> --model sonnet` (flag cravada) com a transcrição no stdin;
  `claude_missing` sem o `claude` no PATH (herdado do casco), `not_found` sem `.txt`, `busy` com outro
  resumo.

## Sequência de parar e concluir (F2-D12)

1. `rec.stop` → `{path, duration_s, auto}`; estado `stopped`.
2. `auto == "final_pass"` (ao vivo ligado no start) ou `"nota"` → o casco chama logo
   `rec.conclude {action: auto}` (longo, com `progress`). Se não chamar, nada se perde: o mp3 fica.
   `nota` termina em `idle`; `final_pass` termina em `stopped` e segue para o passo 3.
3. `auto == null` → a interface mostra as saídas; o clique padrão é `rec.conclude {action:"save"}`, e o
   casco copia `"<path>"` entre aspas duplas para o clipboard.

## Eventos globais (sem `id`)

- `ready` — `{import_s, has:{sc,np,av,ov}, lang, reco_version}` quando o `import reco` termina (ou
  `{import_s, error}` se falhou: aí todo comando que usa o `reco` responde `unavailable`). O `hello`
  seguinte diz `ready:true`. Comandos que chegam antes esperam o import (teto de 60 s).
- `state` — `{state: idle|recording|paused|stopping|stopped, elapsed_s}` a cada troca (o `state`
  do comando homônimo pode mostrar `starting` por milissegundos, durante o `rec.start`).
- `level` — `{mic: x|null, sys: y|null}` a cada 50 ms, só em `recording`: maior RMS da janela, já com o
  ganho (`null` = sem bloco do canal na janela).
- `timer` — `{elapsed_s}` uma vez por segundo enquanto grava (o tempo pausado não conta).
- `rec.error` — `{channel: mic|sys|save, detail, fatal}`; `fatal` (falha ao salvar ou todas as fontes
  mortas) descarta a gravação e volta a `idle`.
- `live.text` — `{channel: mic|sys, speaker: <rótulo traduzido>, text}`.
- `live.warn` — `{text}` (fila do ao vivo atrasada ou parada; a gravação continua).

Evento com `id`: `progress` — `{pct: n|null, text}`. Na transcrição o `pct` sai de
`tf("Transcrevendo… {p}%")` (teto 99, F2-D5); "Carregando áudio…" e a preparação do modelo vão com
`pct:null`.

## Códigos de erro

`bad_args`, `busy`, `cancelled`, `claude_missing`, `internal`, `no_audio`, `no_audio_stream`,
`no_device`, `not_found`, `refused` (regra: fora do estado certo, excluir fora da biblioteca, exclusão
negada), `save_failed`, `unavailable`. Lista em `engine/reco_engine/errors.py`.

## Contrato de falha entre processos (D11)

- **Casco morre gravando**: o stdin do motor fecha (EOF); o motor para, fecha o MP3 (o `close()`
  escreve o header com a duração) e só então sai. Mesmo caminho no `shutdown` no meio da gravação.
  Transcrição em andamento é cancelada (o `.txt` não nasce, como o app velho ao sair); o ao vivo para
  sem esperar. Tudo cabe nos 8 s que o casco dá antes de matar o processo.
- **Motor morre gravando**: o casco mostra alarme visível e nunca exibe "gravando" sem gravar; o
  reinício automático não religa gravação sozinho (Fase 3). Ao subir de novo, `state` ressincroniza.
- **Sair no meio da gravação**: o casco pede `rec.stop` (30 s) e espera o arquivo fechar antes de
  encerrar.

## O que fica no casco (F2-D9)

Clipboard (copiar o caminho entre aspas), abrir arquivo, pasta e URL, o mutex de instância única
`Local\Reco.SingleInstance` (D7), bandeja, atalho e o diálogo de escolher arquivo. O motor não cria
mutex nem janela.

## CLIs do motor

Sem servidor, sem mutex, saída por código (iguais às do `reco.py`, F2-D17):

- `reco-engine.exe --transcribe <áudio> [--diarize]` — grava `with_suffix(".txt")` com o texto (ou
  vazio); log em `%TEMP%\reco_transcribe_log.txt`, que termina em `OK -> <caminho>`; exit 0, ou 2 em
  erro; AEC só com `--diarize`. O stdout fica vazio.
- `reco-engine.exe --selftest` — grava em `%TEMP%\reco_selftest.txt` as 5 linhas (`frozen= lang=
  HAS_*`, `backend=`, `ov_devices=`, `resolved(AUTO)=`, `transcription_available=`) e sai com 0. Não
  carrega o pipeline.
- Enquanto o `dist\Reco` velho existir, `Reco.exe --transcribe` segue nele. O casco (Fase 3) repassa
  `--transcribe` ao motor; o `--selftest` se chama direto no motor.
