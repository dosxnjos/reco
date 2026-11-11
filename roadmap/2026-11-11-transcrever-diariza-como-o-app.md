# `tools/transcrever.py` diariza gravação do Reco como o app (11/11/2026)

## Entendimento

Pedido do Gabriel: os `.mp3.txt` da pasta `Documents\Reco` saem como texto corrido,
enquanto os `.txt` do botão "Salvar + transcrever" saem com `Eu:` / `Interlocutor(es):`.

Causa (verificada no código e nas sessões locais):

- O app tem um caminho só de transcrição, `App._run_transcriber` (`reco.py`), que liga
  diarização e AEC quando o nome tem a etiqueta `reco` (`is_reco_recording`) e a config
  pede (`diarize`, `aec` do `~/.reco_config.json`). Grava `x.txt` (`_autosave_txt`).
- Todo `x.mp3.txt` vem de `tools/transcrever.py`, o "ouvido dos agentes". Ele tem
  `--diarizar`/`--aec` **desligados por padrão**, e as docs que as sessões seguem
  (`cerebro/temas/harness/guides-e-sensores.md`, `vocabulario-curto.md`, `Reco/CLAUDE.md`)
  mandam rodar sem flag. Prova: o lote de 10/11 09:23 saiu da sessão `afdb4ac2` (triagem
  de issues), que rodou `python tools/transcrever.py` seguindo o guia.
- Escreve `src.with_suffix(src.suffix + ".txt")` = `x.mp3.txt`, que a biblioteca do app
  não lê (armadilha 026).

## Decisões

1. **Sem flag, o script decide como o app**: gravação do Reco (`is_reco_recording`, `.mp3`)
   → diariza e cancela eco conforme a config. Nunca diariza sem AEC por conta própria
   (armadilha 009: sem AEC, as faixas repetem o mesmo texto em gravação no alto-falante).
   `--diarizar`/`--aec` continuam como "forçar"; `--texto-corrido` desliga (uso legítimo
   registrado no histórico: só conteúdo, sem autoria). Confiança alta; reverte tirando o
   ramo automático.
2. **Nome da saída igual ao do app para gravação do Reco**: `x.txt`. Uma convenção por tipo
   de arquivo: gravação do Reco = `x.txt` (app e script); qualquer outro áudio =
   `<arquivo>.<ext>.txt` (contrato do coletor do WhatsApp e do `instagram_post.py`,
   intacto porque esses nomes não têm a etiqueta `reco`). Confiança média-alta; reverte
   voltando a regra única antiga.
   - Pula se `x.txt` existe (feito pelo app ou pelo script novo).
   - `x.mp3.txt` antigo **não** conta como pronto: é o texto corrido do bug; o script avisa
     e gera o `x.txt` diarizado ao lado, sem apagar nem renomear o antigo.
   - `--texto-corrido` mantém o nome antigo `x.mp3.txt` (não é o que o app faria).
3. **`pretriar_transcricoes.py`**: com `x.txt` novo e `x.mp3.txt` antigo no mesmo radical,
   a regra "`.mp3.txt` na frente" faria o bruto vencer. Nova precedência: `_alinhado`
   primeiro, depois o mais recente (mtime).
4. **Não mexer no `reco.py` agora**: o Reco.exe está aberto (pode estar gravando) e a regra
   do projeto exige recompilar. O ramo headless `Reco.exe --transcribe` tem o mesmo
   defeito (só diariza com `--diarize`), fica como pendência com o E3a do roadmap
   `2026-08-21-salto-de-alinhamento-sob-carga.md`.
5. **Acervo**: depois da prova, retranscrever em segundo plano (GPU, prioridade baixa) as
   gravações `gravacao_reco_*.mp3` (sem `_alinhado`) que só têm `.mp3.txt`. Gera `x.txt`
   novo ao lado; nada é apagado. Pares `_alinhado` e as de 21/08 ficam fora (decisões do
   § 4.15 do roadmap de 21/08).

## Ajustes da revisão adversarial (11/11, 3 lentes + verificação)

- **Modelo/dispositivo não seguem a config do app** (a 1ª versão seguia): NPU escolhida no
  app quebraria `instagram_post.py` e o importador do WhatsApp, que não passam `--device`
  (armadilha 028). Fica AUTO, ou a flag.
- **`x.txt` só na pasta de gravações do app** (`output_dir` ou `Documents\Reco`): o
  importador do WhatsApp calcula `midia + ".txt"`, e uma gravação do Reco que chegue como
  anexo com o nome original quebraria. Fora da pasta: diarizado, mas em `x.mp3.txt`.
- **`x.mp3.txt` antigo já diarizado é aproveitado** (7 dos 43 foram feitos com
  `--diarizar`); só o corrido gera `x.txt` ao lado.
- **`pretriar` por conteúdo, não por data**: `_alinhado` > diarizada > `x.txt` >
  `x.mp3.txt`. Em 21/08 o `.mp3.txt` bruto é o mais novo, então mtime escolhia errado.
- Não mexido: o `planejar()` do `pretriar` reaproveita a sugestão s/n da linha antiga
  quando a versão escolhida troca (mesma gravação, mesmo assunto; reler custaria cota).
  O idioma segue `--lang pt` (o app usa o idioma da config; o Gabriel usa pt).
- Acervo: 27 gravações (12 h de áudio) chegaram a entrar na fila, mas o Gabriel mandou
  parar (já trabalhou em cima dos `.mp3.txt`). Parado antes do 1º arquivo; o passo 6
  está cancelado. Os antigos não são sobrescritos: rodar o script num deles cria
  `x.txt` ao lado.

## Passos

1. `tools/transcrever.py`: `opcoes(src, cfg, args)` → `(diarize, aec)` e
   `destino(src, diarize)`; docstring e `--help` atualizados.
2. `tools/pretriar_transcricoes.py`: precedência por mtime.
3. Prova por comportamento (scratchpad, cópia com o nome original):
   gravação curta com `.txt` do app → sem flags sai `Eu:`/`Interlocutor(es):` em `x.txt`;
   `.m4a` comum continua `x.m4a.txt` em texto corrido; `--texto-corrido` volta ao bruto;
   arquivo com `reco` no nome e mono não quebra.
4. Revisão adversarial (Workflow).
5. Docs rio abaixo: docstring, `Reco/CLAUDE.md`, `docs/TOOLS.md`, `docs/ARQUITETURA.md`,
   `cerebro/temas/harness/guides-e-sensores.md`, `vocabulario-curto.md`; armadilha nova
   por `python tools/visoes.py novo`.
6. Acervo em segundo plano.
7. Commit por pathspec (repo público: sem trecho de transcrição em teste ou doc); diário.

## O que o pedido não dizia

- Nome da saída igual ao do app: sem isso a biblioteca segue sem ver o arquivo novo.
- Precedência do `pretriar`: senão o texto bruto antigo continuaria vencendo o novo.
- Retranscrição do acervo: o conserto só vale para o futuro; os 43 antigos seguiriam brutos.
- Docs que ensinam "sem flag": são elas que fazem as sessões errarem.
