---
titulo: O stop() fechava o MP3 com o codificador no meio: assert do LAME
data: 2026-11-17
---
**Sintoma:** sob carga de GIL, a gravação morria no Parar com `Assertion failed: esv->header[...].write_timing >=
bs->totbit, ... bitstream.c` (processo sai com rc 3), às vezes falha de memória (rc 139) ou `EOFError` no fechamento.
Na rodada de 16/11 foram 2 mortes em 3 `--carga gil` (o LAME já reclamava de "Internal buffer inconsistency" antes).

**Causa (provável, não provada em hardware):** o `_wind_down` espera o thread do codificador por 3 s; se estourar, o
`stop()` chama `writer.close()` com o `_pump` ainda dentro de `writer.feed()`. Dois threads no mesmo libmp3lame. Sem
som, isso reproduz a mesma família de assert (`bitstream.c`). As mortes de 16/11 foram no Parar (corridas de ~193 e
~203 s, contra ~190 das outras), o que bate, mas não prova. A corrida existe também no código sem A1 (a 0.3.0
publicada): a primeira reprodução foi nele. Que o buffer de 1 s a torne mais frequente é hipótese.

**O que fazer:** `MP3Writer` herda de `captura.TravaEscrita`: `feed`, `close` e `discard` sob a mesma trava, e `feed`
depois do fechamento é descartado. Prova sem som em `tools/test_trava_mp3.py` (4 corridas em processo filho): com a
trava `falhas 0`; sem ela `falhas 4` (3 com rc 3). Limite: a trava troca a morte por um corte silencioso do que o
codificador ainda devia quando o join estourou (o `feed` depois do fechamento é descartado); o tamanho desse corte
não foi medido. O `stop()` continua podendo passar de 500 ms sob carga.
