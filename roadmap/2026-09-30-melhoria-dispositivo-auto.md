# Roadmap de melhoria — Reco: opções "Auto" de dispositivo (2026-09-30)

Risco: dado (a Fase 1 reescreve `~/.reco_config.json` por migração; gravação
no dispositivo errado perde a fala do outro lado sem erro nenhum)

Card: `c00f415c2ae28` (urgente até 02/10/2026). Arquiteto: opus 5.5 com
advisor fable, 30/09/2026.

## Contexto e motivação

Em 29/09/2026 o PDI do Gabriel com a Andressa foi gravado **sem a voz dela**.
Ele estava no fone Bluetooth "QCY do Gabriel", que era o padrão do Windows; o
Reco gravou o loopback dos alto-falantes Realtek, que estavam mudos. Nenhum
erro, nenhum aviso.

Medido nesta sessão no arquivo do incidente
(`Documents/Reco/gravacao_reco_2026-09-29_15-37-18.mp3`, 425 s):

| canal | RMS mediano | segundos em zero digital exato |
| --- | --- | --- |
| L (mic) | −27,7 dB | 0 de 424 |
| R (sistema) | −240 dB (zero) | **424 de 424** |

O pedido, nas palavras dele: "quero que ele tenha as opções 'Auto' dentro
dele, pra que siga o que está decidido pelo Windows. padrão ou padrão para
comunicações".

**Ler antes de começar:**

- `C:\Dev\Reco\CLAUDE.md` (regra de recompilar; opção nova em `_CFG_DEFAULTS`
  + `_migra_config`).
- `docs/ARMADILHAS.md` § "O `soundcard` fabrica silêncio pelo relógio quando o
  loopback está mudo" (l.535): é a base do detector da Fase 2.
- `docs/ARQUITETURA.md` § Config e persistência (l.264).
- Este md inteiro, em especial § Riscos (tree sujo de outra sessão).

## O que o pedido não dizia

**Feito (técnico, reversível; vira passo marcado `+`):**

- `+` **A causa-raiz é o autosave, não só o `pick_device`.** O trace de escrita
  do combobox grava como "escolha" o dispositivo que o próprio app pré-selecionou
  na 1ª abertura; sem cortar isso, o Auto nasce com a mina armada (passo 1.4).
- `+` **Migração incondicional para Auto** nesta máquina e em qualquer config
  existente: nada no JSON distingue escolha deliberada de autosave (passo 1.3).
- `+` **Auto resolve com enumeração fresca**: fone conectado depois de abrir o
  app funciona sem clicar "Atualizar dispositivos" (passo 1.5).
- `+` **Pin `soundcard==0.4.6`** no `requirements.txt` e no `build.ps1`: o papel
  "comunicação" usa API privada do pacote (passo 0.3).
- `+` **Alarme de silêncio também no mic** (zero exato = mic mudo no hardware ou
  na privacidade do Windows), mesmo mecanismo, custo marginal (passo 2.1).
- `+` **Prova automatizada do caso do bug sem o fone**: tocar um tom no
  Realtek e gravar o loopback do monitor LG reproduz "canal mudo" (passo 3.2).
- `+` **Resolver o tree sujo antes** (WIP de outro card, ver § Riscos).

- `+` **Limiar do alarme medido, não chutado**: a varredura do acervo mostrou
  que "10 s de silêncio" dispararia em quase toda reunião; o alarme passou a
  olhar "mudo desde o início" (60 s) e "dispositivo ≠ padrão" (§ Fase 2).

**Proposto (fora do escopo, sem urgência):**

- Troca a quente do dispositivo no meio da gravação (hoje: só aviso). Ver § O
  que NÃO fazer. Recomendo esperar a Fase 4 dizer se o aviso basta.
- **Outras 5 gravações com o sistema mudo inteiro** (18/07, 31/07 e três de
  27/09; § Medições). Podem ser o mesmo defeito, com fala do outro lado
  perdida, ou reunião presencial. Só o Gabriel sabe; recomendo ele olhar as
  três de 27/09 primeiro (são as mais recentes). Não bloqueia nada.

**Descartado:** nenhum outro.

## Alvo e estado atual

Tudo em `reco.py` (números de linha do working tree de 30/09, que inclui o WIP
do modo nota; depois do passo 0.1 eles ficam iguais):

- `_CFG_DEFAULTS` (l.103): `mic_device`/`sys_device` = `None` (l.119-120).
- `list_capture_devices` (l.1306), `default_mic_id` (l.1323),
  `default_speaker_id` (l.1332): só o papel `eConsole`, via
  `sc.default_microphone()`/`sc.default_speaker()`.
- `pick_device` (l.1341): **id salvo vence o padrão** do Windows.
- `_build_advanced` (l.3232-3252): dois `ttk.Combobox` "Entrada:"/"Saída:", com
  `var.trace_add("write", … _on_device_change)`.
- `_on_device_change` (l.3349): grava o id no config a cada escrita da var.
- `_populate_devices` (l.3589): faz `var.set(...)` programático → dispara o
  trace → **o padrão do dia da 1ª abertura vira `sys_device` para sempre**.
- `_start_rec` (l.3623) e `_start_nota` (l.3690, WIP): `id_for_name(lista do
  scan, nome do combo)`.
- `DualRecorder._rec_mic` (l.1672) / `_rec_sys` (l.1696): abrem com
  `sc.get_microphone(id, include_loopback=…)`, que re-enumera os endpoints.

Config atual desta máquina: `sys_device` = Realtek, `mic_device` = grupo de
microfones Intel, `_migracao` = 1.

## Diagnóstico

### O que está bom (não mexer)

- Captura por `soundcard` + loopback WASAPI real (ARMADILHAS l.203: não trocar
  por `sounddevice`).
- `sc.get_microphone(id, …)` re-enumera a cada abertura: passar o id resolvido
  na hora já pega dispositivo novo.
- Formato fixo, `_pump`, alinhamento, encode em streaming (CLAUDE.md § "o que
  não é acidente"): nada aqui toca nisso.
- Pausa: `_rec_*` faz `continue` antes de `on_level` (l.1688, l.1712).

### O que está frágil ou custando

1. **Autosave do pré-selecionado** (medido no código, l.3248 + l.3349 +
   l.3596-3603): toda escrita programática na var vira escolha persistida.
2. **`pick_device` prefere o id salvo** (l.1344): nunca segue o Windows depois
   da 1ª abertura.
3. **Só existe o papel `eConsole`** no `soundcard` 0.4.6
   (`mediafoundation.py:282-283`, `eConsole = 0` fixo). O papel
   `eCommunications` (2) exige chamar `GetDefaultAudioEndpoint` por conta própria.
   **Medido (spike desta sessão):** reusar `mediafoundation._DeviceEnumerator`,
   `_ffi` e `_com` funciona, inclusive de outra thread; `role=0` bate com
   `sc.default_speaker().id`. Sem patch no pacote.
4. **Gravar endpoint mudo não gera sinal nenhum.** O `_record_chunk` do
   `soundcard` devolve `numpy.zeros` quando o endpoint não entrega pacote
   (ARMADILHAS l.535). No incidente: 424/424 s de zero exato no canal R.
5. **`build.ps1:24` instala `soundcard` sem versão**; com API privada em uso,
   um upgrade silencioso quebra o Auto de comunicação.
6. **Mudança de padrão no meio da gravação** (fone conectado com a reunião
   andando): o stream segue no endpoint antigo, sem aviso.
7. **Bluetooth pode ter dois endpoints** (estéreo A2DP e Hands-Free) e o papel
   "comunicação" pode apontar para o Hands-Free. **Suspeita não medida**: o QCY
   não estava conectado nesta sessão (aqui só há Realtek e monitor LG).

Conceitos do acervo aplicados: **via-negativa** (a correção-mãe é *tirar* o
autosave, não só somar opções) e **ancoragem-e-confirmacao** (o limiar de 10 s
do alarme só se crava depois de medir o falso alarme no acervo, passo 0.4).

## Decisões técnicas (opus com advisor fable, 30/09)

| decisão | motivo | confiança | o que reverteria |
| --- | --- | --- | --- |
| Valor no mesmo campo: `"auto:console"`, `"auto:comm"` ou um id | sem campo novo, migração simples, id antigo continua válido | alta | outro consumidor do JSON que espere id puro (não há: só `reco.py`) |
| Default dos dois = `"auto:console"` (padrão do Windows) | é o que Chrome/Meet usam sem configurar; é o papel que o `soundcard` já cobre | **média** | Fase 4 medir que, em call com o QCY, o som sai no endpoint de comunicação → migração 3 para `"auto:comm"` |
| Migração 2 incondicional (`mic_device`/`sys_device` → `"auto:console"`) | o JSON não distingue escolha de autosave (diag. 1); mesmo racional da migração 1 | alta | usuário com dispositivo manual deliberado reclamar: escolhe de novo no combo, 1 clique |
| Padrão mudou no meio: **avisar, não trocar** | troca a quente mexe no `Barrier`, no `_al_estimar_inicial` e no estado do encoder | alta | Fase 4 mostrar que o aviso não basta na prática |
| Detector por **zero digital exato** contado em blocos, antes do ganho; alarme por "mudo desde o início ≥ 60 s" ou "manual ≠ padrão e mudo ≥ 10 s", nunca por "mudo ≥ 10 s" sozinho | zero exato só nasce do endpoint sem pacote; o acervo tem zero no meio de reunião boa o tempo todo, mas zero desde o início no máximo 73 s | alta | o passo 0.4, com os 15 arquivos que faltaram, achar gravação boa com > 60 s mudos no início (aí subir para 90–120 s) |
| WIP do modo nota: commit próprio antes de mexer em `reco.py` | evita levar código de outro card no commit errado; preserva material; autorizado pela condição 2 do decisor do card (30/09 17:50) | alta | dono do card `6d5bebccb1cd` pedir `git revert` do commit |

## Roadmap

### Fase 0 — destravar o tree e medir o limiar (sem lógica nova em `reco.py`)

⚠️ **Onde roda:** a Fase 0 roda **no tree principal `C:\Dev\Reco`, branch
`master`, nunca num worktree** — o WIP do passo 0.1 só existe ali (card de fase
com `pequeno: true`). Antes de commitar, **pausar o maestro e religar ao fim**
(`C:\Dev\CLAUDE.md` § Git). As Fases 1–3 partem do HEAD que sair daqui.

0.1. [x] (832527e; test_encoder TUDO OK; callers 0) Commitar o WIP do modo nota **sozinho** (`git add reco.py` por
pathspec; mensagem citando o card `6d5bebccb1cd` e "Fase 1 do modo nota, sem
UI, `_start_nota` sem caller"). Antes, conferir que o diff é o mesmo descrito
aqui (+132/−6, `nota_dir`, `prefix=`, `_start_nota`, `_run_nota_final_pass`) e
rodar `python tools/test_encoder.py`. Depois: `anotar_card("6d5bebccb1cd", …)`
dizendo o commit. Se o diff for outro: parar e relatar, não commitar.
— **prova:** `git status --short reco.py | wc -l` → `0`
   **reprova se:** `1` (o WIP segue fora de commit).
— **prova:** `python -c "print('callers', open('reco.py',encoding='utf-8').read().count('self._start_nota()'))"` → `callers 0`
   **reprova se:** ≥ 1 (o código deixou de ser inerte; o commit precisa de
   revisão antes).

0.2. [x] (e020f49 ARMADILHAS; md + README no commit final da fase) Commitar o adendo de 25/09 em `docs/ARMADILHAS.md` (13 linhas, "O
residual zero de 21/08 não é garantia") **sozinho**, mensagem citando o
roadmap `2026-08-21-salto-de-alinhamento-sob-carga.md`. Na sequência,
commitar **este md e o `roadmap/README.md`** regenerado (a sessão de
arquitetura de 30/09 deixou os dois fora de commit para não passar o
`pre-commit`, que faz stash do WIP alheio, com o maestro no ar).
— **prova:** `git status --short docs/ARMADILHAS.md roadmap | wc -l` → `0`
   **reprova se:** > 0.

0.3. [x] (pin 2) `+` Pin: `soundcard==0.4.6` em `requirements.txt` (linha `soundcard`)
e em `build.ps1:24` (`pip install soundcard==0.4.6 lameenc …`).
— **prova:** `python -c "print('pin', sum('soundcard==0.4.6' in open(f).read() for f in ('requirements.txt','build.ps1')))"` → `pin 2`
   **reprova se:** `pin 0` ou `pin 1`.

0.4. [x] (r_zero_inicio=424 no PDI; acervo de 83 arquivos varrido, achado novo: relatório da Fase 0) `+` Ferramenta de medição: juntar `temp/varrer_zero.py` e
`temp/varrer_zero_inicio.py` (escritos nesta sessão; `temp/` não é versionado,
se tiverem sumido reescrever pelo descrito aqui) em `tools/varrer_silencio.py`:
docstring, argumentos `[arquivos ou pasta]` (default `~/Documents/Reco`,
`*reco*.mp3` sem `_alinhado`), `ProcessPoolExecutor`, e uma linha por arquivo
`<nome> dur=<s> r_zero_inicio=<s> r_zero_total=<s> r_maior_seq=<s> mic_maior_seq_zero=<s>`.
Linha nova em `docs/TOOLS.md`. Os números de § Medições já saíram dela.
— **prova:** `python tools/varrer_silencio.py "%USERPROFILE%\Documents\Reco\gravacao_reco_2026-09-29_15-37-18.mp3"` → `r_zero_inicio=424`
   **reprova se:** qualquer outro número (a ferramenta não mede o incidente).

### Fase 1 — núcleo do Auto (`reco.py`)

1.1. [ ] Helper `default_endpoint_id(kind: str, role: int) -> str | None` ao
lado de `default_speaker_id` (l.1332). `kind` = `"speaker"`/`"microphone"`
(fluxo 0/1), `role` 0 = console, 2 = comunicação. Implementação (a do spike):
`with mediafoundation._DeviceEnumerator() as enum:` →
`GetDefaultAudioEndpoint(enum._ptr[0], flow, role, pp)` → `_com.check_error` →
`enum._device_id(pp)` → `_com.release(pp)`. Qualquer exceção: se `role == 2`,
cair no papel 0 com `print("[auto] eCommunications indisponível: …")`; se
`role == 0`, `None`. Guard novo `tools/test_dispositivo_auto.py`: cruza o papel
0 com `sc.default_speaker().id`/`sc.default_microphone().id`, chama o papel 2
nos dois fluxos (e numa thread separada) e mede o tempo de 4 chamadas.
— **prova:** `python tools/test_dispositivo_auto.py` → `OK console==soundcard (speaker, microphone) · comm resolvido · thread ok · 4 chamadas < 50 ms`
   **reprova se:** o cruzamento falha (role errado ou fluxo trocado) ou dá
   exceção de import (API privada mudou: conferir o pin do 0.3).

1.2. [ ] Constantes `AUTO_CONSOLE = "auto:console"` e `AUTO_COMM =
"auto:comm"`, e `resolve_device(value, kind) -> tuple[str | None, str | None,
str]` (id, nome, `via`). **O config é a única fonte da verdade** (o combo só
mostra; nunca é lido para decidir o dispositivo). Regras:
- `"auto:console"`/`None` → papel 0; `"auto:comm"` → papel 2; `via="auto"`.
- id presente na enumeração fresca (`sc.all_speakers()`/`sc.all_microphones()`,
  nunca a lista do último scan) → o próprio id, `via="manual"`.
- id **ausente** (fone desligado) → cai no papel 0, `via="ausente"`; o status
  do 1.5 diz "{X} ausente: usando o padrão do Windows ({Y})". Nunca devolver id
  morto: o `_fail` faria o encoder preencher o canal com zeros, o mesmo silêncio
  sem alarme do incidente.
`pick_device` (l.1341) só tem caller em `_populate_devices` (`tools/` não usa,
conferido): remover junto com o 1.4.
— **prova:** `python tools/test_dispositivo_auto.py` → `OK resolve_device (4 casos)`
   **reprova se:** o caso Auto devolve o id salvo, `None` vira id fixo, ou o
   id ausente volta como id (os 4 casos do guard: console, comm, manual
   presente, manual ausente).

1.3. [ ] Config: `_CFG_DEFAULTS["mic_device"] = AUTO_CONSOLE` e
`["sys_device"] = AUTO_CONSOLE` (comentário atualizado); `CFG_MIGRACAO = 2`;
em `_migra_config` (l.169) bloco `if v < 2:` que põe `AUTO_CONSOLE` nos dois
campos, com docstring da migração 2 (motivo: diag. 1). Risco `dado`: a
migração reescreve o JSON do Gabriel; antes de rodar o app, copiar
`~/.reco_config.json` para `temp/reco_config.antes-migracao-2.json`.
— **prova:** `python -c "import reco;c={'_migracao':1,'sys_device':'{0.0.0.x}','mic_device':'{0.0.1.y}'};print(reco._migra_config(c),c['sys_device'],c['mic_device'],c['_migracao'])"` → `True auto:console auto:console 2`
   **reprova se:** devolve `False` ou mantém os ids (`CFG_MIGRACAO` não subiu
   ou o bloco `v < 2` falta).

1.4. [ ] Combobox (l.3232-3252 e `_populate_devices` l.3589):
- `values` = `[rótulo Auto padrão, rótulo Auto comunicação, *nomes]`, rótulos
  `"Auto: padrão do Windows ({nome})"` e `"Auto: padrão de comunicação ({nome})"`
  via `tf`; nome resolvido entre parênteses.
- Mapa `rótulo → valor de config` guardado no `App` (`self._dev_vals[cfg_key]`).
- **Trocar** o `trace_add("write")` por `cb.bind("<<ComboboxSelected>>", …)`:
  só a escolha do usuário grava config. Escrita programática nunca grava.
- `_populate_devices` seleciona o rótulo do valor salvo; id salvo que sumiu →
  mostra `"{nome salvo ou 'Dispositivo salvo'} (ausente: usando o padrão)"`,
  **sem gravar** (o id fica no JSON até o usuário escolher outro).
- `_scan_thread` (l.3576) passa os 4 ids (2 papéis × 2 fluxos), resolvidos
  fora do Tk.
- Rótulos Auto atualizados no scan e no início de cada gravação (1.5). **Sem
  `postcommand`**: ele rodaria COM no thread do Tk a cada clique no combo.
- O handler novo se chama `_on_device_selected(cfg_key, event)`;
  `_on_device_change` (l.3349) é **removido** (nome velho sumindo é a prova).
— **prova:** `python -c "print('autosave', open('reco.py',encoding='utf-8').read().count('_on_device_change'))"` → `autosave 0`
   **reprova se:** ≥ 1 (o trace de escrita segue gravando a seleção
   programática; hoje dá `autosave 2`).
   Verificação manual complementar (Tk, não automatizável sem janela): abrir
   Opções → 2 Auto no topo dos dois combos, com o nome resolvido; o
   `~/.reco_config.json` não muda ao só abrir o app.

1.5. [ ] `_start_rec` (l.3623) e `_start_nota` (l.3690): trocar
`id_for_name(...)` por `resolve_device(self._cfg["mic_device"], "microphone")`
e `resolve_device(self._cfg["sys_device"], "speaker")`. **Exceção declarada à
regra "COM fora do Tk"**: estas duas chamadas rodam síncronas no clique de
Gravar, porque o id tem de existir antes do `DualRecorder.start`; o limite
medido no guard do 1.1 (4 chamadas < 50 ms) é o que a autoriza. Status de
início: `"Gravando…  mic: {m} · sistema: {s}"` (e o aviso de `via="ausente"`).
Guardar `self._rec_devs = {"mic": (id, nome, via), "sys": (…)}` para a Fase 2.
— **prova:** `python -c "s=open('reco.py',encoding='utf-8').read();print('lista_velha', s.count('id_for_name(self._mic_devs')+s.count('id_for_name(self._sys_devs'))"` → `lista_velha 0`
   **reprova se:** > 0 (algum início ainda decide pelo nome do combo e pela
   lista do último scan).

1.6. [ ] i18n: toda string nova com par em `_TR_EN` (l.~300).
— **prova:** `python tools/check_i18n.py` → `OK — cobertura completa, nada morto.`
   **reprova se:** o script lista `FALTANTES` (string nova sem par EN).

1.7. [ ] Regressão + build: `python tools/test_encoder.py`, depois
`powershell -ExecutionPolicy Bypass -File "C:\Dev\Reco\build.ps1"`.
— **prova:** `python -c "import os;print('exe_novo', os.path.getmtime('dist/Reco/Reco.exe') > os.path.getmtime('reco.py'))"` → `exe_novo True`
   **reprova se:** `exe_novo False` (o build não rodou depois da mudança).

### Fase 2 — vigia durante a gravação

⚠️ **Por que os limiares são esses** (§ Medições): zero exato no sistema é
**comum em gravação boa** — 22/06 teve 19 janelas de 10 s em zero com mic
ativo, 21/07 teve 32, e há trechos de 622 s. Um alarme "10 s de silêncio"
dispararia em quase toda reunião. O que separa o incidente é o **zero desde o
início**: nas gravações boas medidas, o maior foi 73 s; no PDI, 424 s.

2.1. [ ] Contadores de zero exato no `DualRecorder`: em `_rec_sys` (l.1696) e
`_rec_mic` (l.1672), depois do `if self._pause_ev.is_set(): continue`, por
canal: `frames_zero_seq` (soma `len(bloco)` se `not bloco.any()`, senão zera) e
`teve_som` (vira `True` no 1º bloco não-nulo, nunca volta). Antes do ganho (o
ganho só entra no `on_level`; ganho 0 daria falso zero). Contar **blocos**,
nunca relógio de parede (a pausa não conta). Expor `zero_seq_s(canal)` e
`zero_desde_inicio_s(canal)` (o 2º = segundos gravados se `not teve_som`, senão
0). Zerar no `start()`. Lógica num método puro testável sem hardware.
— **prova:** `python tools/test_dispositivo_auto.py` → `OK contadores de zero (5 casos)`
   **reprova se:** um bloco com 1 amostra ≠ 0 não zera a sequência (alarme
   preso), ou bloco pausado conta.

2.2. [ ] Vigia de padrão: thread daemon iniciada no `_start_rec`/`_start_nota`
e parada no `_stop_rec` (l.3775) e no abort, com `threading.Event`; consulta
`default_endpoint_id` dos papéis 0 e 2 nos dois fluxos a cada 2 s e entrega via
`self._post`. Sem COM no thread do Tk aqui.
— **prova:** `python tools/test_dispositivo_auto.py` → `OK vigia para em < 3 s`
   **reprova se:** a thread segue viva 3 s depois do `Event.set()`.

2.3. [ ] Regras de aviso numa função pura `_avisos_dispositivo(estado) ->
list[tuple[str, bool]]` (texto, mostra balão?), chamada pelo `_tick_timer`
(l.3969) a cada 1 s com o estado do recorder + o último resultado da vigia.
Status persistente enquanto durar; balão `_balloon_if_hidden` uma vez por
episódio; some quando a condição acaba.

| regra | condição | texto (PT; par EN no `_TR_EN`) | balão |
| --- | --- | --- | --- |
| A | canal em Auto e o padrão do papel mudou | "O Windows trocou {canal} para {novo}. Esta gravação segue em {atual}: pare e grave de novo para trocar." | sim |
| B forte | sistema **manual**, ≠ padrão console **e** ≠ comunicação, `zero_seq_s ≥ 10` | "Sem som do sistema há {n} s: gravando {atual}, mas o Windows toca em {padrão}." | sim |
| B suave | `zero_desde_inicio_s(sys) ≥ 60` (qualquer modo) | "Nenhum som do sistema desde o início ({atual}). Se o outro lado está falando, confira a saída. Reunião presencial: ignore." | sim |
| C | `zero_seq_s(mic) ≥ 10` | "Microfone mudo há {n} s ({atual})." | sim |

- Modo nota (sem sistema): só C.
- Em Auto, B forte não se aplica (o dispositivo é o padrão por construção; a
  troca no meio é a regra A).

— **prova:** `python tools/test_dispositivo_auto.py` → `OK regras A/B/C (7 casos)`
   **reprova se:** algum dos 7 casos do guard falha. Casos obrigatórios:
   (1) incidente: Realtek manual, QCY padrão, R zero 15 s → B forte;
   (2) Auto, R zero 15 s no meio, já teve som → nada;
   (3) Auto, R zero desde o início 61 s → B suave;
   (4) idem 59 s → nada;
   (5) mic zero 11 s → C;
   (6) padrão trocou em Auto → A;
   (7) manual = padrão de comunicação, R zero 15 s → nada.

2.4. [ ] i18n + build: mesmas provas de 1.6 e 1.7.
— **prova:** `python tools/check_i18n.py` → `OK — cobertura completa, nada morto.`
   **reprova se:** lista `FALTANTES`.
— **prova:** `python -c "import os;print('exe_novo', os.path.getmtime('dist/Reco/Reco.exe') > os.path.getmtime('reco.py'))"` → `exe_novo True`
   **reprova se:** `exe_novo False`.

### Fase 3 — prova real sem o fone, docs e commit

3.1. [ ] Regressão: `python tools/test_encoder.py` e
`python tools/test_gravacao_real.py 15` (este passa a usar
`resolve_device(AUTO_CONSOLE, …)` no lugar de `default_mic_id`/`default_speaker_id`).
— **prova:** `python tools/test_encoder.py` → `TUDO OK`
   **reprova se:** exceção ou exit ≠ 0.
O script ganha a linha `resolvido: mic={'sim' if mic_id else 'não'} sys={'sim' if sys_id else 'não'}`.
— **prova:** `python tools/test_gravacao_real.py 15` → `resolvido: mic=sim sys=sim`
   **reprova se:** algum `não` (o Auto não resolveu) ou `não iniciou`.

3.2. [ ] `+` Prova do caso do bug, automatizada: script
`tools/test_dispositivo_errado.py` que toca 440 Hz por 15 s no
`sc.default_speaker()` (Realtek aqui) e, em paralelo, grava pelo
`DualRecorder` duas vezes: (a) sistema em Auto padrão; (b) sistema fixo no
outro endpoint (monitor LG). Mede o R de cada MP3 com a função de
`tools/varrer_silencio.py`, roda `_avisos_dispositivo` com o estado de (b) e
imprime uma linha-resumo. Apaga os MP3 no fim.
— **prova:** `python tools/test_dispositivo_errado.py` → `RESUMO a_zero_inicio=0 b_zero_inicio>=14 b_regra=B_forte`
   **reprova se:** (a) tem zero desde o início (o Auto não seguiu o padrão) ou
   (b) não tem (o teste não reproduz o bug e não prova nada). Sem segundo
   endpoint na máquina, o script imprime `RESUMO SKIP sem segundo endpoint`,
   nunca a linha de sucesso.

3.3. [ ] Docs:
- `docs/ARMADILHAS.md`: entrada nova "Dispositivo salvo grava o alto-falante
  mudo" (sintoma: PDI de 29/09; causa: autosave + `pick_device`; o que fazer:
  Auto, nunca gravar seleção programática). Mais o pin do `soundcard`.
- `docs/ARQUITETURA.md` § Config: migração 2 e o formato `auto:*`.
- `README.md` (EN l.~98 e PT l.~206): as duas opções Auto e o aviso de silêncio.
- `docs/TOOLS.md`: `test_dispositivo_auto.py`, `test_dispositivo_errado.py`,
  `varrer_silencio.py`.
- `python C:\Dev\cerebro\scripts\gerar_indice_roadmaps.py C:\Dev\Reco\roadmap --escrever`.
— **prova:** `python -c "print('docs', sum('auto:console' in open(f,encoding='utf-8').read() for f in ('docs/ARQUITETURA.md','README.md','docs/ARMADILHAS.md')))"` → `docs 3`
   **reprova se:** `docs 0`, `docs 1` ou `docs 2` (algum doc ficou sem o Auto).

3.4. [ ] Commit por pathspec (`reco.py`, `tools/…`, `docs/…`, `README.md`,
`requirements.txt`, `build.ps1`, `roadmap/…`), push só com autorização (ou
pelo `/executar`, que pusha ao fechar fase verde). Pausar o maestro antes do
commit e religar ao fim. Diário do dia em `C:\Dev\cerebro\pessoal\diario\` e
decisão no hub `C:\Dev\cerebro\projetos\reco.md`.
— **prova:** `git status --short reco.py tools docs README.md requirements.txt build.ps1 | wc -l` → `0`
   **reprova se:** > 0.

### Fase 4 — prova com o fone QCY (precisa do Gabriel)

Ação física: conectar o fone. Roteiro em 1 linha para ele: **"liga o QCY,
deixa ele como padrão no Windows, abre o Reco e grava 30 s de um vídeo do
YouTube falando junto; depois entra numa call de teste do Meet e grava mais
30 s."**

4.1. [ ] Com o QCY conectado e ocioso, e depois em call: rodar
`python tools/test_dispositivo_auto.py --listar` (saída: endpoints + padrão de
cada papel). Registrar em § Medições se o QCY tem 1 ou 2 endpoints e se o
papel 2 diverge do 0 em call. (`--listar` é implementado no passo 1.1.)
— **prova (manual, precisa do fone e de uma call):** a tabela de § Medições
preenchida com as duas listagens.
   **reprova se:** só uma listagem (sem a de call, a decisão do default fica no
   chute).

4.2. [ ] As duas gravações do roteiro, conferidas com
`python tools/varrer_silencio.py <os dois mp3>`.
— **prova (manual, os arquivos só existem depois do roteiro):** as duas linhas
com `r_zero_inicio=0`.
   **reprova se:** qualquer uma com `r_zero_inicio` > 0 longo (o Auto gravou
   o endpoint errado com o fone).

4.3. [ ] Se 4.1 mostrar que em call o som sai no endpoint de comunicação e o
Auto padrão grava mudo: migração 3 para `AUTO_COMM` (decisão já registrada em
§ Decisões; não precisa de nova rodada de arquitetura).

## Medições

| medição | resultado | quando |
| --- | --- | --- |
| R do PDI 29/09 em zero exato | 424 de 424 s | 30/09, esta sessão |
| `role=2` via API privada, mesma thread e outra | funciona, bate com o papel 0 nesta máquina (sem fone) | 30/09, spike |
| endpoints de render aqui | Realtek, LG ULTRAWIDE (sem QCY conectado) | 30/09 |
| R em zero exato, janelas de 10 s com mic ativo (79 arquivos `*reco*`) | comum em gravação boa: 22/06 = 19, 21/07 = 32, 23/07 = 16; maior sequência até 622 s (13/09) | 30/09 |
| R em zero **desde o início**, gravações com som depois (64 de 79 lidos) | máximo 73 s (21/08 14:16); depois 55 s, 42 s; a imensa maioria 0 s | 30/09 |
| gravações com R mudo inteiro (ou quase) | 18/07 (338 s até o 1º som, 2086 s), 31/07 (4725 s), 27/09 20:19 (802 s), 27/09 21:14 (86 s), 27/09 21:56 (168 s), 29/09 PDI (424 s) | 30/09 |
| mic em zero exato, maior sequência | ≤ 4 s em todas, exceto 31/07 (174 s, mesmo arquivo com R mudo) | 30/09 |
| endpoints do QCY ocioso × em call | não medido | 4.1 |

Os 15 arquivos que faltaram na 2ª varredura (a de 13/09 tem 7,7 h e travou a
fila ordenada; interrompida) ficam para o passo 0.4, que roda de novo com a
ferramenta definitiva. As 5 gravações mudas além do PDI podem ser o mesmo
defeito ou reunião presencial: ver § O que o pedido não dizia.

## Priorização (impacto × esforço × risco)

| item | impacto | esforço | risco | veredito |
| --- | --- | --- | --- | --- |
| Fase 0 (tree, pin, limiar) | destrava tudo | baixo | baixo | primeiro |
| 1.3 + 1.4 (migração + fim do autosave) | resolve a causa | baixo | dado (config) | núcleo |
| 1.1-1.2, 1.5 (Auto com papéis) | o pedido literal | médio | API privada (pin) | núcleo |
| Fase 2 (avisos) | pega o que o Auto não cobre | médio | falso alarme (0.4) | logo depois |
| Fase 3 | prova + docs | baixo | nenhum | fecha |
| Fase 4 | decide o default | baixo | depende do Gabriel | em paralelo |

## O que NÃO fazer

- **Não trocar de dispositivo a quente no meio da gravação.** O `Barrier` sincroniza
  o início dos dois streams, o `_al_estimar_inicial` fixa o offset uma vez, e o
  encoder pareia por contagem de amostras; trocar o loopback no meio cria um
  salto no arquivo (o defeito do roadmap de 21/08). Só com medição de que o
  aviso não basta.
- **Não usar dB para o alarme de silêncio.** O piso de um endpoint vivo varia;
  zero exato é a assinatura do endpoint sem pacote (ARMADILHAS l.535).
- **Não alarmar "sistema mudo há 10 s" sozinho.** Medido: zero exato no meio de
  reunião boa é rotina (até 622 s seguidos). Viraria aviso que todo mundo
  aprende a ignorar.
- **Não patchear o `soundcard` instalado** nem vendorizar: o pin + o guard do
  1.1 bastam e o build já coleta o pacote (`reco.spec:22`).
- **Não instalar `pycaw`/`comtypes`** para medidor de pico por endpoint: soma
  dependência para ganho que o zero exato já entrega.
- **Não usar `IMMNotificationClient`** (callback COM via cffi) no lugar do
  polling de 2 s: mais frágil, ganho desprezível.
- **Não preservar o id salvo na migração 2** por heurística ("é igual ao padrão
  de hoje?"): nesta máquina daria certo por acaso, e o critério é falso.

## Riscos e pré-requisitos

- **Tree sujo de outro card** (`reco.py` +132/−6 do modo nota, card
  `6d5bebccb1cd`, nunca commitado desde 21/08; `docs/ARMADILHAS.md` +13 de
  25/09). O decisor deste card chamou isso de "WIP deste card": não é. Sem o
  passo 0.1, `git add reco.py` leva o modo nota no commit errado.
- **API privada do `soundcard`** (`_DeviceEnumerator`, `_ffi`, `_com`):
  mitigado pelo pin (0.3) e pelo guard (1.1); fallback para o papel 0 se falhar.
- **Default do Auto é palpite de confiança média** até a Fase 4 (ação física do
  Gabriel). A Fase 1-3 entrega valor mesmo se o default mudar depois.
- **Migração reescreve o JSON** (`risco: dado`): backup no passo 1.3.
- **Falso alarme da regra B suave** em reunião com o outro lado no mudo: o
  texto é condicional ("se o outro lado está falando") e o limiar vem de medição.
- Sessões concorrentes: só esta sessão mexe em `reco.py` enquanto o card roda;
  conferir `git status` antes de cada fase.

## Crítica do advisor

Modelo consultado: fable (advisor da sessão opus), 2 passadas, a 2ª com o md
já gravado.

- **Provas não-literais** (o `maestro.py validar` compara literal e só roda
  `python`/`git`/…): aplicado; todas as provas viraram `python -c`/`git` com
  saída exata, e as que dependem do fone ficaram declaradas manuais.
- **`ls` do `mediafoundation.py` não reprovava** (o arquivo já existe do build
  anterior): aplicado; a prova do build compara a data do exe com a do fonte.
- **Id salvo ausente tinha três comportamentos em três passos**: aplicado;
  config é a única fonte, id ausente cai no padrão com aviso (1.2, 1.4, 1.5).
- **COM no thread do Tk contradizia o 2.2**: aplicado; `postcommand` saiu, e a
  resolução no clique de Gravar virou exceção declarada com limite medido.
- **Executor em worktree não veria o WIP**: aplicado; Fase 0 no tree principal,
  card com `pequeno: true`, pausar o maestro antes de commitar.
- **Recusado:** nada.

Achado desta sessão depois da 1ª consulta, não do advisor: a varredura do
acervo derrubou o alarme "10 s de silêncio" desenhado na 1ª versão (§ Fase 2).

## Linhagem

> Escrita pelo maestro ao fim de cada rodada (`registrar_linhagem`). É o
> registro de QUEM fez o quê neste roadmap: o arquiteto que o desenhou, os
> executores que o cumpriram, custo e commit de cada passo. Serve à revisão
> do fable — ele lê o desenho E a execução, não só o resultado.

| quando | card | papel | modelo | custo | sinal | commit |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-09-30 21:56 | `c00f415c2ae28` | arquiteto | opus | US$ 8.19 | feito | `1ecf570` |
