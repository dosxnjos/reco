---
titulo: Gravar nota logo depois de abrir não grava: a checagem do modelo ocupa a vaga da transcrição
data: 2026-11-12
status: superada
superada_por: adf3fc0
---
**Sintoma:** no Reco Novo instalado, trocar para Nota e clicar em "Gravar nota" uns 2 s depois de abrir não
grava nada. No instalador do passo 16 (SHA256 `72e98338…`) a tela mostrava "O motor está ocupado com outra tarefa: transcrição em
andamento" (rótulo Erro); no build `aac7ca7` o clique some calado (a tela volta a "Pronto"). O segundo clique,
segundos depois, grava normal. Gravação comum (modo `rec`) não sofre: só a nota. Visto 3 vezes no teste real do
passo 17 da Fase 3 (12/11/2026), com `HF_HUB_OFFLINE=1`; sem o clipe tocando e com o clique a ~1,4 s da partida,
gravou de primeira.

**Causa:** o casco pede `model.update_check` 1,5 s depois do primeiro `ready` (passo 5, F3-D15), e o motor faz a
checagem ocupando a vaga da transcrição (`engine/reco_engine/extras.py:7`, `transcribing` ligado). O
`rec.start {mode: nota}` recusa com `busy` enquanto há transcrição (`recording.py:140-141`), porque a nota
transcreve ao parar. Com rede de verdade a checagem demora mais, e se houver modelo novo para baixar a nota fica
travada pelo download inteiro.

**O que fazer:** em teste, esperar a checagem acabar (ou clicar de novo) antes de concluir que a nota quebrou.
No app: o `rec.start` da nota pode aceitar a checagem em curso (a transcrição só começa no `rec.stop`, e aí
espera a vaga), ou a tela mostra o motivo ("conferindo atualização do modelo") em vez de engolir o `busy`.
