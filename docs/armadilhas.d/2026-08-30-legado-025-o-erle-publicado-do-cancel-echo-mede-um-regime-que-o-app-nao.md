---
titulo: O ERLE publicado do `cancel_echo` mede um regime que o app não usa (30/08/2026)
data: 2026-08-30
---
**Sintoma.** Todo número de AEC deste projeto (inclusive o "+15,5 dB" do
`CLAUDE.md`) sai de `tools/medir_aec.py`, que mede em **janela contígua de 15 s**.

**Causa.** O pipeline real chama `cancel_echo` sobre outra coisa: as partes de um
grupo VAD livres de dominância, **concatenadas** (`_transcribe_channel`, o
`np.concatenate([audio[s:t] for s, t in partes])`) — ~3 s de fala em vários
retalhos. O eco chega ao mic ~200 ms depois da referência, então recortar só a
fala descarta o rabo do eco de cada retalho; e o `np.roll` global de
`_alinhar_canais` cruza as emendas, trazendo referência de outro instante.

**O que fazer.** Tratar os números de ERLE como **do laboratório**, não do
produto, até a Fase 0.6 do roadmap de 21/08 medir no regime real
(`tools/medir_aec_regime.py`). Vale para qualquer gate de AEC daqui: medir onde
o código roda, não onde é conveniente medir.
