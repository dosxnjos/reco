---
titulo: Thread presa no readline do stdin trava o carregamento de DLL em outra thread
data: 2026-11-11
---
**Sintoma:** no motor (`engine/`), o `import reco` em segundo plano levou 12 a 20 s em vez de 0,4 s,
e o evento `ready` só saía quando o casco mandava a linha seguinte. Medido em 11/11/2026: com uma
thread presa em `sys.stdin.buffer.readline()` num pipe, o import de 0,4 s levou exatamente o tempo
até a próxima linha (20,3 s com 20 s de espera); sem a leitora, 0,35 s. O `faulthandler` mostra a
outra thread parada no `create_module` do `numpy._core._multiarray_umath`, isto é, carregando DLL.
O mesmo travaria o aquecimento (`openvino`) e a primeira transcrição.

**Causa:** a inicialização de DLL nativa consulta o handle padrão do stdin, e o Windows serializa
I/O síncrono num mesmo objeto de arquivo: a consulta espera o `ReadFile` pendente da leitora.

**O que fazer:** antes de subir a leitora, tirar o pipe do fd 0 e do `STD_INPUT_HANDLE`: `src =
os.dup(0)`, `os.dup2(<fd do NUL>, 0)` (a UCRT troca o handle padrão junto), e a leitora lê de
`os.fdopen(src, "rb")` (`_isolate_stdin` em `reco_engine/server.py`). Medido: import 2 s com o
aquecimento inteiro, leitora ainda esperando a linha. A rodada padrão de
`tools/test_engine_protocol.py` espera o `ready` e o "aquecimento pronto" sem mandar linha nenhuma, e
reprova se isso regredir. Vale para qualquer processo Python servido por pipe (o Lacre não tropeçou
porque o motor dele não carrega numpy nem openvino depois de subir a leitora).
