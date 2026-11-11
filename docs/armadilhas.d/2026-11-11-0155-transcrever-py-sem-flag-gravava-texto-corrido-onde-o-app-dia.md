---
titulo: "`transcrever.py` sem flag gravava texto corrido onde o app diariza (11/11/2026)"
data: 2026-11-11
---
**Sintoma:** na pasta `Documents\Reco`, os `gravacao_reco_*.mp3.txt` saem em texto
corrido, sem `Eu:` / `Interlocutor(es):`, enquanto os `gravacao_reco_*.txt` do botão
"Salvar + transcrever" saem separados por quem falou. Contado em 11/11/2026: 43
`.mp3.txt` assim, de 03/08 a 10/11.

**Causa:** dois caminhos de transcrição com padrões diferentes. O app
(`App._run_transcriber`) liga diarização e AEC quando o nome tem a etiqueta `reco` e a
config pede, e grava `x.txt`. O `tools/transcrever.py` tinha `--diarizar`/`--aec`
desligados por padrão e gravava `x.mp3.txt`; as docs que as sessões seguem
(`guides-e-sensores.md`, `Reco/CLAUDE.md`) mandavam rodar sem flag. Prova: o lote de
10/11 09:23 saiu de uma sessão de triagem de issues que seguiu o guia ao pé da letra.

**O que fazer:** desde 11/11/2026 o script decide como o app (`opcoes()`/`destino()`
em `tools/transcrever.py`): gravação do Reco → diarizada + AEC conforme a config; na
pasta de gravações do app sai em `x.txt`, fora dela em `x.mp3.txt` (os chamadores do
WhatsApp calculam `midia + ".txt"`, inclusive para anexo com nome `gravacao_reco_*`).
Outro áudio → texto corrido em `<arquivo>.<ext>.txt`. `--texto-corrido` volta ao
corrido. `x.mp3.txt` antigo em texto corrido não conta como pronto (o `x.txt` nasce ao
lado, nada é apagado); 7 dos 43 antigos já eram diarizados e são aproveitados.
⚠️ Modelo e dispositivo **não** seguem a config do app, de propósito: NPU escolhida no
app quebraria os lotes de fundo que não passam `--device` (armadilha 028). Prova: numa
gravação curta o `x.txt` do script saiu byte a byte igual ao do app. **Regra para não voltar:** opção de
transcrição nova entra nos dois caminhos (app e script) ou em função comum; o ramo
headless `Reco.exe --transcribe` ainda só diariza com `--diarize` (pendente, pede
recompilar). Plano: `roadmap/2026-11-11-transcrever-diariza-como-o-app.md`.
