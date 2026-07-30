"""Alimenta o LiveTranscriber com um MP3 real em tempo real SIMULADO — mede
latencia real entre o FIM do trecho transcrito (via on_group, nao o avanco do
laco de alimentacao) e o texto sair, e o tempo ate o PRIMEIRO texto aparecer.

⚠️ Ate 29/07/2026 este script usava `t_audio_atual` (a posicao mais recente
alimentada) como proxy do fim do trecho — mede o overhead do proprio laco de
alimentacao, nao a latencia real (achado numa revisao/consulta ao advisor).
Corrigido pra usar `on_group`, que devolve o fim absoluto (em amostras) do
grupo que acabou de ser transcrito.

O gravador de verdade entrega os pares a CAPTURE_SR (48000); os MP3s ja
gravados sao 16000. Para simular sem gravar de novo, reamostra 16k -> 48k
(resample_poly 3/1) antes de alimentar o LiveTranscriber, que reamostra de
volta 48k -> 16k por dentro — round-trip funcional, nao um teste de qualidade
de audio.

    python tools/test_live.py <mp3> [segundos]
"""
import sys, time, threading
from pathlib import Path
import numpy as np
from scipy.signal import resample_poly

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reco import decode_16k, OVTranscriber, LiveTranscriber, load_config

TICK = 0.2   # mesmo ENC_TICK do DualRecorder


def main():
    mp3 = Path(sys.argv[1])
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 90.0
    cfg = load_config()

    chans = decode_16k(mp3, split=True)
    mic16, sys16 = chans[0], chans[1]
    n = min(len(mic16), len(sys16), int(secs * 16000))
    mic16, sys16 = mic16[:n], sys16[:n]
    print(f"[audio] {mp3.name} -> {n/16000:.0f}s simulados\n", flush=True)

    tr = OVTranscriber()
    tr.set_model(cfg.get("model"))
    tr.set_device("GPU")
    live = LiveTranscriber(tr, lang="pt")

    lock = threading.Lock()
    fim_pendente = [None]     # setado por on_group, lido por on_text (mesma call, em ordem)
    eventos = []              # (fim_abs_s, t_wall_chegada)
    t0 = time.perf_counter()

    def on_group(canal, fim_abs_amostras):
        fim_pendente[0] = fim_abs_amostras / 16000.0

    def on_text(spk, texto):
        with lock:
            fim_s = fim_pendente[0]
            eventos.append((fim_s, time.perf_counter()))
        print(f"  [{time.perf_counter()-t0:.1f}s wall, fim do trecho={fim_s:.1f}s] "
              f"{spk}: {texto[:70]}", flush=True)

    def on_warn(msg):
        print(f"  [warn] {msg}", flush=True)

    live.start(on_text=on_text, on_warn=on_warn, on_group=on_group)

    step16 = int(TICK * 16000)
    for i in range(0, n, step16):
        m16 = mic16[i:i + step16]
        s16 = sys16[i:i + step16]
        m48 = resample_poly(m16, 3, 1).astype(np.float32)
        s48 = resample_poly(s16, 3, 1).astype(np.float32)
        live.feed_pair(m48, s48)
        time.sleep(TICK)   # ritmo real

    print("\n[fim do audio simulado] esperando o rascunho drenar...", flush=True)
    live.stop(wait=True, timeout=30.0)

    if not eventos:
        print("\nNENHUM texto produzido — FALHOU")
        return 1
    primeiro_wall = eventos[0][1] - t0
    lat = sorted(wall - t0 - fim_s for fim_s, wall in eventos)
    mediana = lat[len(lat)//2]
    print(f"\n[tempo até o 1º texto] {primeiro_wall:.1f}s (limitado pelo tamanho do "
          f"1º segmento de fala do VAD — pode chegar a ~28s no pior caso, max_s)")
    print(f"[latência fim-do-trecho -> texto] mediana={mediana:.1f}s | "
          f"min={lat[0]:.1f}s | max={lat[-1]:.1f}s | n={len(lat)} trechos")
    ok = mediana <= 5.0
    print(("PASSOU" if ok else "FALHOU") + ": critério = latência mediana <= 5s")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
