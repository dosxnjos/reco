# Reco em Rust: Fase 0 — Medir o hoje e provar o que é barato provar

> Índice: [2026-11-11-melhoria-reco-em-rust.md](2026-11-11-melhoria-reco-em-rust.md) · anterior: — · seguinte: [fase-1](2026-11-11-melhoria-reco-em-rust-fase-1.md) (a [fase-2](2026-11-11-melhoria-reco-em-rust-fase-2.md) anda em paralelo) · Base: Reco `7c5c1a1` (2026-11-11)

## Por que esta fase

- O Gabriel pediu um Reco "rápido", mas ninguém mediu quanto o app de hoje leva para abrir, começar a gravar e salvar.
- Sem esses números, a Fase 4 não tem régua para dizer se o app novo ficou mais rápido.
- A bandeja de hoje mostra a janela no hover sem roubar o foco. Ninguém provou que o Tauri 2 faz isso, e a D2 depende disso.
- A Fase 2 precisa saber quanto o motor Python leva para subir antes de prometer "Gravar na hora".
- Esta fase mede o hoje e prova a bandeja num spike descartável. Não muda o app que o Gabriel usa.

## O que ler antes

- `C:\Dev\Reco\roadmap\2026-11-11-melhoria-reco-em-rust.md` (índice: D1–D12, O que NÃO fazer, § Riscos; a D12 usa os números desta fase como régua de "rápido").
- `C:\Dev\cerebro\projetos\reco.md` (hub; o hook `guarda-escrita` cobra) e `C:\Dev\Reco\CLAUDE.md`.
- `C:\Dev\Reco\docs\ARMADILHAS.md` (gerada; inteira), em especial a tabela de custo da GPU por processo (linhas 758-764).
- Evidência: `C:\Dev\Reco\roadmap\2026-11-11-melhoria-reco-em-rust.d\diagnostico\`
  - `1-mapa-do-reco-atual.md` (§ 1 funções, § 3 por que pula, § 6 build);
  - `3-lacre-como-molde.md` (§ 4 armadilhas, § 5 o que falta: bandeja e instância única);
  - `6-critica-de-completude.md` (§ 2 "ninguém mediu", § 4.3 e 4.4 mutex e bandeja, § 1.3 loopback mudo).
- Código que os passos supõem (todos lidos para escrever esta fase):
  - `C:\Dev\Reco\reco.py`: 98-102, 210-215, 569, 738-830, 1491-1492, 1611-1698, 1742-1781, 1854-1880, 1959-2011, 2054-2083, 2853-2941, 3025-3029, 3089-3110, 3218-3270, 3565-3600, 3746-3812, 3933-3990, 4914-5060, 5079-5112, 5130-5213;
  - `C:\Dev\Reco\tray.py`: 1-40, 100-200, 300-329;
  - `C:\Dev\Reco\tools\test_gravacao_alinhada.py:79-85` (tocar áudio pelo alto-falante) e `tools/test_gravacao_real.py`;
  - `C:\Dev\albion\guarita\app\src-tauri\Cargo.toml` e `src\lib.rs:355-411` (bandeja e plugin de instância única);
  - no cache do cargo (`%USERPROFILE%\.cargo\registry\src\index.crates.io-*\`):
    - `tray-icon-0.25.1/src/lib.rs:636-665` e `.../platform_impl/windows/mod.rs:478-529`;
    - `tauri-2.12.5/src/window/mod.rs:887-894,1765,1982` e `tauri-2.12.5/src/tray/mod.rs:620`;
    - `tao-0.37.2/src/platform_impl/windows/window_state.rs:293-295,457-468` e `.../windows/window.rs:1263-1265,1415-1420`;
    - `tauri-plugin-single-instance-2.5.5/src/platform_impl/windows.rs:90-93`.

## Fase 0 — Medir o hoje e provar o que é barato provar

**Critério de aceite:**

1. Quem lê o relatório da fase encontra, em segundos e megabytes, quanto o Reco de hoje leva para abrir, mostrar que está gravando, começar a gravar de fato no disco e salvar, e quanta memória usa parado e gravando, com a condição de cada número (com ou sem som tocando).
   - Se a fase falhar: o relatório tem número estimado, campo vazio sem explicação ou número sem a condição em que foi medido.
2. Um app de teste em Tauri mostra uma janelinha sem moldura, de tamanho fixo, logo acima do ícone da bandeja quando o mouse passa por cima.
   Ela aparece sem tirar o cursor do texto que se estava digitando e some quando o mouse sai. O mesmo app se recusa a abrir junto com o Reco de hoje, e vice-versa.
   - Se a fase falhar: a janela de onde se digitava perde o foco, a janelinha nasce no meio da tela, muda de tamanho, ou os dois apps ficam abertos ao mesmo tempo. O relatório diz se a escolha do Tauri para a interface ficou confirmada ou reaberta.
3. Ao fim, o Reco do Gabriel está aberto de novo, nenhuma gravação dele se perdeu, e as gravações de teste não aparecem na biblioteca dele.
   - Se a fase falhar: o ícone do Reco some da bandeja depois da fase, ou a lista de gravações dele ganha arquivos de teste.

**Ordem:** o Bloco A roda com o app do Gabriel aberto e não fecha nada. O Bloco B é a única janela em que o app dele fica fechado, e termina reabrindo. O Bloco C registra.

### Bloco A — com o Reco do Gabriel aberto

1. [ ] Conferir o frescor: nada mudou no código citado desde a base — **prova:** `git -C C:/Dev/Reco log --oneline 7c5c1a1..HEAD -- reco.py tray.py tools/` → saída vazia
   **reprova se:** aparece commit. Aí reler as linhas citadas acima com `sed -n` e corrigir os números deste md antes de seguir.
2. [ ] Criar `tools/medir_partida.py` com o modo `--ram-viva` (memória do Reco aberto, só leitura) — **prova:** `python C:/Dev/Reco/tools/medir_partida.py --ram-viva` → uma linha JSON `{"pid": N, "ws_mb": X, "privado_mb": Y, "cpu_pct": Z}` com X entre 50 e 3000
   **reprova se:** imprime "Reco não está aberto" com o app aberto, ou `ws_mb` sai 0 (a chamada de memória falhou).
   - Só `ctypes` e stdlib (F0-D1): `psutil`, `pywinauto` e `uiautomation` não estão instalados nesta máquina (conferido em 11/11).
   - Achar o pid: `tasklist /FI "IMAGENAME eq Reco.exe" /FO CSV /NH`. Memória: `psapi.GetProcessMemoryInfo` com `PROCESS_MEMORY_COUNTERS_EX` (`WorkingSetSize`, `PrivateUsage`), em MB.
   - Referência de sanidade: o `tasklist` mostrou 190 MB para o Reco aberto às 19:14 de 11/11 (exe em `C:\Dev\Reco\dist\Reco\Reco.exe`).
   - Este número é a "RAM em repouso de verdade" (app aberto há horas). Guardar a saída para o relatório.
   - A linha também traz `cpu_pct`: CPU do processo em 5 s por `GetProcessTimes`, a mesma conta do passo 9. Se o app parado passar de 5%, o limiar do passo 9 vira o dobro do medido, registrado no relatório.
   - Trava do pre-commit: arquivo novo até 500 linhas e funções curtas (complexidade ≤ 10, ramos ≤ 12, comandos ≤ 50, `tools/tamanho.json`). Cada modo é uma função; nada entra no `reco.py`.
3. [ ] Acrescentar o modo `--imports [--pipeline]`: tempo de processos que só importam — **prova:** `python C:/Dev/Reco/tools/medir_partida.py --imports --pipeline` → JSON com as 5 chaves da lista abaixo, cada uma com `primeira_s` e `mediana_s` > 0
   **reprova se:** falta chave, ou o Reco do Gabriel muda de estado durante a prova (sinal de que algo pegou o mutex ou abriu janela).
   - Cada medida roda 5 vezes num processo novo (`subprocess`, `cwd=C:\Dev\Reco`); a primeira sai separada da mediana.
   - `import_reco`: `python -c "import reco"`. O `reco` importa `tkinter`, numpy, soundcard e `tray` no topo (`reco.py:17`, `523-547`), mas só procura o `openvino_genai` (`reco.py:569`); importar não grava o config (`reco.py:210-215`).
   - `import_openvino_genai`: `python -c "import openvino_genai"` (o import de verdade é preguiçoso, `reco.py:2062`). `import_os_dois`: os dois juntos.
   - `exe_selftest`: `dist/Reco/Reco.exe --selftest`. Mede a partida do Python congelado sem janela; sai antes do mutex (`reco.py:5131-5146`, comentário em `5198-5200`) e grava `%TEMP%\reco_selftest.txt`.
   - `pipeline_gpu` (só com `--pipeline`, 1 vez): `reco.make_transcriber()`, `set_model(<model do config>)`, `set_device("GPU")` e `tr._pipeline(None)` (`reco.py:2054-2083`). Custa ~1,35 GB de GPU por alguns segundos (ARMADILHAS, tabela da GPU).
   - Esses números estimam a partida do motor da Fase 2: `import_reco` + `pipeline_gpu` é o "motor quente"; `exe_selftest` é o piso do motor congelado.
4. [ ] Acrescentar o modo `--checar-gravando [--pasta DIR]`: diz se há gravação em curso pela trava do arquivo — **prova (positiva, com um arquivo preso de propósito):** o comando abaixo (Git Bash) → `em curso: trava_teste.mp3` e `codigo 4`
   `mkdir -p C:/Dev/Reco/temp/medicoes && python -c "import subprocess,sys; f=open('C:/Dev/Reco/temp/medicoes/trava_teste.mp3','ab'); r=subprocess.run([sys.executable,'C:/Dev/Reco/tools/medir_partida.py','--checar-gravando','--pasta','C:/Dev/Reco/temp/medicoes']); print('codigo', r.returncode)"`
   **reprova se:** sai `codigo 0` com o arquivo preso (a checagem não vê trava nenhuma e o passo 9 pediria o Sair no meio de uma gravação).
   - **prova (negativa, na pasta do Gabriel):** `python C:/Dev/Reco/tools/medir_partida.py --checar-gravando; echo "codigo=$?"` → `pasta=<pasta de saída dele>`, `nenhuma gravação em curso` e `codigo=0` (o Gabriel não está gravando)
   - **reprova se:** acusa "em curso" sem o Gabriel estar gravando, ou a `pasta=` impressa não é a dele. Aí a premissa da trava está errada: parar e reportar, porque o Bloco B depende dela.
   - Pasta de saída: ler `~/.reco_config.json` só como JSON (`cfg.get("output_dir") or ~/Documents/Reco`: hoje a chave existe com valor `null`), como o `reco.py:98-102`. Não importar o `reco` aqui. Apagar `temp/medicoes/trava_teste.mp3` depois da prova.
   - Para cada `*.mp3` da pasta modificado nas últimas 6 h, tentar `CreateFileW(caminho, GENERIC_READ, 0, None, OPEN_EXISTING, 0, None)`.
   - Falha com erro 32 (`ERROR_SHARING_VIOLATION`) = o app segura o arquivo aberto = gravação em curso (código 4). Isso cobre os 10 a 20 s de retenção (o arquivo nasce no `start()`, `reco.py:1660-1665`, `1689-1698`) e a pausa.
   - O handle de teste fecha na hora; nunca segurar o arquivo.
5. [ ] Propagar o índice aos 6 roadmaps em voo (§ Riscos): linha datada sob o título, por `Edit` ancorado — **prova:** `grep -l "Atualizado em 2026-11-11: ver roadmap/2026-11-11" C:/Dev/Reco/roadmap/2026-0*.md C:/Dev/Reco/roadmap/2026-10-*.md` → exatamente os 6 nomes abaixo
   **reprova se:** falta algum dos 6, ou aparece um sétimo arquivo (linha no roadmap errado).
   - `2026-10-02-melhoria-modularizacao.md`: `> Atualizado em 2026-11-11: ver roadmap/2026-11-11-melhoria-reco-em-rust.md (efeito: superado; o reco.py não será cortado nas 4 fases, a lista de fronteiras vira o mapa do engine/ na Fase 2).`
   - `2026-08-21-salto-de-alinhamento-sob-carga.md`: `... (efeito: a Fase 5, captura em Rust, absorve o que falta; A1 e A1b no Python continuam valendo se alguém executar antes).`
   - `2026-09-30-melhoria-dispositivo-auto.md`: `... (efeito: a Fase 2 do vigia de zero vira especificação da Fase 5; o que já está no reco.py segue valendo).`
   - `2026-08-13-melhoria-modo-nota-speech-to-ia.md`: `... (efeito: as Fases 2 e 3, botão e fluxo do modo nota, ficam absorvidas pela Fase 3 do Reco em Rust).`
   - `2026-07-29-melhoria-transcricao-ao-vivo-vad-diarizacao.md`: `... (efeito: o teste de 20 min, passo 3.6, reabre na Fase 5 com a captura nova; até lá segue estacionado).`
   - `2026-08-19-melhoria-antieco-de-verdade.md`: `... (efeito: nenhum na ordem; segue independente, e o medir_aec continua sendo a régua do gate da Fase 5, D8).`
   - Os `...` acima são o mesmo prefixo da primeira linha. Nenhuma linha passa de 300 caracteres.
6. [ ] Montar o spike descartável `temp/spike-bandeja/` (fora do git) e compilar — **prova:** `cargo build --manifest-path C:/Dev/Reco/temp/spike-bandeja/src-tauri/Cargo.toml` → termina com `Finished` e existe `C:\pt\debug\reco-spike-bandeja.exe`
   **reprova se:** erro de resolução de crate (o `tauri-plugin-positioner` não está no cache do cargo e precisa de rede) ou o exe não aparece em `C:\pt\debug\`.
   - `temp/` está no `.gitignore` (`.gitignore:25`, conferido com `git check-ignore -v`). `CARGO_TARGET_DIR` é `C:\pt`, compartilhado com Lacre e Guarita: o crate se chama `reco-spike-bandeja` para não colidir.
   - Não há `cargo tauri` instalado: build e execução por `cargo` puro. Sem `devUrl`, o `frontendDist` estático entra embutido (premissa P4).
   - `src-tauri/Cargo.toml`:
     - `tauri = { version = "2", features = ["tray-icon"] }` (o cache tem 2.12.5) e `tauri-build = "2"`;
     - `tauri-plugin-positioner = { version = "2", features = ["tray-icon"] }`;
     - `windows-sys = "0.59"` (está no cache) com `Win32_Foundation`, `Win32_System_Threading` e `Win32_UI_WindowsAndMessaging`.
   - `tauri.conf.json`: `identifier` próprio do spike, `build.frontendDist = "../ui"`, `app.windows = []` (a janela nasce no código), `bundle.active = false`.
   - `icons/icon.ico`: cópia de `C:\Dev\Reco\logo\tray_idle.ico`. `ui/index.html`: um parágrafo que alterna entre texto curto e longo a cada 500 ms (prova de tamanho fixo).
   - `src/main.rs` (até ~250 linhas), comportamentos:
     - Mutex: sem a variável `SPIKE_SEM_MUTEX=1`, chama `CreateMutexW(null, 0, "Local\\Reco.SingleInstance")`. Se `GetLastError() == 183`, faz `PostMessageW(HWND_BROADCAST, RegisterWindowMessageW("Reco.Show"))`, registra `mutex_existente` no log e sai. É a cópia do `reco.py:5201-5211`.
     - O plugin `tauri-plugin-single-instance` não serve para a D7: ele cria o mutex `"{identifier}-sim"` (`windows.rs:90`), nunca o nome do Reco (F0-D5).
     - Janela `painel`: `decorations(false)`, `resizable(false)`, `inner_size(340.0, 220.0)`, `skip_taskbar(true)`, `always_on_top(true)`, `visible(false)`. O modo vem da variável `SPIKE_MODO`:
       - `tao`: `focused(false)` mais `focusable(false)` e `show()`. Quem segura o foco nos shows do hover é o `focusable(false)`, que põe `WS_EX_NOACTIVATE` (`window_state.rs:293-295`).
       - O `focused(false)` só vale para a criação: o tao tira a marca `MARKER_DONT_FOCUS` logo depois de criar a janela (`window.rs:1415-1420`), então os `show()` seguintes usam `SW_SHOW`, não o `SW_SHOWNOACTIVATE` de `window_state.rs:457-468`.
       - `showwindow`: `show()` não é chamado; usa `ShowWindow(hwnd, 4)` pelo `hwnd()` (`window/mod.rs:1765`), como o `tray.py:327-329`.
     - Bandeja: `TrayIconBuilder` com `show_menu_on_left_click(false)` (molde: Guarita `lib.rs:355-396`, que só trata `Click` e sempre chama `set_focus`). No `on_tray_icon_event`, primeiro `tauri_plugin_positioner::on_tray_event(app, &ev)`.
       - `Enter`: guardar `GetForegroundWindow()`, mostrar pelo modo e `move_window(Position::TrayBottomCenter)`. Se cair longe do ícone, usar o `rect` do evento como o `reco.py:4980-4997`. Após 300 ms, logar `foco_preservado=<igual?>`.
       - `Leave`: polling de 120 ms do cursor contra janela ∪ ícone, como o `reco.py:5024-5045`. Fora dos dois, esconde.
       - `Click` esquerdo: mostrar e `set_focus()` (fixa, como o `reco.py:4999-5009`). No modo `tao`, chamar antes `set_focusable(true)` (`window/mod.rs:1982`) e voltar a `false` ao esconder; sem isso a janela não aceita o foco.
     - `Enter` e `Leave` existem no Windows no `tray-icon` 0.25.1 (`lib.rs:641-665`, `windows/mod.rs:478-529`); `TrayIcon::rect()` em `tray/mod.rs:620`.
     - Log em arquivo `temp/spike-bandeja/spike.log`, com hora em ms, porque o `eprintln!` some com `windows_subsystem` (armadilha do Lacre, relatório 3 § 1). Na partida loga `icone_rect=x,y,w,h` e `escala=<scale_factor>`. Loga todo `WindowEvent::Resized`/`Moved` depois do primeiro show.
7. [ ] Provar a bandeja no modo `tao`, com o Reco do Gabriel aberto (`SPIKE_SEM_MUTEX=1`) — **prova:** `python C:/Dev/Reco/temp/spike-bandeja/hover.py --modo tao` → uma linha com os 7 campos da lista abaixo, todos no valor bom
   **reprova se:** qualquer campo sai `false`, `enter=nunca` (o evento não chegou) ou `redimensionou=true`.
   - Campos: `enter=ok`, `foco_preservado=true`, `fica_com_cursor_dentro=true`, `some_ao_sair=true`, `acima_do_icone=true`, `redimensionou=false`, `visivel_ms=<N>`.
   - `hover.py` (descartável, fora do git, só `ctypes`) abre o exe do spike com `SPIKE_MODO` e `SPIKE_SEM_MUTEX=1` e lê `icone_rect` no `spike.log`.
   - Depois guarda o `GetForegroundWindow()` (o terminal) e leva o cursor ao centro do ícone com `SetCursorPos`. Espera a janela `painel` ficar visível (até 2 s) e confere se o foreground não mudou.
   - Leva o cursor para dentro da janela e espera 1,5 s: tem de continuar visível. Leva o cursor para longe: tem de esconder em até 1 s.
   - `acima_do_icone`: a borda de baixo da janela fica acima do topo do ícone, com sobreposição horizontal. `redimensionou`: há `Resized` no log com o texto da página alternando.
   - Pré-requisito manual: no Windows 11, ícone novo nasce escondido no menu de ícones ocultos. Se `icone_rect` cair fora da barra de tarefas, fixar o ícone do spike em Configurações > Personalização > Barra de tarefas > Outros ícones da bandeja e rodar de novo.
   - Se o `SetCursorPos` não gerar o `Enter` (premissa P5), passar o mouse à mão e conferir as mesmas linhas no `spike.log`: verificação manual, porque o hover precisa de movimento real do mouse.
8. [ ] Provar a bandeja no modo `showwindow` e decidir a D2 — **prova:** `python C:/Dev/Reco/temp/spike-bandeja/hover.py --modo showwindow` → a mesma linha do passo 7
   **reprova se:** campo `false` ou ausente. Isso não interrompe a fase: o resultado dos dois modos decide a D2 pela regra abaixo.
   - Rodar os dois modos sempre, mesmo que o primeiro passe; anotar `visivel_ms` dos dois.
   - Regra da D2:
     - `tao` passa: D2 confirmada, e a Fase 3 usa `focusable(false)` com `show()` (e `set_focusable(true)` antes do clique que fixa).
     - Só `showwindow` passa: D2 confirmada com remendo, e a Fase 3 usa `ShowWindow(hwnd, 4)` pelo `hwnd()`.
     - Nenhum passa (sem `Enter`, ou foco roubado nos dois): D2 reaberta. Registrar no índice e propor um spike de Slint 1.17 antes da Fase 3; as Fases 1 e 2 não dependem disso.
   - Fechar o spike ao fim (`taskkill /IM reco-spike-bandeja.exe /F`; é processo do spike, não do Gabriel).

### Bloco B — janela com o Reco do Gabriel fechado

9. [ ] Modo `--esperar-fechado`: checar que nada grava, pedir ao Gabriel o Sair pela bandeja e esperar o processo sumir — **prova:** `medir_partida.py --esperar-fechado` → `pode sair`; depois `medir_partida.py --esperar-fechado --so-esperar` → `fechado pid N em <s> s`
   **reprova se:** a 1ª chamada recusa (`gravação em curso: <arquivo>` ou `ocupado: cpu=<N>%`) ou a 2ª estoura (`ainda aberto após 8 min`, código 5). Aí nada se força: o Bloco B fica para quando o Gabriel puder.
   - Duas chamadas, porque a saída de um comando só aparece quando ele termina e o Bash corta em 10 min: a 1ª checa e sai com `pode sair`; o executor pede o Sair; a 2ª só espera (a cada 2 s, até 8 min). Estourou: pedir de novo e repetir a 2ª.
   - O executor **nunca** mata o `Reco.exe` do Gabriel (`taskkill /F` perde uma gravação em curso), como nas Fases 2 e 3. Quem fecha é ele, pelo menu da bandeja → Sair (Pendente, abaixo).
   - A 1ª chamada roda a checagem do passo 4 duas vezes, com 25 s entre elas (mais que `ALIGN_DESISTE_S = 20`, `reco.py:1492`). Só então imprime `pode sair` e termina.
   - Nos mesmos 25 s, mede o tempo de CPU do processo (`kernel32.GetProcessTimes`, núcleo + usuário). Acima de 10% de um núcleo, recusa com `ocupado: cpu=<N>%`: transcrição ou atualização de modelo não seguram o MP3 (P2).
   - A 2ª chamada (`--so-esperar`) consulta o `tasklist` e imprime `fechado pid N em <s> s` quando o processo some. Nenhuma das duas fecha nada.
   - Os comandos completos são `python C:/Dev/Reco/tools/medir_partida.py ...`; a prova acima abrevia o caminho.
   - Por que o executor não fecha sozinho: o X e o `WM_CLOSE` só escondem na bandeja (`reco.py:5079-5086`), e o menu usa `TPM_RETURNCMD` sem tratar `WM_COMMAND` de fora (`tray.py:228-236`, `177-197`).
   - Se uma gravação nascer entre a checagem e o Sair, nada se perde: o Sair salva o MP3 antes de sair (`reco.py:5088-5111`, "Salvando antes de sair…"), e a espera só termina quando o processo some.
   - Anotar a hora: o app do Gabriel fica fechado do passo 9 ao 14.
   - Com o app fechado e antes do passo 10, guardar uma reserva dos modelos (as instâncias de teste podem trocar o modelo de ~790 MB, `reco.py:1230-1260`), como o passo 2 da Fase 4. **prova:** a soma do sub-item seguinte, igual na origem e na reserva
     **reprova se:** o `robocopy` sai com código 8 ou mais, ou as duas somas diferem. Aí não seguir para o passo 10.
     - Copiar (PowerShell): `robocopy "$env:LOCALAPPDATA\Reco\models" C:\Dev\Reco\temp\medicoes\models-reserva /E /NFL /NDL` (código < 8 = ok). Fica em `temp/`, ignorado pelo git, longe da `Reco-reserva` da Fase 4.
     - Somar (PowerShell): `(Get-ChildItem -Recurse <pasta> | Measure-Object Length -Sum).Sum` nas duas pastas; anotar o valor para o passo 14.
10. [ ] Acrescentar o modo `--descobrir` e conferir como achar os botões da janela Tk de fora — **prova:** `python C:/Dev/Reco/tools/medir_partida.py --descobrir` → `janela=TkTopLevel botoes_visiveis=1 gravar=<x,y,w,h>` e o processo de teste encerrado no fim
    **reprova se:** `botoes_visiveis=0`, ou seja, o Tk não cria um HWND por botão. Aí reverter a F0-D2 para o caminho do menu da bandeja e reescrever o passo 11.
    - Toda instância de teste dos passos 10 a 13 (aqui, no passo 11 e no `mutex.py` do 13) abre com `HF_HUB_OFFLINE=1` só no ambiente do `Popen` (P8): a checagem de modelo novo falha calada e não troca a pasta. Nunca na máquina toda, nem na reabertura do passo 14.
    - Abre `dist/Reco/Reco.exe` e acha a janela por `EnumWindows` (classe `TkTopLevel`, título `Reco`, `reco.py:33`, mesmo pid, visível).
    - Lista os filhos com `EnumChildWindows` (classe `Button`, visíveis, ordenados da esquerda para a direita).
    - Em repouso, o único `tk.Button` visível é Gravar (`reco.py:3573-3575`); os botões de janela são `tk.Label` (`reco.py:2998-3005`). Premissa P1: o `tk.Button` do Tk 8.6 no Windows é um controle nativo `BUTTON`.
    - Encerra o processo de teste com `taskkill /PID N /F` (só o pid que ele abriu).
11. [ ] Implementar a rodada de medição e rodar 3 vezes sem som tocando — **prova:** `python C:/Dev/Reco/tools/medir_partida.py --rodadas 3 --segundos 35` → 3 linhas JSON com as chaves da lista abaixo, `trava_detectada=true` em todas e a nota `mp3_movido=temp/medicoes/<nome>`
    **reprova se:** alguma chave falta ou sai `null` sem motivo, `trava_detectada=false` (a premissa da trava caiu), `clique_mp3_cresce_s` abaixo de 9 s (o MP3 não cresce antes de 10 s de coleta, `reco.py:1862-1864`: o número mede outra coisa), ou o MP3 de teste continua na pasta do Gabriel.
    - Recusa rodar se já houver `Reco.exe` aberto (código 3): com o mutex, o exe novo sairia em milissegundos e mediria a mensagem `Reco.Show`, não a partida (`reco.py:5201-5211`).
    - `abrir_visivel_s`: do `Popen` até a janela `TkTopLevel` visível. `abrir_pronta_s`: até alfa 255 por `GetLayeredWindowAttributes` (o fade sobe 0,07 a cada 14 ms, `reco.py:3025-3029`).
    - `ram_repouso_mb`: memória 5 s depois de pronta. `config`: valores de `live` e `device` lidos do JSON (o ao vivo ligado põe a GPU no caminho da gravação, `reco.py:3769-3784`).
    - Clique real no centro do botão Gravar: `SetCursorPos` mais `SendInput` com botão esquerdo para baixo e para cima (F0-D2).
    - `clique_ui_gravando_s`: até haver 2 botões visíveis, Parar e Pausar (`reco.py:3576-3580`).
    - `clique_arquivo_criado_s`: até nascer `gravacao_reco_*.mp3` novo na pasta (`reco.py:1689-1698`). `clique_mp3_cresce_s`: até o tamanho passar do primeiro valor visto, ou `null` com `nao_cresceu_em_s`.
    - `ram_gravando_mb`: memória a `segundos - 2`. `trava_detectada`: a checagem do passo 4 acusa o arquivo durante a gravação.
    - Clique em Parar (o botão mais à esquerda). `parar_arquivo_fechado_s`: até o `CreateFileW` exclusivo funcionar (o `close()` grava o Xing e solta o arquivo, `reco.py:803-815`).
    - `parar_ui_parado_s`: até haver 3 botões visíveis, Salvar, Excluir e Reproduzir (`reco.py:3586-3590`).
    - Depois: `taskkill /PID N /F` no processo de teste (estado parado, arquivo já fechado) e o MP3 vai para `C:\Dev\Reco\temp\medicoes\`, que é ignorado pelo git. Mover é reversível; não apagar.
    - Cada instância de teste rodaria a checagem de modelo novo 1,5 s depois de abrir (`reco.py:2940-2949`, `1230-1260`) e não há como ler o status de fora. Por isso o `HF_HUB_OFFLINE=1` do passo 10 e a reserva do passo 9; o relatório anota "checagem de modelo desligada" como condição.
    - Cada `taskkill /F` deixa um ícone morto na bandeja, que some quando o mouse passa por cima. É cosmético.
    - Cada linha também vai para `temp/medicoes/partida.jsonl`. A rodada 1 sai marcada `primeira=true`: o cache de disco já está quente, não é partida a frio (premissa P3).
    - Faixas esperadas, lidas no código, sem número inventado:
      - `parar_arquivo_fechado_s` < 7 s (as joins têm timeout de 3 s, `reco.py:1746`, `1772-1781`);
      - sem som, `clique_mp3_cresce_s` perto de 20 s (teto da retenção, `reco.py:1491-1492`, `1865-1868`) ou `null`.
    - `null` sem som é achado, não erro: responde a dúvida "loopback mudo não entrega pacote" (relatório 6 § 1.3), porque com `buf_sys` vazio o pareamento não avança (`reco.py:1862-1868`, `1991-1993`).
12. [ ] Rodar 2 vezes com som tocando (`--tocar`) — **prova:** `python C:/Dev/Reco/tools/medir_partida.py --rodadas 2 --segundos 35 --tocar` → 2 linhas JSON com `tocou=true` e `clique_mp3_cresce_s` entre 9 e 14 s
    **reprova se:** a chave falta, `tocou=false`, ou `clique_mp3_cresce_s` abaixo de 9 s (mede outra coisa, como no passo 11).
    - `clique_mp3_cresce_s` perto de 20 s não reprova: significa que o eco não chegou ao mic (fone, ou caixa no mudo) e vai para o relatório como condição.
    - `--tocar` toca ruído a −6 dBFS pelo alto-falante padrão nos primeiros 15 s, numa thread, como o `toca()` do `tools/test_gravacao_alinhada.py:79-85` (soundcard a 48 kHz).
    - Com eco medível, o alinhamento fecha em `ALIGN_COLETA_S = 10` s (`reco.py:1491`, `1862-1864`).
    - Toca som na máquina do Gabriel: rodar só nesta janela, nunca com ele em chamada.
13. [ ] Provar a exclusão mútua spike × Reco nos dois sentidos (D7) — **prova:** `python C:/Dev/Reco/temp/spike-bandeja/mutex.py` → `spike_primeiro: reco_saiu_em_ms=<N> reco_vivos=0` e `reco_primeiro: spike_saiu_em_ms=<N> mutex_existente_no_log=true`, com N < 3000
    **reprova se:** `reco_vivos=1` (o Reco abriu junto) ou o spike continua vivo depois de 3 s com o Reco aberto.
    - `mutex.py` (descartável, só `ctypes` e `subprocess`) faz os dois sentidos e abre o `Reco.exe` com `HF_HUB_OFFLINE=1` no ambiente (passo 10, P8).
    - Sentido 1: abre o spike sem `SPIKE_SEM_MUTEX`, espera o log `icone_rect`, abre `dist/Reco/Reco.exe` e mede quanto ele leva para sair.
    - Sentido 2: abre o `Reco.exe`, espera a janela, abre o spike e mede a saída dele.
    - No fim, encerra por pid só os processos que abriu. No sentido 2 a janela do Reco de teste aparece (efeito do `Reco.Show`); é esperado.
14. [ ] Reabrir o Reco do Gabriel e conferir que a biblioteca dele está limpa — **prova:** `powershell -NoProfile -Command "Start-Process 'C:\Dev\Reco\dist\Reco\Reco.exe'"` e depois `python C:/Dev/Reco/tools/medir_partida.py --ram-viva` → pid novo com `ws_mb` > 0
    **reprova se:** "Reco não está aberto", ou a pasta de saída dele ainda tem algum MP3 com a hora de uma rodada dos passos 11 a 13 (comparar com `temp/medicoes/partida.jsonl`).
    - **Antes do `Start-Process`, reprova também se:** `ls "$LOCALAPPDATA/Reco/models/"` não lista `whisper-large-v3-turbo-int8-ov`, lista algo terminado em `.old`, ou a soma de `models` difere da anotada no passo 9 (uma instância de teste mexeu no modelo).
      Aí, ainda com nenhum `Reco.exe` aberto, repor (PowerShell): `robocopy C:\Dev\Reco\temp\medicoes\models-reserva "$env:LOCALAPPDATA\Reco\models" /MIR /NFL /NDL` e somar de novo.
    - Soma igual (de primeira ou depois de repor): só então o `Start-Process`, e depois dele apagar `temp/medicoes/models-reserva` (790 MB).
    - O app reabre com a janela centralizada, não escondida na bandeja (`reco.py:2930-2937`): é o comportamento normal ao abrir.
    - Conferir também que `tasklist` não lista nenhum `reco-spike-bandeja.exe`.

### Bloco C — registrar e propagar

15. [ ] Escrever o relatório `roadmap/2026-11-11-melhoria-reco-em-rust.d/fase-0-relatorio.md` — **prova:** `grep -cE "abrir_pronta_s|clique_mp3_cresce_s|parar_arquivo_fechado_s|ram_gravando_mb|pipeline_gpu|D2" <rel>` → 6 ou mais e `grep -c exe_selftest <rel>` → 1 ou mais
    **reprova se:** o segundo grep dá 0 (a Fase 1 lê `exe_selftest`), algum número aparece sem a condição (som, `live`, `device`, escala de DPI, checagem de modelo desligada) ou "estimado" ocupa o lugar de um número medido.
    - Conteúdo:
      - tabela das rodadas (mediana e primeira) dos passos 11 e 12;
      - RAM viva (passo 2) e RAM do app recém-aberto (passo 11);
      - imports e pipeline (passo 3);
      - os dois modos da bandeja com `visivel_ms` (passos 7 e 8), o veredito da D2 e o resultado do mutex (passo 13).
    - Seção "O que isso diz às próximas fases":
      - Fase 1: quanto tempo a tela pode levar para responder, e o `exe_selftest` como duração do estado "motor subindo";
      - Fase 2: a partida do motor e se Gravar pode esperar por ele;
      - Fase 4: a régua de comparação.
    - Sem host, token nem caminho pessoal além de `C:\Dev\Reco` (o repo é público).
16. [ ] Propagar ao índice por `Edit` ancorado: linha após as notas das Decisões (F5-D14, `is_reco_recording`) com o veredito da D2 e o link do relatório, e o link em § Sidecar — **prova:** `grep -n "fase-0-relatorio" C:/Dev/Reco/roadmap/2026-11-11-melhoria-reco-em-rust.md` → 2 linhas
    **reprova se:** 0 linhas, ou a D2 foi reaberta e o índice não diz que a Fase 3 espera o spike de Slint.
    - Se a D2 confirmou com remendo (`showwindow`), a linha diz "Fase 3: mostrar pela `hwnd()` com `ShowWindow(4)`". O md da Fase 3 é de outra sessão: deixar a linha no índice, não editar a fase.
    - A mesma linha registra a F0-D5: a D7 (mesmo mutex `Local\Reco.SingleInstance`) se cumpre com `CreateMutexW` à mão, porque o plugin de instância única de "Caminho escolhido" cria outro mutex. **prova:** `grep -c "F0-D5" C:/Dev/Reco/roadmap/2026-11-11-melhoria-reco-em-rust.md` → 1 ou mais
    - **reprova se:** dá 0 (a F3-D2 da Fase 3, que já dispensa o plugin, fica sem a prova dos dois sentidos registrada no índice, e "Caminho escolhido" segue sugerindo o plugin).
    - Se a D7 tiver revertido para mutex próprio (cláusula "reverte se" dela, Fase 4 com os dois apps abertos), a linha diz que o passo 13 provou o nome antigo e que o nome novo pede nova prova.
17. [ ] Atualizar a documentação: linha do `medir_partida.py` em `docs/TOOLS.md` e o hub — **prova:** `grep -c "medir_partida.py" C:/Dev/Reco/docs/TOOLS.md` → 1 e `grep -c "Reco em Rust" C:/Dev/cerebro/projetos/reco.md` → 1 ou mais
    **reprova se:** algum dá 0.
    - `docs/TOOLS.md`: uma linha na tabela com os modos e o aviso "nunca fecha o Reco do usuário: `--esperar-fechado` só checa a gravação e espera o Sair pela bandeja; move os MP3 de teste para temp/medicoes".
    - Hub `cerebro/projetos/reco.md`, por `Edit` ancorado: em "Estado agora", uma linha 11/11 com os 3 números principais e o link do índice; em "Roadmaps em voo", a entrada "Reco em Rust · 1/8".
    - O spike revelou pegadinha (ícone escondido no Windows 11, posicionador errado, `Enter` que não chega)? Entrada nova só por `python tools/visoes.py novo "título"`, nunca editando `docs/ARMADILHAS.md`.
    - README, `docs/ARQUITETURA.md` e o `CLAUDE.md` do projeto não mudam: a fase não muda comportamento nem cria regra. Dizer isso no relatório.
    - Fragmento do diário em `C:\Dev\cerebro\pessoal\diario\2026-11-11\` (template `diario/_TEMPLATE.md`) e `cerebro/scripts/compilar_fragmentos.py`, pelo ritual.
18. [ ] Commitar por pathspec nos dois repos — **prova:** `git -C C:/Dev/Reco status --short tools docs roadmap` → nada dos arquivos desta fase; `git -C C:/Dev/Reco log -1 --stat` lista `tools/medir_partida.py`
    **reprova se:** o pre-commit recusa (ruff, trava de tamanho, gitleaks). Corrigir e commitar de novo, nunca com `--no-verify`.
    - Antes do commit, o repo é público: tirar caminhos pessoais dos arquivos novos (em 11/11 havia em `fase-1.md`, `fase-6.md` e `diagnostico/6-critica-de-completude.md`). Trocar por `%USERPROFILE%` ou `%LOCALAPPDATA%`.
      - **prova:** `grep -rlE 'C:[\\/]Users|Gabriel dos Anjo[s]|App[D]ata' C:/Dev/Reco/roadmap/2026-11-11-melhoria-reco-em-rust* C:/Dev/Reco/tools/medir_partida.py C:/Dev/Reco/docs/TOOLS.md` → saída vazia
      - **reprova se:** lista algum arquivo.
    - Reco: `git add tools/medir_partida.py docs/TOOLS.md "roadmap/2026-11-11-melhoria-reco-em-rust*"` mais os 6 roadmaps do passo 5 e a entrada de `docs/armadilhas.d/`, se houver. Nunca `git add -A`.
    - Commit por pathspec, para não levar o que outra sessão deixou no stage: `git commit -m "..." -- <os mesmos caminhos>`. Depois `git push`.
    - O glob leva o índice, os mds de fase e o sidecar, todos não rastreados em 11/11. `temp/` fica fora pelo `.gitignore`.
    - C:\Dev: `git -C C:/Dev add cerebro/projetos/reco.md <fragmento do diário> <páginas geradas pelo compilar_fragmentos>` e `git -C C:/Dev commit -m "..." -- <os mesmos caminhos>`.
    - Nenhum arquivo que entra no executável mudou: não recompilar. Se algum passo tocar `reco.py` ou `tray.py`, parar: está fora do escopo.

## Decisões da fase

| id | decisão | motivo | confiança | reverte se |
| --- | --- | --- | --- | --- |
| F0-D1 | Medir de fora do processo, com `ctypes` e stdlib, no exe que o Gabriel usa | sem dependência nova; o `reco.py` não cresce; um harness com `App()` mediria o fonte, gravaria o config (`reco.py:2868`) e pularia o mutex | alta | a Fase 4 medir o app novo por dentro |
| F0-D2 | Clique real (`SendInput`) no centro do HWND do botão, achado por classe `Button` | é o caminho do dedo do Gabriel; UIA não está instalado, e o Tk 8.6 não expõe nomes acessíveis (P1) | média | o passo 10 achar 0 botões: usar o menu da bandeja pelo teclado |
| F0-D3 | Sinais externos: janela visível e opaca = pronta; troca de botões visíveis = estado; trava exclusiva do arquivo = gravando ou fechado | o app não tem log e não pode ganhar; os três sinais se leem sem tocar no processo | média | o passo 11 mostrar `trava_detectada=false` |
| F0-D4 | Spike por `cargo build` puro em `temp/spike-bandeja/`, crate `reco-spike-bandeja` | `cargo tauri` não está instalado; `temp/` é ignorado; `C:\pt` é compartilhado | alta | o build sem CLI não embutir o front (P4): instalar `tauri-cli` só no spike |
| F0-D5 | Exclusão mútua por `CreateMutexW` feito à mão, com o nome do Reco e o broadcast `Reco.Show`, não pelo plugin de instância única | o plugin cria `"{identifier}-sim"` (`windows.rs:90`) e não fala com o Reco velho | alta | a D7 mudar para mutex próprio na Fase 4 |
| F0-D6 | Medir com e sem som tocando | a retenção é de 10 s com eco e de até 20 s sem eco (`reco.py:1491-1492`); um número só esconderia a diferença | alta | — |
| F0-D7 | O app do Gabriel fecha só pelo Sair da bandeja, feito por ele, após 2 checagens de trava a 25 s; a sessão espera o processo sumir e reabre | sem saída limpa por mensagem (`reco.py:5079-5086`); matar perde gravação, o Sair salva (`reco.py:5088-5111`); Fases 2 e 3 | alta | — |

## Premissas não verificadas

- **P1:** o `tk.Button` do Tk 8.6 no Windows é um controle nativo `BUTTON`, com HWND próprio, que some quando o `pack_forget` desempacota. O passo 10 prova; se falhar, vale a reversão da F0-D2.
- **P2:** uma transcrição em andamento no app do Gabriel não segura o MP3 aberto o tempo todo, então a checagem de trava não a vê. Por isso o passo 9 também recusa com CPU acima de 10% de um núcleo (limiar não medido). Se escapar e ele der Sair, perde-se só a transcrição, que se refaz.
- **P3:** não dá para medir partida a frio sem reiniciar a máquina. A rodada 1 é "primeira depois de fechar o app", com o cache de disco provavelmente quente.
- **P4:** com `cargo build` puro, sem `devUrl`, o Tauri 2 embute o `frontendDist` no binário de debug. Se a janela abrir em branco, compilar com `--release` ou instalar o `tauri-cli` no spike.
- **P5:** `SetCursorPos` sobre o ícone faz o Explorer mandar `WM_MOUSEMOVE` ao ícone e o `tray-icon` emitir `Enter`. Se não fizer, o passo 7 vira verificação manual com o mouse de verdade.
- **P6:** o ffmpeg do PyAV abre o MP3 com compartilhamento total (`_SH_DENYNO`), então o `CreateFileW` exclusivo falha enquanto o app escreve e funciona depois do `close()`. Os passos 4 e 11 provam (`trava_detectada`).
- **P7:** o `tauri-plugin-positioner` 2 tem `Position::TrayBottomCenter` e `on_tray_event` com a feature `tray-icon`. Não está no cache do cargo e não foi lido; o passo 6 descobre ao compilar.
- **P8:** com `HF_HUB_OFFLINE=1` no ambiente, o `update_model_if_newer` cai no `except` e não troca o modelo (`reco.py:1230-1260`). Conferido em 11/11 só no Python do fonte (`huggingface_hub` 1.20.1 → `OfflineModeIsEnabled`); o exe leva a mesma versão, sem teste. A reserva do passo 9 cobre.

## Pendente (dono: gabriel)

- **Sair do Reco pela bandeja quando a sessão pedir (passo 9)**, sem estar em chamada (o passo 12 toca ruído no alto-falante). `dono: gabriel`.
  O executor **nunca** mata o `Reco.exe` dele. Sem o Sair, faz o Bloco A inteiro e o Bloco C no que der, e deixa os passos 9 a 14 para quando ele puder.

## O que esta fase NÃO faz

- Não muda `reco.py`, `tray.py`, `build.ps1` nem o exe: o app do Gabriel sai igual.
- Não cria `engine/` nem `app/`: o spike é descartável, mora em `temp/` e não vira base da Fase 3.
- Não desenha a interface nem escolhe a identidade visual (Fase 1).
- Não corrige o pulo de janela, o DPI nem o bundle de 859 MB (Fases 3 e 4).
- Não mede transcrição de ponta a ponta: o `tools/test_e2e.py` já existe e o motor não muda até a Fase 6.
- Não testa a captura sob carga (gate da Fase 5).

## Gatilho que fecha

- O relatório `fase-0-relatorio.md` no sidecar com os números dos passos 2, 3, 11 e 12, cada um com a condição.
- O veredito da D2 (confirmada, confirmada com remendo ou reaberta) escrito no índice, e a D7 provada nos dois sentidos (passo 13).
- O Reco do Gabriel aberto de novo e nenhum MP3 de teste na pasta dele (passo 14).
- As 6 linhas datadas nos roadmaps em voo (passo 5), `docs/TOOLS.md` e o hub atualizados, e o commit no repo do Reco feito sem `--no-verify`.
- Se a D2 foi reaberta, a Fase 1 e a Fase 2 podem começar mesmo assim; a Fase 3 espera o spike de Slint.
