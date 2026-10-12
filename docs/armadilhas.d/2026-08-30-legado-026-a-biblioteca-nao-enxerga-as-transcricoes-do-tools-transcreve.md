---
titulo: A biblioteca não enxerga as transcrições do `tools/transcrever.py` (30/08/2026)
data: 2026-08-30
---
**Sintoma.** Gravação com transcrição pronta no disco aparece na view
"Gravações…" **sem o ✓** da coluna 📄, não é achada pela busca por conteúdo, e os
botões "Abrir transcrição" e ✦ Resumo IA ficam desabilitados. Contado em
30/08/2026 na pasta do Gabriel: **14 dos 47 `.txt` (30%)** estão nessa situação.

**Causa.** Existem **duas convenções de nome** e a biblioteca só lê uma:

| escritor | regra | resultado |
| --- | --- | --- |
| `reco.py` `_autosave_txt` (o app) | `audio.with_suffix(".txt")` | `x.mp3` → `x.txt` |
| `tools/transcrever.py` | `src.with_suffix(src.suffix + ".txt")` | `x.mp3` → `x.mp3.txt` |

Os cinco pontos de leitura da view (`_lib_sync_actions`, `_lib_scan_thread`,
`_lib_txt_content`, `_lib_open_txt`, `_lib_resumo`) usam `p.with_suffix(".txt")`,
que nunca resolve para `x.mp3.txt`. Cada convenção está certa sozinha — e o
`CLAUDE.md` documenta as duas, em seções diferentes, sem notar a colisão.

**O que fazer.** **Ler as duas convenções, escrever uma.** O conserto é uma função
de resolução (`_txt_de`) trocando os cinco pontos de leitura — não renomear os 14
arquivos, que é irreversível na prática e quebra o "pula `.txt` existente" do
`transcrever.py`. Passo `E3a` em
[roadmap/2026-08-21-salto-de-alinhamento-sob-carga.md](../roadmap/2026-08-21-salto-de-alinhamento-sob-carga.md)
§ 4.14. ⚠️ Consequência que já mordeu: a transcrição **limpa** de 21/08 16:52
(`…_alinhado.mp3.txt`) é uma das 14 — a decisão de renomear a contaminada tirava a
errada da busca sem pôr a certa no lugar (§ 4.15 do mesmo roadmap).

---
