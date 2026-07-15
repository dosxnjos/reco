# Consolidado — 2026-07-15 · Ganho por canal (mic / sistema)

## O que mudou
Adicionado controle de **ganho por canal** no Reco: um handle vertical arrastável
**sobre** cada VU meter (mic e sistema), para aumentar/reduzir o volume que cada
canal grava — resolvendo o mic gravar bem mais baixo que a saída de som.

- Slider em eixo **multiplicador bi-linear** (revisado a pedido do Gabriel; antes
  era dB): unity 1,0× no centro, metade esquerda 0×..1× (atenua/muta), metade
  direita 1×..10× (amplifica). Arrasto snapa em 0,5. O multiplicador atual
  aparece embaixo de cada barra (`fmt_gain`, ex. "1,0x"); sem rótulo em dB.
- Ganho é **baked no arquivo salvo** (`_save`, após resample, antes do clip), então
  AEC/diarização/transcrição veem o áudio já ganhado. Aplica-se uniformemente ao
  arquivo inteiro mesmo se ajustado durante a gravação.
- O **VU meter reflete o nível já ganhado** (RMS escalado no callback), feedback
  em tempo real. Label da coluna mostra o offset em dB ao vivo (some no unity).
- Persistido em `~/.reco_config.json` (`mic_gain`, `sys_gain`, default `1.0`).

## Arquivos tocados
- `reco.py`
  - `_CFG_DEFAULTS`: `mic_gain`/`sys_gain`.
  - `DualRecorder`: `self.mic_gain/sys_gain`, `set_gain()`, escala no callback de
    nível (`_rec_mic`/`_rec_sys`), multiplicação em `_save`.
  - Helpers `_gain_db`/`gain_to_frac`/`frac_to_gain` + constantes `GAIN_DB/MIN/MAX`.
  - `VuMeter`: canvas alto (H=20), trilha + barra de nível + tick de unity +
    **handle arrastável** (`on_gain`, `set_gain`, `gain`, `_drag`).
  - `App._build_meters`: refs de label, callback, ganho inicial do config;
    `App._gain_label`, `App._on_gain`; init do ganho do recorder na criação.
- `README.md`: item de "Barras de nível" (PT/EN) descrevendo o ganho.
- `roadmap/2026-07-15-ganho-por-canal.md`: plano.

## Verificação
- `ast.parse` OK; `import reco` OK; defaults `1.0/1.0`; `VuMeter.H=20`.
- Helpers dB: unity→frac 0.5, extremos 0.126×/7.943×, snap em ±1 dB, round-trip OK.
- `VuMeter` em Tk efêmero: `set_gain`, drag (dir→máx, esq→mín, centro→unity),
  callback `on_gain` dispara, `update_level` desenha — tudo OK.

## Pendências / não feito
- Não rodei a GUI completa headful (bloqueia); validei o widget isolado, que é
  onde estava o risco de runtime.
- Rebuild do executável (`build.ps1`) fica a critério do Gabriel quando quiser
  distribuir a versão nova.
