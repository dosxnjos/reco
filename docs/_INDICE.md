---
tipo: indice
projeto: reco
atualizado: 2026-11-12
---
# Índice dos docs do Reco

Um link por doc, com o que tem dentro e quando ler. A regra que vale sempre está no
[CLAUDE.md](../CLAUDE.md); aqui fica só o mapa.

## Docs deste repo

- [ARMADILHAS.md](ARMADILHAS.md): o que **parece** funcionar e não funciona (sintoma → causa →
  o que fazer), uma entrada por caso datado. Leia antes de mexer em transcrição, AEC, captura,
  alinhamento dos canais ou benchmark. **Gerado** (fora do git) de `armadilhas.d/` (um arquivo por
  entrada, versionado): entrada nova é `python tools/visoes.py novo "título"`, nunca `Edit` na página.
- [ARQUITETURA.md](ARQUITETURA.md): como cada peça funciona por dentro e o que **não** é
  acidente (build, MP3 por container, `_pump`, AEC só na transcrição, anti-loop, biblioteca e
  resumo IA, ícones, config, motor e o casco Tauri do app novo em `app/`). Leia antes de mudar
  comportamento do app ou recompilar.
- [PROTOCOL.md](PROTOCOL.md): contrato JSON Lines entre o motor sem janela (`engine/`) e a
  interface nova (comandos, eventos, códigos de erro, timeouts, CLIs, contrato de falha). Leia antes
  de mexer no motor ou de escrever o casco Tauri (Fase 3 do roadmap Reco em Rust).
- [TOOLS.md](TOOLS.md): para que serve cada script de `tools/`, com o gate e o número medido.
  Leia antes de medir, transcrever em lote ou criar ferramenta nova.
- [design/](../design/DESIGN.md): identidade e contrato de tela da interface nova (`DESIGN.md` com as
  regras R1–R15 e as skins Fita, Caderno e Instrumento; `PRODUCT.md`; `tokens.css`; `vitrine.html`, gerada
  por `montar-vitrine.cjs`; testes `testar-anti-pulo.cjs` e `testar-contrato.cjs`). Leia antes de desenhar
  ou mexer em qualquer tela da interface nova.
- [README.md](../README.md): vitrine do repo público (recursos, rodar do fonte, gerar o app), em
  inglês e português. Leia para explicar o Reco a quem não o conhece; não é doc interna.

## Planos e decisões

- [roadmap/README.md](../roadmap/README.md): índice gerado dos roadmaps (ativos, sem passos,
  fechados; fora do git desde 12/10, os hooks de `tools/visoes.py` o recompilam). Leia para saber por que decidimos X, o que foi descartado e o que está em voo.

## Ainda não existe

- `docs/MODULOS.md` (mapa de onde foi parar cada símbolo): nasce com a
  [modularização do `reco.py`](../roadmap/2026-10-02-melhoria-modularizacao.md); até lá o código
  segue quase todo no `reco.py`.
