"""Teste end-to-end da defesa anti-loop, no caso que a reproduzia.

Roda as janelas de menor energia (onde o Whisper degenera) pelo caminho real do
app — _generate_sem_loop — e compara com o pipe.generate cru. Criterio de pronto
da Fase 1 do roadmap: nenhum n-grama repetindo mais de 3x consecutivas.
"""
import sys, time
from pathlib import Path
import numpy as np
import av

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reco import OVTranscriber, ensure_ov_model, _user_data_dir

SR = 16000


def decode_mic(path):
    with av.open(str(path)) as c:
        rs = av.audio.resampler.AudioResampler(format="fltp", layout="stereo", rate=SR)
        b = []
        for fr in c.decode(audio=0):
            for r in rs.resample(fr):
                b.append(r.to_ndarray())
        for r in rs.resample(None) or []:
            b.append(r.to_ndarray())
    return np.concatenate(b, axis=1).astype(np.float32)[0]


def janelas_fracas(a, n):
    step = 30 * SR
    c = []
    for i in range(0, len(a), step):
        w = a[i:i + step]
        if w.size < step // 2:
            continue
        r = float(np.sqrt(np.mean(w ** 2)))
        if r >= 0.0035:
            c.append((r, w))
    c.sort(key=lambda x: x[0])
    return [w for _r, w in c[:n]]


def pior(txt):
    ws = txt.split()
    p, alvo = 1, ""
    for n in range(1, 9):
        i = 0
        while i + n <= len(ws):
            g = ws[i:i + n]
            k = 1
            while ws[i + k * n:i + (k + 1) * n] == g:
                k += 1
            if k > p:
                p, alvo = k, " ".join(g)
            i += 1 if k == 1 else k * n
    return p, alvo[:50]


def main():
    mp3 = Path(sys.argv[1])
    size = sys.argv[2] if len(sys.argv) > 2 else "small"
    dev = sys.argv[3] if len(sys.argv) > 3 else "GPU"
    jans = janelas_fracas(decode_mic(mp3), 6)
    print(f"[{mp3.name}] {len(jans)} janelas fracas | {size} @ {dev}\n")

    import openvino_genai as og
    pipe = og.WhisperPipeline(str(ensure_ov_model(size)), dev,
                              CACHE_DIR=str(_user_data_dir() / "ovcache"))
    tr = OVTranscriber()
    cfg = tr._gen_cfg(pipe, "pt")

    cru, protegido = [], []
    t0 = time.perf_counter()
    for w in jans:
        cru.append(OVTranscriber._texto_de(pipe.generate(w, cfg)))
    t_cru = time.perf_counter() - t0

    t0 = time.perf_counter()
    for w in jans:
        _res, txt = tr._generate_sem_loop(pipe, cfg, w)
        protegido.append(txt)
    t_prot = time.perf_counter() - t0

    a, b = " ".join(cru), " ".join(protegido)
    pa, ta = pior(a)
    pb, tb = pior(b)
    print(f"SEM defesa: {len(a)} chars | pior repeticao {pa}x {ta!r}")
    print(f"COM defesa: {len(b)} chars | pior repeticao {pb}x {tb!r}")
    print(f"\ncusto de tempo: {t_cru:.1f}s -> {t_prot:.1f}s "
          f"({t_prot/max(t_cru,1e-6):.2f}x)")
    ok = pb <= 3
    print(f"\n{'PASSOU' if ok else 'FALHOU'}: criterio = nenhum n-grama > 3x")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
