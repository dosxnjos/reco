---
titulo: A rede de segurança do `cancel_echo` mede o RMS global e nunca dispara (30/08/2026)
data: 2026-08-30
---
**Sintoma.** O `cancel_echo` tem, desde 29/07, um fallback que devolve o mic cru
"se a saída sair mais alta que a entrada" (`reco.py`, fim de `cancel_echo`) — e
esta armadilha até manda mantê-lo (§ NLMS acima). Mesmo assim, no arquivo de
21/08 15:00 o AEC entrega **ERLE de −17,4 a −3,9 dB nas 6 janelas medidas**: ele
soma energia e o fallback não reage.

**Causa.** A régua é **global** (`r_out > r_in * 1.05` sobre a chamada inteira) e
o dano é **local** — o ERLE mede só os blocos em que apenas o far-end toca. Voz
do usuário e silêncio diluem o aumento, e a razão global fica abaixo de 1,05.
Assinatura para conferir: quando o fallback dispara, a saída é o próprio mic e o
ERLE daquela janela sai **0,0 exato**; em 15:00 não há nenhum zero.

**O que fazer.** ~~Comparar a energia do resíduo com a da entrada **por bloco de
estimativa** e zerar o filtro no bloco em que ele piora~~ — **corrigido em
16/11/2026 (#21): essa régua por bloco nunca dispara** (o mínimo quadrado tem `h = 0`
como candidato, então o bloco inteiro não piora; armadilha de 16/11 "A régua por
bloco do guard do cancel_echo nunca dispara"). O que entrou foi a régua **por quadro
da STFT, sobre a saída depois da pós-supressão** (`aec_guarda.sem_piora`), mantendo
esta rede global de 1,05 por fora. Passo `E4b` em
[roadmap/2026-08-21-salto-de-alinhamento-sob-carga.md](../roadmap/2026-08-21-salto-de-alinhamento-sob-carga.md)
§ 4.10. E lembrar do contexto de § 8.5: **os arquivos com ERLE ≤ 0 são os que têm
salto de alinhamento** — o guard evita o dano, não conserta o eco. O número em 15:00
com a régua nova ainda não foi medido.
