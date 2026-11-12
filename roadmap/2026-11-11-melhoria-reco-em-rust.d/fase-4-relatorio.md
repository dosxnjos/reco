## Relatório de execução — Fase 4 (2026-11-12, sessão 4c65eb01)

> **Parcial.** Esta rodada adianta os passos 1 a 8 que não dependem do dono. Condição: o Reco velho do dono **aberto**
> (`dist\Reco\Reco.exe`) e o dono usando a máquina. Nada instalou, desinstalou, abriu o Reco Novo ou o casco contra o
> motor real; nenhum mouse ou teclado; nenhuma prova que grava. As gravações dele foram lidas só por **cópia**, numa
> pasta temporária fora do repo; nomes de gravação viram G01 a G10 aqui (repo público). Nada foi publicado no GitHub.

Fase: [fase-4](../2026-11-11-melhoria-reco-em-rust-fase-4.md) · índice: [Reco em Rust](../2026-11-11-melhoria-reco-em-rust.md).

### Frescor (item 5 de "Como retomar")

- `git diff --stat 7c5c1a1..HEAD -- reco.py tray.py tools/varrer_silencio.py tools/varrer_acervo.py tools/reparar_duracao.py tools/test_antiloop.py tools/transcrever.py`
  → vazio: as linhas citadas desses arquivos valem como escritas em 11/11 (conferidas uma a uma as do `reco.py` e das ferramentas).
- O que mudou desde 11/11 e o md citava: `app/` e `engine/` (Fase 3). Notas datadas no md: passo 1 (sem `mainBinaryName`,
  binário `reco.exe`), passo 6 (nome com espaço, cópias), passo 7 (nunca `--forcar` na pasta do app), passo 8 (`app_name`
  no `lib.rs:207`, outras ocorrências, formato do log), passo 14 (regex do `ready em`) e F4-D9 (o aviso de versão compara
  com o `reco.APP_VERSION`, não com o casco).

### Reserva (passo 2)

- Cópias feitas às 15:57 de 12/11 por `robocopy … /E` (rc `1` nas duas = arquivos copiados, sem erro), em ~5 s.
- `Reco.exe` da reserva: SHA256 `6F9A4599B336DBEE853AA4613B3200A4622C4EB3481F0170987CE966C4EF442F`, data do arquivo
  `2026-11-11 19:03:45` (o mesmo do `dist`). Nada foi apagado; o velho seguiu aberto (mutex `True` e o processo com o
  caminho do `dist` depois do smoke). O `--selftest` sai antes do mutex e da janela.

### A régua (passos 4 e 5)

- Reusa por import `reparar_duracao.declared_and_real`, `varrer_silencio.medir`, `varrer_acervo.mede`/`resume`,
  `test_antiloop.pior` e `transcrever.diarizada` (e o regex dos rótulos que ela monta, para o `pior` não contar `Eu:`).
- **Achado no passo 5:** o `head -c 3000000` de hoje cortou no meio de um frame; o último pacote não decodifica e o
  `declared_and_real` (e o `varrer_silencio.medir`) desistem com `InvalidDataError`. Em 11/11 o mesmo corte, noutro
  arquivo, caiu em fronteira. A régua mede a duração pulando o pacote ruim (`duracao_tolerante`, 12 linhas) e ainda diz
  `xing=ERRADO`; o arquivo sai `FALHOU (xing, cauda-corrompida)`. Os scripts antigos não mudaram.
- **Conserto da régua depois do advisor:** a primeira versão media o `pior` no `x.txt` inteiro sem os rótulos, então
  quatro turnos curtos iguais ("sim" / "sim" / "sim" / "sim") dariam `pior=4` e FALHOU. Agora mede fala a fala (uma
  linha por fala, como o `test_antiloop` vê um canal só) e pega o maior. Prova em cópia com `x.txt` de mentira: quatro
  turnos "sim" → `pior=1 -> ok`; uma fala `a b a b a b a b` → `pior=4 -> FALHOU (loop)`.
- **Achado no passo 4:** a gravação mais nova com `x.txt` do app velho tem um token alucinado pelo Whisper (fora do
  português) repetido 4 vezes **dentro de uma fala só** (a de 555 palavras): `pior=4`, `FALHOU (loop)`, com a régua
  nas duas versões. A régua segue o md (`pior` > 3 reprova); é defeito real do app
  velho, e o passo 18 lê o novo contra esta linha de base. Se o critério reprovar gravação boa do app novo pelo mesmo
  motivo, a revisão é do critério (`pior` sobre o arquivo inteiro × o `test_antiloop`, que mede só as 6 janelas mais fracas).

### Linha de base do app velho (passo 6)

As 10 gravações `gravacao_reco_*` mais recentes da pasta do app (sem `_alinhado`, por data de modificação, de 20/10 a
11/11/2026), copiadas com o `x.txt` ao lado para uma pasta temporária fora do repo; a pasta real não foi tocada.
`python tools/paridade.py <as 10 cópias> --anonimo` → rc 1 (por dois FALHOU de conteúdo, não de leitura), 25 s:

| G | dur (s) | xing | r_zero_inicio | mic_zero_max | alinhamento | txt | pior | veredito |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| G01 | 659,5 | ok | 0 | 0 | salto | diarizado | 4 | FALHOU (loop) |
| G02 | 594,7 | ok | 594 | 0 | sem correlação | ausente | - | FALHOU (sistema-mudo) |
| G03 | 409,4 | ok | 0 | 0 | ok | diarizado | 2 | ok |
| G04 | 1428,0 | ok | 250 | 1 | salto | ausente | - | ALERTA (r_zero_inicio, salto) |
| G05 | 271,4 | ok | 0 | 0 | ok | diarizado | 3 | ok |
| G06 | 26,2 | ok | 0 | 0 | ok | ausente | - | ok |
| G07 | 1573,6 | ok | 0 | 0 | ok | ausente | - | ok |
| G08 | 1286,8 | ok | 0 | 5 | salto | ausente | - | ALERTA (salto) |
| G09 | 622,0 | ok | 0 | 0 | ok | ausente | - | ok |
| G10 | 306,8 | ok | 0 | 0 | ok | ausente | - | ok |

- **Contagem:** `ok=6, ALERTA=2, FALHOU=2`; alinhamento `ok=6, salto=3, sem_correlacao=1`. Salto em 3 de 9 medíveis
  (33%), perto dos 16 de 43 (37%) de 30/08. Xing certo nas 10; nenhum erro de leitura (a prova passa: 10 linhas).
- **G02:** o canal do sistema em zero exato do começo ao fim (594 de 594 s), sem correlação. Ou o dono gravou só a
  própria voz (aí `--sem-sistema` é o certo), ou é o incidente do `soundcard` que fabrica silêncio (o do PDI de 29/09).
  A régua não sabe qual; o app velho não acusou na hora. Fica como referência: o app novo grava pelo mesmo `reco.py`.
- **G01:** loop do Whisper no `x.txt` do app velho (acima). **G04:** sistema mudo nos primeiros 250 s (acima dos 73 s
  da melhor reunião boa) e salto.
- Só 3 das 10 têm o `x.txt` do app; as outras 7 têm só o `x.mp3.txt` do transcritor dos agentes (texto corrido antigo),
  que a régua não lê. Por isso o `--exigir-txt` do passo 18 vale para as gravações novas, não para esta base.

### Passo 8: troca do nome e instalador (16:09 a 16:20)

- **O que mudou** (commit `818c257`): `productName` `Reco`; `app_name("Reco")` do autostart (`lib.rs:207`); o texto da
  versão em Opções (`Reco {app} · motor {motor}`, PT e EN); comentários do `lib.rs`, `atalho.rs`, `build.ps1` e
  `hooks.nsh` (este segue só ASCII); `boot.py` loga `ready em <n> s`. `identifier` (`io.github.dosxnjos.reco`) e
  `instancia.rs` (mutex `Local\Reco.SingleInstance`) intocados: `git diff 037ef65 HEAD -- app/src-tauri/src/instancia.rs`
  → vazio.
- **Provas antes do build:** `npm --prefix app run ui:build` → `built`; `i18n:check` → `237 chaves PT, 237 EN … 0 faltando`;
  `gravar.cjs` 0 em 53, `telas.cjs` 0 em 50, `revisao.cjs` 0 em 21, `paridade.cjs` 17 de 17, `passo17.cjs` 0 em 9;
  `cargo test … -- --include-ignored` → `ok. 43 passed` (inclui os 2 de `instancia`); `cargo clippy --all-targets` → 0
  avisos; `python tools/test_nsis_atalho.py` → `falhas 0`; `python tools/test_engine_protocol.py` (rodada padrão, sem
  as que gravam) → 13 linhas `OK`. O motor do fonte, com `hello` + `shutdown` → stderr
  `… INFO reco_engine.boot: ready em 0.17 s` e `encerrando (shutdown)`, exit 0.
- **Build** (`app/build.ps1` completo, porque o motor mudou; feito do `818c257`, e o `60122c7` só muda `tools/` e
  roadmap): `exit=0`; smoke do motor congelado `ready ok=True` em 1,67 / 0,47 / 0,53 s e `devices ok=True (1, 2)`; tempos:
  motor 94,9 s, `npm ci` 2,8 s, interface 2,1 s, `tauri build` 555 s, total 655,8 s. Pasta instalada calculada: 495,5 MB.
- **Hashes (SHA256):**
  - Instalador `C:\pt\release\bundle\nsis\Reco_0.3.0_x64-setup.exe`: 128,8 MB (135022313 bytes), 16:20:10,
    `76C890E88B2B10BC6CBBAB191DB0CB6BECB5E6D097E4A98D7209C1875B1A4D90`.
  - Casco `C:\pt\release\reco.exe`: 4513792 bytes, `E0309C6F7339082F9118ECE615958F7E548A9C7B164A648E55D58B38445A9B77`.
  - Motor `engine\dist\reco-engine\reco-engine.exe`: 25162376 bytes, 16:10:43,
    `214822A8331C349ED94A8321E14DE4E1DBD71F37E2D825E0622D51CF220BCEE0`.
  - Substitui o `a06809a6…a0f4f422` (`Reco Novo_0.1.0`) da Fase 3 como instalador a usar no passo 9.
- **Sem colisão com o Reco velho, lido no `installer.nsi` gerado** (`C:\pt\release\nsis\x64\`): `PRODUCTNAME "Reco"`,
  `VERSION "0.3.0"`, `INSTALLMODE "currentUser"`, `MAINBINARYNAME "reco"`, `BUNDLEID "io.github.dosxnjos.reco"`,
  `!include …\windows\hooks.nsh`. Nenhum `FindProcess`/`KillProcess` no `installer.nsi` nem no `utils.nsh` (0 e 0): o
  `CheckIfAppIsRunning` registra no Restart Manager **o caminho** `$INSTDIR\reco.exe`, então o `Reco.exe` do dono em
  `dist\` (mesmo nome de imagem) não é alvo. A desinstalação só apaga `$SMPROGRAMS\Reco.lnk` se o alvo dele for o exe
  instalado (`IsShortcutTarget`). A pasta de instalação passa a ser `%LOCALAPPDATA%\Reco`, a dos modelos (F4-D4): o
  passo 10 prova que instalar e desinstalar não os apagam.
- **Nota do frescor:** o `app_name` estava no `lib.rs`, não no `atalho.rs`; o `^ready em ` do passo 14 não casaria com o
  formato do log (os dois corrigidos no md por nota datada).

### Decisões técnicas — Fase 4 (esta rodada)

| decisão | motivo | confiança | o que reverteria |
| --- | --- | --- | --- |
| Gravações do dono só por cópia em pasta temporária; nomes como G01 a G10 | regra da tarefa e repo público; o `--forcar` na pasta do app reescreveria o `x.txt` dele | alta | — |
| `pior` fala a fala no `x.txt` diarizado | o arquivo inteiro sem rótulos acusaria turnos curtos iguais como loop (achado do advisor) | alta | o passo 18 mostrar loop que atravessa falas e escapa |
| Duração tolerante a pacote final quebrado na régua | o corte no meio de um frame derrubava a leitura antes de medir o Xing; o arquivo de processo morto pode ter o mesmo rabo | média | preferir que todo rabo quebrado saia só como erro de leitura (também FALHOU) |
| Linha `ready em <n> s` com o `import_s` (do início da thread do import até o `ready`) e só no `ready` sem erro | o passo 14 casa a linha no `engine.log`; `ready` com erro não é "pronto" | alta | o passo 14 precisar do tempo desde o início do processo (o laço já mede de fora, pelo cronômetro) |
| README: só as duas frases que o nome novo deixaria falsas (nome do instalador e o atalho que "nunca trocava"), sem prometer nada sobre desinstalar e modelos | o passo 20 reescreve o resto; o passo 10 ainda não provou a desinstalação | alta | — |
| `reco.py` intocado; o aviso de versão contra o `reco.APP_VERSION` só anotado (F4-D9) | "O que esta fase NÃO faz": o `reco.py` não cresce; hoje P23 passa | média | decidir o release público (Pendente) |

### Passos

| passo | estado | prova (comando → o que veio) |
| --- | --- | --- |
| 1 nomes e versão | [x] | `node -p "…[c.productName,c.version,c.identifier,c.mainBinaryName].join(' ')"` → `Reco Novo 0.3.0 io.github.dosxnjos.reco ` (o 4º vazio: sem `mainBinaryName`, o binário é `reco.exe`) |
| 2 reserva | [x] | conferência do md → `True`. Além dela, soma da árvore inteira (caminho relativo + SHA256 de cada arquivo): `dist\Reco` e `Reco-reserva\Reco` → `4010 arquivos, 891997220 bytes, soma 9126509F…9C11DCCB` nos dois; `Reco\models` e `Reco-reserva\models` → `46 arquivos, 828097157 bytes, soma 45BBD98A…400D7F0C` nos dois. Smoke `Start-Process …\Reco-reserva\Reco\Reco.exe --selftest -Wait` → `exit=0`, `reco_selftest.txt` reescrito depois do lançamento (`novo=True`), `transcription_available=True`, `resolved(AUTO)=GPU` |
| 3 foto do que o instalador toca | [x] | `Reco.lnk` → `sem lnk`; `reg query …\Run /v Reco` → rc `1` (não existe); `_migracao` → `2`; modelos → `828097157` bytes (789,7 MiB). Extras: `Reco Novo.lnk` existe, `/v "Reco Novo"` rc `1`, Reco Novo instalado (`uninstall.exe` presente, `reco.exe` SHA256 `b1eef366…ea3d9dbd`, o do `aac7ca7`) |
| 4 `tools/paridade.py` | [x] | `python tools/paridade.py <cópias de 2 gravações recentes com x.txt> --anonimo` → `dur=409.4 xing=ok r_zero_inicio=0 mic_zero_max=0 alinhamento=ok txt=diarizado pior=2 -> ok` (a G03 da linha de base) e `dur=271.4 … pior=3 -> ok` (a G05), `PASSOU`, rc 0; 213 linhas; `ruff` e C901/PLR0912/PLR0915 limpos. A 3ª recente com `x.txt` (a G01 da linha de base) sai `dur=659.5 … alinhamento=salto … pior=4 -> FALHOU (loop)` (abaixo). Nesta linha, o `--anonimo` numerou G01/G02 pela ordem da chamada; daqui em diante G01 a G10 são os da linha de base |
| 5 prova negativa | [x] | `python tools/paridade.py trunc_reco.mp3 mono.mp3` → `trunc_reco.mp3 dur=252.2 xing=ERRADO leitura=ERRO txt=ausente pior=- -> FALHOU (xing, cauda-corrompida)`, `mono.mp3 dur=26.2 xing=ok canais=nao-estereo … -> FALHOU (nao-estereo)`, `REPROVOU`, rc 1. Controle extra: corte em fronteira de frame → `xing=ERRADO r_zero_inicio=0 … -> FALHOU (xing)`; flag desconhecida → rc 2 |
| 6 linha de base | [x] | 10 linhas (tabela "Linha de base"), `vereditos: ok=6, ALERTA=2, FALHOU=2 \| alinhamento: ok=6, salto=3, sem_correlacao=1`; nenhum FALHOU por leitura. Comando do md trocado por cópias e lista entre aspas (nota no md) |
| 7 determinismo do transcritor | [x] | cópia da G05 (271 s, fala dos dois lados, `x.txt` do app ao lado) em pasta temporária; 2 rodadas seguidas `python tools/transcrever.py <cópia> --forcar --modelo large-v3-turbo --device AUTO` (o config: `large-v3-turbo`, `AUTO`; modo `diarizado + AEC`) → rc 0 em 95 s e 105 s; `cmp det1.txt det2.txt && echo IGUAL` → `IGUAL` (3215 bytes). Extra: `cmp det1.txt <x.txt do app>` → igual. Linha de base do byte a byte: `python tools/paridade.py <a cópia> --txt-contra-script` → `dur=271.4 xing=ok … pior=3 script=igual -> ok`, `PASSOU`, rc 0 (1 min 46 s, com o build do passo 8 rodando ao lado) |
| 8 nome "Reco" e instalador | [x] | depois do build: `grep -rln "Reco Novo" app --exclude-dir=node_modules` → nada (rc 1); `ls C:/pt/release/bundle/nsis/` → `Reco_0.3.0_x64-setup.exe` (o `Reco Novo_0.1.0_x64-setup.exe` antigo continua lá, sem uso); `powershell -ExecutionPolicy Bypass -File app/build.ps1` → `exit=0`, última linha `Instalador: C:\pt\release\bundle\nsis\Reco_0.3.0_x64-setup.exe`. **Não instalado nem aberto** |

### O que falta (passos 9 a 25) e com quem

- **Dono (Gabriel), na ordem:**
  1. Sair do Reco velho pela bandeja, sem gravação em curso, quando puder ficar uns 30 a 60 min sem gravar. Com ele
     fechado, a sessão roda as checagens que gravam (`test_engine_protocol.py --gravar 5 --concluir` e `--eof 25`,
     herdadas da Fase 3), desinstala o "Reco Novo" (`aac7ca7`, ainda instalado) e instala o `Reco_0.3.0` (passos 9 e 10).
     **Ele não deve rodar o instalador novo por conta própria**: o passo 9 desinstala o "Reco Novo" antes e confere os
     modelos.
  2. Os testes que pedem a mão dele: atalho Ctrl+Shift+R por tecla física (11), hover e clique no ícone, minimizar
     (herdado), reiniciar o Windows 3 vezes para o "a frio" do passo 14 (combinar a hora), e o checklist manual do 17.
  3. Usar o app novo no dia a dia por 5 dias ou mais, com as 6 gravações G1 a G6 de F4-D1, e dizer "aprovo" (18).
- **Sessão (técnico, depois do passo 9):** passos 10 a 16 (modelos, atalho, mutex nos dois sentidos, autostart, D12, D11
  no instalado, ensaio da volta), 17 e 19 (paridade e ouvido dos agentes), 20 a 25 (README completo com screenshot,
  ARQUITETURA, CLAUDE.md, armadilhas, hub e fechamento).
- **Decisão pendente que esta rodada achou:** antes de um release público `v0.3.0`, o aviso de versão do app novo
  compara com o `reco.APP_VERSION` (0.2.0) e ficaria acusando versão nova para sempre (nota na F4-D9 do md).

### completei:

- Soma da árvore inteira da reserva (4010 arquivos e os 46 dos modelos), além do `Reco.exe` que o md pedia.
- Régua com `--anonimo`, contagem dos vereditos e do alinhamento, duração tolerante a pacote final quebrado e `pior` fala
  a fala; controles negativos extras (corte em fronteira de frame, loop de mentira, quatro turnos curtos).
- `cmp` do transcritor contra o `x.txt` do app (igual), além das duas rodadas.
- README nas duas línguas sem as duas frases que o nome novo tornaria falsas.
- Leitura do `installer.nsi` gerado: nenhum fechamento de processo por nome que pegaria o `Reco.exe` do dono.

### Máquina no fim

- Reco velho aberto e intocado: pid 29256, `C:\Dev\Reco\dist\Reco\Reco.exe` (conferido depois do build).
- `Documents\Reco`: os mesmos 213 arquivos, nenhum novo, sumido ou com tamanho/data mudados (foto das 15:55 contra o
  fim). `~/.reco_config.json` igual à cópia das 15:55 (`cmp`).
- Cópias das gravações (linha de base, determinismo, prova negativa) no scratchpad da sessão, fora do repo; nada de
  áudio ou transcrição no git. `%LOCALAPPDATA%\Reco-reserva` fica (F4-D3, até a Fase 7).
- Reco Novo `aac7ca7` segue instalado; nenhum instalador ou desinstalador rodou.

### Commits

| hash | o quê |
| --- | --- |
| `037ef65` | passo 1 (0.3.0) e as notas de frescor do md |
| `7f21ea0` | passos 2 e 3 (reserva e foto) |
| `5037e1f` | passos 4 e 5 (`tools/paridade.py`, `docs/TOOLS.md`) |
| `818c257` | passo 8, fonte (nome `Reco`, `ready em`, README) — o instalador sai deste código |
| `60122c7` | passos 6 e 7 e o `pior` fala a fala |
