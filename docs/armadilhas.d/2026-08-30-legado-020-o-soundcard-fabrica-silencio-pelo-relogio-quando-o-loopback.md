---
titulo: O `soundcard` fabrica silêncio pelo relógio quando o loopback está mudo (30/08/2026)
data: 2026-08-30
---
**Sintoma.** Gravação sem áudio de sistema tocando (fone, reunião silenciosa)
pode dessincronizar sem que nenhum aviso de descontinuidade apareça — e a
correlação cruzada é cega ali, porque não há eco para correlacionar.

**Causa.** `_record_chunk` (`mediafoundation.py:735-756`) **não bloqueia**
esperando o WASAPI: faz polling e, passados `deviceperiod_default * 4` ≈ 40 ms
sem pacote nenhum, devolve um bloco de zeros **dimensionado pelo relógio**
(`int(samplerate * elapsed_ns / 1e9)`). Só o **loopback** entra nesse caminho —
o mic sempre entrega pacote. O `int()` trunca e o `_idle_start_time` avança
pelo tempo inteiro, então o resto fracionário se perde: até 1 frame por
disparo, ou ~31 ms/min no pior caso de ociosidade contínua. E esse caminho
**não** levanta `AUDCLNT_BUFFERFLAGS_DATA_DISCONTINUITY`.

**O que fazer.** Não tratar "contar o warning de descontinuidade" como cobertura
completa de perda de amostra: essa via é invisível a ele. Medir com contagem de
frames × relógio de parede por canal, com a caixa muda. Contexto e plano:
[roadmap/2026-08-21-salto-de-alinhamento-sob-carga.md](../roadmap/2026-08-21-salto-de-alinhamento-sob-carga.md)
§ 1.6.

⚠️ **Corolário para quem for aumentar o buffer de captura:** o laço de captura
sai no `_stop_ev` e o que ficou no buffer do WASAPI é descartado no `__exit__`.
Com `blocksize=1024` isso são 22 ms; com um buffer de 1 s, passa a ser **até 1
segundo do fim de toda gravação**. Buffer maior exige drenar a cauda antes de
sair do `with`, nos dois canais.
