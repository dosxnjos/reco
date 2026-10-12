---
titulo: `tools/test_alinhamento.py` está vermelho desde que nasceu (30/08/2026)
data: 2026-08-30
---
**Sintoma.** O `CLAUDE.md` manda rodá-lo "sempre que mexer em
`estimar_offset`/`_al_*`/`_pump`", e o roadmap de 19/08 o lista como prova da
Fase 1 — mas ele termina em `1 FALHA(S)`. Quem rodar pela primeira vez vai supor
que quebrou por causa da própria mudança.

**Causa.** O caso 8 ("gravação longa simulada: jitter de atraso corrigido na
reestimativa") deixa **+352 amostras (22 ms)** de residual na janela que contém a
transição (`0s=+0, 10s=+0, 20s=+0, 30s=+352, 40s=+0`), contra um gate de 160.
Determinístico — as seeds do gerador sintético são fixas. Verificado com
`git worktree` no `HEAD`, no `HEAD` sem trabalho não commitado de outras sessões,
e **no próprio commit que criou o teste** (`4714ee0`): falha nos três.

**O que fazer.** Antes de mexer na Fase C do roadmap de 21/08, decidir se os
22 ms são defeito real do `_al_corrigir_deriva` (é o mesmo fenômeno de
recuperação lenta que a Fase C existe para consertar, então C1 provavelmente já
o corrige) ou gate apertado demais para uma janela que contém a transição.
**Não relaxar o gate sem responder isso** — seria apagar o sinal em vez do
defeito. Enquanto estiver vermelho, "meus casos novos passam" e "o teste falha
pelo motivo de sempre" são indistinguíveis. Passo `C0` em
[roadmap/2026-08-21-salto-de-alinhamento-sob-carga.md](../roadmap/2026-08-21-salto-de-alinhamento-sob-carga.md).

⚠️ De quebra, a linha de falha imprime `(pior: -1)` quando o valor que reprovou
é `+352` — o teste não reporta o número com que decidiu.
