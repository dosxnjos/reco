---
titulo: Áudio comprimido antes de transcrever zera o arquivo inteiro — o VAD tem limiar global (26/08/2026)
data: 2026-08-26
---
**Sintoma:** um arquivo longo tratado com compressor/limiter (para recuperar fala
distante) volta da transcrição com **uma linha só** — `.` — ou duas ou três
palavras, sem erro, sem exceção, sem aviso. O log mostra `Transcrevendo… 0%` e o
processo termina normalmente. Pedaços de 5 min do **mesmo arquivo tratado**
transcrevem perfeitamente (800+ palavras), o que faz parecer defeito de duração
ou de memória. Não é: um arquivo de 80 min sem tratamento transcreve inteiro.

**Causa:** `segmentar_por_vad()` (`reco.py`) calcula o limiar de fala **sobre o
arquivo inteiro** — `piso = percentil 20 da energia dos quadros de 30 ms`,
`lim = max(piso × 3, 0.0035)`. O VAD depende do **contraste** entre silêncio e
fala. Compressor e limiter existem justamente para destruir esse contraste: eles
levantam o piso, o percentil 20 sobe junto, `lim` sobe com ele e quase nenhum
quadro passa como fala. Em trechos curtos o piso é recalculado localmente e o
contraste local sobrevive — daí o teste em pedaço enganar. Medida no caso real:
o áudio tratado não tinha **nenhum** silêncio detectável a −33 dB
(`silencedetect`), contra 6 no original.

**O que fazer:** ao transcrever áudio que passou por compressão dinâmica,
**fatiar em blocos** (5 min funciona) e transcrever bloco a bloco — o VAD
recalcula o piso em cada um. Passar todos os blocos numa única invocação do
`tools/transcrever.py` carrega o modelo uma vez só. E não confie em teste de
trecho para validar tratamento de arquivo longo: o trecho é justamente o caso
em que o defeito não aparece.

⚠️ **Corolário, medido no mesmo material:** tratamento não é ganho universal. Em
trechos com aplauso alto ou áudio de vídeo tocando na sala, o compressor esmaga
a fala e o **áudio cru rende mais** (425 contra 3 palavras num bloco de 5 min).
Em gravação estéreo de dois microfones, vale medir **canal a canal**: os dois
raramente prestam igual — no caso real o canal direito deu 302 palavras
distintas contra 149 do esquerdo no mesmo trecho, e o downmix ficou no meio
porque **soma o ruído do pior**. Mas tratar um canal isolado piora tudo: a
cadeia com compressor depende dos ~4 dB de SNR que a soma dos dois canais dá.
Régua prática: escolher a fonte **por bloco**, comparando palavras distintas.

---
