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
- **Segundo conserto depois do advisor:** com `--txt-contra-script`, `script=erro` (o transcritor falhou) e
  `script=sem-txt` saíam `ok`. Agora tudo que não for `igual` reprova. Prova: cópia sem `x.txt` + a flag →
  `… script=sem-txt -> FALHOU (script-sem-txt)`, `REPROVOU`, rc 1. As provas dos passos 4 e 5 rodaram de novo no
  código final, com as mesmas linhas da tabela (`ok`, `ok`, `PASSOU`, rc 0; `FALHOU (xing, cauda-corrompida)`,
  `FALHOU (nao-estereo)`, rc 1).
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
| G10 | 306,8 | ok | 0 | 2 | ok | ausente | - | ok |

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
  O motor **congelado** deste build, com `hello` + `shutdown` → stderr `… INFO reco_engine.boot: ready em 0.59 s` e
  `encerrando (shutdown)`, exit 0: a linha que o passo 14 casa está no exe que vai no instalador.
- **Hashes (SHA256):**
  - Instalador `C:\pt\release\bundle\nsis\Reco_0.3.0_x64-setup.exe`: 128,8 MB (135022313 bytes), 16:20:10,
    `76C890E88B2B10BC6CBBAB191DB0CB6BECB5E6D097E4A98D7209C1875B1A4D90`.
  - Casco `C:\pt\release\reco.exe` (o arquivo de saída do build, com data 1 s depois do instalador; não conferi se é
    byte a byte o que vai dentro dele): 4513792 bytes, `E0309C6F7339082F9118ECE615958F7E548A9C7B164A648E55D58B38445A9B77`.
  - Motor `engine\dist\reco-engine\reco-engine.exe`: 25162376 bytes, 16:10:43,
    `214822A8331C349ED94A8321E14DE4E1DBD71F37E2D825E0622D51CF220BCEE0`.
  - Substitui o `a06809a6…a0f4f422` (`Reco Novo_0.1.0`) da Fase 3 como instalador a usar no passo 9.
- **Sem colisão com o Reco velho, lido no `installer.nsi` gerado** (`C:\pt\release\nsis\x64\`): `PRODUCTNAME "Reco"`,
  `VERSION "0.3.0"`, `INSTALLMODE "currentUser"`, `MAINBINARYNAME "reco"`, `BUNDLEID "io.github.dosxnjos.reco"`,
  `!include …\windows\hooks.nsh`. Nenhum `FindProcess`/`KillProcess` no `installer.nsi` nem no `utils.nsh` (0 e 0): o
  `CheckIfAppIsRunning` registra no Restart Manager **o caminho** `$INSTDIR\reco.exe`, então o `Reco.exe` do dono em
  `dist\` (mesmo nome de imagem) não é alvo. A desinstalação só apaga `$SMPROGRAMS\Reco.lnk` se o alvo dele for o exe
  instalado (`IsShortcutTarget`). Apagão recursivo (`RmDir /r`) só em `$APPDATA\${BUNDLEID}` e
  `$LOCALAPPDATA\${BUNDLEID}` (`installer.nsi:8083-8084`, só com a caixa "apagar dados"); o `$INSTDIR` sai com
  `RMDir` sem `/r` (`:8021`) depois de apagar arquivo por arquivo o que instalou. A pasta de instalação passa a ser `%LOCALAPPDATA%\Reco`, a dos modelos (F4-D4): o
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

### Revisão adversarial (12/11/2026, 16:30 a 17:10)

Revisor em subagente, só com MP3 sintéticos (nenhuma gravação do dono lida por ele). Cinco achados: 1 alto, 2 médios,
2 baixos; todos reais, com uma parte do 5 falsa (abaixo). Frescor antes do primeiro toque: `git diff --stat 7c5c1a1..HEAD`
nos arquivos de `tools/` que os passos citam → vazio; as linhas que a revisão cita (`paridade.py:99-100`, `:138-141`,
`:163`, `engine/reco_engine/__init__.py:7`, `motor.ts:65`) conferidas no código de hoje.

- **1 (alto) Lado mudo passava quando o outro soa desde o 1º frame.** Reproduzido: sistema em zero e mic com seno desde
  t=0 → `r_zero_inicio=0 … -> ok`; o espelhado → `mic_zero_max=59 -> ok`. Medido pelo próprio `reco.MP3Writer` (o
  container do app), não só pelo encoder cru do revisor: `varrer_silencio.medir` → `r_total=59` de 60 e `mic_maior=59`
  de 60; com ruído de banda larga saturado, 120 s → 335 amostras não-zero no lado mudo, a última em 0,0209 s. O
  vazamento é do 1º frame e não cresce com o sinal, então a tolerância é de 1 s. **Conserto:** `limiar_mudo(seg)` =
  `seg - 1` (com piso: arquivo de menos de 2 s exige todos os segundos, senão todo arquivo de 1 s sairia mudo); o
  sistema usa `r_total >= limiar`, o mic `mic_maior >= limiar`. **Prova:** os 5 arquivos do revisor → `rmudo`,
  `rmudo_cedo`, `rmudo_suave` `FALHOU (sistema-mudo)`, `micmudo_cedo` `FALHOU (mic-mudo)`, `bom` `ok`, rc 1. Linha de
  base nas 10 cópias de novo → as 10 linhas `G…` idênticas às de antes (`diff` vazio), `ok=6, ALERTA=2, FALHOU=2`.
  Passo 4 de novo (G05 e G03) → `ok`, `ok`, `PASSOU`, rc 0. **Limite que fica (só ALERTA, não reprova):** o mesmo
  vazamento zera o `r_zero_inicio` quando o mic soa desde o 1º frame, e o ALERTA de sistema mudo no começo não sai
  nesse caso (anotado no docstring e no `docs/TOOLS.md`). Candidata a armadilha no passo 23.
- **2 (médio) A prova negativa do passo 5 passava com a régua quebrada.** Reproduzido o raciocínio: a prova só casava
  veredito e rc. **Conserto:** `tools/test_paridade.py` (163 linhas), MP3 sintéticos pelo `reco.MP3Writer` numa pasta
  temporária, 15 casos que casam veredito **e a lista exata de motivos** (mais 4 de rc do `main`). **Prova:**
  `python tools/test_paridade.py` → `paridade: falhas 0`, rc 0, 17 s. Contra cópias da régua com uma linha mudada
  (`--regua <cópia>`): Xing desligado → `falhas 2` (os dois cortes); estéreo desligado → `falhas 1` (mono); sem a
  tolerância de 1 s → `falhas 2`; sem o piso → `falhas 1` (arquivo de 1 s); `vazio` fora do `--exigir-txt` → `falhas 1`;
  loop desligado → `falhas 1`; sistema mudo desligado → `falhas 2`; a régua de antes da revisão (`git show HEAD:…`) →
  `falhas 3` (sistema mudo, mic mudo, txt vazio). **Achado do teste:** o "rabo corrompido" é o **cabeçalho** do último
  frame cortado (1 a 3 bytes depois da fronteira dão `InvalidDataError`; de 4 bytes em diante o decoder aceita o frame
  curto). O truncado real da prova antiga terminava num pacote de 3 bytes. O md do passo 5 diz isso por nota datada, e
  a prova do passo passa a ser o teste (repetível, sem gravação do dono).
- **3 (médio) `x.txt` vazio passava com `--exigir-txt`.** Reproduzido: `gravacao_reco_vazio` + a flag →
  `txt=vazio pior=1 -> ok`. **Conserto:** com `--exigir-txt`, `vazio` reprova, sem limiar de duração (a flag é do passo
  18, reunião real). **Prova:** o mesmo arquivo → `FALHOU (txt-vazio)`, rc 1; sem a flag segue `ok` (caso do teste).
- **4 (baixo) Motor em 0.1.0.** Real. **Conserto:** `engine/reco_engine/__init__.py` em `0.3.0`, junto com o casco;
  `docs/PROTOCOL.md` (linha do `hello`) diz que o `engine_version` acompanha a versão do casco a cada instalador e que
  `protocol` só sobe se o contrato quebrar. A checagem `tools/engine_checks_proto.py`, que tinha `"0.1.0"` cravado,
  compara com o `__version__` lido do fonte (assim um motor congelado velho reprova). **Prova:** `python
  tools/test_engine_protocol.py` (rodada padrão, sem gravar) → 13 linhas `OK`, rc 0; `--conferir-doc` → `OK doc: 22
  comandos no registro, 22 na tabela do PROTOCOL.md, nenhum faltando`, rc 0. `git diff --stat 818c257 9b6294b -- app
  engine reco.py tray.py` → só `engine/reco_engine/__init__.py`. O motor mudou, então o build foi refeito (abaixo).
  Lacuna do teste novo: nenhum caso dele produz `ALERTA` (as regras de alerta seguem provadas só pela linha de base, G04 e G08).
- **5 (baixo) Reserva incompleta.** Real em duas partes, falso numa:
  - Config: copiado `~/.reco_config.json` para `%LOCALAPPDATA%\Reco-reserva\reco_config.json` às 16:51:39, `Get-FileHash`
    igual nos dois, JSON válido (`_migracao` 2). Ele já não era o das 15:55: `sys_gain` 0.5 → 1.0, o ajuste que o dono
    fez no Reco Novo às 16:39 (seção "Passos 9 a 17"), com o arquivo regravado às 16:51:38, durante a troca dos apps
    daquela seção; nada desta revisão grava o config real. A outra frente recopiou às 16:53, depois de instalar, com
    hashes iguais. Por isso o passo 9 ganhou nota para recopiar com os apps fechados, antes de instalar.
    Observação dela que vale aqui: a `Reco-reserva\models` ficou na revisão anterior do modelo (o Reco Novo baixou uma
    nova às 16:39); ela segue um modelo inteiro e conferido (soma do passo 2), só não é mais a revisão da pasta viva.
  - Volta: o passo 16 d) ganhou nota datada: sem `%LOCALAPPDATA%\Reco\models`, `robocopy` da reserva; config ilegível,
    copiar de volta o da reserva.
  - **Falso:** "o `--selftest` da reserva lê os modelos de `%LOCALAPPDATA%\Reco\models`". O selftest
    (`reco.py:5133-5146`) não lê modelo nenhum: só os imports, os devices do OpenVINO e o `resolve_device`. Ele prova o
    exe; a cópia dos modelos foi provada pela soma da árvore (46 arquivos, mesma soma nos dois lados, passo 2). Nota
    datada no passo 2 do md.
- **Também corrigido:** a tabela da linha de base dizia `mic_zero_max` 0 na G10; a saída da régua (antes e depois) diz 2.

**Instalador refeito** (só build; nada instalado nem aberto por esta revisão): `app/build.ps1` completo do `9b6294b`
(o `d837de2` só muda `tools/` e roadmap), 16:43:09 a 16:55:58, `exit=0`; smoke do motor congelado `ready ok=True` em
1,94 / 0,66 / 0,60 s e `devices ok=True (1, 2)`; tempos: motor 167 s, `tauri build` 591,3 s, total 768,7 s. O motor
congelado novo, com `hello` + `shutdown` → `"engine_version":"0.3.0"`.

- Instalador `C:\pt\release\bundle\nsis\Reco_0.3.0_x64-setup.exe`: 134992448 bytes, 16:55:58,
  `84EE114218BF5FFD4318E37B8C12C1C559A0263D1C9312ADB616BFF8D92211CF`.
- Casco `C:\pt\release\reco.exe`: 4513792 bytes, `11689B19900507056C52B9B470718F49A5FBA6651CB8DD6F7AB5DD94E731BBB5`.
- Motor `engine\dist\reco-engine\reco-engine.exe`: 25162376 bytes, 16:45:46,
  `281A0D76E3745159F6E67340E04455B1943D451763C73612D33882EBC4098A5F`.
- Substitui o `76C890E8…5B1A4D90` do passo 8 no caminho do `$setup`. **Atenção:** o app instalado nos passos 9 e 10
  (seção abaixo, outra frente, a partir das 16:37) é o `76C890E8…` (cópia em `temp/instaladores/`), com o motor 0.1.0;
  a diferença para o novo é só o número da versão do motor (Opções mostra "motor 0.1.0"). A próxima reinstalação pelo
  `$setup` (passo 16 f) leva o novo. Este build reescreveu o `engine\dist` de 16:43 a 16:46 e o `C:\pt\release` até
  16:55:58, enquanto a outra frente testava; a cópia do instalador dela não foi tocada.

### Commits

| hash | o quê |
| --- | --- |
| `037ef65` | passo 1 (0.3.0) e as notas de frescor do md |
| `7f21ea0` | passos 2 e 3 (reserva e foto) |
| `5037e1f` | passos 4 e 5 (`tools/paridade.py`, `docs/TOOLS.md`) |
| `818c257` | passo 8, fonte (nome `Reco`, `ready em`, README) — o instalador sai deste código |
| `60122c7` | passos 6 e 7 e o `pior` fala a fala |
| `9b6294b` | revisão, achado 4: motor 0.3.0 (o instalador `84EE…` sai deste código) |
| `d837de2` | revisão, achados 1, 2, 3 e 5: régua, `tools/test_paridade.py`, notas no md |

### Passos 9 a 17 — app instalado (12/11/2026, a partir das 16:37)

Condição: o dono autorizou instalar (~16:3x, "Já pode instalar sim") e está usando a máquina. **Sem mouse e sem
teclado**: nada de `SendInput`/`SetCursorPos`; o casco abre com `--oculto` e o WebView2 com
`--remote-debugging-port`, cliques por `el.click()` no DOM via CDP, itens da bandeja por `PostMessageW(WM_COMMAND)` na
janela do ícone (armadilha de 12/11 12:22). Gravações de teste com o clipe de fala tocando no alto-falante; cada
arquivo de teste sai de `Documents\Reco` para `temp/medicoes/f4/` (fora do git) ou vai à Lixeira; clipboard do dono
reposto depois de cada "copiar caminho". Instalador usado: cópia em `temp/instaladores/` do `Reco_0.3.0_x64-setup.exe`
do passo 8, SHA256 `76C890E8…5B1A4D90` conferido na cópia e no original. Início: `HEAD` `df07ffe`.

**Antes de fechar (16:37 a 16:45) — correção da premissa:** o Reco velho (pid 29256) já não estava aberto. Às 16:39:20
o dono abriu o "Reco Novo" instalado (`aac7ca7`) pelo Menu Iniciar (pai `explorer.exe`, `oculto=false`), gravou um teste
curto às 16:39:32 (o `.txt` dele ficou na pasta, intocado) e mudou o ganho do sistema de 0,5 para 1,0 (mantido; a foto
do config foi refeita com isso). Esse build antigo, online, **baixou uma revisão nova do modelo** às 16:39:27–45
(`.hf_revision` `4929ae8` → `b568445`; models 828 097 157 → 828 098 952 bytes, 46 → 49 itens). A reserva
(`Reco-reserva\models`) segue na revisão anterior, que também transcreve. Antes de fechar: `--checar-gravando` →
`nenhuma gravação em curso` duas vezes, `travados` vazio duas vezes com 25 s entre elas e CPU do motor 0,1% (o casco 0%);
fechado pelo Sair da bandeja por mensagem (`WM_COMMAND 1003`) → saiu em 1,4 s, log `saída: Ocioso`, motor `encerrando
(shutdown)`, nenhum processo Reco e mutex livre.

**Herdado da Fase 3, antes de instalar (16:45 a 16:48):** `python tools/test_engine_protocol.py --gravar 5 --concluir`
→ `OK conclusões: save, delete (Lixeira), transcribe, transcribe_delete, nota, final_pass (1 live.text), 2 cancelados
com mp3`, rc 0; `--eof 25` → `OK eof: declarada 25.0 s, decodificada 25.0 s, saiu em 0.5 s; OK shutdown no meio:
declarada 25.0 s, decodificada 25.0 s, saiu em 0.5 s`, rc 0.

**Passo 9 (16:48):** guarda `Get-Process | ? Path -like '*\Reco*\*'` → só o gravador do **Medal**
(`…\Medal\recorder-2645…\MedalEncoder.exe` e `crashpad_handler.exe`): o padrão casa `\recorder`, falso positivo lido
pelo caminho (nenhum Reco). `Test-Path "…\Reco Novo\uninstall.exe"` → `True`; `uninstall.exe /S` → sumiu em ~3 s;
pasta `Reco Novo`, `Reco Novo.lnk` (Menu Iniciar e Área de Trabalho) → `False`; `reg query …\Run /v "Reco Novo"` → rc 1;
soma dos modelos igual (828 098 952). `Start-Process $setup -ArgumentList '/S' -Wait` → exit 0 em 27,3 s; `Test-Path
$exe` → `True`; `Reco.lnk` no Menu Iniciar `True`, **na Área de Trabalho `False`** (o hook do NSIS da Fase 3 vale no
`/S` real); `reco-engine.exe` instalado SHA256 `214822A8331C349ED94A8321E14DE4E1DBD71F37E2D825E0622D51CF220BCEE0`, igual ao
motor do passo 8;
`reco.exe` instalado `BA142BDA7915C6FDBFFDD63D990EAC13C2F88DDE15E142CB8E2548879F7F20A5` (≠ o `C:\pt\release\reco.exe`
`E0309C6F…` anotado no passo 8: o casco que vai no instalador não é byte a byte o arquivo solto da pasta de saída).
Config copiado para `Reco-reserva\reco_config.json` às 16:53 (nota da revisão no md; feito depois de instalar, com os
dois apps fechados) → `Get-FileHash` igual nos dois (`3119E0CE…`).

**Herdado da Fase 3, depois de instalar (16:50 a 16:52, app instalado, CDP):**

- Nota 2,21 s depois do Gravar habilitado, **online** (sem `HF_HUB_OFFLINE`, o caso real da checagem do modelo) →
  `Parar` no 1º clique; o `.md` nasce e o clipboard traz `"…\nota_2026-11-12_16-50-09.md"` entre aspas (o `.md` saiu da
  pasta para `temp/medicoes/f4/`, sem ler o conteúdo).
- Antes da 1ª gravação: Entrada `Grupo de microfones (…Smart Sound…)`, Saída `Alto-falantes (Realtek(R) Audio)`, status
  `Pronto para gravar. Microfone: <mic> · Sistema: <alto-falante>`; depois da nota e de volta ao modo gravação, os
  mesmos nomes.
- `Reco.log` na hora local (`[16:50:04]` para 16:50 locais; o `Reco Novo.log` antigo seguia em UTC, `19:39`).
- Sair (`WM_COMMAND 1003`) → código 0 em 0,75 s; `engine.log` → `ready em 0.50 s` e `encerrando (shutdown)`.
- Ao vivo ligado em Opções (`aria-checked=true`, `live: true` no config), 25 s gravando com o clipe, Parar → "Salvar e
  copiar caminho" em 14,3 s (passada final), `x.txt` com 2 falas `Eu`/`Interlocutor(es)`, nenhum `busy` nem `ERROR` no
  `engine.log` ou no `Reco.log`, `encerrando (shutdown)`; régua `dur=25.5 xing=ok r_zero_inicio=0 mic_zero_max=4
  alinhamento=ok txt=diarizado pior=1 -> ok`, `PASSOU`. Ao vivo desligado de novo (`live: false`). Observação: o
  painel do ao vivo estava vazio aos 25 s (o P10 pede 5 min).
- Instalação silenciosa sem atalho na Área de Trabalho (passo 9, acima).

**Passo 10 (16:52):** soma antes 828 098 952 e soma da árvore (caminho + SHA256 dos 45 arquivos)
`E3089D1F…70EBBB2E1D`. `uninstall.exe /S` → `reco.exe` e `uninstall.exe` sumiram em 4 s; soma 828 098 952, árvore
igual, `models` existe; sobraram `models`, `ovcache`, `transcribe_worker.py` (do app velho); `Reco.lnk` saiu.
Reinstalar `/S` → exit 0, `Test-Path $exe` `True`, soma 828 098 952, árvore igual, `reco.exe` com o mesmo SHA256.

**Passos 11 a 13 (16:53 a 16:56, build `76C890E8`):**

- 11: `Reco.lnk` → `%LOCALAPPDATA%\Reco\reco.exe |` (alvo = `$exe`, `HotKey` vazio, sem argumentos). Tecla física
  Ctrl+Shift+R: **pulado a pedido do dono: sem teclado**. O atalho global nasce desligado (`aria-checked=false` em Opções).
- 12, ida: novo aberto com `--oculto` (sem CDP) → `TryOpenExisting` `True`; `Start-Process …\dist\Reco\Reco.exe` →
  `WaitForExit(60000)` `True`, código 0; a janela do novo, oculta antes, ficou visível e na frente (o `Reco.Show`
  chegou). O X (`WM_CLOSE`) a escondeu de novo com o processo vivo; Sair por mensagem → código 0.
- 12, volta: velho aberto e escondido pelo X dele; `Start-Process $exe` → `True 0`; a janela do velho voltou;
  `procs` → só `C:\Dev\Reco\dist\Reco\Reco.exe` (nenhum `reco-engine.exe`). Velho fechado por `taskkill /F` depois de
  `--checar-gravando` → `nenhuma gravação em curso`; mutex livre.
- 13: Run `/v Reco` rc 1 antes; Opções → autostart → `aria-checked=true` e `Reco REG_SZ
  %USERPROFILE%\AppData\Local\Reco\reco.exe --oculto`, rc 0; de novo → `false`, rc 1; `/v "Reco Novo"` rc 1. **Achados:**
  (1) o valor vai sem aspas e o home tem espaço: o `auto-launch` 0.6.0 grava `format!("{} {}", app_path, args)`
  (`windows.rs:77`); o Windows resolve tentando `C:\Users\<primeira palavra>.exe`, `…\<duas palavras>.exe`… até achar, então funciona,
  mas é o caminho sem aspas clássico (um `.exe` plantado num desses nomes subiria no lugar). Conserto possível no casco:
  passar o caminho já entre aspas ao plugin. A subida no boot fica para o dono. (2) O ligar cria `Reco` em
  `HKCU\…\Explorer\StartupApproved\Run` (`02 00…`, habilitado) e o desligar não apaga; apaguei à mão (`reg delete … /f`,
  depois rc 1), porque o app velho nunca teve autostart.

**Passo 14 (16:56 a 17:04):** laço do md, janela visível, sem CDP, `HF_HUB_OFFLINE=1`, `live=False`, `device=AUTO`,
Sair por mensagem entre as aberturas, nenhum `cargo`/`rustc` rodando.

| build | CPU total | aberturas (s) | mediana | régua Fase 0 |
| --- | --- | --- | --- | --- |
| `76C890E8` (motor 0.1.0) | 25 / 46 / 23% | 1,034 / 0,982 / 0,797 | **0,982** | 1,515 |
| `84EE1142` (final, motor 0.3.0) | 79 / 84 / 85% (outras sessões: `node`, `python`, `svchost`) | 1,735 / 1,986 / 2,41 | 1,986 | 1,515 |

- O motor deu `ready em` 0,15 a 0,47 s em todas; o que cresceu sob carga foi o resto (janela e WebView2). A Fase 0
  mediu o velho com a máquina livre; a linha do build final não é comparável e se repete com a CPU livre (abaixo, se
  couber nesta rodada).
- Cláusula do Gravar (build `76C890E8`, CDP, clique no mesmo `eval` que vê o botão habilitar, clipe tocando):
  `ready` 16:57:45,093 → clique 45,193 → "Parar" 45,454 → cronômetro `00:00:01` às 46,476; `aquecimento pronto em
  1.76 s` às 46,854. Gravar não espera o aquecimento. (A 1ª tentativa ficou ambígua: o clique saiu 32 ms antes do
  aquecimento acabar.)
- "A frio": **pendente do dono** (3 reinícios do Windows; a sessão não reinicia).

**Reinstalação do build final (17:02):** a revisão refez o instalador (SHA256
`84EE114218BF5FFD4318E37B8C12C1C559A0263D1C9312ADB616BFF8D92211CF`, commit `9b6294b`, só a versão do motor muda).
Cópia em `temp/instaladores/Reco_0.3.0_x64-setup.84EE1142.exe`, SHA conferido; `/S` por cima → exit 0; soma dos
modelos 828 098 952 antes e depois; `reco.exe` `3B8CBE2947CA33440F78DD71BF9496735E9FD3EE4D3932599F5CEECADCED210E`,
`reco-engine.exe` `281A0D76E3745159F6E67340E04455B1943D451763C73612D33882EBC4098A5F`; Opções →
`Reco 0.3.0 · motor 0.3.0`; atalho certo, nada na Área de Trabalho. Daqui para baixo, tudo neste build.

**Passo 15 (17:07 a 17:09, build `84EE1142`):**

- Casco morto aos 40 s (`Get-Process | ? Path -eq $exe | Stop-Process -Force`) → motor saiu sozinho; régua
  `dur=47.3 xing=ok r_zero_inicio=0 mic_zero_max=0 alinhamento=ok -> ok`, `PASSOU`; ffprobe 2 canais, 16000 Hz.
  **Por que 47 e não 40:** o próprio comando da prova levou 4,7 s (o `Get-Process` lê o `Path` de todos os processos), e o
  motor saiu 0,0 s depois de o casco morrer (medido numa repetição no build `76C890E8`: `stop_process_levou_s=4.69`,
  `motor_saiu_depois_do_stop_s=0.0`, `dur=47.4 … -> ok`). O casco seguiu gravando até morrer; o D11 é imediato.
- Motor morto aos 41 s → a tela saiu de "Parar" em **0,05 s** para "Gravar" desabilitado com "A gravação foi
  interrompida em 00:00:41. O arquivo fica na pasta das gravações." e "Abrir pasta"; em 10 s nunca voltou a "Parar";
  motor novo de pé, status "O motor reiniciou; a tela foi atualizada.". Arquivo: `dur=20.2 xing=ok … -> ok`; o
  reparador numa cópia em `temp/reparo/` → "já correto" (declarado 20 s = real 20 s). Perde o trecho no buffer do
  encode (≈ 21 s de 41), o que o md e o `CLAUDE.md` ("o MP3 só nasce no 1º pacote") já preveem.

**Passo 16 (17:10 a 17:13, build `84EE1142`), sem mouse:**

- a) novo fechado pelo Sair por mensagem; b) Run `/v Reco` rc 1; c) `_migracao` `2`; d) `models` presente (revisão
  `b568445`; a reserva tem a `4929ae8`), config legível; `Reco-reserva\reco_config.json` = config atual (hash igual).
- e) **equivalente por script** de Opções → "Remover atalho" → "Criar atalho" (os links de Opções do velho só
  respondem a clique real): apaguei o `Reco.lnk` e o recriei com os campos de `reco.py:4902-4908` → `…\dist\Reco\Reco.exe
  | Ctrl+Shift+R`.
- Prova, entre e) e f): `Get-Process -Name Reco -EA 0 | Select -Expand Path` → só `C:\Dev\Reco\dist\Reco\Reco.exe`.
- Gravação de 30 s do velho: `BM_CLICK` e `WM_LBUTTONDOWN/UP` postados no `Button` "Gravar" **não** gravam (nada
  mudou na tela; causa provável, não conferida: o Tk lê o estado real do botão do mouse). Gravou pelo **menu da bandeja do velho, só por mensagens**:
  `WM_APP+1` com `lParam=WM_RBUTTONUP` na `RecoTrayWindow` abre o `TrackPopupMenu` (itens `Gravar · Abrir · Sair`), e
  `WM_KEYDOWN` Down + Enter postados na janela do menu (`#32768`) escolhem o 1º item; 1 → 2 botões; 32 s; o mesmo
  para "Parar" (itens `Parar · Pausar · Abrir · Sair`) → 3 botões. Régua: `dur=31.7 xing=ok r_zero_inicio=0
  mic_zero_max=0 alinhamento=ok -> ok`, `PASSOU`. O menu abre no ponto do cursor e o velho toma a frente: uma
  interrupção visual curta, sem mexer no cursor nem no teclado.
- f) `--checar-gravando` → nenhuma; velho fechado por `taskkill /F`; mutex livre; `$setup` (`84EE1142`) `/S` → exit 0,
  `Test-Path $exe` `True`; `Reco.lnk` → `%LOCALAPPDATA%\Reco\reco.exe |` (o instalador sobrescreveu o `.lnk` do velho com
  tecla: F4-D5 confirmada). A 1ª rodada do ensaio (só os cliques por `BM_CLICK`) fez o mesmo e/f com o mesmo resultado.

**Passo 17 — checklist de paridade (17:15 a 17:36, build `84EE1142`, online, sem mouse).** Uma sessão do app por CDP
para P2 a P26, outra para P1, P8, P10 e P16, e o repasse do P25 com o app fechado. Toda gravação com o clipe tocando;
todo arquivo de teste fora da pasta do dono no fim (`sobrou_na_pasta: []` nas duas sessões). **Máquina carregada** por
outros processos durante toda a rodada (CPU total 79 a 85%, `node`/`python` de outras sessões): os tempos abaixo e o
`desalinhado` do P10 saem sob essa carga. Marcas: ✓ provado; ⏸ pulado ou pendente do dono (sem mouse ou sem olho dele).

| # | resultado | evidência |
| --- | --- | --- |
| P1 | ⏸ | por script: Minimizar no DOM → `IsIconic` verdadeiro; X → janela oculta, processo vivo, ícone na bandeja (também no passo 12). Arrastar e ver o minimizado voltar só pela bandeja: **pulado a pedido do dono: sem mouse** |
| P2 | ✓ | 10 cliques no DOM (abas, modo, processar) → 1 tamanho só de janela (`GetWindowRect`) e de página (400×560); `testar-anti-pulo.cjs --url` no `ui:preview` do build → `0 diferenças em 23868 medições`; `testar-contrato.cjs --url` → `0 falhas` |
| P3 | ✓ | ganho do mic no controle → `2,0×` na tela e `mic_gain` 2.0 no config; de volta → `3,0×` e 3.0 |
| P4 | ✓ | 20 s, Pausar (cronômetro parado em `00:00:20` por 20 s), Continuar, até `00:00:40`, Parar → régua `dur=40.1 xing=ok … -> ok` |
| P5 | ✓ | "Salvar e copiar caminho" → `Get-Clipboard` = `"…\gravacao_reco_2026-11-12_17-18-49.mp3"` entre aspas |
| P6 | ✓ | Salvar + transcrever → `x.txt` nasce, MP3 fica; Transcrever e excluir → `x.txt` nasce, MP3 sai e está na Lixeira (`Shell.Application` `NameSpace(10)`); Excluir → MP3 na Lixeira, sem `.txt` |
| P7 | ⏸ | abrir no player padrão toma a frente da tela do dono: **pulado** (olho do dono) |
| P8 | ⏸ | status com `white-space: nowrap`, `text-overflow: ellipsis`, altura de 1 linha (16 px); "Abrir transcrição" abre o `.txt` no editor (toma a frente): pendente do dono |
| P9 | ✓ | Salvar + transcrever de 30 s e "Parar transcrição" 0,8 s depois → nenhum `.txt` em 15 s; status "Transcrição parada. O áudio continua na pasta." |
| P10 | ✓ | ao vivo ligado, 5 min com o clipe: painel com 37 / 488 / 655 / 783 / 1270 caracteres em 1 / 2 / 3 / 4 / 5 min; Parar → `x.txt` diarizado; régua `dur=300.8 xing=ok … txt=diarizado pior=3 -> ALERTA (desalinhado)` (salto sob carga, F4-D2); ao vivo desligado de novo |
| P11 | ✓ | nota de 8 s → `.md` existe, clipboard com o `.md` entre aspas, nenhum `nota_*.mp3` na pasta |
| P12 | ⏸ | "Auto comunicação" no select → `mic_device` `auto:comm`, de volta `auto:console` (script ✓); trocar o padrão do Windows e ver a gravação seguir: pendente do dono |
| P13 | ⏸ | "Escolher" abre o diálogo de pasta do Windows: **pulado a pedido do dono: sem mouse** |
| P14 | ✓ | Processar em GPU → `device` `GPU`; AUTO → `AUTO` |
| P15 | ✓ | EN → botão principal `Record` (captura `p17-ingles.png`) e arquivo `recording_reco_2026-11-12_17-23-50.mp3`; PT → `Gravar` |
| P16 | ⏸ | por script só a troca do atributo: Aparência escuro / claro / sistema → `data-tema` `escuro`, `claro` e sem tema; skins `a`, `b`, `c` em Opções. A cor de fundo do `body` saiu igual nos três (transparente: a cor mora noutro elemento), então a mudança visual não está provada: olho do dono |
| P17 | ✓ | navegação pelas 4 abas no DOM (P2); gravando, a aba Arquivo fica `aria-disabled=true` com o motivo "Bloqueada enquanto grava ou transcreve" na própria aba (captura `p17-abas-gravando.png`); Biblioteca e Opções seguem livres |
| P18 | ⏸ | "Escolher arquivo" abre o diálogo do Windows: **pulado a pedido do dono: sem mouse** (o caminho do motor está provado no P25 e no `--concluir`) |
| P19 | ⏸ | a Biblioteca lista 108 itens (contador `108`); a pasta tem 106 `.mp3` e 1 `.m4a` (provavelmente o 108º é um `.txt` sem áudio ao lado, como o do teste do dono das 16:39; não conferido); comparar com a contagem do velho e cada ação exige a tela do velho (mouse): pendente do dono |
| P20 | ✓ | Biblioteca → item → Resumo → `x.resumo.md` ao lado |
| P21 | ⏸ | Converter também começa no diálogo de arquivo: **pulado a pedido do dono: sem mouse** |
| P22 | ⏸ | menu por mensagem: Gravar (`WM_COMMAND 1000`) e Sair (`1003`) funcionam (P26, passos 9 a 16); hover, clique no ícone e ícone vermelho: **pulado a pedido do dono: sem mouse** |
| P23 | ⏸ | Opções `Reco 0.3.0 · motor 0.3.0`; 8 s depois do pronto, online, o botão "Baixar a {tag}" segue com `data-escondido`; release Latest no GitHub `v0.2.0`. Não discrimina: o botão também fica escondido se o `app.update_check` nunca rodar, e ele não deixa linha no log (o `model.update_check` aparece como o GET ao `huggingface.co/api/models/…` no `engine.log`) |
| P24 | ✓ | passos 11 e 12 (atalho sem tecla; mutex nos dois sentidos); a tecla física fica com o dono (passo 11) |
| P25 | ✓ | `(Start-Process $exe -ArgumentList '--transcribe','<cópia em temp>','--diarize' -Wait -PassThru).ExitCode` → `0` em 59,8 s; `a_reco.txt` com 4 falas `Eu`/`Interlocutor(es)`; durante o repasse o mutex **não** existiu e nenhuma janela apareceu (responde à pendência da Fase 3) |
| P26 | ✓ | Gravar pela bandeja, 16 s, Sair pela bandeja gravando → saiu em 12 s com código 0; régua `dur=16.0 xing=ok … -> ok` |

Contagem: 15 ✓, 11 ⏸, 0 ✗. O passo 17 fica `[ ]` até as 11 linhas ⏸ virarem ✓ (lista em "Com o dono", abaixo).

**Config e pasta do dono:** os testes deixaram `language: "pt"` (antes nulo) e `casco_tema: "sistema"` (chave nova) no
`~/.reco_config.json`; com os dois apps fechados, o config voltou da cópia das 16:45 (`cmp` → igual; a cópia já tinha o
ganho do sistema 1,0 que o dono escolheu às 16:39). `Documents\Reco`: 214 arquivos, os mesmos da foto das 16:45 (o
`.txt` do teste do dono das 16:39 incluído e intocado). Arquivos de teste em `temp/medicoes/f4/` (fora do git) ou na
Lixeira (os que o próprio app manda para lá: nota, Transcrever e excluir, Excluir, o arquivo em inglês). Clipboard
reposto depois de cada "copiar".

**Com o dono (pendente):**

- Passo 11: Ctrl+Shift+R por tecla física (ligar o atalho em Opções, app na bandeja; depois com o app fechado).
- Passo 13: com o autostart ligado, reiniciar e ver o ícone subir sem janela (desligar depois, se não quiser).
- Passo 14: só o "a frio" (3 reinícios) é dele.
- Passo 17: P1 (arrastar), P7 (player), P8 (Abrir transcrição), P12 (trocar o padrão do Windows), P13 (pasta), P16 (ver
  os temas), P18 e P21 (escolher arquivo), P19 (comparar a Biblioteca com a do velho), P22 (hover, clique e ícone
  vermelho) e P23 (ver o aviso de versão, ou uma prova que mostre o `app.update_check` rodando).

**Com a sessão (pendente):** passo 14 a quente no build final com a máquina livre (`passo14.ps1`, 3 aberturas, e a
cláusula do Gravar, que só foi provada no `76C890E8`). **O único número do build instalado final não cumpre a régua:**
mediana 1,986 s contra 1,515 s, medida com a CPU em 79–85% por outras sessões; a do `76C890E8` (CPU 23–46%) foi 0,982 s.

**Armadilhas novas** (commit `bdab7a5`): o Tk do velho ignora clique por mensagem (e o caminho pelo menu da bandeja);
guardas por caminho do processo (Medal e a demora do `Get-Process` por `Path`); autostart sem aspas e a marca do
`StartupApproved`.

**Máquina no fim (17:43):** o app novo **"Reco" `84EE1142` instalado e aberto na bandeja** (pid 38448, motor pid 46184,
`--oculto`, sem `HF_HUB_OFFLINE` e sem porta de depuração: nenhum `msedgewebview2` com `remote-debugging`, 9351/9361
fechadas), mutex `True`; `reco.exe` instalado `3B8CBE29…ADCED210E`; nenhum commit em `app/` desde o início
(`df07ffe`). Reco velho fechado (nenhum `Reco.exe` do `dist` vivo). Autostart desligado (`Run /v Reco` rc 1,
`StartupApproved` rc 1); atalho global desligado (nunca ligado). `Reco.lnk` → exe novo, sem tecla; nada na Área de
Trabalho. Modelos 828 098 952 bytes (revisão `b568445`). `~/.reco_config.json` = cópia das 16:45 (`cmp` igual, sem
chave `casco_*`), conferido de novo com o app aberto. `Documents\Reco`: 214 arquivos, 0 diferenças contra a foto. O
clipboard foi reposto depois de cada teste (último às 17:36); no fim ele tinha outro conteúdo, que não é caminho de
teste (o dono copiou algo depois), e ficou como estava. `Reco-reserva` intacta (o `reco_config.json` dela = config atual).
