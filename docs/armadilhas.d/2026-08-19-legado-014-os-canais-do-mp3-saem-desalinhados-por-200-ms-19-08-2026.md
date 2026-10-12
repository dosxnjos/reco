---
titulo: Os canais do MP3 saem desalinhados por ~200 ms (19/08/2026)
data: 2026-08-19
---
**Sintoma.** Ao ouvir a gravação, a fala do interlocutor aparece duas vezes com
separação nítida — soa como eco de sala grande, não como vazamento fraco.

**Causa.** Não é acústica: eco de caixa a um metro são ~3 ms. Medido no arquivo
de 19/08 11:00, o atraso mic↔loopback é de **3241 amostras (203 ms)**, com jitter
de 24 ms entre janelas e deriva de +21 ppm (+76 ms/hora). É **latência de buffer**
entre os dois streams: o `DualRecorder` sincroniza o *início* dos streams com
`threading.Barrier`, mas o loopback entrega o primeiro bloco com offset próprio, e
`_pump` pareia por **contagem de amostras** — o offset inicial fica gravado para
sempre. Acima de ~50 ms o ouvido deixa de integrar a reflexão como reverberação e
passa a ouvir eco separado, então esse offset é provavelmente a causa da queixa,
mesmo quando o acoplamento é modesto.

⚠️ **O sinal do offset varia entre gravações.** No arquivo de 18/08 15:16 o
loopback vem DEPOIS do mic, e o atraso chega a **−6385 amostras (−399 ms)** —
fora da busca de ±0,2 s que `_alinhar_canais` usava. Consequência medida: o AEC
saía com **ERLE negativo** (−1 a −6 dB, ou seja *somando* energia) naquele
arquivo. Corrigido em 19/08 subindo `maxlag_s` para 0.5 s; com a busca larga o
mesmo arquivo dá +4 a +10 dB. Implementação de alinhamento que assuma sinal
positivo está errada.

**O que fazer.** Compensar o offset na gravação (Fase 1 do roadmap de 19/08) —
alinhar não é "processar o áudio", é corrigir buffer, e é pré-requisito de
qualquer AEC e da diarização. ⚠️ E não confundir alinhar com cancelar: alinhar +
ganho escalar ótimo dá **−1,1 dB** de ERLE (não cancela nada); o ganho do
alinhamento é percepção e correção do resto do pipeline.
