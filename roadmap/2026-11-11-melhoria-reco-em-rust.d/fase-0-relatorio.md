## Relatório de execução — Fase 0 (2026-11-11, sessão 4c65eb01)

> **Parcial:** Bloco A feito; spike da bandeja (passos 6 a 8) em andamento; Bloco B (passos 9 a 14) espera o
> Gabriel fechar o Reco pela bandeja. Este arquivo cresce até o fecho da fase.

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

- Bloco B (passos 9 a 14): o Gabriel fecha o Reco pela bandeja (Sair), fora de chamada. `dono: gabriel`.
