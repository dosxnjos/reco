---
titulo: `print` com emoji derruba script no console desta máquina (19/08/2026)
data: 2026-08-19
---
**Sintoma.** `UnicodeEncodeError: 'charmap' codec can't encode characters` no meio
de um teste de hardware que já tinha começado a gravar — perdendo a execução
inteira por causa de uma linha de aviso.

**Causa.** O console do Windows aqui é **cp1252**; `⚠️` (e qualquer caractere fora
dessa página) não tem representação, e o `print` levanta exceção em vez de degradar.

**O que fazer.** Nos **scripts de `tools/`**, prints em ASCII puro (`***`, `!`,
`->`). Emoji só em arquivo de texto (md, docstring que ninguém imprime) e na UI do
Tkinter, que é Unicode de verdade. Vale principalmente para script longo: falhar no
minuto 2 de um teste de 3 minutos por causa de um aviso é o pior custo possível.
