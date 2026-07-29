"""Mede o acoplamento acustico real (caixa -> mic) e o ERLE do cancel_echo atual.

ERLE = Echo Return Loss Enhancement: quanto de energia do eco foi removida, em dB.
Medido nos trechos em que SO o sistema fala (R com energia, sem fala do near-end),
que e onde o residuo e audivel e onde a diarizacao erra.
"""
import sys
from pathlib import Path
import numpy as np
import av

SR = 16000


def decode(path):
    with av.open(str(path)) as cont:
        st = cont.streams.audio[0]
        rs = av.audio.resampler.AudioResampler(format="fltp", layout="stereo", rate=SR)
        buf = []
        for frame in cont.decode(audio=0):
            for r in rs.resample(frame):
                buf.append(r.to_ndarray())
        for r in rs.resample(None) or []:
            buf.append(r.to_ndarray())
    a = np.concatenate(buf, axis=1).astype(np.float32)
    return a[0], a[1]


def db(x):
    return 20 * np.log10(max(x, 1e-12))


def rms(x):
    return float(np.sqrt(np.mean(x ** 2))) if x.size else 0.0


def main():
    mp3 = Path(sys.argv[1])
    mic, sysc = decode(mp3)
    n = min(len(mic), len(sysc))
    mic, sysc = mic[:n], sysc[:n]
    print(f"[{mp3.name}] {n/SR:.0f}s")
    print(f"  RMS mic={db(rms(mic)):.1f} dBFS   sistema={db(rms(sysc)):.1f} dBFS")

    # Blocos de 100 ms rotulados por quem esta falando.
    B = int(0.1 * SR)
    nb = n // B
    m = np.array([rms(mic[i*B:(i+1)*B]) for i in range(nb)])
    s = np.array([rms(sysc[i*B:(i+1)*B]) for i in range(nb)])
    lim_m, lim_s = 0.0035, 0.0035

    so_sys = (s >= lim_s) & (m < lim_m * 3)   # PC fala, voce (quase) calado
    so_mic = (m >= lim_m) & (s < lim_s)       # so voce fala
    ambos = (m >= lim_m) & (s >= lim_s)
    print(f"  blocos: so_sistema={so_sys.sum()} so_mic={so_mic.sum()} "
          f"ambos={ambos.sum()} silencio={nb - so_sys.sum() - so_mic.sum() - ambos.sum()}")

    if so_sys.sum() < 5:
        print("  ! poucos trechos de 'so o PC falando' — medida inconclusiva")
        return

    # Acoplamento: energia que aparece no mic enquanto SO o sistema fala.
    vaz = float(np.mean(m[so_sys]))
    ref = float(np.mean(s[so_sys]))
    print(f"\n  ACOPLAMENTO (caixa -> mic): {db(vaz) - db(ref):+.1f} dB")
    print(f"    (0 dB = mic capta o PC tao alto quanto o proprio PC;"
          f" abaixo de -35 dB e desprezivel)")

    # ERLE do cancel_echo atual, por janela de 30 s (como o app faz).
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from reco import cancel_echo
    step = 30 * SR
    erles = []
    for i in range(0, n - step, step):
        w_m, w_s = mic[i:i+step], sysc[i:i+step]
        bi = slice(i // B, (i + step) // B)
        if so_sys[bi].sum() < 5:
            continue
        limpo = cancel_echo(w_m, w_s)
        k = min(len(limpo), len(w_m))
        idx = np.where(so_sys[bi])[0]
        antes = np.mean([rms(w_m[j*B:(j+1)*B]) for j in idx])
        dep = np.mean([rms(limpo[j*B:(j+1)*B]) for j in idx if (j+1)*B <= k])
        erles.append(db(antes) - db(dep))
    if erles:
        print(f"\n  ERLE do cancel_echo atual: mediana {np.median(erles):+.1f} dB "
              f"(min {min(erles):+.1f}, max {max(erles):+.1f}, n={len(erles)} janelas)")
        print("    (referencia: AEC bom entrega 20-40 dB; abaixo de 10 dB o eco"
              " continua audivel e a diarizacao continua errando)")


if __name__ == "__main__":
    main()
