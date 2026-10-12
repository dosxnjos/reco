---
titulo: `--diarizar` sem `--aec` não separa nada em gravação no alto-falante (03/08/2026)
data: 2026-08-03
---
**Sintoma:** rodamos `transcrever.py --diarizar` numa gravação real para
responder "quem falou esta frase — o Gabriel ou a interlocutora?". A saída veio
com **as duas faixas repetindo o mesmo texto**, deslocadas por uma fração de
segundo: cada frase aparece uma vez em `Interlocutor(es)` e de novo em `Eu`.
Inútil para atribuir autoria.

**Causa:** a gravação foi feita **sem fone**. O áudio do sistema saiu pelos
alto-falantes e voltou pelo microfone, então o canal do mic contém a fala do
outro lado — e `--diarizar` **sozinho não cancela eco**, só separa canais.

**A correção é usar as duas flags: `--diarizar --aec`.** Refeito assim, no mesmo
arquivo, a separação ficou limpa: blocos longos da interlocutora de um lado,
intervenções curtas do Gabriel do outro, e o `.txt` encolheu **38%** (69 KB →
42,6 KB) — o que sumiu era a duplicata de eco.

⚠️ **Meça antes de confiar.** `tools/medir_eco.py <mp3>` dá acoplamento e ERLE
reais **daquela gravação**. Neste arquivo: acoplamento caixa→mic **−20,5 dB** e
ERLE mediano **+17,6 dB** (min 1,4 / max 23,8) — resíduo em torno de −38 dB,
desprezível. O "~7 dB" citado no `CLAUDE.md` é o número de **uma** medição de
29/07, não uma constante: o ERLE varia com volume, sala e microfone. Abaixo de
~10 dB, a diarização volta a errar mesmo com `--aec`, e aí não há flag que
salve — só gravar de fone.

**Efeito colateral a conhecer:** onde o AEC zera o canal do mic (a interlocutora
falando sozinha), sobra silêncio — e o Whisper **alucina** nele, tipicamente
`"Obrigada."` repetido. Não é fala real perdida (é o oposto: o Gabriel
realmente não falava ali), mas polui a faixa `Eu:`. Ao ler, descartar linhas
`Eu:` curtas e genéricas que não respondem ao contexto.
