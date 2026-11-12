---
titulo: O MP3 só nasce no 1º pedaço de áudio, não no Gravar
data: 2026-11-12
---
**Sintoma:** depois do clique em Gravar, a pasta de saída fica sem o `gravacao_reco_*.mp3` por
**~11 s com eco** (som do PC chegando ao mic) e **~20,7 s sem eco** (medido de fora no exe, Fase 0 do
roadmap Reco em Rust, passos 11 e 12: 11,0–11,2 s em 2 rodadas com eco detectado; 20,7–20,9 s nas
demais, `temp/medicoes/partida.jsonl`). Uma checagem única de "há gravação em curso?" pela trava do
arquivo (`tools/medir_partida.py --checar-gravando`) responde "nenhuma" nesse intervalo.

**Causa:** o `MP3Writer` é criado no `start()` (o nome e o timestamp saem dali), mas o PyAV só cria o
arquivo no disco no primeiro pacote gravado: `av.open(caminho, "w")` + `add_stream` não cria nada, nem
o `close()` sem pacote (provado à parte em 11/11/2026). O `_pump` só entrega áudio ao encoder quando o
alinhamento fecha (`ALIGN_COLETA_S = 10`, com eco) ou desiste (`ALIGN_DESISTE_S = 20`, sem eco). Isso
contradiz o comentário de `reco.py:1660-1662` ("a crash mid-meeting leaves a playable partial MP3"):
um crash nos primeiros 11 a 21 s não deixa MP3 nenhum.

**O que fazer:** guarda que decide "pode fechar o Reco" pela trava do arquivo precisa de **duas
checagens com mais de 20 s entre elas** (o passo 9 da Fase 0 usa 25 s); uma só fica cega de 11 a 21 s.
Não prometer MP3 parcial para queda nos primeiros 20 s. O comentário do `reco.py` segue errado até
alguém mexer no arquivo (exige recompilar); a regra 3 do `CLAUDE.md` e o `docs/ARQUITETURA.md` já dizem
o medido.
