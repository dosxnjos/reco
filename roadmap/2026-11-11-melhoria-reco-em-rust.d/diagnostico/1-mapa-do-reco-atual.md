# Mapa funcional do Reco atual (fase de arquitetura, só leitura)

Cobertura: li `CLAUDE.md`, `docs/ARQUITETURA.md`, `docs/_INDICE.md`, `requirements.txt`, `reco.spec` e `build.ps1` inteiros. Também li `reco.py` (5213 linhas) por blocos (UI inteira entre 2853 e 5213), `tray.py` e o README por cabeçalhos. Não rodei o app: `App()` grava o config dele (`load_config(persist=True)`, `reco.py:2869`) e um segundo exe faria a janela aberta dele saltar.

## 1. Funcionalidades visíveis ao usuário

| Função | Onde vive |
|---|---|
| Janela sem moldura, título próprio arrastável, botões minimizar e fechar (glifos Segoe MDL2), fade-in | `reco.py:2853-2941`, `_build` 3146, `_winbtn` 2998, `_minimize` 2987, `_fade` 3025 |
| VU de mic e de sistema; arrastar o medidor ajusta o ganho de 0× a 10×, com o número embaixo ("8,0x") | `VuMeter` 2771-2845, `_build_meters` 3180, `_on_gain` 3206, `_on_gain_release` 3214 |
| Máquina de estados IDLE, RECORDING, PAUSED, STOPPED, BUSY: Gravar, Parar, Pausar, Continuar, cronômetro e ponto piscando | `_build_recording` 3218, `_set_rec_state` 3565, `_tick_timer` 4123, `_blink_dot` 4136 |
| Depois de parar: Salvar (o clique salva e copia o caminho entre aspas), Excluir (vai para a Lixeira), Reproduzir; o hover do Salvar abre menu com 4 itens | 3242-3262, `_show_menu` 3630, `_conclude_*` 4082-4111 |
| Uma única linha de status (`wraplength=300`) e o link "Abrir transcrição" | 3266-3270, `_show_open_txt` 4357 |
| Botão Parar da transcrição disparada pela tela de gravar | 3276, `_rec_show_stop_tr` 4351 |
| Modo ao vivo (rascunho): painel de texto de 8 linhas e passada final ao parar | 3286-3303, `_live_show` 3317, `_run_live_final_pass` 4005, `LiveTranscriber` 2408 |
| Modo nota (só mic, mono, vira `.md`, copia o caminho, apaga o mp3) | `_start_nota` 3813, `_run_nota_final_pass` 4028. **Existe no código, mas não tem entrada para o usuário**: o grep não acha nenhum chamador em `reco.py` nem em `tray.py` |
| Opções em painel que expande: entrada e saída (Auto console, Auto comunicação ou manual), "Atualizar dispositivos", pasta de saída, "Processar em" (AUTO/GPU/NPU/CPU), idioma PT/EN, tema (fundo e destaque escolhidos no colorchooser, mais "Padrão"), caixa do ao vivo, criar ou remover atalho Ctrl+Shift+R | `_build_advanced` 3350-3456, `_toggle_advanced` 3458 |
| Telas exclusivas trocadas por links de texto: Gravações…, Converter…, Transcrever…; o link da tela atual vira "← Gravar" | `_build_links` 3325, `_show_view` 4308 |
| Transcrever: escolher arquivo, Transcrever, Parar, status | `_build_transcribe_section` 4264, `_tr_transcribe` 4826 |
| Biblioteca: busca por nome e por conteúdo do `.txt`, Treeview (Arquivo, Data, Duração, ✓), Reproduzir, Transcrever, Abrir txt, Resumo IA, Excluir, Abrir pasta, duplo clique toca | `_build_library_section` 4385-4451, `_lib_*` 4453-4724 |
| Resumo IA: `claude -p --model sonnet` gera `.resumo.md` | `_lib_resumo` 4663, `PROMPT_RESUMO` 1306 |
| Converter MP4 e outros para MP3 de 16 kHz, mono, 64k | `_build_convert_section` 4726, `_cv_convert` 4783, `extract_mp3` 836 |
| Bandeja: hover mostra a janela sem roubar o foco, clique fixa; menu Gravar/Parar, Pausar/Continuar, Abrir, Sair; balão de aviso; ícone vermelho gravando; o X esconde na bandeja | `tray.py` (menu 197-236), `_init_tray` 4914, `_hover_watch` 5024, `_anchor_to_tray` 4980 |
| Atualizações: o modelo atualiza sozinho pelo Hugging Face; versão nova do app aparece como link | `update_model_if_newer` 1230, `check_app_update` 1274, `_show_app_update` 2956 |
| i18n: frase em PT é a chave, dicionário `_TR_EN` com ~200 entradas | 269-512 |
| Atalho de teclado: **só** o hotkey de um `.lnk` no Menu Iniciar, que abre ou mostra a janela; não existe atalho dentro do app (os únicos `bind` de evento são `<Map>`, combo, Treeview e duplo clique) | `_create_shortcut` 4892 |
| Instância única (mutex mais mensagem `Reco.Show`), CLIs `--selftest` e `--transcribe` | 5120-5213 |

## 2. Camadas reais

| Camada | Linhas | Dependências |
|---|---|---|
| Config, migração, caminhos | 98-256, 578-634 | stdlib |
| Decode e VAD (`decode_16k`, `segmentar_por_vad`, `agrupar_segmentos`) | 635-737 | av, numpy |
| Encoder (`_open_mp3`, `MP3Writer`, `extract_mp3`) | 738-884 | av (libmp3lame em ABR) |
| AEC e diarização (`_alinhar_canais`, `dominancia_sistema`, `cancel_echo`) | 916-1112 | numpy, scipy.signal (correlate, stft) |
| Acelerador e modelo (`resolve_device`, `_find_model_dir`, `ensure_ov_model`) | 1113-1290 | openvino, huggingface_hub |
| Dispositivos (`default_endpoint_id` usa a API privada do soundcard) | 1339-1474 | soundcard==0.4.6, COM |
| Captura (`estimar_offset`, `DualRecorder` com `_pump`, alinhamento e 3 threads) | 1512-2028 | soundcard, numpy, scipy |
| Transcrição (`OVTranscriber`: anti-loop, VAD, merge) | 2030-2407 | openvino_genai, zlib |
| Ao vivo (`LiveTranscriber`) | 2408-2622 | queue, scipy.resample_poly |
| MLX (macOS) | 2623-2728 | mlx_whisper |
| UI (`VuMeter`, `App`) | 2748-5119 | tkinter/ttk (tema clam), Pillow (ícones) |
| Bandeja | `tray.py` 1-329 | só ctypes (Shell_NotifyIcon) |

A UI chama o núcleo direto por callbacks e usa `_post` com a fila `_ui_q` drenada a cada 40 ms (3008-3023). Não existe camada de serviço.

## 3. Por que a janela pula a cada clique (lido, não medido)

**Causa estrutural.** A janela nunca recebe tamanho fixo. O `__init__` posiciona sem dar tamanho (`geometry(f"+{x}+{y}")`, 2932), usa `resizable(False)` e todo o layout é `pack` com conteúdo variável. No Tk, um toplevel sem tamanho explícito acompanha o tamanho pedido pelo conteúdo, então **qualquer** mudança de largura ou altura dos filhos redimensiona a janela, mesmo sem chamar `geometry("")`. As 5 chamadas a `geometry("")` (3323, 3467, 3562, 3602, 4338) desfazem qualquer tamanho que tivesse sido travado e mostram que encaixar a janela no conteúdo é política de projeto: o comentário em 3596 diz "Refit so the window shrinks back".

**Exemplo concreto do clique em Gravar:**
1. `_set_rec_state(RECORDING)` faz `pack_forget` em tudo e reempacota Parar, Pausar, timer e ponto, com outra largura; depois força `width=1, height=1` e `geometry("")` (3565-3602).
2. `_live_show` liga ou desliga o painel de 8 linhas e chama `geometry("")` (3317-3323).
3. O status muda para "Gravando… mic: {nome} · sistema: {nome}  ⚠ …" (3877-3896). Com `wraplength=300` ele quebra em 1 a 3 linhas e a altura muda.

**Fontes de movimento, separadas:**
- **Altura:**
  - status de tamanho variável em todas as telas (3269, 4279, 4296, 4449, 4741, 4755);
  - link "Abrir transcrição" que aparece e some (4357);
  - botão Parar da transcrição (4351);
  - painel ao vivo;
  - painel de Opções (3458);
  - troca de tela: a biblioteca tem Treeview de 8 linhas (4308);
  - `_tr_show_stop` e `_lib_stop` empacotados sob demanda (4343, 4610).
- **Largura:**
  - cada estado tem uma linha de botões diferente (no estado STOPPED o timer ganha `padx=16`);
  - links que mudam de texto ("Opções" ↔ "Ocultar opções", 3462; "Transcrever…" ↔ "← Gravar", 4333-4335);
  - o link "Nova versão" é acrescentado na linha de links (2962);
  - nomes de dispositivo longos nos combos e status.
- **Posição:**
  - `_anchor_to_tray` calcula x,y uma vez só, ao mostrar (4980). Quando a janela cresce depois, o canto superior esquerdo fica parado e a borda de baixo avança por cima da barra de tarefas;
  - `_minimize` alterna `overrideredirect(False)` e `True` (2987-2996), o que põe e tira a moldura do Windows (suspeita de salto visível).
- **Pisca sem redimensionar:**
  - cada hover cria e destrói um `Toplevel` overrideredirect e `-topmost` (`_make_pop` 3607, chamado em todo `<Enter>`);
  - `_rebuild_ui` destrói a UI inteira ao trocar tema ou idioma e reabre as Opções à força (3547-3562).

## 4. Outros problemas de UI/UX no código

- **Sem DPI awareness.** Medido: o grep não acha `SetProcessDpiAwareness` em `reco.py`, e `grep -a -c dpiAware dist/Reco/Reco.exe` dá 0. O `tray.py:300` já compensa a escala. Suspeita forte: com escala de 125% ou 150%, o Windows estica o bitmap e o texto fica borrado.
- **Fontes minúsculas:** 8 pt na maior parte dos rótulos e links (`SEG_XS`, 94); `wraplength` em pixels fixos.
- **Navegação por links de texto com reticências**, sem abas. Trocar de tela é bloqueado durante gravação ou transcrição, e o aviso sai só no status (4310-4318).
- **Ações escondidas no hover** do Salvar: são 4 saídas. O clique simples copia o caminho, o que não é óbvio.
- **Sem barra de progresso** de transcrição, só texto. São 4 variáveis de status separadas, e o erro é cortado em `[:80]`/`[:110]`.
- **Tema livre** (qualquer cor no colorchooser) sobre ttk "clam": combos e Treeview não combinam. A coluna ✓ e o cabeçalho "📄" continuam texto ou emoji por limite do widget.
- **Ganho escondido no gesto de arrastar o VU**: o único indício é o cursor `sb_h_double_arrow`.
- **Sem navegação por teclado nem foco visível** (`tk.Button`, `relief=flat`, `bd=0`). `_drain_ui` engole exceção em silêncio (3016-3019).
- **Auditoria anterior com 17 achados (F1-F17)**: `roadmap/2026-08-12-melhoria-ux-ui-logica.md` é insumo direto para isto.

## 5. Quem depende do `reco.py` fora do app

| Quem depende | Como | O que precisa continuar valendo |
|---|---|---|
| `tools/transcrever.py`, o "ouvido dos agentes" | `import reco`: `make_transcriber`, `load_config`, `is_reco_recording`, `default_output_dir`, `_spk_me`/`_spk_them` (linhas 71-188) | Caminho `Reco/tools/transcrever.py`, stdout com um caminho de `.txt` por linha, exit≠0 em erro, nomes `x.txt` / `x.mp3.txt` / `<arq>.<ext>.txt` |
| Coletor de WhatsApp da central | `central/canais/whatsapp/coletor/src/caminhos.js:12`, `anexos.js` (subprocess) | O mesmo contrato do script |
| Importação de exportações do WhatsApp | `central/tools/importar_exportacoes_whatsapp.py:57` | O mesmo |
| `cerebro/scripts/instagram_post.py:23,86` e a skill instagram-conteudo | subprocess com `cwd=Reco` | O mesmo, com `--lang` |
| `central/canais_comuns.py:35` e `central/tools/testa_canais.py:360-366` | **lê o texto-fonte do `reco.py`** procurando o literal `"(no content recognized)"` (`reco.py:2374, 2721, 4045`) | O literal; se o `reco.py` sumir, o teste vira no-op em silêncio (`if os.path.isfile`) |
| `cerebro/scripts/check-orfaos.py:115` | ignora `Reco/dist/` | Caminho do dist |
| Guias do harness (`cerebro/temas/harness/guides-e-sensores.md:72-82`, `vocabulario-curto.md`) | instrução para agentes | Comando documentado |
| Jarvis | Só existe um **plano** de importar o transcritor como biblioteca (`central/roadmap/2026-08-28-jarvis-voz-e-notebook.md:40,180`); **o código da central não importa o reco** (grep) | — |
| 24 scripts em `tools/` (testes, benchmarks, medições) | importam `reco`: `DualRecorder`, `MP3Writer`, `estimar_offset`, `ALIGN_*`, `cancel_echo`, `_alinhar_canais`, `dominancia_sistema`, `LiveTranscriber`, `default_endpoint_id`... | São os gates de regressão: `medir_aec`, `test_alinhamento`, `test_gravacao_alinhada`, `test_dispositivo_auto`, `test_encoder` e outros |

Também precisam continuar valendo: `~/.reco_config.json` (com `_migracao`), `%LOCALAPPDATA%\Reco\models\whisper-large-v3-turbo-int8-ov` (790 MB, medido), o acervo de mp3, `.txt` e `.resumo.md` com a etiqueta `reco` no nome, o mutex `Local\Reco.SingleInstance` e o `.lnk` com hotkey.

**Se o `reco.py` sumir**, quebram o ouvido dos agentes, o coletor de WhatsApp, as exportações, a skill do Instagram e todos os gates de áudio. A sentinela da central para de vigiar o literal sem avisar.

**Alcance da varredura:** grep por diretório em todo `C:\Dev` e em `~/.claude`. Ficaram de fora `prova-digital-iphone` (estourou o tempo), worktrees `*-wt-*`, `node_modules`, `_arquivo` e `consolidado`.

## 6. Build e distribuição hoje

- **Empacotamento:** PyInstaller em modo onedir (`reco.spec`) com `collect_all` de soundcard, openvino, openvino_genai, openvino_tokenizers, av e huggingface_hub. Leva as máscaras PNG dos ícones e os `.ico`; janela sem console. Roda Python 3.14 (`cp314` no dist).
- **Tamanho:** `dist/Reco` tem **859 MB** (medido). Os maiores: modelo `small` bundlado 245 MB, openvino 225 MB, pyarrow 80 MB, av.libs 63 MB, scipy 73 MB, duckdb 36 MB, numpy.libs 21 MB, PIL 13 MB, cryptography 9 MB.
  - Lixo medido: **pyarrow e duckdb, cerca de 116 MB que o app não usa**. A razão é suspeita: arrastados pelo `collect_all` ou pelo ambiente global, porque o `excludes` não os lista.
- **Modelo:** o bundle leva o `small` só como reserva offline. O modelo usado de fato, o turbo, é baixado na primeira vez para `%LOCALAPPDATA%`. O cabeçalho do `reco.spec` diz "not bundled", e o corpo e o `build.ps1` bundlam: um contradiz o outro.
- **`build.ps1`:** instala `lameenc` (linha ~22), o que contraria a regra do `CLAUDE.md`, e baixa o modelo se ele faltar. Falha com `Reco.exe` aberto.
- **Distribuição:** copiar a pasta inteira. Não há instalador nem assinatura. A atualização do app é só aviso de release no GitHub (`dosxnjos/reco`).
- **Pre-commit:** ruff, gitleaks, trava de 500 linhas por arquivo e de complexidade (`tools/tamanho.json`). O `reco.py` com 5213 linhas está em congelamento ("não cresce").

**Medido ou lido:** linhas, greps, tamanhos (`du`), ausência de `dpiAware` no exe, ausência de chamador de `_start_nota`. **Suspeita:** texto borrado por DPI, salto visível no minimizar, por que o pyarrow e o duckdb entram no bundle.