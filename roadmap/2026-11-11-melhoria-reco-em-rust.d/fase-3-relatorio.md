## Relatório de execução — Fase 3 (2026-11-11, sessão 4c65eb01)

> **Fase 3 fechada (12/11/2026, ~16h): os 18 passos marcados.** O relatório cresceu por rodadas, nesta ordem:
> passos 2 a 10 (casco Rust, 11/11); 11 a 16 (interface e instalador, madrugada de 12/11); revisão adversarial
> (~12:30); passo 17, o teste real no instalador do `aac7ca7` (11:50 a 12:22); a correção dos 5 defeitos dele (tarde);
> a revisão adversarial desses consertos e o fechamento (passos 1 e 18), na seção "Revisão adversarial dos consertos
> e fechamento", no fim. As frases "fica para o 17" e "aberto" das seções mais antigas são do momento em que foram
> escritas; o que ainda não foi provado no app instalado está em "Fechamento", com dono na Fase 4.

Fase: [fase-3](../2026-11-11-melhoria-reco-em-rust-fase-3.md) · índice: [Reco em Rust](../2026-11-11-melhoria-reco-em-rust.md).

- **Base da fase:** `9fd4f95` (`git rev-parse --short HEAD` antes do primeiro commit; anotada no passo 1 do md).
- **Condição:** o chamador avisou que o Reco do dono estava aberto (mutex `Local\Reco.SingleInstance`). Nenhuma
  prova abriu, fechou ou mandou mensagem a ele. **O app velho não estava rodando quando olhei** (23:18 e 23:22,
  `Get-CimInstance Win32_Process` com nome `like '%reco%'`: às 23:18 só o `reco.exe` de teste, às 23:22 nenhum);
  não sei desde quando. Não o reabri nem rodei as provas de app fechado: é decisão do chamador.
- **Toolchain:** rustc/cargo 1.96.1, node 24.15, npm 11.12; `CARGO_TARGET_DIR=C:\pt` (nada de `target/` no repo).

### Passos

| passo | estado | prova (comando → o que veio) |
| --- | --- | --- |
| 1 contrato | [x] (12/11, no fechamento) | prova inteira em 11/11 → `OK doc: 22 comandos…`, `anti-pulo: 0 diferenças em 23868 medições`, `s=1` (11 `data-direcao` nos tokens, que são as skins B e C mantidas pelo dono). Prova trocada no md ("a skin padrão é a A") e rodada no fechamento → `s=0` |
| 2 trava `.rs`/`.ts` | [x] | `grep -o … tools/tamanho.json \| wc -l` → `2`; `grep -A4 'id: trava-tamanho' … \| grep -cE '[\|(]ts[\|)]'` → `1`; `gate_tamanho.py --medir` → `5213 reco.py`, `1 arquivo(s) de código acima de 500 linhas` |
| 3 esqueleto | [x] | `npm --prefix app run ui:build` → `✓ built in 66ms`; `cargo check --manifest-path app/src-tauri/Cargo.toml` → `Finished dev profile … in 54.99s` |
| 4 ponte | [x] | `cargo test … motor` → `test result: ok. 13 passed; … 2 ignored` (17 depois do passo 5); `-- --ignored fake_engine` → `1 passed`; `-- --ignored motor_real_hello` → `1 passed` (motor real do fonte, só `hello`+`shutdown`); `wc -l motor/*.rs` → maior 391 |
| 5 lib.rs | [x] | `cargo test … -- --ignored sair_fecha_gravacao apos_ready_checa_versao` → `test motor::saida::testes::sair_fecha_gravacao ... ok`, `…apos_ready_checa_versao ... ok`, `test result: ok. 2 passed` |
| 6 comandos | [x] | `cargo test … comandos -- --include-ignored` → `test result: ok. 5 passed` (aspas, `.exe`/`.bat`/`.lnk` recusados, `file:`/`javascript:` recusados, `parar_encadeia_auto`, serialização da conclusão) |
| 7 instância | [x] | `cargo test … instancia` → `repasse_cli_so_com_transcribe ... ok`, `mutex_detecta_a_segunda_aquisicao ... ok`, `test result: ok. 2 passed` |
| 8 bandeja | [x] | `cargo test … bandeja` → `test result: ok. 3 passed` (rótulos por estado, dica com cronômetro, ícone vermelho gravando e pausado) |
| 9 hover | [x] | `cargo test … hover` → `test result: ok. 4 passed` (cursor parado no ícone, borda de 6 px, fora das zonas, âncora presa à área) |
| 10 atalho | [x] | `cargo test … atalho` → `test result: ok. 3 passed` (`deve_registrar` só com `true`; leitura de `data.config.casco_atalho`; Ctrl+Shift+R) |

Rodada inteira no fim: `cargo test … -- --include-ignored` → `test result: ok. 40 passed; 0 failed`;
`cargo clippy --all-targets` → 0 avisos. Cada `cargo test` imprime também duas linhas `ok. 0 passed` (bin e
doctests); a régua é a linha da lib (pegadinha nova abaixo).

**Provas que reprovam (controle negativo):**

- `sair_fecha_gravacao` com a saída mutada para mandar o `rec.stop` sem esperar a resposta (cópia restaurada
  em seguida, `git diff` vazio) → `FAILED`, `left: ["state", "rec.stop", "shutdown", "rec.stop:respondido"]`.
  O motor falso anota o momento da resposta do `rec.stop` justamente para o teste ver a ordem real.
- `ancora_acima_do_icone_e_presa_na_area` falhou duas vezes na escrita por conta errada **minha** no valor
  esperado (a margem de 4 px da área vence o "8 px acima do ícone" quando o ícone fica na barra); a função
  estava certa e o teste ganhou um caso folgado.

**Fumaça do casco (fora do md, sem tocar o app do dono):** `RECO_SEM_MUTEX=1 RECO_ENGINE=C:\nao-existe\…
C:\pt\debug\reco.exe --oculto` → `[reco] casco pronto (oculto=true)`, bandeja montada, motor tentando 5 vezes com
backoff e `o motor continua caindo; desisto até o próximo pedido`. Encerrado por `Stop-Process -Id <pid do
teste>` (conferido pelo `ExecutablePath`). Motor inexistente de propósito: com o real, o primeiro `ready`
dispararia `config.get` e `model.update_check` (que pode trocar a pasta do modelo).

### Contrato reconciliado (passo 1)

A seção "Conferido contra o `docs/PROTOCOL.md` real" do md da Fase 3 lista tudo. Os nomes batem (22 comandos);
mudam formas de resposta: `config.get` aninha em `{config:{…}}` (o atalho lê `data.config.casco_atalho`), `state`
traz `auto` e pode mostrar `starting`, `ready` pode vir com `error`, `final_pass` continua em `stopped`,
`rec.stop` pode dar `no_audio`/`refused`. Nenhum comando novo no motor. Pela decisão do dono (~22:40), entrou
`casco_skin` (`a|b|c`, padrão `a`) ao lado de `casco_atalho` e `casco_tema`; a interface aplica
`data-direcao="<skin>"` no `<html>` (passos 11+).

### Decisões técnicas — Fase 3

| decisão | motivo | confiança | o que reverteria |
| --- | --- | --- | --- |
| Passos 2 a 10 andaram com as Fases 0 e 1 abertas (Bloco B da Fase 0 e escolha visual) | o casco Rust não depende de direção visual nem das medidas do Bloco B; a D2 já estava confirmada pelo spike | alta | o Bloco B mostrar algo que mude a bandeja ou o hover (aí reabrir 8 e 9) |
| Sem `tauri-plugin-positioner`; âncora pelo rect do ícone (`hover::posicao_ancorada`) | pegadinha 3 da Fase 0: `TrayBottomCenter` põe a janela em cima da barra | alta | o plugin corrigir a conta no Windows |
| Janela nasce `focus:false`, `focusable:false`, `skipTaskbar:true`; `always_on_top` só enquanto é espiada | modo `tao` provado na Fase 0; o spike passou com `always_on_top(true)`; fixada vira janela comum (o velho só faz `lift()`) | média | o teste manual mostrar a janela atrás de outra ou a falta dela na barra de tarefas incomodar |
| Foco na janela **não** fixa; a tela chama `window_pin` em todo clique | pegadinha 5 da Fase 0 (`Focused(true)` falso no modo `tao`) | alta | — |
| Reações aos eventos do motor em `estado.rs` (funções puras) e ações executadas no `lib.rs` | o D11 (motor caído gravando → alarme e `idle`) fica testável sem Tauri | alta | — |
| Saída conta `starting` como gravando; `state` da saída com prazo de 5 s | o motor fecha o arquivo que nasce durante o start (F2 `_claim_exit`); motor travado não pode segurar o Sair 60 s | média | o motor responder `refused` a `rec.stop` em `starting` com frequência (aí só `shutdown`) |
| `Engine::send` + `Engine::wait` (além de `request`) | `parar_gravacao` precisa escrever o `rec.conclude` antes de voltar, para a ordem ser garantida | alta | — |
| Primeiro `ready` também aplica a preferência do atalho (`config.get`) | a preferência mora no motor (D6) e só dá para ler depois dele de pé | alta | — |
| `RECO_SEM_MUTEX=1` só em debug | o chamador pediu para provar o casco sem fechar o app velho; o release ignora (D7 intacta) | alta | — |
| Setters da bandeja nunca chamados com trava do casco na mão; `definir_lingua` assíncrono | os setters do Tauri esperam a thread principal (`run_item_main_thread`): trava na mão vira deadlock | alta | — |
| Rótulo sem ação = item desabilitado (o `tray.py` omitia o item) | o menu do Tauri troca texto e habilitado sem remontar | média | o Gabriel estranhar o item cinza |
| `window_pin` (clique dentro da janela do hover) também dá `set_focus()` na primeira vez | com `focusable(false)` o clique não ativa a janela; sem isso ela fixaria sem foco de teclado | média | o teste manual mostrar que o foco roubado no clique incomoda (aí só fixar) |

### Verificações manuais dos passos 7, 9 e 10 (12/11/2026, 00:08 a 00:15, mesma sessão)

Condição: o Reco do dono fechado desde ~23:18 de 11/11 (Sair pela bandeja); antes de cada prova, a guarda
(`Get-CimInstance Win32_Process`, por **caminho** do exe, porque o casco e o velho se chamam os dois `reco.exe`)
não achou Reco que eu não tivesse aberto. Exe do casco recompilado antes (`C:\pt\debug\reco.exe`, 00:08, com o
`c20ffd9`). Config do dono copiado para `temp/fase3-manual/reco_config.antes.json` antes da primeira prova.
CPU total da máquina entre 53% e 78% no início de cada script (outras sessões: `claude`, `vmmemWSA`, `node`):
nenhuma destas provas tem critério de tempo, então não esperei; os milissegundos abaixo são só referência.
Scripts descartáveis em `temp/fase3-manual/` (fora do git): `comum.py`, `passo7.py`, `passo9.py`, `passo10.py`,
`invocar.cjs`. Todos encerram por pid (árvore) só o que abriram.

**Passo 7 — exclusão mútua nos dois sentidos** (`python passo7.py` → código 0; casco com motor inexistente de
propósito, velho com `HF_HUB_OFFLINE=1`, sem `RECO_SEM_MUTEX`):

- Casco primeiro (`--oculto`, janela escondida): `velho_codigo: 0`, `velho_saiu_em_ms: 704`,
  `janela_casco_visivel_antes: false` → `janela_casco_apareceu: true`, `casco_no_foreground: true`. O
  `Reco.Show` do velho chega à janela de topo escondida criada pelo Rust (a premissa do passo).
- Velho primeiro (janela escondida por `WM_CLOSE`, que no velho só esconde): `casco_codigo: 0`,
  `casco_saiu_em_ms: 33`, `janela_velha_apareceu: true`, `velho_vivo: true`. (O `casco_fez_janela: false` da
  saída não prova nada: foi lido depois de o processo sair. A prova de que ele não montou o app é o código 0
  em 33 ms.)
- Fim: `reco_rodando_no_fim: []`.

**Passo 9 — hover real com o Bloco de Notas focado** (`python passo9.py` → código 0 às 00:11, com a webview na
página de erro do `devUrl` porque o Vite não estava no ar; repetido com `python passo9.py --vite` → código 0 às
00:19, com a webview em `http://localhost:1430/` conferida pelo CDP, mesmos valores abaixo; motor inexistente):

- Ícone: a entrada `2799579577188804128` (`C:\pt\debug\reco.exe`) em `NotifyIconSettings` não tinha
  `IsPromoted`; promovi **preventivamente** (gravei `1` antes de abrir o casco, sem conferir se ele nascia
  escondido no "^") e apaguei o valor no fim, nas duas rodadas. Rect pelo
  `Shell_NotifyIconGetRect` (janela `tray_icon_app` do pid, `uID` 2): `2018,1020,2058,1080`, dentro da barra.
- Alvo: arquivo próprio `temp/fase3-manual/alvo-hover.txt` aberto no Bloco de Notas (abriu como aba na janela
  do Bloco de Notas que já estava aberta); cada tecla só saía com o foreground nessa janela e com esse título.
- Resultado: `apareceu: true` (200 ms e 196 ms do harness, 12 passos de 15 ms incluídos; só referência, CPU
  76% a 78%), `acima_do_icone: true`,
  `mostrou_fg_igual`, `mostrou_gui_igual`, `dentro_fg_igual`, `dentro_gui_igual`, `depois_fg_igual`,
  `depois_gui_igual` todos `true`, `fica_com_cursor_dentro: true`, `some_ao_sair: true`, e o arquivo salvo
  com `antes durante dentro depois` (o texto digitado com a janela à vista entrou no Bloco de Notas).
- Controle negativo: o clique no ícone fixa e toma o foreground (`clique_fg_casco: true`) e a janela fica
  visível com o cursor longe (`clique_fica_visivel_fora: true`); o X esconde (`x_esconde: true`). O teste vê o
  roubo de foco quando ele existe.
- A aba de teste foi salva e fechada (Ctrl+S, Ctrl+W); o processo do Bloco de Notas não foi tocado.
- **Agora o `[x]` do passo 9 cobre a janela real**, não só as funções puras.

**Passo 10 — atalho e iniciar com o Windows, ligados e desligados** (`python passo10.py`; motor real do fonte com
`HF_HUB_OFFLINE=1`, Vite em 1430 aberto pelo script, comandos chamados pela webview real por CDP do WebView2
com `window.__TAURI_INTERNALS__.invoke`, porque a tela de Opções é do passo 13):

- Antes: `reg query …\Run /v "Reco Novo"` não acha; `autostart_ligado → false`, `atalho_registrado → false`,
  `casco_atalho` ausente no config; Ctrl+Shift+R com o Bloco de Notas focado não mostra nada e o foco fica nele.
- Ligado: `definir_autostart(true) → true`, `reg query` acha `Reco Novo REG_SZ C:\pt\debug\reco.exe --oculto`;
  `definir_atalho(true) → true`, `casco_atalho: true` no config (gravado pelo motor); Ctrl+Shift+R mostra a
  janela e o foreground vai para ela.
- Desligado: `definir_atalho(false) → false`, `atalho_registrado → false`, `casco_atalho: false`; Ctrl+Shift+R não
  mostra nada e o foco fica no Bloco de Notas; `definir_autostart(false) → false`, `reg query` não acha.
- O texto digitado entre os passos (`a b c d`) está no arquivo salvo: nenhuma tecla do atalho vazou para o alvo.
- O script terminou com código 1 só na limpeza: entre o último `digitar` e o Ctrl+S, o foreground foi para
  janelas de outros programas (causa não identificada: outra sessão ou o próprio dono no teclado; a guarda
  recusou mandar teclas). Salvei e fechei a aba à mão, com a mesma guarda e `SetForegroundWindow` (no meio, o
  foreground saiu de novo, para o WhatsApp, e a guarda segurou o Ctrl+W até a aba voltar à frente). O que se
  sabe: todo caractere digitado está nos dois arquivos salvos (`antes durante dentro depois` e `a b c d`), e
  nenhuma tecla saiu depois de cada Ctrl+W; não tirei retrato da aba do dono antes, então não afirmo mais que
  isso. Nenhum critério da prova falhou.
- **Sobra apagada:** o `disable()` do plugin deixa `Reco Novo` (`REG_BINARY 02 00 …`) em
  `Explorer\StartupApproved\Run` (`auto-launch` 0.6.0 grava no `enable` e não apaga no `disable`). Apaguei com
  `reg delete … /v "Reco Novo" /f`; pegadinha nova em `docs/armadilhas.d/`.
- **Fica pendente:** "foco no botão principal" ao apertar o atalho (não há botão até o passo 12; o casco emite
  `reco-atalho` para a tela focar). Conferir no passo 13 com a tela de Opções.

**Estado da máquina no fim (00:15, conferido de novo depois da repetição do passo 9 às 00:19):** nenhum
`reco.exe`, motor, WebView2 ou Vite meu rodando; portas 1430, 9333 e 9334 livres; `Run` e `StartupApproved\Run` sem `Reco Novo`; `IsPromoted` da entrada do casco apagado (como
estava). O config só diferia da cópia em `casco_atalho: false` (nenhuma outra chave mudou, inclusive pelo velho
de teste do passo 7): a cópia voltou, `cmp` igual. **O Reco do dono continua fechado** (a tarefa manda fechar só o
que abri; reabrir é com ele).

### Passo 16 — `app/build.ps1` e o instalador (12/11/2026, 03:34 a 03:58)

Condição: o chamador avisou que o Reco do dono estava aberto, mas ele **já não rodava antes do build**: às ~03:31
o `Get-Process` com os nomes `reco` e `reco-engine` (entre outros) só achou `node`, e às 03:59, depois do build,
`tasklist` não achou nenhum processo com "reco" no nome. Não sei quando nem por que ele fechou; não o reabri. Esta rodada não
abriu, fechou nem mandou mensagem a ele: o build não abre o app (o casco de release pega o mesmo mutex) nem o
instalador, e o smoke sobe só o `reco-engine.exe` congelado, que encerra com `shutdown`. Uma execução anterior caiu às ~03:25 com o `build.ps1` escrito e sem commit; ela chegou a gerar
`C:\pt\release\reco.exe` às 03:09, mas nenhum instalador. Retomada sem processo de build órfão (só MCP do
Playwright e o coletor do WhatsApp). O `build.ps1` foi lido, conferido contra o passo e rodado sem mudança.

- **Prova:** `powershell -ExecutionPolicy Bypass -File app/build.ps1` → `exit=0`, última linha
  `Instalador: C:\pt\release\bundle\nsis\Reco Novo_0.1.0_x64-setup.exe`. Nome exato do `tauri.conf.json` e data
  posterior ao início da rodada (instalador do Lacre ou antigo não passa).
- **Instalador:** `C:\pt\release\bundle\nsis\Reco Novo_0.1.0_x64-setup.exe`, 128,8 MB (135005911 bytes), SHA256
  `72e983389d2b54c39eeca920ca7ac2c0d1835d79e9125687fc17a8212231d660`. Fora do repo; não instalado nem rodado.
- **Pasta final (calculada, sem instalar):** casco `reco.exe` 4,3 MB + motor `engine/` 491,2 MB = 495,5 MB, sem o
  desinstalador. Não medi a pasta de `C:\pt\release` porque ela é dividida com o Lacre.
- **Tempo de build:** 1435,5 s (~24 min) no total: congelar o motor e o smoke 178,4 s, `npm ci` 4,5 s, interface
  5,2 s, `tauri build` 1246,6 s (compilação release 5 min 07 s; o `makensis` comprimindo os ~500 MB levou ~15 min).
- **Smoke do motor congelado (D12, lado do motor):** 3 rodadas, `hello` em 0,75/0,56/0,53 s e `ready` em
  1,10/0,98/0,88 s, `shutdown ok=True exit=0`; a última listou dispositivos (1 entrada, 2 saídas) em 0,09 s. A régua
  da Fase 0 é o velho pronto em 1,515 s (mediana). O número que fecha o D12 é o do app instalado (abaixo).
- **Controle negativo:** com `engine/dist/reco-engine` renomeada, `build.ps1 -SemCongelar` → `ERROR: frozen engine
  not found at …\reco-engine.exe`, saída 1, antes de qualquer build; pasta renomeada de volta em seguida.
- **Fica para o passo 17** (precisa do app velho fechado, proibido nesta rodada): o tempo do clique no ícone até a
  janela e o tempo até Gravar habilitar no app instalado, ao lado do 1,515 s do velho.
- **Cosmético, sem efeito na prova:** o `memória` do smoke sai `mem?ria` (o Python grava o stdout redirecionado
  em cp1252 e o script lê UTF-8), e os tempos misturam vírgula e ponto (formatação do PowerShell por cultura).
- **Repo depois do build:** `git status` limpo (sem instalador nem `dist/` no git); `reco.py`, `tray.py` e o
  `build.ps1` do velho intocados. Commit `a8f183c` (o script, logo depois da primeira rodada verde).

### Revisão adversarial (12/11/2026, ~11:40 a 12:30)

16 achados (5 altos, 4 médios, 7 baixos). Nenhum é falso: todos batem com o código. O de número 10 (aspas no
modo falso) não pede código: fica para o passo 17. Commits: `7efcc33` (interface), `c42cc11` (casco), `bcd7d78`
(smoke) e `aac7ca7` (conferência do advisor: o cache de skin e tema vencia o config do motor quando a chave
faltava, faltava o ponto antes do aviso de saída ausente, e o `stopping` agora mostra "Parando…" com os
medidores parados). O Reco do dono não foi aberto, fechado nem chamado: nenhuma prova sobe o casco (que pega o mesmo mutex).

| # | achado | gravidade | o que foi feito |
| --- | --- | --- | --- |
| 1 | duplo clique em Parar com o motor em `stopping` mostra "interrompida" | alta | `cliques.ts` ignora `detail > 1`; `gravar.ts` tem a trava de pedido em voo (principal, secundário, Só salvar, Excluir; sem valer com o condutor); `refused`/`busy` no parar ressincronizam pelo `state` |
| 2 | duplo clique em "Salvar e copiar" começa gravação nova | alta | mesma trava e mais: no principal, o clique de ponteiro cujo aperto começou antes da última troca de papel (`principalTrocouEm`) é ignorado (teclado passa) |
| 3 | duplo clique em Gravar começa e para; `busy` no start vira erro falso | alta | mesma trava; `busy`/`refused` no `rec.start` ressincronizam |
| 4 | motor caído ocioso ou `hello` que falha deixam a tela "Pronto" ou "Preparando" para sempre | alta | `Vista.motorFora` desabilita o principal; queda ocioso → aviso "O motor de gravação parou"; `hello` que falha ou `ready` com erro → "O motor não carregou"; 20 s em `motor-subindo` → "O motor está demorando"; o aviso (`doMotor`) some no `ready` e o alarme do D11 fica. Provados no `revisao.cjs`: queda ocioso e volta, `ready` com erro e volta. **Lidos, sem prova:** `hello` que falha e o prazo de 20 s (`PRAZO_MOTOR_MS`) |
| 5 | medidores acesos depois da queda; tempo gravado perdido | média | `mostrarInterrompida` zera os VUs (também no `rec.error` fatal) e põe "interrompida em 00:12:34" no status |
| 6 | janela nasce em Fita e troca de skin e tema depois do `ready` | média | cache local `reco.aparencia` (`aparencia.ts`), lido na `vistaInicial` e por um script em linha no `index.html` antes do primeiro desenho; gravado no `config.get` e em Opções; o motor continua dono |
| 7 | painel muda a ordem das linhas ao gravar | baixa | gravando também em Entrada, Saída, Pasta (`app/ui/index.html`). A vitrine (`design/vitrine.html`) não foi tocada e segue com Arquivo, Entrada, Saída gravando: a fonte do desenho diverge nessa camada até alguém alinhar (sem efeito nos testes, que medem caixas) |
| 8 | textos com cara de rascunho e detalhe cru no status | baixa | `Microfone: X · Sistema: Y`, um espaço entre frases, ` · ` antes do nome, erro do `rec.start` por código (`no_device`, `unavailable`, outro), `refused`/`busy`/`internal` em frase humana, "Processar em" sem jargão; o detalhe cru vai só ao Detalhes e ao console (`app.falhou`) |
| 9 | Transcrever da Biblioteca desabilitado sem motivo | baixa | status da seleção ganha "Transcrever volta quando a gravação ou a transcrição em curso terminar." |
| 10 | aspas do colar não verificáveis no modo falso | baixa | sem código: o teste `aspas` do Rust (passo 6) cobre a montagem; o colar real fica no passo 17 |
| 11 | smoke aprova motor que diz `hello` mas não importa o `reco` | alta | `engine/build.py` imprime `ready ok=…` e `devices ok=…` e sai 1 se falhar (`--motor` para provar); `Assert-Smoke` exige os dois; armadilha nova |
| 12 | Sair logo depois de Parar corta o `close()` do MP3 | média | `saida.rs`: com `stopping`, pergunta o `state` a cada 200 ms até sair dele (teto de 120 s) e só então `shutdown`, sem `rec.stop` novo (`Saida::EsperouFechar`) |
| 13 | motor morre em `stopping` e a tela segue "Gravando" | média | `estado.rs` trata `stopping` como arquivo aberto (alarme e `reco-gravacao-interrompida`); a tela, gravando, vira alarme no `engine-status` caído mesmo sem o evento; `ressincronizar` com `idle` e a tela gravando → alarme, parada → Pronto com aviso |
| 14 | Gravar pela bandeja com a tela em Nota mostra "Gravando nota" | baixa | `recording` vindo de fora vira modo gravação (a bandeja grava `rec`), lê o `state` para o ao vivo e põe Opções em `durante-gravacao`; durante o `rec.start` da própria tela, o evento espera a resposta (`comecando`) |
| 15 | `reco-conclusao` antes da resposta do parar prende a tela em transcrevendo | baixa | a conclusão que chega com o parar (da tela ou da bandeja) em curso fica guardada e é aplicada depois |
| 16 | falha de Gravar/Pausar pela bandeja some no log | baixa | `lib.rs` `pedir` avisa com a janela escondida (`Aviso::BandejaFalhou`) |

**Provas rodadas depois das correções:**

- `npm --prefix app run ui:build` → `built`; `npm --prefix app run i18n:check` → `234 chaves PT, 234 EN … 0 faltando`.
- `node app/ui/tests/gravar.cjs` → `falhas 0 em 53`; `telas.cjs` → `falhas 0 em 50`; `paridade.cjs` → `17 de 17
  presentes`; **novo** `revisao.cjs` → `falhas 0 em 21` depois do `aac7ca7` (18 antes; duplo clique nos três papéis, motor lento no start e no
  stop, aperto antes da troca de papel, bandeja com a tela em Nota, conclusão antes do parar, motivo na Biblioteca,
  motor caído ocioso e de volta, `ready` com erro e de volta, "Parando…" no `stopping`, caído em `stopping` sem o
  evento, VUs zerados e tempo no alarme, ordem do painel, skin e tema do cache no `DOMContentLoaded` e o config do
  motor vencendo depois do `ready`). As provas desta lista foram rodadas de novo depois do `aac7ca7`, com os mesmos
  números (Fase 1 com `--url`: 0 e 0; sabotagens: 1 e 1).
- Controle negativo do `revisao.cjs`: com a interface antiga (os arquivos de `HEAD` e o backend falso novo) →
  ordem do painel, os três duplos cliques e o stop lento em `FALHA` e o teste quebra no Excluir (a tela parou em
  erro); com a trava desligada (`false &&` por Edit, desfeito e conferido por `cmp`) → os dois "motor lento" em
  `FALHA`.
- Fase 1 com `--url` (`ui:preview` na 1431, parado no fim por pid) → `anti-pulo: 0 diferenças em 23868 medições`,
  `a=0`; `contrato: 0 falhas`, `c=0`; sabotagens → `anti-pulo=1` (1932 diferenças), `contrato=1` (981 falhas).
- `cargo test --manifest-path app/src-tauri/Cargo.toml -- --include-ignored` → `test result: ok. 41 passed` (40
  antes; novo `sair_espera_o_stopping`, e `stopping` nos testes de `saida` e `estado`); controle negativo com o ramo
  do `stopping` desligado → `left: Ocioso, right: EsperouFechar { ok: true }`, `FAILED`. `cargo clippy --all-targets`
  → 0 avisos.
- Smoke: motor falso (`engine/build.py --motor python <falso> <modo>`) → `ok` sai 0; `ready-erro` e
  `devices-falha` saem 1 com `SMOKE REPROVADO`. `Assert-Smoke` carregado do `build.ps1` pela AST com linhas prontas
  → a boa é aceita; a linha antiga (`devices ok=False`, sem `ready ok=`), `ready ok=False` e `devices ok=False` são
  recusadas.

**Pegadinha do processo:** o guarda de comando recusa `git checkout -- $(…)`; o controle negativo usou
`git restore -- <arquivos>` nomeados e a cópia no scratchpad para voltar.

### Pendências da rodada dos passos 2 a 10 (resolvidas no fechamento, 12/11)

- **Passo 10, foco no botão principal** pelo atalho: provado no backend falso (`gravar.cjs`, `reco-atalho` com foco no
  principal, passo 12). Com tecla física no app instalado, não: vai para a Fase 4 (passo 11 dela).
- **Clique dentro da janela do hover** (`window_pin` com `set_focus()` na primeira vez): a tela chama `window_pin` em
  todo clique (passo 12), mas o clique real dentro da janela nunca foi feito (o teste real foi sem mouse). Fase 4.
- **D11 de ponta a ponta:** feito no passo 17 (build `aac7ca7`): casco morto → motor fecha o MP3 (30,827 = 30,827 s);
  motor morto → alarme em 0,11 s, sem religar. Resolvido.
- **Minimizar sem botão na barra de tarefas** (`skipTaskbar: true`): não conferido no app instalado. Fase 4 (uso real;
  se incomodar, tirar o `skipTaskbar` ao fixar).
- **Perfil `%LOCALAPPDATA%\io.github.dosxnjos.reco\`:** é o perfil normal do app novo, que segue instalado (`aac7ca7`)
  para a Fase 4. Fica.
- **Passos 17 e 18:** feitos (seções "Passo 17" e "Revisão adversarial dos consertos e fechamento").

### completei:

- Testes extras além do mínimo: `estado.rs` (D11 e porteira do `ready`, 3 testes), `avisos.rs` (1), `prazos` de
  `rec.conclude` por ação, `launch_dev` e `motor_real_hello` rodado de verdade (o md só pedia que existisse).
- Controle negativo do `sair_fecha_gravacao` (mutação em cópia, restaurada).
- `ready` com `error` (import falhou) não dispara checagem de versão nem atalho.
- O ícone da bandeja só é trocado quando muda de cor (o `timer` chega 1/s).
- Fumaça do exe de debug com motor inexistente: setup, bandeja e backoff conferidos sem efeito na máquina.
- Duas pegadinhas novas em `docs/armadilhas.d/` (abaixo).

### Pegadinhas novas

- `Image::from_bytes` do Tauri só existe com a feature `image-ico`.
- `cargo test` do casco imprime `ok. 0 passed` do bin e dos doctests além da linha da lib.
- (12/11) O `disable()` do autostart (`auto-launch` 0.6.0) apaga o `Run` mas deixa `Reco Novo` em
  `Explorer\StartupApproved\Run`.

### Desvios do md

- Passo 3: sem `positioner` no `Cargo.toml` (pegadinha 3 da Fase 0) e `windows-sys` com `Security`,
  `Graphics_Gdi` e `System_LibraryLoader`; `tsconfig.json` só inclui `ui/src` (o `vite.config.ts` pedia
  `@types/node`). Anotado no md.
- Passo 5: a lógica do Sair fica em `motor/saida.rs` (o md pedia "módulo `motor/`"); arquivos extras fora da
  lista do md: `estado.rs`, `avisos.rs`, `motor/mod.rs`.
- Duas edições de texto foram feitas com Python, contra a regra da casa: a mutação temporária do controle
  negativo (restaurada de cópia) e a troca de `#[derive(Default)]` por `impl` manual no `bandeja.rs` (conferida
  pela compilação e pelos testes). Daqui em diante só `Edit`.
- Os passos 2 a 10 foram marcados `[x]` no md com o passo 1 em aberto (só a parte de contrato), por instrução
  do chamador.
- **O commit `9367228` (passos 5 e 6) não compila sozinho:** o `lib.rs` dele já cita `atalho`, `bandeja`, `hover`
  e `instancia`, que só chegam no `a40d9db`. Juntar os dois (squash) antes do push, se o chamador quiser;
  não reescrevi o histórico porque a árvore tem edições de outra sessão em `design/` e nos roadmaps.
- No md da Fase 3, o bullet "Base: `9fd4f95` … mecanismo do hover" foi escrito **dentro do passo 1**, fora das
  seções liberadas (contrato e passos 2 a 10). É anotação que o próprio passo 1 pede, mas fica registrada.

### Commits

| hash | o quê |
| --- | --- |
| `4072704` | `tools/tamanho.json`: `.rs` e `.ts` (commit próprio, regra do json) |
| `ceaa5d3` | `.pre-commit-config.yaml` (`files:` com `rs\|ts`) e `.gitignore` (`node_modules/`, `app/src-tauri/gen/`) |
| `1bbd08b` | esqueleto de `app/` + contrato conferido no md (passos 1 e 3) |
| `b2e2afc` | ponte com o motor em `motor/` (passo 4) |
| `9367228` | `lib.rs`, saída segura, `estado.rs`, `avisos.rs`, `comandos/` (passos 5 e 6) |
| `a40d9db` | `instancia.rs`, `bandeja.rs`, `hover.rs`, `atalho.rs` e md (passos 7 a 10) |
| `d1dcbff` | duas pegadinhas em `docs/armadilhas.d/` |

### Arquivos

Criados: `app/package.json`, `app/package-lock.json`, `app/vite.config.ts`, `app/tsconfig.json`,
`app/ui/index.html`, `app/ui/src/main.ts` (esqueleto), `app/src-tauri/{Cargo.toml, Cargo.lock, build.rs,
tauri.conf.json, capabilities/default.json, icons/*.ico}`, `app/src-tauri/src/{main, lib, estado, avisos,
instancia, bandeja, hover, atalho}.rs`, `src/motor/{mod, router, processo, log, prazos, saida, testes}.rs`,
`src/comandos/{mod, motor, arquivos, janela}.rs`, os dois fragmentos de armadilha e este relatório.
Alterados: `tools/tamanho.json`, `.pre-commit-config.yaml`, `.gitignore`, o md da Fase 3. Não tocados:
`reco.py`, `tray.py`, `engine/`, `design/`, outros roadmaps.

### Instalador depois da revisão adversarial (12/11/2026)

O app mudou (interface e casco), então o passo 16 rodou de novo, duas vezes:

- `powershell -ExecutionPolicy Bypass -File app/build.ps1` (completo, no `4ab9a3c`) → `exit=0`, smoke novo com
  `ready ok=True` nas 3 rodadas e `devices ok=True (1, 2)` na última; motor 60,5 s, `tauri build` 278,1 s, 341,8 s no
  total (o `makensis` foi bem mais rápido que os ~15 min de 03:34; não investiguei por quê).
- Depois do `aac7ca7` (interface), `app/build.ps1 -SemCongelar` (o motor não mudou), 12:09 a 12:14 → `exit=0`,
  smoke `ready ok=True` em 0,30 a 0,35 s e `devices ok=True (1, 2)`, `tauri build` 306 s, 311,3 s no total.
- **Instalador final (o do passo 17):** `C:\pt\release\bundle\nsis\Reco Novo_0.1.0_x64-setup.exe`, 128,8 MB
  (135027126 bytes), gravado às 12:14:13 (depois do início da rodada), feito do `aac7ca7`, SHA256
  `75d02dae0fcd31a3997e54e4d7c7f79587a7cff6b2bcf20b7e7e18bc0e729872`. O SHA256 da seção do passo 16 (03:58) é de um
  instalador velho, substituído. Não instalado nem rodado; nenhum processo meu sobrou (conferido por caminho).

### Passo 18 (12/11/2026, parcial)

Prova como escrita: `git diff --stat 9fd4f95 -- docs/ARQUITETURA.md README.md CLAUDE.md` → os três arquivos (8,
46 e 66 linhas mudadas); `pre-commit run gate-claude-md --files CLAUDE.md` → `Passed` (5948 bytes). Feitos:
README nas duas línguas (seção do app novo em construção e como gerar o instalador), ARQUITETURA § Casco Tauri,
`_INDICE`, CLAUDE.md (1 linha e meia), duas armadilhas (`visoes.py novo`), hub e diário no C:\Dev (`9a02b019`).
Commit dos docs: `4ab9a3c`. O passo ficou `[ ]` nesta rodada porque dependia do 17; foi fechado no fim (seção
"Revisão adversarial dos consertos e fechamento").

### Passo 17 — teste real (12/11/2026, 11:50 a 12:22)

Condição: Reco velho fechado pela sessão principal antes de começar, sem gravação em curso (o dono autorizou:
"Fica à vontade para fechar, não estou usando"). Antes de cada abertura, guarda pelo **mutex**
`Local\Reco.SingleInstance` (`OpenMutexW`) e pelos processos `reco.exe`/`reco-engine.exe` por caminho. Fala do PC:
`temp/bench-voz/clip10.wav` em laço no alto-falante (`Clipe` de `tools/engine_checks_rec.py`). Config real do dono
(ganho mic 3,0, sistema 0,5, dispositivos `auto:console`, `live: false`), com `HF_HUB_OFFLINE=1` para a checagem
de modelo não baixar nada no meio. Scripts descartáveis no scratchpad da sessão (`p17lib.py`, `driver.cjs`
persistente por CDP, `cenario.py`, `d12.py`, `diag_nota.py`); logs em `temp/medicoes/p17/`, capturas em
`temp/provas/2026-11-12/p17/` (fora do git).

**Sem mouse nem teclado (pedido do dono, ~11:40, chegou durante a execução):** até ~11:56 a fumaça e as rodadas
de partida usaram `SendInput` (hover, clique no ícone, menu da bandeja com o botão direito) e abriram a janela
visível 7 vezes (cada abertura e cada clique no ícone tomaram o foreground). Parei a rodada em curso assim que o pedido chegou (a 5ª não abriu; nada
ficou aberto). **Daí em diante, tudo sem mouse e sem teclado:** o casco abre com `--oculto` e
`WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=9351`, cliques por `el.click()` no DOM via CDP
(sem `pointerdown`, então sem `window_pin` roubando o foco) e itens da bandeja por `PostMessageW(WM_COMMAND)` na
janela `tray_icon_app` (Gravar = 1000, Sair = 1003; armadilha nova). Hover, clique no ícone e "Parar pela bandeja"
(que mostra a janela fixada e toma o foco) **pulados a pedido do dono: sem mouse** no build final; ficam os
números do build anterior abaixo e a prova do passo 9.

**Builds:** a primeira rodada (11:50 a 12:14) foi no instalador do passo 16 (SHA256 `72e98338…`, `reco.exe`
`3585c344…`). A outra frente refez o instalador no `aac7ca7` (revisão adversarial); desinstalei
(`uninstall.exe /S` → exit 0, pasta, atalho do Menu Iniciar e exe removidos; `%LOCALAPPDATA%\io.github.dosxnjos.reco`
fica) e instalei o final (`/S` → exit 0; SHA256 do instalador `75d02dae0fcd31a3997e54e4d7c7f79587a7cff6b2bcf20b7e7e18bc0e729872`
conferido, `reco.exe` instalado `b1eef36604e09524f63e3457342cea6866cda205d2b30864728a6cdfea3d9dbd`). **O `[x]` vale
pelo build final**; o anterior fica como referência.

**Instalação** (`/S`, 16,2 s na primeira): `%LOCALAPPDATA%\Reco Novo\reco.exe` + `engine\` + `uninstall.exe`;
cria `Reco Novo.lnk` no Menu Iniciar **e na Área de Trabalho** (o NSIS do Tauri cria o da área de trabalho no
modo silencioso, `installer.nsi:4330-4335`); apaguei o da área de trabalho nas duas instalações. Não abre o app
sozinho (sem `/R`). `Reco.lnk`: `False` antes e depois.

**Prova do passo (build final, 12:20, `cenario.py principal`):**

- Gravar (clique no DOM) → "Parar" na hora; 30 s pelo cronômetro com o clipe tocando; Parar → "Salvar e copiar
  caminho" em **0,469 s de "Parando…"** (0,452 s na rodada de 12:16); clique no principal → status `Caminho copiado:
  "…"`.
- `Get-Clipboard` → `"%USERPROFILE%\Documents\Reco\gravacao_reco_2026-11-12_12-20-24.mp3"` (entre aspas).
- `ffprobe -v error -show_entries stream=channels,sample_rate:format=duration` → `sample_rate=16000 channels=2
  duration=30.101313`; cronômetro ao parar `00:00:30` (diferença 0,1 s). PyAV: declarada 30,101 = decodificada
  30,101 (cabeçalho certo).
- Lados por dado (`lados()` do `engine_checks_rec.py`): clipe×R **0,737** > clipe×L 0,446 (voz do PC no direito).
  Na rodada de 12:16 deu clipe×R 0,409 > L 0,374, abaixo do mínimo de 0,5, com o RMS do R no dobro (0,081 contra
  0,045 de todas as outras): som de outro programa do PC entrando no loopback com o dono usando a máquina. Repeti
  e passou; as rodadas de D11 e Sair também passaram (R 0,72 a 0,78).
- Transcrever pela Biblioteca (aba, item, Transcrever, tudo no DOM) → `gravacao_reco_…_12-20-24.txt` ao lado,
  mesmo nome do velho, 2 linhas com rótulo `Eu:`/`Interlocutor(es):` (diarizado), status "Transcrição salva".

**Nota (build final, 12:17):** o `.md` nasce em `Documents\Reco` (`nota_dir` nulo) e `Get-Clipboard` →
`"%USERPROFILE%\Documents\Reco\nota_2026-11-12_12-17-30.md"`; o mp3 da nota vai à Lixeira pelo motor. **Defeito:**
o primeiro "Gravar nota" ~2 s depois de abrir não grava (abaixo).

**D11, casco morre gravando (build final, 12:18):** 30 s, `Stop-Process -Id <casco>` (pid achado como pai do
`reco-engine.exe`) → o motor saiu sozinho em 0,72 s; arquivo com declarada 30,827 = decodificada 30,827, 2 canais,
16000 Hz, lados R 0,749 > L 0,611. (Build anterior: 0,72 s, 30,72 = 30,72.)

**D11, motor morre gravando (build final, 12:18):** 30 s, `Stop-Process -Id <reco-engine>` → a tela saiu de
"Gravando" em 0,11 s para "Erro" com "A gravação foi interrompida" e "Abrir pasta", medidores zerados (no build
anterior ficavam com o último nível, achado 5 corrigido); o motor
voltou sozinho e **não** religou a gravação (8 s depois: principal "Gravar", status "O motor reiniciou; a tela
foi atualizada."). O arquivo do motor morto: declarada 19,45 s × decodificada 20,88 s (sem a contagem final e
sem os últimos ~9 s, que estavam no buffer do encode, como o md previa) → Lixeira; `reparar_duracao.py` não rodou.
O ícone fora do vermelho depois da queda só está na captura do **build anterior** (`IsPromoted` ainda ligado:
ícone de repouso, cinza); no build final o ícone já estava no "^" e a captura `08-…png` não o mostra. Pelo código,
o mesmo evento que põe a tela no alarme põe o ícone em repouso (`estado.rs`, D11), mas no build final isso não foi
visto.

**Bandeja grava e Sair gravando (build final, 12:19):** `WM_COMMAND 1000` (Gravar do menu) → a tela foi a
"Parar"; 30 s; `WM_COMMAND 1003` (Sair) → o casco saiu com código 0 em 0,51 s; log do casco `Sair com gravação
aberta: rec.stop antes do shutdown (D11)` e `saída: FechouGravacao { ok: true }`; arquivo declarada 30,016 =
decodificada 30,016, 2 canais, 16000 Hz, lados R 0,719 > L 0,596.

**Repasse `--transcribe` (build final, 12:21):** cópia `a_reco.mp3` em `temp/medicoes/p17/build-novo/repasse/`,
`reco.exe --transcribe <cópia> --diarize` esperado até o fim → exit 0 em 19,1 s, `a_reco.txt` ao lado (2 linhas
rotuladas), fim de `%TEMP%\reco_transcribe_log.txt` = `OK -> …\a_reco.txt`; nenhuma janela visível de nenhum
processo Reco durante a execução; o `reco-engine.exe` rodou como filho. (Se o repasse pega o mutex não foi
medido: a única leitura foi depois de o processo sair.)

**D12 — abrir até pronto para gravar (régua: velho `abrir_pronta_s` mediana 1,515 s):**

| build e método | visível | Gravar habilitado |
| --- | --- | --- |
| passo 16, janela visível, sem CDP, pela cor do botão (`d12.py`, 5 rodadas, CPU 5% a 18%) | 0,302 a 0,358 s, mediana **0,306 s** | 1,074 a 1,313 s, mediana **1,156 s** |
| passo 16, 1ª abertura depois de instalar (com CDP) | 0,393 s | ≤ 1,048 s |
| final `aac7ca7`, `--oculto` + CDP, 6 aberturas (teto: inclui conectar o CDP) | — | 0,644 a 0,823 s, mediana **0,781 s** |

- Os dois métodos ficam abaixo de 1,515 s. O da cor conta o fim da transição de cor do botão (~0,12 s), então é
  conservador. Não repeti a abertura visível no build final: ela toma o foreground do dono.
- Ícone até a janela (só no build do passo 16, com mouse, antes do pedido): cursor entra no ícone → janela visível
  em 0,047 a 0,048 s (5 de 5 **sem** tirar o foco de quem estava na frente); clique no ícone → foco na janela em
  0,067 a 0,074 s.
- "Parando…" real (achado da revisão): 0,452 e 0,469 s do clique em Parar até "Salvar e copiar caminho".

**Defeitos e observações:**

1. **"Gravar nota" logo depois de abrir não grava** (os dois builds; 3 vezes). O casco pede `model.update_check`
   1,5 s depois do `ready`; a checagem ocupa a vaga da transcrição (`engine/reco_engine/extras.py:7`) e o
   `rec.start {mode: nota}` recusa com `busy` (`recording.py:140-141`). No build anterior a tela mostrava "O motor
   está ocupado com outra tarefa: transcrição em andamento"; no final o clique some calado (volta a "Pronto"). O
   segundo clique grava. Com rede de verdade (sem `HF_HUB_OFFLINE`) a janela é maior, e com modelo novo para baixar
   a nota fica travada pelo download. Gravação comum não sofre. Armadilha nova; a correção é da frente do app.
   - Efeito no teste: no build anterior, meu roteiro esperava 2 min antes do 2º clique, e duas notas gravaram o
     microfone com o dono falando (uma de ~5 min). Não copiei o texto para cá; os `.md` foram à Lixeira, e os logs
     que guardavam trechos da transcrição (`principal*.log`, `nota*.raw`) foram apagados (os números estão aqui).
2. **Entrada e Saída vazias antes da primeira gravação** com `auto:console`: o painel mostra "Entrada"/"Saída" sem
   nome e o status sai "Pronto para gravar. Microfone:  · Sistema: " (os dois builds); os nomes aparecem quando a
   gravação começa (a resposta do `rec.start`).
3. **Log do casco em UTC**: `Reco Novo.log` marca 14:55 para 11:55 locais (o `engine.log` está em hora local).
4. **Sair encerra o motor por EOF, não por `shutdown`**: no `engine.log`, a maioria das saídas (ociosa e gravando)
   registra `encerrando (eof)`. Nada se perde (a gravação fechou antes, pelo `rec.stop`), mas o `shutdown(8 s)` do
   casco parece não chegar ao motor antes de o processo sair. Não investiguei.
5. Instalação silenciosa cria atalho na Área de Trabalho (acima); a instalação com tela oferece a caixa.
6. Sair durante a passada final de uma nota curta (só no diagnóstico) deixou o mp3 e um `.md` de 14 bytes na pasta:
   nada perdido; os dois foram à Lixeira.

**Máquina no fim (12:22):** nenhum `reco.exe`/`reco-engine.exe` do app novo e mutex livre antes de reabrir o velho;
`Documents\Reco` com os mesmos 213 arquivos de antes (nenhum novo, sumido ou com tamanho mudado; todas as gravações,
`.txt` e `.md` de teste foram à Lixeira, as cópias do repasse também); `cmp ~/.reco_config.json
temp/medicoes/reco_config.antes-p17.json` → igual (nenhuma chave `casco_*`); `reg query …\Run /v "Reco Novo"` e
`…\StartupApproved\Run` → não acha (rc 1), atalho global nunca ligado; `IsPromoted` que eu gravei na entrada do ícone
do app novo foi apagado (não existia antes); `Reco.lnk` `False`; atalho da área de trabalho apagado; clipboard do
dono reposto (o texto de antes, conferido). App novo **instalado** (Fase 4 usa) e fechado. Reco velho reaberto:
`Start-Process …\dist\Reco\Reco.exe` → `python tools/medir_partida.py --ram-viva` → `{"pid": 29256, "ws_mb": 56.0,
"privado_mb": 487.7, "cpu_pct": 15.6}`, `ExecutablePath` `C:\Dev\Reco\dist\Reco\Reco.exe`.

### Defeitos do passo 17: correção (12/11/2026, commits de 14:43 a 14:53, build 14:50 a 15:01)

Condição: o Reco velho do dono **aberto** (`C:\Dev\Reco\dist\Reco\Reco.exe`, pid 29256, conferido no fim) e o dono
usando a máquina. Nada abriu o Reco Novo instalado nem o casco contra o motor real; nenhum mouse ou teclado; nenhuma
prova que grava (as do `--gravar`/`--eof` abortam com o app velho aberto e não foram forçadas); `reco.py` intocado.
Cada defeito tem teste que reprova sem o conserto (controle negativo rodado) e commit próprio com push.

| # | defeito | causa achada | conserto | prova (e o controle negativo) | commit |
| --- | --- | --- | --- | --- | --- |
| 1 | "Gravar nota" logo depois de abrir não grava | `model.update_check` ocupava a vaga da transcrição durante a consulta inteira ao hub; a tela, com o `busy` do `rec.start`, ressincronizava e voltava a "Pronto" calada | `engine/reco_engine/modelo.py`: a consulta (revisão do hub × `.hf_revision`) não ocupa nada; só com revisão nova a troca espera o motor ocioso (`idle`, sem transcrição nem ao vivo), ocupa a vaga e chama o `reco.update_model_if_newer`. Na tela, `busy`/`refused` no Gravar e no Parar que o `state` não explica viram aviso com o motivo | `test_engine_protocol` rodada padrão: `OK modelo em voo` (consulta presa num hub falso local por `HF_ENDPOINT`, modelo de mentira no `LOCALAPPDATA` temporário → `state.transcribing=false`; hub responde 500 → ok calado, pasta intacta) e `OK modelo troca` (a troca espera gravação, `stopped` e transcrição); `app/ui/tests/passo17.cjs` (nota com `busy` → status "O Reco está ocupado com uma transcrição ou uma atualização do modelo…"; o clique seguinte grava). Controles: o motor de `ab2152d` → `transcribing: True`; a tela antiga → status "Pronto para gravar…" (2 FALHA) | `adf3fc0`, `c6be9dc` (teste com modelo de mentira, para o `--exe` também consultar); armadilha `superada_por: adf3fc0` em `ae14ee3` |
| 2 | Entrada e Saída vazias e "Microfone:  · Sistema: " antes da 1ª gravação | a tela **já** pedia `devices.list` depois do `ready`; o motor manda em `console`/`comm` o **nome** do padrão (`reco.scan_device_state`), e a tela buscava por id. O backend falso mandava ids, por isso todo teste de tela passava | `dados.ts` usa o nome; sem padrão, "Automático (padrão do Windows)"; `name: null` no `rec.start` também cai nesse texto. Backend falso com nomes, como o motor; contrato no `PROTOCOL.md` e na rodada padrão (`console` é um dos nomes da lista) | `passo17.cjs`: nomes no painel e no status antes de gravar; Windows sem padrão → "Automático…". Controle com o `dados.ts` antigo → exatamente "Pronto para gravar. Microfone:  · Sistema: " (3 FALHA) | `f2952b2` |
| 3 | `Reco Novo.log` em UTC (o `engine.log` em hora local) | o `tauri-plugin-log` usa `TimezoneStrategy::UseUtc` por padrão | `lib.rs`: `fuso_do_log()` = `UseLocal` no construtor do plugin. O `engine.log` já é local (`asctime` do Python) | `cargo test log_do_casco_na_hora_local` (deslocamento do carimbo = fuso local, UTC−3 aqui). Controle com `UseUtc` → `FAILED` | `410b316` |
| 4 | Sair registra `encerrando (eof)` no motor | o casco **não** fecha o stdin antes: escreve o `shutdown` com `write_all` + `flush` síncronos e só então solta o stdin (`processo.rs`). A corrida era do motor: o `shutdown` rodava numa thread à parte e a leitora, lendo o EOF logo atrás, marcava `eof` primeiro. Nada se perdia (os dois fecham o MP3) | `server.py`: o `shutdown` roda na própria thread leitora, então o motivo fica marcado antes de ela ler o EOF | rodada padrão: `OK saída como o casco: shutdown + EOF imediato → encerrando (shutdown) nas 16 rodadas` (fonte e congelado). Antes do conserto: 1 em 8 deu `eof` no fonte e 4 em 8 no congelado (por isso 16 rodadas; depois dele é determinístico) | `416eda6` |
| 5 | instalação silenciosa cria atalho na Área de Trabalho | o template do Tauri chama `CreateOrUpdateDesktopShortcut` sempre em `/S` e `/P`; não há opção de configuração | `app/src-tauri/windows/hooks.nsh` (`installerHooks`): o PREINSTALL lembra se o atalho já existia, o POSTINSTALL apaga só o que esta instalação silenciosa ou passiva criou; a caixa da página final vem desmarcada (`MUI_FINISHPAGE_SHOWREADME_NOTCHECKED`) | `python tools/test_nsis_atalho.py` → `falhas 0`: compila com o `makensis` do Tauri um instalador mínimo que faz o mesmo que o template, com o atalho numa pasta temporária, e roda `/S`: com os hooks não fica atalho; o que já existia fica; o controle sem os hooks deixa o atalho. O `.nsi` gerado pelo build inclui o hook (`installer.nsi:32`). **A instalação real com `/S` não foi refeita** (o app instalado é o do `aac7ca7`) | `db64f5d` |

**Provas da Fase 3 que tocam o que mudou (todas depois do último código, `db64f5d`/`c6be9dc`):**

- `python tools/test_engine_protocol.py` → 10 linhas `OK`, saída 0 (inclui as três novas; rodada de novo depois do
  `c6be9dc`); o mesmo com `--exe
  engine/dist/reco-engine/reco-engine.exe` (motor congelado novo) → 10 `OK`, saída 0; `--conferir-doc` → `22 comandos
  no registro, 22 na tabela`.
- `npm --prefix app run ui:build` → `built`; `i18n:check` → `237 chaves PT, 237 EN … 0 faltando`; `gravar.cjs` →
  `falhas 0 em 53`; `telas.cjs` → `falhas 0 em 50`; `revisao.cjs` → `falhas 0 em 21`; `paridade.cjs` → `17 de 17`;
  **novo** `passo17.cjs` → `falhas 0 em 8`.
- Fase 1 com `--url` (`ui:preview` na 1431, parado no fim pelo pid) → `anti-pulo: 0 diferenças em 23868 medições`,
  `a=0`; `contrato: 0 falhas`, `c=0`; sabotagens → `anti-pulo=1`, `contrato=1`.
- `cargo test --manifest-path app/src-tauri/Cargo.toml -- --include-ignored` → `test result: ok. 42 passed` (41 antes;
  novo `log_do_casco_na_hora_local`); `cargo clippy --all-targets` → 0 avisos.
- `python tools/test_nsis_atalho.py` → `nsis-atalho: falhas 0`.

**Instalador novo** (`powershell -ExecutionPolicy Bypass -File app/build.ps1`, completo porque o motor mudou, no
`db64f5d`, 14:50 a 15:01): `exit=0`, última linha `Instalador: C:\pt\release\bundle\nsis\Reco Novo_0.1.0_x64-setup.exe`;
smoke `ready ok=True` em 0,27 a 0,50 s nas 3 rodadas e `devices ok=True (1, 2)`; motor 115,5 s, `tauri build` 512,8 s,
631,3 s no total. Instalador de 128,7 MB (134972490 bytes), gravado às 15:01:00, SHA256
`f3f2f3918f13ed4ef5e6195d1d51990a699a6c19f0e23a56ecbf97769ccb9f05`; casco `C:\pt\release\reco.exe` SHA256
`3a11420a61566a27336129ea00a6656c33355e7f8d8fbb3bc7c73dd02f7861dc`; `reco-engine.exe` SHA256
`3b37612b11af540527853039beaae29d5416c82ec61edbf481465b14bed8ab12`. **Substitui** o `75d02dae…` do passo 17. Não
instalado nem aberto. (A mensagem do commit `3e62a2d` abrevia o hash como `f3f2f391…f7861dc`, errado: o fim
`f7861dc` é do `reco.exe`; o certo é o inteiro acima, `…ccb9f05`.)

**Efeito colateral aceito:** o casco espera o `model.update_check` antes de pedir o `app.update_check`. Com revisão
nova do modelo e uma gravação em curso, a troca espera o motor ficar ocioso, e o aviso de versão nova do app espera
junto (até o fim da gravação ou o prazo de 2 h do casco). Raro e sem perda; nenhum código mudou por isso.

**completei:** a resposta `name: null` do `rec.start` também cai em "Automático (padrão do Windows)"; o Parar com
`busy` que o motor não explica também avisa; a caixa "criar atalho na Área de Trabalho" da instalação com tela vem
desmarcada; o teste do motor fixa o contrato de `console`/`comm` como nome; o `PROTOCOL.md` diz como o
`model.update_check`, o `shutdown` e o `devices.list` se comportam agora.

**Reteste com o app velho fechado (dono na máquina):** instalar e conferir na prática a nota logo depois de abrir, os
nomes de Entrada e Saída antes de gravar, o `Reco Novo.log` em hora local, o `encerrando (shutdown)` ao Sair e a
ausência do atalho na Área de Trabalho depois do `/S`. No fechamento, passou para a Fase 4 ("Herdado da Fase 3"
no md dela), com o instalador da seção seguinte, que substitui este.

### Revisão adversarial dos consertos e fechamento (12/11/2026, 15:00 a 16:00)

Condição igual à da correção: o Reco velho do dono **aberto** (`C:\Dev\Reco\dist\Reco\Reco.exe`, pid 29256, conferido
no fim) e o dono usando a máquina. Nada abriu o Reco Novo instalado nem o casco contra o motor real; nenhum mouse ou
teclado; nenhuma prova que grava; `reco.py` intocado. Controles negativos em cópias no scratchpad da sessão, nunca no
repo (as duas mutações da tela e do casco foram feitas por `Edit` no repo, rodadas e desfeitas por `Edit`).

| # | achado do revisor | real? | o que foi feito | prova (e o controle negativo) | commit |
| --- | --- | --- | --- | --- | --- |
| 1 | médio: com revisão nova, a vaga da transcrição ficava presa durante o **download** inteiro (o `reco.update_model_if_newer` baixa e troca com ela presa): a nota e o Transcrever levavam `busy` por minutos, logo depois de qualquer trabalho | sim | `modelo.py` faz os passos do `update_model_if_newer` (o `reco.py` não muda): baixa numa temporária **sem** a vaga, espera o motor ocioso, ocupa a vaga só para renomear e mover; troca que falha no meio devolve a pasta antiga; a temporária sai em todo caminho | `OK modelo em voo` ganhou a 2ª rodada: o hub falso diz que há revisão nova e segura o download → `state.transcribing=false`; o download falha → pasta intacta e nenhuma `reco_model_*` no `TEMP` do teste. `OK modelo troca` (download com a vaga livre, uma transcrição entra no meio, troca só depois). `OK modelo pasta` (troca e devolução). Controle com a vaga ocupada antes do download → `FALHOU vaga` (`[True]`) e `FALHOU voo` (`transcribing: True`) | `058acfc` |
| 2 | baixo: o teste não cobria a guarda do ao vivo nem `starting`/`stopping`/`paused`; e, anterior, o abort soltava `live_active` antes de o worker do ao vivo terminar | sim, os dois | casos novos no `run_espera_vaga`; `_stop_live` sem esperar descarta a fila e só solta `live_active` quando o worker termina (teto de 120 s), com contador `live_gen` para a soltura atrasada não apagar um ao vivo novo; `make_live` não liga ao vivo com o worker anterior ainda gerando (`live_suprimido`) | `OK modelo troca` (6 estados) e `OK ao vivo solto no fim`. Controles: sem `or core.live_active` → `FALHOU vaga a troca rodou com o motor em idle, ao vivo=True`; com o `recording.py`/`conclude.py` de antes → `FALHOU vivo` (o primeiro `check`, o `discard`, já reprova) | `058acfc` |
| 3 | baixo: depois de uma nota, a Saída e o status viravam "Automático (padrão do Windows)" (a nota manda `sys` sem nome) | sim | `gravar.ts` não escreve a Saída na nota; o backend falso devolve `sys` vazio na nota, como o motor | `passo17.cjs` → `falhas 0 em 9` (caso novo). Controle com a regra antiga (`|| true` por `Edit`, desfeito) → `FALHA depois de uma nota, a Saída segue com o nome do alto-falante: Automático (padrão do Windows)` | `456eb23` |
| 4 | baixo: o teste do fuso via só a função, não o `run()` | sim | `plugin_de_log()` monta o plugin num lugar só e o `run()` o usa. Os campos do `Builder` do plugin são privados e o `split` pede um `AppHandle`, então o teste novo `log_do_casco_usa_o_fuso` confere pelo fonte (só o código fora de `#[cfg(test)]`): um `Builder::new()`, com `.timezone_strategy(fuso_do_log())`, e o `run()` com `.plugin(plugin_de_log().build())` | `cargo test … log_do_casco` → `2 passed`. Controle sem o `.timezone_strategy(...)` → `FAILED` | `69636f0` |
| 5 | baixo: `model_info` sem prazo; conexão travada segurava o `app.update_check` até 2 h | sim | `timeout=15` (`CONSULTA_TIMEOUT_S`) | `OK modelo prazo: … timeout=15 s` (API falsa no processo). Controle sem o `timeout` → `FALHOU prazo` | `058acfc` |

**Provas da Fase 3 depois do último código (`69636f0`), o "Gatilho que fecha" inteiro:**

- `python tools/test_engine_protocol.py` → 13 linhas `OK` (5 novas do modelo e do ao vivo); `--exe
  engine/dist/reco-engine/reco-engine.exe` (motor congelado neste build) → as mesmas 13; `--conferir-doc` → `22
  comandos no registro, 22 na tabela`.
- `cargo test --manifest-path app/src-tauri/Cargo.toml -- --include-ignored` → `test result: ok. 43 passed` (42 antes);
  `cargo clippy --all-targets` → 0 avisos.
- `npm --prefix app run ui:build` → `built`; `i18n:check` → `237 chaves PT, 237 EN … 0 faltando`; `passo17.cjs` → `falhas
  0 em 9`; `gravar.cjs` → `falhas 0 em 53`; `telas.cjs` → `falhas 0 em 50`; `revisao.cjs` → `falhas 0 em 21`;
  `paridade.cjs` → `17 de 17 presentes`; `python tools/test_nsis_atalho.py` → `falhas 0`.
- Fase 1 com `--url` (`ui:preview` na 1431, parado no fim pelo pid) → `anti-pulo: 0 diferenças em 23868 medições`,
  `a=0`; `contrato: 0 falhas`, `c=0`; sabotagens → `anti-pulo=1`, `contrato=1`.
- Passo 1, prova nova → `s=0`; controle (`data-direcao="b"` esperado) → `s=1`.
- Passo 18 → `git diff --stat 9fd4f95 -- docs/ARQUITETURA.md README.md CLAUDE.md` lista os três; `gate-claude-md` →
  `Passed` (5948 bytes).

**Instalador final da Fase 3** (o motor mudou, então build completo; feito do `69636f0`). A 1ª rodada (15:28) congelou
o motor e passou no smoke, mas o `npm ci` falhou com `-4048` porque eu deixei o `ui:preview` aberto ao mesmo tempo
(armadilha nova); servidor parado, `app/build.ps1 -SemCongelar` (15:30:56 a 15:39:31) com o motor congelado dessa
mesma rodada (15:30:29) → `exit=0`, última linha `Instalador: C:\pt\release\bundle\nsis\Reco Novo_0.1.0_x64-setup.exe`;
smoke `ready ok=True` em 0,27 a 0,28 s e `devices ok=True (1, 2)`; `tauri build` 510 s, 514,6 s no total.

- Instalador: 128,8 MB (135038252 bytes), gravado às 15:39:31, SHA256
  `a06809a6909a84cd4e8dd35b4c335678f8f8f6061b6453292888cb50a0f4f422`.
- Casco `C:\pt\release\reco.exe` SHA256 `551674c6b4a4f4b00bc07ca029c4010b86ac16d85622419fb4d466b733ee598a`.
- Motor `engine\dist\reco-engine\reco-engine.exe` SHA256 `e49f20127be43ba1d553003aa0c5c3b9d082d456ae85daa8e8a9e0ffc53daa2f`.
- **Substitui** o `f3f2f391…ccb9f05`. Não instalado nem aberto: o app instalado na máquina continua o do `aac7ca7`.

**Passo 18 fechado:** README nas duas línguas troca "ainda não é o app de uso" por "em teste", ensina a instalar
pelo instalador do build (pasta, atalho, Sair pela bandeja, desinstalar, aviso do SmartScreen) e diz que o Reco Novo e
o Reco atual nunca abrem juntos (e como trocar sem gravar). ARQUITETURA, `PROTOCOL.md` e a tabela do md acompanham a
troca do modelo. Os tempos do app instalado estão na seção "Passo 17", tabela D12, por build: passo 16 (janela visível)
Gravar habilitado em 1,156 s de mediana, `aac7ca7` (`--oculto` com CDP) 0,781 s, contra 1,515 s do velho; ícone até a
janela 0,047 s (só no build do passo 16).

### Fechamento: o que a Fase 3 entrega e o que passa para a Fase 4

- **Provado no app instalado (`aac7ca7`):** tudo da seção "Passo 17" (colar com aspas, `ffprobe`, lados, nota,
  transcrever, Sair gravando, D11 nos dois sentidos, repasse, D12).
- **Provado só fora do app instalado** (backend falso, `cargo test`, motor do fonte e congelado): os 5 defeitos do passo
  17 e os 5 achados acima. O reteste no app instalado é o primeiro bloco da Fase 4 ("Herdado da Fase 3", no md dela),
  junto com o que nunca foi visto no build final: hover e clique no ícone, ícone fora do vermelho com o motor caído,
  clique dentro da janela do hover, minimizar com `skipTaskbar`, atalho por tecla física, mutex do repasse.
- **Máquina:** Reco velho aberto e intocado (pid 29256); nenhum processo meu sobrando (porta 1431 livre); o repo só
  com os commits desta rodada.

### A lista "O que falta para fechar", item por item (resolvida em 12/11)

1. **Passo 17:** feito no instalador do `aac7ca7` (seção "Passo 17"): `Reco.lnk` `False` antes e depois; colar,
   `ffprobe`, nota, transcrever, Sair gravando, `stopping` real (0,452 e 0,469 s), D11 nos dois sentidos, repasse e
   máquina como estava. Hover, clique no ícone e ícone fora do vermelho só no build anterior (sem mouse a pedido do
   dono): passam para a Fase 4.
2. **Resto do passo 18:** README com a instalação, tempos do app instalado neste relatório (por build) e `[x]`.
3. **Passo 1:** prova trocada por "a skin padrão é a A" (nota datada no md), rodada → `s=0`, `[x]`.
4. **Fechar:** 17 e 18 marcados; índice (coluna "estado" e Pendente com a Fase 4), hub e diário atualizados.
