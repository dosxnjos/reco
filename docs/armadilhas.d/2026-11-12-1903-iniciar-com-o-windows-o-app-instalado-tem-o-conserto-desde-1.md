---
titulo: Iniciar com o Windows: o app instalado tem o conserto desde 12/11 18:34 (o defeito da entrada das 17:57 saiu do instalado)
data: 2026-11-12
---
**Sintoma:** a entrada das 17:57 ("o plugin gravava o caminho sem aspas…") diz que **o instalado ainda tem o defeito**.
Isso deixou de valer às 18:34 de 12/11/2026, quando o instalador `96B45826` (do `880c446`) foi instalado por cima do
`84EE1142`. Prova refeita no app instalado (passo 13 da Fase 4): ligar grava `"<exe>" --oculto` entre aspas; desligar
deixa rc 1 no `Run` e no `StartupApproved\Run`, mesmo com a marca semeada antes.

**Causa:** fragmento de armadilha é imutável, então a correção vem numa entrada nova. Dois detalhes da entrada das 17:57
também mudaram:
- O reparo na partida não regrava "um valor antigo diferente". Desde o `880c446` ele só regrava o valor sem aspas **do
  próprio exe**, para um casco de build em `C:\pt` não tomar o boot do instalado.
- Ligar já apaga a marca do `StartupApproved`. Um rc 1 nela depois de desligar não prova a limpeza; para provar,
  semear a marca (`02 00…`) antes de desligar.
