---
titulo: A NPU leva ~7 minutos para compilar o modelo na primeira vez (29/07/2026)
data: 2026-07-29
---
**Sintoma:** ao transcrever pela primeira vez com um modelo novo na NPU, o app
fica parado por vários minutos sem sinal de vida. Parece travamento.

**Causa:** é compilação real do grafo para o acelerador. Medido: **415 s** para
`large-v3-turbo` na NPU (contra ~10 s na iGPU). Fica em `CACHE_DIR`
(`_user_data_dir()/ovcache`), então acontece **uma vez por (modelo, device)** —
mas uma vez por combinação, não uma vez na vida.

**O que fazer:** `_pipeline()` marca cada combinação já compilada com um arquivo
`.compilado-<size>-<device>` no cache e mostra um aviso explícito na primeira vez.
Não remover esse aviso; sem ele o usuário mata o app achando que pendurou.

---
