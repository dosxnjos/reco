---
titulo: Botão que troca de papel recebe o 2º clique do duplo clique
data: 2026-11-12
---
**Sintoma:** na interface nova, um duplo clique no botão principal vira duas ações diferentes. Em Gravar,
começa e para na hora (arquivo de 00:00:00); em "Salvar e copiar caminho", salva e já começa uma gravação nova
sem ninguém pedir; em Parar, com o motor ainda fechando o MP3 (`stopping`), a tela mostrava "A gravação foi
interrompida" (o 2º `rec.stop` levava `refused`). Achado da revisão adversarial da Fase 3 (12/11/2026), no
backend falso.

**Causa:** o botão principal fica no mesmo lugar e muda de papel (Gravar → Parar → Salvar → Gravar) assim que
a resposta chega. O 2º clique cai no papel novo. Com o motor real, que demora para responder, o 2º clique cai no
papel antigo com um pedido ainda em voo e o motor recusa.

**O que fazer:** não trocar o "botão parado no lugar" (é a regra anti-pulo); filtrar o clique. Em
`app/ui/src/controle/cliques.ts`: ignorar `detail > 1` e, no principal, o clique de ponteiro cujo aperto
começou antes da última troca de papel (`principalTrocouEm`); em `controle/gravar.ts`: trava de pedido em voo
nos pedidos curtos, e `busy`/`refused` ressincronizam pelo `state` em vez de mostrar erro. Prova:
`node app/ui/tests/revisao.cjs` (duplo clique em cada estado e motor lento).
