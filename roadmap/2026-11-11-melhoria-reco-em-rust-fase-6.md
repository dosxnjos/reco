# Reco em Rust: Fase 6 — Transcrição em Rust (spike com portão)

> Índice: [2026-11-11-melhoria-reco-em-rust.md](2026-11-11-melhoria-reco-em-rust.md) · anterior: [fase-5](2026-11-11-melhoria-reco-em-rust-fase-5.md) · seguinte: [fase-7](2026-11-11-melhoria-reco-em-rust-fase-7.md) · Base: Reco `7c5c1a1` (2026-11-11)

## Por que esta fase

- Depois da Fase 5, só a transcrição (Whisper, VAD, AEC, anti-loop, diarização) segue em Python, presa ao `numpy`/`scipy`/PyInstaller.
- O motor C++ é o mesmo (OpenVINO GenAI), então Rust **não** acelera a transcrição (D1); o ganho possível é tirar o Python do caminho.
- O risco é alto e barato de medir: a crate da Intel nunca rodou nesta máquina, e a camada segura não expõe `initial_prompt` nem temperatura.
- Por isso a fase começa por um spike com **portão**: só porta se der o mesmo texto no mesmo tempo. Se fechar, nada muda (D1).
- O `tools/transcrever.py` é infraestrutura da casa (coletor de WhatsApp, importador, skill do Instagram): o caminho do script é contrato (D6).

## O que ler antes

- `C:\Dev\Reco\CLAUDE.md`, o hub `C:\Dev\cerebro\projetos\reco.md` e `C:\Dev\Reco\docs\ARMADILHAS.md` inteira.
  - Em especial: legado-001 (anti-loop), 006 (`np.linalg.solve`), 017 (janelas do `medir_aec`), 018 (VAD global), 022, 024, 028 (NPU).
- O índice inteiro: `C:\Dev\Reco\roadmap\2026-11-11-melhoria-reco-em-rust.md` (D1, D6, D8, "O que NÃO fazer").
- Evidência em `C:\Dev\Reco\roadmap\2026-11-11-melhoria-reco-em-rust.d\diagnostico\`:
  - `2-restricoes-do-porte.md` (§ A e § 4), `4-ecossistema-rust.md` (§ 3 e § 5), `6-critica-de-completude.md` (V1).
- Código: `C:\Dev\Reco\reco.py:635-735` (decode, VAD), `:916-1110` (alinhamento, dominância, AEC), `:2030-2405` (`OVTranscriber`).
- Contrato: `C:\Dev\Reco\tools\transcrever.py` (213 linhas, inteiro) e `C:\Dev\Reco\docs\TOOLS.md:43`.
- Chamadores: `C:\Dev\central\canais\whatsapp\coletor\src\midia.js:63-130` e `audios.js:120-127`.
- Chamadores (cont.): `C:\Dev\central\tools\importar_exportacoes_whatsapp.py:168-183`.
- Sentinela do literal: `C:\Dev\central\tools\testa_canais.py:360-366` (lê o `reco.py`) e a constante `SEM_CONTEUDO_RECO` em `C:\Dev\central\canais_comuns.py:38`. A Fase 7 (passos 10 e 11) fixa o alvo final.
- Importadores do script: hoje nenhum arquivo de `tools/` faz `import transcrever` (grep de 11/11); o `tools/paridade.py` da Fase 4 (passo 4) passa a importar `transcrever.diarizada`.
- Skill: `%USERPROFILE%\.claude\skills\instagram-conteudo\SKILL.md:29-32`.
- Fonte da crate (baixada por `cargo info`) em `%USERPROFILE%\.cargo\registry\src\index.crates.io-*\`:
  - `openvino-genai-0.11.1\src\whisper_pipeline.rs`, `whisper_generation_config.rs`, `lib.rs`;
  - `openvino-genai-sys-0.11.1\build.rs`, `src\lib.rs`, `upstream\src\c\include\openvino\genai\c\whisper_*.h`.

## Convenções desta fase

- Comandos rodam no Git Bash a partir de `C:/Dev/Reco`. `CARGO_TARGET_DIR=C:\pt` já vale nesta máquina.
- Atalhos usados nas provas:
  - `T=temp/traco` (traços), `RX=C:/pt/release/reco-transcrever.exe`, `SP=C:/pt/release/spike-transcricao.exe`;
  - `CT=app/crates/reco-transcritor/Cargo.toml` (crate solta, sem workspace, no padrão da `app/crates/reco-captura` da Fase 5);
  - `REL=roadmap/2026-11-11-melhoria-reco-em-rust.d/fase-6-portao.md` (relatório do portão);
  - `LOGR="$LOCALAPPDATA/Reco/transcrever-reserva.log"` (log de uso da reserva Python).
  - `MOD="$LOCALAPPDATA/Reco/models/whisper-large-v3-turbo-int8-ov"` (o que `python -c "import reco;print(reco._find_model_dir())"` imprime aqui).
  - `OVD=C:/Dev/Reco/temp/ov-2621/runtime/bin/intel64/Release` (pasta das DLLs da 2026.2.1, absoluta; trocar pela que o passo 1 anotar, se outra).
  - `H0=$(git rev-parse HEAD)` no início da fase, anotado no relatório: é o `<hash do início da fase>` do passo 27.
- **Material privado nunca entra no repo** (o repo é público): MP3, `.txt`, traços e janelas ficam em `temp/` (ignorado pelo git).
- O relatório leva só números, hashes e nomes de arquivo. Nunca trecho de transcrição (o `tools/test_e2e.py:81` imprime 400 caracteres).
  - Nem caminho com o nome de usuário: escrever `%USERPROFILE%`/`%LOCALAPPDATA%`.
- Arquivos de referência, todos 16 kHz estéreo em `%USERPROFILE%\Documents\Reco\` (conferido com `ffprobe` em 11/11):
  - **R1** `gravacao_reco_2026-11-11_18-42-59.mp3` (~11 min; o mesmo da medição V2 de joint stereo);
  - **R2** `gravacao_reco_2026-08-14_09-04-17.mp3` (~93 min);
  - **R3** `gravacao_reco_2026-09-21_19-04-43.mp3` (~125 min; a régua de tempo das 2 h).
  - Cópias em `temp/ref/` (`$R1c`…): fora da pasta do app, para nenhuma prova escrever ao lado das gravações reais.
  - Criar: `mkdir -p temp/ref && cp "$USERPROFILE/Documents/Reco/<nome>" temp/ref/` para cada um.
  - Depois: `R1c=temp/ref/gravacao_reco_2026-11-11_18-42-59.mp3`, e `R2c`/`R3c` do mesmo jeito.
- Fixtures de contrato em `temp/fix/`, geradas com `ffmpeg` (8.1.1, já no PATH; o som vem de R1), antes do passo 5:
  - `amostra.opus` (mono, 120 s, sem a etiqueta `reco`), `mudo.mp4` (vídeo sem trilha de áudio), `com-som.mp4` (vídeo + 120 s de R1);
  - `gravacao_reco_fixture.mp3` (os primeiros 60 s de R1, com a etiqueta no nome).
  - `mkdir -p temp/fix` (o `ffmpeg` não cria a pasta), depois os quatro (rodados em 11/11 numa pasta à parte: saem 120 s, 5 s, 120 s e 60 s):
  - `ffmpeg -y -i "$R1c" -t 120 -ac 1 -c:a libopus temp/fix/amostra.opus`
  - `ffmpeg -y -f lavfi -i color=c=black:s=320x240:d=5 -an temp/fix/mudo.mp4`
  - `ffmpeg -y -f lavfi -i color=c=black:s=320x240:d=120 -i "$R1c" -map 0:v -map 1:a -t 120 -c:a aac temp/fix/com-som.mp4`
  - `ffmpeg -y -i "$R1c" -t 60 -c copy temp/fix/gravacao_reco_fixture.mp3`
- Cache de compilação próprio por versão (`temp/ovcache-<versão>`), **nunca** o `%LOCALAPPDATA%\Reco\ovcache` do app.
- O Python do sistema (OpenVINO 2026.2.1, numpy 2.4.4, scipy 1.17.1, PyAV 17.1.0, zlib-ng 1.3.1) não recebe `pip install`.
- Medir com o app parado, sem gravação nem ao vivo, iGPU livre. Reservar ~6 h de máquina para a Parte A.
- Commit por pathspec ao fim de cada passo verde (`git add <arquivos>`; nunca `-A`, nunca `--no-verify`).
- Arquivo de código novo até 500 linhas (`.rs` incluso, ver Premissas). `reco.py` não muda (5213 linhas, não pode crescer).
  - O `tools/tamanho.json` também trava complexidade nas tools novas (complexidade 10, 12 ramos, 50 comandos por função).

## Fase 6 — Transcrição em Rust (spike com portão)

**Critério de aceite:**

1. No relatório do portão dá para ver, para cada arquivo de referência, quanto do texto saiu igual e quanto tempo levou de cada lado; a decisão segue a régua escrita antes de medir.
   - Se falhar: a decisão vem sem números, com "parece igual", ou contra a régua.
2. Se o portão abrir: áudio do WhatsApp, vídeo do Instagram e gravação do Reco viram o mesmo texto, no mesmo lugar, em até 10% a mais de tempo; se o motor novo faltar ou cair, o antigo assume sem ninguém notar.
   - Se falhar: um áudio fica sem texto, uma gravação sai sem "Eu:"/"Interlocutor(es):" ou com texto diferente, ou fica mais lenta.
3. Se o portão fechar: nada muda para quem usa (a transcrição segue no motor de hoje) e o motivo fica escrito com números.
   - Se falhar: algo muda no uso, ou o motivo não está escrito.

### Régua do portão (escrita antes de medir; não muda depois de ver o número)

| linha | o que a Parte A mostrou | decisão |
| --- | --- | --- |
| M1 | o pacote não traz `openvino_genai_c.dll`, ou faltam os símbolos de criar, gerar e `set_initial_prompt` | FECHA |
| M2 | a temperatura não muda a saída em janela degenerada (o retry do anti-loop ficaria inerte) | FECHA |
| M3 | Rust × Python **na mesma versão** do OpenVINO: alguma chamada gulosa com texto diferente, além do piso | FECHA (bug de binding) |
| M4 | a crate só roda com a 2026.4.x, não com a 2026.2.1 do motor Python | FECHA por ora; reabre quando o motor Python subir de versão |
| M5 | tempo de geração do Rust acima de 1,10× o do Python no R3 | FECHA |
| M6 | M1–M5 limpos | ABRE com OpenVINO em Rust |
| M7 | OpenVINO em Rust fecha, mas whisper.cpp + Vulkan sai ≥ 20% mais rápido com WER ≤ 10% contra o Python | FECHA aqui; vira proposta de roadmap próprio |

- "Piso de ruído" = a diferença entre duas rodadas do próprio Python no mesmo arquivo (passo 5). Se o piso não for zero, "idêntico" vira "dentro do piso".
- Chamada com amostragem (`do_sample`) só precisa sair idêntica se o Python sair idêntico entre duas rodadas; senão, basta não degenerar.
- Na linha M4, o WER da deriva 2026.2.1 → 2026.4.x (passo 6) vai ao relatório como dado para a subida futura do motor Python.
- M2 sem prova (nenhuma janela em que a temperatura mude o Python, passo 8) conta como não limpa: a decisão é `FECHA (M2, não medido)`.

### Parte A — Spike (nada entra no app nem no `tools/transcrever.py`)

1. [ ] Baixar os zips Windows do OpenVINO GenAI 2026.4.1 e 2026.2.1 e extrair em `temp/ov-2604/` e `temp/ov-2621/` — **prova:** `find temp/ov-2604 temp/ov-2621 -name openvino_genai_c.dll` → um caminho por pacote
   **reprova se:** nenhum caminho sai para a 2026.4.1 (linha M1); faltar só no 2026.2.1 já indica a linha M4, mas a Parte A segue para registrar os números.
   - Os releases do GitHub não trazem anexo; os zips moram no storage da Intel (HEAD 200 em 11/11/2026):
     - `https://storage.openvinotoolkit.org/repositories/openvino_genai/packages/2026.4.1/windows/openvino_genai_windows_2026.4.1.0_x86_64.zip`
     - `https://storage.openvinotoolkit.org/repositories/openvino_genai/packages/2026.2.1/windows/openvino_genai_windows_2026.2.1.0_x86_64.zip`
   - Depois do `unzip`, mover o conteúdo da pasta raiz do zip para cima: `temp/ov-2604/runtime/...`, sem a pasta do nome do zip no meio.
   - O `dist` atual só tem `openvino_genai.dll`, sem `*genai_c*` (relatório 6, V1): a wheel não serve. O SHA-256 de cada zip vai ao relatório.
   - Anotar a pasta das DLLs (esperado `runtime/bin/intel64/Release`) e a do TBB (`runtime/3rdparty/tbb/bin`): os passos 2, 7 e 21 usam as duas.
2. [ ] Conferir os símbolos da DLL C antes de qualquer `cargo`, com `temp/simbolos.py` (~20 linhas: `os.add_dll_directory` + `ctypes.CDLL` + `getattr`) — **prova:** `python temp/simbolos.py temp/ov-2604` → `ok 8/8` e `sem setter de temperatura` (ou `com setter`)
   **reprova se:** sai `AttributeError` em algum dos 8 (linha M1).
   - Os 8, por extenso (o script faz `getattr` com o nome exato):
     - `ov_genai_whisper_pipeline_create`, `ov_genai_whisper_pipeline_generate`;
     - `ov_genai_whisper_generation_config_create_from_json`, `ov_genai_whisper_generation_config_set_initial_prompt`;
     - `ov_genai_whisper_generation_config_set_language`, `ov_genai_whisper_generation_config_set_task`;
     - `ov_genai_whisper_generation_config_set_return_timestamps`, `ov_genai_whisper_decoded_results_get_chunk_at`.
   - `os.add_dll_directory` nas duas pastas do passo 1 (DLLs e TBB): sem a do TBB, o `CDLL` falha por dependência, não por símbolo.
   - Por que antes do cargo: com `runtime-linking` cada símbolo vira `Option` (`openvino-genai-sys-0.11.1/src/linking/runtime.rs`, macro `link!`).
   - Símbolo faltando só aparece na hora da chamada, não ao carregar.
   - A config do Whisper não tem setter de temperatura nem de `do_sample`. O `..._get_generation_config` dela devolve uma cópia ("newly created", `whisper_generation_config.h:51-59`).
   - E não existe `ov_genai_whisper_generation_config_set_generation_config` para devolver a cópia mexida.
   - (O `ov_genai_whisper_pipeline_set_generation_config`, `whisper_pipeline.h:256`, existe, mas troca a config do pipeline, não resolve a temperatura.)
   - "Com setter" = a 2026.4.1 exporta `ov_genai_whisper_generation_config_set_generation_config` ou `..._set_temperature` (mesmo prefixo); aí a F6-D3 cai.
   - Rodar o mesmo script em `temp/ov-2621`.
3. [ ] Criar o venv isolado `temp/venv-ov2604` com o OpenVINO 2026.4.x — **prova:** `for p in temp/venv-ov2604/Scripts/python python; do $p -c "import openvino_genai as g;print(g.__version__)"; done` → `2026.4…` e depois `2026.2.1…`
   **reprova se:** a segunda linha não sai `2026.2.1…` (o Python do app foi contaminado: reinstalar a 2026.2.1 antes de seguir).
   - Pacotes do venv: `openvino`, `openvino-genai`, `openvino-tokenizers` 2026.4.x, mais `numpy scipy av huggingface_hub`.
   - Comando: `python -m venv temp/venv-ov2604 && temp/venv-ov2604/Scripts/python -m pip install "openvino-genai==2026.4.1.*" numpy scipy av huggingface_hub`.
   - O `openvino-genai` puxa `openvino` e `openvino-tokenizers` da mesma versão; há wheel `cp314` para Windows (PyPI, 11/11).
4. [ ] Escrever `tools/traco_whisper.py` (até 250 linhas): proxy no `_pipeline` (`reco.py:2054-2085`) que grava cada `generate`
   — **prova:** `python tools/traco_whisper.py "$R1c" --sondar-temperatura 20 --saida $T/r1-py2621-a && grep -c "^Eu: " $T/r1-py2621-a/final.txt` → `chamadas=N …` e uma contagem ≥ 1
   **reprova se:** sai `chamadas=0`, ou a contagem dá 0 (o proxy quebrou o caminho real da diarização).
   - O pipeline do proxy nasce com `CACHE_DIR=temp/ovcache-<versão>` e `device` fixo em `GPU`.
   - Sem editar o `reco.py`: o `_pipeline` crava o cache do app (`reco.py:2063`), mas devolve `self._pipe` se `self._key` bater (`:2059-2060`).
   - Então o proxy cria o `og.WhisperPipeline` próprio, embrulha e injeta `tr._pipe` e `tr._key = (tamanho, "GPU")` antes do `transcribe`.
   - Com `tr.set_device("GPU")`, para a chave calculada (`resolve_device`, `:2057-2058`) bater com a injetada.
   - O `_key[1]` também decide o `initial_prompt` (`reco.py:2261-2262`): com `GPU` ele é usado, como no app.
   - `initial_prompt` vai ao JSON como está: `""` (primeira janela, `:2307`) é diferente de ausente, e o replay e o Rust preservam a diferença.
   - Por chamada: a janela em `NNNNN.f32` e uma linha JSON com `initial_prompt`, `do_sample`, `temperature`, `language`, `task`, `return_timestamps`.
   - E também: texto, chunks `(início, fim, texto)` e tempo em ms. O `.txt` final vai a `final.txt`; o resumo impresso traz `retentativas` e `t_generate`.
   - Roda `OVTranscriber.transcribe(path, lang="pt", diarize=True, aec=True)` como o `tools/test_e2e.py:39-59`.
   - `--sondar-temperatura 20`: nas 20 janelas de menor energia (critério de `tools/test_antiloop.py:30-42`), chama T=0,2/0,4/0,6.
   - As sondas ficam marcadas `sonda` e fora do texto final. O traço de R3 nos dois canais ocupa ~0,9 GB: conferir o disco.
5. [ ] Medir piso de ruído e linha de base de tempo no Python do app (duas rodadas por arquivo) com `tools/comparar_traco.py` (novo, até 200 linhas)
   — **prova:** `python tools/comparar_traco.py $T/r3-py2621-a $T/r3-py2621-b` → `gulosas iguais X/Y · amostradas iguais P/Q · WER Z · t_generate A × B · parede C × D`
   **reprova se:** o total `Y` difere entre as rodadas (a segmentação não é determinística: parar e investigar antes de qualquer régua).
   - Formato único do `comparar_traco.py` (os passos 6 e 8 leem o mesmo): gulosas e amostradas (retentativas do anti-loop) contadas à parte.
   - As chamadas `sonda` ficam fora da contagem, do WER e do `t_generate`; só a opção `--sondas` as compara.
   - O `traco_whisper.py` roda as sondas só depois de o `transcribe` terminar: o `final.txt` da rodada `a` é a referência do passo 19.
   - Arquivos R1, R2 e R3, em ordem alternada entre as rodadas. O WER reusa `norm`/`wer` de `tools/bench_final.py:109-128`.
   - Rodada `a`: `python tools/traco_whisper.py "$R3c" --sondar-temperatura 20 --saida $T/r3-py2621-a` (o passo 8 compara essas sondas).
   - Rodada `b`: o mesmo sem `--sondar-temperatura`, em `$T/r3-py2621-b`. Idem R1 (a rodada `a` já saiu no passo 4) e R2.
   - A parede de referência é a da rodada `b`, que não tem sondas.
   - A linha de base de tempo é esta, do mesmo dia e com cache quente; o "~19 min para 2 h" do `README.md:107-110` é só referência.
   - Medir também o arquivo curto a frio (processo novo, cache quente): `python tools/transcrever.py temp/fix/amostra.opus --forcar`, 5 vezes, mediana.
   - É a carga do coletor: subir o processo e carregar o modelo pesa mais que a geração (legado-028: 14,6 s por processo na GPU).
6. [ ] Escrever `tools/replay_traco.py` (novo, até 150 linhas), que refaz cada chamada com a mesma janela e o mesmo `cfg`; rodar no Python do app e no venv — **prova:** `python tools/comparar_traco.py $T/r1-py2621-a $T/r1-replay-py2621` → `gulosas iguais G/G`
   **reprova se:** alguma gulosa do replay na própria 2026.2.1 difere do original (falta parâmetro no traço: corrigir o passo 4 antes de comparar línguas).
   - As chamadas com amostragem seguem a régua do portão: idênticas só se o piso do passo 5 as deu idênticas.
   - Rodar: `python tools/replay_traco.py $T/r1-py2621-a --saida $T/r1-replay-py2621`.
   - E no venv: `temp/venv-ov2604/Scripts/python tools/replay_traco.py $T/r1-py2621-a --saida $T/r1-replay-py2604`. Repetir os dois para R2 e R3.
   - O replay no venv dá a deriva de versão: `comparar_traco.py $T/r1-py2621-a $T/r1-replay-py2604` → WER que vai ao relatório.
7. [ ] Criar o spike `temp/spike-transcricao/` (crate bin descartável, fora do git) que refaz o traço — **prova:** `cargo build -r --manifest-path temp/spike-transcricao/Cargo.toml && $SP --ov temp/ov-2604 --modelo "$MOD" --traco $T/r1-py2621-a --saida $T/r1-rs2604` → `chamadas=N ok`
   **reprova se:** símbolo `None` ou erro no `pipeline_create` (anotar; repetir com `--ov temp/ov-2621`; se as duas falharem, linha M1).
   - Falha ao **carregar** a DLL com o passo 2 verde não é M1: é dependência fora do caminho de busca. Consertar o spike e repetir.
   - O `libloading::Library::new` (`openvino-genai-sys-0.11.1/src/linking/runtime.rs:109`) chama `LoadLibraryExW` com flags 0, que não procura dependências na pasta da DLL.
   - (Conferido no fonte da `libloading` 0.7.4 do registry, `src/os/windows/mod.rs:105`; a crate pede a 0.8, que não está baixada.)
   - Logo o spike põe a pasta das DLLs e a do TBB no começo do `PATH` do próprio processo antes do `load_from`.
   - Fora do git como os spikes da Fase 5 (passos 4–5 dela). Até 400 linhas.
   - Dependência `openvino-genai-sys = { version = "=0.11.1", features = ["runtime-linking"] }` (sem ela o `build.rs` exige a DLL no build).
   - Tudo pela camada `-sys`: a crate segura guarda o ponteiro em campo privado (`as_ptr` é `pub(crate)`, `whisper_generation_config.rs:137`).
   - Logo, não dá para chamar `set_initial_prompt` sobre a config segura, ao contrário do que o relatório 4 § 3 supunha.
   - DLL carregada por `openvino_genai_sys::library::load_from` (`openvino-genai-sys-0.11.1/src/lib.rs:66-70`), com o caminho do **arquivo** `openvino_genai_c.dll`.
   - Nada de depender do `openvino-finder`.
   - Pipeline por `ov_genai_whisper_pipeline_create` com o par `CACHE_DIR`; os varargs passam pelo helper da crate (`openvino-genai-sys-0.11.1/src/lib.rs:485-499`, até 8 pares).
   - Chamada gulosa: config de `ov_genai_whisper_pipeline_get_generation_config`, como o `_gen_cfg` do Python (`reco.py:2090-2093`).
   - Temperatura: config criada por `..._create_from_json` a partir do `generation_config.json` do modelo, com `do_sample`/`temperature` trocados.
   - Se a config do JSON der texto guloso diferente da do pipeline, a diferença é de config, não de binding: anotar, não contar como M3.
   - `initial_prompt` `""` do traço vai como `""`, nunca `NULL`: o cabeçalho diz que `NULL` remove o prompt (`whisper_generation_config.h:291`).
   - `language` vai como `<|pt|>` (`reco.py:2092`). Chunks por `get_chunk_at`; sem chunk, `get_text_at`, como o `_texto_de` (`reco.py:2144-2150`).
8. [ ] Comparar as camadas nos três arquivos (Rust × replay Python na mesma versão; sondas; tempo) — **prova:** `python tools/comparar_traco.py $T/r3-replay-py2604 $T/r3-rs2604 --sondas` → `gulosas iguais Y/Y · sondas mudaram S/60 · t_generate A × B`
   **reprova se:** alguma gulosa difere além do piso (M3), `S` sai 0 enquanto o Python muda (M2), ou `B > 1,10 × A` no R3 (M5).
   - Camadas: Rust 2026.4.x × replay no venv 2026.4.x; e Rust 2026.2.1 × traço original do Python do app (a que decide a linha M4).
   - Antes, rodar o spike nas rodadas `a` dos três arquivos e nas duas versões, ex.: `$SP --ov temp/ov-2621 --modelo "$MOD" --traco $T/r3-py2621-a --saida $T/r3-rs2621`.
   - A camada M4: `python tools/comparar_traco.py $T/r3-py2621-a $T/r3-rs2621 --sondas`, e o mesmo em R1 e R2.
   - Se o Python também der 0/60 nas sondas, M2 fica sem prova: sondar de novo só nas janelas que tiveram retentativa real no traço (`retentativas` > 0).
   - Sem nenhuma janela assim nos três arquivos, a decisão do passo 10 é `FECHA (M2, não medido)` (notas da régua).
9. [ ] Registrar o whisper.cpp com Vulkan nos mesmos arquivos (iGPU contra iGPU; NPU fora, legado-028) — **prova:** `vulkaninfo --summary | grep -i arc; whisper-cli -m temp/ggml/ggml-large-v3-turbo-q8_0.bin -l pt -f $T/r3-voz-L.wav` → a Arc 130T e a linha `total time`
   **reprova se:** o `vulkaninfo` não lista a Arc, ou o backend que o `whisper-cli` imprime não é Vulkan. Anotar e seguir: o Vulkan é só registro.
   - Binário Vulkan pronto do whisper.cpp se existir; senão, build com CMake + Vulkan SDK instalados por `winget`.
   - Modelo: `ggml-large-v3-turbo-q8_0.bin` do repositório `ggerganov/whisper.cpp` no Hugging Face. Quantização diferente do int8 do OpenVINO: anotar.
   - Entrada justa: `comparar_traco.py --exportar-wav` concatena, por canal, as janelas exatas que o Python mandou ao `generate`, com 0,5 s de silêncio.
   - Medir parede, tempo real (×) e WER contra os textos do Python.
   - O que o `winget` instalou e o portão não usar sai por `winget uninstall`, dito no relatório.
10. [ ] Escrever o relatório do portão em `$REL` (números por arquivo, hashes, versões, a linha da régua que valeu, a decisão) e commitar tools e relatório — **prova:** `grep -c "^| R[123] " $REL; grep "^Decisão do portão:" $REL` → `3` e `Decisão do portão: ABRE (M6)` ou `FECHA (Mx)`
   **reprova se:** a contagem não dá 3, a decisão não cita uma linha da régua, aparece trecho de transcrição, ou `grep -ciE 'c:[\\/]users[\\/]' $REL` não dá 0.
   - Colunas: chamadas, gulosas iguais (mesma versão), piso, WER da deriva, `t_generate` Python × Rust, curto a frio, parede e WER do Vulkan.
   - Commit: `git add tools/traco_whisper.py tools/replay_traco.py tools/comparar_traco.py $REL` (o spike fica em `temp/`, fora do git).
   - O relatório anota os comandos exatos do spike, para quem precisar refazer.

### Parte B — Porte (só se o passo 10 disser ABRE; senão, pular para o passo 27)

A versão do OpenVINO da Parte B é a mesma do motor Python (linha M4), então a régua de texto daqui em diante é **idêntico** (ou dentro do piso).

11. [ ] Criar a crate `app/crates/reco-transcritor/` (lib + bin `reco-transcrever`), levar o embrulho `-sys` do spike para `src/ov.rs` e escrever `src/dispositivo.rs` — **prova:** `cargo build -r --manifest-path $CT && $RX --version` → `reco-transcrever 0.1.0`
   **reprova se:** o build falha, ou o exe pede DLL ao abrir (o carregamento tem de ser tardio, por `load_from`, para a reserva funcionar).
   - `dispositivo.rs` segue a ordem do `resolve_device` (`reco.py:1121-1145`): preferido → GPU → NPU → CPU.
   - Modelo: a busca do `_find_model_dir` (`reco.py:1158-1178`), `%LOCALAPPDATA%\Reco\models\whisper-<tamanho>-*` primeiro; sem download (a reserva baixa).
   - `CACHE_DIR` de produção: `%LOCALAPPDATA%\Reco\transcritor\ovcache` (F6-D11), nunca o do app.
   - Onde o exe acha as DLLs: `RECO_OV_DIR`, senão a pasta do próprio exe. Antes do `load_from`, pôr essa pasta e a do TBB no `PATH` do processo (passo 7).
   - No desenvolvimento (passos 19 e 20, e o build de teste do passo 23), rodar com `RECO_OV_DIR=$OVD`. O TBB: `RECO_OV_DIR/../../../3rdparty/tbb/bin`, ou a própria pasta quando instalado.
   - `ffmpeg.exe`: a pasta do exe primeiro, depois o `PATH`.
12. [ ] Escrever `tools/oraculo_transcricao.py` (novo, até 300 linhas), que despeja os intermediários do Python em `temp/oraculo/<id>/` (`.npy` e `.json`) — **prova:** `python tools/oraculo_transcricao.py "$R1c" --saida temp/oraculo/r1` → `canais=2 segs_L=… segs_R=… grupos=… janelas_aec=… corpus=…`
   **reprova se:** algum contador sai 0 em R1 (o oráculo não exercita o caminho que o Rust vai copiar).
   - Itens: canais do `decode_16k` (`reco.py:635-659`); segmentos e grupos (`:668-735`); o `d` de cada `_alinhar_canais` (`:916-950`).
   - Itens (cont.): máscara da dominância (`:976-1023`); janela antes e depois do `cancel_echo` (`:1026-1110`).
   - Itens (cont.): comprimento zlib e veredito do `_degenerado` (`:2117-2141`) sobre os textos dos traços; o `.txt` final.
   - O oráculo é o despejo direto: o `tools/test_alinhamento.py` está vermelho desde que nasceu (legado-022) e não serve de régua.
   - Como, sem editar o `reco.py`: embrulhar as funções do módulo (`reco._alinhar_canais = espiao(...)` etc.) antes do `transcribe`.
   - O `_alinhar_canais` devolve os arrays, não o `d`: o espião repete a correlação e o `argmax` do original (`reco.py:940-944`) e grava o `d`.
   - Rodar também em `$R2c`, `$R3c` e nas três fixtures (`temp/oraculo/r2`, `r3`, `amostra`, `com-som`, `mudo`): os passos 13 a 18 leem todos.
13. [ ] Decodificar em Rust por `ffmpeg.exe` (`-ar 16000 -f f32le`, mono ou canais separados) em `src/decodificar.rs` — **prova:** `cargo test -r --manifest-path $CT oraculo_decode -- --ignored --nocapture` → `R1 R2 R3 amostra.opus com-som.mp4: diferença máxima 0 · mudo.mp4: sem trilha`
   **reprova se:** a diferença passa de 1e-6 (anotar onde; medir o efeito no texto no passo 19 antes de aceitar; ver F6-D5).
   - "Sem trilha de áudio" vira `.txt` vazio, como o `tools/transcrever.py:40-50` e `:134-139`.
   - Vale para os passos 13 a 18: o `cargo test` roda na pasta da crate e esconde a saída de teste verde.
   - Por isso o `--nocapture` na prova, e o teste acha os dados por `env!("CARGO_MANIFEST_DIR")` + `../../../temp/oraculo`, nunca por caminho relativo.
   - O PyAV reamostra com o `swresample` do FFmpeg, e o `ffmpeg` da linha de comando também. A igualdade é premissa até esta prova.
   - `ffmpeg.exe`: o 8.1.1 que o `winget` já instalou aqui (build da gyan.dev), só para uso local; distribuir é assunto do instalador.
14. [ ] Portar VAD e agrupamento (`reco.py:668-735`; `ALVO_ACUMULO_S=3.0` em `:2027`) para `src/vad.rs`, com percentil linear e média em `f32` no jeito do numpy — **prova:** `cargo test -r --manifest-path $CT oraculo_vad -- --ignored --nocapture` → `6/6 canais: segmentos e grupos idênticos`
   **reprova se:** algum segmento muda de borda (um quadro de 30 ms já muda a janela e o texto).
   - "No jeito do numpy" = soma em pares (blocos de 128), não soma corrida; sem isso, quadro no limiar vira para o outro lado.
   - O limiar global zera arquivo comprimido (legado-018): portar igual, não "consertar" aqui.
15. [ ] Portar alinhamento e dominância (`reco.py:916-1023`; `K_DB_DOMINANCIA=15.0` em `:973`) para `src/alinhar.rs` e `src/dominancia.rs` — **prova:** `cargo test -r --manifest-path $CT oraculo_dominancia -- --ignored --nocapture` → `d idêntico em todas as janelas · máscara idêntica`
   **reprova se:** algum `d` difere. Só se aceita empate de pico com diferença relativa < 1e-9, anotado no relatório.
   - Correlação por FFT (`realfft`). Busca em ±0,5 s (`maxlag_s`, `reco.py:917-940`, legado-014).
   - Histerese 3, blocos de 0,1 s e realinhar a cada 30 s são parâmetros da dominância (`reco.py:976-979`), não do `_alinhar_canais`.
   - `np.roll` com zeragem da borda (`reco.py:944-949`).
16. [ ] Portar o `cancel_echo` (`reco.py:1026-1110`) para `src/stft.rs` + `src/aec.rs`, igual ao `scipy.signal.stft/istft` e ao `np.linalg.solve` complexo — **prova:** `cargo test -r --manifest-path $CT oraculo_aec -- --ignored --nocapture` → `janelas N/N · diferença máxima ≤ 1e-4`
   **reprova se:** alguma janela passa de 1e-4 contra a saída do Python.
   - STFT do scipy: Hann periódica, `nperseg=1024`, `noverlap=768`, `boundary='zeros'`, `padded=True`, escala `spectrum`.
   - O `istft` normaliza pela soma das janelas e corta o padding (`reco.py:1101-1102`).
   - Equações normais por bin com Tikhonov relativo (`reco.py:1076-1089`), solve por LU complexo (`faer`); erro vira `h=0` (`:1087-1088`).
   - Pós-supressão `beta=0.1` (`:1091-1099`) e rede de segurança `r_out > r_in × 1,05` (`:1102-1109`), mesmo sendo defeito (legado-024).
   - O risco numérico conhecido: o `np.linalg.solve` já mudou de semântica uma vez e quebrou o AEC (legado-006).
17. [ ] Ensinar o `tools/medir_aec.py` a medir o AEC do Rust e passar o gate pelo par ERLE×dano — **prova:** `python tools/medir_aec.py "$R2c"; RECO_MOTOR_AEC=rust python tools/medir_aec.py "$R2c"` → mesmo veredito e ERLE/dano por janela a ±0,1 dB
   **reprova se:** o veredito muda ou alguma janela difere mais de 0,1 dB.
   - Variável de ambiente, não flag: o `medir_aec.py` lê argumentos por posição (`tools/medir_aec.py:166-173`).
   - Com `RECO_MOTOR_AEC=rust`, o `cancel_echo` vira uma chamada ao subcomando oculto `reco-transcrever aec-bruto <mic.f32> <ref.f32> <saida.f32>`.
   - O exe é o de `$RX` (ou `RECO_TRANSCREVER_EXE`, se definido). O `aec-bruto` não carrega o OpenVINO.
   - As janelas saem só do perfil do arquivo cru (`escolhe_janelas`, `tools/medir_aec.py:104-130`), então são as mesmas nas duas rodadas (legado-017).
   - ERLE sozinho é métrica proibida (CLAUDE.md, item 4 do "não é acidente"): sempre o par.
18. [ ] Portar o anti-loop (`_degenerado`, `reco.py:2117-2141`) para `src/antiloop.rs`, com `flate2` sobre zlib-ng — **prova:** `cargo test -r --manifest-path $CT oraculo_zlib -- --ignored --nocapture` → `corpus N: comprimento e veredito iguais N/N`
   **reprova se:** algum comprimento difere (o corte de 2,4 pode virar para o outro lado em janela de fronteira).
   - O Python daqui usa `1.3.1.zlib-ng` (`zlib.ZLIB_RUNTIME_VERSION`), não o zlib clássico: o comprimento comprimido muda entre os dois.
19. [ ] Portar o resto do caminho (`reco.py:2156-2405`) para `src/transcrever.rs`, com o subcomando `bruto`
   — **prova:** `RECO_OV_DIR=$OVD $RX bruto "$R1c" --diarizar --aec --saida $T/r1-rs.txt && cmp $T/r1-rs.txt $T/r1-py2621-a/final.txt && echo igual` → `igual`, e o mesmo em R2 e R3
   **reprova se:** o `cmp` acusa diferença além do piso medido no passo 5.
   - O caminho: `_generate_sem_loop`, `_transcribe_channel` e o legado cego de 30 s, `transcribe`, `_merge`.
   - `bruto` transcreve um arquivo com opções explícitas, sem as regras de contrato (essas vêm no passo 20).
   - Bytes que mudam fácil: `initial_prompt` com as 30 últimas palavras só fora da NPU (`reco.py:2262`, `:2305-2324`).
   - E também: ordenação estável por início com `Eu` antes no empate (`:2382-2405`); `"(no content recognized)"` com texto vazio (`:2374`).
   - E `trim`/`split` com o mesmo conjunto de espaço em branco do `str.strip()`/`str.split()` do Python.
   - Tempo: parede do Rust no R3 até 1,10× a do `tools/transcrever.py` medida no mesmo dia.
20. [ ] Levar o contrato inteiro do `tools/transcrever.py` para `src/main.rs`, `src/contrato.rs` e `src/config.rs`, e escrever `tools/test_contrato_transcrever.py` (até 250 linhas)
   — **prova:** `RECO_OV_DIR=$OVD python tools/test_contrato_transcrever.py` → `13/13 casos iguais (stdout, arquivos, bytes, exit)`
   **reprova se:** algum caso difere entre o motor Python e o Rust.
   - Flags: `arquivos...`, `--lang`, `--modelo`, `--device`, `--diarizar`, `--aec`, `--texto-corrido`, `--forcar` (`:164-183`); erro de argumento sai com 2.
   - Regras: `opcoes` (`:63-75`), `destino` (`:87-96`), `diarizada` (`:102-113`), pulado e nome antigo (`:116-139`), lote (`:197-209`).
   - stdout **não** é só caminho: `[pulado, já existe] …` e `[sem trilha de áudio, .txt vazio] …` também vão para lá. Reproduzir byte a byte.
   - Config só leitura, com os padrões do `_CFG_DEFAULTS` (`reco.py:104-128`). JSON quebrado vira padrão, **sem** renomear para `.corrupt`.
   - (O `reco.py:220-224` renomeia o JSON quebrado mesmo só lendo: não copiar.)
   - Casa do config: `%USERPROFILE%\.reco_config.json`, como o `Path.home()` do Python (`reco.py:102`).
   - Rótulos `Eu`/`Interlocutor(es)`: `language` da config, senão o idioma da interface do Windows (`reco.py:269-285`, `:512-516`).
   - Exit 3 = "motor Rust indisponível" (DLL ou modelo ausente), só antes do primeiro arquivo.
   - Isolamento: cada caso roda com `USERPROFILE=temp/contrato/home`, que tem um config com `output_dir=temp/contrato/gravacoes`. Nada toca a pasta real.
   - No config, `output_dir` em caminho absoluto (`C:/Dev/Reco/temp/contrato/gravacoes`): o `na_pasta_do_reco` compara com `resolve()` (`tools/transcrever.py:76-82`).
   - Os dois lados: `python tools/transcrever.py` (o Python de hoje) × `RECO_OV_DIR=$OVD $RX` direto (o invólucro só nasce no passo 22).
   - Casos 1–4: gravação na pasta do app → `x.txt` diarizado; fora → `x.mp3.txt`; `--texto-corrido`; `amostra.opus` → `.opus.txt` corrido.
   - Casos 5–8: `--diarizar` em estéreo sem etiqueta; `mudo.mp4` → `.txt` vazio; `com-som.mp4`; saída existente sem `--forcar` → pulado.
   - Casos 9–13: `x.mp3.txt` antigo corrido; antigo diarizado; lote de 3 com 1 inexistente (exit 1); `--texto-corrido --aec` (exit 2); config `language: en`.
21. [ ] Escrever `tools/instalar_transcritor.ps1` (até 80 linhas): copia exe, DLLs e `ffmpeg.exe` para `%LOCALAPPDATA%\Reco\transcritor\`
   — **prova:** `powershell -ExecutionPolicy Bypass -File tools/instalar_transcritor.ps1 && "$LOCALAPPDATA/Reco/transcritor/reco-transcrever.exe" --version` → `reco-transcrever 0.1.0`
   **reprova se:** a versão não sai, ou sai pedindo DLL.
   - Vem antes da troca do passo 22: quando o invólucro nascer, o exe já está no lugar e o coletor não cai na reserva.
   - DLLs: tudo de `runtime/bin/intel64/Release/*.dll` mais o `tbb12.dll` do TBB, do pacote 2026.2.1 (`temp/ov-2621`, F6-D4). Enxugar a lista fica para o instalador.
   - `ffmpeg.exe`: o `.Target` de `Get-Item (Get-Command ffmpeg).Source`, que é um link simbólico do `winget` (conferido em 11/11).
   - Regra de compilar desta crate: depois de cada mudança em Rust, `cargo build -r --manifest-path $CT` e este script de novo, senão o script do coletor usa o exe velho.
22. [ ] Trocar o motor: o script de hoje vira `tools/transcrever_py.py` (intacto, a reserva) e o novo, até 150 linhas, só chama o exe
   — **prova:** `rm -f "$LOGR"; python tools/transcrever.py temp/fix/amostra.opus --forcar; echo "exit=$?"; cat "$LOGR" 2>/dev/null | wc -l` → caminho do `.txt`, `exit=0` e `0`
   **reprova se:** o exit não é 0, ou o log de reserva tem linha (o exe não foi usado).
   - Busca do exe: `RECO_TRANSCREVER_EXE`, depois `%LOCALAPPDATA%\Reco\transcritor\reco-transcrever.exe`; `RECO_MOTOR_TRANSCRICAO=python` força a reserva.
   - Filho com `CREATE_NO_WINDOW` (`reco.py:558-559`), na mesma classe de prioridade do script, dentro de Job Object "matar ao fechar" (F6-D13).
   - stdout/stderr repassados linha a linha e exit repassado. Com `RECO_TRANSCREVER_PROTOCOLO=1`, o exe marca cada entrada terminada no stderr (`@@feito <entrada>`).
   - O invólucro consome essas marcas e não as mostra.
   - Exit 3 ou falha ao iniciar → roda `transcrever_py.main()` com os mesmos argumentos e grava uma linha datada em `$LOGR`.
   - Saída anormal (exit fora de 0–3, ex.: queda na FFI) → roda a reserva só nas entradas sem `@@feito`, com os mesmos argumentos, e grava no log.
   - Reexporta de `transcrever_py` o que outros scripts importam: `from transcrever_py import diarizada, destino, opcoes, na_pasta_do_reco, sem_trilha_de_audio, canais, transcrever_um`.
   - Antes de escrever, refazer o grep: `grep -rnE "^\s*(from transcrever import|import transcrever\b)|\btranscrever\.[a-z_]+\(" tools --include=*.py | grep -v "tools/transcrever"`.
   - Em 11/11 ele não acha ninguém; o importador conhecido é o `tools/paridade.py` (Fase 4, passo 4: `transcrever.diarizada`). Nome novo que o grep achar entra na lista acima.
   - `RE_DIARIZADA` não entra: é global preenchida tarde dentro do `diarizada` (`tools/transcrever.py:99-113`), e a cópia reexportada ficaria `None`.
   - Prova dos nomes: `python -c "import sys; sys.path.insert(0, 'tools'); import paridade, transcrever, transcrever_py; print(transcrever.diarizada is transcrever_py.diarizada)"` → `True`
     **reprova se:** sai `ImportError`/`AttributeError` (o `tools/paridade.py`, gate da Fase 5, quebraria) ou `False`.
   - A Fase 7 (`check_superficie`) passa a cobrir esses nomes do `transcrever`: anotar no relatório da fase para ela pegar.
   - Curto a frio (régua do gatilho): a mesma medição do passo 5, 5 vezes, mediana.
     **reprova se:** a mediana passa de 1,10× a do passo 5.
23. [ ] Provar a reserva por exe ausente e por queda — **prova:** `rm -f "$LOGR"; RECO_TRANSCREVER_EXE=nao-existe python tools/transcrever.py temp/fix/amostra.opus --forcar; echo "exit=$?"; wc -l < "$LOGR"` → caminho do `.txt`, `exit=0`, `1`
   **reprova se:** o `.txt` não nasce, o exit não é 0, ou o log não ganhou a linha.
   - Segunda prova (queda), com o build de teste: `cargo build --manifest-path $CT` (sem `-r`) gera `C:/pt/debug/reco-transcrever.exe`.
   - Depois: `rm -f "$LOGR"; RECO_TRANSCREVER_EXE=C:/pt/debug/reco-transcrever.exe RECO_OV_DIR=$OVD RECO_TRANSCREVER_FALHAR=2 python tools/transcrever.py <3 fixtures> --forcar`.
   - As 3 fixtures: `temp/fix/amostra.opus temp/fix/com-som.mp4 temp/fix/gravacao_reco_fixture.mp3`; o exe aborta depois do 2º arquivo.
     **reprova se:** o 3º arquivo fica sem `.txt`, ou o log não tem exatamente uma linha, citando só a 3ª entrada (os 2 primeiros não podem ir para a reserva).
   - `RECO_TRANSCREVER_FALHAR` só existe em build de teste (`cfg(debug_assertions)`), nunca no exe instalado.
24. [ ] Provar que não sobra órfão nem janela quando o chamador mata ou esconde o script
   — **prova:** `python tools/transcrever.py "$R2c" --forcar & P=$!; sleep 20; tasklist | grep -c reco-transcrever; taskkill //F //PID $(cat /proc/$P/winpid); sleep 2; tasklist | grep -c reco-transcrever` → `1` e depois `0`
   **reprova se:** a primeira contagem não é 1 (o exe nem subiu: a prova não vale), ou a segunda não é 0 (o exe órfão seguraria a iGPU; o importador mata em 600 s, `importar_exportacoes_whatsapp.py:179-181`).
   - Verificação manual da janela: rodar o importador (`python C:/Dev/central/tools/importar_exportacoes_whatsapp.py` numa exportação de teste) e olhar a tela.
     **reprova se:** pisca uma janela de console (o importador chama o script com `SEM_JANELA`, e o exe não pode abrir console próprio). Manual porque janela não sai em log.
25. [ ] Provar a prioridade Idle na sequência real do coletor (spawn e depois `os.setPriority`, `midia.js:112-118`) — **prova:** `node temp/prioridade.mjs "$R1c"` (script de 15 linhas que faz o mesmo e consulta o filho) → `reco-transcrever: Idle`
   **reprova se:** sai `Normal` (o exe disputaria CPU com a máquina; o coletor rebaixa de propósito, `midia.js:63-66`).
   - O script consulta o filho com `powershell -NoProfile -Command "(Get-Process reco-transcrever).PriorityClass"` (o `wmic` não existe nesta máquina, conferido em 11/11).
   - O invólucro passa ao filho a classe de prioridade que ele tem na hora do spawn; se o Node rebaixar depois, o filho já nasceu Idle porque o Python leva mais que isso para subir.
   - Se a prova pegar a corrida, o invólucro relê a própria classe 1 s depois e aplica ao filho.
26. [ ] Propagar rio abaixo: rodar cada chamador real, incluir a fonte Rust na sentinela da central e abrir a issue datada da reserva
   — **prova:** `cd C:/Dev/central && python tools/testa_canais.py | tail -1; grep -c "reco-transcritor/src/transcrever.rs" tools/testa_canais.py` → `ok — 0 falhas` e `1` ou mais
   **reprova se:** o `grep` dá 0: a sentinela segue lendo só o `reco.py` (o literal que chega ao coletor passa a nascer no Rust e mudaria sem alarme).
   - O `testa_canais.py` só imprime `ok — 0 falhas` (`:494`), sem dizer o que leu: por isso o `grep` no próprio arquivo.
   - Com o portão aberto o literal mora em dois lugares: no `reco.py` (a transcrição do app segue no Python) e no `.rs`. A sentinela confere a constante de `canais_comuns.py:38` entre aspas duplas em cada um, cada um com o seu `checar`.
   - Chamadores, um a um com arquivo de `temp/fix/`: lote do coletor (`midia.js:112`), `audios.js:125`, importador (`:179`), skill do Instagram (`--lang en` no `com-som.mp4`).
   - Segunda prova: `gh issue list --repo dosxnjos/reco --search "reserva Python"` → 1 aberta, com a data no título.
     **reprova se:** volta vazio (a reserva fica para sempre por esquecimento).
   - Título: "Aposentar a reserva Python do transcrever.py (a partir de AAAA-MM-DD)", 30 dias depois do commit do passo 22 (F6-D12).
   - Sentinela em `testa_canais.py:360-366` (abre o `reco.py` e busca `SEM_CONTEUDO_RECO`, definida em `canais_comuns.py:38`). Ler `cerebro/projetos/central.md` antes.
   - O commit da sentinela é no repo da central, por pathspec. A Fase 7 (passo 10) decide o alvo final; aqui só se fecha o buraco aberto nesta fase.

### Parte C — Se o passo 10 disser FECHA

27. [ ] Registrar o fechamento no relatório (linha da régua, o que reabriria, transcrição segue no Python por D1) e conferir que o script não mudou — **prova:** `git diff --stat $H0 -- tools/transcrever.py` → vazio (o `$H0` anotado no início, ver Convenções)
   **reprova se:** aparece qualquer linha no diff, ou o relatório não diz o que reabriria o portão.
   - O que reabriria: a crate ganhar `initial_prompt` e temperatura na API segura; o motor Python subir para uma versão que a crate roda (M4).
   - O spike em `temp/spike-transcricao/` pode ser apagado; os comandos e números já estão no relatório.
   - `traco_whisper.py`, `replay_traco.py` e `comparar_traco.py` ficam: servem de régua para qualquer atualização futura do OpenVINO.

### Fechamento (vale para os dois ramos)

28. [ ] Atualizar a documentação e o hub — **prova:** `grep -ln "reco-transcrever\|portão" README.md docs/ARQUITETURA.md docs/TOOLS.md CLAUDE.md ../cerebro/projetos/reco.md` → cada arquivo do ramo listado
   **reprova se:** algum arquivo do ramo fica sem a mudança, o `CLAUDE.md` cresce mais de 3 linhas, ou `wc -c < CLAUDE.md` passa de 6144 (teto do `gate-claude-md`; hoje 5210).
   - **Abriu:** `docs/TOOLS.md:43` (invólucro, variáveis, log de reserva, instalador); `docs/ARQUITETURA.md` (seção "Transcrição em Rust", oráculos e régua).
   - **Abriu:** `README.md` (a linha de como funciona); `CLAUDE.md` em 1–3 linhas: o contrato vale nos dois motores e se prova pelo teste de contrato.
   - **Abriu:** regra de compilar no `CLAUDE.md` do projeto: mexeu na crate, `cargo build` e `tools/instalar_transcritor.ps1`.
   - **Fechou:** `docs/ARQUITETURA.md` com uma linha e o link do relatório; README e CLAUDE.md não mudam.
   - Armadilha nova só por `python tools/visoes.py novo "título"` (nunca editar `docs/ARMADILHAS.md`).
   - Candidatas: a crate segura sem `initial_prompt` e sem temperatura; zlib-ng × zlib no veredito do anti-loop.
   - Hub `C:\Dev\cerebro\projetos\reco.md`: uma linha em "Estado agora" com a decisão e o link; diário do cérebro por fragmento (ritual).
   - Esta fase não toca `reco.py`/`tray.py`: o `build.ps1` só roda se algum passo os tiver mudado.

## Decisões da fase

| id | decisão | motivo | confiança | reverte se |
| --- | --- | --- | --- | --- |
| F6-D1 | Spike por replay das janelas exatas do Python, antes de portar DSP | isola binding, versão e ruído sem portar VAD/AEC | alta | o traço não reproduzir o próprio Python (passo 6) |
| F6-D2 | Whisper inteiro pela camada `-sys`, com embrulho próprio | a crate segura esconde o ponteiro; sem isso não há `initial_prompt` | alta | a crate ganhar `initial_prompt` e temperatura na API segura |
| F6-D3 | Temperatura por config criada de JSON | o C API da 0.11.1 não tem setter de temperatura na config do Whisper | média | a 2026.4.x trazer o setter (passo 2) |
| F6-D4 | A CLI usa a mesma versão do OpenVINO do motor Python (hoje 2026.2.1) | senão o app e o script voltam a dar textos diferentes (o caso de 11/11) | média | o motor Python subir de versão: a CLI sobe junto, com a mesma régua |
| F6-D5 | Decodificar por `ffmpeg.exe`, não `symphonia` + `rubato` | mesmo `swresample` do PyAV; `symphonia` não lê Opus (WhatsApp) | média | a prova do passo 13 dar diferença, ou o exe pesar demais |
| F6-D6 | A CLI é dona do contrato inteiro; o script vira invólucro com reserva | é o pedido da fase; o contrato se prova por teste nos dois motores | média | o teste divergir de novo: as regras voltam ao Python e o Rust só transcreve |
| F6-D7 | Exe instalado em `%LOCALAPPDATA%\Reco\transcritor\` | lugar fixo, sem admin, fora do repo e do app | média | o instalador das Fases 3–4 der caminho fixo melhor |
| F6-D8 | whisper.cpp + Vulkan é só registro nesta fase | trocar modelo e quantização invalida réguas medidas (k_db, WER, anti-loop) | alta | a linha M7 bater: vira roadmap próprio |
| F6-D9 | Régua: idêntico na mesma versão (ou dentro do piso); tempo até 1,10× no R3 e no curto a frio | "mesmo texto" e "mesmo tempo" precisam de número antes de medir | média | o piso medido no passo 5 passar de 1% de WER |
| F6-D10 | Exit 3 = "motor indisponível antes do 1º arquivo" aciona a reserva | falha no meio do lote já tem semântica (exit 1) | alta | algum chamador tratar o 3 de outro jeito |
| F6-D11 | `CACHE_DIR` próprio da CLI, separado do `ovcache` do app | blob compilado por outra versão ou processo não pode estragar o do app | alta | medir que compartilhar é seguro e economiza a compilação |
| F6-D12 | Reserva Python por 30 dias corridos, com log de uso e issue datada | um mês cobre o volume do coletor sem deixar a reserva eterna | média | o log mostrar uso da reserva: o prazo recomeça depois do conserto |
| F6-D13 | Job Object "matar ao fechar" + prioridade herdada + `CREATE_NO_WINDOW` no filho | o importador mata por tempo, o coletor rebaixa a prioridade, ninguém quer janela | alta | um chamador precisar que o exe sobreviva ao script |
| F6-D14 | `flate2` sobre zlib-ng no anti-loop | o veredito depende do comprimento comprimido, e o Python daqui é zlib-ng | média | o oráculo do passo 18 mostrar igualdade com outro backend |

## Pendente (dono: gabriel)

- Nada. Instalar CMake e Vulkan SDK (passo 9) é técnico e reversível por `winget uninstall`.

## Premissas não verificadas

- Os zips Windows do GenAI 2026.4.1 e 2026.2.1 trazem `openvino_genai_c.dll` em `runtime/bin/intel64/Release` (relatório 6 V1: suspeita).
  - Os dois zips existem no storage da Intel (HEAD 200 em 11/11/2026); o conteúdo não foi aberto.
- A crate 0.11.1 roda com a 2026.2.1: o CI da Intel cobre 2026.1.0 e 2026.4.1 (relatório 6 V1), não a 2.1. É a linha M4.
- `..._create_from_json` lê `do_sample` e `temperature` (o construtor C++ herda do `GenerationConfig`): o C++ não foi aberto. As sondas do passo 8 provam.
- Amostragem com a semente padrão é determinística entre processos e entre línguas, e a gulosa na GPU também. O passo 5 mede o piso.
- O `ffmpeg` da linha de comando reamostra igual ao `AudioResampler` do PyAV 17.1.0 (a versão do FFmpeg embutido no PyAV não foi conferida).
- Existe binário pronto do whisper.cpp com Vulkan para Windows; senão, o build pede CMake, Vulkan SDK e talvez libclang (nenhum no PATH hoje).
- O filho herda a prioridade Idle do script (comportamento documentado do `CreateProcess`, não medido). O passo 25 prova.
- A Fase 5 deixa a crate `app/crates/reco-captura` solta, com `--manifest-path` (fase-5, passo 6); esta fase segue o mesmo padrão.
- `tools/tamanho.json` hoje não lista `.rs`; a Fase 3 (passo 2) o inclui. Se não tiver entrado, conferir com `wc -l app/crates/reco-transcritor/src/*.rs`.
- R2 tem eco medível: confirmar com `python tools/varrer_aec.py "$R2c"` antes do passo 16; sem eco, trocar por outra gravação longa com eco.

## O que esta fase NÃO faz

- Não troca a transcrição do app: "Salvar + Transcrever", `Reco.exe --transcribe`, ao vivo e modo nota seguem no `OVTranscriber` em Python.
- O que impede o app e o script de divergirem enquanto isso é a mesma versão do OpenVINO (F6-D4) com texto idêntico (passos 19 e 20).
- Não sobe a versão do OpenVINO do motor Python (se só a 2026.4.x rodar, o portão fecha pela linha M4).
- Não muda modelo, quantização, `k_db`, limiar do VAD nem a rede de segurança do AEC: paridade primeiro, conserto depois, com gate próprio.
- Não adota whisper.cpp/Vulkan, mesmo se mais rápido (F6-D8). Não usa a NPU (legado-028).
- Não aposenta a reserva Python (Fase 7, pela issue datada) nem apaga o `reco.py`.
- Não muda nenhum chamador: o caminho `Reco/tools/transcrever.py`, as flags e os nomes de `.txt` continuam (D6).

## Gatilho que fecha

- **Fechou o portão:** relatório com números e linha da régua commitado; `tools/transcrever.py` igual a antes.
  - A Fase 7 segue só com a dependência da Fase 4.
- **Abriu o portão:** passos 11–26 verdes; teste de contrato 13/13; `.txt` idêntico nos três arquivos; R3 e curto a frio em até 1,10× do tempo.
  - Mais: uma semana do coletor pelo motor novo sem linha no log de reserva; issue da reserva aberta; docs e hub atualizados (passo 28).
