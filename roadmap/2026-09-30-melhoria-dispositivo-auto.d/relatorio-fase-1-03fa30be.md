## Relatório de execução — Fase 1 (2026-10-11, sessão 03fa30be)

Card `cd1483d67a708`, executor sonnet 5.5 no tree principal `C:\Dev\Reco` (master), sem
worktree. frescor: ok (11 dias; só os 5 commits da Fase 0 desde 30/09, nenhum mexe nos
símbolos da fase; notas do card lidas). aceite: fase sem critério.

**Estado final: passos 1.1–1.6 feitos e verdes; 1.7 (build) NÃO feito** porque o `Reco.exe`
do Gabriel continua aberto (pid 19760): ver § Pendências. Código commitado e pushado
(`master`), `[ ]` do 1.7 mantido no md.

### O que foi feito, por passo (e a prova)

- **1.1** `default_endpoint_id(kind, role)` (API privada do `soundcard` 0.4.6; papel 2 falho
  cai no 0). Prova `python tools/test_dispositivo_auto.py` → `OK console==soundcard (speaker,
  microphone) · comm resolvido · thread ok · 4 chamadas < 50 ms` (medido 3–5 ms).
  Vermelho antes: `AttributeError: module 'reco' has no attribute 'default_endpoint_id'`
  (commit `9d83c1b`, teste sozinho). `--listar` implementado (passo 4.1 usa).
- **1.2** `AUTO_CONSOLE`/`AUTO_COMM`, `resolve_audio_device(valor, kind) -> (id, nome, via)`
  com enumeração fresca; id ausente cai no console com `via="ausente"` e nunca volta como
  id. `pick_device` e `id_for_name` removidos. Prova → `OK resolve_audio_device (4 casos)`
  + `OK papéis Auto independentes da máquina (1 fluxo(s) com 2+ endpoints)`.
  **Mutações executadas** (cópia de scratch, guard apontado pela cópia): (A) fluxo
  speaker/mic invertido → `FALHOU console≠soundcard`; (B) id morto devolvido → `FALHOU manual
  ausente`; (C) Auto devolve o 1º da lista → `FALHOU papéis (speaker, valor='auto:console')`;
  (D) comm vira console → `FALHOU papéis (speaker, valor='auto:comm')`. C e D só morreram
  depois do reforço com papéis forjados (nesta máquina console == comm == 1º da lista).
- **1.3** `_CFG_DEFAULTS` → `"auto:console"`, `CFG_MIGRACAO = 2`, bloco `v < 2`
  incondicional. Prova → `True auto:console auto:console 2`; vermelho antes: `False
  {0.0.0.x} {0.0.1.y} 1`. Backup do JSON real em `temp/reco_config.antes-migracao-2.json`
  (não versionado) **antes** do 1º `import reco` com a migração.
- **1.4** Combo com 2 Auto no topo (rótulos com o nome resolvido), `<<ComboboxSelected>>`
  mapeando por **índice** (`_on_device_selected`), `trace_add` e `_on_device_change`
  removidos, `_populate_devices` não grava. Id salvo ausente mostra "Dispositivo salvo
  (ausente: usando o padrão do Windows)" sem gravar. Prova → `autosave 0` (era `2`).
  **Verificação do Tk (manual→script):** smoke com `App()` real e HOME isolado: abrir o app
  não muda o JSON (`config_inalterado_ao_abrir True`); `current(1)`+evento grava
  `auto:comm`; `current(2)`+evento grava o id; id ausente → rótulo de aviso e o JSON fica.
- **1.5** `_start_rec`/`_start_nota` resolvem pelo config (`_resolve_devices`, síncrono no
  clique: exceção declarada à regra "COM fora do Tk"); status `Gravando…  mic: {m} ·
  sistema: {s}` + aviso de ausente; `self._rec_devs` guardado. Prova → `lista_velha 0`
  (era `3`). Tempo medido do caminho real do clique: `resolve_audio_device` (mic + sistema)
  3–5 ms + `scan_device_state` ~6 ms.
- **1.6** 7 chaves novas no `_TR_EN`, 0 mortas (a chave velha de "(mic + sistema)" saiu).
  Prova → `OK — cobertura completa, nada morto.`
- **1.7** `python tools/test_encoder.py` → `TUDO OK`; `python reco.py --selftest` →
  `resolved(AUTO)=GPU`. **Build não rodado** (ver pendência).

### Revisão adversarial e advisor

`revisor-diff` (contexto zero) derrubou o diff antes do commit. Achados:

1. **Crítico, corrigido:** `resolve_device` já existia (acelerador OpenVINO, l.1114); a 2ª
   `def` o sobrescrevia sem erro e toda transcrição (e o `--selftest`) levantava `TypeError`.
   O nome vinha do md. Renomeada para `resolve_audio_device` (md, doc e guard corrigidos),
   guard ganhou checagem de def duplicada e de `resolve_device('AUTO')` intacto (vermelho
   mostrado: `FALHOU def/class duplicada no nível do módulo: ['resolve_device']`).
2. Baixo, corrigido: aviso de ausente sumia no ramo `live_suprimido` e no retomar da pausa
   (que ainda dizia "mic + sistema" inclusive em nota) → `_status_gravando()` único.
3. Baixo, **registrado, não corrigido:** `auto:comm` cuja API privada falha cai no console
   só com `print` (retorna `via="auto"`); em ARQUITETURA e no card da Fase 2.
4. Baixo, corrigido: a doc dizia "~5 ms" e "scan fora do Tk"; o clique também roda
   `scan_device_state` → doc e guard (cronometra) corrigidos.

`advisor:` fable consultado antes da escrita e depois do commit. **Procedeu e foi
corrigido:** (a) backup do JSON e vermelhos das provas estáticas antes do 1º Edit; (b) o
guard foi para commit próprio *antes* do conserto (regra do teste travado); (c) cronometrar
o caminho real do clique; (d) **bloqueador:** o `load_config()` de import-time persistia a
migração 2 no JSON real; o exe antigo, ao abrir, regrava o id do padrão mantendo
`_migracao: 2`, e o exe novo trataria o id como manual: re-armaria o bug sem migração que
o conserte. Corrigido: `load_config(persist=False)` por padrão, só `App.__init__` persiste;
guard falha se `import reco` mudar o JSON (vermelho no HEAD com config v1 isolada:
`FALHOU import reco reescreveu ~/.reco_config.json`); o JSON real foi **restaurado do backup
para v1** (`cmp` idêntico), e ARMADILHAS/ARQUITETURA registram a regra. (e) propagação para
os 6 cards. **Recusado:** nada. Baixo anotado: `_start_rec` não zera `self._nota`
(inerte: `_start_nota` ainda sem caller; nota no card `6d5bebccb1cd`).

### Decisões técnicas — Fase 1

| decisão | motivo | confiança | o que reverteria |
| --- | --- | --- | --- |
| Nome `resolve_audio_device` em vez de `resolve_device` do md | colisão com a função do acelerador; renomear a antiga mexeria em 4 chamadores + tools | alta | nada (nome puro) |
| Testes em 4 commits próprios antes do conserto, e o último ajusta o nome do md | regra do teste vermelho travado (card `tipo: bug`); o rename e os reforços não afrouxam asserção alguma | alta | — |
| `load_config(persist=False)` por padrão | advisor: persistir antes do exe novo re-arma o autosave do exe antigo; também impede ferramentas/testes de reescrever o JSON real | alta | o 1.7 buildado: aí o persist no `import` seria inofensivo (mas continua indesejável) |
| Restaurar o `~/.reco_config.json` real ao v1 (backup) | mesma causa; reversível (`cp` do estado migrado, ou o `App` novo migra sozinho) | alta | — |
| Commit da fonte sem o build, 1.7 `[ ]`, sinal `[[ESPERANDO]]` | o build com o app aberto apagou 26 arquivos do `dist/` na Fase 0; deixar `reco.py` sujo no master travou o roadmap por 7 semanas (modo nota) | alta | Gabriel fechar o app: o build roda e fecha o 1.7 |
| `auto:comm` falho só com `print` | sinalizar exige `via` novo e a vigia da Fase 2 decide como mostrar | média | Fase 2 pedir `via="auto-console"` |
| Sem build de scratch (`--distpath` temporário) | só provaria compilação; o `reco.spec` já coleta o pacote `soundcard` inteiro | média | exe novo falhar na 1ª abertura |

### completei:

- Backup do JSON antes da migração (briefing) e restauração depois (advisor).
- Guard mais forte que o do md: papéis forjados, def duplicada, `import` não grava, tempos.
- `--listar` (o 4.1 dependia dele).
- `_status_gravando()` e aviso de ausente também no retomar e no ramo `live_suprimido`.
- Docs: ARQUITETURA § Dispositivo (e a exceção da migração 2 à regra "só default antigo"),
  TOOLS, 2 entradas de ARMADILHAS (migração antes do exe novo; def duplicada).
- Hub `cerebro/projetos/reco.md` e fragmento do diário (abaixo).

### propagou: 6 cards/0 mds

Anotados `c1884663accca` (Fase 2), `c5c0e64bb55c8` (Fase 3), `cde8bf98a2853` (Fase 4),
`cd2edd29532b5` e `c4b056f69190a` (modularização; este corrige o "não afetado" da Fase 0),
`6d5bebccb1cd` (modo nota). Mds sem card aberto: os 3 que citam `resolve_device` falam do
acelerador OpenVINO, que continua válido (não afetados).

### Arquivos tocados e commits

`9d83c1b`, `15ee9ae`, `01ca49f`, `9997cae` (só `tools/test_dispositivo_auto.py`, vermelhos),
`5ddfcd2` (`reco.py`, `docs/ARQUITETURA.md`, `docs/TOOLS.md`, md), `8a19d1d` (`reco.py`,
`docs/ARMADILHAS.md`, `docs/ARQUITETURA.md`); commit final: este relatório, o md/README dos
roadmaps. `master` pushado até `8a19d1d`.

### Pendências e decisões pendentes

1. **Gabriel (ação física, bloqueia o 1.7):** fechar o `Reco.exe` e rodar `build.ps1`;
   detalhe e receita em [pendencias-decisao-2026-10-11-03fa30be.md](pendencias-decisao-2026-10-11-03fa30be.md).
   ⚠️ **Não reabrir o Reco antigo antes do build.**
2. Carregadas da Fase 0 (sem mudança): gravação de 10/10 21:27 (bug ou reunião?) e as 3 de 27/09.
