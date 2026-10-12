---
titulo: O acoplamento NÃO prediz se o `cancel_echo` vai ajudar ou piorar (30/08/2026)
data: 2026-08-30
---
**Sintoma.** Depois de achar uma gravação em que o AEC entrega **ERLE negativo**
(21/08 15:00: acoplamento −36,1 dB, ERLE −7,8 dB — o filtro *soma* energia), a
conclusão natural é "acoplamento fraco ⇒ desligar o AEC", e daí sai a tarefa de
calibrar um limiar de acoplamento. **Esse limiar não existe.**

**Causa.** Medidas 13 gravações de junho a agosto (`tools/varrer_aec.py`), as
duas populações se sobrepõem no eixo do acoplamento:

| gravação | acoplamento | ERLE |
| --- | --- | --- |
| 21/08 15:00 | −36,1 dB | **−7,8 dB** (piora) |
| 05/08 11:01 | **−14,4 dB** | **−0,5 dB** (piora) |
| 22/06 10:50 | −24,1 dB | +15,7 dB (ajuda muito) |
| 21/08 16:52 | −17,8 dB | +16,2 dB (ajuda muito) |

Um corte em −14,4 dB mata o AEC nos dois melhores casos do acervo; um corte em
−30 dB deixa passar o de 05/08. O acoplamento mede *quanta* energia do sistema
chega ao mic; se o filtro consegue **modelar** esse caminho é outra pergunta
(linearidade, AGC do mic, alinhamento, estacionariedade) e não se lê no primeiro
número.

**O que fazer.** Guard que mede o **ganho no próprio sinal** — comparar a saída
do `cancel_echo` com a entrada e devolver o mic cru quando piora — em vez de
qualquer régua baseada em acoplamento, e em vez de uma opção de config que
obriga o usuário a adivinhar arquivo a arquivo. **Não é caso raro:** 2 dos 13
(15%) têm ERLE ≤ 0. Desenho em
[roadmap/2026-08-21-salto-de-alinhamento-sob-carga.md](../roadmap/2026-08-21-salto-de-alinhamento-sob-carga.md)
§ 6.2 (passo E4).
