---
titulo: Smoke só com hello aprova motor congelado que não importa o reco
data: 2026-11-12
---
**Sintoma:** o `app/build.ps1` terminava com "Instalador: …" mesmo com o motor congelado quebrado: o smoke
imprimia `hello ok=True` e `shutdown ok=True exit=0`, e o `devices ok=False` da última rodada passava sem
ninguém julgar. O app instalado abriria e responderia `unavailable` a todo Gravar. Achado da revisão
adversarial da Fase 3 (12/11/2026), lido no código.

**Causa:** o motor responde o `hello` **antes** do `import reco` (F2-D3, `boot.py`); o import roda em segundo
plano e termina no evento `ready`, que vem com `error` se falhar. Um congelamento do PyInstaller sem um import
oculto (a falha clássica do onedir) passa no `hello` e no `shutdown`.

**O que fazer:** julgar o `ready` e um comando que use o `reco`. O `engine/build.py` sai com 1 se o `ready`
traz `error` ou o `devices.list` falha (`--motor <cmd…>` prova o julgamento com um motor falso), e o
`Assert-Smoke` do `app/build.ps1` exige `ready ok=True` em toda rodada e `devices ok=True` na última.
