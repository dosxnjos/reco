---
titulo: Duas `def` de mesmo nome no `reco.py`: a 2ª esconde a 1ª sem erro (11/10/2026)
data: 2026-10-11
---
**Sintoma.** `import reco` passa, o `check_i18n` passa, o guard novo passa, e toda
transcrição levanta `TypeError: resolve_device() missing 1 required positional
argument` ao montar o pipeline. Pego só pela revisão de contexto zero.

**Causa.** `resolve_device(pref)` já era do acelerador OpenVINO (l.~1114); o roadmap
do Auto mandou chamar a função nova de dispositivo de áudio pelo mesmo nome, e a 2ª
`def` sobrescreveu a 1ª em silêncio.

**O que fazer.** Antes de nomear função no `reco.py` (5 mil linhas, módulo único),
`grep -n "def <nome>"`. A função do dispositivo de áudio é `resolve_audio_device`. O guard
`tools/test_dispositivo_auto.py` confere def duplicada no nível do módulo (só dentro
do `reco.py`: depois da modularização, colisão entre módulos pede checagem própria).
