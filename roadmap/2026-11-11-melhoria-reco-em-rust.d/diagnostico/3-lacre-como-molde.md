# O Lacre como molde para um Reco em Tauri

Fonte: só leitura, nenhum arquivo foi editado. O caminho `C:\Dev\cerebro\projetos\marcas.md` não existe. A regra de marcas mora em `C:\Dev\cerebro\nomura\projetos\marcas.md`.

## 1. Arquitetura exata (lido)

**Três camadas.** A interface é TypeScript sem framework, com Vite. O casco é Rust com Tauri 2. O motor é Python, congelado com PyInstaller em modo onedir. O README.md:115-121 mostra o desenho. O motor emite códigos e parâmetros, e a interface traduz para pt-BR e en (docs/PROTOCOL.md:1-7).

**Interface → Rust (commands).** São 6 commands registrados em `src-tauri/src/lib.rs:66-73`: `engine_request`, `engine_status`, `save_text_file`, `get_settings`, `set_settings` e `open_external`.
- `engine_request(cmd, args, requestId?)` repassa qualquer comando do protocolo, menos `shutdown`, que é reservado ao casco (`commands.rs:16`, `commands.rs:25-53`).
- O timeout de cada comando é decidido no Rust (`engine.rs:526-540`). O `fdr` ganha mais 4 h, `read` 300 s, e o padrão é 60 s.
- Diálogo nativo de salvar, settings gravados de forma atômica (tmp seguido de rename) e abertura de URL só http/https ficam todos no Rust (`commands.rs:61-99`, `195-208`, `214-229`).
- A capability dá à webview apenas `core:event:allow-listen/unlisten`. Os plugins dialog e opener rodam só a partir do Rust (`capabilities/default.json`).

**Rust → interface (events).** Há dois eventos: `engine-event`, que repassa a linha JSON do motor sem mexer, e `engine-status` (`{running, mode}`), em `lib.rs:16-18` e `lib.rs:49-57`.
- O front usa `invoke` e `listen` por import dinâmico (`ui/src/backend.ts:39-51`).
- Fora do Tauri, carrega um backend falso que roda o fluxo inteiro num navegador comum (`backend.ts:35`, `backend.ts:70`; `ui/src/mock.ts`). Isso é bom para revisão visual.

**Rust → Python (sidecar próprio, não o `sidecar` do Tauri).** O motor é declarado como recurso do bundle: `"../engine/dist/lacre-engine/": "engine/"` (`tauri.conf.json:45-46`). O Rust o inicia com `std::process::Command` (`engine.rs:182-201`):
- stdin, stdout e stderr em pipe;
- variáveis `PYTHONUNBUFFERED`, `PYTHONIOENCODING=utf-8` e `PYTHONUTF8`;
- flag `CREATE_NO_WINDOW` no Windows.

**Protocolo.** JSON Lines, uma mensagem por linha:
- pedido: `{"v":1,"id","cmd","args"}`;
- resposta: `{"v":1,"id","ok","data"|"error":{code,detail}}`;
- evento: `{"v":1,"id","event",...}` (PROTOCOL.md:15-40).

O `Router` casa a resposta com o pedido pelo `id`, usando um `HashMap<id, oneshot>`. Linha com a chave `event` vira evento (`engine.rs:62-131`). O motor Python também separa canais: o stdout só leva protocolo, e `sys.stdout = sys.stderr` desvia qualquer `print` para o stderr (`engine/lacre_engine/server.py:324`). O motor roda cada comando numa task asyncio e tem um lock por aparelho (`server.py:46`, `90`, `108`).

**Ciclo de vida do motor.**
- **Partida:** o motor sobe no `setup` (`lib.rs:61-63`).
- **Três modos de rodar:** em debug, `uv run --project engine python -m lacre_engine`; em debug com `LACRE_ENGINE=<exe>`, o binário congelado; em release, o recurso empacotado (`lib.rs:25-41`).
- **Reinício:** se o motor morre, o Rust tenta de novo com backoff exponencial de 300 ms a 5 s, no máximo 5 vezes em 60 s. Um pedido novo reabre a chance (`engine.rs:235-238`, `401-438`, `466-471`).
- **Contador de geração:** cada spawn incrementa um número, para que a thread de leitura de um processo morto não sobrescreva o processo novo (`engine.rs:244`, `371-379`).
- **Saída:** no `RunEvent::Exit`, o Rust manda `shutdown`, fecha o stdin, espera até 8 s e então mata o processo (`lib.rs:82`, `engine.rs:492-522`).
- **Comunicação no Rust:** threads do sistema mais `tokio::oneshot` e `timeout`. Nenhum lock fica preso durante um `await` (`engine.rs:457-489`).

**Logs.**
- O stderr do motor é drenado numa thread. Isso é obrigatório, senão o pipe enche e trava o motor. O conteúdo vai para `app_log_dir/engine.log`, que gira em 2 MB para `.log.old` (`engine.rs:543-584`, `lib.rs:58-60`).
- O motor mascara identificadores do aparelho em toda linha de log (`server.py:308`, `326`).
- **Lido:** o próprio Rust só usa `eprintln!`, não há `tauri-plugin-log` no `Cargo.toml`, e o release usa `windows_subsystem = "windows"` (`main.rs:2`).
- **Suspeita forte:** por isso, os logs do casco se perdem no release. Daí "só o cabeçalho do Rust aparecia" (hub lacre.md).

## 2. Stack do front e design system

**Stack (lido).** Vite 7 e TypeScript 5.9, sem framework (`package.json`). O DOM é montado por um helper `h()` que usa só `textContent` (`ui/src/dom.ts:1-28`). As únicas dependências são `@tauri-apps/api` e `qrcode`. O build gera CSS e JS embutidos e não acessa a rede (`vite.config.ts:17-21`).

**Onde moram os tokens.** Depende da árvore:
- **`C:\Dev\lacre` (main):** não há pasta `design/` nem `docs/ARMADILHAS.md`. Os tokens são literais no `:root` de `ui/src/styles.css:3-36`, com o tema escuro em `@media (prefers-color-scheme: dark)` (`styles.css:38`).
- **Só nos PRs em rascunho #1 e #2** (worktrees `C:\Dev\lacre-wt-design` e `C:\Dev\lacre-wt-icones`) existem `design/tokens.css` (fonte única de cor, sombra e fonte, lida por `@import`), `design/DESIGN.md`, a vitrine, os ícones Lucide e a "Regra da Vida". O próprio `DESIGN.md` se declara "provisório, a confirmar pelo mantenedor".
- Espaço, raio e tamanho de letra continuam px literais (DESIGN.md § Migração).

**O que faz o Lacre parecer bom (lido, concreto):**
1. Uma só cor de ação (o teal `--seal`) mais um semáforo de três tokens por situação: texto, fundo e linha (ok, warn, alert, na).
2. Fontes do sistema (Segoe UI Variable Display e Text) com escala curta de 28, 19, 15 e 13 px e tracking negativo nos títulos.
3. Um único elemento "alto" por tela, o veredito. O resto é plano, com profundidade por camada de tom e contorno de 1 px. A sombra aparece só como resposta.
4. Raios que crescem com o tamanho do elemento: 10, 14, 16, 18, 22 e 999 px.
5. Topbar com `backdrop-filter` (`styles.css:102`).
6. Uma única animação de destaque, o carimbo do veredito (`styles.css:271`). Transições de 0,15 s e o bloco `prefers-reduced-motion` (`styles.css:417`).
7. Cor nunca é o único sinal: sempre há ícone ou texto junto.
8. Claro e escuro seguem o sistema.
9. Botões com 40 a 48 px de altura e `:focus-visible` de 3 px.

**Dívida medida e não corrigida (DESIGN.md).** Alvos de toque abaixo de 44 px. `--ink-3` no tema claro mede 3,24:1.

## 3. Empacotamento (lido)

- **Motor:** `engine/build.py` roda PyInstaller com `--onedir`, `--console` (escondido pelo `CREATE_NO_WINDOW`), `--collect-all pymobiledevice3` e exclusões (`build.py:24`, `38`, `47`). Tem também um smoke test (`--smoke`) que mede o tempo até o `hello`. O onedir foi escolhido porque o onefile levava 17 s para abrir (roadmap/2026-11-09-lacre-app.md:16-17).
- **`build.rs`:** falha no release se o motor congelado não existir. Em debug, cria a pasta vazia para o `cargo check` passar.
- **Tamanhos medidos aqui:**

  | Artefato | Tamanho |
  | --- | --- |
  | `engine/dist/lacre-engine` | 71 MB |
  | `lacre.exe` | 3,5 MB |
  | Instalador NSIS (`C:\pt\release\bundle\nsis`) | 30,6 MB |
  | Instalador da Guarita (Tauri sem Python) | 2,6 MB |

  A comparação com a Guarita mostra o custo do Python.
- **Instaladores:** NSIS `currentUser` em pt-BR e en, mais MSI (`tauri.conf.json:50`, `tauri.windows.conf.json`). No Mac, `app` e `dmg` com assinatura ad-hoc `"-"` (`tauri.macos.conf.json:4-6`). No Linux, deb (com dependência de `usbmuxd`) e AppImage.
- **CI** (`.github/workflows/build.yml`), disparado por tag `v*`:
  - um job `release` cria o rascunho uma vez e recusa tag diferente da versão;
  - uma matriz monta Windows, mac-arm, mac-intel (`macos-15-intel`, linha 120) e ubuntu-22.04;
  - cada job faz o smoke `hello` do motor congelado (252), roda `tauri-action@v0` (271) e copia os arquivos para nomes fixos;
  - no Windows sai um zip portátil (331); no Linux, o motor é conferido dentro do deb e do AppImage (358);
  - o job `verify` confere os 6 arquivos.
- **Assinatura:** nenhuma no Windows, ad-hoc no Mac, sem notarização. CSP `null` (`tauri.conf.json:27`).
- **Auto-update:** não existe (sem `tauri-plugin-updater`).

## 4. Armadilhas que o Lacre já pagou e o Reco herdaria

- **Pipe do stderr precisa ser drenado**, senão o motor trava (`engine.rs:315`).
- **stdout só para protocolo.** Qualquer `print` de biblioteca quebra o parse. Por isso o desvio para o stderr.
- **Encoding UTF-8 explícito e unbuffered** nas variáveis de ambiente.
- **Janela de console:** precisa de `CREATE_NO_WINDOW` (`engine.rs:194-199`).
- **Thread de leitura velha** derrubando o processo novo: resolvido com o contador de geração.
- **Tempo de abertura do PyInstaller:** onefile levou 17 s. A solução foi onedir mais `_warm_imports` em segundo plano (`server.py:222`).
- **`tauri-build` exige a pasta do recurso**, o que bloqueava o `cargo check` (`build.rs`).
- **Windows sem assinatura:** SmartScreen, Smart App Control bloqueando sem botão "Executar assim mesmo", e o Defender acusando o PyInstaller (docs/LIMITATIONS.md § Platforms).
- **AppImage:** o strip estraga o PyInstaller, por isso `NO_STRIP: "true"` (`build.yml:276`).
- **Mac Intel:** cryptography fixada em 48.0.1, mais checagem do macOS mínimo de cada Mach-O (`engine/pyproject.toml:18-19`, `build.yml:206-249`).
- **CI:** o `tauri-action` substitui assets de release já publicado. O rascunho só aparece com a conta `dosxnjos` no `gh` (hub lacre.md).
- **`CARGO_TARGET_DIR` desta máquina é `C:\pt`** (hub).
- **Movimento:** o bloco `reduce` só zera durações, então um `transform` fora de `no-preference` continua saltando (ARMADILHAS do worktree de ícones).

## 5. O que serve literalmente como template e o que não serve

**Copiável quase literalmente:**
- `engine.rs` inteiro (Router, Launch dev/bundled, reinício, shutdown, log com rotação), já desacoplado do Tauri e com testes (`engine.rs:597+`);
- o esqueleto de `lib.rs`, `commands.rs` (settings, salvar, open_external) e a capability mínima;
- `build.rs`, o padrão `build.py` + smoke e a estrutura do CI (release, matriz, verify, nomes fixos, zip portátil);
- `backend.ts` com o backend falso para revisar a interface no navegador;
- o i18n por códigos;
- o ritual de vitrine e testes Playwright do PR #1.

**Não serve, ou falta (lido):**
- **Sem bandeja, single-instance, atalho global, window-state, autostart ou updater.** O `tauri` está com `features = []`. A referência da casa para isso é a Guarita: `C:\Dev\albion\guarita\app\src-tauri\Cargo.toml` (`tray-icon`, `single-instance`, `global-shortcut`, `window-state`, `autostart`, `plugin-log`, `notification`, `store`) e `src/lib.rs:355-396` (bandeja, fechar para a bandeja).
- **O modelo de render da interface não serve.** Ligação com a queixa do Gabriel: `render()` reconstrói a árvore inteira com `replaceChildren` e devolve scroll e foco à mão (`ui/src/main.ts:158-171`). O Lacre já precisou de remendos: `patchCheck` (`views/tests.ts:86`), o banner `fdr-lost` (`main.ts:202-207`) e `patchFdrClock` (`main.ts:173`).
  - Leitura: o Lacre é estável porque muda pouco, não porque tenha um mecanismo contra pulo de layout.
  - Suspeita: um Reco com medidor de nível, cronômetro e transcrição ao vivo voltaria a "se mexer" se copiasse esse modelo. Precisa de atualização pontual por componente, layout de dimensões fixas e números `tabular-nums`.
- **A "Regra da Vida"** (botão sobe 1 px no hover e afunda com `scale(0.98)` no clique) é movimento intencional. **Suspeita:** pode ser exatamente o que o Gabriel chama de "ficar se mexendo". Precisa ser validado com ele antes de herdar.
- **Sem áudio em tempo real.** Os eventos do Lacre são raros (etapas). **Suspeita, não medido:** medidor de áudio em JSON Lines a 10-30 Hz por `emit` funciona, mas áudio bruto não deve passar por esse canal. A captura WASAPI poderia ir para Rust, como a Guarita já faz com a captura de rede em thread própria.
- **Suspeita, não medida:** OpenVINO GenAI congelado deve deixar o instalador bem maior que 30 MB, e um PyInstaller maior tende a ser acusado mais vezes pelo Defender.

## 6. Regra da casa: design system não se compartilha

Lido em `cerebro/nomura/projetos/marcas.md:37-40`: "design system nunca se compartilha entre produtos (identidade própria por produto) [...] nunca CSS de outro produto". Linha correspondente no `C:\Dev\CLAUDE.md`: "Design system nunca se compartilha entre produtos".

O que isso implica:
- O Reco **não importa nem copia** o `tokens.css` nem o `styles.css` do Lacre: nada do teal `--seal`, nada do selo, nada da paleta de semáforo como identidade.
- Pode herdar o **método**: arquivo de tokens como fonte única, a estrutura do `DESIGN.md` (frontmatter, regras nomeadas), a vitrine com cobertura de classes, os testes de movimento e de vitrine, o padrão "cor nunca é o único sinal" e o Lucide como biblioteca de ícones (é um pacote de terceiros, não identidade).
- O Reco é pessoal, não Nomura, então a obrigação de herdar a paleta do Grupo não se aplica.
- O Reco ganha pasta `design/` própria, com North Star, cor de ação e tipografia próprias, aprovadas pelo Gabriel. Nada de "Lacre 2".

**Contigo:** nada nesta fase. Duas decisões vão chegar na proposta de interface: se o botão deve se mexer no clique (a regra do Lacre faz isso) e qual identidade visual o Reco terá.