"""Testa o alinhamento dos canais na gravacao (Fase 1 do roadmap 2026-08-19).

Sem hardware e deterministico: injeta sinais com atraso CONHECIDO e confere que
o offset estimado e aplicado batem. Rodar sempre que mexer em `estimar_offset`,
`_al_*` ou `_pump`.

    python tools/test_alinhamento.py

Cobre:
  1. estimar_offset com atraso positivo, negativo e zero;
  2. canais sem relacao (fone / caixa muda) -> qualidade baixa, NAO alinha;
  3. canal mudo -> (0, 0);
  4. _pump retendo o audio ate estimar, e o par saindo alinhado;
  5. correcao de deriva com sinal nos dois sentidos;
  6. gravacao de canal unico -> estado "off" (nada a alinhar).
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reco import (ALIGN_COLETA_S, ALIGN_MIN_AJUSTE, ALIGN_RECHECK_S,  # noqa: E402
                  CAPTURE_SR, DualRecorder, estimar_offset)

falhas = []


def ok(cond, msg):
    print(("  OK   " if cond else "  FALHOU ") + msg)
    if not cond:
        falhas.append(msg)


def fala_sintetica(n, seed=0):
    """Ruido filtrado com envelope de silabas — parecido o bastante com voz para
    a correlacao cruzada se comportar como no audio real."""
    rng = np.random.default_rng(seed)
    x = rng.normal(0, 1, n).astype(np.float64)
    k = np.ones(40) / 40.0                      # passa-baixa tosco
    x = np.convolve(x, k, mode="same")
    t = np.arange(n) / CAPTURE_SR
    env = (np.sin(2 * np.pi * 3.0 * t) > -0.3).astype(np.float64)
    env = np.convolve(env, np.ones(2000) / 2000.0, mode="same")
    return (x * env).astype(np.float32)


def par_com_atraso(dur_s, atraso, ganho_eco=0.5, seed=1):
    """(mic, sistema) onde o mic contem o eco do sistema atrasado por `atraso`.

    `atraso` > 0 = o eco aparece no mic DEPOIS (caso normal).
    """
    n = int(dur_s * CAPTURE_SR)
    folga = abs(atraso) + 1
    sistema = fala_sintetica(n + folga, seed)
    voz = fala_sintetica(n + folga, seed + 100) * 0.3
    eco = np.roll(sistema, atraso)
    if atraso > 0:
        eco[:atraso] = 0
    elif atraso < 0:
        eco[atraso:] = 0
    mic = (voz + ganho_eco * eco).astype(np.float32)
    return mic[:n], sistema[:n].astype(np.float32)


class WriterFake:
    """Só guarda os pares que o `_pump` entregaria ao MP3Writer."""

    def __init__(self):
        self.mic = np.zeros(0, np.float32)
        self.sys = np.zeros(0, np.float32)

    def feed(self, mic, sistema, gm=1.0, gs=1.0):
        self.mic = np.concatenate([self.mic, mic])
        self.sys = np.concatenate([self.sys, sistema])


def recorder_falso(mic, sistema):
    r = DualRecorder()
    r._writer = WriterFake()
    r._mic_live = r._sys_live = True
    r._al_estado = "coletando"
    r._buf_mic = np.asarray(mic, np.float32).copy()
    r._buf_sys = np.asarray(sistema, np.float32).copy()
    return r


print(__doc__.splitlines()[0])
print("\n1) estimar_offset com atraso conhecido")
for atraso in (0, 480, 3200, 9744, -4800, -9744):
    mic, sistema = par_com_atraso(12.0, atraso)
    d, q = estimar_offset(mic, sistema)
    erro = abs(d - atraso)
    ok(erro <= 3 and q >= 0.15,
       f"atraso {atraso:+6d} -> estimado {d:+6d} (erro {erro} amostras, q={q:.3f})")

print("\n2) canais sem relacao (fone, ou caixa muda): nao deve alinhar")
mic = fala_sintetica(12 * CAPTURE_SR, 7)
sistema = fala_sintetica(12 * CAPTURE_SR, 8)
d, q = estimar_offset(mic, sistema)
ok(q < 0.15, f"qualidade baixa como esperado (q={q:.3f}, d={d:+d})")

print("\n3) canal mudo")
d, q = estimar_offset(np.zeros(12 * CAPTURE_SR, np.float32),
                      fala_sintetica(12 * CAPTURE_SR, 9))
ok((d, q) == (0, 0.0), f"devolveu ({d}, {q})")

print("\n4) _pump retem o audio ate estimar, e entrega o par alinhado")
ATRASO = 9744                                   # 203 ms @48k, o caso real medido
mic, sistema = par_com_atraso(ALIGN_COLETA_S + 5.0, ATRASO)
r = recorder_falso(mic[:int(3 * CAPTURE_SR)], sistema[:int(3 * CAPTURE_SR)])
r._pump()
ok(r._writer.mic.size == 0 and r._al_estado == "coletando",
   "com 3 s ainda nao escreveu nada (retido para estimar)")

r = recorder_falso(mic, sistema)
r._pump()
info = r.alinhamento()
ok(info["estado"] == "ok", f"estado apos coleta: {info['estado']}")
ok(abs(info["offset_amostras"] - ATRASO) <= 3,
   f"offset aplicado {info['offset_amostras']:+d} (esperado {ATRASO:+d})")
ok(r._writer.mic.size > 0, f"escreveu {r._writer.mic.size / CAPTURE_SR:.1f} s")
d_res, q_res = estimar_offset(r._writer.mic, r._writer.sys)
ok(abs(d_res) <= 160,
   f"par escrito ficou alinhado: atraso residual {d_res:+d} amostras "
   f"({d_res / CAPTURE_SR * 1000:+.1f} ms, gate: |d| < 160)")

print("\n5) mesma coisa com o loopback atrasado (sinal negativo — caso de 18/08)")
mic, sistema = par_com_atraso(ALIGN_COLETA_S + 5.0, -14400, seed=3)
r = recorder_falso(mic, sistema)
r._pump()
info = r.alinhamento()
d_res, _ = estimar_offset(r._writer.mic, r._writer.sys)
ok(info["estado"] == "ok" and abs(info["offset_amostras"] + 14400) <= 3,
   f"offset negativo aplicado: {info['offset_amostras']:+d}")
ok(abs(d_res) <= 160, f"par escrito alinhado (residual {d_res:+d})")

print("\n6) correcao de deriva")
mic, sistema = par_com_atraso(ALIGN_COLETA_S + 5.0, 0, seed=4)
r = recorder_falso(mic, sistema)
r._pump()
antes = len(r._buf_mic)
# Janela de reestimativa com 6 ms de deriva (o mic atrasou), e o contador cheio.
jm, js = par_com_atraso(10.0, 288, seed=5)
from scipy.signal import resample_poly                                # noqa: E402
r._al_jan_m = resample_poly(jm, 1, CAPTURE_SR // 16000).astype(np.float32)
r._al_jan_s = resample_poly(js, 1, CAPTURE_SR // 16000).astype(np.float32)
r._buf_mic = np.concatenate([r._buf_mic, np.zeros(CAPTURE_SR, np.float32)])
r._al_desde = int(ALIGN_RECHECK_S * CAPTURE_SR) + 1
r._al_corrigir_deriva()
info = r.alinhamento()
ok(info["ajustes_deriva"] == 1 and abs(info["deriva_amostras"] - 288) <= 48,
   f"deriva corrigida: {info['deriva_amostras']:+d} amostras "
   f"em {info['ajustes_deriva']} ajuste(s)")
ok(abs(len(r._buf_mic) - (antes + CAPTURE_SR - 288)) <= 48,
   "o ajuste saiu do buffer do mic, como esperado")

r._al_desde = ALIGN_MIN_AJUSTE            # abaixo do limite: nao reestima
ajustes = r.alinhamento()["ajustes_deriva"]
r._al_corrigir_deriva()
ok(r.alinhamento()["ajustes_deriva"] == ajustes,
   "nao reestima antes de ALIGN_RECHECK_S")

print("")
print("8) gravacao longa simulada: jitter de atraso corrigido na reestimativa")
# Sem hardware e sem tocar som: alimenta o _pump em blocos de 200 ms com o atraso
# MUDANDO no meio (o jitter de ~24 ms medido em audio real) e confere que o que foi
# "gravado" volta a ficar alinhado. ALIGN_RECHECK_S e reduzido no modulo para o
# teste caber em 60 s de audio em vez de 5 minutos.
import reco as _reco
_RECHECK_ORIG = _reco.ALIGN_RECHECK_S
_reco.ALIGN_RECHECK_S = 20.0
try:
    D1, D2, TROCA_S, TOTAL_S = 9744, 10800, 30.0, 60.0     # +203 ms -> +225 ms
    _a, _sistema = par_com_atraso(TOTAL_S, D1, seed=21)
    _b, _ = par_com_atraso(TOTAL_S, D2, seed=21)
    _corte = int(TROCA_S * CAPTURE_SR)
    _mic = np.concatenate([_a[:_corte], _b[_corte:]])      # o atraso salta no meio
    r = DualRecorder()
    r._writer = WriterFake()
    r._mic_live = r._sys_live = True
    r._al_estado = "coletando"
    _passo = int(0.2 * CAPTURE_SR)
    for _i in range(0, len(_mic), _passo):
        with r._lk_mic:
            r._mic_chunks.append(_mic[_i:_i + _passo].copy())
        with r._lk_sys:
            r._sys_chunks.append(_sistema[_i:_i + _passo].copy())
        r._pump()
    r._pump(final=True)
    info = r.alinhamento()
    ok(info["estado"] == "ok" and info["ajustes_deriva"] >= 1,
       f"reestimou durante a gravacao: {info['ajustes_deriva']} ajuste(s), "
       f"{info['deriva_amostras']:+d} amostras")
    from scipy.signal import resample_poly as _rp
    _m16 = _rp(r._writer.mic, 1, CAPTURE_SR // 16000).astype(np.float32)
    _s16 = _rp(r._writer.sys, 1, CAPTURE_SR // 16000).astype(np.float32)
    _res, _jan = [], 10 * 16000
    for _i in range(0, min(len(_m16), len(_s16)) - _jan, _jan):
        _d, _q = estimar_offset(_m16[_i:_i + _jan], _s16[_i:_i + _jan], sr=16000)
        if _q >= 0.15:
            _res.append((_i / 16000.0, _d))
    print("       residual por janela: " +
          ", ".join(f"{_t:.0f}s={_d:+d}" for _t, _d in _res))
    _depois = [_d for _t, _d in _res if _t >= TROCA_S + 25]
    ok(bool(_depois) and max(abs(_d) for _d in _depois) < 160,
       f"depois da correcao o residual fica < 160 amostras @16k "
       f"(pior: {max((abs(_d) for _d in _depois), default=-1)})")
finally:
    _reco.ALIGN_RECHECK_S = _RECHECK_ORIG

print("\n7) canal unico -> nada a alinhar")
r = DualRecorder()
r._writer = WriterFake()
r._mic_live, r._sys_live = True, False
r._al_estado = "off"
r._buf_mic = fala_sintetica(CAPTURE_SR, 11)
r._buf_sys = np.zeros(0, np.float32)
r._pump(final=True)
ok(r._writer.mic.size > 0 and r.alinhamento()["estado"] == "off",
   "gravou com um canal só, sem tentar alinhar")

print(f"\n{'TODOS OS TESTES PASSARAM' if not falhas else f'{len(falhas)} FALHA(S)'}")
for f in falhas:
    print(f"  - {f}")
sys.exit(1 if falhas else 0)
