---
titulo: `warnings.catch_warnings` NÃO isola por thread — não serve para achar de qual canal veio o glitch (30/08/2026)
data: 2026-08-30
---
**Sintoma.** Um plano razoável para contar as descontinuidades do WASAPI é
envolver o laço de cada thread de captura em `warnings.catch_warnings(record=True)`
e ler a lista. Ele parece funcionar e atribui os avisos ao canal **errado**.

**Causa.** `catch_warnings` copia e restaura `warnings.filters` e
`showwarning` — que são **globais do processo**, não do thread. Nesta build
(Python 3.14.4, `warnings._use_context == 0`) o bloco de um thread captura o
que outro emitiu. Medido: dois threads, um dentro do `catch_warnings` e outro
só emitindo, e o warning do segundo apareceu na lista do primeiro. Com os dois
threads de captura do `DualRecorder`, cada um também sobrescreve o
`showwarning` do outro ao entrar e ao sair.

**O que fazer.** Instalar **um** `warnings.showwarning` no `start()` e resolver
o canal por `threading.current_thread()`, restaurando no `_wind_down`. E não
esquecer `simplefilter("always", SoundcardRuntimeWarning)`: o registro de
deduplicação do módulo engole a segunda ocorrência em diante.
