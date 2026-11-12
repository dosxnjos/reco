# Reco em Rust: Fase 3 — Casco Tauri e telas novas

> Índice: [2026-11-11-melhoria-reco-em-rust.md](2026-11-11-melhoria-reco-em-rust.md) · anterior: [fase-2](2026-11-11-melhoria-reco-em-rust-fase-2.md) · seguinte: [fase-4](2026-11-11-melhoria-reco-em-rust-fase-4.md) · Base: Reco `7c5c1a1` (2026-11-11)

## Por que esta fase

- É a fase que entrega o que o Gabriel pediu de verdade: janela bonita, que não pula, que abre e responde na hora.
- O motor Python da Fase 2 continua gravando, transcrevendo e cuidando do config; aqui nasce só o casco
  (Tauri 2 + Rust em `app/src-tauri`) e as telas (TypeScript + Vite sem framework em `app/ui`, D2).
- O molde é o Lacre (ponte com o motor) e a Guarita (bandeja e plugins); o visual vem da direção escolhida na Fase 1.
- O app velho (Tk) **continua sendo o que o Gabriel usa**: a troca é da Fase 4. Por isso o instalador desta
  fase nunca sobrescreve o atalho do Menu Iniciar nem o hotkey do app velho.

## O que ler antes

- Índice inteiro: `C:\Dev\Reco\roadmap\2026-11-11-melhoria-reco-em-rust.md` (D1–D12 e "O que NÃO fazer").
  D11 (contrato de falha entre processos) e D12 (régua do "rápido") valem aqui: passos 5, 8, 16 e 17.
- `C:\Dev\Reco\CLAUDE.md`, `C:\Dev\cerebro\projetos\reco.md`, `C:\Dev\Reco\docs\ARMADILHAS.md` (gerada).
- Evidência: `roadmap\2026-11-11-melhoria-reco-em-rust.d\diagnostico\` `1-mapa-do-reco-atual.md` (§ 1 é a lista de
  paridade), `3-lacre-como-molde.md`, `4-ecossistema-rust.md` § 4, `6-critica-de-completude.md` § 4.
- Saídas das fases anteriores (premissas até existirem):
  - Fase 0: relatório do spike da bandeja no sidecar `2026-11-11-melhoria-reco-em-rust.d/` (hover sem foco no Tauri).
  - Fase 1: `C:\Dev\Reco\design\DESIGN.md` (regras R1–R15, nomes de `data-area`, estados por tela e o condutor de
    estados `?tela=&estado=&tema=&texto=&versao=` com `window.vitrine.definir({...})`, F1-D12), `design\tokens.css`
    (janela de 400 × 560 px lógicos, F1-D1, nos tokens `--janela-largura`/`--janela-altura`), a vitrine e os testes
    `design/testar-anti-pulo.cjs` e `design/testar-contrato.cjs` (os dois com `--url` e o controle negativo `--sabotar`).
  - Fase 1, abas: Gravar, Biblioteca, Arquivo (uma origem, ações Transcrever e Converter para MP3, F1-D4) e Opções;
    gravando ou transcrevendo, a aba que conflita fica desabilitada com o motivo nela (F1-D7).
  - Fase 2: `C:\Dev\Reco\engine\reco_engine\` (servidor JSON Lines), `docs/PROTOCOL.md` (comandos, eventos, códigos,
    timeouts sugeridos), `tools/test_engine_protocol.py` e `engine/build.py` (onedir em `engine/dist/reco-engine/`).
- Molde Lacre (`C:\Dev\lacre`, `d06a2c4`): `src-tauri\src\engine.rs` (872 linhas), `lib.rs`, `commands.rs`,
  `build.rs`, `tauri.conf.json`, `capabilities\default.json`, `ui\src\backend.ts`, `ui\src\mock.ts`, `vite.config.ts`.
- Molde Guarita: `C:\Dev\albion\guarita\app\src-tauri\Cargo.toml` e `src\lib.rs:355-405` (bandeja), `:464-479` (fechar).
- Código do app velho que a fase espelha: `reco.py:3218-3303` (tela gravar), `:4066-4111` (salvar/copiar),
  `:4914-5086` (bandeja, hover, fechar), `:5197-5210` (mutex), `tray.py:150-236` (mensagens e menu).

## Contrato com o motor (nomes do md da Fase 2)

Os nomes abaixo vêm de `2026-11-11-melhoria-reco-em-rust-fase-2.md` (passos 2 a 13). A fonte de verdade é o
`docs/PROTOCOL.md` que a Fase 2 commitou: o passo 1 confere cada linha contra ele e anota aqui a divergência.

| tipo | nome (Fase 2) | o que a interface faz com ele |
| --- | --- | --- |
| comando | `hello` → `{engine_version, protocol, ready}`; `state` → `{ready, rec_state, elapsed_s, transcribing, live, last_rec}` | versão e retrato completo para ressincronizar depois de reinício (o comando `state` tem o mesmo nome do evento `state`) |
| evento | `ready {import_s, has, lang}` | até chegar, Gravar fica desabilitado com "Preparando…" (o `hello` responde `ready:false` antes) |
| comando | `rec.start {mode: rec\|nota}`, `rec.pause`, `rec.resume`, `rec.stop` → `{path, duration_s, auto}` | máquina de estados |
| comando | `rec.conclude {action: save\|delete\|transcribe\|transcribe_delete\|final_pass\|nota}` | saídas depois de parar; `save` → `{path}`, `nota` → `{md}`, transcrição → `{txt, deleted}` |
| comando | `rec.set_gain {mic?, sys?}` (muda o ganho ao vivo, sem gravar config) | ganho durante o arrasto |
| comando | `config.get`, `config.set {changes}` (merge; aceita chaves de `_CFG_DEFAULTS` e o prefixo `casco_`, F2-D16; aplica `mic_gain`/`sys_gain` no gravador ativo e grava no disco) | ganho ao soltar, Opções, preferências `casco_*` |
| comando | `devices.list`, `devices.refresh` | Opções (entrada e saída) |
| comando | `transcribe.file {path}` → `{txt}`, `transcribe.cancel {}` (sem id: um por vez) | aba Arquivo, ação Transcrever, e parar a transcrição |
| comando | `convert.extract_mp3 {path}` | aba Arquivo, ação Converter para MP3 (a Fase 2 não tem cancelar conversão) |
| comando | `library.list`, `library.search {q}`, `library.delete {path}`, `resumo.ia {path}` | aba Biblioteca |
| comando | `model.update_check`, `app.update_check` → `{tag, url}` ou `null` | o Rust chama os dois depois do primeiro `ready` (passo 5); aviso de versão; o casco abre a URL |
| evento | `state {state, elapsed_s}` (`idle\|recording\|paused\|stopping\|stopped`), `timer {elapsed_s}` 1/s | tela, cronômetro e dica da bandeja |
| evento | `level {mic, sys}` a cada 50 ms, só gravando (F2-D13) | VU |
| evento | `progress {id, pct\|null, text}` | barras de progresso; `text` já vem traduzido pelo motor (dívida da Fase 2) |
| evento | `live.text {channel, speaker, text}`, `live.warn {text}`, `rec.error {channel, detail, fatal}` | painel ao vivo e status |

- Não existem os eventos `status`, `nota_done` nem `transcribe_done`: o `.md` da nota e o `.txt` chegam como
  **resposta** de `rec.conclude`/`transcribe.file`. O status da tela sai de `state`, `rec.error`, dos códigos de
  erro (`bad_args`, `busy`, `cancelled`, `claude_missing`, `internal`, `no_audio`, `no_audio_stream`, `no_device`,
  `not_found`, `refused`, `save_failed`, `unavailable`) e dos textos do próprio casco.
- **Quem encadeia `rec.stop` → `auto` → `rec.conclude` (F2-D12): o Rust.** O casco expõe o comando `parar_gravacao`
  (passo 6), que pede `rec.stop` e, se `auto` vier preenchido, chama `rec.conclude {action: auto}` em seguida.
  - Retorno: a resposta do `rec.stop` (`{path, duration_s, auto}`), logo que ela chega; a conclusão segue em
    segundo plano no Rust.
  - O resultado da conclusão (ou o erro) vai à tela pelo evento do casco `reco-conclusao`
    `{action, ok, data|error}`, que a tela escuta. Assim a bandeja (passo 8) e a interface param pelo mesmo
    caminho, e a tela fica sabendo mesmo quando quem parou foi a bandeja.
  - Na resposta de `nota`, o Rust copia o `"<md>"` entre aspas (F3-D4).
  - Notificação com a janela escondida: o Rust olha toda resposta de `rec.conclude` e `transcribe.file` que passa
    por ele, inclusive as pedidas pela tela via `engine_request` (gancho no passo 6).
  - Sair (passo 5) para **sem** encadear: o mp3 fica, nada se perde (F2-D12).
- **`ready` pode se perder:** o motor sobe no `setup`, antes de a tela escutar, e de novo a cada reinício. A tela
  pede `hello` ao montar e a cada `engine-status` com `running: true`; o evento `ready` é só o atalho rápido.

### Conferido contra o `docs/PROTOCOL.md` real (passo 1, 11/11/2026, base `9fd4f95`)

`--conferir-doc` → 22 comandos no registro e na tabela (os 21 acima mais `shutdown`, reservado ao casco). Os nomes
batem; o que muda é forma de resposta e estado, e vale no lugar da tabela acima:

- `hello` → `{engine_version, reco_version|null, protocol:1, platform, ready, uptime_s}` (teto sugerido 10 s).
- `state` (comando) traz também `auto|null` e pode mostrar `starting` por milissegundos durante o `rec.start`;
  o evento `state` nunca mostra `starting`.
- `ready` → `{import_s, has:{sc,np,av,ov}, lang, reco_version}`, ou `{import_s, error}` se o `import reco` falhou
  (aí os comandos respondem `unavailable`): com `error`, o casco **não** pede as checagens de versão.
- `rec.start` → `{mic:{id,name,via}, sys:{…}, live, live_suprimido}`; `rec.pause`/`rec.resume` → `{elapsed_s}`.
- `rec.stop` pode responder `no_audio` (volta a `idle`) ou `refused` (fora de gravação); o Sair segue para o
  `shutdown` nos dois casos. Teto sugerido 30 s; o casco usa 120 s de folga (passo 4).
- `rec.conclude`: `delete` → `{path, deleted}`; `final_pass` → `{txt, text}` e **continua em `stopped`** (a tela
  ainda conclui com `save` ou `delete`); `nota` termina em `idle`. `parar_gravacao` não presume `idle` depois do auto.
- `rec.set_gain` → `{applied}` (0 a 10); `transcribe.cancel` → `{found}`.
- `config.get`/`config.set` → `{config:{…}, output_dir_efetivo, lang_efetivo}`: a preferência mora em
  `data.config.casco_atalho` (passo 10). `casco_*` aceita qualquer valor (sem validação de tipo no motor).
- **Preferências do casco (decisão do dono, 11/11 ~22:40):** `casco_atalho` (bool), `casco_tema`
  (`sistema|claro|escuro`) e **`casco_skin`** (`a|b|c`, padrão `a` = direção A "Fita"; B "Caderno" e C
  "Instrumento" ficam como skins em Opções, sem poda). A interface aplica `data-direcao="<skin>"` no `<html>`,
  igual ao condutor da vitrine. Todas gravadas pelo motor via `config.set` (prefixo `casco_`, F2-D16); o Rust só lê.
- `library.list` → `{folder, items:[{name, path, mtime, bytes, duration_s, txt, resumo}]}`; `library.search` →
  `{q, items}`; `library.delete` → `{path, deleted}`.
- `convert.extract_mp3` → `{path, src_bytes, dst_bytes}`, `progress` com `pct` inteiro e `text: null`.
- `resumo.ia` → `{path, existia}`; `model.update_check` → `{}` e pode responder `busy` (o casco engole).
- `rec.error.channel` é `mic|sys|save`. Códigos do próprio casco, fora da lista do motor: `timeout` (Router) e
  `hotkey_taken` (passo 10).
- Nenhum comando novo no motor foi preciso para os passos 2 a 10.

## Regras de execução desta fase

- Prova que sobe o app real exige o **app velho fechado** (mesmo mutex, D7): com ele aberto, o novo só faz
  a janela velha aparecer e sai. Por isso a maioria das provas é `cargo test`, build e Playwright no backend falso.
- **Fechar o app velho só pela bandeja (Sair) e só se ele não estiver gravando** (ícone vermelho = gravando:
  esperar o Gabriel parar). Nunca matar o processo: morto, o MP3 fica sem o cabeçalho de duração (`CLAUDE.md` § MP3).
- Comandos rodam de `C:\Dev\Reco` no Git Bash, salvo os marcados como PowerShell (`Get-Clipboard`, `Test-Path`,
  `reg query`, `Stop-Process`): esses rodam em `powershell -NoProfile -Command '...'` ou numa janela do PowerShell.
- `cargo test <filtro>` com filtro que não casa nada imprime `test result: ok. 0 passed`: toda prova de
  `cargo test` exige o número de testes passados indicado, e `0 passed` reprova.
- O `CARGO_TARGET_DIR` desta máquina é `C:\pt` (binário em `C:\pt\debug` e `C:\pt\release`, instalador em
  `C:\pt\release\bundle\nsis`, junto dos do Lacre: filtrar pelo nome).
- Nada aqui mexe em `reco.py` nem em `tray.py`; se mexer por engano, desfazer (5213 linhas, não cresce).
- Commit por pathspec a cada passo verde (`git add <caminhos do passo> && git commit`; se o passo 1 acrescentar comando
  ao motor, toca também `engine/`, `tools/test_engine_protocol.py` e `docs/PROTOCOL.md`), nunca `git add -A` nem `--no-verify`.
- **Deixar a máquina como achou** ao fim de todo passo manual: iniciar com o Windows desligado, app novo fechado
  pela bandeja (Sair) e app velho reaberto. Se o novo ficar no início do Windows, no boot seguinte ele pega o
  mutex e o velho não abre mais.
  - Antes do primeiro passo manual, copiar `~/.reco_config.json` para o sidecar da fase (fora do git); ao fim,
    restaurar a cópia se ganho, dispositivo, idioma ou pastas mudaram (as chaves `casco_*` podem ficar).
  - Gravações, notas e `.txt` de teste vão para a Lixeira ao fim: a biblioteca do Gabriel não ganha arquivo de teste.
- Playwright dos testes `.cjs`: `playwright-core` como devDependency de `app/`, com a mesma busca de
  `design/testar-anti-pulo.cjs` da Fase 1 (`PLAYWRIGHT_CORE`, `playwright-core`, `playwright`, por último o
  `playwright` global de `npm root -g`, que existe nesta máquina), e `chromium.launch()`.
  - O `playwright-core` não baixa navegador: usa o cache `%LOCALAPPDATA%\ms-playwright` (tinha chromium 1228, 1247
    e 1248 em 11/11/2026). Se reclamar de navegador ausente: `npx --prefix app playwright-core install chromium`.

## Fase 3 — Casco Tauri e telas novas

**Critério de aceite:**

- Com o app velho fechado, o Gabriel instala o app novo, grava uma conversa (microfone e som do PC), para e,
  com um clique, fica com o caminho do arquivo entre aspas pronto para colar.
  - Se a fase falhou: o arquivo não aparece na pasta, o colar sai vazio ou sem aspas, ou o clique não faz nada.
- Em nenhum clique, troca de tela, troca de idioma ou status comprido a janela muda de tamanho ou um botão sai do lugar.
  - Se a fase falhou: a janela cresce ou encolhe, ou o botão principal anda quando Gravar vira Parar.
- Pela bandeja: passar o mouse mostra a janela sem tirar o foco de onde ele digita, clicar fixa, o menu grava e
  para, o ícone fica vermelho gravando; e o app velho continua abrindo normal quando o novo está fechado.
  - Se a fase falhou: o hover rouba o foco, aparecem duas bandejas, ou o atalho de teclado do app velho (quando o
    Gabriel tem um ligado) some ou deixa de funcionar.
- Se a tela nova fecha de repente no meio de uma gravação, a gravação termina inteira; se o lado que grava cai, a
  tela e o ícone avisam na hora e nunca continuam dizendo "gravando".
  - Se a fase falhou: o arquivo sai truncado ou sem duração, ou o ícone segue vermelho sem nada gravando.

1. [ ] Fases 0 a 2 fechadas e contrato reconciliado com o `engine/` real — **prova:** `test -f docs/PROTOCOL.md && python tools/test_engine_protocol.py --conferir-doc && node design/testar-anti-pulo.cjs && test "$(grep -c data-direcao design/tokens.css)" = 0; echo "s=$?"` → `s=0`
   **reprova se:** `s` diferente de 0: falta o `PROTOCOL.md`, um teste falha ou sobra `data-direcao` nos tokens (direção visual não escolhida). Parar: a fase depende das três.
   - Anotar aqui a base da fase: `git rev-parse --short HEAD` antes do primeiro commit desta fase (o passo 18 usa).
     **Base: `9fd4f95`** (11/11/2026). Mecanismo do hover sem foco (Fase 0, D2 confirmada): modo `tao`,
     `focused(false)` + `focusable(false)` na criação, `show()`, e `set_focusable(true)` + `set_focus()` no clique
     que fixa. Prova rodada em 11/11: `s=1` só pelos 11 `data-direcao` (Fase 1 sem direção escolhida); os passos
     2 a 10 andaram mesmo assim (decisão técnica no relatório), sem tocar em interface.
   - Ler o relatório da Fase 0 no sidecar e anotar aqui qual mecanismo provou o hover sem foco. Se o relatório
     diz que a escolha do Tauri ficou **reaberta** (D2), parar e devolver ao índice: esta fase não começa.
   - Conferir a tabela "Contrato com o motor" contra o `docs/PROTOCOL.md` e anotar cada divergência nela.
   - Preferência do casco, sem mexer no motor: o `config.set` da Fase 2 já aceita qualquer chave com o prefixo
     `casco_` (F2-D16; o teste dela grava `casco_teste`). Esta fase usa só `casco_atalho` (bool) e `casco_tema`
     (`sistema|claro|escuro`); nenhuma lista nova no `config_cmd.py`. Conferir no `docs/PROTOCOL.md` que o prefixo vale.
     - O app velho preserva chave desconhecida ao ler e ao gravar o config (`reco.py:216-219`, `save_config` em `:234-244` grava o dict inteiro).
   - Outro comando que a interface precisa e o motor não tem: entra no `engine/` como sub-passo explícito deste
     passo (arquivo novo até 500 linhas, teste do motor, protocolo atualizado). Propagar rio abaixo: o
     backend falso (passo 11) e a tabela de paridade usam o nome novo.
   - Depois de mexer no motor: `python tools/test_engine_protocol.py` e `--conferir-doc` de novo, verdes.
2. [x] Trava de tamanho ver `.rs` e `.ts` (`tools/tamanho.json` e `files:` do hook) — **prova:** `grep -o '"\.rs"\|"\.ts"' tools/tamanho.json | wc -l` → `2` e `grep -A4 'id: trava-tamanho' .pre-commit-config.yaml | grep 'files:' | grep -E '[|(]rs[|)]' | grep -cE '[|(]ts[|)]'` → `1`
   **reprova se:** o primeiro dá `0` ou `1`, ou o segundo dá `0` (o hook continuaria cego para o casco).
   - Depois, `python C:/Dev/cerebro/scripts/gate_tamanho.py --config tools/tamanho.json --medir` → só `reco.py`
     acima de 500 (o gate só olha o que está no stage, então `pre-commit run --all-files` passaria vazio).
   - O gate decide "é código" só pela extensão (`gate_tamanho.py:78-79`): basta o json.
   - Motivo: hoje `extensoes` só tem `.py .js .mjs .cjs .ps1 .sh .cmd .bat` (`tools/tamanho.json`), então a regra
     de 500 linhas do D3 não alcançaria o casco. Mudança no json vai em **commit próprio** (regra do json).
   - No mesmo passo, `.gitignore` da raiz ganha `node_modules/` e `app/src-tauri/gen/` (commit separado do json).
     `dist/` e `build/` já valem para `app/ui/dist` e `engine/dist`.
3. [x] Esqueleto de `app/`: `package.json`, `vite.config.ts`, `tsconfig.json`, `ui/index.html`, `src-tauri/` (Cargo, `build.rs`, `tauri.conf.json`, capability, `main.rs`) — **prova:** `npm --prefix app run ui:build && cargo check --manifest-path app/src-tauri/Cargo.toml` → `Finished`
   **reprova se:** o `tauri-build` reclama da pasta de recurso do motor, do `frontendDist` ou de capability inválida.
   - Antes da prova: `npm --prefix app install`; o `app/package-lock.json` entra no commit (o `npm ci` do passo 16 depende dele).
   - O build da interface vem antes do `cargo check` porque o `generate_context!` procura `app/ui/dist` (premissa).
   - Molde: `package.json` e `vite.config.ts` do Lacre (`C:\Dev\lacre\vite.config.ts`), com `root: "ui"`, porta
     **1430** (o Lacre usa 1420) e `server.fs.allow: [searchForWorkspaceRoot(process.cwd()), "../../design"]`
     (o caminho relativo parte de `app/ui`; sem o primeiro item o Vite deixa de servir a própria pasta).
   - Scripts do `app/package.json`: `ui:build`, `i18n:check` (passo 11) e `ui:preview` (`vite preview --port 1431
     --strictPort`, serve `app/ui/dist` com o backend falso para os testes da Fase 1 no passo 14).
   - `Cargo.toml`: `name = "reco"`, lib `reco_lib`, `tauri` com feature `tray-icon`; plugins `log`, `dialog`,
     `opener`, `clipboard-manager`, `global-shortcut`, `autostart`, `notification`; `windows-sys` 0.59 (Foundation,
     **Security**, System_Threading, UI_WindowsAndMessaging, mais Graphics_Gdi e System_LibraryLoader para a janela
     do `Reco.Show`); release igual ao Lacre.
     - **Sem `positioner`** (execução, 11/11): a Fase 0 provou que o `TrayBottomCenter` põe a janela em cima da barra
       (pegadinha 3); o casco ancora pelo rect do ícone, como o spike e o `reco.py:4980-4997`.
     - A janela nasce com `focus: false` e `focusable: false` (modo `tao` provado na Fase 0) e `skipTaskbar: true`.
     - `tsconfig.json` só inclui `ui/src`: o `vite.config.ts` usa `process.cwd()` e o Vite o transpila sozinho
       (sem `@types/node`). O script `i18n:check` entra no passo 11, com o arquivo dele.
   - **Sem** `tauri-plugin-single-instance` e **sem** `tauri-plugin-store` (F3-D2, F3-D5).
   - **Caminhos um nível acima do Lacre:** lá o `src-tauri` fica na raiz do repo; aqui fica em `app/src-tauri`.
     - `build.rs`: cópia do Lacre (`C:\Dev\lacre\src-tauri\build.rs:8-38`) com
       `manifest.join("..").join("..").join("engine").join("dist").join("reco-engine")` e o exe `reco-engine.exe`.
     - `tauri.conf.json` `bundle.resources`: `{"../../engine/dist/reco-engine/": "engine/"}` (no Lacre, `:45-47`).
     - `frontendDist` continua `"../ui/dist"` (relativo a `app/src-tauri`), `devUrl` `http://localhost:1430`.
   - `tauri.conf.json`: `productName` **"Reco Novo"** (F3-D3), `identifier` `io.github.dosxnjos.reco`, janela
     `main` de **400 × 560** (F1-D1; se o `design/tokens.css` final disser outro número, vale o dos tokens),
     `resizable: false`, `decorations: false`, `visible: false` (o casco decide quando mostrar),
     NSIS `currentUser` em `PortugueseBR` e `English`, `targets: ["nsis"]`.
   - Capability: a do Lacre (`core:event:allow-listen`, `allow-unlisten`) mais `core:window:allow-start-dragging`
     para a barra de título própria. Nada de permissão de plugin para a webview: plugins rodam só do Rust.
4. [x] Ponte com o motor: copiar `engine.rs` do Lacre **dividido** em `app/src-tauri/src/motor/` (`router.rs`, `processo.rs`, `log.rs`, `prazos.rs`, `testes.rs`) — **prova:** `cargo test --manifest-path app/src-tauri/Cargo.toml motor` → `test result: ok`, 11 ou mais testes
   **reprova se:** algum teste do Router falha ou um arquivo de `motor/` passa de 500 linhas (`wc -l`).
   - De onde vem cada parte: Router `engine.rs:47-131`; Launch `:137-211`; processo, geração, backoff e shutdown
     `:217-523`; log com rotação de 2 MB e `truncate` `:542-591`; testes `:597-871`.
   - Trocar `eprintln!` por `log::info!`/`log::warn!` (lição do Lacre: sem plugin de log o casco some no release,
     `3-lacre-como-molde.md` § 1 Logs). Prefixo `[reco]`, nomes de thread `reco-motor-*`.
   - `Launch::dev` do Lacre roda `uv run ... python -m lacre_engine` (`engine.rs:154-157`). Aqui: programa `python`,
     argumentos `-m reco_engine`, diretório de trabalho `engine/` (como o teste da Fase 2 sobe o motor).
     `bundled_exe_name()` devolve `reco-engine(.exe)`.
   - O teste ignorado que sobe o motor real com `uv` (`engine.rs:744-767`) vira `motor_real_hello`, com `python`.
   - `prazos.rs` substitui `timeout_for` (`engine.rs:525-540`) com os timeouts sugeridos do `docs/PROTOCOL.md`:
     `transcribe.file` 12 h; `rec.conclude` 12 h se `action` é `transcribe`, `transcribe_delete`, `final_pass` ou
     `nota`, senão 60 s; `convert.extract_mp3` 2 h; `resumo.ia` 960 s; `rec.stop` 120 s (folga sobre os 30 s
     sugeridos: é o prazo que segura o Sair, D11); `model.update_check` 2 h (baixa o modelo novo quando há, `reco.py:1230-1266`;
     em 60 s o Router daria timeout no meio do download); resto 60 s. Teste de `prazo("rec.conclude", {action})`.
   - O teste ignorado `fake_engine_end_to_end` vem junto: `cargo test ... -- --ignored fake_engine` → `1 passed`.
5. [x] `lib.rs`: plugins, partida do motor, `engine.log`, **saída segura** que fecha a gravação antes do `shutdown` e checagem de versão após o `ready` — **prova:** `cargo test --manifest-path app/src-tauri/Cargo.toml -- --ignored sair_fecha_gravacao apos_ready_checa_versao` → `2 passed`
   **reprova se:** menos de `2 passed`, o motor falso registra `shutdown` antes de `rec.stop` com estado gravando, ou não recebe `model.update_check` e `app.update_check` depois do `ready`.
   - Molde `C:\Dev\lacre\src-tauri\src\lib.rs:25-85` (`resolve_launch` em `:25-41`). Debug: `python -m reco_engine`
     em `engine/` (passo 4); `RECO_ENGINE=<exe>` em debug roda o congelado; release usa o recurso `engine/`.
   - Sair (menu da bandeja e `RunEvent::ExitRequested`; o Lacre só trata `RunEvent::Exit`, `lib.rs:76-84`):
     pedir `state`; se gravando ou pausado, `rec.stop` e esperar a resposta (até 120 s) e só então
     `shutdown(8 s)`. O MP3 só fica com duração certa se o container fechar (`CLAUDE.md` § MP3); o velho faz
     o mesmo em `_quit` (`reco.py:5088`).
   - A lógica do Sair fica numa função do módulo `motor/` que recebe o motor (testável sem Tauri); o teste novo
     usa o mesmo motor falso do passo 4, com `state` respondendo `rec_state: recording`, e confere a ordem dos pedidos.
   - Motor caiu (D11): o evento `engine-status` com `running: false` com o último `state` em `recording`/`paused`
     faz o Rust pôr o ícone em idle, mostrar a notificação "A gravação foi interrompida" (também com a janela
     escondida) e a interface mostrar o aviso com "Abrir pasta". Nunca religar a gravação sozinho.
   - Reinício do motor: `running: true` depois de `false` faz a interface pedir `state` e se redesenhar.
   - **Execução (11/11):** `motor/saida.rs` (`sair_com_seguranca`, `PrimeiroReady`, `checar_versoes`). Conta como
     gravando `recording`, `paused` e `starting`; o `state` da saída tem prazo de 5 s (motor travado não segura o
     Sair). `ExitRequested` é barrado até a saída segura terminar; `RunEvent::Exit` ainda dá `shutdown` de rede.
     O primeiro `ready` também aplica a preferência do atalho (passo 10). `ready` com `error` não checa versão.
   - Checagens de versão (paridade com `_kick_update_checks`, `reco.py:2940-2949`, que roda 1,5 s depois de abrir):
     no primeiro `ready` do processo do casco (não a cada reinício do motor), esperar 1,5 s e pedir `model.update_check`
     e depois `app.update_check`, em segundo plano. Funciona com a janela escondida (F3-D4, F3-D15).
     - O `progress` do `model.update_check` vai ao status como qualquer progresso; o velho pula o modelo sem
       OpenVINO (`reco.py:2944`), e o motor responde o que couber.
     - Resposta `{tag, url}` do `app.update_check`: o Rust guarda e emite `reco-versao-nova {tag, url}`; a tela lê
       o guardado pelo comando `versao_nova` ao montar (o evento pode chegar antes de ela escutar). `null` não avisa nada.
     - O teste `apos_ready_checa_versao` usa o motor falso: emite `ready` e confere os dois pedidos, nessa ordem.
6. [x] Comandos do casco em `app/src-tauri/src/comandos/` (`motor.rs`, `arquivos.rs`, `janela.rs`) — **prova:** `cargo test --manifest-path app/src-tauri/Cargo.toml comandos -- --include-ignored` → `test result: ok`, 4 passed ou mais
   **reprova se:** `0 passed`, falta teste que recuse `file:`/`javascript:` e `.exe` e confira as aspas do caminho copiado, ou falta `parar_encadeia_auto`.
   - `engine_request` e `engine_status`: cópia de `commands.rs:16-58` (`shutdown` reservado ao casco), com um
     gancho: resposta de `rec.conclude`/`transcribe.file` com a janela escondida → notificação (passo 8).
   - `parar_gravacao`: `rec.stop` e, se `auto` vier preenchido, `rec.conclude {action: auto}` (ver "Contrato com o
     motor"); com `nota`, copia o `"<md>"`; emite `reco-conclusao`. O teste `parar_encadeia_auto` usa o motor
     falso (ignorado por precisar de `python`, como o do passo 5): `rec.stop` com `auto: "nota"` → confere o
     `rec.conclude {action: nota}` pedido em seguida.
   - **Sem** `get_settings`/`set_settings` do Lacre (`commands.rs:145-208`): config só pelo motor (D6).
   - `copy_path(path)`: grava `"<caminho>"` com o plugin de clipboard, como `_copiar_caminho` (`reco.py:4073-4080`).
   - `open_path`/`reveal_path`: plugin opener, só para arquivo de extensão conhecida (mp3, txt, md, áudio e vídeo
     de `reco.py:153-154`) ou pasta; recusa `.exe`, `.bat`, `.lnk` e afins (F3-D9).
   - `pick_file(kind)`/`pick_folder()`: plugin dialog com a janela como pai. `open_external`: cópia de
     `commands.rs:214-229` (só http/https). `window_hide`, `window_minimize`, `window_pin`.
   - **Execução (11/11):** também `definir_lingua(lingua)` (assíncrono: os setters da bandeja esperam a thread
     principal). `pick_file(kind)` aceita `audio` ou `midia`. `parar_encadeando` escreve o `rec.conclude` no motor
     antes de voltar (ordem garantida) e devolve a conclusão para o casco esperar em segundo plano.
   - `versao_nova()`: devolve o `{tag, url}` guardado pela checagem do passo 5, ou `null`.
7. [x] Em `app/src-tauri/src/instancia.rs`: repasse de `--transcribe` e mutex `Local\Reco.SingleInstance` antes do `Builder`, mensagem `Reco.Show` nos dois sentidos — **prova:** `cargo test --manifest-path app/src-tauri/Cargo.toml instancia` → `test result: ok`, 2 passed ou mais
   **reprova se:** menos de `2 passed`, o teste de dupla aquisição (nome `Local\Reco.Teste.<pid>`) não detecta a segunda, ou falta o teste de `repasse_cli`.
   - Repasse de `--transcribe` (D6, F3-D14), **antes** do mutex, como o velho (`reco.py:5148-5179` roda antes de `:5197-5210`):
     a função pura `repasse_cli(args)` devolve os argumentos quando há `--transcribe` (com `--diarize` e o resto
     intactos), senão nada. Com argumentos, o casco roda o motor congelado com eles, espera e sai com o código dele.
     - Sem janela, sem webview, sem bandeja e sem mutex; o processo filho com `CREATE_NO_WINDOW`. O log e o `.txt`
       são do motor (`cli.py` da Fase 2, passo 12): o casco não escreve nada.
     - Onde está o motor: em release, `engine/reco-engine.exe` ao lado do exe do casco (recurso do passo 3); em debug,
       `RECO_ENGINE=<exe>` ou `python -m reco_engine` em `engine/` (passo 5). Motor ausente → exit 2, como erro do velho.
     - Teste: `repasse_cli` com `["--transcribe", "a.mp3", "--diarize"]` devolve os três; sem a flag, nada.
     - A prova com o motor congelado de verdade fica no passo 17 (app instalado).
     - **Execução (11/11):** em debug, `RECO_SEM_MUTEX=1` pula o mutex (só para provar o casco com o app velho
       aberto; o release ignora a variável). Pegadinha: `CreateMutexW` no mesmo processo também devolve 183.
   - Igual ao velho (`reco.py:5197-5210`): `CreateMutexW`; se `GetLastError() == 183`, `PostMessageW(HWND_BROADCAST,
     RegisterWindowMessageW("Reco.Show"))` e sair com código 0.
   - Receber: janela de topo escondida (não message-only: essas não recebem broadcast) numa thread própria com
     laço de mensagens; ao chegar `Reco.Show`, `run_on_main_thread` mostra, foca e fixa (como `tray.py:189`).
     O velho faz igual: janela sem pai (`tray.py:136-137`, `CreateWindowExW(..., None, ...)`).
   - O plugin oficial não serve: o mutex dele se chama `<identifier>-sim`, fixo (`tauri-plugin-single-instance`
     2.5.5, `src/platform_impl/windows.rs:81-93`), por isso F3-D2.
   - Verificação manual (precisa de dois processos e da área de trabalho), com o app velho fechado no início:
     abrir o novo, rodar `dist\Reco\Reco.exe` → a janela nova aparece e o velho sai; o contrário também.
   - **Verificação manual feita (12/11, 00:09):** `python temp/fase3-manual/passo7.py` com o exe de debug, sem
     `RECO_SEM_MUTEX` → casco primeiro: velho sai com `0` e a janela do casco passa de escondida a visível (o
     broadcast chega à janela do Rust); velho primeiro: casco sai com `0` e a janela escondida do velho
     reaparece. Tempos (704 ms e 33 ms) só de referência: CPU da máquina entre 53% e 78%. Detalhe no relatório.
8. [x] Bandeja em `app/src-tauri/src/bandeja.rs`, dirigida pelo Rust a partir dos eventos do motor — **prova:** `cargo test --manifest-path app/src-tauri/Cargo.toml bandeja` → `test result: ok`, 2 passed ou mais
   **reprova se:** `0 passed`, ou os rótulos por estado diferem de `reco.py:4938-4952` (ex.: "Parar" oferecido em `stopping`/`stopped`).
   - Molde `C:\Dev\albion\guarita\app\src-tauri\src\lib.rs:355-405`. Ícones `logo/tray_idle.ico` e `tray_rec.ico`
     copiados para `app/src-tauri/icons/`; vermelho também pausado (`reco.py:5064-5066`).
   - Menu: Gravar/Parar, Pausar/Continuar (texto e habilitado mudam com o evento `state`), Abrir, Sair.
     Parar pela bandeja usa `parar_gravacao` (passo 6) e mostra a janela fixada, como `_tray_toggle_rec` (`reco.py:4954-4963`).
   - Dica: "Reco — gravando 00:12:34" a partir do evento `timer` (1/s); textos PT/EN numa tabela pequena no Rust
     (a interface informa o idioma efetivo por comando, como `definir_lingua` da Guarita, `lib.rs:349`).
   - Notificação (plugin) só com a janela escondida, em `rec.error`, motor caído gravando (passo 5) e transcrição
     pronta (resposta de `rec.conclude`/`transcribe.file`), como `_balloon_if_hidden` (`reco.py:3999-4003`).
   - Nota: o Rust copia o caminho do `.md` entre aspas na resposta de `rec.conclude {action: nota}`, mesmo com a
     janela escondida (`reco.py:4053`).
   - Fechar (X) esconde na bandeja e a gravação segue (`reco.py:5079-5086`; `on_window_event` da Guarita `:471-479`).
   - Testes cobrem as funções puras `rotulos(estado)` e `dica(estado, segundos)`.
   - **Execução (11/11):** `rotulos` devolve `None` em `starting`/`stopping`/`stopped` e o item fica desabilitado
     (o menu do Tauri não some item como o `tray.py`). Os setters de menu e ícone esperam a thread principal: a
     bandeja nunca os chama com uma trava do casco na mão (pegadinha registrada). Notificações em `avisos.rs`;
     reações aos eventos em `estado.rs` (puras, com teste do D11: motor caído gravando → alarme e `idle`).
     Evento do D11 para a tela: `reco-gravacao-interrompida`.
9. [x] Hover que mostra sem foco e clique que fixa, em `app/src-tauri/src/hover.rs` — **prova:** `cargo test --manifest-path app/src-tauri/Cargo.toml hover` → `test result: ok`, 3 passed ou mais
   **reprova se:** `0 passed`, ou `dentro_da_zona` falha para cursor parado sobre o ícone (o caso de `reco.py:5025-5028`), na borda de 6 px da janela ou fora das duas zonas.
   - Evento `TrayIconEvent::Enter`/`Move` com a janela escondida: posicionar acima do ícone (plugin positioner,
     preso à área de trabalho como `reco.py:4980-4997`) e mostrar **sem ativar**, pelo mecanismo da Fase 0
     (padrão se ela não disser outro: `ShowWindow(hwnd, SW_SHOWNOACTIVATE)`, como `tray.py:326-328`).
     - **Execução (11/11):** sem positioner; `posicao_ancorada` (função pura, testada) ancora pelo rect do ícone
       como o `reco.py`. Mecanismo da Fase 0: `show()` com `focusable(false)` e `always_on_top(true)` enquanto é
       espiada (o spike passou assim); ao fixar, `set_focusable(true)` + `set_focus()` e volta a janela comum.
   - Vigia: 500 ms de carência, depois a cada 120 ms; zona = janela ±6 px ∪ ícone ±4 px (`reco.py:5007-5044`);
     fora da zona e não fixada → esconde. Clique no ícone, foco na janela ou `window_pin` fixam (`reco.py:5054`).
     - **Execução:** foco na janela **não** fixa (pegadinha 5 da Fase 0: no modo `tao` o `Focused(true)` chega sem
       foco de verdade); a tela chama `window_pin` em todo clique dentro dela (passo 12).
   - Verificação manual da sensação (não dá para automatizar o foco de outro app): com o Bloco de Notas
     focado e digitando, passar o mouse no ícone → a janela aparece e o texto continua entrando no Bloco de Notas.
   - **Verificação manual feita (12/11, 00:11; repetida às 00:19 com a interface servida em `localhost:1430`):**
     `python temp/fase3-manual/passo9.py --vite` (ícone promovido só na entrada do exe do casco, desfeito no
     fim; hover por `SendInput` em passos) → o foreground e o
     `GetGUIThreadInfo` continuam no Bloco de Notas ao mostrar, com o cursor dentro da janela e depois que ela
     some; o arquivo salvo tem `antes durante dentro depois` (o texto digitado com a janela à vista entrou no
     Bloco de Notas). Controle: o clique no ícone fixa e toma o foreground. Detalhe no relatório da fase.
10. [x] Atalho global e iniciar com o Windows, os dois opt-in em Opções (`app/src-tauri/src/atalho.rs`) — **prova:** `cargo test --manifest-path app/src-tauri/Cargo.toml atalho` → `test result: ok`, 2 passed ou mais
   **reprova se:** `0 passed`, ou o teste aceita registrar o atalho quando `casco_atalho` lido é `false` ou ausente.
   - Os testes cobrem a função pura `deve_registrar(pref_atalho)` (ausente → não registra) e a leitura de
     `casco_atalho` do `config.get`.
   - Atalho: padrão Ctrl+Shift+R, desligado até ele ligar (paridade com o `.lnk` opt-in, `reco.py:4866-4912`).
     Mostra a janela com foco no botão principal (Enter grava). Falha ao registrar não derruba nada: Opções
     mostra o código `hotkey_taken`. A preferência fica no config pelo motor, chave `casco_atalho` (F3-D5, passo 1).
   - Iniciar com o Windows: plugin autostart com `.app_name("Reco Novo")` explícito e o argumento `--oculto`
     (nasce na bandeja). Sem `app_name`, o plugin usa o nome do pacote (`tauri-plugin-autostart` 2.7.0,
     `lib.rs:207-229`). O estado é lido do próprio Windows (`is_enabled`), sem gravar em lugar nenhum.
   - **Execução (11/11), comandos para a tela (passo 13):** `definir_atalho(ligar)` registra e grava `casco_atalho`
     pelo motor (ligar que falha devolve `hotkey_taken` e não grava), `atalho_registrado()`, `autostart_ligado()`
     e `definir_autostart(ligar)`. A preferência é lida de `data.config.casco_atalho` no primeiro `ready`.
     Evento `reco-atalho` ao apertar (a tela foca o botão principal).
   - Verificação manual em PowerShell (a barra de `/v` quebra no Git Bash), app novo aberto:
     ligar em Opções → `reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "Reco Novo"` acha a
     entrada; desligar → o mesmo comando responde que não encontrou. Sem ligar, ela nunca aparece.
   - O atalho global não tem prova por comando (precisa de tecla física com outro app em foco): verificação
     manual, com o Bloco de Notas focado, Ctrl+Shift+R → a janela aparece com foco no botão principal.
   - Ao terminar: iniciar com o Windows **desligado**, app novo fechado, app velho reaberto (regras de execução).
   - **Verificação manual feita (12/11, 00:12):** sem a tela de Opções, os comandos foram chamados pela webview
     real (CDP do WebView2, `temp/fase3-manual/passo10.py`) → antes de ligar, `reg query … /v "Reco Novo"` não
     acha e Ctrl+Shift+R com o Bloco de Notas focado não mostra nada; `definir_autostart(true)` → o `reg query`
     acha `C:\pt\debug\reco.exe --oculto`; `definir_atalho(true)` → `casco_atalho: true` no config e
     Ctrl+Shift+R mostra a janela com o foreground nela; desligados os dois → o `reg query` não acha, o atalho
     não responde. Pendente: "foco no botão principal" (não há botão até o passo 12); a sobra no
     `StartupApproved\Run` foi apagada à mão (pegadinha nova). Detalhe no relatório da fase.
11. [x] Base da interface em `app/ui/src/`: `backend.ts`, `mock.ts`, i18n por códigos e o padrão de componente — **prova:** `npm --prefix app run ui:build` → `built in` sem erro de tipo, e `npm --prefix app run i18n:check` → `0 faltando`
   **reprova se:** o build passa com `any` implícito ou existe código sem par PT/EN.
   - `backend.ts`: molde `C:\Dev\lacre\ui\src\backend.ts:1-73`, com os comandos do passo 6 no lugar dos do Lacre.
   - `mock.ts`: molde `C:\Dev\lacre\ui\src\mock.ts`; simula `level {mic, sys}` a cada 50 ms, `timer`, `state`,
     `ready` atrasado, `progress`, `live.text` e uma biblioteca de nomes inventados (repo público: nada de gravação
     real), mais `versao_nova` e `reco-versao-nova`.
   - Condutor de estados da Fase 1 (F1-D12) no backend falso: a página aceita `?tela=&estado=&tema=&texto=&versao=` e
     expõe `window.vitrine = { telas, estados, definir({tela, estado, tema, texto, versao}) }`, com os nomes de tela,
     estado e `data-area` do `design/DESIGN.md` (ler a seção "Condutor de estados" antes; sem `direcao`, podada na Fase 1).
     - Os cenários são estados do DESIGN.md (`motor-subindo`, `nota-gravando`, `erro`, `dispositivo-ausente`; texto longo
       por `texto=`). O que lá não existe (motor caído gravando, D11) entra como estado novo de Gravar no DESIGN.md e no mock.
     - Os testes `.cjs` desta fase usam o mesmo condutor; não há `?mock=`.
   - i18n: `i18n/pt.ts` e `i18n/en.ts` com chaves para os códigos de erro e os estados do protocolo e para os
     textos do casco; `i18n:check` (script ≤500 linhas) confere que todo código do protocolo e do mock tem PT e EN,
     como o `tools/check_i18n.py` faz no velho. O `text` de `progress` chega já traduzido pelo motor e é mostrado como vem.
   - Componente: monta os nós uma vez e expõe `atualizar(parte)` que só mexe em `textContent`, atributo ou
     classe. Proibido `replaceChildren` na raiz depois da montagem (`C:\Dev\lacre\ui\src\main.ts:158-171`).
   - CSS: `@import` de `design/tokens.css` e as regras do `DESIGN.md`; nenhum hexadecimal solto fora dos tokens.
   - **Execução (12/11):** a estrutura da janela mora no `ui/index.html` (áreas `data-area` da vitrine, textos por
     `data-t`); a tela é projeção de uma `Vista` (`tipos.ts`), redesenhada por `render/*.ts` só com texto, atributo e
     variável CSS. O condutor (`condutor.ts`) monta a Vista do cenário e expõe `window.vitrine` com `direcoes`
     (`casco_skin` vira `data-direcao` no `<html>`); ao assumir, congela o backend falso para nenhuma resposta
     atrasada mexer na Vista. `i18n:check` (`app/scripts/i18n-check.cjs`) também barra hexadecimal em `app/ui/src`.
     Desvio: o motor caído gravando (D11) usa o estado `erro` com título e saída próprios ("Abrir pasta"), sem estado
     novo no `DESIGN.md` (fora dos arquivos desta frente).
12. [ ] Tela Gravar completa, com áreas de altura reservada — **prova:** `node app/ui/tests/gravar.cjs` → `falhas 0`
   **reprova se:** algum fluxo do mock (gravar, pausar, continuar, parar, cada saída, nota) não chega ao estado esperado, ou a checagem de atualização pontual (abaixo) acusa nó criado.
   - O `gravar.cjs` também confere a atualização pontual: `MutationObserver` por 3 s gravando, com zero `childList` vindo
     do VU, até 4 mudanças de texto no cronômetro e a raiz com os mesmos filhos do início.
   - Conferido à parte, antes do commit: os dois testes da Fase 1 com `--url` (passo 14) seguem com 0.
   - Botões Gravar e **Nota** no mesmo lugar que Parar ocupa depois (absorve as Fases 2 e 3 de
     `roadmap/2026-08-13-melhoria-modo-nota-speech-to-ia.md`: botão, pasta de notas em Opções, i18n, teste real).
   - Até o motor dizer pronto (evento `ready` ou `hello` com `ready: true`, ver "Contrato com o motor"), Gravar e
     Nota ficam no lugar, desabilitados, com "Preparando…" no status (sem mudar tamanho).
   - A tela escuta `reco-conclusao` para mostrar o resultado da conclusão, mesmo quando quem parou foi a bandeja.
   - VU em `canvas` desenhado por `requestAnimationFrame` com o último `level` guardado; nenhum nó criado por evento.
   - Ganho por canal **sempre visível** ("1,0x", vírgula como `fmt_gain`, `reco.py:2763`): arrastar ou setas
     do teclado mudam o rótulo na hora e mandam `rec.set_gain {mic|sys}` no máximo a cada 150 ms (ao vivo, sem gravar
     config, como `_on_gain`, `reco.py:3206-3212`); ao soltar, uma vez só, `config.set {changes: {mic_gain|sys_gain}}`
     (o motor aplica e grava com `round(g, 4)`, como `_on_gain_release`, `reco.py:3214-3216`). Nunca `config.set` no arrasto.
     - Sem gravação ativa, a resposta do `rec.set_gain` não muda nada na tela: vale o rótulo, e o soltar grava.
     Porte de `gain_to_frac`/`frac_to_gain` (`reco.py:2748-2761`) com teste dos mesmos pontos (0, 0,5, 1, 5, 10).
   - Cronômetro com `tabular-nums`, atualizado pelo evento `timer`; status em 1 linha com reticências e o texto
     inteiro no `title`; barra de progresso e "Abrir transcrição" em espaço reservado mesmo vazios.
   - Parar chama `parar_gravacao` (passo 6), nunca `rec.stop` direto, para o `auto` (ao vivo, nota) ser encadeado.
   - Depois de parar (F3-D8): botão principal "Salvar e copiar caminho" (`rec.conclude save` + `copy_path`),
     Excluir, Reproduzir e "Mais" com as outras saídas num menu sobreposto, que não empurra nada.
   - Ao vivo: painel de altura fixa sempre presente na tela; desligado, mostra o aviso de rascunho desligado.
13. [ ] Abas Biblioteca, Arquivo e Opções ao lado de Gravar, em abas fixas (F1-D4, F1-D7, F3-D12), todas no mesmo tamanho de janela — **prova:** `node app/ui/tests/telas.cjs` → `falhas 0`
   **reprova se:** alguma ação da aba não chama o comando certo no mock, ou, gravando ou transcrevendo, a aba que conflita não fica desabilitada com o motivo visível nela.
   - Arquivo (F1-D4): uma origem escolhida (`pick_file`) e duas ações sobre ela.
     - Transcrever: `transcribe.file`, parar (`transcribe.cancel`), progresso, abrir `.txt`.
     - Converter para MP3: `convert.extract_mp3`, progresso, abrir pasta. Sem botão de parar: a Fase 2 não tem
       cancelar conversão (o velho também não tem).
   - Biblioteca: lista de altura fixa com rolagem interna, busca por nome e conteúdo, Reproduzir, Transcrever, Abrir
     txt, Resumo IA, Excluir (Lixeira, pelo motor), Abrir pasta. Duplo clique numa gravação toca (`open_path`), como
     o velho (`reco.py:4423`, `_lib_play` em `:4580`); o `telas.cjs` cobre o duplo clique.
   - Opções: entrada e saída (Auto console, Auto comunicação, manual) e atualizar, pasta de gravações, pasta de
     notas (`nota_dir`), Processar em, idioma, tema (F3-D7, chave `casco_tema`), ao vivo, atalho (`casco_atalho`),
     iniciar com o Windows, versão.
   - Navegação bloqueada (F1-D7): gravando, transcrevendo ou convertendo, a aba que conflita fica desabilitada com o
     motivo nela (ícone + texto, estado `durante-gravacao` do DESIGN.md); o velho só avisava no status (`reco.py:4308-4317`).
   - Conferido à parte, antes do commit: os dois testes da Fase 1 com `--url` (passo 14) seguem com 0.
14. [ ] Testes da Fase 1 na interface real, backend falso (F1-D12) — **prova:** `u=http://127.0.0.1:1431/; node design/testar-anti-pulo.cjs --url $u; echo "a=$?"; node design/testar-contrato.cjs --url $u; echo "c=$?"` → `anti-pulo: 0 diferenças em N medições`, `contrato: 0 falhas`, `a=0`, `c=0`
   **reprova se:** qualquer linha `FALHA`, diferença acima de 0 px, o teste não acha `window.vitrine.definir` (condutor ausente), ou o controle negativo (abaixo) sai com 0.
   - Antes da prova: `npm --prefix app run ui:build` e, em segundo plano, `npm --prefix app run ui:preview` (porta 1431,
     passo 3); parar o servidor ao fim do passo. Fora do Tauri, a interface usa o backend falso (passo 11).
   - Controle negativo, conferido à parte: `for t in anti-pulo contrato; do node design/testar-$t.cjs --url $u --sabotar >/dev/null; echo "$t=$?"; done` → `anti-pulo=1`, `contrato=1`.
   - Nenhum teste anti-pulo próprio em `app/ui/tests/`: os dois da Fase 1 já cobrem R1–R15 (caixas exatas por tela,
     estado, tema, texto PT/EN longo, escala e versão nova; contrato de clique, foco, transição, abas e hover).
   - Se a interface real precisar de algo que os testes da Fase 1 não aceitam (nome de área, estado novo), corrigir
     o DESIGN.md e o teste em commit próprio, com a vitrine ainda passando sem `--url`; nunca afrouxar a diferença 0.
   - A atualização pontual (VU sem criar nó, cronômetro) fica no `gravar.cjs` do passo 12.
15. [ ] Tabela de paridade (abaixo) vira verificação: cada linha "tela" tem `data-paridade="<id>"` no elemento — **prova:** `node app/ui/tests/paridade.cjs` → `17 de 17 presentes`
   **reprova se:** falta id (função do app velho sem tela no novo) ou sobra id que não está na tabela.
   - As 2 linhas "rust" (`bandeja`, `instancia`) não têm elemento na tela: a prova delas são os `cargo test` dos passos 7 a 9.
   - O script lê os ids da própria tabela deste md, para a tabela e o teste não divergirem.
16. [ ] `app/build.ps1`: congela o motor (Fase 2), smoke `hello`, `npm ci`, build da interface e `tauri build` — **prova:** `powershell -ExecutionPolicy Bypass -File app/build.ps1` → última linha `Instalador: ...\nsis\Reco Novo_<versão>_x64-setup.exe`
   **reprova se:** o script segue sem o motor congelado (o `build.rs` do release deveria parar) ou pega o instalador do Lacre.
   - Falha com mensagem clara se o motor não existir ou o smoke não responder; não copia o instalador para
     dentro do repo (ele fica em `C:\pt\release\bundle\nsis`, fora do git).
   - Medir e anotar no relatório da fase: tamanho do instalador e tempo do clique no ícone até a janela.
   - D12: anotar também o tempo até Gravar ficar habilitado (evento `ready`), ao lado do número do app velho
     medido na Fase 0. Pior que o velho não reprova esta fase (a régua fecha na Fase 4), mas vai ao relatório.
17. [ ] Teste real manual, app velho fechado: instalar, gravar 30 s com fala e vídeo, parar, clicar no principal — **prova:** `Get-Clipboard` → `.mp3` entre aspas; `ffprobe -v error -show_entries stream=channels,sample_rate:format=duration <arq>` → `2`, `16000`, duração do cronômetro ±1 s
   **reprova se:** o colar sai sem aspas, o arquivo tem 1 canal ou outra taxa, ou a duração difere mais de 1 s do cronômetro ao parar (sem o cabeçalho do container ela sai muito maior ou zero).
   - Manual porque precisa de microfone, som tocando e o Gabriel ou o executor na máquina.
   - **Antes de instalar**, anotar `Test-Path "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Reco.lnk"`
     (em 11/11/2026 dava `False`: o Gabriel não tinha o atalho ligado). Ao fim, o mesmo comando dá o mesmo valor.
     Se era `True`, o Ctrl+Shift+R com o novo fechado continua abrindo o velho.
   - No mesmo teste: Nota (o `.md` nasce na pasta de notas e o caminho vai para o colar), Transcrever a gravação
     (`x.txt` diarizado ao lado, nome igual ao do velho, D6), bandeja (passo 9), Sair gravando (arquivo fecha inteiro).
   - D11, casco morre gravando: achar os PIDs com `Get-CimInstance Win32_Process -Filter "Name='reco-engine.exe'" |
     Select ProcessId,ParentProcessId` (o pai é o casco; não matar pelo nome, que se confunde com o `Reco.exe`
     velho), `Stop-Process -Id <ParentProcessId>` → o motor sai sozinho e o `ffprobe` do arquivo dá a duração certa.
   - D11, motor morre gravando: numa gravação nova, `Stop-Process -Id <ProcessId do reco-engine.exe>` → a tela mostra
     o aviso, o ícone sai do vermelho e nunca segue "gravando". Esse arquivo pode ficar sem duração (motor morto
     não fecha o container): anotar no relatório e mandá-lo à Lixeira. Nunca rodar `tools/reparar_duracao.py`
     na pasta real de gravações; se quiser testar o conserto, numa pasta temporária só com a cópia desse arquivo.
   - Repasse de `--transcribe` (D6, passo 7), conferido à parte em PowerShell, numa cópia `a_reco.mp3` da gravação de
     teste numa pasta temporária: `$p = Start-Process -FilePath <exe do casco instalado> -ArgumentList '--transcribe',
     '<cópia>','--diarize' -Wait -PassThru; $p.ExitCode` → `0`, `a_reco.txt` ao lado e o fim de `$env:TEMP\reco_transcribe_log.txt` em `OK -> <caminho>`.
     - `Start-Process -Wait`, não `&`: o PowerShell não espera exe de interface gráfica. O exe do casco é o de
       `Get-ChildItem "$env:LOCALAPPDATA\Reco Novo" -Filter *.exe` (sem `-Recurse`: o `reco-engine.exe` mora em `engine\`).
     - Reprova o passo: exit diferente de 0, nenhum `.txt`, ou uma janela do app abre (o repasse deveria sair antes do `Builder`).
   - Ao fim: Sair do novo pela bandeja, conferir iniciar com o Windows desligado e reabrir o velho para o Gabriel.
18. [ ] Documentar e fechar — **prova:** `git diff --stat <base da fase anotada no passo 1> -- docs/ARQUITETURA.md README.md CLAUDE.md` → os três arquivos listados, e `pre-commit run gate-claude-md --files CLAUDE.md` → `Passed`
   **reprova se:** algum dos três não aparece no diff (a doc ficou para trás; vale também depois do commit), ou o gate acusa mais de 6 KB.
   - A base é o HEAD do início desta fase, não `7c5c1a1`: as Fases 1 e 2 também mexem nesses arquivos.
   - Armadilha nova (só se a execução achou uma) por `python tools/visoes.py novo "<título>"`; `docs/ARMADILHAS.md`
     é gerada e fica fora do git (`.gitignore:36`).
   - README: seção "App novo (em teste)" com como instalar e que ele exclui o velho. `docs/ARQUITETURA.md`: casco,
     módulos do Rust, contrato com o motor, anti-pulo. `CLAUDE.md` do projeto: 1 a 3 linhas (build do app novo em
     `app/build.ps1`; telas seguem o contrato anti-pulo do `design/DESIGN.md`).
   - Hub `cerebro/projetos/reco.md`: linha datada em "Estado agora". Relatório da fase no sidecar `.d/`.
   - Commit final por pathspec; push só autorizado.

## Tabela de paridade (relatório 1 § 1, 19 linhas)

| id | função do app velho | onde fica no novo | comando ou evento | prova |
| --- | --- | --- | --- | --- |
| janela | sem moldura, título arrastável, minimizar, fechar, fade | barra própria; fechar esconde (passos 3, 8) | `window_minimize`, `window_hide` | tela |
| vu-ganho | VU de mic e sistema, ganho 0× a 10× | Gravar, ganho sempre visível (passo 12) | `level`, `rec.set_gain` (arrasto), `config.set` (soltar) | tela |
| estados | Gravar, Parar, Pausar, Continuar, cronômetro, ponto | Gravar (passo 12) | `rec.*`, `parar_gravacao`, `state`, `timer` | tela |
| apos-parar | Salvar (copia caminho), Excluir, Reproduzir, 4 saídas | principal + Mais (passo 12) | `rec.conclude`, `copy_path`, `open_path` | tela |
| status | linha de status e "Abrir transcrição" | linha fixa e espaço reservado | `state`, `rec.error`, resposta `{txt}` | tela |
| parar-tr | parar a transcrição iniciada na tela gravar | Gravar, junto da barra de progresso | `transcribe.cancel` | tela |
| ao-vivo | painel de rascunho e passada final | painel fixo em Gravar | `live.text`, `live.warn`, `rec.conclude final_pass` | tela |
| nota | modo nota (sem botão hoje) | botão Nota e pasta de notas | `rec.start {mode: nota}`, `rec.conclude nota` | tela |
| opcoes | dispositivos, pasta, acelerador, idioma, tema, ao vivo, atalho | aba Opções (passo 13) | `devices.*`, `config.*` | tela |
| telas | Gravações, Converter, Transcrever por links, bloqueados gravando | abas fixas Gravar, Biblioteca, Arquivo e Opções; a que conflita fica desabilitada com o motivo (F1-D7) | — | tela |
| transcrever | escolher, transcrever, parar, status | aba Arquivo, ação Transcrever (F1-D4) | `pick_file`, `transcribe.file`, `transcribe.cancel`, `progress` | tela |
| biblioteca | busca, lista, tocar (botão e duplo clique), transcrever, txt, resumo, excluir, pasta | aba Biblioteca | `library.*`, `open_path`, `reveal_path` | tela |
| resumo-ia | `claude -p --model sonnet` gera `.resumo.md` | botão na aba Biblioteca | `resumo.ia` | tela |
| converter | vídeo para MP3 16 kHz mono 64k | aba Arquivo, ação Converter para MP3 (F1-D4) | `convert.extract_mp3`, `progress` | tela |
| bandeja | hover, clique fixa, menu, balão, ícone vermelho, X esconde | Rust (passos 8 e 9) | `state`, notificação | rust |
| atualizacoes | modelo se atualiza; aviso de versão nova (1,5 s depois de abrir) | o Rust checa depois do primeiro `ready` (passo 5); aviso em Opções e na barra de título | `model.update_check`, `app.update_check`, `versao_nova`, `open_external` | tela |
| i18n | PT/EN com a frase PT como chave | PT/EN por códigos; seletor em Opções | códigos de erro e estados | tela |
| atalho | `.lnk` com Ctrl+Shift+R | atalho global opt-in em Opções (passo 10) | plugin global-shortcut | tela |
| instancia | mutex `Reco.Show`; CLIs `--selftest`, `--transcribe` | mutex e repasse de `--transcribe` ao motor no casco (passo 7); `--selftest` direto no motor (`reco-engine.exe --selftest`, Fase 2) | — | rust |

Fica de fora da paridade, de propósito: a cor livre do tema (F3-D7).

## Decisões da fase

| id | decisão | motivo | confiança | reverte se |
| --- | --- | --- | --- | --- |
| F3-D1 | `engine.rs` do Lacre entra dividido em `motor/` (5 arquivos) | tem 872 linhas; a trava é 500 por arquivo novo | alta | a trava ganhar exceção registrada para Rust |
| F3-D2 | Mutex e `Reco.Show` por Win32 próprio, sem o plugin single-instance | D7 pede o nome `Local\Reco.SingleInstance`; o plugin 2.5.5 fixa `<identifier>-sim` (`windows.rs:81-93`) | alta | o plugin aceitar nome de mutex e mensagem própria |
| F3-D3 | Instalador da Fase 3 se chama "Reco Novo"; **a Fase 4 renomeia para "Reco"** na troca (`productName`, atalho, pasta, autostart) | não sobrescrever `Reco.lnk` com o hotkey do velho enquanto ele é o app de uso | média | o NSIS não usar o `productName` no atalho |
| F3-D4 | Bandeja, notificação e cópia do `.md` da nota no Rust | webview escondida tem timers estrangulados | alta | a Fase 0 mostrar que a webview escondida responde igual |
| F3-D5 | `casco_atalho` e `casco_tema` no config pelo motor, pelo prefixo `casco_` (F2-D16), sem lista própria | D6; o `config.set` aceita `casco_*`; o velho preserva chave nova (`reco.py:216-219`, `:234`) | média | F2-D16 reverter para arquivo próprio do casco, gravado pelo motor |
| F3-D6 | Atalho opt-in, Ctrl+Shift+R, só mostra; falha de registro não é fatal | paridade com o `.lnk`; o velho nunca criava sozinho | média | o Gabriel pedir atalho que já grava |
| F3-D7 | Tema segue o sistema, com escolha claro ou escuro; sem cor livre | design system da Fase 1 tem 2 temas; cor livre desencontrava os widgets | média | o Gabriel sentir falta na Fase 4 |
| F3-D8 | Saídas depois de parar visíveis (principal + Mais sobreposto), sem hover | ação escondida no hover era queixa do mapa (§ 4) | alta | o Gabriel preferir o hover depois de usar |
| F3-D9 | `open_path` só para extensões do Reco e pastas | a webview não pode abrir executável | alta | — |
| F3-D10 | `package.json` em `app/`, porta do Vite 1430 | não misturar com a raiz Python; o Lacre usa 1420 | alta | — |
| F3-D11 | Trava de tamanho passa a cobrir `.rs` e `.ts` | o D3 diz que vale e hoje não alcança | alta | a trava gerar falso positivo em arquivo gerado (aí `ignorar`) |
| F3-D12 | Abas fixas Gravar, Biblioteca, Arquivo e Opções (F1-D4) no lugar dos links; a que conflita com a gravação fica desabilitada com o motivo (F1-D7) | link de texto mudava a largura (`reco.py:3462`, `:4333`); a Fase 1 fixou as abas | alta | a Fase 1 desenhar outra navegação |
| F3-D13 | O Rust encadeia `rec.stop` → `auto` → `rec.conclude` (comando `parar_gravacao`) | bandeja e interface param pelo mesmo caminho; funciona com a janela escondida; a cópia do `.md` já é do Rust (F3-D4) | média | a Fase 2 mudar F2-D12 para o motor encadear sozinho |
| F3-D14 | O casco repassa `--transcribe` ao motor congelado antes do mutex e sai com o código dele (passo 7) | D6: quando o casco virar `Reco.exe` (Fase 4), quem chama `Reco.exe --transcribe` não quebra | média | o contrato virar `reco-engine.exe --transcribe` direto, no PROTOCOL.md |
| F3-D15 | Checagens de versão saem do Rust, uma vez por processo, 1,5 s depois do primeiro `ready` | paridade com `reco.py:2940-2949`; webview escondida tem timers estrangulados (F3-D4) | média | baixar o modelo no meio de uma gravação pesar (aí adiar para depois de parar) |

## Pendente (dono: gabriel)

- Nada bloqueia a execução. A direção visual é a da Fase 1 (já escolhida quando esta fase começa).
- Para a Fase 4 confirmar com ele, sem parar esta: F3-D7 (sem cor livre) e F3-D8 (saídas visíveis, sem hover).

## Premissas não verificadas

- Nomes do contrato: vêm do md da Fase 2 (planejado, não executado); o `docs/PROTOCOL.md` real vence e o passo 1 reconcilia.
- Resultado do spike da Fase 0: que o Tauri 2 entrega `TrayIconEvent::Enter`/`Move` no Windows e mostra sem foco.
- Que o NSIS do Tauri cria o atalho do Menu Iniciar com o `productName` (motivo do F3-D3); não abri o template.
- Que o `HWND_BROADCAST` chega a uma janela de topo escondida criada pelo Rust (é o que o `tray.py:136-137` faz em Python).
- Comportamento do hotkey de `.lnk` quando o novo registra o mesmo Ctrl+Shift+R; por isso o atalho é opt-in.
- Que o `generate_context!` do Tauri exige `app/ui/dist` existente no `cargo check` (por isso o passo 3 builda antes).
- Que `server.fs.allow` com `searchForWorkspaceRoot` é o necessário para o Vite servir `design/tokens.css` em dev.
- Conferido em 11/11/2026 (sai da lista): o plugin single-instance fixa o nome do mutex (`windows.rs:81-93`); o
  autostart usa `app_name` ou o nome do pacote (`lib.rs:207-229`); o gate de tamanho decide só pela extensão
  (`gate_tamanho.py:78-79`); a janela é 400 × 560 (F1-D1); o harness é `design/testar-anti-pulo.cjs`; `level` sai
  a cada 50 ms com os dois canais (F2-D13).

## O que esta fase NÃO faz

- Não substitui o app velho, não renomeia o instalador para "Reco" e não remove o `Reco.lnk` (Fase 4).
- Não mexe em `reco.py`, `tray.py`, `build.ps1` do velho nem em `tools/transcrever.py` (contratos do D6).
- Não troca o nome para `Reco.exe`: o repasse de `--transcribe` já existe no casco (passo 7, F3-D14), mas quem chama
  `Reco.exe --transcribe` segue no `dist\Reco` velho até a Fase 4 renomear (D6, F3-D3; Fase 4, P25).
- Não grava `~/.reco_config.json` pelo Rust; não passa áudio cru por JSON Lines nem por `emit`.
- Não porta captura, MP3 ou transcrição para Rust (Fases 5 e 6); não copia CSS, tokens nem a "Regra da Vida" do Lacre.
- Não publica release nem CI (a estrutura do CI do Lacre fica para quando houver release, Fase 4 ou 7).

## Gatilho que fecha

- Passos 1 a 18 marcados, com `cargo test` (incluindo os ignorados de motor falso), `ui:build`, `i18n:check`,
  `design/testar-anti-pulo.cjs --url` e `design/testar-contrato.cjs --url` com 0, `telas.cjs`, `gravar.cjs` e `paridade.cjs` verdes.
- Instalador gerado por `app/build.ps1` e o teste real do passo 17 feito, com o app velho reaberto e intacto.
- Relatório da fase no sidecar com tamanho do instalador, tempo até a janela e cada divergência do contrato.
- A Fase 4 começa com um app novo instalável que faz tudo da tabela de paridade.
