## Relatório de execução — Fase 4 (2026-11-12, sessão 4c65eb01)

> **Parcial.** Esta rodada adianta os passos 1 a 8 que não dependem do dono. Condição: o Reco velho do dono **aberto**
> (`dist\Reco\Reco.exe`) e o dono usando a máquina. Nada instalou, desinstalou, abriu o Reco Novo ou o casco contra o
> motor real; nenhum mouse ou teclado; nenhuma prova que grava. As gravações dele foram lidas só por **cópia**, numa
> pasta temporária fora do repo; nomes de gravação viram G01 a G10 aqui (repo público). Nada foi publicado no GitHub.

Fase: [fase-4](../2026-11-11-melhoria-reco-em-rust-fase-4.md) · índice: [Reco em Rust](../2026-11-11-melhoria-reco-em-rust.md).

### Frescor (item 5 de "Como retomar")

- `git diff --stat 7c5c1a1..HEAD -- reco.py tray.py tools/varrer_silencio.py tools/varrer_acervo.py tools/reparar_duracao.py tools/test_antiloop.py tools/transcrever.py`
  → vazio: as linhas citadas desses arquivos valem como escritas em 11/11 (conferidas uma a uma as do `reco.py` e das ferramentas).
- O que mudou desde 11/11 e o md citava: `app/` e `engine/` (Fase 3). Notas datadas no md: passo 1 (sem `mainBinaryName`,
  binário `reco.exe`), passo 6 (nome com espaço, cópias), passo 7 (nunca `--forcar` na pasta do app), passo 8 (`app_name`
  no `lib.rs:207`, outras ocorrências, formato do log), passo 14 (regex do `ready em`) e F4-D9 (o aviso de versão compara
  com o `reco.APP_VERSION`, não com o casco).

### Reserva (passo 2)

- Cópias feitas às 15:57 de 12/11 por `robocopy … /E` (rc `1` nas duas = arquivos copiados, sem erro), em ~5 s.
- `Reco.exe` da reserva: SHA256 `6F9A4599B336DBEE853AA4613B3200A4622C4EB3481F0170987CE966C4EF442F`, data do arquivo
  `2026-11-11 19:03:45` (o mesmo do `dist`). Nada foi apagado; o velho seguiu aberto (mutex `True` e o processo com o
  caminho do `dist` depois do smoke). O `--selftest` sai antes do mutex e da janela.

### Passos

| passo | estado | prova (comando → o que veio) |
| --- | --- | --- |
| 1 nomes e versão | [x] | `node -p "…[c.productName,c.version,c.identifier,c.mainBinaryName].join(' ')"` → `Reco Novo 0.3.0 io.github.dosxnjos.reco ` (o 4º vazio: sem `mainBinaryName`, o binário é `reco.exe`) |
| 2 reserva | [x] | conferência do md → `True`. Além dela, soma da árvore inteira (caminho relativo + SHA256 de cada arquivo): `dist\Reco` e `Reco-reserva\Reco` → `4010 arquivos, 891997220 bytes, soma 9126509F…9C11DCCB` nos dois; `Reco\models` e `Reco-reserva\models` → `46 arquivos, 828097157 bytes, soma 45BBD98A…400D7F0C` nos dois. Smoke `Start-Process …\Reco-reserva\Reco\Reco.exe --selftest -Wait` → `exit=0`, `reco_selftest.txt` reescrito depois do lançamento (`novo=True`), `transcription_available=True`, `resolved(AUTO)=GPU` |
| 3 foto do que o instalador toca | [x] | `Reco.lnk` → `sem lnk`; `reg query …\Run /v Reco` → rc `1` (não existe); `_migracao` → `2`; modelos → `828097157` bytes (789,7 MiB). Extras: `Reco Novo.lnk` existe, `/v "Reco Novo"` rc `1`, Reco Novo instalado (`uninstall.exe` presente, `reco.exe` SHA256 `b1eef366…ea3d9dbd`, o do `aac7ca7`) |
