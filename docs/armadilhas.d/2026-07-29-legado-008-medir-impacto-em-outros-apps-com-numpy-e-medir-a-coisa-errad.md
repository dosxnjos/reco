---
titulo: Medir "impacto em outros apps" com numpy é medir a coisa errada (29/07/2026)
data: 2026-07-29
---
**Sintoma:** um benchmark de convivência acusou combinações rodando **mais
rápido** que a máquina ociosa e o app vizinho **acelerando** durante a
transcrição. Resultado incoerente, descartado.

**Duas causas somadas:**

1. O "vizinho" usava `numpy @ numpy`, que aciona **BLAS multi-thread** e satura
   todos os núcleos. Isso simula um segundo job pesado, não um app interativo — e
   ainda distorce a medida de velocidade do que se está medindo (a iGPU caiu de
   14,9× para 7,2× por causa dele).
2. O baseline "ocioso" é medido com a CPU em **frequência baixa**. Quando a
   transcrição carrega a máquina, o governor sobe o clock e o vizinho fica
   genuinamente mais rápido. O baseline é que estava lento.

**O que fazer:** medir **latência**, não throughput, com um vizinho
single-thread em **processo separado** que acorda periodicamente e faz trabalho
fixo (`temp/vizinho.py`) — é o perfil de um app de interface. E lembrar que esse
teste é puro CPU: ele **não** mede a iGPU disputando com renderização de tela e
vídeo, que é o cenário "transcrever durante reunião com câmera".
