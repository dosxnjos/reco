# Crítica de completude: as 5 frentes de reescrita do Reco

## 1. Contradições entre frentes

1. **O argumento da NPU contra o whisper.cpp não se sustenta.** A frente rust-ecossistema e a frente prontos descartam o Vulkan/whisper.cpp porque ele "não usa a NPU, que o Reco escolhe de propósito". A frente reco-restricoes diz o contrário, citando ARMADILHAS:737-771: desde 25/09 a NPU **quebra** com o large-v3-turbo int8 (`roi_end <= max_dim`), e o "5,5× tempo real" não se repetiu. Com a NPU quebrada, o critério real fica sendo iGPU OpenVINO contra iGPU Vulkan, e o benchmark do Meetily proposto pela frente prontos passa a pesar mais.
2. **As frentes não concordam sobre o que vai para Rust primeiro.**
   - A frente prontos põe captura, encode e interface em Rust já no primeiro passo.
   - As frentes reco-restricoes e rust-ecossistema mandam trocar só a interface primeiro.
   - A frente reco-restricoes ainda avisa que fazer a captura em Rust ao mesmo tempo que a Fase A1 no Python (buffer de 1 s) é trabalho duplicado.
   - Nenhuma frente fecha a ordem. A decisão é técnica.
3. **O loopback sem pacotes quando nada toca foi tratado de dois jeitos.** A frente rust-ecossistema marca como [lido] que "loopback mudo não entrega pacote", citando o legado-020. A frente reco-restricoes marca o mesmo ponto como suspeita não confirmada em documentação da Microsoft. Esse comportamento decide se o motor Rust precisa fabricar silêncio pelo QPC. Merece uma linha de prova no spike de captura.
4. **A modularização não está "obsoleta" na Fase A.** A frente reco-restricoes a declara obsoleta, mas a Fase A, que todas recomendam, exige um servidor JSON Lines em Python em volta do `reco.py`.
   - **Lido:** `reco.py:17` faz `import tkinter` no topo. Os tools já importam o `reco` sem abrir a UI, então dá para fazer sem cortar o arquivo.
   - Mesmo assim, o servidor nasce em arquivo novo, por causa da trava de 500 linhas. Ele também vira mais um consumidor do `import reco`.
5. **Divergências menores:**
   - **Scripts que importam o `reco`:** a frente reco-mapa diz 24 e a frente reco-restricoes diz 23.
   - **Tokens de design do Lacre:** a frente rust-ecossistema diz "mesma linguagem visual do Lacre". A frente lacre-molde diz que os tokens só existem nos PRs em rascunho, e a regra da casa proíbe copiar.

## 2. Afirmações sem evidência que sustentam decisões

- **Nenhuma frente mediu o que é lento hoje** (abertura do exe de 859 MB, primeiro clique em Gravar, compilação do modelo). O Gabriel pediu "rápido", e a recomendação unânime da Fase A mantém o motor Python na partida.
  - **Lido:** o custo de subir a GPU por processo é de 14,6 s e 1,35 GB (ARMADILHAS:760).
  - Se o botão Gravar depender do motor aquecido, a Fase A pode **não** entregar o "rápido". Falta medir o tempo até a primeira gravação possível e propor o motor aquecido em segundo plano, como o `_warm_imports` do Lacre (`server.py:222`).
- **"Tauri = estável" é suposição.** A frente lacre-molde mostra que o `render()` do Lacre reconstrói a árvore inteira (`main.ts:158-171`), que é o oposto do que o Gabriel reclama. O que dá a estabilidade é o contrato de layout: janela de tamanho fixo, áreas reservadas para status e transcrição, `tabular-nums` e transição só em opacidade. Isso ainda não foi especificado, e nenhuma frente desenhou a tela.
- **"WebView2 come dezenas de MB" e "instalador pesado por causa do OpenVINO"** são suspeitas sem número. Não mudam a decisão, mas não podem entrar como fato na proposta.

## 3. As 3 perguntas que mudam o desenho, verificadas aqui

**V1. O `openvino-genai` em Rust roda no Windows? Responde em boa parte a dúvida que a frente rust-ecossistema chamou de "o ponto que decide tudo".**
- **Lido:**
  - O CI do intel/openvino-rs roda a matriz `[ubuntu-22.04, ubuntu-24.04, windows-latest]` × OpenVINO `[2026.1.0, 2026.4.1]` (`.github/workflows/main.yml:26-27`).
  - Existe `crates/openvino-genai/tests/whisper_pipeline.rs`, com o fixture `whisper-tiny`.
  - As 3 últimas execuções na `main` passaram (a mais recente em 02/11/2026).
- **Ressalvas:**
  - Os crates de GenAI ficam **fora** do passo de linkagem dinâmica (linha 71) e só rodam com `--features ...genai-sys/runtime-linking` (linha 75).
  - O Reco usa a 2026.2.1, que não está na matriz.
  - O crate linka `openvino_genai_c` (`crates/openvino-genai-sys/build.rs:5`). **Medido:** o `dist` atual só tem `_internal/openvino_genai/openvino_genai.dll`, sem `*genai_c*`.
- **Suspeita:** a DLL C vem do pacote de arquivo do GenAI, não da wheel.
- **Consequência:** o spike continua necessário, mas com escopo menor. Precisa responder quatro coisas:
  - versão 2026.4.x com runtime-linking;
  - empacotamento da DLL C;
  - `initial_prompt` via a camada `-sys`;
  - o mesmo `.txt` no mesmo MP3.

**V2. Os MP3 atuais são joint stereo? A frente rust-ecossistema pediu essa conferência antes de fixar `Mode::Stereo`.**
- **Medido:** varri os cabeçalhos de frame com um parser próprio.
  - `gravacao_reco_2026-11-11_18-42-59.mp3`: 18.322 de 18.323 frames em joint stereo, com M/S ligado em 1.972 deles (10,8%).
  - `..._2026-11-10_09-11-12.mp3`: 16.522 frames em joint, M/S em 2 deles.
- **Consequência:** `k_db=15`, o par ERLE×dano e o WER foram todos medidos sobre arquivos joint stereo. Trocar para `Mode::Stereo` muda o formato e precisa de gate próprio (`medir_aec`, dominância). Não é "conserto grátis".
- **Suspeita:** o vazamento de quantização entre canais no M/S prejudica a diarização. Ninguém mediu.
- **Medido também:** o arquivo de 659,5 s sai a 34,6 kbps no ffprobe, não 96. Suspeita: o ABR do LAME derruba a taxa nos trechos de silêncio, e o "96" funciona como alvo. O encoder Rust precisa reproduzir esse comportamento do ABR, não o número da constante.

**V3. O modo ao vivo sobrevive com captura em Rust e transcrição em Python?**
- **Lido:** o `DualRecorder._pump` entrega pares de amostras **no próprio processo** (`reco.py:2006-2011`). O `App` liga isso a `self._live.feed_pair` (`reco.py:3774-3783`).
- **Consequência:** na Fase B, com a captura saindo do Python, o modo ao vivo precisa de um canal de áudio cru entre processos. A frente lacre-molde já disse que o JSON Lines não serve para isso. As opções são três:
  - um pipe binário ou memória compartilhada;
  - o motor Python ler o MP3 que está crescendo;
  - deixar o ao vivo em Rust e o resto no Python.
- O mesmo vale para a passada final do modo nota. Nenhuma frente tratou disso, e isso afeta a ordem das fases.

## 4. Riscos ignorados

1. **Expectativa do dono.** Ele pediu "em Rust", e o consenso é um híbrido sem prazo de fim, com a transcrição igual (~19 min para 2 h) e o Python dentro por tempo indeterminado. Isso precisa ser dito a ele de frente, como decisão dele: o que ele chama de "Rust" é a sensação (bonito, estável, abre na hora), e isso a Fase A entrega sem trocar o motor.
2. **A sentinela da central passa a não vigiar nada.** `central/canais_comuns.py:35` lê o literal `"(no content recognized)"` no texto do `reco.py`. Se o motor mudar de arquivo ou de linguagem, o `if os.path.isfile` passa sem avisar (frente reco-mapa §5). Precisa entrar no plano como passo explícito.
3. **Dois apps vivos na transição.** Na Fase A, a interface Tauri e o Reco.exe antigo disputam o mesmo `~/.reco_config.json` e os mesmos endpoints. Falta decidir o nome do mutex e o momento em que o config migra (ARMADILHAS:773).
4. **O comportamento da bandeja não foi checado no Tauri.** Hoje o hover mostra a janela sem roubar o foco e o clique fixa (`tray.py`, `reco.py:5024`). Nenhuma frente confirmou que o Tauri 2 entrega os eventos de entrar e sair do ícone no Windows e consegue mostrar a janela sem foco. Fica como item do spike de interface.
5. **Gate de captura.** Falta o teste sob carga D1 (`test_gravacao_sob_carga.py`). Sem linha de base, ninguém prova que a captura em Rust resolveu o salto de 37% (frente reco-restricoes §4).
6. **Lixo no bundle.** pyarrow e duckdb (~116 MB) iriam junto para o motor congelado da Fase A se o `collect_all` for copiado sem `excludes`.
7. **Mac.** A frente reco-restricoes trata o Mac como congelado e as outras o ignoram. Saber se o Mac continua no escopo muda o motor de transcrição (MLX contra OpenVINO) e é decisão do dono.

## 5. Perguntas que nenhuma frente respondeu e mudam o desenho

- O que o Gabriel chama de "rápido": abrir, começar a gravar ou transcrever?
- Os botões devem ou não se mexer no clique (a regra do Lacre faz o botão se mexer)?
- Qual a identidade visual própria do Reco?
- O ao vivo e o modo nota continuam no escopo? Isso decide a V3.
- O Mac está dentro ou fora?

A medição da V2 usou um parser de cabeçalho de frame MP3 descartável, feito na pasta temporária da sessão (fora do repo).