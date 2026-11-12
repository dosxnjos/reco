---
titulo: O build do app novo falha no npm ci (-4048) com o ui:preview rodando
data: 2026-11-12
---
**Sintoma:** `powershell -File app/build.ps1` congela o motor, passa no smoke e para em
`ERROR: npm ci failed (npm ci --no-audit --no-fund exited with -4048)`; o `app/node_modules` fica pela metade
(6 entradas). Visto em 12/11/2026, com o `npm --prefix app run ui:preview` (porta 1431) aberto para os testes
da Fase 1 com `--url`.

**Causa:** o `npm ci` apaga o `app/node_modules` inteiro antes de reinstalar, e no Windows o `vite preview` em
execução segura arquivos de lá (o `node` dele e o binário do esbuild): a remoção falha com `EPERM`
(-4048). O build não sabe que há outro processo usando a pasta.

**O que fazer:** nunca rodar o `ui:preview` (nem o `vite` de dev) junto com o `app/build.ps1`: primeiro o build,
depois os testes com `--url` (ou o contrário, parando o servidor pelo pid antes). Se o build já falhou assim, parar
o servidor e rodar de novo; com o motor congelado na mesma rodada, `app/build.ps1 -SemCongelar` basta.
