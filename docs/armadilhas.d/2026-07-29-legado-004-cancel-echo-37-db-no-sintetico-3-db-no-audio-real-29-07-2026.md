---
titulo: `cancel_echo`: 37 dB no sintético, 3 dB no áudio real (29/07/2026)
data: 2026-07-29
---
**Sintoma:** o cancelamento de eco estava documentado como "~37 dB ERLE
validado", mas o eco da caixa de som continuava audível e a diarização seguia
atribuindo ao usuário falas do interlocutor.

**Causa:** os 37 dB eram reais — em eco **sintético**, linear e invariante no
tempo. A implementação estimava **um** ganho complexo por bin de frequência para
a janela **inteira** de 30 s, o que assume que o caminho acústico é invariante
por 30 s e cabe num único quadro de FFT (64 ms). Numa sala real, medido nas
gravações do próprio Gabriel: **+3,2 dB** e **+3,7 dB**, com acoplamento
caixa→mic de −17,9 dB e −23,7 dB (abaixo de −35 dB seria desprezível).

**O que fazer:** a versão atual usa mínimos quadrados em blocos de 2 s com 6 taps
(~96 ms) + pós-supressão residual, e entrega **+7,2 dB** custando 0,3 dB da voz
do usuário. **Não tentar chegar a 20-40 dB alongando o filtro** — ver a armadilha
seguinte. E sempre medir ERLE em áudio **real**, nunca em eco sintético: é
exatamente esse teste que validou uma implementação que não funcionava.

---
