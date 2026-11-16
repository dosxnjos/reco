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

⚠️ **Meça antes de confiar, mas pela régua certa: `tools/medir_aec.py <mp3>`**,
que dá o par **(ERLE, dano na voz)** com a rotulagem alinhada (gate: ERLE mediano
≥ 5 dB, dano ≤ 2 dB em toda janela). ERLE sozinho é métrica proibida
(`CLAUDE.md`, item 4).

~~Neste arquivo: acoplamento caixa→mic −20,5 dB e ERLE mediano +17,6 dB (min
1,4 / max 23,8), resíduo em torno de −38 dB, desprezível.~~ **Métrica inválida
(corrigido em 16/11/2026, issue #22):** esses números saíram do
`tools/medir_eco.py`, que tem dois defeitos registrados em 19/08: o acoplamento
é medido só nos blocos com o mic quase mudo (viés de seleção, ver a armadilha
"`medir_eco.py` subestima o eco por construção") e o ERLE vem de rótulos por
energia simultânea com os canais desalinhados, sem o dano na voz (ver "Rotulagem
por energia simultânea mede o OPOSTO…"). Ficam aqui só como registro; não citar
como acoplamento nem como ERLE daquela gravação, que ninguém remediu. Também é
da régua antiga a regra "abaixo de ~10 dB a diarização volta a errar mesmo com
`--aec`": o limiar não vale para o ERLE do `medir_aec.py`. O que segue válido: o
ERLE varia com volume, sala e microfone (não é constante), e gravar de fone é o
único jeito de zerar o eco na origem. Números honestos do `cancel_echo` e o
"~7 dB" de 29/07 (também inválido): `docs/ARQUITETURA.md` e o § 1.3 de
`roadmap/2026-08-19-melhoria-antieco-de-verdade.md`.

**Efeito colateral a conhecer:** onde o AEC zera o canal do mic (a interlocutora
falando sozinha), sobra silêncio — e o Whisper **alucina** nele, tipicamente
`"Obrigada."` repetido. Não é fala real perdida (é o oposto: o Gabriel
realmente não falava ali), mas polui a faixa `Eu:`. Ao ler, descartar linhas
`Eu:` curtas e genéricas que não respondem ao contexto.
