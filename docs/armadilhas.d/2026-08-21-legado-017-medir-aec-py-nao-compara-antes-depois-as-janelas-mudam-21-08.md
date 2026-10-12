---
titulo: `medir_aec.py` não compara antes×depois: as janelas mudam (21/08/2026)
data: 2026-08-21
---
**Sintoma.** Depois de alinhar a gravação de 21/08 10:41 (residual medido 0,0 ms),
o `tools/medir_aec.py` mostrou o ERLE mediano **caindo** de +5,6 para +0,5 dB.
Lido de forma ingênua: "alinhar piorou o AEC" — conclusão falsa.

**Causa.** O script **escolhe as janelas pelo perfil de energia do arquivo** (as
que têm mais blocos rotuláveis como só-far-end e só-near-end). Alinhar muda esse
perfil, então o original foi medido em 2,9 / 3,8 / 4,0 / 4,4 / 4,9 / 6,5 min e o
alinhado em 2,8 / 5,0 / 6,5 / 9,0 / 9,5 / 10,5 min. **São trechos diferentes do
áudio** — e naquele arquivo os minutos finais não têm áudio do sistema tocando
(`q` < 0,05), então o "ERLE" ali é ruído medido contra referência inexistente.

**O que fazer.** Para comparar duas versões do mesmo áudio, comparar **as mesmas
janelas** (o script hoje não aceita janelas fixas — é o que falta implementar) ou
julgar pelo par que não depende da escolha: **atraso por janela** (0 em todas,
depois de alinhar) e a **transcrição**. O ERLE mediano só é comparável entre
arquivos medidos com o mesmo perfil de conteúdo. No arquivo de 11:16, onde 9/9
trechos correlacionam e as janelas caíram no mesmo material, a comparação vale e
deu +5,6 → +12,2 dB.

⚠️ Isto vale para **qualquer** comparação antes/depois neste projeto: instrumento
que escolhe sozinho o que medir não serve para medir mudança.

---
