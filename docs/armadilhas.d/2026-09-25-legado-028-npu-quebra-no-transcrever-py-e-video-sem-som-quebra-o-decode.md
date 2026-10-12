---
titulo: NPU quebra no `transcrever.py`, e vídeo sem som quebra o decode (25/09/2026)
data: 2026-09-25
---
**Sintoma.** Com `--device NPU`, o `tools/transcrever.py` sai com `rc 1` e
`Check '*roi_end <= *max_dim' failed at src\inference\src\dev\make_tensor.cpp:35`,
depois de subir a memória até ~4 GB. Em vídeo sem som (o GIF que o WhatsApp
manda como mp4), qualquer dispositivo dá `tuple index out of range` em
`Carregando áudio`.

**Causa.**

- NPU: a checagem de forma do tensor falha no `infer_request` com o
  `large-v3-turbo` int8 desta máquina (Core Ultra 5 225H, "Intel AI Boost").
  Não investigado além disso. O "NPU 5,5× tempo real" da docstring de
  `resolve_device` é de 29/07 e não se repetiu.
- Vídeo sem som: `reco.py` faz `cont.streams.audio[0]` sem checar se existe
  trilha (a outra leitura, perto da linha 815, checa).

**O que fazer.**

- Não escolher NPU no app nem em chamada automática. O coletor da central
  passa `--device GPU` justamente para não herdar a escolha do app.
- Custo medido por processo, com um áudio de 26 s:

  | dispositivo | parede | CPU | pico |
  | --- | --- | --- | --- |
  | GPU | 14,6 s | 9,0 s | 1,35 GB |
  | CPU | 18,2 s | 33,1 s | 2,0 GB |
  | NPU | falha | 10,5 s | 4,0 GB |

- Quatro áudios num processo só: 13,2 s de CPU. Carregar o modelo é o grosso.
- Vídeo sem som: `tools/transcrever.py` confere a trilha antes
  (`sem_trilha_de_audio`) e grava `.txt` vazio, a resposta verdadeira. O app
  (`reco.py`) segue sem a checagem: consertar lá pede recompilar.
- Roadmap da medição:
  `C:\Dev\central\roadmap\2026-09-25-coletor-apaga-midia-transcrita-e-transcreve-leve.md`.
