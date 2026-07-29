"""Calibra k_db de dominancia_sistema por dado, nao por chute
(C:\\Dev\\CLAUDE.md secao Decidir por evidencia).

Reusa a rotulagem por blocos de 0,1s de medir_eco.py: so_sys (so o sistema
fala — bleeding de eco pro mic, GROUND TRUTH de eco), so_mic (so o mic fala —
GROUND TRUTH de fala real, nao pode ser descartada).

Para cada k_db candidato, mede:
  - recall em so_sys: fracao dos blocos de eco de fato marcados como dominancia
    (quanto maior, melhor — e o que resolve D3)
  - falso-positivo em so_mic: fracao de fala REAL marcada como dominancia
    (tem que ficar ~0 — Riscos do roadmap: "na duvida, MANTER o segmento";
    transcrever eco e menos grave que apagar fala real)

Escolhe o menor k_db (mais sensivel, maior recall) que ainda mantem o
falso-positivo em so_mic abaixo de FP_MAX.
"""
import sys
from pathlib import Path
import numpy as np
import av

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reco import dominancia_sistema

SR = 16000
FP_MAX = 0.02   # falso-positivo tolerado em fala real: <= 2% dos blocos


def decode(path):
    with av.open(str(path)) as cont:
        rs = av.audio.resampler.AudioResampler(format="fltp", layout="stereo", rate=SR)
        buf = []
        for frame in cont.decode(audio=0):
            for r in rs.resample(frame):
                buf.append(r.to_ndarray())
        for r in rs.resample(None) or []:
            buf.append(r.to_ndarray())
    a = np.concatenate(buf, axis=1).astype(np.float32)
    return a[0], a[1]


def rms(x):
    return float(np.sqrt(np.mean(x ** 2))) if x.size else 0.0


def main():
    arquivos = [Path(p) for p in sys.argv[1:]]
    if not arquivos:
        print("uso: python tools/calibrar_dominancia.py <mp3> [mp3...]")
        return 1

    B = int(0.1 * SR)
    lim = 0.0035
    resultados = {}   # k_db -> [recall_por_arquivo], [fp_por_arquivo]

    for mp3 in arquivos:
        mic, sysc = decode(mp3)
        n = min(len(mic), len(sysc))
        mic, sysc = mic[:n], sysc[:n]
        nb = n // B
        m = np.array([rms(mic[i*B:(i+1)*B]) for i in range(nb)])
        s = np.array([rms(sysc[i*B:(i+1)*B]) for i in range(nb)])
        so_sys = (s >= lim) & (m < lim * 3)
        so_mic = (m >= lim) & (s < lim)
        print(f"[{mp3.name}] {n/SR:.0f}s — so_sistema={so_sys.sum()} so_mic={so_mic.sum()}")
        if so_sys.sum() < 5:
            print("  ! poucos blocos 'so sistema' — pulando arquivo pra calibracao")
            continue

        for k_db in (3, 4, 5, 6, 7, 8, 9, 10, 12, 15):
            mask = dominancia_sistema(mic, sysc, sr=SR, bloco_s=0.1, k_db=k_db, histerese=3)
            # mask por amostra -> por bloco (mesma grade de B usada acima)
            mask_b = mask[:nb*B].reshape(nb, B).mean(axis=1) > 0.5
            recall = float(mask_b[so_sys].mean()) if so_sys.sum() else float("nan")
            fp = float(mask_b[so_mic].mean()) if so_mic.sum() else float("nan")
            resultados.setdefault(k_db, ([], []))
            resultados[k_db][0].append(recall)
            resultados[k_db][1].append(fp)

    print(f"\n{'k_db':>5} {'recall(so_sys)':>15} {'fp(so_mic)':>12}")
    escolhido = None
    for k_db in sorted(resultados):
        recalls, fps = resultados[k_db]
        r, f = np.mean(recalls), np.mean(fps)
        marca = ""
        if f <= FP_MAX and escolhido is None:
            escolhido = k_db
            marca = "  <- escolhido (menor k_db com fp <= 2%)"
        print(f"{k_db:>5} {r:>14.1%} {f:>11.1%}{marca}")

    if escolhido is not None:
        print(f"\nK_DB = {escolhido}")
    else:
        print("\nNenhum k_db manteve fp <= 2% — revisar FP_MAX ou os dados de entrada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
