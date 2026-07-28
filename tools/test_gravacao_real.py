"""Gravação real de ~15 s pelos dispositivos padrão: mede o tempo do stop() e
confere se a duração declarada bate com o tempo gravado. Apaga o MP3 no fim.

    python tools/test_gravacao_real.py [segundos]
"""
import sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import av
import reco

SECS = float(sys.argv[1]) if len(sys.argv) > 1 else 15.0
OUT = Path(__file__).resolve().parent

mics, spks = reco.list_capture_devices()
mic_id = reco.default_mic_id()
sys_id = reco.default_speaker_id()
print(f"mic = {reco.name_for_id(mics, mic_id)}")
print(f"sys = {reco.name_for_id(spks, sys_id)}")

r = reco.DualRecorder()
r.start(mic_id, sys_id, on_error=lambda k, m: print(f"  [erro {k}] {m}"),
        out_sr=reco.OUT_SR, out_channels=reco.OUT_CH, bitrate=reco.MP3_BR,
        out_dir=OUT)
if not r.recording:
    print("não iniciou"); sys.exit(1)

t_start = time.perf_counter()
print(f"gravando {SECS:.0f}s…")
time.sleep(SECS)
t_rec = time.perf_counter() - t_start

t0 = time.perf_counter()
path = r.stop()
t_stop = time.perf_counter() - t0

with av.open(str(path)) as c:
    declared = c.duration / av.time_base
    ch = c.streams.audio[0].channels
size = path.stat().st_size
print(f"\narquivo    : {path.name}  ({size/1024:.0f} KB, {ch} canais)")
print(f"gravado    : {t_rec:.2f}s")
print(f"declarado  : {declared:.2f}s   (erro {declared - t_rec:+.2f}s)")
print(f"stop()     : {t_stop*1000:.0f} ms")
print(f"bitrate    : {size*8/declared/1000:.0f} kbps")
ok = abs(declared - t_rec) < 0.5 and t_stop < 0.5
print("\n" + ("OK" if ok else "FALHOU"))
path.unlink(missing_ok=True)
sys.exit(0 if ok else 1)
