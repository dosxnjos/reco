# Ecossistema Rust no Windows para o Reco (nov/2026)

Convenção: **[lido]** = vi na fonte primária ou no código; **[medido]** = número local; **[suspeita]** = inferência que ainda não testei. Não editei nenhum arquivo.

## Linha de base local
- **[medido]** 2 h de áudio levam cerca de 19 min de ponta a ponta com diarização. Sem diarização, cerca de 10 min. Na prática são uns 12x tempo real por passada, com large-v3-turbo INT8 na iGPU (`C:\Dev\Reco\README.md:107-110`).
- **[medido]** `dist/Reco` ocupa 859 MB, e só `_internal/openvino` ocupa 225 MB (OpenVINO 2026.2.1).
- **[lido]** A captura usa `soundcard` (`reco.py:4`, `:530`). O MP3 sai do PyAV com `abr=1` a 96 kbps (`reco.py:738-746`, `:150`). O alinhamento é correlação por FFT com scipy (`reco.py:936-945`). O AEC usa STFT/ISTFT do scipy (`reco.py:1055`). A transcrição usa `og.WhisperPipeline(..., CACHE_DIR=)` (`reco.py:2078`). No config o código mexe em `language`, `task`, `return_timestamps` (`:2092-2094`), `do_sample` e `temperature` no re-try de janela degenerada (`:2169-2178`) e `initial_prompt` (`:2307`, `:2595`).
- **[lido]** O Lacre é Tauri 2 com um motor Python congelado. Os dois conversam por JSON Lines em stdin/stdout (`C:\Dev\lacre\src-tauri\src\engine.rs:1-15`, `:171-207`). O perfil de release usa `lto`, `opt-level="s"` e `strip` (`C:\Dev\lacre\src-tauri\Cargo.toml`).

## 1. Captura (loopback do sistema + microfone)
- **cpal 0.18.2** **[lido]**: o WASAPI é o backend padrão. A doc da `Host` diz: "If you use a WASAPI output device as an input device it will transparently enable loopback mode" ([docs.rs](https://docs.rs/crate/cpal/0.18.2/source/src/host/wasapi/mod.rs)). Para o Reco, o que pesa no [CHANGELOG](https://raw.githubusercontent.com/RustAudio/cpal/master/CHANGELOG.md):
  - a 0.18.2 tirou o aviso `DeviceChanged` na troca de dispositivo padrão, porque ele "wrongly implied the stream had rerouted automatically";
  - xrun de captura passou a sair como `ErrorKind::Xrun`;
  - o `drop` deixou de dar pânico quando o dispositivo some.

  Conclusão: o cpal faz loopback, mas seguir a troca do dispositivo padrão fica por nossa conta.
- **wasapi (HEnquist) 0.27.0** **[lido]**: pede Rust 1.85 e edition 2024 ([docs.rs](https://docs.rs/crate/wasapi/latest), [GitHub](https://github.com/HEnquist/wasapi-rs)). Traz loopback, captura de um único aplicativo (exemplo `record_application`), exemplo de AEC e avisos de "default device changes", volume e desconexão. Também dá acesso ao COM cru (`as_immdevice`, `as_iaudioclient`). Tem 95 estrelas e um mantenedor só (o do CamillaDSP).
  - **[suspeita]** Não confirmei se ele escolhe o dispositivo padrão por papel (console × comunicação), que o Reco usa (`reco.py:1384`). Pelo COM cru isso sempre dá para fazer.
- **[lido]** Riscos que qualquer crate herda, documentados no próprio Reco:
  - mic e loopback rodam em relógios de hardware diferentes: deriva de +21 ppm, atraso de cerca de 203 ms que às vezes salta 400 ms (`docs/ARMADILHAS.md:100-117`, `:344-400`);
  - loopback mudo não entrega pacote nenhum. Hoje o `soundcard` inventa zeros pelo relógio (`docs/armadilhas.d/2026-08-30-legado-020-...md`).

  Em Rust, com WASAPI direto, o silêncio vira responsabilidade nossa. Isso é ganho de controle, mas o código tem de existir.
- **Recomendação:** `wasapi` como primeira opção (cobre loopback, avisos de dispositivo e COM), com cpal de reserva.

## 2. Codificação (MP3 com duração correta, ou outro formato)
- **mp3lame-encoder 0.3.0** **[lido]** ([docs.rs](https://docs.rs/crate/mp3lame-encoder/latest/source/src/lib.rs)): tem `lame_tag_size()`, `lame_tag_encode()` e `set_mode(Mode::Stereo | JointStereo)`. O padrão é joint stereo. A ordem do arquivo é "id3v2 tag → VBR tag → actual mp3 content". Como o Reco grava enquanto captura, isso exige reservar o espaço do cabeçalho no começo e voltar para escrever a tag no fim. É a mesma coisa que o muxer do ffmpeg faz hoje (`reco.py:729-733`).
  - **[suspeita]** Não confirmei se o `mp3lame-sys` compila o LAME estático no Windows/MSVC.
  - **[lido]** O PyAV hoje não fixa o modo estéreo (`reco.py:742-745`), então o LAME escolhe. Com L=mic e R=sistema, vale fixar `Mode::Stereo` no Rust para não misturar os canais. Antes disso, é preciso conferir que o arquivo atual não sai em joint stereo.
- **Alternativas** **[lido]**: `flacenc` 0.5.1 (Rust puro, ainda antes da 1.0), [libflac-rs](https://docs.rs/crate/libflac-rs/latest) 0.143.1 (porte bit-exato, com Ogg FLAC) e `opus1` 0.3.0 (Opus em Rust puro). Não verifiquei o empacotamento Ogg do Opus.
- **Custo de trocar de formato** **[lido]**: 9 ferramentas em `tools/` abrem `.mp3`, entre elas `transcrever.py`, `reparar_duracao.py` e `varrer_acervo.py`. O botão Salvar copia "o caminho do MP3". Consumidores fora do repo, como a skill `instagram-conteudo`, eu não levantei.
- **Recomendação:** manter MP3. FLAC dobra ou triplica o disco e quebra os consumidores. Opus não dá ganho que pague a migração.

## 3. Whisper no Core Ultra (iGPU Arc 130T / NPU)
- **openvino-genai 0.11.1** **[lido]**: crate da própria Intel, repositório [intel/openvino-rs](https://github.com/intel/openvino-rs). Tem `WhisperPipeline::with_properties(path, device, &[("CACHE_DIR", ..)])` e `generate(&[f32], Option<&WhisperGenerationConfig>)` ([docs](https://docs.rs/openvino-genai/latest/openvino_genai/struct.WhisperPipeline.html)). Os chunks vêm com `get_start_ts`, `get_end_ts` e `get_text` ([docs](https://docs.rs/openvino-genai/latest/openvino_genai/struct.WhisperDecodedResultChunk.html)). O config tem `set_language`, `set_task` e `set_return_timestamps`. `set_do_sample` e `set_temperature` ficam no `GenerationConfig` interno.
  - **Lacuna** **[lido]**: a camada segura não tem `initial_prompt` nem `hotwords`. A camada `-sys` tem (`ov_genai_whisper_generation_config_set_initial_prompt`, `_set_hotwords`, [all.html](https://docs.rs/openvino-genai-sys/latest/openvino_genai_sys/all.html)), então dá para chamar com `unsafe` ou mandar PR. Não há streamer para Whisper.
  - **[suspeita]** O suporte a Windows não está documentado: o README só fala de macOS e Linux, e o build do docs.rs é Linux. Também não está dito para qual versão do GenAI as bindings foram geradas, nem confirmei a DLL `openvino_genai_c.dll`. **É o ponto que decide tudo**, e um spike de um dia responde.
  - **[suspeita]** É o mesmo motor C++ que o Reco usa hoje, então a velocidade deve ficar igual (~19 min). O Rust não acelera a inferência.
- **whisper-rs 0.16.0** **[lido]** ([features](https://docs.rs/crate/whisper-rs/latest/features)): tem `vulkan` e `intel-sycl`, mas não tem `openvino`. No whisper.cpp, o OpenVINO acelera **só o encoder** (README do [whisper.cpp](https://github.com/ggml-org/whisper.cpp), recomenda 2026.3.0). O PR [#3492](https://github.com/ggml-org/whisper.cpp/pull/3492), de nov/2025, ativou o Vulkan em iGPU: diz "3-4x vs CPU" e também "12x", sem dizer o modelo e sem conciliar os dois números (testado num Core Ultra 7 155H). Não achei nenhum número publicado de large-v3-turbo em Arc que chegue perto de 12x tempo real.
  - **[suspeita]** O whisper.cpp com Vulkan pode empatar, mas só um benchmark local responde. Ele também não usa a NPU, que o Reco escolhe de propósito durante chamada de vídeo (`README.md:110-112`).
- **ort 2.0.0-rc.12** **[lido]**: ainda é release candidate. Tem o provedor de execução OpenVINO (CPU/GPU/NPU, [docs](https://docs.rs/crate/ort/latest/source/src/ep/openvino.rs)), mas o laço de decodificação do Whisper teria de ser escrito à mão. É mais trabalho sem ganho claro. **candle**: não pesquisei, e não sei de backend para GPU Intel. Fica descartado por ora.

## 4. Interface
- **Tauri 2** **[lido]**: tem plugin oficial para atalho global, instância única, autostart, updater, posicionamento, estado da janela e notificação. A bandeja vem no núcleo ([plugins](https://v2.tauri.app/plugin/)). O popover em cima da bandeja sai pelo `positioner` com a feature `tray-icon` e `on_tray_event` ([doc](https://v2.tauri.app/plugin/positioner/)). Janela sem moldura e de tamanho fixo é configuração. **É o que o Lacre já usa**: mesma pilha, mesmo build, mesmo padrão de motor e mesma linguagem visual (HTML/CSS).
  - **[suspeita]** O que deixa a tela estável ("não se mexer") é layout de tamanho fixo e transição só em opacidade e transform. Isso é disciplina de CSS, e o Tauri não impede.
  - **[suspeita]** O WebView2 come algumas dezenas de MB de RAM. Os números de blog (50-100 MB parado) não têm fonte controlada, e o Lacre não tem `target/` local para eu medir.
- **Slint** **[lido]**: a bandeja (`SystemTrayIcon`, Shell_NotifyIcon) só chegou na 1.17, em 24/06/2026 ([blog](https://slint.dev/blog/slint-1.17-released)). É bom e leve, mas é uma DSL nova e ecossistema menor para o dono.
- **iced 0.14** **[lido]**: "final experimental release before 1.0" ([release](https://github.com/iced-rs/iced/releases/tag/0.14.0)). **egui**: modo imediato, que redesenha o tempo todo, e a estética padrão é de ferramenta. **gpui**: não há crate oficial estável da Zed. Só existem forks (`gpui-ce`, `gpui-standalone`), e não confirmei o suporte a Windows.
- **Recomendação:** Tauri 2. É o menor risco, porque reaproveita o Lacre e porque ajustar HTML/CSS com IA é o caminho mais maduro.

## 5. Processamento de sinal (porte do AEC e do alinhamento)
- **[lido]** O algoritmo atual é correlação por FFT, STFT/ISTFT, mínimos quadrados regularizados por bloco (`lam` relativo à energia do bloco) e reamostragem com estado (`reco.py:771`, `:1045-1060`). O `rubato` 5.0.0 existe para reamostrar ([docs.rs](https://docs.rs/crate/rubato/latest)).
- **[suspeita]** `rustfft`/`realfft`, `ndarray` e um resolvedor linear (`nalgebra` ou `faer`) cobrem o resto. O porte é viável, mas os blocos são pequenos e a perda é baixa.
- O risco real é igualar os números do `scipy.signal.stft/istft` (janela, sobreposição, escala, padding) e do `correlate`. O próprio Reco já registrou que mudar o comportamento do `np.linalg.solve` quebrou o AEC (`armadilhas.d/...legado-006`). Os oráculos já existem: `tools/medir_aec.py`, `test_alinhamento.py` e `varrer_aec.py`. Por outro lado, `test_alinhamento.py` está vermelho desde que nasceu (`legado-022`), então ele não serve de oráculo até ser consertado.

## 6. Veredito
**Maduro hoje:**
- Tauri 2 com bandeja e os plugins;
- captura WASAPI (`wasapi` 0.27 ou cpal 0.18);
- MP3 via LAME com tag Xing;
- FFT e reamostragem.

**Arriscado:**
- `openvino-genai` no Windows: sem documentação, a camada segura está incompleta e há poucos mantenedores;
- whisper.cpp na Arc: velocidade não provada, só encoder no OpenVINO, sem NPU;
- igualar o AEC/STFT ao scipy;
- iced, gpui e o Slint recente para um dono leigo.

**Divisão recomendada (reversível, em fases):**
1. **Fase A (o que o Gabriel sente):** interface em Tauri 2 + Rust, controlando o motor Python atual como processo filho via JSON Lines, igual ao Lacre (`engine.rs`). O Python continua com captura, MP3, AEC e Whisper. A interface sai bonita e estável sem mexer no que funciona.
2. **Fase B:** captura e codificação MP3 em Rust (`wasapi` + `mp3lame-encoder`, `Mode::Stereo`). Aí o medidor de volume e a gravação ficam nativos e a interface responde na hora. Prova: contar frames × relógio de parede por canal, com a caixa muda, e a duração do MP3 batendo.
3. **Fase C, condicionada a um spike:** Whisper em Rust via `openvino-genai` (+ `-sys` para o `initial_prompt`), **só se** compilar no Windows com o GenAI 2026.2.x e der o mesmo texto e o mesmo tempo (~19 min) no mesmo arquivo. Se falhar, o Whisper e o AEC ficam no Python, que hoje leva 225 MB de OpenVINO de qualquer jeito.
   - **[suspeita]** Mesmo com tudo em Rust, o instalador continua pesado por causa das DLLs do OpenVINO. O ganho grande de tamanho vem de sair do PyInstaller/numpy/scipy, não do OpenVINO.

"Rápido" aqui significa interface e arranque. A transcrição não fica mais rápida por ser em Rust, porque a inferência é a mesma.

**Contigo:** nada nesta fase. A decisão entre Python embutido e tudo em Rust só aparece depois do spike da Fase C.