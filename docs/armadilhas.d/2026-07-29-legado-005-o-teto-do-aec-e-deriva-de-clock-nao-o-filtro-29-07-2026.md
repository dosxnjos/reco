---
titulo: O teto do AEC é deriva de clock, não o filtro (29/07/2026)
data: 2026-07-29
---
**Sintoma:** melhorar o filtro de eco dá ganhos que estancam por volta de 7 dB,
e a melhora some em gravações longas.

**Causa:** microfone e loopback do sistema correm em **relógios de hardware
independentes**. Medido pelo atraso ótimo de correlação ao longo do arquivo:

| gravação | atraso mic↔loopback | desvio-padrão | deriva |
| --- | --- | --- | --- |
| 5,7 min | 608 amostras (38 ms) | **0** | 0,1 ppm |
| 80 min | 2283 amostras (143 ms) | **2314** | **−65,8 ppm** (≈ −237 ms/h) |

Em gravação curta o alinhamento é estável; em 80 minutos ele passeia centenas de
milissegundos. Nenhum filtro linear acompanha isso sem **reamostragem contínua**
de compensação.

**O que fazer:** aceitar o teto. Passar dele exigiria compensar a deriva *e* a
distorção não-linear da caixa — caro e incerto. Para o objetivo real (diarização
correta), o caminho barato é decidir o locutor por **dominância de energia entre
os canais**, que é robusto a eco residual e não depende de cancelar nada. Fone de
ouvido continua sendo a solução de custo zero que elimina o problema na origem.

⚠️ **O "teto de ~7 dB" é métrica inválida** (marcado em 16/11/2026, issue #22):
o ERLE de 29/07 foi calculado com rótulos por energia simultânea e o alinhamento
saturado (§ 1.3 de `roadmap/2026-08-19-melhoria-antieco-de-verdade.md`). Pela régua certa (`tools/medir_aec.py`, rotulagem alinhada)
o `cancel_echo` entrega +6,4 a +15,5 dB com dano ≤ +1,2 dB, e a deriva de clock é
um dos tetos, não o único (AGC do mic e distorção da caixa também pesam): ver
`docs/ARQUITETURA.md` e o § 1.5 de `roadmap/2026-08-19-melhoria-antieco-de-verdade.md`.
A tabela de atraso e deriva acima foi medida por correlação e segue valendo.

---
