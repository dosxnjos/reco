"""Peças do `DualRecorder` que moram fora do `reco.py` (ele não cresce: trava `tools/tamanho.json`).

Hoje: a trava de escrita do `MP3Writer` (#17, 17/11/2026). O buffer de 1 s e o dreno da cauda
(A1/A1b do mesmo #17) entram aqui quando passarem na prova em hardware: ramo
`wt/issues-17-21-22-34`, `roadmap/2026-11-16-issues-17-21-22-34.md`.
"""
import threading


class TravaEscrita:
    """Base do `MP3Writer`: `feed`, `close` e `discard` sob a mesma trava (#17, 17/11).

    O `stop()` espera o thread do codificador por 3 s e fecha o arquivo; sob carga o
    codificador ainda pode estar no meio de um `feed`, e os dois threads entram juntos no
    libmp3lame: assert em `bitstream.c` (o processo morre, rc 3), falha de memória (rc 139)
    ou arquivo truncado. Com a trava, o `close` espera o `feed` em curso e todo `feed`
    depois do fechamento é descartado. Prova sem som: `tools/test_trava_mp3.py`."""

    def _trava(self):
        return self.__dict__.setdefault("_lk_escrita", threading.Lock())   # setdefault: atômico

    def feed(self, *a, **k):
        with self._trava():
            if self._cont is not None:
                self._feed(*a, **k)

    def close(self):
        with self._trava():
            return self._close()

    def discard(self):
        with self._trava():
            return self._discard()
