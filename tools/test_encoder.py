"""Testes do encoder streaming — duração, sincronia L/R e pareamento dos canais.

Roda sem hardware: exercita MP3Writer e DualRecorder._pump diretamente.
    python tools/test_encoder.py
"""
import sys, time, math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
import av
import reco

OUT = Path(__file__).resolve().parent
CAP = reco.CAPTURE_SR
fails = []


def check(label, ok, detail=""):
    print(f"  {'OK ' if ok else 'FALHOU'}  {label}{'  — ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


def tone(freq, n, sr=CAP, start=0):
    tt = (np.arange(n) + start) / sr
    return (0.3 * np.sin(2 * math.pi * freq * tt)).astype(np.float32)


def band_peak(x, sr=reco.OUT_SR):
    S = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    return float(np.fft.rfftfreq(len(x), 1 / sr)[S.argmax()])


def read_mp3(path):
    """(duração declarada pelo header, canais decodificados)."""
    with av.open(str(path)) as c:
        declared = c.duration / av.time_base
        rs = av.audio.resampler.AudioResampler(format="fltp", layout="stereo",
                                               rate=reco.OUT_SR)
        buf = [r.to_ndarray() for f in c.decode(audio=0) for r in rs.resample(f)]
        buf += [r.to_ndarray() for r in rs.resample(None)]
    arr = np.concatenate(buf, axis=1)
    return declared, arr


print("\n[1] MP3Writer: duração, header Xing e separação de canais")
SECS, BLK = 60, 1024
p = OUT / "t_writer.mp3"
w = reco.MP3Writer(p, CAP, reco.OUT_SR, reco.OUT_CH, reco.MP3_BR)
pos = 0
t0 = time.perf_counter()
while pos < SECS * CAP:
    n = min(BLK, SECS * CAP - pos)
    w.feed(tone(440, n, start=pos), tone(1500, n, start=pos))   # L=440 Hz, R=1500 Hz
    pos += n
t_feed = time.perf_counter() - t0
t0 = time.perf_counter()
w.close()
t_close = time.perf_counter() - t0

head = p.read_bytes()[:4096]
declared, arr = read_mp3(p)
real = arr.shape[1] / reco.OUT_SR
check("header Xing presente", head.find(b"Xing") > 0 or head.find(b"Info") > 0)
check("duração declarada == real", abs(declared - SECS) < 0.1,
      f"declarada {declared:.2f}s, esperada {SECS}s, decodificada {real:.2f}s")
check("L é o mic (440 Hz)", abs(band_peak(arr[0][:16384]) - 440) < 15,
      f"pico em {band_peak(arr[0][:16384]):.0f} Hz")
check("R é o sistema (1500 Hz)", abs(band_peak(arr[1][:16384]) - 1500) < 15,
      f"pico em {band_peak(arr[1][:16384]):.0f} Hz")
check("close() é instantâneo", t_close < 0.5, f"{t_close*1000:.0f} ms")
print(f"       encode ao vivo de {SECS}s levou {t_feed:.2f}s de CPU "
      f"({t_feed/SECS*100:.1f}% de um núcleo); arquivo {p.stat().st_size/1024:.0f} KB")

print("\n[2] Sincronia: canais chegando desalinhados (o encoder só pareia o comum)")
r = reco.DualRecorder()
r._writer = reco.MP3Writer(OUT / "t_sync.mp3", CAP, reco.OUT_SR, reco.OUT_CH, reco.MP3_BR)
r._mic_live = r._sys_live = True
r._mic_chunks[:] = [np.ones(3000, np.float32) * 0.5]      # mic 3000 à frente
r._sys_chunks[:] = [np.ones(1000, np.float32) * 0.5]
r._pump()
check("só o trecho comum é encodado", r._writer.samples == 1000,
      f"{r._writer.samples} amostras")
check("sobra do mic fica em buffer", len(r._buf_mic) == 2000 and len(r._buf_sys) == 0,
      f"mic {len(r._buf_mic)}, sys {len(r._buf_sys)}")
r._sys_chunks[:] = [np.ones(2000, np.float32) * 0.5]      # sistema alcança
r._pump()
check("o par alcançado é encodado", r._writer.samples == 3000,
      f"{r._writer.samples} amostras")
r._writer.discard()

print("\n[3] Canal morto vira silêncio (não trava o outro)")
r = reco.DualRecorder()
r._writer = reco.MP3Writer(OUT / "t_dead.mp3", CAP, reco.OUT_SR, reco.OUT_CH, reco.MP3_BR)
r._mic_live, r._sys_live = False, True                    # mic nunca abriu
r._sys_chunks[:] = [np.ones(5000, np.float32) * 0.5]
r._pump()
check("sistema flui sem o mic", r._writer.samples == 5000, f"{r._writer.samples} amostras")
r._writer.discard()

print("\n[4] Pump final: rabo de um canal é preenchido com silêncio")
r = reco.DualRecorder()
r._writer = reco.MP3Writer(OUT / "t_final.mp3", CAP, reco.OUT_SR, reco.OUT_CH, reco.MP3_BR)
r._mic_live = r._sys_live = True
r._mic_chunks[:] = [np.ones(4000, np.float32) * 0.5]
r._sys_chunks[:] = [np.ones(1000, np.float32) * 0.5]
r._pump(final=True)
check("nada é descartado no fim", r._writer.samples == 4000, f"{r._writer.samples} amostras")
r._writer.discard()

for f in ("t_writer.mp3",):
    (OUT / f).unlink(missing_ok=True)
print(f"\n{'TUDO OK' if not fails else 'FALHAS: ' + ', '.join(fails)}\n")
sys.exit(1 if fails else 0)
