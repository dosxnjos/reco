---
titulo: Rotulagem por energia simultânea mede o OPOSTO quando os canais estão desalinhados (19/08/2026)
data: 2026-08-19
---
**Sintoma.** Medindo o `cancel_echo`, o AEC aparecia **destruindo a voz do
usuário em até 28,4 dB** nos blocos rotulados "só o usuário fala". O diagnóstico
que saiu disso — "o AEC não tem detector de double-talk e está apagando a voz" —
foi escrito, commitado (`76bcb9c`) e está **errado**.

**Causa.** O rótulo vinha de energias **simultâneas** (`mic` alto e `sistema`
abaixo do limiar, no mesmo bloco de 100 ms), e o eco chega ao mic **~200 ms
depois** (latência de buffer entre os streams). O bloco em que o sistema já
silenciou mas o mic ainda toca o rabo do eco é rotulado "só o usuário falando" —
o AEC remove eco de verdade ali, e a métrica registra como voz destruída. O
espelho do mesmo erro infla `so_sys`: o mic aparece em −51 dBFS porque o eco
daquele trecho ainda não chegou, e o "ERLE" ali é atenuação de ruído de piso.

**Como foi pego** (vale mais que a conclusão): a "correção" não fechava. O
detector de double-talk derrubou o dano de 28,4 → 9,1 dB mas matou o ERLE
(+15 → +0,5), o que nenhum DTD deveria fazer. Depurando a janela suspeita, os
blocos que "perdiam 34 dB de voz" perdiam 23,7 dB **mesmo com `residual=False`**
— subtração linear pura só remove tanto se o conteúdo estiver na referência. Era
eco. Rotulando com o sistema **alinhado**, o mesmo código mediu **+15,6 dB de
ERLE com +0,5 dB de dano**.

**O que fazer.**

- Rotular far-end-only / near-end-only **sempre** com o canal do sistema alinhado
  (`_alinhar_canais`) — é o que `tools/medir_aec.py` faz. `tools/medir_eco.py`
  **não** faz, e por isso não serve para julgar AEC.
- Reportar AEC como par **(ERLE, dano na voz)**. ERLE sozinho não distingue
  cancelar de abaixar o volume — isso continua verdade, e é por isso que o par
  existe; o que era falso é o número que ele acusou.
- Números honestos do `cancel_echo` (19/08, rotulagem alinhada): ERLE mediano
  **+15,5 / +6,4 / +9,0 dB** em três gravações, dano **≤ +1,2 dB**; a
  decomposição dá +8,7 dB de cancelamento linear e +6,8 dB de pós-supressão.
- E a lição de método: **quando a correção de um defeito "resolve" o número mas
  destrói o resultado que deveria preservar, suspeite da medição antes de aceitar
  o trade-off.**

---
