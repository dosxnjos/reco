# Reco em Rust: Fase 7 — Aposentar a interface Tk e propagar

> Índice: [2026-11-11-melhoria-reco-em-rust.md](2026-11-11-melhoria-reco-em-rust.md) · anterior: [fase-6](2026-11-11-melhoria-reco-em-rust-fase-6.md) · seguinte: — · Base: Reco `7c5c1a1` (2026-11-11)

## Por que esta fase

- Depois da Fase 4, o Gabriel usa o app novo (Tauri, `app/`) com o motor Python (`engine/`); a interface Tk do `reco.py` virou só reserva.
- Código morto custa: o `reco.py` tem 5213 linhas (a trava de tamanho só deixa encolher) e importa `tkinter` e Pillow no topo (`reco.py:17-18`, `:543-547`).
- Esse peso viaja no motor congelado de hoje. Tirar a UI encolhe o arquivo, o bundle e a superfície que os 23 scripts de `tools/` e o motor importam.
- O Reco é infraestrutura da casa: a sentinela da central, os guias do harness, o checador de órfãos do cérebro e 5 roadmaps e ~15 issues apontam para o app velho.
- Se a UI sair sem propagar, esses pontos mentem ou viram no-op em silêncio. Esta fase fecha o roadmap: remove com prova e propaga rio abaixo.

## O que ler antes

- `C:\Dev\Reco\CLAUDE.md`, `C:\Dev\cerebro\projetos\reco.md` (o hook `guarda-escrita` cobra) e `C:\Dev\Reco\docs\ARMADILHAS.md` inteira.
- `C:\Dev\cerebro\projetos\central.md` antes do passo 11 (edita a central) e `C:\Dev\central\CLAUDE.md`.
- O índice inteiro: `C:\Dev\Reco\roadmap\2026-11-11-melhoria-reco-em-rust.md` (D6 e D7 mandam aqui).
- Relatórios das Fases 2 a 6 em `C:\Dev\Reco\roadmap\2026-11-11-melhoria-reco-em-rust.d\` (build do motor e do app, veredito do portão da Fase 6).
- Evidência: `...rust.d\diagnostico\1-mapa-do-reco-atual.md` (§ 1, 2, 5, 6) e `...rust.d\diagnostico\2-restricoes-do-porte.md` (§ 3 e 4).
- Código: `C:\Dev\Reco\reco.py` (UI em `:2737-5128`, `__main__` em `:5131-5213`), `C:\Dev\Reco\tray.py`, `C:\Dev\Reco\tools\check_i18n.py`, `C:\Dev\Reco\tools\transcrever.py`.
- Fase 2 (de onde vêm os nomes do motor): `engine/reco_engine/`, `engine/build.py` (`--smoke`), `engine/reco-engine.spec`, saída em `engine/dist/reco-engine/` (passos 14 e 15 e F2-D6 e F2-D9 da Fase 2).
- Fora do Reco: `C:\Dev\central\canais_comuns.py:35-38`, `C:\Dev\central\tools\testa_canais.py:360-366`, `C:\Dev\central\canais\whatsapp\coletor\src\anexos.js:21-24`.
- Fora do Reco: `C:\Dev\cerebro\scripts\check-orfaos.py:112-115`, `C:\Dev\.obsidian\app.json`, `C:\Dev\cerebro\temas\harness\guides-e-sensores.md:45,72-82`, `C:\Dev\cerebro\temas\harness\vocabulario-curto.md:60`.

## Fase 7 — Aposentar a interface Tk e propagar

**Critério de aceite:**

- O Gabriel grava, para e transcreve no app novo como antes, e uma mídia mandada no chat continua virando texto igual ao de antes da fase. Se falhar: o app novo não abre, não grava, ou a transcrição de um áudio sai diferente (ou nem sai).
- Quem chega ao repo, ao hub ou aos guias da casa encontra só o app novo como "o Reco"; nenhuma instrução manda abrir, compilar ou consertar a janela antiga. Se falhar: um guia ou doc ainda ensina o caminho velho, ou um roadmap superado aparece como trabalho em voo.
- A vigia da central que protege a fila do WhatsApp continua acusando quando o aviso "sem fala" do Reco muda de lugar. Se falhar: a vigia passa verde mesmo apontando para um arquivo que não existe mais.

Regras que valem para todos os passos:

- Cada passo que muda arquivo fecha com commit próprio por pathspec (`git add <arquivos>`; nunca `git add -A`, nunca `--no-verify`). Reverter um passo = `git revert <sha>`.
- A pasta `C:\Dev\Reco\dist\Reco\` (o exe velho, fora do git) e a cópia `%LOCALAPPDATA%\Reco-reserva` (F4-D3) **não se apagam** nesta fase: são a reserva física do Gabriel (ver Pendente).
- Comandos rodam de `C:\Dev\Reco` salvo indicação. `temp/` é ignorado pelo git (`.gitignore:25`): toda saída de prova vai para `temp/fase7/`.
- Mexeu no que entra no motor congelado (`reco.py`, `engine/`) → recompila pelo build da Fase 2/3 (passo 8) antes de dizer que chegou ao app.

1. [ ] Conferir as portas de entrada no sidecar `roadmap/2026-11-11-melhoria-reco-em-rust.d/` (Fases 4 e 6) — **prova:** `grep -in "aprov" roadmap/2026-11-11-melhoria-reco-em-rust.d/*fase-4*` → linha dizendo que o Gabriel aprovou a troca
   **reprova se:** o grep volta vazio ou nenhuma linha registra a aprovação dele, ou a Fase 6 não tem veredito do portão (aberto ou fechado): a fase não começa, a reserva Tk ainda é necessária.
   - Ler a linha que o grep achou: "Recomendação: aprovar só se…" copiada da Fase 4 não é aprovação.
   - Veredito da Fase 6 (índice: a Fase 7 depende de 4 e 6): `grep "^Decisão do portão:" roadmap/2026-11-11-melhoria-reco-em-rust.d/fase-6-portao.md` → `ABRE (M6)` ou `FECHA (Mx)` (Fase 6, passo 10).
     **reprova se:** volta vazio, ou diz `ABRE` mas a Fase 6 não fechou a Parte B (passos 11 a 26 sem `[x]`): sem veredito fechado, os passos 3, 10 e 11 não sabem se o invólucro e o `.rs` existem.
   - Conferir também `Get-Process | Where-Object Path -like '*Reco*' | Select-Object Path` no PowerShell: o app em uso **não** pode estar em `C:\Dev\Reco\dist\Reco\` nem em `%LOCALAPPDATA%\Reco-reserva`.
   - Contrato headless (D6): copiar `temp/bench-voz/clip05.wav` para `temp/fase7/clip.wav` e rodar `engine/dist/reco-engine/reco-engine.exe --transcribe temp/fase7/clip.wav`.
   - Tem de nascer `temp/fase7/clip.txt` (o `--transcribe` troca a extensão por `.txt`, `reco.py:5176`). Sem isso, a fase para.
   - Repetir com o exe do casco novo (`Reco.exe`, saída em `C:\pt`). A Fase 3 implementa o repasse (passo 7, F3-D14, em `instancia.rs`) e a Fase 4 o testa (P25); aqui só se confirma que continua valendo.
   - Se não repassar, a fase **não** para aqui: o `dist\Reco\Reco.exe` velho segue no disco e honra o contrato enquanto isso. Anotar no relatório.
   - Mas o repasse vira condição para **fechar** esta fase (D6), não só para apagar o app velho: o passo 8 o implementa e prova, e o passo 16 confere de novo.
   - Anotar no relatório da fase o veredito da Fase 6: ele decide o ramo dos passos 3 (invólucro), 10 e 11 (onde mora o literal da sentinela).

2. [ ] Congelar a linha de base em `temp/fase7/base/` **antes** de remover qualquer coisa (lista abaixo) — **prova:** `ls temp/fase7/base/ | wc -l` → `11` (os 2 áudios, os 2 `.txt` e as 7 saídas `.out`)
   **reprova se:** falta arquivo, `test_encoder.out` não termina em `TUDO OK` ou `testa_canais.out` não diz `ok — 0 falhas`: sem base verde, nada prova que a remoção não quebrou.
   - Saídas esperadas: `clip.wav.txt`, `gravacao_reco_base.mp3.txt`, `test_encoder.out`, `test_model_dir.out`, `test_dispositivo_auto.out`, `check_i18n.out`, `test_alinhamento.out`, `smoke_motor.out`, `testa_canais.out`.
   - Áudio comum: `cp temp/bench-voz/clip05.wav temp/fase7/base/clip.wav` e `python tools/transcrever.py temp/fase7/base/clip.wav --device GPU` (texto corrido em `clip.wav.txt`; contrato em `tools/transcrever.py:87-96`).
   - Gravação do Reco: copiar a menor `~/Documents/Reco/gravacao_reco_*.mp3` (`ls -S ... | tail -1`) para `temp/fase7/base/gravacao_reco_base.mp3`.
   - Fora da pasta do app, ela sai diarizada em `gravacao_reco_base.mp3.txt` (`tools/transcrever.py:63-75`, `:87-96`; a etiqueta vem de `reco.py:136-138`).
   - Testes: `python tools/test_encoder.py`, `python tools/test_model_dir.py`, `python tools/test_dispositivo_auto.py`, `python tools/check_i18n.py`, cada um com `> temp/fase7/base/<nome>.out 2>&1`.
   - `python tools/test_alinhamento.py` é **vermelho desde que nasceu** (caso 8, +352 amostras; diagnóstico `2-restricoes-do-porte.md` § 4). Guardar a saída: a régua é "o mesmo vermelho", não verde.
   - Smoke do motor (Fase 2, passo 15): `python engine/build.py --smoke > temp/fase7/base/smoke_motor.out 2>&1` (molde: `C:\Dev\lacre\engine\build.py:1-8`).
   - O smoke imprime tempos, que mudam a cada rodada: "igual à base" nele quer dizer as mesmas linhas `hello ok`/`ready` e nenhum erro, nunca bytes iguais.
   - Central: `cd C:\Dev\central && python tools/testa_canais.py > C:\Dev\Reco\temp\fase7\base\testa_canais.out`.

3. [ ] Criar `tools/check_superficie.py` (novo, até 150 linhas): por AST, todo `reco.X` e `from reco import X` de `engine/**/*.py` e `tools/*.py` tem de existir no `reco` — **prova:** `python tools/check_superficie.py` → `OK — <N> nomes ... todos presentes`, exit 0
   **reprova se:** com `--incluir temp/fase7/falso.py` (contém `import reco; reco.NAO_EXISTE`) a saída não traz `FALTA reco.NAO_EXISTE (temp/fase7/falso.py:1)` com exit 1.
   - A opção `--incluir <arquivo>` existe só para provar o próprio checador.
   - Ele é a rede dos passos 6 e 7: o que o motor ou um tool usa não pode sumir junto com a UI.
   - Cobre também o módulo `transcrever` (`tools/transcrever.py`): todo `transcrever.X` e `from transcrever import X` de `engine/` e `tools/` tem de existir nele.
   - Com o portão da Fase 6 aberto, `tools/transcrever.py` é o invólucro (Fase 6, passo 22) e reexporta de `transcrever_py`; o `tools/paridade.py` da Fase 4 importa `transcrever.diarizada`.
   - Formato único da falta, nos dois módulos: `FALTA <módulo>.<nome> (<arquivo>:<linha>)`.
   - Segunda prova: `--incluir temp/fase7/falso2.py` (contém `import transcrever; transcrever.NAO_EXISTE`) → `FALTA transcrever.NAO_EXISTE (temp/fase7/falso2.py:1)`, exit 1.
     **reprova se:** passa com exit 0: o checador não olha o `transcrever`, e um nome que o invólucro deixou de reexportar quebraria a régua da Fase 4 em silêncio.
   - Nomes vistos hoje nos tools (grep em `7c5c1a1`): `DualRecorder`, `MP3Writer`, `estimar_offset`, `ALIGN_*`, `cancel_echo`, `_alinhar_canais`, `dominancia_sistema`, `LiveTranscriber`, `OVTranscriber`.
   - E ainda: `load_config`, `make_transcriber`, `_spk_me`, `_spk_them`, `default_endpoint_id`, `resolve_audio_device`, entre outros.
   - O `check_i18n.py` carrega o `reco` por `spec_from_file_location` (`tools/check_i18n.py:111-119`): tratar esse caso como uso de `_TR_EN`.
   - Seguir todo nome ligado ao módulo, não só a palavra `reco`: `import reco as _reco` (`tools/test_alinhamento.py:170`) e, no motor, `importlib.import_module("reco")` (o `boot.py` da Fase 2 importa o `reco` em segundo plano).
   - Imprimir também, uma por linha, `UI usada: <nome> (<arquivo>:<linha>)` para cada nome da UI que aparecer no uso (o passo 4 consome): `App`, `VuMeter`, `gain_to_frac`, `frac_to_gain`, `fmt_gain`, `apply_theme`, `set_dark_titlebar`, `_icon_file`, `LANG_LABELS`, `SEG_*`, `HAS_TRAY`, `HAS_PIL`.
   - Documentar em `docs/TOOLS.md` (uma linha) no passo 15.

4. [ ] Garantir que nada que o motor precisa mora só no `App`, a começar pela persistência da migração do config (hoje só em `reco.py:2868`) — **prova:** `python tools/check_superficie.py` → nenhuma linha `UI usada:`
   **reprova se:** o checador lista um nome da UI usado pelo motor ou por um tool: o passo 6 apagaria algo vivo.
   - Migração do config: o motor **não** passa a chamar `load_config(persist=True)` nesta fase, e o exe velho segue no disco (F7-D6).
   - A Fase 2 proibiu (F2-D6) pela ARMADILHA "Migração de config persistida antes do exe novo re-arma o autosave do exe antigo" (`docs/ARMADILHAS.md`; docstring de `reco.py:210-215`).
   - Segunda prova: `git grep -n "persist=True" -- engine/` → vazio.
     **reprova se:** aparece linha: com o `dist\Reco\Reco.exe` ainda abrível, uma migração 3 gravada pelo motor faz o exe velho regravar o config (a armadilha).
   - O `config.set` do motor segue a releitura crua da Fase 2 (F2-D6: `json.loads` de `reco.CONFIG_PATH`, merge só das chaves recebidas); nunca grava o resultado de `load_config()`, que traz a migração em memória.
   - Conferir em `engine/reco_engine/config_cmd.py`; se ele gravar o config relido por `load_config()`, é desvio da F2-D6: voltar à releitura crua e recompilar (passo 8).
   - Atualizar a docstring de `load_config` (`reco.py:210-215`, "que é só o `App.__init__`"): sem o `App`, ninguém persiste a migração até o exe velho sair. Ligar o `persist=True` no motor fica para então (Pendente).
   - Se o checador listar nome da UI: mover a lógica usada para módulo novo em `engine/` (até 500 linhas), sem alterar o comportamento, e repetir o passo 3.
   - Exemplo provável: a regra de diarizar/AEC de `App._run_transcriber` (`reco.py:4196`), que o `tools/transcrever.py:63-75` já replica. Se o motor ainda a chama pelo `App`, ela vai para o núcleo.
   - Atualizar a docstring de `tools/transcrever.py:64`, que cita `App._run_transcriber`, para o lugar novo da regra.

5. [ ] Aposentar o build do exe velho antes do código que ele empacota: `git rm build.ps1 reco.spec setup.ps1` e, no mesmo commit, `CLAUDE.md:16-23` passa a mandar o build novo — **prova:** `git ls-files build.ps1 reco.spec setup.ps1; grep -c "build.ps1" CLAUDE.md` → só `0`
   **reprova se:** algum dos três segue listado, ou o `CLAUDE.md` ainda manda rodar `build.ps1`: o próximo agente recompila um exe que não existe e acha que a mudança chegou ao app.
   - Por que antes do passo 6: depois que a UI sai, o `build.ps1` geraria um exe quebrado. Sem o build velho, o repo nunca fica num estado que produz app quebrado.
   - O `build.ps1:24` e o `setup.ps1:21` ainda instalam `lameenc`, que o `CLAUDE.md:45` proíbe: some junto.
   - Outras menções que sobram depois do commit (`git grep -n "build.ps1\|reco.spec\|setup.ps1"`): `README.md:81,91,194,203` e `docs/ARQUITETURA.md:16,241,252`, que o passo 15 reescreve; `tools/gerar_icones.py:9` (F7-D3) e o comentário de `ruff.toml:11`, que só citam o nome.
   - O `setup.ps1` termina mandando rodar `python reco.py` (abrir a janela Tk); o caminho de "rodar do fonte" passa a ser o do app novo (README no passo 15).
   - O exe já compilado em `dist\Reco\` continua abrindo: o binário não depende do fonte. A reserva física fica intacta.

6. [ ] Remover a UI do `reco.py`: `VuMeter` (`:2771-2849`), `LANG_LABELS` (`:2850`), `App` (`:2853-5128`) e o ramo da janela no `__main__` (`:5178-5213`) — **prova:** `python -c "import reco; print(hasattr(reco, 'App'), hasattr(reco, 'VuMeter'))"` → `False False`
   **reprova se:** o `import reco` quebra, ou `python tools/check_superficie.py` acusa `FALTA`, ou `wc -l reco.py` continua em 5213 (o esperado é por volta de 2800).
   - `GAIN_*` e as funções de ganho (`:2737-2768`) saem só se o checador do passo 3 não as listar (o motor pode usar a escala do ganho).
   - Ficam no `__main__` o `--selftest` (`:5132-5146`) e o `--transcribe` (`:5148-5176`). Sem flag, `python reco.py` imprime em stderr "a interface do Reco agora é o app em app/" e sai com código 2 (F7-D2).
   - Saem junto o `messagebox` de dependências ausentes (`:5178-5191`, vira `print` em stderr) e o mutex `Local\Reco.SingleInstance` (`:5197-5208`), que agora é do app novo (D7).
   - O literal `"(no content recognized)"` sai das linhas da UI (`:4045` modo nota, `:4184` `_autosave_txt`) e **fica** no núcleo (`:2374` `OVTranscriber.transcribe`, `:2721` MLX). O passo 10 confere.
   - Prova extra (mesma sessão): `python tools/test_encoder.py` → `TUDO OK`.
   - Prova extra: `python tools/transcrever.py temp/fase7/clip.wav --device GPU --forcar`, depois `cmp temp/fase7/clip.wav.txt temp/fase7/base/clip.wav.txt` → sem saída.
   - A trava de tamanho só encolhe o `reco.py`; o pre-commit da complexidade compara a soma contra o HEAD e cai (`tools/tamanho.json`).

7. [ ] Tirar o resto do Tk do núcleo (`reco.py:17-18`, `:36-96`, `:252-266`, `:537-547`) e `git rm tray.py` — **prova:** `python -c "import sys, reco; print(sorted(m for m in ('tkinter', 'PIL', 'tray') if m in sys.modules))"` → `[]`
   **reprova se:** a lista não vem vazia: o motor congelado continua arrastando Tcl/Tk e Pillow, e a exclusão do passo 8 quebra o motor na hora de subir.
   - O que sai: imports de `tkinter`/`ttk`/`filedialog`/`messagebox`/`colorchooser`, tema e fontes, `_icon_file`, `set_dark_titlebar`, `import tray` e Pillow.
   - `_asset` (`:247-249`) fica só se o checador do passo 3 achar uso fora da UI; hoje os 3 usos são UI (`:253`, `:3079`, `:4917`).
   - `apply_theme`/`DEFAULT_BG`/`DEFAULT_ACCENT` saem; as chaves `bg_color`/`accent_color` do config **ficam** (contrato do arquivo, D6; o motor ignora).
   - O `_CFG_DEFAULTS` usa as duas constantes (`reco.py:106-107`): trocar pelos literais `"#181A1B"` e `"#E0825F"` (`reco.py:44-45`), senão o `import reco` quebra. A chamada solta `apply_theme(DEFAULT_BG, DEFAULT_ACCENT)` (`reco.py:90`) sai junto.
   - `requirements.txt:5` (Pillow) sai se o checador e `git grep -n "PIL" -- engine/` não acharem uso.
   - Rodar de novo `python tools/check_superficie.py`, `python tools/test_encoder.py` e `python tools/test_dispositivo_auto.py` → os mesmos resultados da base.
   - `python tools/test_alinhamento.py > temp/fase7/alinhamento.out 2>&1`, depois `diff temp/fase7/alinhamento.out temp/fase7/base/test_alinhamento.out` → só a linha de tempo difere (o mesmo vermelho do caso 8).

8. [ ] Encolher o motor e recompilar: `tkinter` e `PIL` (e `pyarrow`/`duckdb`, se faltarem) nas exclusões do build do motor da Fase 2 (`engine/reco-engine.spec` / `engine/build.py`); recompilar motor e app — **prova:** `ls engine/dist/reco-engine/_internal | grep -ci "tcl\|tk\|PIL"` → `0`
   **reprova se:** o `grep` acha `tcl`/`tk`/`PIL` (a exclusão não entrou, o bundle segue gordo; o exe velho em `dist/Reco/_internal` dá `7` com o mesmo comando) ou o smoke do motor perde uma linha `hello ok`/`ready` da base ou passa a ter erro.
   - O Lacre faz o mesmo (`C:\Dev\lacre\engine\build.py:24`, `EXCLUDES` com `tkinter` e `PIL`). Até aqui o motor não podia excluir Tk porque o `reco.py:17` o importa no topo (F2-D9); o passo 7 tirou esse import.
   - Anotar no relatório o tamanho do motor congelado antes e depois (`du -sh`); o lixo pyarrow + duckdb foi medido em ~116 MB (`1-mapa-do-reco-atual.md` § 6).
   - O binário do app sai em `C:\pt` (`CARGO_TARGET_DIR` desta máquina), não em `app/src-tauri/target`.
   - Repasse do `--transcribe` (D6), se o passo 1 achou que regrediu: no mesmo lugar onde a Fase 3 o pôs (`instancia.rs` do casco), antes do mutex e da janela, `--transcribe <arq>` roda o motor com o mesmo argumento, sem console, e devolve o exit dele.
   - Prova do repasse: apagar `temp/fase7/clip.txt` e rodar o `Reco.exe` do casco recompilado com `--transcribe temp/fase7/clip.wav` → nasce `temp/fase7/clip.txt`, exit 0, nenhuma janela.
     **reprova se:** o `.txt` não nasce, o exit não é 0, ou o casco abre a janela ou acusa a instância única: sem o repasse, a fase não fecha (contrato D6).
   - Verificação manual (precisa do Gabriel ou da tela dele): abrir o app novo, gravar 30 s, parar, salvar e transcrever. O MP3 e o `.txt` nascem na pasta de gravações.

9. [ ] Podar a tradução: `tools/check_i18n.py:17` varre `reco.py` + `engine/**/*.py` (sai `tray.py`) e as `MORTAS` saem de `_TR_EN` (`reco.py:290-499`) — **prova:** `python tools/check_i18n.py` → `OK — cobertura completa, nada morto.`, exit 0
   **reprova se:** aparece `FALTANTES` (o núcleo usa uma frase apagada; o usuário em inglês vê português) ou `MORTAS` (sobrou entrada só da UI).
   - O núcleo usa `t()`/`tf()` em ~20 lugares (download e atualização de modelo, `Transcrevendo… {p}%`, avisos do ao vivo, `device_options`; `reco.py:1202-2693`). Essas chaves **ficam**.
   - Se o app novo traduz códigos do motor na UI (padrão do Lacre), as frases restantes só chegam por `tools/transcrever.py` e pelo log. Não mudar isso aqui.

10. [ ] Confirmar onde nasce o aviso "sem fala" que a central copia e fixar a lista de alvos da sentinela pelo veredito da Fase 6 — **prova:** `git grep -n '"(no content recognized)"' -- reco.py engine app` → só no núcleo de transcrição
   **reprova se:** o literal some (o coletor volta a tratar "sem fala" como transcrição, ARMADILHAS #261) ou aparece só em arquivo que o `tools/transcrever.py` não executa.
   - Portão fechado: lista = `reco.py`, onde o literal mora em `OVTranscriber.transcribe` (`:2374`) e no MLX (`:2721`).
   - Portão aberto: lista = `reco.py` (a reserva `tools/transcrever_py.py` ainda usa o `OVTranscriber`) e `app/crates/reco-transcritor/src/transcrever.rs` (Fase 6, passo 26). O literal mora nos dois.
   - Quem consome é o coletor: ele chama `tools/transcrever.py`, que grava o texto do `done_cb` (`reco.py:2374`) ou, com o portão aberto, o do exe Rust. Esse é o lugar que importa, não o `.txt` do app.
   - Anotar no relatório a lista exata dos alvos (arquivo + função de cada um), usada no passo 11.

11. [ ] Fazer a sentinela falhar alto: em `C:\Dev\central\tools\testa_canais.py:360-366`, o `if os.path.isfile(reco):` vira laço na lista `alvos`, com `checar(os.path.isfile(alvo), ...)` e o literal em cada um — **prova:** `cd C:\Dev\central && python tools/testa_canais.py` → `ok — 0 falhas`
   **reprova se:** `RECO_FONTE_SENTINELA=C:/nao/existe python tools/testa_canais.py` ainda imprime `ok — 0 falhas`: a sentinela é no-op e a fila do WhatsApp perde a vigia em silêncio.
   - `alvos` = variável de ambiente `RECO_FONTE_SENTINELA` (um ou mais caminhos separados por `os.pathsep`), ou, sem ela, a lista fixada no passo 10.
   - Com o portão aberto, os dois `checar` que a Fase 6 (passo 26) pôs lado a lado viram essa lista; nenhum dos dois arquivos sai da vigia.
   - Lista vazia também falha (`checar(len(alvos) > 0, ...)`): um laço sobre lista vazia é o mesmo no-op de hoje.
   - Alvo inexistente conta uma falha só: o `checar` do literal pula o arquivo que não existe.
   - Com um alvo inexistente, a saída certa é `FALHA — 1 problema(s):` com a mensagem dizendo que a fonte sumiu e que é preciso apontar para o arquivo novo.
   - Segunda prova: `RECO_FONTE_SENTINELA="C:/Dev/Reco/reco.py;C:/nao/existe" python tools/testa_canais.py` → `FALHA — 1 problema(s):`.
     **reprova se:** imprime `ok — 0 falhas`: o laço para no primeiro alvo válido e o segundo arquivo perde a vigia.
   - Terceira prova (só com o portão aberto): `grep -c "reco-transcritor/src/transcrever.rs" tools/testa_canais.py` → `1` ou mais.
     **reprova se:** dá `0`: a lista padrão voltou a só o `reco.py`, e o literal que nasce no Rust mudaria sem alarme.
   - Atualizar os comentários que dizem onde está a frase: `C:\Dev\central\canais_comuns.py:35-37` e `C:\Dev\central\canais\whatsapp\coletor\src\anexos.js:21`, citando arquivo e função (não número de linha).
   - Rodar também `node canais/whatsapp/coletor/tools/testa_coletor.js` → o caso `"(no content recognized)"` (linha ~603) passa.
   - Commit no repo da central (`dosxnjos/central-demandas`) por pathspec: só os três arquivos.

12. [ ] Propagar ao harness e ao cérebro: guias e `Reco/engine/dist/` no `.obsidian/app.json` e em `check-orfaos.py:112-115` — **prova:** `python -c "import json; print('Reco/engine/dist/' in json.load(open('C:/Dev/.obsidian/app.json', encoding='utf-8'))['userIgnoreFilters'])"` → `True`
   **reprova se:** imprime `False` (o Obsidian indexa os `.md` de licença de dentro do motor congelado), ou `python C:/Dev/cerebro/scripts/check-orfaos.py --orfaos` imprime `aviso: FILTROS_FALLBACK diverge do app.json real`.
   - O script em si já pula toda pasta `dist` (`SKIP_DIRS`, `check-orfaos.py:43-48`); o filtro serve ao grafo do Obsidian, e o fallback espelha o `app.json` para clone limpo.
   - O `.obsidian/` não é versionado (config da máquina): o `app.json` muda só no disco; no commit entra o `check-orfaos.py`.
   - Onde mexer: `guides-e-sensores.md:45` (contagem de testes do Reco) e `:72-82` (Transcrever com o Reco); `vocabulario-curto.md:60` (linha "reco").
   - O comando `python tools/transcrever.py "<arquivo>"` **não muda** (D6). Os guias só mudam se a Fase 6 mudou algo no modo de chamar, ou se descrevem o app como Tkinter.
   - Conferir a contagem com `ls tools/test_*.py | wc -l` antes de trocar o "Reco 10" de `guides-e-sensores.md:45`.
   - `Reco/dist/` **fica** nas duas listas enquanto a pasta do exe velho existir no disco (Pendente). Os dois arquivos andam juntos: o script compara um com o outro (`check-orfaos.py:141-144`).
   - Ver o `MAPA.md` de `dosxnjos/harness-conceitos`: lista de caminhos de um checador não muda conceito, então só atualizar lá se o mapa citar esses arquivos.
   - Commit no repo `C:\Dev` (`dosxnjos/dev-diretrizes`) por pathspec, só os arquivos tocados.

13. [ ] Marcar os 6 roadmaps (lista abaixo) com `> Superado em <data>` ou `> Atualizado em <data>` sob o H1 — **prova:** `for f in <os 6>; do head -10 "$f" | grep -c "^> \(Superado\|Atualizado\) em .*melhoria-reco-em-rust-fase-"; done` → `1` seis vezes
   **reprova se:** algum arquivo dá `0` (a linha falta, não linka a fase ou caiu abaixo da linha 10, onde ninguém lê) ou `2` (duplicada).
   - A Fase 0 já deixou em cinco deles `> Atualizado em 2026-11-11: ver roadmap/2026-11-11-melhoria-reco-em-rust.md …` (link do índice, não de fase). Essa linha **fica**; a da Fase 7 entra acima dela, e a prova só conta a que linka um `…-fase-N.md`.
   - Os 6: `roadmap/2026-10-02-melhoria-modularizacao.md`, `roadmap/2026-08-13-melhoria-modo-nota-speech-to-ia.md`, `roadmap/2026-08-21-salto-de-alinhamento-sob-carga.md`.
   - E: `roadmap/2026-09-30-melhoria-dispositivo-auto.md`, `roadmap/2026-07-29-melhoria-transcricao-ao-vivo-vad-diarizacao.md`, `roadmap/2026-08-02-melhoria-evolucao-mac-tela-meet.md`.
   - Cada linha diz o que aconteceu e linka a fase deste roadmap que absorveu (Mac/Meet: esta Fase 7).
   - Modularização: `> Superado em <data>`: a reescrita a tornou obsoleta; a UI saiu do `reco.py` na Fase 7. Vale só o mapa de fronteiras (índice, "O que NÃO fazer").
   - Modo nota: `> Superado em <data>`: as Fases 2 e 3 (botão, `nota_dir`) foram feitas na Fase 3 deste roadmap. Conferir no relatório da Fase 3 antes de escrever.
   - Salto: `> Superado em` só se o relatório da Fase 5 mostrar os gates verdes (pior janela < 10 ms e o teste sob carga D1). Senão, `> Atualizado em` com o que falta.
   - Dispositivo Auto: `> Atualizado em`: Fase 1 entregue no motor do app novo; Fase 2 (vigia) é especificação da Fase 5; Fase 4 (fone QCY) segue valendo em qualquer motor.
   - Ao vivo: `> Atualizado em`, dizendo se o teste de 20 min foi feito na Fase 5 ou segue pendente do Gabriel. A linha `> Estacionado em 2026-10-01` existente fica.
   - Mac/Meet (`2026-08-02-...`): `> Atualizado em`: a interface do desenho era Tk e saiu; Mac segue fora (D9). Antieco não muda.
   - Regenerar o índice: `python C:\Dev\cerebro\scripts\gerar_indice_roadmaps.py roadmap --escrever`.
   - Limite do gerador: ele só conhece `MOVIDO` no topo (`gerar_indice_roadmaps.py:50`); um roadmap superado com `[ ]` segue em "Ativos". Abrir issue no `dosxnjos/dev-diretrizes` pedindo o status "superado" (F7-D4).

14. [ ] Propagar às issues abertas do `dosxnjos/reco`: fechar as superadas com motivo e comentar as que ficam — **prova:** `gh issue list -R dosxnjos/reco --state open --search '"melhoria-modularizacao.md" in:body' --json number --jq length` → `0`
   **reprova se:** sobra issue aberta da modularização (ou, com `'"melhoria-modo-nota-speech-to-ia.md" in:body'`, do modo nota), ou uma que fica aberta não tem comentário da data da fase (`gh issue view <n> --comments`).
   - A frase entre aspas duplas é obrigatória: sem ela, `modularizacao in:body` casa 11 issues em 11/11/2026 (#8, #12–#19, #25, #26), inclusive as que este passo manda não mexer; com ela, só #12–#15.
   - Busca: `gh issue list -R dosxnjos/reco --state open --limit 100 --json number,title,body` e `--search '"<nome do arquivo do roadmap>" in:body'` para cada um dos seis do passo 13.
   - Mapa em `7c5c1a1` (refazer a busca, o estado muda): #12–#15 modularização → `gh issue close <n> -R dosxnjos/reco --reason "not planned" --comment "..."`.
   - #16 modo nota → `--reason completed`, citando a Fase 3. #8 (build da Fase 1 do Auto) → `completed` se o Auto está no motor do app novo; o build velho deixou de existir.
   - #17–#20 salto (A–D) e #9 (vigia) → `completed` só com o gate do relatório da Fase 5; senão, comentário apontando a fase que absorve.
   - #21 (salto, Fase E), #10 e #11 (Auto, provas) → comentário com o contexto novo; ficam abertas. #11 (fone) vale em qualquer motor.
   - Issue cujo corpo cite `tray.py`, `App`, `build.ps1` ou a janela Tk (procurar no JSON) recebe comentário com o lugar novo. #22–#26, #28 e #29 não citam a UI velha em `7c5c1a1`: não mexer.
   - Texto dos comentários em pt-BR, sem caminho de máquina nem host (repo público), com link para o roadmap.

15. [ ] Atualizar as docs do Reco (README, CLAUDE, ARQUITETURA, TOOLS, _INDICE; seções abaixo) — **prova:** `git grep -n -i "tkinter\|build.ps1\|reco.spec\|setup.ps1\|tray.py\|App._icon" -- README.md CLAUDE.md docs/ ':!docs/armadilhas.d'` → 0 linhas, salvo as datadas "até <data>"
   **reprova se:** alguma doc ainda ensina o build velho, a janela Tk ou o `App._icon()` como coisa viva: doc desatualizada é armadilha nova.
   - `README.md`, EN e PT: "Run from source" (`:76-88`), "Build" (`:89-99`), "How it works" (`:100-114`) e os espelhos em português (`:189-229`).
   - `docs/ARQUITETURA.md`: § Build (`:14-29`), instância única (`:155-160`, cita `tray._wnd_proc`), § Ícones Lucide (`:228-270`).
   - A prova exclui `docs/armadilhas.d/`: entrada antiga ali é histórico datado e não se edita.
   - `CLAUDE.md`: a abertura (`:3-8`, "Tkinter" e modularização) vira app Tauri + motor Python em 1–3 linhas com link; § Ícones (`:66-74`) aponta para o design do app novo. Teto: `wc -c CLAUDE.md` ≤ 6144 (hoje 5210).
   - `docs/TOOLS.md`: entram `check_superficie.py` e `check_i18n.py` (hoje fora da lista, já com o escopo novo); `gerar_icones.py` entra, ou não, conforme F7-D3.
   - Listar todo `tools/*.py` fecha o item 4 da issue #27 (faltavam também `exp_alvo.py`, `exp_ao_vivo.py`, `exp_contexto.py`, `test_model_dir.py`, `visoes.py`).
   - Fechar a #27 só se os 4 itens do "Detalhe" dela estiverem feitos (o 2, typo da § Build, cai na reescrita da § Build); senão, comentar o que ficou.
   - `docs/_INDICE.md:30-34` ("Ainda não existe" `docs/MODULOS.md`, da modularização) sai.
   - Armadilha nova só se a fase achou uma (ex.: o persist do config do passo 4): `python tools/visoes.py novo "título"`; nunca editar `docs/ARMADILHAS.md`.
   - Ícones (F7-D3): `assets/icons/`, `assets/icons_src/` e `tools/gerar_icones.py` saem só se `git grep -n "assets/icons" -- app engine` voltar vazio.

16. [ ] Regressão final contra a base e fechamento: repetir o passo 2 em `temp/fase7/depois/` — **prova:** `cd temp/fase7 && cmp depois/clip.wav.txt base/clip.wav.txt && cmp depois/gravacao_reco_base.mp3.txt base/gravacao_reco_base.mp3.txt && echo IGUAL` → `IGUAL`
   **reprova se:** algum `cmp` acusa diferença (a remoção mexeu no caminho da transcrição que o coletor e as sessões usam) ou um teste verde na base ficou vermelho.
   - Contrato headless (D6): o `Reco.exe` do casco instalado com `--transcribe temp/fase7/clip.wav` faz nascer `temp/fase7/clip.txt` (passo 8). Sem isso, a fase não fecha.
   - Também: `test_encoder` → `TUDO OK`; `test_model_dir` → `OK`; `test_dispositivo_auto` igual à base; `check_i18n` → `OK`; `check_superficie` → `OK`; smoke do motor com as mesmas linhas `hello ok`/`ready` (tempos à parte); `testa_canais` → `ok — 0 falhas`.
   - `test_alinhamento` com o mesmo vermelho do caso 8. Se ficou verde ou mudou de caso, investigar antes de fechar: nada nesta fase devia mexer no alinhamento.
   - Hub `C:\Dev\cerebro\projetos\reco.md`: a descrição (`:8-13`, "Tkinter", "PyInstaller", "modularização") e "Roadmaps em voo" (`:58-79`) refletem o app novo. Nova linha em "Estado agora" com link para este md.
   - Diário: fragmento em `C:\Dev\cerebro\pessoal\diario/<data>/<HHMM>-<sid8>-reco-fase-7.md` (molde `diario/_TEMPLATE.md`) e, de `C:\Dev`, `python cerebro/scripts/compilar_fragmentos.py raiz --escrever` (`raiz` é subcomando; o padrão já é `C:\Dev`, lado pessoal).
   - Relatório da fase em `roadmap/2026-11-11-melhoria-reco-em-rust.d/relatorio-fase-7-<sid8>.md`, com linhas do `reco.py` antes e depois, tamanho do motor antes e depois, issues fechadas e comentadas.
   - Marcar `[x]` nos 16 passos deste md e escrever "feita em <data>" com o link do relatório na linha da Fase 7 da tabela do índice (a tabela não tem caixa de marcar). Push dos três repos (Reco, central, `C:\Dev`).

## Decisões da fase

| id | decisão | motivo | confiança | reverte se |
| --- | --- | --- | --- | --- |
| F7-D1 | O `reco.py` fica como núcleo importável (não vira pacote nem muda de nome) | 23 scripts de `tools/`, o motor e a sentinela da central apontam para ele; renomear quebra sem ganho | alta | outra fase cortar o núcleo em módulos (aí a sentinela segue o literal, passo 10) |
| F7-D2 | `python reco.py` sem flag avisa em stderr e sai com código 2; `--selftest` e `--transcribe` ficam | ninguém de fora chama o ramo da janela (grep em central, cerebro, lacre, albion e skills); o headless é contrato D6 | alta | aparecer um chamador que espere a janela |
| F7-D3 | Ícones PNG, fontes SVG e `gerar_icones.py` saem só se o app novo não os usar | servem ao `App._icon()` (`reco.py:3066-3079`); o app novo tem design próprio (D5) | média | o design do app novo quiser as mesmas fontes SVG (aí movê-las para `design/`) |
| F7-D4 | Não ensinar o status "superado" ao gerador de índice nesta fase; abrir issue | o gerador é da casa (`cerebro/scripts`), serve a todos os projetos e mexer nele é mudança de harness | média | o índice "Ativos" enganar uma sessão antes de a issue andar |
| F7-D5 | Sentinela com lista de alvos configurável (`reco.py` e, com portão aberto, o `.rs`), que falha se um alvo some ou a lista vem vazia | o `if os.path.isfile` de hoje vira no-op calado (diagnóstico 1, § 5); a variável prova a falha | alta | a central trocar a sentinela por teste do coletor |
| F7-D6 | A pasta `dist\Reco\` do exe velho e a cópia `Reco-reserva` (F4-D3) ficam no disco, e `Reco/dist/` fica no filtro de órfãos | é reserva física e está fora do git; apagar é ação do dono | alta | o Gabriel autorizar a remoção (Pendente) |

## Pendente (dono: gabriel)

- **Apagar o app velho da máquina:** a pasta `C:\Dev\Reco\dist\Reco\` (859 MB) e o atalho antigo do Menu Iniciar com Ctrl+Shift+R, se ainda apontar para ela.
  - Recomendação: apagar depois de uma semana usando só o app novo, sem volta ao velho.
  - Ao apagar, tirar `Reco/dist/` de `check-orfaos.py` e do `.obsidian/app.json` (os dois juntos).
  - O repasse de `Reco.exe --transcribe` pelo casco já é condição para fechar esta fase (passos 8 e 16), então não espera a remoção.
  - No commit em que `dist\Reco\` **e** `%LOCALAPPDATA%\Reco-reserva` tiverem sumido, o motor passa a chamar `load_config(persist=True)` ao subir (passo 4; F2-D6 deixa de valer sem exe velho abrível), com recompilação.
- **Apagar a cópia `%LOCALAPPDATA%\Reco-reserva`** (exe velho + `models`, F4-D3) quando a reserva não for mais necessária: junto com a pasta `dist\Reco\`, pelo mesmo critério de uma semana sem volta ao velho.
- **Releases antigos no GitHub** (o exe Tk tem downloads públicos): manter publicados como histórico (recomendado, reversível) ou marcar como obsoletos com link para o instalador novo.

## O que esta fase NÃO faz

- Não mexe em captura, alinhamento, AEC, anti-loop, VAD, encoder nem no formato do MP3: só remove UI e build e propaga (exceção: o repasse do `--transcribe` no casco, passo 8, se faltar).
- Não muda o contrato do `tools/transcrever.py` (caminho, saída, nomes `x.txt`/`x.mp3.txt`/`<arq>.<ext>.txt`) nem o formato do `~/.reco_config.json`.
- Não apaga `dist\Reco\`, `%LOCALAPPDATA%\Reco-reserva`, releases do GitHub nem o acervo de gravações.
- Não corta o núcleo do `reco.py` em módulos (a modularização está superada; o núcleo segue num arquivo).
- Não mexe no `MLXTranscriber` (Mac congelado, D9) nem nos roadmaps antieco e Meet além da linha de topo.
- Não executa o teste de 20 min do ao vivo nem a prova do fone QCY: só registra onde estão.

## Gatilho que fecha

- Passo 16 verde: as duas transcrições idênticas à base, os testes como na base e o motor recompilado sem Tcl/Tk.
- `python -c "import sys, reco; ..."` sem `tkinter`, `PIL` e `tray` (passo 7) e `wc -l reco.py` bem abaixo de 5213.
- A sentinela da central reprova com qualquer alvo inexistente na lista e passa com os alvos reais (passo 11).
- O casco instalado repassa `Reco.exe --transcribe` ao motor e o `.txt` nasce (passos 8 e 16; contrato D6).
- Zero issue aberta da modularização e do modo nota; os seis roadmaps com a linha de topo; docs, guias e hub sem instrução do app velho.
- É a última fase do roadmap: ao fechar, a linha da Fase 7 do índice diz "feita em <data>" e o roadmap inteiro sai de "em voo" no hub.

## Premissas não verificadas

- As Fases 2 a 6 têm md escrito, mas nenhuma foi executada quando este md nasceu. Supõe-se que a execução siga o md delas:
  - o motor mora em `engine/reco_engine/`, importa o `reco`, sai em `engine/dist/reco-engine/` e tem `python engine/build.py --smoke` (Fase 2, passos 14 e 15);
  - o motor atende `--transcribe` (Fase 2, passo 12); o casco repassa (Fase 3, passo 7; Fase 4, P25): o passo 1 confirma e o passo 8 só age se tiver regredido;
  - a Fase 4 registra a aprovação do Gabriel no relatório do sidecar.
- Não li o código de `engine/` nem de `app/` (não existem em `7c5c1a1`). Tudo o que o passo 4 supõe sobre o motor (`config.set` com releitura crua, não usar o `App`) é conferido por grep na hora.
- Os números de linha do `reco.py` são do `7c5c1a1`. Se as Fases 2 a 6 mexerem no arquivo, reler por símbolo (`class App`, `class VuMeter`, `if __name__`).
- Supõe-se que `tools/transcrever.py` continua no Python depois da Fase 6. Se o portão abriu, ele é o invólucro do exe Rust (Fase 6, passo 22): o passo 3 o cobre e os passos 10 e 11 incluem o `.rs` na lista.
- Conferido na auditoria (11/11): o `gerar_indice_roadmaps.py` recebe a pasta como argumento posicional (`:305`), então `roadmap` relativo, rodado de `C:\Dev\Reco`, serve.
- O mapa das issues (#8 a #29) é de `7c5c1a1`, lido com `gh issue list` em 11/11/2026; o estado vai mudar até a fase rodar.
