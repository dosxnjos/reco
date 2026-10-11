## Relatório de execução — Fase 0 (2026-10-11, sessão 7d21540f)

Card `c7a92e98d9748`, executor sonnet 5.5 em tree principal `C:\Dev\Reco` (master).
frescor: ok (11 dias, 5 commits em `Reco` desde 30/09, nenhum toca `reco.py`;
`6d5bebccb1cd` e cards de Fase 1–4 lidos). aceite: fase sem critério.

### O que foi feito, por passo

- **0.1** `reco.py` tinha +126/−6 (o md diz "+132/−6": são as 132 linhas alteradas, 126
  inseridas + 6 removidas; mesmos elementos: `nota_dir`, `prefix=`, `_start_nota`,
  `_run_nota_final_pass`). `python tools/test_encoder.py` → `TUDO OK`. Commit
  `832527e`, só `reco.py`. Provas: `git status --short reco.py | wc -l` → `0`;
  `callers 0`. Nota gravada no card `6d5bebccb1cd`.
- **0.2** `docs/ARMADILHAS.md` (+13) em `e020f49`, sozinho. `md` + `roadmap/README.md`
  regenerado entram no commit final desta fase (após os `[x]`).
- **0.3** `soundcard==0.4.6` em `requirements.txt` e `build.ps1`; `+` também em
  `setup.ps1` (o loop instalava sem versão; achado do revisor). Prova: `pin 3`
  (contrato pedia `pin 2`; o 3º é o complemento). Instalado: 0.4.6.
- **0.4** `tools/varrer_silencio.py` (streaming, janela de 1 s, `ProcessPoolExecutor`
  com `as_completed`, pasta ou arquivos) + linha em `docs/TOOLS.md`. Commit `45f9d2d`.
  Prova: PDI de 29/09 →
  `dur=424 r_zero_inicio=424 r_zero_total=424 r_maior_seq=424 mic_maior_seq_zero=0`.
  **Vermelho por mutação** (cópia em `temp/mut/`, trocar `bloco[1]` por `bloco[0]`):
  mesmo arquivo dá `r_zero_inicio=0 r_zero_total=0` — a prova reprova com o canal
  errado. Varredura do acervo: 83 arquivos, 0 erro, 2 min 33 s
  (`temp/2026-10-11-varredura-silencio.txt`, não versionado): 58 com
  `r_zero_inicio=0`.

### Revisão adversarial (`revisor-diff`, contexto zero)

Comparou `medir()` com referência ingênua em 12 MP3 reais (5 métricas iguais), rodou
o acervo todo. Achados e destino:

1. `setup.ps1` sem o pin → **corrigido**.
2. Arquivo passado pelo nome com `_alinhado` era descartado em silêncio →
   **corrigido** (filtro só em pasta).
3. Worker morto derrubava o lote (`BrokenProcessPool`) → **corrigido** (`try` em
   volta de `fut.result()`).
4. `dur` é piso inteiro (janela final parcial não conta) → **documentado** no
   cabeçalho.
5. Arquivo sem stream de áudio dava `list index out of range` → **corrigido**
   (`ERRO sem stream de áudio`).
6. Observação: MP3 sintético com R zerado deixou resíduo de 0,001–0,006 nas janelas
   de borda e `.any()` contou como som. Nos 12 reais e no PDI não aparece →
   **documentado** no cabeçalho como ressalva ("zero exato" depende do encoder).

advisor: consultado depois do commit de código (fable). Procedeu e foi corrigido:
(a) "dist/ intacto" não estava provado — de fato 26 arquivos tinham sumido
(ver abaixo); (b) a propagação tinha pegado só 20 de 31 cards — refeita lendo
`dados/pendencias.json`; (c) decisões técnicas saíram do arquivo de pendências para
cá. Recusado: nada.

### Falha do build e restauração do `dist/` (fato novo, não previsto no md)

`build.ps1` (regra do CLAUDE.md: recompilar depois de tocar em `reco.py`) falhou:
`PermissionError: [WinError 5]` em `dist\Reco\_internal\av\audio\codeccontext.pyd`,
porque o `Reco.exe` do Gabriel está aberto (pid 19760, desde 10/10 21:27). Antes de
falhar o PyInstaller apagou 26 arquivos do `dist/Reco/_internal` (ícones, `.pyd` do
`aiohttp`, `dist-info` do `attrs`, `av/audio/codeccontext.py/.pxd`). Comparei com
`build/reco/COLLECT-00.toc` (de 19/08) → 26 faltando; restaurei 27 cópias pelas
origens do próprio TOC → 0 faltando. Documentado em `docs/ARQUITETURA.md` § Build.
O build **não foi refeito**: nada desta fase chega ao exe (modo nota inerte).

### Decisões técnicas — Fase 0

| decisão | motivo | confiança | o que reverteria |
| --- | --- | --- | --- |
| Não pausar o maestro antes de commitar (o briefing pedia) | `janela.py abrir` devolve rc 2 para a própria rodada do maestro, por desenho; o risco coberto (stash do pre-commit sobre WIP alheio) não existia: stash é por repo e nenhuma outra sessão viva tinha `cwd` no Reco | alta | outra sessão aparecer no Reco durante a fase |
| Não matar o `Reco.exe` aberto nem repetir o build | é o app em uso do Gabriel (ação dele); nada do exe muda nesta fase | alta | Fase 1.7 exigir o exe novo (aí `[[ESPERANDO]]`) |
| Restaurar o `dist/` pelo TOC em vez de deixar quebrado | um dist com ícones e `.pyd` faltando quebra a próxima abertura; restaurar é reversível (cópias) | média: as origens são as de hoje, não as de 19/08 | `build.ps1 -Clean` com o app fechado refaz tudo |
| Limiar da regra B suave (Fase 2): **recomendar 120 s**, sem mudar o md | a varredura achou `10/10 21:27` com `r_zero_inicio=182` com som depois, e `21/08` (73 s, tratada como boa pelo arquiteto) já ultrapassa os 60 s: o gatilho de reversão do § Decisões disparou. Tabela: 60 s alarma 3 gravações com som depois, 120 s alarma 2, 200 s alarma 1 mas perde dois mudos inteiros (27/09 de 86 s e 168 s) | média | o Gabriel dizer que a de 10/10 era o bug (60 s fica) |

A decisão final do limiar é do executor da Fase 2 (nota gravada no card
`c1884663accca`); a tabela de limiares está nesta linha e na § Medição nova.

### completei:

- `setup.ps1` com o pin (o contrato citava só `requirements.txt` e `build.ps1`).
- Ferramenta robusta além do pedido: erro por arquivo, `as_completed`, worker morto,
  arquivo sem áudio, ressalva do encoder.
- Varredura completa do acervo (os 15 arquivos que a 2ª varredura de 30/09 não leu).
- Nota de "build trava com o app aberto" em `docs/ARQUITETURA.md` § Build.
- Restauração do `dist/`.

### Medição nova (varredura de 11/10, 83 arquivos)

| medição | resultado |
| --- | --- |
| R mudo inteiro (`r_zero_inicio == dur`) | 4: 27/09 20:19 (802 s), 27/09 21:56 (168 s), 27/09 21:14 (86 s), PDI 29/09 (424 s) |
| R com som depois e `r_zero_inicio` ≥ 60 s | 18/07 (338 s), 10/10 21:27 (182 s de 312 s, **gravação nova**), 21/08 (73 s) |
| mic em zero exato, maior sequência | 174 s em 31/07; 8 s em 13/09; 4 s em 3 arquivos; ≤ 3 s no resto (a regra C de 10 s não dispara em nenhum além de 31/07) |

### propagou: 6 cards, 0 mds

Anotados: `cd1483d67a708` (Fase 1), `c1884663accca` (Fase 2), `c5c0e64bb55c8` (Fase 3),
`cde8bf98a2853` (Fase 4), `cd2edd29532b5` (modularização Fase 0) e
`6d5bebccb1cd` (modo nota). Não afetado: `c4b056f69190a` (modularização Fase 1, folhas
`audio_io`/`i18n`/`config`: não cita o que mudou). md de modularização tem card aberto
(`cd2edd29532b5`), então vai pela nota do card, sem `## Atualizações recebidas`.

### Arquivos tocados e commits

`832527e` (reco.py), `e020f49` (docs/ARMADILHAS.md), `45f9d2d` (`build.ps1`,
`requirements.txt`, `setup.ps1`, `tools/varrer_silencio.py`, `docs/TOOLS.md`,
`docs/ARQUITETURA.md`); commit final: este md, `roadmap/README.md`, a pasta `.d/`.

### Pendências e decisões pendentes

1. **Gabriel:** fechar o `Reco.exe` aberto e rodar o build antes de reabrir o app
   (detalhe em [pendencias-decisao-2026-10-11-7d21540f.md](pendencias-decisao-2026-10-11-7d21540f.md)).
2. **Gabriel (opcional, sem bloquear):** a gravação de 10/10 21:27 (182 s de sistema
   mudo no início) era o bug ou reunião normal? Define o limiar de 60 s × 120 s da Fase 2.
3. As 4 outras gravações com sistema mudo inteiro (27/09 ×3 e PDI) seguem do
   § O que o pedido não dizia; o PDI é o incidente, as 3 de 27/09 só ele sabe.
