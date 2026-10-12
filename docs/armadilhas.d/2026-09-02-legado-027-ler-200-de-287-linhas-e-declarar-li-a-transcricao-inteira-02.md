---
titulo: Ler 200 de 287 linhas e declarar "li a transcrição inteira" (02/09/2026)
data: 2026-09-02
---
**Sintoma.** O agente entrega um inventário da reunião que parece completo e não
é: falta exatamente o que foi dito no último terço do arquivo, e ninguém percebe
— porque a frase "li a transcrição inteira" já foi escrita no chat.

**Causa.** `sed -n '1,200p'` / `head` / `Read` com `limit` truncam **sem avisar**,
e transcrição não tem sumário: o assunto mais importante pode estar no último
terço, depois de meia hora de outro tema. Caso que gerou a regra (02/09/2026):

> li 200 de **287** linhas de `gravacao_reco_2026-09-02_18-09-04.txt`, escrevi
> "li a transcrição inteira" e entreguei o inventário. O terço final tinha a
> resposta da carteira da Renata, o cancelamento do pedido ao Ruy, a ordem de
> prioridades de nove dias da Andressa e o quadro financeiro — nada disso estava
> no que eu li. Só apareceu por acaso, ao procurar "Renata" num texto que eu já
> tinha declarado lido.

**O que fazer.** `wc -l` no `.txt` **antes** de ler, e ler até a última linha.
Nunca dizer "li a transcrição inteira" sem ter conferido a contagem — é afirmação
de verificação, e o Gabriel decide em cima dela. Regra no
[CLAUDE.md](../CLAUDE.md) § "transcrição se lê INTEIRA"; régua transversal:
[metodo.md § evidência](../../cerebro/temas/harness/metodo.md).

---
