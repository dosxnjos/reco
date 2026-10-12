---
titulo: O alinhamento ao vivo demora ~10 min para se recuperar de um SALTO (21/08/2026)
data: 2026-08-21
---
**Sintoma.** Gravações do dia 21/08 com eco separado audível nos primeiros 5 a 10
minutos e limpas do meio para o fim — em 3 das 5 do dia. As de 20/08, com o mesmo
executável, saíram alinhadas de ponta a ponta (mediana +0 ms). Ou seja: não é
regressão de build, é intermitência.

**Causa.** O atraso mic↔loopback não só deriva devagar — ele **salta**. Medido
trecho a trecho (15 s, correlação cruzada):

| gravação | começa em | salta para | quando | volta a ~0 em |
| --- | --- | --- | --- | --- |
| 21/08 16:52 | 0 / −16 / −24 ms | **−359 ms** | t=60 s | t≈480 s |
| 21/08 11:16 | +118 ms | **+497 ms** | t=75 s | não volta (arquivo tem 4,5 min) |
| 21/08 10:41 | +83 / ~0 ms | **−495 ms** | t=165 s | t≈540 s |

E a volta é uma **escada de 50 em 50 ms, um degrau por minuto**: é exatamente
`ALIGN_MAX_AJUSTE` (2400 amostras @48k = 50 ms) por reestimativa, com
`ALIGN_RECHECK_S` = 60 s. O teto existe de propósito — uma estimativa ruim não
pode arrancar 400 ms do arquivo de uma vez —, mas ele não distingue **deriva de
clock** (dezenas de ppm, o que ele foi feito para corrigir) de **salto**.

⚠️ **A origem do salto foi encontrada no mesmo dia, e é uma constante nossa:** os
recorders são criados com `blocksize=CHUNK` (1024), e no `soundcard`
(`mediafoundation.py:549`) esse parâmetro vira a **duração do buffer** que o
WASAPI aloca — medido nesta máquina, **1056 frames = 22,0 ms** (com
`blocksize=48000` o Windows entrega 1000 ms). O thread de captura tem 22 ms para
voltar ao `record()`; sob carga (quantum do scheduler, GIL, GC, iGPU ocupada) ele
não volta, o buffer circular é sobrescrito e as amostras **somem sem ninguém
contar**. Como o `_pump` pareia por contagem de amostras, o que se perdeu vira
offset permanente. O Gabriel confirmou o contexto: *"eu estava com alto uso de
recursos do PC durante as gravações"* — e 20/08, sem carga, saiu perfeito com o
mesmo executável.

⚠️ **E o `soundcard` avisa — nós é que não escutamos.** `mediafoundation.py:771`
levanta `warnings.warn("data discontinuity in recording", SoundcardRuntimeWarning)`
exatamente nesse evento. Rodando pelo `Reco.exe` (sem console) o aviso não vai
nem para o stderr. Plano de correção (buffer de 1 s, escutar o warning, corrigir
pelo relógio em vez da correlação):
[roadmap/2026-08-21-salto-de-alinhamento-sob-carga.md](../roadmap/2026-08-21-salto-de-alinhamento-sob-carga.md).

**Consequência medida.** No arquivo de 11:16, ERLE mediano do `cancel_echo` de
**+5,6 dB** com atraso por janela de +118 a +497 ms; alinhado por trecho com
`tools/alinhar_gravacao.py --aplicar`, o mesmo áudio dá **+12,2 dB com atraso 0 em
todas as janelas e dano na voz +0,0 dB**. No de 16:52, o ERLE mediano não muda
(+16,2 dB — as janelas que a métrica escolhe já eram do trecho pós-convergência),
mas os ~7 primeiros minutos deixam de ter eco separado.

**O que fazer.** Enquanto o código não distinguir os dois casos, gravação com
queixa de eco se conserta pós-fato com `tools/alinhar_gravacao.py <mp3> --aplicar`
(escreve `_alinhado.mp3` ao lado; residual medido: 0,0 ms no pior trecho).

⚠️ **O residual zero de 21/08 não é garantia (25/09/2026).** Na gravação de 23/09 11:02
(call de 23 min, queixa de eco), o `varrer_acervo.py` deu salto de +87 a +491 ms, com
100% dos trechos medíveis acima de 50 ms. Depois do `alinhar_gravacao.py --aplicar`, a
mediana foi a 0 ms, mas **11% dos trechos seguiram acima de 50 ms** (pior +436 ms) e a
faixa virou −404..+436 ms: só 18 de 47 janelas de 30 s correlacionavam, e a correção
entre elas não pega salto curto. Transcrita com `--diarizar --aec`, a faixa `Eu:` ainda
teve 12 de 72 falas com eco claro do outro lado e 14 de `"Tchau."`/vazio alucinado no
silêncio. **O que fazer:** depois de alinhar, rodar o `varrer_acervo.py` no
`_alinhado.mp3` e não prometer faixa limpa. A faixa `Interlocutor(es):` sai limpa. Na
`Eu:`, descartar a fala que repete a linha vizinha do outro lado; o que sobra é a fala do
dono da gravação.

Direção proposta para a correção, **não decidida ainda**: duas reestimativas
consecutivas concordando em magnitude alta (> ~100 ms) e com `q` acima do limiar
não são estimativa ruim — são salto, e aí o offset deve ser aplicado inteiro
(um salto no áudio custa menos que 10 minutos de eco). Alternativa mais barata:
encurtar `ALIGN_RECHECK_S` enquanto o residual for grande.

⚠️ **Não confundir com "o AEC piorou".** Nos trechos em que o áudio do sistema não
toca, a correlação vira ruído (`q` < 0,05) e tanto o atraso quanto o ERLE que as
ferramentas imprimem ali não significam nada. Julgar sempre pelos trechos com `q`
acima de `ALIGN_Q_MIN`.
