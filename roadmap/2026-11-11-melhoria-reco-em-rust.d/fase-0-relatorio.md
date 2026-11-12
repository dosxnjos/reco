## Relatório de execução — Fase 0 (2026-11-11, sessão 4c65eb01)

> **Parcial:** Bloco A feito; Bloco B medido (passos 9 a 13) com o app do Gabriel fechado; a reabertura do
> passo 14 ficou para a última etapa (as próximas precisam do app fechado). Este arquivo cresce até o fecho.

Frescor: ok (0 dias, 0 commits em `reco.py`, `tray.py` e `tools/` desde `7c5c1a1`).

## Bloco A — com o Reco do Gabriel aberto

### Passo 2 — RAM viva

`python tools/medir_partida.py --ram-viva` → `{"pid": 36616, "ws_mb": 85.2, "privado_mb": 1016.3, "cpu_pct": 0.9}`

- Condição: app aberto desde 19:14 de 11/11 (exe `dist/Reco/Reco.exe`), parado, sem gravar; escala 125%.
- `privado_mb` de 1016 MB sugere modelo carregado na memória (transcrição feita mais cedo); `ws_mb` é o que
  está em RAM agora.
- CPU parado 0,9% (< 5%): o limiar do passo 9 fica em 10%.

### Passo 3 — imports e pipeline

`python tools/medir_partida.py --imports --pipeline` (Python 3.14 do fonte; 5 vezes cada, a 1ª separada):

| medida | 1ª (s) | mediana das vezes 2 a 5 (s) |
| --- | --- | --- |
| `import_reco` | 1,481 | 1,475 |
| `import_openvino_genai` | 2,608 | 2,460 |
| `import_os_dois` | 2,374 | 2,851 |
| `exe_selftest` (exe congelado, sem janela) | 7,398 | 5,428 |
| `pipeline_gpu` (large-v3-turbo, GPU, 1 vez) | 48,249 | — |

- `exe_selftest` é a partida do Python congelado até sair: é a duração esperada do estado "motor subindo"
  da Fase 1 (≈ 5,4 s; 7,4 s na primeira).
- **Achado:** `pipeline_gpu` levou 48 s (51,96 s com o import), não "alguns segundos". Nenhum arquivo novo no
  cache do OpenVINO (não foi compilação). Condição: o Reco do Gabriel aberto com ~1 GB privado (provável
  modelo carregado), então pode ter havido disputa de GPU ou memória. Repetir no Bloco B com o app fechado.
  Reforça D12: Gravar nunca espera a GPU.

### Passo 4 — checagem de gravação em curso

- Positiva (arquivo preso de propósito em `temp/medicoes/`) → `em curso: trava_teste.mp3`, `codigo 4`.
- Negativa (pasta do Gabriel, 106 MP3, 1 modificado nas últimas 6 h, solto) → `nenhuma gravação em curso`,
  `codigo=0`.

### Passo 5 — propagação

`grep -l "Atualizado em 2026-11-11: ver roadmap/2026-11-11" …` → os 6 roadmaps exatos; maior linha com 197
caracteres.

### Passos 6 a 8 — spike da bandeja no Tauri 2 (veredito: **D2 confirmada**)

- Passo 6: `cargo build --manifest-path C:/Dev/Reco/temp/spike-bandeja/src-tauri/Cargo.toml` → `Finished`,
  exe em `C:\pt\debug\reco-spike-bandeja.exe`. `tauri-plugin-positioner` 2.4.0 baixado (P7 ok); a página sai
  embutida no binário de debug (P4 ok).
- Passo 7, `hover.py --modo tao` → `enter=ok foco_preservado=true fica_com_cursor_dentro=true some_ao_sair=true acima_do_icone=true redimensionou=false visivel_ms=50`
- Passo 8, `hover.py --modo showwindow` → a mesma linha, `visivel_ms=11`.
- **Prova que reprova:** um modo de controle com `show()` comum, sem `focusable(false)`, dá
  `foco_preservado=false` (o spike toma o foreground). O teste vê o roubo de foco quando ele existe.
- Clique que fixa no modo `tao`: `set_focusable(true)` + `set_focus()` dão o foco à janela; com o cursor fora
  ela continua visível.
- Regra do passo 8: `tao` passou → a Fase 3 usa `focusable(false)` com `show()` e `set_focusable(true)` antes
  do clique que fixa. O `ShowWindow(hwnd, 4)` fica de reserva.
- Condição: Windows 11, escala 125%, ícone do spike promovido na barra (ver pegadinha 1); o `hover.py` usa
  `SendInput` porque `SetCursorPos` não gera o `Enter` (P5 caiu).

Pegadinhas do spike (viram entradas de ARMADILHAS no passo 17):

1. Ícone escondido no menu "^" do Windows 11: `TrayIcon::rect()` devolve o rect do botão "^", dentro da barra,
   e `enter=nunca`. Promover por `IsPromoted=1` em `HKCU\Control Panel\NotifyIconSettings\<id>` (só a entrada
   do exe do spike; nasce depois da 1ª execução).
2. `SetCursorPos` não gera o `Enter` do ícone (4 de 4); `SendInput` com `MOVE|ABSOLUTE|VIRTUALDESK` em 12 passos
   de 15 ms gera.
3. `Position::TrayBottomCenter` do positioner põe a janela em cima da barra (conta `y = tray_y`, pensada para o
   macOS); ancorar pelo rect do ícone, como o `reco.py`.
4. O `Leave` do `tray-icon` 0.25.1 nem sempre chega: esconder por polling iniciado no `Enter`.
5. No modo `tao`, o evento `Focused(true)` chega sem a janela ter foco de verdade: não basear lógica nele.
6. No modo `showwindow`, o tao perde a conta da visibilidade (marca `VISIBLE` dessincronizada): `hide()` e
   `set_focus()` viram nada (lido no código, não provado rodando).
7. Janela padrão rouba o foco ao nascer mesmo escondida: `focused(false)` na criação.
8. `windows-sys` 0.59 precisa da feature `Win32_Security` para `CreateMutexW` (E0432).
9. Janela sem moldura tem borda invisível: `GetWindowRect` 443×285 contra 425×275 úteis (340×220 × 1,25).
10. O primeiro show emite um `Resized` com o tamanho nominal; "redimensionou" é mais de um tamanho distinto.

Efeito colateral na máquina: `IsPromoted=1` só na entrada do exe do spike (desfazer = apagar a subchave
`HKCU\Control Panel\NotifyIconSettings\15959779321739684602`). O Reco do Gabriel (pid 36616) não foi tocado; o
foco da janela ativa dele saiu 4 vezes por um instante nas rodadas de controle.

Verificação manual que fica: digitar num campo real com o mouse de verdade passando sobre o ícone (a P5 caiu,
então o hover físico não foi exercitado). `mutex.py` (passo 13) escrito, não rodado.

## Bloco B — com o Reco do Gabriel fechado (11/11, 23:18 a 23:49, retomado depois da queda das 23:30)

Condição comum a todos os números deste bloco: exe `dist/Reco/Reco.exe` de hoje, uma instância de teste por
vez, aberta com `HF_HUB_OFFLINE=1` só no ambiente do `Popen` (**checagem de modelo desligada**); config
`live=false`, `device=AUTO`, `mp3_bitrate=64`; **escala de DPI 125%** (`GetDpiForSystem` = 120); CPU total da
máquina entre 3% e 23% antes de cada medição (soma do `Get-Process` em 5 s, 14 núcleos; nos levantamentos
por processo, nenhum acima de 3,1%). O app do Gabriel está fechado desde ~23:18 (ele deu o Sair pela bandeja); marca
do bloco em `temp/medicoes/bloco-b-inicio.txt` (23:27:41).

### Passo 9 — app fechado e reservas

- A 1ª chamada (`--esperar-fechado`) não rodou nesta sessão: o Gabriel já tinha dado o Sair antes. A 2ª
  (`--esperar-fechado --so-esperar`) saiu `Reco não está aberto`, código 2, e o `tasklist` não lista
  `Reco.exe`. **Desvio:** a saída literal `fechado pid N em <s> s` não existe porque o processo já tinha
  sumido antes da chamada.
- Reserva dos modelos (feita às 23:27 pela execução interrompida, conferida agora): origem e
  `temp/medicoes/models-reserva` com **828.097.157 bytes** e 46 arquivos cada; só
  `whisper-large-v3-turbo-int8-ov`.
- Config: `cmp ~/.reco_config.json temp/medicoes/reco_config.antes.json` → igual (a cópia de 23:27 não foi
  sobrescrita). Lista da pasta de saída guardada em `temp/medicoes/pasta_antes.txt` (213 entradas).

### Passo 10 — descobrir os botões

`python tools/medir_partida.py --descobrir` → `janela=TkTopLevel botoes_visiveis=1 gravar=20,160,123,45` e
`processo de teste 8760 encerrado`. A P1 vale: o `tk.Button` é um `BUTTON` nativo. O retângulo sai antes de
o Tk centralizar a janela; na rodada o centro do Gravar fica em 1152,441.

### Passo 11 — 3 rodadas sem som (23:36:58 a 23:39:15)

**As 3 rodadas de 23:28 foram descartadas** (movidas para `temp/medicoes/partida-descartada.jsonl`): todas
recusaram o clique com `ponto 1152,441 coberto por outra janela`. O código que rodou já levava a janela de
teste a `HWND_TOPMOST`; então quem cobria o ponto estava numa faixa acima do topmost comum ou também era
topmost (janelas de outras conversas na tela). Na retomada o ponto era da janela de teste antes e depois
do topmost (diagnóstico com `WindowFromPoint` + `GetAncestor`). Correção sem afrouxar a guarda
(`tools/medir_partida_win.py`): o clique continua recusado se o ponto não for do pid de teste; antes de
recusar, (1) põe só a janela de teste em topmost, (2) leva só ela aos cantos da área útil e relê o botão, e
(3) a recusa agora diz quem cobre (classe, processo, pid, topmost, retângulo; sem título). Cada linha do
jsonl ganhou `clique_via` e `parar_via` (`direto|topmost|movida`). Dados das 3 descartadas, só como
referência: `abrir_pronta_s` 1,855 / 1,756 / 1,527 e `ram_repouso_mb` 113,1 / 112,6 / 112,9.

`python tools/medir_partida.py --rodadas 3 --segundos 35` → 3 linhas, código 0, `trava_detectada=true` nas 3,
MP3 movidos para `temp/medicoes/`. Cliques: Gravar `direto, topmost, direto`; Parar `topmost, direto,
direto`.

| medida (sem som) | 1ª rodada | mediana das 3 | faixa |
| --- | --- | --- | --- |
| `abrir_visivel_s` | 0,647 | 0,639 | 0,510–0,647 |
| `abrir_pronta_s` (alfa 255) | 1,330 | 1,515 | 1,330–1,718 |
| `ram_repouso_mb` (5 s depois de pronta) | 115,2 | 113,0 | 113,0–115,2 |
| `clique_ui_gravando_s` | 0,250 | 0,250 | 0,250 |
| `clique_arquivo_criado_s` | 20,772 | 20,734 | 20,704–20,772 |
| `clique_mp3_cresce_s` | `null` | `null` | `null` nas 3 (`nao_cresceu_em_s=35`) |
| `ram_gravando_mb` (a 33 s) | 246,3 | 246,4 | 246,3–247,0 |
| `parar_arquivo_fechado_s` | 0,504 | 0,503 | 0,503–0,504 |
| `parar_ui_parado_s` | 0,504 | 0,503 | 0,503–0,504 |

- A "1ª rodada" não é a primeira partida depois do Sair: o `--descobrir`, o diagnóstico do clique e as 3
  rodadas descartadas já tinham aberto o exe antes (P3: cache de disco quente).
- `clique_ui_gravando_s = 0,25` é o piso do método: o `clicar` espera 250 ms antes de devolver o cursor.
  O número real é "≤ 0,25 s".
- `parar_*` de 0,50 s também está no passo de amostragem (50 ms) somado ao mesmo atraso; leia "≤ 0,5 s".

**Achado 1 — o MP3 não nasce no `start()`.** O PyAV só cria o arquivo no disco no primeiro pacote gravado
(provado à parte: `av.open(caminho, "w")` + `add_stream` não cria o arquivo; nem o `close()` sem pacote cria).
Sem eco, o `_pump` só solta o áudio quando desiste de alinhar (`ALIGN_DESISTE_S = 20`), então o arquivo
aparece a ~20,7 s do clique. Isso contradiz o comentário de `reco.py:1660-1662` e a regra 3 do `CLAUDE.md` ("o
arquivo nasce no `start()`"). Consequências:
- a checagem de gravação em curso do passo 4 (e do passo 9) é **cega nos primeiros ~11 a 21 s** de uma
  gravação: não há arquivo para estar preso. A F0-D7 continua segura porque o Sair salva antes de sair
  (`reco.py:5088-5111`), mas a premissa "a trava cobre a retenção" (passo 4) caiu;
- um crash nos primeiros ~20 s não deixa MP3 parcial.
Nenhuma mudança no `reco.py` nesta fase (fora do escopo); vai para as Fases 2 e 5 e para a ARMADILHAS no
passo 17.

**Achado 2 — sem som, o MP3 não cresce depois de nascer.** Com o loopback mudo, o pareamento não avança
(relatório 6 § 1.3): o arquivo recebe o bloco de ~20 s de uma vez e não cresce mais até o Parar.

### Passo 12 — com som tocando (`--tocar`)

Rodadas válidas, `python tools/medir_partida.py --rodadas 2 --segundos 35 --tocar` às 23:46:52 (CPU 2,8%),
`tocou=true` nas 2:

| medida (ruído −6 dBFS nos primeiros 15 s) | rodada 1 | rodada 2 |
| --- | --- | --- |
| `abrir_pronta_s` | 1,548 | 1,579 |
| `ram_repouso_mb` | 114,7 | 114,8 |
| `clique_ui_gravando_s` | 0,251 | 0,250 |
| `clique_arquivo_criado_s` | 11,195 | 20,740 |
| `clique_mp3_cresce_s` | 33,480 | 31,390 |
| `ram_gravando_mb` | 226,0 | 317,1 |
| `parar_arquivo_fechado_s` | 0,453 | 0,453 |
| `parar_ui_parado_s` | 0,503 | 0,504 |

- **Prova literal não fecha** (`clique_mp3_cresce_s` entre 9 e 14 s): pelo Achado 1, o número que o md quer
  ("o áudio chega ao disco") é o `clique_arquivo_criado_s`. Ele dá **11,0–11,2 s quando o eco foi detectado**
  (dentro de 9–14 s; 2 de 5 rodadas com som) e 20,7 s quando não foi (o eco não chegou ao mic). O
  `clique_mp3_cresce_s` de 26–33 s mede o buffer de escrita do FFmpeg (o arquivo cresce em blocos), não o
  alinhamento. Passo 12 fica `[ ]` com esta nota: o md precisa trocar a chave da prova.
- `ram_gravando_mb` é maior quando o alinhamento desistiu (317 MB) do que quando fechou em 10 s (226 MB).
- Outras rodadas com som, guardadas no `partida.jsonl` e fora da tabela:
  - 23:40, rodada 1 (`tocou=true`): pronta 1,557 s, arquivo a 11,029 s, `cresce=null`, RAM 228,2 MB, parar
    0,302 s. Rodada 2: `tocou=false` (`Error 0x800401f0`, COM não iniciado na thread nova).
  - 23:42, as 2: `tocou=false` (`Error 0x100000001`, efeito da primeira tentativa de correção). Corrigido em
    `medir_partida_rodada.py`: o `soundcard` é importado na thread principal e cada thread entra no MTA.
  - 23:44, rodada 1: pronta 1,893 s, arquivo 20,719 s, cresce 30,058 s, RAM 316,3 MB, parar 0,302 s.
    Rodada 2: **o clique em Parar não pegou** (`parar_*=null` em 30 s; o MP3 de teste cresceu até 512 KiB e
    a instância foi encerrada gravando). Causa não achada; o clique foi `direto` (o ponto era do pid de
    teste). Não se repetiu nas 6 rodadas seguintes.

### Passo 13 — exclusão mútua spike × Reco (D7, F0-D5)

`python temp/spike-bandeja/mutex.py` às 23:48:33, sem nenhum `Reco.exe` nem casco da Fase 3 aberto →
`spike_primeiro: reco_saiu_em_ms=445 reco_vivos=0` e `reco_primeiro: spike_saiu_em_ms=20
mutex_existente_no_log=true`, código 0. A D7 vale nos dois sentidos com o `CreateMutexW` feito à mão.

### Passo 3 repetido — imports e pipeline com o app fechado

`python tools/medir_partida.py --imports --pipeline`, duas vezes (23:48:51 com CPU 14,9%; 23:49:23 com
CPU 23,4%):

| medida | Bloco A, app aberto (1ª / mediana) | Bloco B, 1ª execução | Bloco B, 2ª execução |
| --- | --- | --- | --- |
| `import_reco` | 1,481 / 1,475 | 0,371 / 0,351 | 0,325 / 0,313 |
| `import_openvino_genai` | 2,608 / 2,460 | 0,887 / 0,689 | 0,632 / 0,672 |
| `import_os_dois` | 2,374 / 2,851 | 0,759 / 0,671 | 0,829 / 0,746 |
| `exe_selftest` | 7,398 / 5,428 | 1,065 / 1,087 | 1,348 / 0,960 |
| `pipeline_gpu` (large-v3-turbo, GPU, 1 vez) | 48,249 | **3,260** | **1,583** |

- Com o app fechado tudo cai de 4 a 30 vezes. O app do Gabriel parado usava 0,9% de CPU, o que não explica
  os imports 4× mais lentos; a carga da máquina às 21:20 não foi registrada no Bloco A. Leitura mais
  provável: a máquina estava carregada no Bloco A (outras frentes compilando), e o `pipeline_gpu` ainda
  disputou a GPU com o modelo carregado no app dele (~1 GB privado). **A régua para as Fases 1, 2 e 4 passa a
  ser a do Bloco B**, com a do Bloco A como pior caso medido.
- `exe_selftest` (piso do motor congelado, estado "motor subindo" da Fase 1): ~1,0 s com a máquina folgada,
  5,4 s com ela carregada.

### Passo 14 — conferências feitas, reabertura adiada

Às 23:49, sem nenhum `Reco.exe` nem `reco-spike-bandeja.exe` aberto:
- `models`: só `whisper-large-v3-turbo-int8-ov`, nada `.old`, soma **828.097.157** (igual à do passo 9);
- config: `cmp` com `reco_config.antes.json` → igual (nada a repor);
- pasta de saída: lista igual à de `pasta_antes.txt` (nenhum MP3 de teste; os MP3 das rodadas estão em
  `temp/medicoes/`, 11 ao todo); `--checar-gravando` → `nenhuma gravação em curso`, código 0.
- **O Reco do Gabriel NÃO foi reaberto** nesta etapa: as próximas etapas precisam dele fechado. A reabertura
  (`Start-Process`, `--ram-viva` com pid novo) e a remoção de `temp/medicoes/models-reserva` ficam para a
  última etapa. Passo 14 fica `[ ]` até lá.

## Desvios do md (Bloco A)

- `medir_partida` saiu em 3 arquivos (`medir_partida.py` 267 linhas, `medir_partida_rodada.py` 265,
  `medir_partida_win.py` 261) para caber na trava de 500 linhas; ruff e complexidade verdes nos três.
- Códigos de saída novos: 6 (`ocupado: cpu=N%`) e 7 (medição falhou). Opções novas: `--limiar-cpu`,
  `--limite-min`. `mp3_movido` virou lista.
- Processos de teste são encerrados por `proc.kill()` do próprio `Popen` (sem risco de pid reaproveitado).
- Uma edição foi feita por substituição de texto via Python (contra a regra da casa); conferida linha a linha.

### Decisões técnicas — Fase 0

- **A Fase 1 começa com este relatório parcial.** Ela só precisa do `exe_selftest` (estado "motor subindo"),
  já medido; `abrir_pronta_s` é régua da D12 para a Fase 4 e chega com o Bloco B. Confiança alta; reverteria
  se o Bloco B mudasse alguma premissa de desenho (não há nenhuma prevista).

## Pendências e decisões pendentes

- ~~Bloco B: o Gabriel fecha o Reco pela bandeja~~ feito (~23:18 de 11/11).
- Passo 14: reabrir o Reco do Gabriel (`Start-Process`), `--ram-viva` com pid novo e só então apagar
  `temp/medicoes/models-reserva`. Fica para a última etapa do lote. `dono: agente`.
- Passo 12: o md da fase precisa trocar a chave da prova (`clique_mp3_cresce_s` → `clique_arquivo_criado_s`),
  pelo Achado 1. `dono: agente` (quem fecha a fase).
- Achado 1 (o MP3 nasce no 1º pacote, não no `start()`): entrada na ARMADILHAS no passo 17; o comentário de
  `reco.py:1660-1662` e a regra 3 do `CLAUDE.md` ficam para quem mexer no `reco.py` (fora desta fase).
