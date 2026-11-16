---
titulo: Letras de outra escrita numa transcrição em português: filtrar antes da conta de cópias, não depois
data: 2026-11-16
---
**Sintoma:** numa transcrição em português aparecem ideogramas ou katakana soltos (#34). Medido numa gravação longa
só de mic: trechos inteiros do Whisper em outra escrita, de um caractere só e sem palavra latina junto, e trechos só
de pontuação. Com a língua forçada em `pt`, o Whisper ainda devolve outra escrita em janela de ruído. A guarda de eco
do #31 tirava as cópias repetidas desses trechos, mas não os que apareciam até 3 vezes. Números no roadmap
`2026-11-16-issues-17-21-22-34.md`, passo 2.

**Causa:** nada filtrava a escrita do texto pronto. Conserto: `antiloop.na_escrita`, chamado pelo `sem_eco` com o
`lang` do `transcribe` (pt, en ou pl): sai a letra não latina e a pontuação larga, e sai o trecho sem letra nem dígito
(inclusive o só de pontuação). Teste `tools/test_escrita.py`.

⚠️ **O filtro roda antes da conta de cópias do `sem_eco`, nunca depois.** O trecho de outra escrita fica entre as
cópias do enchimento e a conta o vê como fala diferente: "cópia, cópia, 嗯, cópia, cópia" passa como duas corridas de 2.
Se o filtro tirar o 嗯 depois da conta, as quatro cópias ficam encostadas e a régua (`paridade.py`, pior > 3) reprova.
Por isso, com o filtro, a guarda de eco pode tirar mais cópias de enchimento do que tirava antes (é o efeito desejado;
na gravação medida, nenhuma a mais), e nenhuma palavra latina sai pelo próprio filtro (medido: a mesma contagem antes
e depois).

Também não: filtrar o `contexto` (o `initial_prompt`) ou o `segs` dentro do `_transcribe_channel`. Mexer no que o
Whisper vê muda o texto de todas as janelas seguintes (armadilha do eco entre janelas, 16/11). E não usar "nome Unicode
começa com LATIN" sozinho: `ª`, `º` e `µ` não têm LATIN no nome e são do texto em português ("1º", "2ª").

**Custo declarado:** sem língua, ou com outra língua (`transcrever.py --lang ja`), não há filtro. Em pt, en ou pl, uma
palavra estrangeira escrita na escrita dela (nome em cirílico, termo em japonês) sai. O rascunho ao vivo não passa pelo
filtro. O enchimento em português que sobra em trincas não é resolvido por ele.
