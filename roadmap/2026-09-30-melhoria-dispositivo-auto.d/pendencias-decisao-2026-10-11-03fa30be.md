## Pendências de decisão (execução 2026-10-11, Fase 1)

Só o que é do Gabriel. As decisões técnicas estão em
[relatorio-fase-1-03fa30be.md](relatorio-fase-1-03fa30be.md).

### 1. Fechar o `Reco.exe` e rodar o build do Auto (dono: gabriel) — bloqueia o passo 1.7

- **O que travou:** o `Reco.exe` do Gabriel está aberto (pid 19760, desde 10/10 21:27).
  `build.ps1` com o app aberto falha com `PermissionError` e, antes de falhar, o
  PyInstaller **apaga arquivos de `dist/Reco/_internal`** (Fase 0: 26 arquivos, restaurados).
  Por isso o build **não foi tentado** nesta fase. O código está pronto e commitado
  (`master@8a19d1d`, provas 1.1–1.6 verdes, `test_encoder` e `--selftest` OK).
- **Instrução em 1 linha:** "fecha o Reco, roda
  `powershell -ExecutionPolicy Bypass -File C:\Dev\Reco\build.ps1`, abre o `dist\Reco\Reco.exe` novo".
- **⚠️ Não reabrir o Reco antigo antes disso.** O `~/.reco_config.json` está em `_migracao: 1`
  de propósito (migração 2 só é gravada pelo exe novo). Se o antigo abrir de novo antes do
  build, ele só regrava os ids como sempre (o exe novo migra na 1ª abertura, sem perda).
  Se, por qualquer motivo, o JSON ficar com `_migracao: 2` e ids de dispositivo "reais"
  (não `auto:*`), trocar `_migracao` para `1` antes de abrir o novo.
- **O que verificar no exe novo (Opções):** os dois combos têm "Auto: padrão do Windows (…)" e
  "Auto: padrão de comunicação (…)" no topo; só abrir não muda o JSON.
- **Prova do 1.7 depois do build:** `python -c "import os;print('exe_novo', os.path.getmtime('dist/Reco/Reco.exe') > os.path.getmtime('reco.py'))"`
  → `exe_novo True`. (A fase 2 mexe no `reco.py` de novo e o `exe_novo` volta a `False`: o
  build da Fase 2 reabre a mesma pendência. Dá para pular este build e fazer só o da
  Fase 2 se o Gabriel preferir; a Fase 1 sozinha no exe não é urgente.)
- **O que foi feito no lugar:** nada no `dist/`; o `[ ]` do 1.7 fica com nota no md.
