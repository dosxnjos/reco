# Roadmap: Reco em Rust, bonito e estável (2026-11-11)

Risco: dado (perda de gravação na troca do motor de captura) · Base: Reco `7c5c1a1` (2026-11-11), lacre `d06a2c4` (2026-11-11), C:\Dev `db0322f1` (2026-11-11) · Arquiteto: opus 5.5, sessão 4c65eb01, skill melhore.
Pedido: reco-rust | Reco em Rust, com interface bonita e que não fica pulando | de: gabriel | desde: 2026-11-11 | origem: chat

> Roadmap modular: este é o **índice** (contexto, decisões, contratos, descartes). Cada fase tem o próprio md
> (`2026-11-11-melhoria-reco-em-rust-fase-N.md`) e o relatório dela vai ao sidecar
> `2026-11-11-melhoria-reco-em-rust.d/`. A evidência das 5 frentes de investigação mora em
> [diagnostico/](2026-11-11-melhoria-reco-em-rust.d/diagnostico/) e é citada pelo nome do arquivo.

## Como retomar

1. Ler o [CLAUDE.md do Reco](../CLAUDE.md), o [hub](../../cerebro/projetos/reco.md) e a
   [ARMADILHAS](../docs/ARMADILHAS.md) (gerada; inteira antes de mexer em captura, MP3 ou transcrição).
2. Ler este índice inteiro (decisões e contratos valem para todas as fases).
3. Ler o md da fase e só os relatórios de `diagnostico/` que ela cita.
4. Conferir o frescor: `git -C C:/Dev/Reco log --oneline 7c5c1a1..HEAD` e reler o que mudou nos arquivos da fase.
5. **Fases 5, 6 e 7 envelhecem:** as linhas citadas valem para `7c5c1a1`, e as Fases 2 a 4 mudam o terreno.
   Antes de executar qualquer uma delas, rodar uma nova auditoria do md contra o código (skill melhore no
   próprio md) e só então começar.

| fase | md | depende de |
| --- | --- | --- |
| 0 Medir o hoje e provar o que é barato provar | [fase-0](2026-11-11-melhoria-reco-em-rust-fase-0.md) | — |
| 1 Identidade visual e contrato de tela | [fase-1](2026-11-11-melhoria-reco-em-rust-fase-1.md) | 0 (medições de tempo e da bandeja) |
| 2 Motor Python como servidor | [fase-2](2026-11-11-melhoria-reco-em-rust-fase-2.md) | 0 |
| 3 Casco Tauri e telas novas | [fase-3](2026-11-11-melhoria-reco-em-rust-fase-3.md) | 1 (direção escolhida) e 2 |
| 4 Paridade, troca e reserva | [fase-4](2026-11-11-melhoria-reco-em-rust-fase-4.md) | 3 |
| 5 Captura e MP3 em Rust | [fase-5](2026-11-11-melhoria-reco-em-rust-fase-5.md) | 4 |
| 6 Transcrição em Rust (spike com portão) | [fase-6](2026-11-11-melhoria-reco-em-rust-fase-6.md) | 5 |
| 7 Aposentar a interface Tk e propagar | [fase-7](2026-11-11-melhoria-reco-em-rust-fase-7.md) | 4 e 6 (o veredito do portão, aberto ou fechado) |

As Fases 1 e 2 podem andar em paralelo depois da 0. O **spike** da Fase 6 (até o portão) só precisa da
Fase 2, não da captura em Rust: pode rodar cedo e dar ao Gabriel o número para decidir "híbrido × tudo em
Rust"; o **porte** da Fase 6 (depois do portão) continua dependendo da 5. Antes de antecipar, reauditar o md
da Fase 6 (item 5 de "Como retomar").

## Contexto e motivação

- **O pedido (11/11/2026, nas palavras do Gabriel):** "fazer ele em Rust", "uma interface mais amigável, mais
  bonita, que nem o lacre", "eu quero algo rápido", e a queixa central: "uma interface que não para de ficar
  se mexendo sempre que eu clico em um botão. Ela tá feia. Ela tá zoada."
- **O que é o Reco hoje:** app Windows em Python/Tkinter (`reco.py`, 5213 linhas, mais `tray.py`) que grava
  mic + sistema num MP3 estéreo (L=mic, R=sistema) e transcreve local com OpenVINO GenAI (Whisper
  large-v3-turbo na iGPU), com diarização por canal, AEC e defesa anti-loop. Mapa completo:
  [1-mapa-do-reco-atual](2026-11-11-melhoria-reco-em-rust.d/diagnostico/1-mapa-do-reco-atual.md).
- **Por que a janela pula (lido no código):** a janela não tem tamanho fixo, todo o layout é `pack` com
  conteúdo variável e há 5 chamadas a `geometry("")` que reencaixam a janela de propósito
  (`reco.py:3323, 3467, 3562, 3602, 4338`). Status que quebra em 1 a 3 linhas, botões que somem e aparecem e
  painéis que abrem mudam a altura e a largura a cada clique. Detalhe na seção 3 do mapa.
- **O Reco é infraestrutura da casa, não só um app:** `tools/transcrever.py` é o "ouvido dos agentes" de
  todo `C:\Dev` (coletor de WhatsApp da central, importação de exportações, skill do Instagram), e 23 scripts
  de `tools/` importam `reco` como régua de regressão. Quebrar isso derruba fluxos fora do Reco.
- **O molde existe:** o Lacre (`C:\Dev\lacre`) é Tauri 2 + Rust com motor Python congelado por PyInstaller,
  falando JSON Lines por stdin/stdout. Está publicado e provado. Ver
  [3-lacre-como-molde](2026-11-11-melhoria-reco-em-rust.d/diagnostico/3-lacre-como-molde.md).

## O que já existe pronto

Detalhe e fontes: [5-apps-prontos](2026-11-11-melhoria-reco-em-rust.d/diagnostico/5-apps-prontos.md).

- **Nenhum app pronto substitui o Reco.** Meetily e Vibe (Tauri + Rust) misturam mic e sistema em mono;
  Anarlog (ex-Hyprnote) separa os canais e tem AEC, mas é beta no Windows e um monorepo de 150 crates.
  Nenhum usa OpenVINO, e nenhum tem o contrato do `tools/transcrever.py`.
- **Caminho escolhido: construir, reaproveitando pronto onde dá.**
  - Casco: Tauri 2 com os plugins oficiais (bandeja, atalho global, posicionador); a instância única é o
    mutex `Local\Reco.SingleInstance` feito à mão (D7, F0-D5, F3-D2), porque o plugin não exclui o app velho.
  - Comunicação com o motor: o `engine.rs` do Lacre (Router por id, reinício com backoff, log com rotação).
  - Bandeja, fechar para a bandeja e plugins: a Guarita (`C:\Dev\albion\guarita\app\src-tauri`).
  - Captura em Rust (Fase 5): a crate `wasapi` (a mesma do Anarlog), com cpal de reserva.
  - MP3 em Rust: `mp3lame-encoder` (tem `lame_tag_encode`, o cabeçalho de duração).
  - Transcrição em Rust (Fase 6): `openvino-genai`, crate da própria Intel (o mesmo motor C++ de hoje).
- **Fonte de ideias, não de código:** o modelo `CaptureFrame` do Anarlog (mic e sistema separados, eventos
  de lacuna) e a interface de Handy e Vibe.

## O que o pedido não dizia

- **feito no desenho (técnico, reversível):**
  - "Em Rust" vira **Rust onde dá ganho que o Gabriel sente, Python onde o resultado já está medido**,
    em fases, sem prazo de fim forçado. A transcrição não fica mais rápida em Rust (o motor C++ é o mesmo);
    o que fica rápido é abrir, gravar e a interface responder. Ver D1.
  - Contrato anti-pulo explícito (D4), porque Tauri sozinho não impede layout que pula: o `render()` do
    Lacre reconstrói a árvore inteira e só não pula porque a tela dele muda pouco.
  - Medir antes de prometer "rápido" (Fase 0): hoje ninguém mediu abrir, primeiro clique e parar.
  - Proteger os contratos externos (D6): `tools/transcrever.py`, nomes de arquivo, config, sentinela da
    central que lê o literal `"(no content recognized)"` no texto do `reco.py`.
  - Gravação nunca se perde na troca: o app velho fica como reserva até a paridade ser provada (Fase 4) e a
    captura nova só entra com os gates que leem o disco (Fase 5).
  - DPI (o exe atual não declara `dpiAware`, texto borrado em escala 125/150%), fontes de 8 pt e lixo de
    ~116 MB no bundle (pyarrow e duckdb) somem no caminho, sem fase própria.
  - O modo nota (já no código, sem botão) ganha botão na Fase 3, absorvendo as Fases 2 e 3 do roadmap dele.
- **proposto (decisão do Gabriel, não bloqueia a escrita):**
  - Identidade visual própria do Reco: a Fase 1 mostra 2 ou 3 direções numa vitrine e ele escolhe.
- **descartado:** usar app pronto, forkar Meetily ou Anarlog, reescrever tudo de uma vez (ver "O que NÃO fazer").

## Diagnóstico

### O que está bom (não mexer)

- Formato do arquivo (16 kHz estéreo, L=mic, R=sistema, ABR 96k) e a biblioteca no filesystem
  (mp3 + .txt + .resumo.md lado a lado).
- A lógica medida do núcleo: alinhamento em runtime, AEC com o par ERLE×dano, dominância `k_db=15`,
  defesa anti-loop, VAD com agrupamento de 3 s, migração de config, dispositivo Auto. Números em
  [2-restricoes-do-porte](2026-11-11-melhoria-reco-em-rust.d/diagnostico/2-restricoes-do-porte.md) § A.
- O contrato do `tools/transcrever.py` e os 23 scripts de régua em `tools/`.

### O que está frágil ou custando

- **Interface:** janela que redimensiona a cada clique, sem DPI awareness, 8 pt, ações escondidas no hover,
  navegação por links de texto, tema livre que desencontra dos widgets ttk, sem progresso de transcrição.
- **Captura:** buffer WASAPI de 22 ms herdado do `soundcard` gera salto de 350 a 566 ms em 16 de 43
  gravações medíveis (37%); o conserto está desenhado em `roadmap/2026-08-21-salto-de-alinhamento-sob-carga.md`.
- **Distribuição:** pasta de 859 MB copiada à mão, sem instalador, build que falha com o app aberto.
- **Fato medido na crítica (V2):** os MP3 atuais saem em **joint stereo** (18.322 de 18.323 frames) e a
  ~35 kbps efetivos no ffprobe, não 96. Todas as réguas (k_db, ERLE×dano, WER) foram medidas sobre isso;
  o encoder novo reproduz esse modo ou passa por gate próprio.
- **NPU quebrada** com large-v3-turbo int8 desde 25/09 (`roi_end <= max_dim`, ARMADILHAS): o argumento "o
  whisper.cpp não usa a NPU" pesa menos do que parece. Fica registrado para a Fase 6.

Conceitos do acervo aplicados: **via-negativa** (cada fase tira peso antes de pôr: a primeira entrega é
interface, não motor novo; DPI, bundle e pulo saem por subtração) e **opcionalidade** (o app velho segue
instalável até a Fase 4 fechar; o portão da Fase 6 pode fechar sem custo para o resto).

## Decisões técnicas

| id | decisão | motivo | quem | confiança | reverte se |
| --- | --- | --- | --- | --- | --- |
| D1 | Híbrido em fases: interface em Tauri 2 + Rust primeiro, motor Python atual como processo filho; captura e MP3 em Rust depois; transcrição em Rust só se o spike passar | entrega o que o Gabriel sente sem tocar no que está medido; cada passo é reversível | opus + advisor | alta | o Gabriel declarar que quer zero Python mesmo sem ganho (vira escopo dele) |
| D2 | Tauri 2 com front em TypeScript + Vite sem framework, como o Lacre | reaproveita build, CI e `engine.rs`; HTML/CSS é o caminho mais maduro para interface bonita; Slint só ganhou bandeja em 24/06/2026, iced é pré-1.0, egui tem cara de ferramenta | opus | alta | a Fase 0 provar que o Tauri não mostra a janela da bandeja sem roubar o foco (aí avaliar Slint 1.17) |
| D3 | Tudo no mesmo repo `dosxnjos/reco`: `engine/` (servidor Python) e `app/` (Tauri: `app/src-tauri` + `app/ui`) | histórico, docs, `tools/` e regras num lugar só; a trava de 500 linhas vale para os arquivos novos (hoje o `tools/tamanho.json` só olha `.py .js .ps1…`: a Fase 3 inclui `.rs` e `.ts` em commit próprio) | opus | média | o repo ficar confuso para quem chega (aí separar `app/` em repo próprio) |
| D4 | Contrato anti-pulo: janela de tamanho fixo, cada área com altura reservada, números com `tabular-nums`, status em uma linha com reticências, transição só de opacidade e cor; botão não se move no clique (nada de `translate`/`scale`) | é a queixa nº 1; Tauri não impede layout que pula | opus | alta | o Gabriel pedir movimento no clique depois de ver a vitrine |
| D5 | Design system próprio do Reco em `design/` (DESIGN.md + tokens.css + vitrine); herda do Lacre só o **método** | regra da casa: design system nunca se compartilha entre produtos | regra | alta | — |
| D6 | O motor (`engine/`) é dono do config e dos contratos: o casco Rust nunca grava `~/.reco_config.json`; `tools/transcrever.py`, nomes `x.txt`/`x.mp3.txt`, etiqueta `RECO_TAG` e `Reco.exe --transcribe` continuam valendo | um dono só por contrato; o coletor de WhatsApp quebra em silêncio se o contrato mudar | opus | alta | — |
| D7 | Mesmo mutex `Local\Reco.SingleInstance` no app novo: o velho e o novo se excluem (só um grava) | evita dois processos nos mesmos endpoints e no mesmo config (ARMADILHAS § config regravado) | opus | média | a Fase 4 precisar dos dois abertos para comparar (aí mutex próprio + config de leitura) |
| D8 | MP3 continua o formato; o encoder Rust reproduz joint stereo e ABR do LAME, e mudar para `Mode::Stereo` só com gate próprio (medir_aec + dominância) | todas as réguas foram medidas sobre joint stereo; 9 ferramentas e a skill do Instagram abrem `.mp3` | opus | alta | o gate mostrar que estéreo puro melhora a diarização |
| D9 | Mac fora do escopo (segue congelado por falta de Mac M1+); o Tauri deixa a porta aberta | sem hardware não há prova | opus | alta | aparecer um Mac |
| D10 | Ao vivo segue no escopo (paridade); na Fase 5 o áudio cru vai ao motor por canal binário próprio, nunca por JSON Lines | o ao vivo existe e tem teste de 20 min pendente; JSON Lines não aguenta PCM | opus | média | o spike da Fase 5 mostrar canal mais simples |
| D11 | Contrato de falha entre processos (vale da Fase 2 em diante): casco morre gravando → o motor vê o stdin fechar, para e fecha o MP3 com o cabeçalho; motor morre gravando → o casco mostra alarme visível e nunca exibe "gravando" sem gravar (o reinício automático do Lacre não religa gravação sozinho); Sair no meio da gravação → o casco pede `rec.stop` e espera o arquivo fechar antes de encerrar (sem o corte de 8 s do Lacre durante gravação) | separar tela e motor cria três jeitos novos de perder gravação; hoje "sair no meio salva o MP3" | opus + advisor | alta | — |
| D12 | "Rápido" tem régua: ao fim da Fase 4, o app novo fica pronto para gravar em tempo menor ou igual ao do app atual medido na Fase 0, e o clique em Gravar não espera a GPU | sem teto, "rápido" vira opinião; o OpenVINO já é importado só quando transcreve (`reco.py:1115`, `reco.py:2062`), então gravar não paga a GPU | opus + advisor | média | a medição da Fase 0 mostrar que o motor congelado não sobe a tempo (aí antecipar a captura em Rust) |

Com a captura em Rust (Fase 5), quem grava é o casco: a 1ª cláusula de D11 vale para a captura Python, e
para a Rust vale a F5-D14 (o cabeçalho de duração é reescrito a cada 5 s, então um casco morto deixa um MP3
legível com no máximo 5 s de duração errada). Se o spike da Fase 5 reprovar isso, a captura vai para
processo filho (reabre a F5-D1).

`is_reco_recording` (`reco.py:136-138`) só olha a etiqueta `reco` no nome do arquivo, não processo nem mutex: a
troca de app não o afeta, mas a etiqueta `RECO_TAG` no nome é contrato (D6).

## O que NÃO fazer

- **Não reescrever tudo de uma vez.** Seis meses sem app novo e o velho sem manutenção é o pior dos mundos;
  e a lógica medida (AEC, alinhamento, anti-loop) perderia a paridade sem régua.
- **Não usar Meetily, Vibe ou Anarlog no lugar do Reco**: perde L/R separado, AEC e OpenVINO.
- **Não forkar** Meetily (núcleo mono, 398 issues, produto pago por cima) nem Anarlog (150 crates, nuvem).
- **Não copiar o design do Lacre** (`styles.css`, teal `--seal`, selo): regra da casa.
- **Não herdar a "Regra da Vida" do Lacre** (botão que sobe e afunda): é movimento, e o Gabriel reclamou de
  movimento. Só entra se ele pedir depois de ver a vitrine.
- **Não copiar o `render()` do Lacre** que refaz a árvore inteira: o Reco tem VU a 20 Hz, cronômetro e texto
  ao vivo; atualização é pontual por componente.
- **Não passar áudio cru por JSON Lines**, nem pelo `emit` do Tauri a cada bloco.
- **Não usar PortAudio/`sounddevice`** nem crate em cima dele: reprovado neste hardware (ARMADILHAS).
- **Não continuar a modularização do `reco.py` em 4 fases**: a reescrita a torna obsoleta; vale só a lista de
  fronteiras (audio_io / dsp / captura / transcrição / ui) como mapa.
- **Não mudar o formato do arquivo** (FLAC, Opus) nem o modo estéreo sem gate (D8).
- **Não prometer transcrição mais rápida por causa do Rust**: o motor C++ é o mesmo.

## Riscos e pré-requisitos

- **Perda de gravação na troca (risco `dado`):** começa na Fase 2, quando tela e motor viram processos
  separados, não só na Fase 5. Mitigado por D11 (contrato de falha, provado matando cada processo no meio de
  uma gravação e conferindo arquivo íntegro + aviso), D7 (só um app grava), app velho como reserva até a
  Fase 4 fechar, gates de disco e teste sob carga antes de a captura Rust virar padrão (Fase 5).
- **"Rápido" pode não vir na Fase 3:** o motor Python congelado leva segundos para subir e a GPU custa
  14,6 s e 1,35 GB por processo (ARMADILHAS). Mitigação: motor sobe com o app (que vive na bandeja), aquece
  em segundo plano, e Gravar não depende da GPU. A Fase 0 mede; a Fase 5 tira o motor do caminho de gravar.
- **Bandeja no Tauri:** o Reco de hoje mostra a janela no hover do ícone sem roubar o foco. Não confirmado
  no Tauri 2; a Fase 0 prova antes de a Fase 3 depender disso.
- **`openvino-genai` em Rust no Windows:** o CI da Intel roda `windows-latest` com OpenVINO 2026.1 e 2026.4,
  mas só com `runtime-linking`, e o crate liga `openvino_genai_c.dll`, que a wheel de hoje não traz. A Fase 6
  é um spike com portão; se fechar, a transcrição fica no Python.
- **Sentinela da central:** `central/tools/testa_canais.py:360-366` procura no `reco.py` o literal que
  `central/canais_comuns.py:38` define (`SEM_CONTEUDO_RECO`); se o `reco.py` sumir, o `if os.path.isfile`
  vira no-op em silêncio. A Fase 7 atualiza (com o portão da Fase 6 aberto, o literal mora em dois lugares).
- **`CARGO_TARGET_DIR` desta máquina é `C:\pt`** (hub do Lacre): o binário do build não fica em `app/src-tauri/target`.
- **Windows sem assinatura:** SmartScreen e Defender podem acusar o instalador (o Lacre já pagou isso; ver
  `C:\Dev\lacre\docs\LIMITATIONS.md`).
- **Roadmaps em voo afetados** (a Fase 0 deixa uma linha em cada um): modularização (superada), salto de
  alinhamento (a Fase 5 absorve o que falta; A1+A1b no Python continuam valendo se alguém executar antes),
  dispositivo Auto (Fase 2 do vigia de zero vira especificação da Fase 5), modo nota (Fases 2 e 3 absorvidas
  pela Fase 3 daqui), ao vivo (o teste de 20 min reabre na Fase 5), antieco (independente, segue).

## Pendente (decisão do Gabriel)

- **Direção visual** (Fase 1): escolher uma das 2 ou 3 direções da vitrine. Não bloqueia as Fases 0 e 2.
  `dono: gabriel`.
- **Híbrido × tudo em Rust** (não bloqueia nada): ao fim da Fase 4 ele recebe o casco e a tela em Rust, o
  motor em Python por dentro e a transcrição na mesma velocidade de hoje. Recomendação: seguir o híbrido
  (D1) e deixar a Fase 6 decidir com números se a transcrição também vai para Rust. Se ele quiser zero
  Python mesmo sem ganho medido, vira escopo dele e a Fase 6 deixa de ter portão. `dono: gabriel`.

## Crítica do advisor

- **1ª tentativa:** a ferramenta respondeu "rate-limited" antes da escrita; nenhum parecer foi inventado.
- **2ª consulta (11/11/2026, só o índice; os md-fase ainda estavam sendo escritos):**
  - Risco de gravação começa na Fase 2 (casco morre, motor morre, sair no meio) → **aplicado**: D11 e
    o item de risco reescrito.
  - `is_reco_recording` não listado → **conferido e aplicado**: só olha o nome do arquivo (nota após D11).
  - "Rápido" sem régua → **aplicado**: D12; o OpenVINO já é importado tarde.
  - Fases 5 a 7 envelhecem → **aplicado**: item 5 de "Como retomar".
  - Expectativa "em Rust" → **aplicado**: segundo item de Pendente.
  - Repo público × relatórios do sidecar → **aplicado no commit**: limpeza dos caminhos locais antes do push.
- **3ª consulta (11/11/2026; alcance: relatos dos auditores, crítica de coerência e conferência, não o texto
  inteiro das 8 fases):**
  - D11 nas Fases 2 a 4 → **conferido**: Fase 2 passo 7 (EOF do stdin), Fase 3 (casco e motor mortos), Fase 4
    passo 15 e P26.
  - Fase 0 sem rede do config → **aplicado**: cópia no passo 9 e conferência/reposição no passo 14 (as gravações
    de teste já iam para `temp/medicoes/`).
  - `testar-contrato.cjs --url` na Fase 3 → **conferido** (2 ocorrências).
  - D1 com "advisor indisponível" → **corrigido**.
  - Spike da Fase 6 cedo → **aplicado** como nota abaixo da tabela das fases.
  - Textos "fora do git" nas fases → **conferido**: falam de `temp/` e build, não do md.

## Sidecar

`2026-11-11-melhoria-reco-em-rust.d/`: `diagnostico/` (as 5 frentes e a crítica de completude, 11/11/2026)
e, depois, um relatório por fase executada.
