# Ganho por canal (mic / sistema) com slider sobre o VU meter — 2026-07-15

## Pedido
No Reco, o microfone grava bem mais baixo que a saída de som (áudio do sistema).
Quero um controle prático de ganho por canal: uma "barra vertical" (handle
arrastável) **sobre** cada VU meter, para aumentar/diminuir o volume que será
gravado de cada um dos dois canais (mic e sistema), independentemente.

## Arquitetura atual (o que existe)
- `DualRecorder._rec_mic` / `_rec_sys`: capturam float32, empilham em
  `_mic_chunks`/`_sys_chunks` e reportam RMS via `on_level(src, rms)`.
- `DualRecorder._save`: concatena, resample p/ 16 kHz e escreve MP3 estéreo
  (L=mic, R=sistema) com `clip([-1,1])`. Nenhum ganho é aplicado.
- `VuMeter` (tk.Canvas, H=4): barra horizontal que enche com o nível; sem interação.
- `_build_meters`: duas colunas (MIC / SISTEMA), cada uma com label + VuMeter.
- Config em `~/.reco_config.json` via `load_config`/`save_config`.

## Decisões
1. **Ganho = multiplicador linear por canal**, persistido em config
   (`mic_gain`, `sys_gain`, default `1.0`).
2. **Mapeamento dB simétrico** no slider: ±18 dB em torno de 0 dB (unity no
   centro). `gain = 10^(dB/20)` → range ~0,126×..7,94×. Snap p/ unity dentro de
   ±1 dB. dB é o eixo perceptualmente uniforme; unity no centro é intuitivo.
3. **Aplicação do ganho baked no arquivo salvo** (`_save`, após resample, antes
   do clip). Assim tudo rio abaixo (AEC, diarização, transcrição) vê o áudio já
   ganhado — consistente. Mudar o ganho durante a gravação aplica de forma
   uniforme ao arquivo inteiro (comportamento previsível).
4. **VU meter reflete o nível já ganhado**: o callback multiplica o RMS pelo
   ganho do canal, então a barra mostra o efeito em tempo real.
5. **UI**: VuMeter vira canvas mais alto (H=20) para o handle ser agarrável.
   Contém: trilha (escala), barra de nível fina centralizada, tick de unity no
   centro e um **handle vertical arrastável** (a "barra vertical" pedida) na
   posição do ganho. Label da coluna mostra o offset em dB ao vivo.

## Passos
1. Config: `mic_gain`/`sys_gain` nos defaults.
2. Helpers de mapeamento dB↔ganho↔fração + constantes (`GAIN_DB/MIN/MAX`).
3. `DualRecorder`: atributos de ganho, `set_gain`, escala no callback de nível,
   multiplicação em `_save`.
4. `VuMeter`: canvas alto, handle arrastável, `set_gain`/`gain`, callback `on_gain`.
5. `_build_meters`: instanciar com gain inicial do config + callbacks; refs de label.
6. `_on_gain(src, g)`: atualiza recorder ao vivo, salva config, atualiza label dB.
7. Inicializar `self._recorder.set_gain(...)` a partir do config na criação.
8. Traduções (label dB é numérico; sem novas strings PT/EN obrigatórias).
9. Testar: `python -c "import reco"` (sanidade) + rodar app se possível.

## Onde propagar (rio abaixo)
- README (seção de gravação/recursos) — mencionar ganho por canal.
- Sem mudança de schema de arquivo (continua MP3 estéreo 16 kHz).
- Consolidado datado ao fim.
