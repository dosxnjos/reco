---
titulo: Relatório que resume uma amostra vazia inventa conclusão (30/08/2026)
data: 2026-08-30
---
**Sintoma.** `tools/varrer_aec.py` imprimiu *"Nenhum arquivo com ERLE ≤ 0 nesta
amostra — o caso de 15:00 pode ser raro"* tendo medido **zero** arquivos. A frase
é gramaticalmente verdadeira e completamente enganosa; lida rápido, teria
encerrado a investigação do guard do AEC pelo motivo errado.

**Causa imediata.** A lista de caminhos vinha de um arquivo com CRLF, o
`xargs -d'\n'` deixou o `\r` colado no fim de cada path, e o filtro
`a.endswith(".mp3")` rejeitou todos em silêncio. **Causa de fundo:** o resumo
tratava "conjunto vazio" como um resultado em vez de como ausência de resultado.

**O que fazer.** Em qualquer script de medição daqui: (1) `.strip()` no caminho
vindo de arquivo, e falhar alto quando a lista de alvos fica vazia ou um alvo não
existe; (2) o bloco de conclusão testa `if not medidos` **antes** de qualquer
outro ramo e diz "amostra vazia, nada se conclui". É a mesma família de defeito
de `medir_aec.py` escolher as janelas sozinho e de `alinhar_gravacao.py` relatar
`medidos` e escrever `usados` — o instrumento descrevendo algo diferente do que
fez.
