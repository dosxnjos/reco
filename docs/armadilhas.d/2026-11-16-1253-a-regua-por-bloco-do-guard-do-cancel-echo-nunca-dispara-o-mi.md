---
titulo: A régua por bloco do guard do cancel_echo nunca dispara: o mínimo quadrado não deixa o bloco piorar
data: 2026-11-16
---
**Sintoma:** o conserto desenhado em 30/08 para a rede de segurança do `cancel_echo` (E4b: comparar, em
cada bloco de 2 s, a energia de `Mb - y` com a de `Mb` e zerar o filtro do bloco que piora) parece certo e
não muda nada. Em sinal sintético com acoplamento de −36 dB, o ERLE onde só o interlocutor fala sai −15 dB
e a régua por bloco não passa de 1 em nenhum bloco (o maior valor visto foi 1 + 3e-8, arredondamento num
bloco de um quadro só).

**Causa:** o filtro do bloco é o mínimo de `|Mb - Xb h|^2 + lam |h|^2`, e `h = 0` está entre os candidatos.
Logo o resíduo do bloco nunca passa a entrada do bloco, por construção e bin a bin. O aumento de energia
mora DENTRO do bloco: o filtro usa a referência para explicar a voz do usuário e, nos quadros em que só o
interlocutor fala, soma o eco estimado a um mic quase mudo. Somado no bloco, o ganho na voz paga o dano no
eco. É o mesmo defeito da rede global (legado-024) uma escala abaixo: régua mais larga que o dano.

**O que fazer:** a régua tem de ser do tamanho do dano. Desde 16/11/2026 (#21) ela é por QUADRO da STFT e
sobre a saída DEPOIS da pós-supressão (`aec_guarda.sem_piora`, logo antes do `istft`): quadro com mais
energia que a entrada volta a ser o do mic. Comparar o resíduo linear em vez da saída final custou 0,5 a
1,2 dB de ERLE nos casos sãos (tirava a supressão de quadros que ela já resolvia). Prova sintética:
`tools/test_aec_guarda.py`; medir em áudio real com `tools/medir_aec.py` antes de afirmar ganho no app.
Regra geral: antes de escrever um guard "se piorou, desliga", conferir se o estimador já não garante
"não piora" na escala escolhida; se garante, o guard é código morto.
