---
tipo: indice
projeto: reco
atualizado: 2026-10-02
---
# Índice dos docs do Reco

Um link por doc, com o que tem dentro e quando ler. A regra que vale sempre está no
[CLAUDE.md](../CLAUDE.md); aqui fica só o mapa.

## Docs deste repo

- [ARMADILHAS.md](ARMADILHAS.md): o que **parece** funcionar e não funciona (sintoma → causa →
  o que fazer), uma entrada por caso datado. Leia antes de mexer em transcrição, AEC, captura,
  alinhamento dos canais ou benchmark.
- [ARQUITETURA.md](ARQUITETURA.md): como cada peça funciona por dentro e o que **não** é
  acidente (build, MP3 por container, `_pump`, AEC só na transcrição, anti-loop, biblioteca e
  resumo IA, ícones, config). Leia antes de mudar comportamento do app ou recompilar.
- [TOOLS.md](TOOLS.md): para que serve cada script de `tools/`, com o gate e o número medido.
  Leia antes de medir, transcrever em lote ou criar ferramenta nova.
- [README.md](../README.md): vitrine do repo público (recursos, rodar do fonte, gerar o app), em
  inglês e português. Leia para explicar o Reco a quem não o conhece; não é doc interna.

## Planos e decisões

- [roadmap/README.md](../roadmap/README.md): índice gerado dos roadmaps (ativos, sem passos,
  fechados). Leia para saber por que decidimos X, o que foi descartado e o que está em voo.

## Ainda não existe

- `docs/MODULOS.md` (mapa de onde foi parar cada símbolo): nasce com a
  [modularização do `reco.py`](../roadmap/2026-10-02-melhoria-modularizacao.md); até lá o código
  segue quase todo no `reco.py`.
