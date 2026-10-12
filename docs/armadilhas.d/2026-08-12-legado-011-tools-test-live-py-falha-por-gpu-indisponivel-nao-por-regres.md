---
titulo: `tools/test_live.py` falha por GPU indisponível, não por regressão (12/08/2026)
data: 2026-08-12
---
**Sintoma.** Rodar `tools/test_live.py <mp3> 60` nesta máquina imprime
`FALHOU: critério = latência mediana <= 5s` (saiu 9,8s de mediana), acompanhado
de dezenas de linhas `onednn_verbose... errcode -59, CL_INVALID_OPERATION` e
`no opencl gpu device is available`.

**Causa.** O device resolvido pelo pipeline (`AUTO` → `GPU`) não conseguiu abrir
o backend OpenCL no momento do teste — cai pra CPU em silêncio, que é bem mais
lento pro modo ao vivo. **Não é regressão de código**: confirmado em
`roadmap/2026-08-12-melhoria-ux-ui-logica.md` Fase 1 (execução de 12/08)
rodando o mesmo teste antes e depois do patch (`git stash`) — falha idêntica
nos dois lados.

**O que fazer.** Não tratar uma falha desse teste como sinal de bug introduzido
sem antes descartar causa ambiental: rodar `git stash` (ou comparar contra o
commit anterior) e repetir o teste. Se a falha persistir idêntica dos dois
lados, é o ambiente (GPU ocupada/indisponível naquele momento), não o código.
O roadmap de 12/08 (Fase 1.4) cita esse script como prova de não-regressão do
`LiveTranscriber.stop(discard=True)` — ele serve pra isso (o app não trava, a
passada final roda), mas **não** serve como gate de latência enquanto esse
problema de GPU não for investigado à parte.
