# Reco em Rust: Fase 4 — Paridade, troca e reserva

> Índice: [2026-11-11-melhoria-reco-em-rust.md](2026-11-11-melhoria-reco-em-rust.md) · anterior: [fase-3](2026-11-11-melhoria-reco-em-rust-fase-3.md) · seguinte: [fase-5](2026-11-11-melhoria-reco-em-rust-fase-5.md) · Base: Reco `7c5c1a1` (2026-11-11)

## Por que esta fase

- Ao fim da Fase 3 o app novo (casco Tauri + motor Python) existe, mas o Gabriel ainda grava com o `Reco.exe` antigo.
- Esta fase troca o app do dia a dia sem risco de perder gravação: prova função por função que o novo faz o que o
  velho fazia, prova pelas réguas que leem o disco que o MP3 e o `.txt` saem iguais, e instala de verdade.
- O app velho fica pronto para voltar em minutos, com o procedimento escrito e ensaiado (D7: os dois se excluem).
- Só fecha com o Gabriel usando o app novo em reuniões reais e dizendo que aprova; mede a régua de "rápido" (D12).
- A ferramenta de paridade nasce aqui e vira o gate da Fase 5 (captura em Rust).

## O que ler antes

- `C:\Dev\Reco\CLAUDE.md`, `C:\Dev\cerebro\projetos\reco.md` e `C:\Dev\Reco\docs\ARMADILHAS.md` (gerada; inteira).
- `C:\Dev\Reco\roadmap\2026-11-11-melhoria-reco-em-rust.md` inteiro (D1–D12, "O que NÃO fazer").
- `C:\Dev\Reco\roadmap\2026-11-11-melhoria-reco-em-rust-fase-3.md` e o relatório da Fase 3 no sidecar.
- O relatório da Fase 0 no sidecar `2026-11-11-melhoria-reco-em-rust.d/` (número de "pronto para gravar", D12).
- `diagnostico/1-mapa-do-reco-atual.md` § 1 (inventário que vira o checklist) e § 5 (contratos externos).
- `diagnostico/2-restricoes-do-porte.md` § 4 (réguas que leem o disco) e § 5 (riscos de perder gravação).
- `diagnostico/3-lacre-como-molde.md` § 3 (instalador e CI do Lacre).
- Código: `tools/varrer_silencio.py`, `tools/varrer_acervo.py`, `tools/reparar_duracao.py`, `tools/test_antiloop.py`,
  `tools/transcrever.py`, `reco.py:4867-4908` (atalho), `reco.py:5196-5213` (mutex), `reco.py:1274-1290` (aviso de versão).
- Molde: `C:\Dev\lacre\src-tauri\tauri.conf.json:45-54` (motor como recurso e NSIS), `C:\Dev\lacre\.github\workflows\build.yml`,
  `C:\Dev\albion\guarita\app\src\lib\autostart.ts` (autostart opcional).

## Nomes que esta fase usa (resolvidos no passo 1)

- `$prod`, `$ver`, `$ident`: `productName`, `version` e `identifier` de `app/src-tauri/tauri.conf.json`.
  - No passo 1, `$prod` ainda é `Reco Novo` (F3-D3); o passo 8 o troca para `Reco`, e daí em diante `$prod` = `Reco`.
- `$exe`: o executável instalado, `$env:LOCALAPPDATA\$prod\<mainBinaryName>.exe` (pasta padrão do NSIS currentUser).
  - Se `mainBinaryName` vier vazio no passo 1, resolver depois do passo 9:
    `(Get-ChildItem "$env:LOCALAPPDATA\$prod\*.exe" | ? Name -ne 'uninstall.exe').FullName`.
- `$setup`: `C:\pt\release\bundle\nsis\${prod}_${ver}_x64-setup.exe` (`CARGO_TARGET_DIR` desta máquina é `C:\pt`).
- Build do app novo: `powershell -ExecutionPolicy Bypass -File app\build.ps1` (Fase 3, passo 16).
- `$log`: `$env:LOCALAPPDATA\$ident\logs\engine.log`, o stderr do motor que o casco anexa (molde Lacre `lib.rs:58-59`, `engine.rs:546-583`);
  `app_log_dir` do Tauri 2 no Windows = pasta local + `identifier` + `logs` (`tauri` `src/path/desktop.rs:296-306`).
- Pasta de gravações: `output_dir` do `~/.reco_config.json` ou `~/Documents/Reco` (`reco.py:98-99`).
- Shell de cada comando:
  - PowerShell: tudo com `$env:`, `$prod`/`$exe`/`$setup`, cmdlets (`Get-*`, `Start-Process`, `Test-Path`), `reg` e `& <exe>`.
  - Git Bash dentro de `C:\Dev\Reco`: `python`, `node`, `head`, `cmp`, `grep`, `ls`, `git`.
  - Variáveis não sobrevivem entre chamadas: redeclarar `$prod`, `$exe`, `$setup` no começo de cada bloco PowerShell
    (ou colar os valores literais anotados no passo 1).
  - O home desta máquina tem espaço no nome (`%USERPROFILE%`): no Git Bash, caminho sempre entre aspas.

## Fase 4 — Paridade, troca e reserva

**Critério de aceite:**

1. O Gabriel instala o Reco novo por um instalador, acha no Menu Iniciar, chama pelo atalho de teclado e grava,
   pausa, salva e transcreve reuniões reais sem precisar do app antigo. Se falhar: o instalador não conclui, o
   atalho abre o app antigo, ou alguma função que ele usava no antigo não existe no novo.
2. As gravações do app novo têm duração certa no player, os dois lados da conversa presentes e a transcrição
   separada por quem falou; nas gravações curtas, idêntica à que o transcritor dos agentes gera do mesmo áudio
   (se esse transcritor der o mesmo texto em duas rodadas; senão, sem trecho em loop). Se falhar: duração
   errada, um lado mudo do começo ao fim, ou texto diferente.
3. Voltar ao app antigo leva poucos minutos seguindo um procedimento escrito, o antigo grava normalmente e os
   dois nunca ficam gravando ao mesmo tempo. Se falhar: o antigo não abre (fecha sozinho), não grava, ou os dois
   aparecem vivos juntos.

### Herdado da Fase 3 (12/11/2026)

> Atualizado em 2026-11-12, no fechamento da Fase 3. O teste real dela rodou no instalador do `aac7ca7`; os consertos
> de depois (os 5 defeitos do passo 17 e os 5 achados da revisão deles, `adf3fc0` a `69636f0`) foram provados no
> backend falso, nos testes do casco e do motor, mas nunca no app instalado: o instalador final (SHA256 no relatório
> da Fase 3, seção "Revisão adversarial dos consertos") não foi instalado. Conferir no app instalado do passo 9:
>
> - "Gravar nota" ~2 s depois de abrir grava de primeira; depois da nota, Entrada e Saída seguem com os nomes.
> - Entrada e Saída com os nomes dos dispositivos e o status "Pronto para gravar. Microfone: X · Sistema: Y" antes
>   da 1ª gravação.
> - `Reco Novo.log` (ou `Reco.log`, depois do passo 8) na hora local; o `engine.log` do Sair diz `encerrando (shutdown)`.
> - A instalação silenciosa não deixa atalho na Área de Trabalho.
> - **Antes de instalar** (Reco velho fechado pelo dono): `python tools/test_engine_protocol.py --gravar 5 --concluir`
>   e `python tools/test_engine_protocol.py --eof 25`
>   (as checagens que gravam abortam com o velho aberto e não rodaram depois do `058acfc`, que mexeu no ao vivo:
>   `recording._stop_live` e `conclude.make_live`) e uma gravação curta com o ao vivo ligado no app instalado,
>   parada normal (passada final sem `busy`).
> - Também ficaram sem prova no build final: o hover e o clique no ícone (sem mouse, a pedido do dono), o ícone saindo
>   do vermelho quando o motor cai gravando, o clique dentro da janela do hover (fixa e foca), minimizar com
>   `skipTaskbar` (a janela só volta pela bandeja) e se o repasse `--transcribe` pega o mutex.

> Nota (2026-11-12, passo 8 feito): o instalador a usar no passo 9 é o `Reco_0.3.0_x64-setup.exe` (SHA256 no relatório
> da Fase 4, seção "Passo 8"), não mais o `Reco Novo_0.1.0` da Fase 3. Onde o bloco acima diz `Reco Novo.log`, o log
> do casco instalado passa a ser `Reco.log`.

### A. Reserva e régua, antes de instalar

1. [x] Resolver `$prod`, `$ver`, `$ident` e o binário em `app/src-tauri/tauri.conf.json`; anotar no relatório. — **prova:** `node -p "const c=require('./app/src-tauri/tauri.conf.json');[c.productName,c.version,c.identifier,c.mainBinaryName].join(' ')"` → 4 valores, versão ≥ `0.3.0`
   **reprova se:** a versão é ≤ `0.2.0` (o app velho é `0.2.0`, `reco.py:34`, e o release `v0.2.0` é o Latest do GitHub), `productName` vem vazio,
   ou `identifier` é igual a `productName` sem diferença de maiúsculas (ex.: `Reco`). Esperado aqui: `Reco Novo` e `io.github.dosxnjos.reco` (Fase 3, passo 3).
   - Versão abaixo: subir para `0.3.0` em `tauri.conf.json` e onde a Fase 3 a espelhou (`Cargo.toml`, `package.json`, e os lockfiles que mudarem).
   - Por que o `identifier`: com a caixa "apagar dados" marcada, a desinstalação faz `RmDir /r "$LOCALAPPDATA\${BUNDLEID}"`
     (molde do Tauri CLI 2.12.4). Se o identifier for `Reco`, isso apaga `%LOCALAPPDATA%\Reco` inteira, com os modelos.
     Corrigir para domínio reverso (ex.: `io.github.dosxnjos.reco`) antes de seguir.
   - Nota (2026-11-12, frescor): `mainBinaryName` não existe no `tauri.conf.json`; o binário sai com o nome do pacote
     Cargo (`reco`), ou seja `reco.exe` (a Fase 3 o viu instalado em `%LOCALAPPDATA%\Reco Novo\reco.exe`). A versão
     estava em `0.1.0` e subiu para `0.3.0` em `tauri.conf.json`, `Cargo.toml`, `Cargo.lock` (pacote `reco`),
     `package.json` e `package-lock.json` (as duas entradas). O `condutor.ts` (dados inventados do backend falso) segue com `0.1.0`.
2. [x] Congelar uma cópia da reserva em `%LOCALAPPDATA%\Reco-reserva\Reco` (F4-D3). — **prova:** a conferência do primeiro sub-item → `True`
   **reprova se:** sai `False`, erro de caminho, ou falta `_internal` ou `models` na cópia.
   - Conferência: `$r="$env:LOCALAPPDATA\Reco-reserva"; $a=(Get-FileHash "$r\Reco\Reco.exe").Hash; $b=(Get-FileHash C:\Dev\Reco\dist\Reco\Reco.exe).Hash; ($a -eq $b) -and (Test-Path "$r\Reco\_internal") -and (Test-Path "$r\models")`.
   - Copiar: `robocopy C:\Dev\Reco\dist\Reco "$env:LOCALAPPDATA\Reco-reserva\Reco" /E /NFL /NDL` (código < 8 = ok).
   - Copiar também os modelos, que o passo 10 arrisca:
     `robocopy "$env:LOCALAPPDATA\Reco\models" "$env:LOCALAPPDATA\Reco-reserva\models" /E /NFL /NDL` (código < 8 = ok).
   - Smoke sem janela: `& "$env:LOCALAPPDATA\Reco-reserva\Reco\Reco.exe" --selftest` e ler `$env:TEMP\reco_selftest.txt`:
     linha `transcription_available=True` (`reco.py:5132-5146`; sai antes do mutex, não incomoda o app aberto).
   - Por quê: `dist/` é ignorado pelo git, `build.ps1 -Clean` o apaga e um build com o app aberto falha no meio de
     `_internal` (`docs/ARQUITETURA.md:19-23`); a reserva quebraria sem aviso. Anotar hash e data do `Reco.exe`.
   - Nota (2026-11-12, revisão): o `--selftest` não lê modelo nenhum (`reco.py:5133-5146` só olha os imports e os
     devices do OpenVINO); quem prova a cópia dos modelos é a soma da árvore (relatório, passo 2). A reserva ganhou
     também o `~/.reco_config.json` (`Reco-reserva\reco_config.json`), que o app novo grava no mesmo arquivo.
3. [x] Fotografar o que o instalador vai tocar, para a volta do passo 16. — **prova:** os 4 comandos abaixo → 4 valores anotados no relatório
   **reprova se:** algum comando falha ou um dos 4 valores fica em branco.
   - Atalho: `$l="$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Reco.lnk"; if(Test-Path $l){$s=(New-Object -ComObject WScript.Shell).CreateShortcut($l); "$($s.TargetPath) | $($s.HotKey)"} else {"sem lnk"}`.
   - Autostart: `reg query HKCU\Software\Microsoft\Windows\CurrentVersion\Run /v Reco; $LASTEXITCODE` (esperado: `1` = não existe; `0` = existe, anotar o valor).
   - Migração: `python -c "import json,pathlib;print(json.loads((pathlib.Path.home()/'.reco_config.json').read_text(encoding='utf-8')).get('_migracao'))"` → `2` (`reco.py:173`).
   - Modelos: `(Get-ChildItem -Recurse "$env:LOCALAPPDATA\Reco\models" | Measure-Object Length -Sum).Sum` (≈ 790 MB do turbo).
4. [x] Criar `tools/paridade.py` (arquivo novo, até 500 linhas) que roda as réguas de disco por MP3; entrada em `docs/TOOLS.md`. — **prova:** `python tools/paridade.py <2 gravações recentes do app velho, com x.txt>` → 2 linhas `-> ok` e `PASSOU`, rc 0
   **reprova se:** rc ≠ 0 numa gravação boa do app velho (a régua está errada), linha faltando, ou o arquivo passa de 500 linhas.
   - Reusar por import, sem copiar lógica: `varrer_silencio.medir` (`tools/varrer_silencio.py:40`),
     `varrer_acervo.mede`/`resume` (`tools/varrer_acervo.py:39`, `:59`), `reparar_duracao.declared_and_real`
     (`tools/reparar_duracao.py:22`), `test_antiloop.pior` (`tools/test_antiloop.py:44`), `transcrever.diarizada` (`:102`).
   - Xing pelo mesmo critério do reparador: `abs(declarado - real) <= max(1, real * 0.01)` (`tools/reparar_duracao.py:60`).
     Não chamar o `reparar_duracao.py` inteiro: ele só aceita pasta (`:44-46`, `:95-97`) e sai 0 mesmo em "seria corrigido".
   - Linha por arquivo: `<nome> dur= xing= r_zero_inicio= mic_zero_max= alinhamento= txt= pior= [script=] -> ok|ALERTA|FALHOU`.
   - FALHOU: Xing errado; não estéreo; sistema em zero o arquivo inteiro (`r_zero_inicio == dur`) sem `--sem-sistema`;
     mic em zero o arquivo inteiro; erro de leitura; `pior` > 3 (critério do `test_antiloop`); `script=DIFERENTE`.
   - ALERTA (não reprova, vai ao relatório): `r_zero_inicio` ≥ 60 s (o maior em reunião boa foi 73 s,
     `tools/varrer_silencio.py:20-22`); veredito `salto` ou `desalinhado` (F4-D2); `sem correlacao` é esperado com fone.
   - `--exigir-txt`: `x.txt` ausente ou texto corrido vira FALHOU (sem a flag, só informa).
   - `--txt-contra-script`: copia o MP3 para uma pasta temporária (fora da pasta do app o script grava `x.mp3.txt`,
     `tools/transcrever.py:87-99`), roda `python tools/transcrever.py <cópia> --modelo <model do config> --device <device do config> --lang <idioma>`
     e compara byte a byte com o `x.txt` do app. O script ignora modelo e device do config (`:189-195`), daí as flags.
   - `<idioma>`: `pt` se o `language` do config for `pt`, ou se for nulo e o Windows estiver em português; senão `en`
     (o app passa `_whisper_lang()`, `reco.py:3743-3744`, que lê o `LANG` de `reco.py:515`).
   - Texto vazio: o app grava `(no content recognized)` (`reco.py:4184`) e o script grava vazio (`tools/transcrever.py:159`); contar como igual.
   - `sys.stdout.reconfigure(encoding="utf-8")` no topo (armadilha do print com emoji no console desta máquina). Saída 0/1/2.
   - Nota (2026-11-12, execução): das 3 gravações recentes com `x.txt` do app, a mais nova sai `FALHOU (loop)`: `pior=4`,
     um token alucinado pelo Whisper (fora do português) repetido 4 vezes no `x.txt` do **app velho**. A régua ficou como o
     md manda (`pior` > 3 reprova): é defeito real da transcrição, e o passo 18 compara com a linha de base. A prova rodou
     nas outras duas. Extras: `--anonimo` (G01…, para o relatório público), contagem dos vereditos e do alinhamento na
     penúltima linha, e o `pior` só como número (o n-grama é trecho de transcrição).
   - Nota (2026-11-12, revisão): "mudo o arquivo inteiro" passou a ser "todos os segundos menos 1" (`limiar_mudo`): o
     encoder vaza ~21 ms do canal com som para o mudo no 1º frame (medido pelo `reco.MP3Writer`), e com som desde o 1º
     frame a regra de zero exato do começo ao fim nunca reprovava. O sistema usa `r_total` (segundos em zero), o mic a
     maior sequência. `--exigir-txt` reprova também o `x.txt` vazio (`(no content recognized)`). Teste da régua:
     `python tools/test_paridade.py` → `paridade: falhas 0`.
5. [x] Prova negativa: a régua tem de reprovar arquivo ruim. — **prova:** `python tools/paridade.py temp/trunc_reco.mp3 temp/mono.mp3` → as duas linhas `FALHOU` (`xing=ERRADO`, `nao-estereo`), rc 1
   **reprova se:** alguma das duas sai `ok` ou `ALERTA`, ou rc 0.
   - `head -c 3000000 "<gravação real com mais de 10 MB>" > temp/trunc_reco.mp3`: o Xing do começo declara a duração inteira
     e o resto sumiu. Conferido em 11/11/2026 com `reparar_duracao.declared_and_real`: declarado 2317 s, real 245 s.
   - Mono pelo mesmo código do Converter (`reco.extract_mp3`, `EXTRACT_CH = 1`, `reco.py:162`):
     `python -c "import sys; sys.path.insert(0,'.'); import reco; reco.extract_mp3(sys.argv[1], sys.argv[2])" "<gravação curta>" temp/mono.mp3`.
   - Nota (2026-11-12, execução): os dois arquivos ficam fora do repo (derivam de gravação do dono). O corte de 3 000 000 bytes
     caiu no meio de um frame: o último pacote não decodifica e o `declared_and_real` desiste nele (`InvalidDataError`). A
     régua mede o Xing pulando esse pacote e sai `xing=ERRADO leitura=ERRO … FALHOU (xing, cauda-corrompida)`; um corte em
     fronteira de frame (2 999 000 bytes) sai `xing=ERRADO … FALHOU (xing)`. Processo morto no meio de uma escrita pode deixar o mesmo rabo (não medido).
   - Nota (2026-11-12, revisão): conferir só veredito e rc deixava passar a régua com a checagem do Xing ou a do estéreo
     desligadas (o truncado ainda caía em `cauda-corrompida`, o mono em `ERRO KeyError`). A prova do passo passa a ser
     `python tools/test_paridade.py` → `paridade: falhas 0`, rc 0: MP3 sintéticos pelo `reco.MP3Writer` (repetível, sem
     gravação do dono), com o motivo casado caso a caso (`xing` sozinho no corte em fronteira, `xing, cauda-corrompida`
     no cabeçalho de frame cortado, `nao-estereo`, `sistema-mudo`, `mic-mudo`, `loop`, `txt-vazio`). O "rabo ruim" é o
     cabeçalho incompleto: o truncado de 3 000 000 bytes terminava num pacote de 3 bytes; com o cabeçalho inteiro o
     decoder aceita o frame curto.
6. [x] Linha de base do app velho: rodar a régua nas 10 gravações mais recentes e anotar a contagem de vereditos. — **prova:** `cd "$HOME/Documents/Reco" && python C:/Dev/Reco/tools/paridade.py $(ls -t gravacao_reco_*.mp3 | grep -v _alinhado | head -10)` → 10 linhas e a contagem anotada
   **reprova se:** menos de 10 linhas ou algum `FALHOU` por erro de leitura (aí a régua, não o app, precisa de conserto).
   - Pasta: se `output_dir` do config não for nulo, trocar `$HOME/Documents/Reco` por ela (em 11/11/2026 era nulo).
     Nomes sem espaço, por isso o `$(ls ...)` sem aspas funciona depois do `cd`.
   - Se a Fase 0 já guardou essa contagem, reusar e citar. Referência histórica: salto em 16 de 43 (37%).
   - Nota (2026-11-12, frescor): uma das 10 mais recentes tem **espaço no nome** (o dono renomeou à mão), então o
     `$(ls ...)` sem aspas quebra. E a regra é ler as gravações só por **cópia**: copiar as 10 (com o `x.txt` ao lado, se
     houver, nomes originais) para uma pasta temporária fora do repo e passar a lista entre aspas. No relatório, nomes
     viram G01 a G10 (repo público).
7. [x] Provar que o transcritor dos agentes é determinístico antes de usá-lo como régua byte a byte. — **prova:** 2 rodadas `--forcar` (sub-itens), depois `cmp temp/det1.txt temp/det2.txt && echo IGUAL` → `IGUAL`
   **reprova se:** os dois diferem. Aí vale F4-D8: a comparação byte a byte sai da régua e fica só `pior` + diarizado.
   - Copiar antes a gravação para `temp/det/` (com o `x.txt` do app ao lado, para o último sub-item).
   - Rodada: `python tools/transcrever.py temp/det/gravacao_reco_<curta>.mp3 --forcar --modelo <model do config> --device <device do config>`,
     copiando o `.mp3.txt` gerado para `temp/det1.txt` e, na segunda, para `temp/det2.txt`. Fora da pasta do app sai `x.mp3.txt`
     (`tools/transcrever.py:87-99`).
   - Usar gravação de 3 a 10 min com fala dos dois lados (o anti-loop refaz janela com temperatura, `reco.py:2117-2183`).
   - Se deu `IGUAL`, linha de base do byte a byte no app velho: `python tools/paridade.py <a mesma gravação, na pasta do app> --txt-contra-script`
     → `script=igual`. Se o velho já sai `DIFERENTE`, o byte a byte não serve para julgar o novo no passo 18 (F4-D8).
   - Nota (2026-11-12, frescor): nunca rodar o `tools/transcrever.py --forcar` sobre arquivo **dentro** da pasta do app: lá
     o destino é o `x.txt` do app (`destino()`, `tools/transcrever.py:87-99`), que seria reescrito. As rodadas e a linha de
     base usam a cópia em pasta temporária, com o `x.txt` do app copiado ao lado. Duas rodadas só, sem repetir até bater.

### B. Instalar e trocar

8. [x] Renomear "Reco Novo" para "Reco" (troca que a F3-D3 deixou para cá) e gerar o instalador NSIS `currentUser`, PT-BR e EN, só `nsis` (F4-D7). — **prova:** `grep -rln "Reco Novo" app --exclude-dir=node_modules` → nada, e `ls C:/pt/release/bundle/nsis/` → `Reco_${ver}_x64-setup.exe`
   **reprova se:** sobra `Reco Novo` em `app/` (ex.: o `.app_name` do autostart, Fase 3 passo 10), o instalador sai com outro nome, só sai MSI, ou o build falha.
   - Trocar `productName` para `Reco` em `app/src-tauri/tauri.conf.json` e `.app_name("Reco Novo")` para `.app_name("Reco")` em `app/src-tauri/src/atalho.rs`. O `identifier` não muda.
   - Por quê: o NSIS usa o `productName` no `.lnk` do Menu Iniciar e na pasta `%LOCALAPPDATA%\<productName>`, e o autostart grava a chave Run com o `app_name`.
     Com "Reco Novo" sairiam `Reco Novo.lnk`, `/v "Reco Novo"` e outra pasta, e os passos 10, 11, 13 e 16 conferem `Reco.lnk`, `/v Reco` e `%LOCALAPPDATA%\Reco`.
   - Molde: `C:\Dev\lacre\src-tauri\tauri.conf.json:45-54` (`resources` do motor e bloco `nsis`). Rodar `powershell -ExecutionPolicy Bypass -File app\build.ps1`
     → última linha `Instalador: ...\nsis\Reco_<versão>_x64-setup.exe`. Daqui em diante `$prod` = `Reco`.
   - Antes do build, para o passo 14: `grep -n "ready em" engine/reco_engine/boot.py` → 1 linha que loga no stderr `ready em <n> s`
     quando o evento `ready` sai. Se não houver, acrescentar essa linha (sem mudar comportamento); o build congela o motor de novo.
   - Anotar o tamanho do instalador no relatório (hoje não há número; o Lacre sem OpenVINO deu 30,6 MB).
   - Nota (2026-11-12, frescor): o `.app_name("Reco Novo")` está em `app/src-tauri/src/lib.rs:207`; o `atalho.rs:7` só o
     cita num comentário. Outros `Reco Novo` versionados em `app/`: `build.ps1:107` (título), `lib.rs:38` (comentário),
     `windows/hooks.nsh:1,6` (comentários, só ASCII) e `o.versao-texto` em `ui/src/i18n/pt.ts` e `en.ts`. O `app/ui/dist`
     (fora do git) só sai limpo depois do build, então o grep da prova roda depois dele. O mutex
     (`instancia.rs:58`, `Local\Reco.SingleInstance`) não depende do nome e não muda.
   - Nota (2026-11-12, frescor): o motor loga pelo `logging` com `%(asctime)s %(levelname)s %(name)s: %(message)s`
     (`engine/reco_engine/server.py:178-179`), então a linha nasce `<data hora> INFO reco_engine.boot: ready em <n> s`, e o
     `^ready em ` do passo 14 nunca casaria. A linha entra por `log.info` em `boot._announce` (só no `ready` sem erro), e o
     passo 14 casa `'reco_engine.boot: ready em '`.
9. [x] Desinstalar o "Reco Novo" e só então instalar o "Reco", em silêncio, com os dois apps fechados pelo Gabriel na bandeja. — **prova:** `Test-Path "$env:LOCALAPPDATA\Reco Novo\uninstall.exe"` → `False`; depois `Start-Process $setup -ArgumentList '/S' -Wait; Test-Path $exe` → `True`
   **reprova se:** o velho ou o "Reco Novo" ainda está vivo (parar: pode estar gravando), o "Reco Novo" segue instalado ou no Menu Iniciar, `False` no fim, ou SmartScreen/Defender bloqueia.
   - Com os dois apps fechados, antes de instalar: as checagens que gravam do bloco "Herdado da Fase 3" (acima); depois
     de instalar, o resto daquele bloco, antes do passo 10.
   - Antes de tudo: `Get-Process | ? Path -like '*\Reco*\*'` → vazio (pega `dist\Reco\Reco.exe`, a reserva e a pasta `Reco Novo`).
     Se não vier vazio, pedir ao Gabriel que saia pela bandeja: a sessão nunca mata app em uso (pode estar gravando).
   - Nota (2026-11-12, revisão): com os apps fechados e antes de instalar, recopiar o config para a reserva (o velho o
     grava a cada ajuste): `Copy-Item "$env:USERPROFILE\.reco_config.json" "$env:LOCALAPPDATA\Reco-reserva\reco_config.json"`
     e conferir por `Get-FileHash` nos dois (iguais).
   - Se `Test-Path "$env:LOCALAPPDATA\Reco Novo\uninstall.exe"` já der `False`, o "Reco Novo" não está instalado: pular a desinstalação.
   - Desinstalar: `$u="$env:LOCALAPPDATA\Reco Novo\uninstall.exe"; Start-Process $u -ArgumentList '/S'`, depois esperar até 120 s
     como no passo 10: `$t=0; while ((Test-Path $u) -and $t -lt 120) { Start-Sleep 1; $t++ }; Test-Path $u` → `False`.
   - Conferir que sumiram `"$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Reco Novo.lnk"` (`Test-Path` → `False`) e a chave
     `reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "Reco Novo"` (`$LASTEXITCODE` → `1`; se `0`, `reg delete` dessa chave com `/f`).
   - A soma dos modelos do passo 3 continua igual depois de desinstalar o "Reco Novo".
   - Bloqueio do Defender ou do Smart App Control: anotar e seguir `C:\Dev\lacre\docs\LIMITATIONS.md`; vira armadilha (passo 23).
   - Nota (2026-11-12, execução, 16:37 a 16:51): o dono autorizou ("Já pode instalar sim") e, antes da sessão fechar o
     velho, ele mesmo saiu do velho e abriu o "Reco Novo" instalado (`aac7ca7`) pelo Menu Iniciar às 16:39, gravou um
     teste curto e mudou o ganho do sistema (0,5 → 1,0, mantido). Esse build antigo **baixou uma revisão nova do modelo**
     às 16:39:45 (`4929ae8` → `b568445`, 828 097 157 → 828 098 952 bytes): a soma de referência do passo 10 passou a
     ser a nova, e a `Reco-reserva\models` fica na revisão anterior. Fechado pela sessão só depois de motor ocioso (CPU
     0,1% em 25 s, `--checar-gravando` duas vezes) e pelo Sair da bandeja por mensagem (`saída: Ocioso`). O guarda
     `Get-Process | ? Path -like '*\Reco*\*'` acusa também o gravador do Medal (`…\Medal\recorder-…\`): falso positivo
     que se lê pelo caminho. Config copiado para a reserva às 16:53 (depois de instalar; hashes iguais). Detalhe no relatório,
     seção "Passos 9 a 17 — app instalado".
10. [x] Provar que instalar e desinstalar não apagam os modelos que moram na mesma pasta (F4-D4). — **prova:** a soma do passo 3 medida duas vezes, cada uma só depois de a ação terminar (sub-itens) → igual à anotada nas duas vezes
    **reprova se:** a soma cai ou `models\` some. Parar e repor com `robocopy "$env:LOCALAPPDATA\Reco-reserva\models" "$env:LOCALAPPDATA\Reco\models" /E` antes de seguir.
    - Desinstalar: `$u="$env:LOCALAPPDATA\$prod\uninstall.exe"; Start-Process $u -ArgumentList '/S'`, depois esperar até 120 s
      (o desinstalador do NSIS se copia e volta antes de terminar):
      `$t=0; while (((Test-Path $exe) -or (Test-Path $u)) -and $t -lt 120) { Start-Sleep 1; $t++ }; Test-Path $exe` → `False`, e medir.
      Se der `True` depois de 120 s, a desinstalação travou: parar e anotar.
    - Reinstalar: `Start-Process $setup -ArgumentList '/S' -Wait; Test-Path $exe` → `True`, e medir.
    - ⚠️ Nunca rodar instalador ou desinstalador em silêncio com o app novo gravando: o `/S` fecha à força
      `$INSTDIR\<binário>.exe` pelo Restart Manager (`RmForceShutdown`, macro `CheckIfAppIsRunning` do molde 2.12.4).
      O Restart Manager registra o arquivo pelo caminho; o molde não tem `FindProcess`/`KillProcess` por nome, então o
      velho em `dist\` não deve ser afetado. Mesmo assim, o velho fica fechado durante os passos 9 e 10.
    - Lido no molde do Tauri CLI 2.12.4 (`node_modules` do Lacre): `StrCpy $INSTDIR "$LOCALAPPDATA\${PRODUCTNAME}"`, que é
      a mesma `%LOCALAPPDATA%\Reco` de `_user_data_dir()` (`reco.py:578-582`); a desinstalação faz `RMDir "$INSTDIR"`
      sem `/r` e só apaga recursivo `$LOCALAPPDATA\${BUNDLEID}` com a caixa "apagar dados" marcada.
11. [ ] Conferir o atalho do Menu Iniciar e o atalho de teclado. — **prova:** o comando "Atalho" do passo 3 → `TargetPath` igual a `$exe` e `HotKey` vazio
    **reprova se:** o alvo ainda é `dist\Reco\Reco.exe` ou o `HotKey` não vem vazio (ex.: `Ctrl+Shift+R`; dois donos para a mesma tecla).
    - O NSIS grava `$SMPROGRAMS\${PRODUCTNAME}.lnk`, o mesmo arquivo de `_shortcut_path` do app velho (`reco.py:4867-4870`),
      que cria o `.lnk` com `HotKey='CTRL+SHIFT+R'` (`reco.py:4892-4908`). O instalador sobrescreve; ver F4-D5.
    - Manual (sem comando: tecla global não se dispara por script com confiança): ligar o atalho em Opções (nasce
      desligado, `casco_atalho`, Fase 3 passo 10), app na bandeja, Ctrl+Shift+R → a janela aparece com foco no botão
      principal. Repetir com o app fechado e anotar o que acontece.
12. [ ] Exclusão mútua nos dois sentidos (D7). — **prova:** com o app novo aberto, os dois primeiros comandos abaixo, nesta ordem → `True` e `True`; com o velho aberto, o terceiro → `True` e `0`
    **reprova se:** o `TryOpenExisting` dá `False` (parar sem lançar o velho), ou um `WaitForExit` dá `False` (o segundo app ficou vivo: dois apps nos mesmos dispositivos e no mesmo config).
    - Sem lançar nada: `$m=$null; $ok=[Threading.Mutex]::TryOpenExisting('Local\Reco.SingleInstance',[ref]$m); if($m){$m.Dispose()}; $ok`.
      O `Dispose` é obrigatório: um handle esquecido numa janela PowerShell aberta mantém o mutex vivo e o velho fecha
      sozinho no passo 16. Sintaxe conferida em 11/11/2026 (deu `True` com o app velho aberto).
    - Só então: `$p=Start-Process C:\Dev\Reco\dist\Reco\Reco.exe -PassThru; $p.WaitForExit(60000)` (o velho sai sozinho).
    - Se o velho ficou vivo: fechá-lo pela bandeja na hora, antes de qualquer gravação.
    - O mutex `Local\Reco.SingleInstance` (`reco.py:5203-5204`) é criado pelo casco por Win32 próprio, sem o plugin de
      instância única (F3-D2, Fase 3 passo 7); o `TryOpenExisting` acima confere que o build instalado o cria.
    - O velho sai calado depois de mandar `Reco.Show` (`reco.py:5205-5210`) e a janela do novo aparece (receptor do
      passo 7 da Fase 3). Se não aparecer, P24 fica ✗.
    - Sentido inverso (o Gabriel sai do novo pela bandeja e abre `C:\Dev\Reco\dist\Reco\Reco.exe`):
      `$p=Start-Process $exe -PassThru; $p.WaitForExit(60000); $p.ExitCode` → `True` e `0`. O novo manda `Reco.Show`
      e sai calado (Fase 3 passo 7), sem ligar motor nem captura; a janela do velho aparece e `Get-Process` mostra só o velho.
    - Depois: Sair do velho pela bandeja e reabrir o novo (`Start-Process $exe`) para os passos seguintes.
13. [ ] Iniciar com o Windows, opcional e desligado por padrão (F4-D6). — **prova:** ligar em Opções e rodar `reg query HKCU\Software\Microsoft\Windows\CurrentVersion\Run /v Reco; $LASTEXITCODE` → valor com o caminho de `$exe` seguido de `--oculto`, e `0`; desligar e repetir → `1`
    **reprova se:** o valor existe sem o usuário ligar, sai com o nome `Reco Novo`, falta o `--oculto`, ou some/fica depois da ação contrária.
    - `tauri-plugin-autostart` 2.7.0 grava o valor com o `app_name` na chave Run do usuário (`lib.rs:207-229`); o passo 8 o trocou para `Reco`.
    - Seguir o modelo da Guarita: o registro é a verdade e a tela reconcilia ao abrir (`autostart.ts`, cabeçalho).
    - Manual, na próxima vez que o Gabriel reiniciar: com a opção ligada, o app sobe com `--oculto` (Fase 3 passo 10) e o
      ícone aparece na bandeja sem abrir a janela.
14. [ ] Medir "pronto para gravar" no app instalado (D12), com método próprio. — **prova:** o laço do 1º sub-item em 3 aberturas a quente → mediana ≤ a mediana de `abrir_pronta_s` do relatório da Fase 0; Gravar clicado logo depois do `ready` põe o cronômetro a andar sem esperar `aquecimento pronto`
    **reprova se:** a mediana passa da de `abrir_pronta_s`, o laço sai pelo teto de 60 s (não achou janela ou `ready em`), ou Gravar espera o aquecimento da transcrição.
    - Laço (PowerShell, `$log` dos Nomes): `$n=@(Get-Content $log -EA 0).Count; $sw=[Diagnostics.Stopwatch]::StartNew(); $p=Start-Process $exe -PassThru;`
      `do { Start-Sleep -m 50; $w=(Get-Process -Id $p.Id -EA 0).MainWindowHandle -ne 0; $r=@(Get-Content $log -EA 0 | Select -Skip $n) -match 'reco_engine.boot: ready em ' }`
      (2026-11-12: era `'^ready em '`, que não casa com o formato do log do motor; ver a nota do passo 8)
      `until (($w -and $r) -or $sw.Elapsed.TotalSeconds -gt 60); $sw.Elapsed.TotalSeconds` → acima de 60 = "não achou" (o processo saiu, ou falta a linha do passo 8).
    - Por que não o método da Fase 0: ele acha `TkTopLevel` e os HWND `Button`, que o WebView2 não tem. Pronto = janela visível
      e evento `ready` do motor (Gravar habilitado, Fase 3 passo 12); no velho Gravar funciona assim que a janela chega a
      alfa 255, por isso `abrir_pronta_s` (do `Popen` até lá) é o número comparável.
    - A linha `ready em <n> s` é do motor no stderr (passo 8), que o casco anexa ao `$log`. Se o log girou para `.log.old`
      (passa de 2 MB, menos linhas que `$n`), repetir a abertura.
    - Sem GPU no caminho de gravar: o motor loga `aquecimento pronto em <n> s` no stderr (Fase 2, passo 3). Clicar Gravar logo
      depois do `ready`; se o aquecimento já tiver terminado antes do clique, anotar o tempo dele (a cláusula vale pelo D12).
    - Entre aberturas: Sair pela bandeja (nada de `Stop-Process`), sem gravação em curso. Anotar `live` e `device` do config,
      como a Fase 0: com o ao vivo ligado a GPU entra no caminho de gravar (`reco.py:3769-3784`); medir com ele desligado.
    - "A frio" = primeira abertura depois de reiniciar o Windows: 3 reinícios, que o Gabriel faz (combinar a hora). Informativo:
      a Fase 0 não tem número a frio (a rodada 1 dela já pega cache quente). Números no relatório, ao lado dos da Fase 0.
15. [ ] Contrato de falha (D11) no build instalado, não só no de desenvolvimento. — **prova:** gravar 40 s, `Get-Process | ? Path -eq $exe | Stop-Process -Force`, depois `python tools/paridade.py <esse mp3>` → `xing=ok` e `dur` ≈ 40
    **reprova se:** o MP3 fica sem cabeçalho (o motor não fechou o arquivo ao ver o stdin fechar) ou some.
    - Segundo caso: gravar 40 s e matar só o processo do motor → a tela mostra alarme em até 2 s e nunca exibe
      "gravando" depois disso. O MP3 parcial pode mentir a duração: reparar só numa cópia, nunca na pasta real
      (a Fase 3, passo 17, proíbe): `mkdir -p temp/reparo && cp "<esse mp3>" temp/reparo/ && python tools/reparar_duracao.py temp/reparo --aplicar`.
16. [ ] Ensaiar a volta à reserva com o procedimento exato abaixo (o mesmo que vai para a doc no passo 21). — **prova:** entre e) e f), `Get-Process -Name Reco -EA 0 | Select -Expand Path` → só `C:\Dev\Reco\dist\Reco\Reco.exe`; gravação de 30 s do velho passa em `python tools/paridade.py`
    **reprova se:** o velho fecha sozinho (o novo ainda segura o mutex), não grava, ou a gravação sai `FALHOU`.
    - a) Bandeja do app novo → Sair. O X só esconde; Sair espera o arquivo fechar se estiver gravando (D11).
    - b) Se "iniciar com o Windows" estiver ligado, desligar antes (ou `reg delete HKCU\Software\Microsoft\Windows\CurrentVersion\Run /v $prod /f`).
    - c) Conferir `_migracao` (comando do passo 3): `2` segue; maior que 2, parar e ler a armadilha 029 antes de abrir o velho.
    - d) Abrir `C:\Dev\Reco\dist\Reco\Reco.exe`; se a pasta estiver quebrada, a cópia `%LOCALAPPDATA%\Reco-reserva\Reco\Reco.exe`.
      Nota (2026-11-12, revisão), antes de abrir: sem `%LOCALAPPDATA%\Reco\models`, repor com
      `robocopy "$env:LOCALAPPDATA\Reco-reserva\models" "$env:LOCALAPPDATA\Reco\models" /E` (código < 8 = ok); com o
      `~/.reco_config.json` ilegível (`python -c "import json,pathlib;json.loads((pathlib.Path.home()/'.reco_config.json').read_text(encoding='utf-8'))"`
      dá erro), copiar de volta `%LOCALAPPDATA%\Reco-reserva\reco_config.json`.
    - e) Atalho do velho: Opções → "Remover atalho" → "Criar atalho (Ctrl+Shift+R)" (`reco.py:4879-4890`). Isso
      troca o `Reco.lnk` do Menu Iniciar para o velho, e o novo some do menu até ser reinstalado.
    - Aqui roda a prova do passo (velho vivo sozinho, gravação de 30 s pela régua).
    - f) Voltar ao novo: Sair do velho pela bandeja e rodar `Start-Process $setup -ArgumentList '/S' -Wait` (repõe o atalho do novo).
    - Os dois se excluem pelo mutex (D7): com um aberto, o outro não sobe. Nunca forçar os dois.

### C. Paridade funcional e uso real

17. [ ] Executar o checklist de paridade abaixo com o app instalado e gravar o resultado de cada linha no relatório. — **prova:** `grep -c "| ✗ |" <relatório da fase>` → `0` e `grep -c "| ✓ |" <relatório da fase>` → número de linhas do checklist
    **reprova se:** alguma linha ✗, ou linha sem resultado. Linha que a Fase 3 tirou de propósito entra como ✓ com o motivo.
18. [ ] Uso real: 6 gravações do Gabriel com o app novo (F4-D1), cada uma pela régua. — **prova:** `python tools/paridade.py <as 6> --exigir-txt` → 6 linhas `ok` ou `ALERTA` e `PASSOU`
    **reprova se:** alguma `FALHOU`, ou faltam G1 (≥ 60 min) ou G2 (fone).
    - Byte a byte em G3 e numa segunda gravação ≤ 10 min: `python tools/paridade.py <mp3> --txt-contra-script` → `script=igual`.
    - Nota (2026-11-12, revisão): com `--exigir-txt`, o `x.txt` vazio (`(no content recognized)`) também reprova.
    - G2 com fone: use `--sem-sistema` só se o outro lado de fato não falou; `alinhamento=sem correlacao` é esperado.
    - `ALERTA` de salto: comparar com a linha de base do passo 6 (F4-D2) e anotar carga da máquina na hora.
19. [ ] O ouvido dos agentes segue igual com o app novo aberto. — **prova:** `python tools/transcrever.py temp/ouvido/<um .opus ou .m4a qualquer> --forcar` → imprime o caminho `<arquivo>.opus.txt`, rc 0; `python tools/test_antiloop.py <G1> large-v3-turbo GPU` → `PASSOU`
    **reprova se:** rc ≠ 0 ou `FALHOU`. Erro de GPU indisponível: repetir com o app fechado para separar disputa de GPU
    (o motor aquecido segura ~1,35 GB, ARMADILHAS) de regressão; se só falha com o app aberto, vira armadilha.
    - O `--forcar` é obrigatório: sem ele, um `.txt` antigo dá "pulado" com rc 0 e a prova passa sem transcrever.

### D. Documentação e fechamento

20. [ ] `README.md`: telas novas nas listas de recursos (EN `:22-75`, PT `:133-188`), instalação pelo instalador e o `app\build.ps1` (`:89-98`, `:201-210`), screenshot novo. — **prova:** `grep -c "setup.exe" README.md` → ≥ 2 e `git diff --stat docs/screenshot.png` → binário alterado
    **reprova se:** só uma língua mudou, ou o screenshot é o antigo.
    - O release público é decisão pendente do Gabriel: até o "sim", o README descreve gerar o `setup.exe` pelo build
      (as duas línguas), sem prometer download em Releases.
    - Repo público: o screenshot não mostra nome de gravação, transcrição nem nome de pessoa; usar pasta vazia ou o
      backend falso no navegador (Playwright, molde `backend.ts` do Lacre). Ajustar `width` do `<img>` (`README.md:15`).
21. [ ] `docs/ARQUITETURA.md`: seções "Camadas do app novo" e "Reserva e volta ao app antigo"; `## Build` (`:14-29`) cita o `app\build.ps1`. — **prova:** `grep -n "^## " docs/ARQUITETURA.md` → as duas seções novas
    **reprova se:** falta uma das seções ou o `## Build` só fala do PyInstaller.
    - "Camadas do app novo": casco (Rust), motor (Python, `engine/`), protocolo (JSON Lines), com link para a doc da Fase 2.
    - "Reserva e volta ao app antigo": o procedimento do passo 16, letra por letra, e o aviso do mutex (D7).
    - `docs/_INDICE.md` ganha 1 linha se nasceu doc nova nas Fases 2 a 4.
    - Nome velho: `grep -rn "Reco Novo" README.md CLAUDE.md docs` → nada fora de nota histórica (a Fase 3 documentou com esse nome).
22. [ ] `CLAUDE.md` do Reco: a regra de compilar (`CLAUDE.md:16-23`) passa a citar o `app\build.ps1` em 1–3 linhas + caminho; a abertura (`:3-8`) troca "Tkinter". — **prova:** `wc -c CLAUDE.md` → < 6144 e `git commit` passa no gate `gate-claude-md`
    **reprova se:** passa de 6144 bytes (hoje 5210) ou o texto cresce sem tirar nada.
    - Ponto que não pode faltar: mexer no `reco.py` agora exige os dois builds, porque o motor importa o `reco`
      e a reserva é o próprio `reco.py` congelado. Porquê e detalhe vão para `docs/ARQUITETURA.md`, não para cá.
23. [ ] Armadilhas novas, uma por pegadinha confirmada nesta fase, só por `python tools/visoes.py novo "título"`. — **prova:** `python tools/visoes.py validar docs/armadilhas.d/<os novos>` → rc 0 e `git status --short docs/armadilhas.d` lista os novos
    **reprova se:** `docs/ARMADILHAS.md` foi editado à mão, ou uma pegadinha do relatório ficou sem entrada.
    - Candidatas já vistas: o `Reco.lnk` dividido entre instalador e app velho; o mutex do plugin não é o do app
      velho; a pasta do instalador é a dos modelos; o que mais aparecer nos passos 9 a 19.
24. [ ] Hub `C:\Dev\cerebro\projetos\reco.md` por `Edit` ancorado (abertura, "Estado agora", "Roadmaps em voo") e fragmento do diário. — **prova:** `python C:/Dev/cerebro/scripts/compilar_fragmentos.py diario --escrever` → rc 0 e a página do dia cita a Fase 4
    **reprova se:** o hub ainda diz "Tkinter" como o app em uso, ou o fragmento não aparece na página gerada.
    - Fragmento: `C:\Dev\cerebro\pessoal\diario\<AAAA-MM-DD>\<HHMM>-<sid8>-reco-rust-fase-4.md`, `projeto: reco`, sem host nem segredo.
25. [ ] Relatório no sidecar e commit por pathspec (nunca `git add -A`, nunca `--no-verify`). — **prova:** `git -C C:/Dev/Reco status --short` → nada da fase fora do commit
    **reprova se:** sobra arquivo da fase sem commit, ou o pre-commit foi pulado.
    - `git add tools/paridade.py docs/TOOLS.md docs/ARQUITETURA.md docs/_INDICE.md README.md docs/screenshot.png CLAUDE.md docs/armadilhas.d/<novos> app/src-tauri/tauri.conf.json roadmap/2026-11-11-melhoria-reco-em-rust.d/<relatório>`.
    - Nota (2026-11-12, revisão): `tools/test_paridade.py`, `engine/reco_engine/__init__.py` (motor 0.3.0),
      `tools/engine_checks_proto.py` e `docs/PROTOCOL.md` já entraram em commits da revisão.
    - Somar ao pathspec o que o passo 1 mudou na versão: `app/src-tauri/Cargo.toml`, `app/src-tauri/Cargo.lock`, `app/package.json` e o lockfile do front.
    - Somar também `app/src-tauri/src/atalho.rs`, qualquer outro arquivo de `app/` que o grep do passo 8 apontou e
      `engine/reco_engine/boot.py`, se o passo 8 acrescentou a linha `ready em`.
    - Repo público: o relatório não leva caminho com nome de usuário, nome de gravação nem trecho de transcrição.
    - O hub e o fragmento do passo 24 moram no repo `C:\Dev`: commit à parte lá, também por pathspec.

### Checklist de paridade (inventário do mapa § 1)

Cada linha vira ✓ ou ✗ no relatório, com a evidência. "Script" = comando com saída conferível; "manual" = olho humano.

| # | função do app velho | como provar no app novo | tipo |
| --- | --- | --- | --- |
| P1 | Janela abre, arrasta, minimiza; X esconde na bandeja (`reco.py:2853-2996`) | abrir, arrastar, minimizar, X → ícone segue na bandeja | manual |
| P2 | Janela não pula (D4; a queixa nº 1) | no commit do `$setup`: a prova do passo 14 da Fase 3 (`testar-anti-pulo.cjs` e `testar-contrato.cjs` com `--url` no backend falso) → 0 falhas (F1-D12); no build instalado, 10 cliques sem a janela mudar de tamanho | script + manual |
| P3 | VU dos dois canais e ganho 0–10× (`reco.py:3180-3216`) | ganho do mic em 2,0× → `mic_gain` = 2.0 no `~/.reco_config.json` | script |
| P4 | Gravar, Pausar, Continuar, Parar, cronômetro (`reco.py:3565`) | 60 s com 20 s de pausa → `dur` ≈ 40 na régua (a pausa descarta, `reco.py:1797`) | script |
| P5 | Salvar copia o caminho entre aspas (`reco.py:4077`) | `Get-Clipboard` → `"...\gravacao_reco_AAAA-MM-DD_HH-MM-SS.mp3"` (`reco.py:1695-1696`) | script |
| P6 | Saídas do menu: Salvar + transcrever, Transcrever e excluir, Excluir (`reco.py:4082-4111`) | cada uma: `.txt` nasce, MP3 vai à Lixeira (`reco.py:616-622`) conferido na Lixeira | script + manual |
| P7 | Reproduzir no player padrão | o player abre com o arquivo | manual |
| P8 | Status em uma linha e "Abrir transcrição" (`reco.py:4357`) | status não quebra linha; o link abre o `.txt` | manual |
| P9 | Parar uma transcrição no meio (`reco.py:4351`) | parar → nenhum `.txt` novo ao lado do MP3 | script |
| P10 | Ao vivo: painel e passada final (`reco.py:3286-3317`, `:4005`) | caixa ligada, 5 min → texto no painel; ao parar, `x.txt` diarizado | manual + script |
| P11 | Modo nota, agora com botão (`reco.py:3813`, `:4028`) | `.md` na pasta de notas, caminho no `Get-Clipboard`, MP3 apagado | script |
| P12 | Dispositivo Auto console/comunicação/manual e Atualizar (`reco.py:1382-1470`) | escolher "Auto comunicação" → `mic_device` = `auto:comm`; trocar o padrão do Windows → a gravação seguinte segue | script + manual |
| P13 | Pasta de saída | trocar → a gravação seguinte nasce lá (`output_dir`) | script |
| P14 | "Processar em" AUTO/GPU/NPU/CPU | trocar → `device` no config muda | script |
| P15 | Idioma PT/EN (`reco.py:269-512`) | EN → interface em inglês e arquivo `recording_reco_...` (`reco.py:1695`) | script + manual |
| P16 | Tema | o que a Fase 1 e a Fase 3 decidiram (claro/escuro); anotar a troca do tema livre | manual |
| P17 | Telas Gravações, Converter, Transcrever (`reco.py:4308`) | navegar entre as abas Gravar, Biblioteca, Arquivo e Opções; gravando ou transcrevendo, a aba que conflita fica desabilitada com o motivo na própria aba (F1-D7; o velho bloqueava só com aviso no status, `:4310-4318`) | manual |
| P18 | Transcrever arquivo escolhido (`reco.py:4826`) | `.m4a` qualquer → `.txt` em texto corrido | script |
| P19 | Biblioteca: busca por nome e conteúdo, colunas, ações, duplo clique (`reco.py:4385-4724`) | mesma contagem de itens que o velho mostra; cada ação funciona | manual |
| P20 | Resumo IA (`reco.py:4663-4670`) | gera `x.resumo.md` ao lado | script |
| P21 | Converter vídeo para MP3 16 kHz mono (`reco.py:836`) | `python -c "import av,sys;s=av.open(sys.argv[1]).streams.audio[0];print(s.rate,s.channels)" <saída>` → `16000 1` | script |
| P22 | Bandeja: hover sem roubar foco, clique fixa, menu, ícone vermelho gravando (`tray.py:197-236`) | conferir cada um; o hover sem foco foi provado na Fase 0 | manual |
| P23 | Modelo atualiza sozinho; aviso de versão nova (`reco.py:1230`, `:1274`) | o casco pede `model.update_check` e `app.update_check` 1,5 s depois do primeiro `ready` (Fase 3, passo 5); o app novo `0.3.0` não acusa versão nova contra `v0.2.0` | manual |
| P24 | Instância única e atalho | passos 11 e 12 | script |
| P25 | Headless `Reco.exe --transcribe` (D6, `reco.py:5148-5179`) | o casco repassa ao motor (Fase 3, passo 7): `(Start-Process $exe -ArgumentList '--transcribe','<mp3 em temp/>','--diarize' -Wait -PassThru).ExitCode` → `0` (com `&` o PowerShell não espera exe de interface gráfica, Fase 3) e `x.txt` ao lado; o `dist\Reco\Reco.exe` segue valendo até a Fase 7 | script |
| P26 | Sair no meio da gravação salva o MP3 (D11) | Sair pela bandeja gravando → régua `xing=ok` | script |

## Decisões da fase

| id | decisão | motivo | confiança | reverte se |
| --- | --- | --- | --- | --- |
| F4-D1 | N = 6 gravações estéreo reais em ≥ 5 dias (G1 a G6, lista abaixo da tabela) mais 1 nota (P11) | cobre os modos que já deram problema (AEC, fone, pausa, ao vivo) sem prender o Gabriel semanas | média | uma régua reprovar: consertar e refazer 3 do tipo que falhou |
| F4-D2 | Salto de alinhamento não reprova a fase, vira ALERTA comparado à linha de base | a captura ainda é a do Python (Fase 5 corrige); defeito herdado não é régua de paridade (relatório 2 § B) | média | mais de 2 das 6 com salto: ver se o motor separado piorou a carga |
| F4-D3 | Reserva = `dist\Reco` + cópia congelada em `%LOCALAPPDATA%\Reco-reserva`, até a Fase 7 | `-Clean` ou build falho apagam `dist`; a cópia fica fora do repo e fora da pasta do instalador | alta | a Fase 7 aposentar o app Tk (aí apagar a cópia) |
| F4-D4 | Instalar na pasta padrão do NSIS currentUser, que divide `%LOCALAPPDATA%\Reco` com `models` e `ovcache` | padrão do Tauri; a desinstalação não é recursiva (molde 2.12.4); mudar exige hook NSIS | média | o passo 10 mostrar modelo sumindo: mudar a pasta por hook NSIS |
| F4-D5 | O instalador fica dono do `Reco.lnk` do Menu Iniciar (sem hotkey); a tecla passa a ser o atalho global do app novo | um dono por tecla; o `.lnk` com hotkey do velho só lança o exe velho | média | o atalho global colidir com outro app: escolher outra combinação na tela |
| F4-D6 | "Iniciar com o Windows" nasce desligado e só liga pela tela | o app velho não iniciava sozinho; modelo da Guarita (`autostart.ts`) | alta | o Gabriel pedir ligado por padrão |
| F4-D7 | Só instalador NSIS, sem MSI | NSIS faz `currentUser` sem admin; o MSI do Tauri instala para a máquina (premissa) e dobra o artefato | média | alguém pedir MSI ou distribuição por política de empresa |
| F4-D8 | Byte a byte só em gravações ≤ 10 min e só se o passo 7 provar determinismo | o transcritor leva minutos por hora de áudio; sem determinismo a comparação mente | alta | o passo 7 falhar: régua fica `pior` + diarizado, e a diferença vai ao relatório |
| F4-D9 | Versão do app novo `0.3.0` | maior que `0.2.0` do velho e do release Latest; o aviso de versão compara números (`reco.py:1268-1272`) | alta | — |

> Nota (2026-11-12, frescor): o `app.update_check` do motor chama `reco.check_app_update()` (`engine/reco_engine/extras.py:82-85`),
> que compara o release Latest com o `reco.APP_VERSION` (`0.2.0`, `reco.py:34`, `:1284`), **não** com a versão do casco.
> Hoje isso não muda nada (Latest `v0.2.0` não é maior que `0.2.0`), e P23 passa. Mas, se um dia sair um release `v0.3.0`,
> o app novo (motor com `reco` 0.2.0) passaria a avisar "versão nova" para sempre. Decidir antes do release (Pendente):
> o casco mandar a própria versão no `app.update_check`, ou o `APP_VERSION` subir junto. Esta fase não mexe no `reco.py`.

As 6 gravações de F4-D1:

- G1: reunião ≥ 60 min no alto-falante (Meet ou Teams): AEC, arquivo longo, `test_antiloop` do passo 19.
- G2: reunião com fone ≥ 15 min: dispositivo Auto seguindo o fone; o alinhamento sai `sem correlacao`, e quem julga é
  `r_zero_inicio` e o `.txt` (é o caso do card do fone no hub).
- G3: curta, 3 a 10 min, com uma pausa no meio: byte a byte contra o transcritor dos agentes e P4.
- G4: ≥ 10 min com o ao vivo ligado: P10 e a passada final.
- G5 e G6: uso livre da semana (o que aparecer); uma delas ≤ 10 min entra no byte a byte.

## Pendente (dono: gabriel)

- **Aprovar a troca.** Usar o app novo como app do dia a dia por pelo menos 5 dias úteis, com as 6 gravações de
  F4-D1, e dizer "aprovo" ou o que falta. Sem isso a Fase 5 não começa e o app velho segue como reserva.
  Recomendação: aprovar só se nenhuma gravação sair `FALHOU` e nada do checklist estiver ✗.
- **Distribuição pública no GitHub (`dosxnjos/reco`).** Recomendação: sim, depois da aprovação acima, como release
  `v0.3.0` em rascunho que ele revisa antes de publicar. Nada é publicado sem o "sim" dele.
  - Desenho: o `build.yml` do Lacre cortado para um job Windows (D9): rascunho → motor congelado com smoke
    `hello` → `tauri-action` → nomes fixos `Reco-Windows-Instalador.exe` e zip portátil → conferência dos arquivos.
  - Consequência 1: ao publicar, todo Reco `0.2.0` instalado passa a mostrar "Nova versão" (`reco.py:1274-1290`
    lê o release Latest; rascunho não conta).
  - Consequência 2: instalador sem assinatura; SmartScreen e Defender podem acusar (`C:\Dev\lacre\docs\LIMITATIONS.md`).
  - Consequência 3: o modelo turbo (790 MB) não vai no instalador; baixa na primeira transcrição, como hoje.
  - Alternativa: só o instalador local desta máquina (o que esta fase entrega de qualquer forma).

## O que esta fase NÃO faz

- Não troca a captura nem o MP3 (Fase 5) nem a transcrição (Fase 6); o motor é o Python da Fase 2.
- Não apaga o app velho, o `build.ps1`, o `reco.spec` nem o `tray.py` (Fase 7). O `reco.py` não cresce.
- Não mexe na sentinela da central que lê `"(no content recognized)"` no `reco.py` (Fase 7).
- Não muda nome de arquivo, formato do MP3, config nem o contrato do `tools/transcrever.py` (D6, D8).
- Não publica release, não cria tag e não liga CI sem o "sim" do Gabriel.
- Não roda os dois apps juntos para comparar (D7); a comparação é sempre pelo disco.

## Gatilho que fecha

- Passos 1 a 25 com a prova verde e o relatório no sidecar com os números (D12, linha de base, 6 gravações).
- Checklist de paridade sem ✗; `tools/paridade.py` commitado e documentado em `docs/TOOLS.md` (a Fase 5 o usa como gate).
- Ensaio de volta à reserva feito uma vez com sucesso e descrito em `docs/ARQUITETURA.md`.
- O Gabriel disse "aprovo" (Pendente). Só então a Fase 5 começa, com o app novo como app do dia a dia.

## Premissas não verificadas

- As Fases 0 a 3 têm md, mas ainda não rodaram: os valores reais de `productName` (`Reco Novo`), `identifier`, versão, nome
  do binário e do exe do motor saem do código no passo 1; o caminho do `$log` sai do relatório da Fase 3.
- O motor loga `ready em <n> s` no stderr ao emitir o evento (o passo 8 confere e acrescenta se faltar), e o casco anexa o
  stderr ao `$log` como o Lacre; se a Fase 3 mudou o nome ou a pasta do log, o passo 14 usa o que ela fez.
- O mutex `Local\Reco.SingleInstance` (F3-D2, Fase 3 passo 7) e o `--oculto` do autostart (Fase 3 passo 10) estão no
  md da Fase 3; os passos 12 e 13 conferem no build instalado.
- O MSI do Tauri instalar para a máquina inteira (F4-D7) vem de memória, não foi lido no molde.
- O `tools/transcrever.py` ser determinístico na mesma máquina e no mesmo device: o passo 7 prova ou derruba.
- `SendKeys` não dispara atalho global com confiança: por isso o passo 11 é manual.
- O `uninstall.exe` do NSIS voltar antes de terminar (ele se copia para o TEMP) vem de memória: por isso o passo 10 espera o `$exe` sumir.
- A trava de 500 linhas cobre `.rs` e `.ts` desde o passo 2 da Fase 3 (D3), então os arquivos que esta fase toca em
  `app/` passam por ela no commit; em `7c5c1a1` o `tools/tamanho.json` ainda não lista as duas.
