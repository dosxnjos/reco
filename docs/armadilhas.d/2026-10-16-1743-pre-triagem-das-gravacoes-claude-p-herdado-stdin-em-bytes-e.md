---
titulo: Pré-triagem das gravações: claude -p herdado, stdin em bytes e custo por chamada (16/10/2026)
data: 2026-10-16
---
**Sintoma.** No piloto de `tools/pretriar_transcricoes.py`, toda leitura saiu `?` com
"bytes enviados 46514 != arquivo 47356": o texto que ia ao `claude -p` era menor que o `.txt`.

**Causa.** `Path.read_text()` e `subprocess.run(text=True)` traduzem `\r\n` ↔ `\n`; a
transcrição tem CRLF, então o "enviado inteiro" não era o byte do arquivo (e a prova do
"li inteira" mentia). Além disso, `claude -p` chamado de dentro de uma sessão herda
`CLAUDECODE`, `CLAUDE_CODE_*` e `CENTRAL_*` (sessão fantasma no board, card errado) e, com o
settings global em `bypassPermissions`, a fala de terceiros teria `Bash`/`Edit` à mão.

**O que fazer.** Mandar o stdin como **bytes** (`read_bytes()` + `input=bytes`, sem
`text=True`) e comparar `len` com `st_size`. Env limpo (`env_limpo()` do script, cópia de
`central/server.py:_env_limpo` + `SESSOES_ABERTAS_IGNORAR=1`), `--tools ''`,
`--no-session-persistence`. Custo medido em 16/10: ~US$ 0,07 por chamada (~59 mil tokens de
cache por causa do CLAUDE.md global e dos hooks da conta), então 79 leituras ≈ US$ 6 de plano.
