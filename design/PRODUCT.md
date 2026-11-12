# Product

<!-- impeccable:product-schema 1 -->

> Respostas tiradas do roadmap, sem entrevista (sessão sem humano, 11/11/2026): fonte
> `roadmap/2026-11-11-melhoria-reco-em-rust.md`, o md da Fase 1 e o hub do projeto. O que é
> inferência está marcado como tal.

## Platform

web

Interface em HTML/CSS dentro do WebView2 de um casco Tauri 2 no Windows (Fase 3). A vitrine desta
pasta é a mesma interface servida como página standalone.

## Stack

delegated: Tauri 2 + TypeScript + Vite sem framework, motor Python atual como processo filho
(decisões D1 e D2 do roadmap). Nesta fase só existe HTML de demonstração em `design/`.

## Users

- **O Gabriel, sozinho.** Grava reuniões (Teams, Meet, WhatsApp) e ditados, quase sempre no meio de
  uma chamada, com a atenção na conversa e não no app.
- **Os agentes da casa**, que não veem a tela: usam o Reco pela linha de comando
  (`tools/transcrever.py`, `Reco.exe --transcribe`). Isso é contrato, não interface.

## Product Purpose

Gravar microfone e áudio do sistema num MP3 estéreo (esquerda = ele, direita = os outros) e
transcrever local, de graça, com quem falou separado por canal. Sucesso é:

- gravar sem pensar: um clique, de relance, durante a chamada;
- achar a transcrição depois: o caminho copiado, a biblioteca com busca por conteúdo;
- nada se mexe: a janela e os botões ficam parados em todo clique (a queixa nº 1, 11/11/2026).

## Positioning

Grava os dois lados separados (L/R) e transcreve na própria máquina com OpenVINO na iGPU, com antieco
e diarização por canal. Apps vizinhos (Meetily, Vibe) misturam os canais em mono ou mandam o áudio
para a nuvem.

## Operating Context

- Janela pequena ancorada à bandeja do Windows; aparece no hover do ícone sem roubar o foco e some no
  X. Usada de relance durante a chamada, por segundos.
- Monitor principal a 125% de escala; a menor área útil medida é 2048 × 816 lógicos.
- Ritual: grava a reunião, para, clica uma vez (salva e copia o caminho entre aspas) e cola o caminho
  numa conversa com um agente, que transcreve e resume.
- Modo **Operate** da skill: a interface serve a tarefa; a marca vive nos detalhes.

## Capabilities and Constraints

- Funções de hoje (19, inventário no `DESIGN.md` § Telas): gravar, pausar, parar, ganho por canal,
  ao vivo, nota, biblioteca com busca e resumo IA, transcrever e converter arquivo, opções, bandeja,
  atalho, atualizações, PT/EN.
- Formato fixo (16 kHz estéreo, ABR 96k) e biblioteca no filesystem: não são interface, não mudam.
- Offline: nada baixado em tempo de execução, só fontes do Windows.
- Gravar nunca espera a GPU (D12): o único tempo de espera visível é o motor subindo (≈ 5,4 s medido
  na Fase 0, 7,4 s na primeira partida).
- Indecidido: a direção visual (escolha do Gabriel na vitrine).

## Brand Commitments

- Nome: Reco. Ícone atual: `logo/logo_symbol_1x1.ico`. Cor histórica de destaque: coral (`reco.py`).
- Identidade própria: nada do Lacre nem de outro produto da casa (regra: design system nunca se
  compartilha).
- Ícones Lucide (decisão de 12/08/2026), nunca emoji.

## Evidence on Hand

- Medições da Fase 0 (`roadmap/2026-11-11-melhoria-reco-em-rust.d/fase-0-relatorio.md`).
- Nomes de dispositivo e textos reais de status em `reco.py`. Não há depoimento nem número de uso: não
  inventar.

## Product Principles

1. Nada se mexe sozinho: tamanho fixo, áreas reservadas, só cor e opacidade mudam.
2. Tudo à vista: nenhuma ação só no hover, nenhuma navegação por link de texto.
3. Uma ação principal por estado, com o nome do que acontece.
4. O motor demora, a tela não: estado de espera explícito, nunca um botão que não responde.
5. O produto é o arquivo: caminho, transcrição e pasta sempre a um clique.

## Accessibility & Inclusion

Teclado completo com foco visível, contraste AA nos dois temas, movimento reduzido respeitado, cor
nunca como único sinal (inferência do roadmap, regras R9, R11, R12 e R14 do `DESIGN.md`).
