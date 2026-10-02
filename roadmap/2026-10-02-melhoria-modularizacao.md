# Roadmap de melhoria: modularização do reco.py (2026-10-02)

Risco: dado (o corte toca a captura e o `~/.reco_config.json`; um nome que o
`DualRecorder` deixa de enxergar grava o canal do sistema mudo ou desalinhado
sem erro nenhum, e a fala do outro lado da reunião se perde)

Card-mãe: `ce6f4221b9086` (mapa de modularização de todos os projetos).
Arquiteto: opus 5.5 com advisor, sessão `ca4a025d`, 02/10/2026. Índice do lote:
[C:\Dev\roadmap\2026-10-02-melhoria-modularizacao-projetos-menores.md](../../roadmap/2026-10-02-melhoria-modularizacao-projetos-menores.md).

## Contexto e motivação

O Gabriel pediu (01/10) para modularizar **antes de seguir construindo**. O
Reco tem tudo num arquivo só: `reco.py` com 5.059 linhas no `HEAD` (o tree de
02/10 tem mais 132 linhas sujas do modo nota). Três roadmaps abertos mexem nele
ao mesmo tempo:

- [2026-08-13-melhoria-modo-nota-speech-to-ia.md](2026-08-13-melhoria-modo-nota-speech-to-ia.md)
  (card `6d5bebccb1cd`: commitar as +132 linhas já auditadas e fazer o build);
- [2026-09-30-melhoria-dispositivo-auto.md](2026-09-30-melhoria-dispositivo-auto.md)
  (opções "Auto" de dispositivo, migração de config);
- [2026-08-21-salto-de-alinhamento-sob-carga.md](2026-08-21-salto-de-alinhamento-sob-carga.md)
  (cards `c54006ae6da2e`, `c0af7eb76656d`, `c9e29ab1a92d8`, `c2fbf9935e4cc`,
  `c82ee10b8e4e4` e `c59dd3610bb93`, todos em `proximo` desde 31/08; ancorado
  em `reco.py:1068/1360/1676/2190`, em `ALIGN_*`, `_pump` e `cancel_echo`).

**Ler antes de começar:**

- `C:\Dev\Reco\CLAUDE.md` (recompilar com `build.ps1` depois de toda mudança;
  opção nova em `_CFG_DEFAULTS` mais `_migra_config`).
- `docs/ARQUITETURA.md` (o que não é acidente: `_pump`, encode em streaming,
  AEC só na transcrição, anti-loop) e `docs/TOOLS.md`.
- `docs/ARMADILHAS.md` inteiro antes de tocar captura ou transcrição.
- O hub `C:\Dev\cerebro\projetos\reco.md`.

## O que o pedido não dizia

- **Feito (vira passo `+`):** propagação para os roadmaps abertos. Porquê: os
  cards de alinhamento citam `reco.py:<linha>`; depois do corte, o executor
  editaria o arquivo errado e a fachada esconderia o erro.
- **Feito (`+`):** corrigir os monkeypatches dos testes no mesmo commit que move
  o nome, com prova que **reprova** apontando para o módulo velho. Porquê:
  `reco.ALIGN_RECHECK_S = 20.0` deixaria de afetar o `DualRecorder` em silêncio.
- **Feito (`+`):** `check_i18n.py` passa a varrer todos os `.py`. Porquê: hoje
  `ARQUIVOS = [RAIZ / "reco.py", RAIZ / "tray.py"]` (L17); com as strings
  espalhadas daria falso verde.
- **Feito (`+`):** atualizar o `CLAUDE.md` do projeto ("Todo o código vive em
  `reco.py` (um arquivo só)" deixa de ser verdade) e o `docs/ARQUITETURA.md`.
- **Proposto:** nada que dependa do Gabriel; a ordem frente aos cards de
  alinhamento é decisão técnica, registrada abaixo.
- `correção:` a leitura de 02/10 dizia "mais de 30 scripts em `tools/` importam
  `reco`"; medido: **23**.

## Alvo e estado atual

`reco.py` (linhas medidas no tree sujo de 02/10; reconferir por `grep` antes de
cada passo, porque o modo nota soma linhas):

| bloco | símbolos | linhas aprox. |
| --- | --- | --- |
| tema | `apply_theme` (muta `BG`, `CARD`, `ACCENT`... via `global`), fontes `SEG*` | 30-100 |
| config | `_CFG_DEFAULTS`, `CFG_MIGRACAO`, `_migra_config`, `load_config`, `save_config` | 100-225 |
| i18n | `LANG` (global mutável), `_TR_EN`, `t`, `tf`, `_init_lang` | 265-515 |
| caminhos | `_user_data_dir`, `_bundled_models_dir` | 543-560 |
| E/S de áudio | `decode_16k`, `segmentar_por_vad`, `_open_mp3`, `MP3Writer`, `NoAudioStream`, `extract_mp3` | 600-860 |
| DSP | `_alinhar_canais`, `dominancia_sistema`, `cancel_echo` | 880-1080 |
| modelos | `_find_model_dir`, `ensure_ov_model`, `resolve_device`, atualização do app | 1120-1300 |
| captura | dispositivos, `ALIGN_*`, `estimar_offset`, `DualRecorder` (`_pump`) | 1360-1915 |
| transcrição | `OVTranscriber`, `LiveTranscriber`, `MLXTranscriber`, `make_transcriber` | 1918-2655 |
| UI | `VuMeter`, `App(tk.Tk)` com ~2.200 linhas | 2659-4975 |
| entrada | `--selftest`, `--transcribe`, mutex de instância | 4975-fim |

Acoplamento medido: 23 scripts de `tools/` importam `reco`; os nomes mais usados
são `OUT_SR`, `MP3_BR`, `name_for_id`, `OUT_CH`, `DualRecorder`, `MP3Writer`,
`ALIGN_RECHECK_S`, `ALIGN_Q_MIN`, `estimar_offset`, `OVTranscriber`,
`load_config`, `decode_16k`, `cancel_echo`, `_alinhar_canais`. O `reco.spec`
(PyInstaller) tem `reco.py` como entrada (L45); import estático de módulo irmão
entra no exe sozinho, import tardio pode faltar.

## Diagnóstico

### O que está bom (não mexer)

- `tray.py` separado e importado tarde (`import tray as _tray`, L503).
- As cinco regras de `CLAUDE.md` § "o que não é acidente": o corte move código,
  não muda comportamento.
- A suíte de `tools/test_*.py` (10 scripts) existe e roda sem hardware em boa
  parte.

### O que está frágil ou custando

- **Monkeypatch por atributo de módulo:** `tools/test_alinhamento.py` L172
  (`_reco.ALIGN_RECHECK_S = 20.0`) e `tools/test_model_dir.py` L32-33
  (`reco._bundled_models_dir`, `reco._user_data_dir`). Depois do corte, o patch
  em `reco` não alcança o módulo novo e o teste testa o valor errado.
- **Estado global mutável lido por nome nu:** `global LANG` (L478 e L3379) e
  `global BG, CARD, ...` em `apply_theme` (L73); `BG` aparece 65 vezes no
  arquivo. `from tema import BG` congelaria a cor e a troca de tema pararia.
- **Duplo import do `__main__`:** `reco.py` roda como `__main__`; um módulo novo
  que faça `import reco` carrega uma segunda cópia (segundo mutex, segundo
  tema, segundo `LANG`). Regra: nenhum módulo novo importa `reco`.
- **`test_alinhamento.py` já está vermelho** (C0, commit `efc23b8`): a régua é
  "mesma saída da linha de base", não "verde".
- **Tree sujo:** +132 linhas do modo nota em `reco.py`, `docs/ARMADILHAS.md` e
  `roadmap/README.md` modificados, `roadmap/2026-09-30-...` não rastreado.

### Conceitos aplicados

`via-negativa`: o corte não muda nenhum comportamento e não corrige o eco junto;
`falacia-da-previsao`: o porte para Mac (MLX) não dita o desenho, só a ordem
(transcrição isolada ajuda o porte, sem módulo especulativo para ele).

## Decisões tomadas pelo fable

| decisão | motivo | confiança | o que reverteria |
| --- | --- | --- | --- |
| Módulos irmãos na raiz e `ui/` para o App; `reco.py` fica como entrada e fachada que re-exporta os nomes que `tools/` usa | não quebra os 23 scripts nem o `reco.spec` | alta | os scripts de `tools/` migrarem todos para os módulos novos (aí a fachada encolhe) |
| Caminhos (`_user_data_dir`, `_bundled_models_dir`) vão para `modelos.py`, junto de `_find_model_dir` | medido: só o código de modelo e o `ovcache` do `OVTranscriber` os usam; o patch do `test_model_dir` fica num módulo só | alta | config passar a gravar em `_user_data_dir` |
| Tema vai para `ui/tema.py` na fase do App, não antes | é lido só pela UI, 150+ leituras por nome nu; mover antes obrigaria a reescrever o App duas vezes | alta | outro módulo fora da UI precisar de cor |
| Ordem: folhas, motor (modelos, DSP, captura, transcrição), App por último | o App depende do motor; mover o App primeiro forçaria `ui/` a importar `reco` (duplo import do `__main__`) | alta | nenhuma |
| O motor (Fase 2) corta **antes** dos cards A-C do alinhamento, desde que nenhum esteja `em_curso`, com propagação obrigatória no md de 21/08 | os cards estão parados há um mês (C bloqueado por C0 vermelho); esperar trava a modularização sem prazo; cortar depois exigiria que eles editassem um arquivo de 5 mil linhas | média | o Gabriel ou a Andressa priorizarem o alinhamento agora, ou um card A-C entrar `em_curso`: aí a Fase 2 espera ele fechar |
| Corte e correção em commits separados | o defeito de eco segue ativo; misturar torna o diff impossível de revisar | alta | nenhuma |

## Roadmap

Regras de todos os passos:

- `python -c "import reco"` sem erro, `build.ps1` e `dist\Reco\Reco.exe --selftest`
  ao fim de cada fase (o `--selftest` grava `%TEMP%\reco_selftest.txt`).
- Nenhum módulo novo faz `import reco` ou `from reco import`.
- Leitura de estado mutável sempre por atributo de módulo (`i18n.LANG`,
  `tema.BG`), nunca `from x import NOME`.
- Ao mover um nome, `reco.py` ganha o re-export explícito
  (`from audio_io import decode_16k, MP3Writer, ...`), nunca `import *`.

### Fase 0: pré-requisitos e rede de proteção (nenhuma linha de código muda)

1. [ ] **Tree limpo.** Conferir que o card `6d5bebccb1cd` (modo nota) fechou e
   que nenhum card Reco está `em_curso` (MCP `mcp__central__buscar_cards
   projeto=Reco status=agora`).
   — **prova:** `git -C C:\Dev\Reco status --short reco.py tray.py` → vazio
   **reprova se:** `M reco.py` (o corte misturaria o modo nota).
2. [ ] **Linha de base.** Em `C:\Dev\Reco`, rodar e guardar a saída em
   `temp/modularizacao/antes/` (o `temp/` é ignorado pelo git, `.gitignore`
   L25): `tools/test_encoder.py`, `test_antiloop.py`, `test_live.py`,
   `test_model_dir.py`, `test_alinhamento.py` (vermelho esperado, C0),
   `check_i18n.py`, `test_gravacao_alinhada.py 30`, `test_gravacao_real.py`,
   `build.ps1` e o `--selftest`. Inventário de nomes:
   `python -c "import reco; print('\n'.join(sorted(n for n in dir(reco) if not n.startswith('__'))))" > temp/modularizacao/antes/nomes.txt`.
   — **prova:** `ls temp/modularizacao/antes | wc -l` → 8 ou mais, e
   `nomes.txt` não vazio
   **reprova se:** faltar a saída de algum teste (sem base, "mesma saída"
   não se prova).
3. [ ] **Script de conferência.** Criar `tools/conferir_fachada.py`: importa
   `reco`, lê `temp/modularizacao/antes/nomes.txt` e lista os nomes que
   sumiram; e falha se algum `.py` da raiz ou de `ui/` (exceto `reco.py`)
   contiver `import reco` ou `from reco`.
   — **prova:** `python tools/conferir_fachada.py` → `0 nomes faltando, 0 imports de reco`
   **reprova se:** com um nome apagado de propósito numa cópia temporária, o
   script continuar dizendo 0 (testar uma vez e desfazer).

### Fase 1: folhas sem estado de UI (audio_io, i18n, config)

1. [ ] **`audio_io.py`.** `OUT_SR`, `OUT_CH`, `MP3_BR`, constantes `EXTRACT_*`,
   `decode_16k`, `segmentar_por_vad`, `agrupar_segmentos`, `_open_mp3`,
   `MP3Writer`, `NoAudioStream`, `extract_mp3`. Re-export em `reco.py`.
   — **prova:** `python tools/test_encoder.py` com a mesma saída da linha de
   base e `python tools/conferir_fachada.py` → `0 nomes faltando`
   **reprova se:** `MP3Writer` sumir do inventário ou o teste do encoder mudar.
2. [ ] **`i18n.py`.** `LANG`, `_TR_EN`, `t`, `tf`, `_init_lang`. O
   `App._set_language` (hoje `global LANG`, L3379) passa a fazer
   `i18n.LANG = code`; `_init_lang` idem. `check_i18n.py`: `ARQUIVOS` (L17)
   vira todos os `.py` da raiz e de `ui/`, e `_tr_en()` (L111) carrega
   `i18n.py` em vez de `reco.py`.
   — **prova:** `python -c "import i18n; i18n.LANG='en'; print(i18n.t('Gravar'))"`
   → `Record` (chave medida em `_TR_EN`, L272), e
   `grep -n "global LANG" reco.py` → vazio, e `python tools/check_i18n.py`
   igual à linha de base
   **reprova se:** o `t()` devolver o português com `LANG='en'`, ou o
   `check_i18n` achar menos strings que antes.
3. [ ] **`config.py`.** `_CFG_DEFAULTS`, `CFG_MIGRACAO`, `_migra_config`,
   `load_config`, `save_config`. Fazer **depois** do dispositivo-auto, que mexe
   em `_CFG_DEFAULTS` e `_migra_config`.
   — **prova:** com cópia do `~/.reco_config.json` em `temp/`, rodar
   `python -c "import config, json; print(json.dumps(config.load_config(), sort_keys=True))"`
   antes e depois do passo e comparar
   **reprova se:** a saída mudar (migração ou default perdido).
4. [ ] **Build e gravação real automatizada.** `build.ps1`, `--selftest` e
   `python tools/test_gravacao_alinhada.py 30` (toca fala pelo alto-falante
   padrão enquanto grava pelos dispositivos padrão e mede o atraso; não precisa
   de pessoa, só da máquina com áudio de saída ativo). Rodar o mesmo comando na
   Fase 0 para ter a linha de base.
   — **prova:** `reco_selftest.txt` igual à linha de base e o gate do teste
   (`|atraso residual| < 160 amostras`) com o mesmo resultado da linha de base
   **reprova se:** canal do sistema sem sinal ou atraso fora do gate quando a
   linha de base passava.
5. [ ] **+ Propagação.** Nos três roadmaps abertos, linha
   `> Auditado em <data>: decode_16k, MP3Writer, ... moveram para audio_io.py; t/tf/LANG para i18n.py; load_config para config.py`.
   — **prova:** `grep -l "audio_io.py" roadmap/2026-08-13-*.md roadmap/2026-08-21-*.md roadmap/2026-09-30-*.md | wc -l` → `3`
   **reprova se:** menos de 3.

### Fase 2: motor (modelos, DSP, captura, transcrição)

Pré-requisito: Fase 1 fechada e nenhum card de alinhamento (A-E) `em_curso`.

1. [ ] **`modelos.py`.** `_user_data_dir`, `_bundled_models_dir`, `_dir_writable`,
   `MODEL_SENTINEL`, `_find_model_dir`, `ensure_ov_model`, `resolve_device`,
   `ov_available_devices`, `update_model_if_newer`, `check_app_update`. No
   mesmo commit, `tools/test_model_dir.py` L32-33 passa a fazer o patch em
   `modelos._bundled_models_dir` e `modelos._user_data_dir`.
   — **prova:** `python tools/test_model_dir.py` → mesma saída da linha de base
   **reprova se:** com o patch ainda apontando para `reco.` (testar uma vez,
   antes de corrigir), o teste continuar passando: aí ele não prova nada e
   precisa de uma asserção que olhe o caminho falso.
2. [ ] **`dsp.py`.** `_alinhar_canais`, `dominancia_sistema`, `cancel_echo`.
   — **prova:** `python tools/test_antiloop.py` e os scripts que importam
   `cancel_echo` com a mesma saída da linha de base, e
   `python tools/conferir_fachada.py` → `0 nomes faltando`
   **reprova se:** qualquer saída diferente.
3. [ ] **`captura.py`.** `CHUNK`, `CAPTURE_SR`, `ALIGN_*`, `estimar_offset`,
   `list_capture_devices`, `default_mic_id`, `default_speaker_id`,
   `name_for_id`, `NoAudioCaptured`, `DualRecorder`. No mesmo commit,
   `tools/test_alinhamento.py` L170-210 passa a importar e fazer o patch em
   `captura` (`captura.ALIGN_RECHECK_S = 20.0`).
   — **prova:** `python tools/test_alinhamento.py` com a mesma saída da linha
   de base (vermelho no mesmo ponto do C0)
   **reprova se:** o caso 8 ("gravação longa simulada") mudar de resultado, ou
   se, com o patch em `reco.ALIGN_RECHECK_S`, o caso 8 der a mesma saída que com
   o patch em `captura` (testar uma vez: prova que o patch velho não alcança).
4. [ ] **`transcricao.py`.** Prompts e rótulos de falante, `OVTranscriber`
   (com `_degenerado`/`_generate_sem_loop`), `LiveTranscriber`,
   `MLXTranscriber`, `make_transcriber`.
   — **prova:** `python tools/test_antiloop.py`, `test_live.py` e
   `python tools/transcrever.py` sobre um MP3 curto do acervo com `.txt`
   idêntico ao gerado antes do passo
   **reprova se:** o `.txt` mudar.
5. [ ] **Build, gravação real e propagação.** `build.ps1`, `--selftest`,
   `python tools/test_gravacao_alinhada.py 120` e `python tools/test_gravacao_real.py`
   (duração declarada × gravada), com o mesmo resultado da linha de base. No md de 21/08, uma
   linha `> Auditado em <data>` com a tabela símbolo → módulo (`ALIGN_*`,
   `_pump`, `DualRecorder`, `estimar_offset` → `captura.py`; `cancel_echo`,
   `_alinhar_canais` → `dsp.py`) e a regra "editar o módulo, nunca o
   re-export de `reco.py`".
   — **prova:** `grep -c "captura.py" roadmap/2026-08-21-salto-de-alinhamento-sob-carga.md` → 1 ou mais
   **reprova se:** 0 (os cards A-E editariam o lugar errado).

### Fase 3: App em `ui/` (por último; assistida)

A conferência de cada tela é clique na interface Tk, sem automação no projeto:
precisa do Gabriel na máquina, ou de uma sessão que ele acompanhe.

1. [ ] **`ui/tema.py` e `ui/widgets.py`.** `apply_theme`, as cores e as fontes
   `SEG*`; `VuMeter` e a escala de ganho. Toda leitura de cor no App vira
   `tema.BG` (etc.).
   — **prova:** `grep -nE "(^|[^.A-Za-z_])(BG|CARD|ACCENT|TEXT|MUTED)\b" ui/*.py reco.py`
   → só as definições em `ui/tema.py`; e trocar de tema no app muda as cores
   na hora
   **reprova se:** sobrar leitura por nome nu (cor congelada).
2. [ ] **App em mixins, uma tela por passo.** `ui/gravacao.py` (gravação e
   modo nota), `ui/transcrever.py`, `ui/biblioteca.py` (com o resumo IA via
   `claude -p --model sonnet`), `ui/converter.py`, `ui/bandeja.py`, montados em
   `ui/app.py`. Cada tela é um commit, com `build.ps1` e uso real daquela tela.
   — **prova:** por tela, o fluxo dela no exe (gravar e parar; transcrever um
   arquivo; abrir a biblioteca e gerar resumo; converter; bandeja gravar e
   parar)
   **reprova se:** botão sem ação ou exceção no log do app.
3. [ ] **Fechamento.** `reco.py` com a entrada (`--selftest`, `--transcribe`,
   mutex) e os re-exports; `wc -l reco.py` abaixo de 400.
   — **prova:** `python tools/conferir_fachada.py` → `0 nomes faltando, 0 imports de reco`,
   e todas as saídas da linha de base iguais
   **reprova se:** qualquer diferença.
4. [ ] **Docs.** `CLAUDE.md` (trocar "Todo o código vive em `reco.py`" pelo mapa
   de módulos em 1-3 linhas com link), `docs/ARQUITETURA.md` (tabela módulo →
   responsabilidade), `docs/ARMADILHAS.md` (duplo import do `__main__`;
   monkeypatch no módulo dono; estado mutável por atributo).
   — **prova:** `grep -c "um arquivo só" CLAUDE.md` → `0`
   **reprova se:** 1.

## Cards deste roadmap

A sessão-mãe cria. Todos: `projeto: Reco`, `roadmap` = este md, `risco: ["dado"]`.
Ids conferidos no board em 02/10: modo nota `6d5bebccb1cd` (`proximo`); dispositivo-auto
Fase 0 `c7a92e98d9748` (destrava o tree do modo nota) e Fase 3 `c5c0e64bb55c8` (commit), ambos
`proximo`; a Fase 4 de lá (`cde8bf98a2853`, fone do Gabriel, `esperando`) não bloqueia o corte.

Criados em 02/10 (sessão `ca4a025d`, filhos do card-mãe `ce6f4221b9086`):

| fase | card | título | depende de |
| --- | --- | --- | --- |
| 0 | `cd2edd29532b5` | Reco: modularização — Fase 0: pré-requisitos e rede de proteção | `6d5bebccb1cd`, `c7a92e98d9748` |
| 1 | `c4b056f69190a` | Reco: modularização — Fase 1: folhas (audio_io, i18n, config) | `cd2edd29532b5`, `c5c0e64bb55c8` (o passo 1.3 mexe no que o dispositivo-auto mexe) |
| 2 | `cf11a270ab5d2` | Reco: modularização — Fase 2: motor (modelos, DSP, captura, transcrição) | `c4b056f69190a` |
| 3 | `ca3164379e5c7` | Reco: modularização — Fase 3: App em `ui/` (assistida: sem `fase`, o maestro não abre) | `cf11a270ab5d2` |

Sentido inverso (recomendado, pela decisão "o motor corta antes dos cards A-C"): os cards de
alinhamento ainda em `proximo` (`c54006ae6da2e` A, `c0af7eb76656d` B, `c9e29ab1a92d8` C,
`c2fbf9935e4cc` D e os demais do md de 21/08) declaram `depende_de` a Fase 2 daqui. Sem isso o
maestro pode abrir um deles no meio do corte. **Aplicado em 02/10:** o card A (`c54006ae6da2e`)
ganhou `cf11a270ab5d2` no `depende_de` (anotado no card); B, C e D herdam pela cadeia A → B → C → D.

## Priorização (impacto × esforço × risco)

| item | impacto | esforço | risco | veredito |
| --- | --- | --- | --- | --- |
| Fase 0 | habilita tudo | baixo | nenhum | já |
| Fase 1 folhas | médio | baixo | baixo | logo depois do modo nota e do dispositivo-auto |
| Fase 2 motor | alto (alinhamento e Mac em módulo próprio) | médio | médio-alto | antes dos cards A-C, se nenhum estiver em curso |
| Fase 3 App | alto (2.200 linhas) | alto | médio | por último |

## O que NÃO fazer

- Não corrigir o eco, o salto de alinhamento ou o anti-loop durante o corte.
- Não usar `from i18n import LANG` nem `from ui.tema import BG`.
- Não deixar módulo novo importar `reco`.
- Não apagar a fachada de `reco.py` enquanto houver script em `tools/` que use
  o nome (o inventário manda).
- Não rodar `ruff format` nem reformatar o arquivo inteiro no corte.

## Riscos e pré-requisitos

- Depende do card `6d5bebccb1cd` (commit do modo nota) e do dispositivo-auto
  fecharem antes; se um deles reabrir, a Fase 1 espera.
- A prova de gravação real (`tools/test_gravacao_alinhada.py`) toca a fala
  sozinha e mede sozinha: não precisa de pessoa, mas precisa da máquina com
  saída de áudio ativa (headless numa máquina sem alto-falante dá falso
  vermelho). Só a Fase 3 (cliques na UI Tk) é assistida.
- `test_alinhamento.py` vermelho de origem: a régua é a saída igual, e o
  executor registra no relatório o trecho que já era vermelho.
- Import tardio de módulo novo (dentro de função) pode faltar no exe: o
  `--selftest` e o uso real de cada tela pegam; se faltar, entra em
  `hiddenimports` do `reco.spec` (L31).

## Crítica do advisor

Consultado (modelo superior via `advisor`, 02/10/2026) antes da escrita:
colisão com os roadmaps abertos (aplicado: pré-requisito e propagação por
fase), monkeypatch com prova que reprova (aplicado: 2.1 e 2.3), `check_i18n.py`
L17 (aplicado: 1.2), `reco.spec` e `CLAUDE.md` como passos (aplicado), decisão
explícita sobre o alinhamento (aplicado: tabela de decisões). Contagem de 23
scripts corrigida. A consulta final está registrada no índice do lote.
