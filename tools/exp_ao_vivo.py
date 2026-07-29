"""Transcricao ao vivo e viavel? Mede o custo REAL dos dois eixos que decidem.

O usuario propoe: durante a gravacao, ao detectar X ms de silencio, transcrever a
frase acumulada. A duvida certa nao e "da pra fazer" (da) — e quanto se perde em
pontuacao e quanto se paga em computacao, os dois em funcao de X.

Duas coisas que tornam isso nao-obvio:

1. O encoder do Whisper SEMPRE processa 30 s (mel de 3000 frames). Um segmento de
   3 s custa quase o mesmo que um de 30 s. Segmentar fino nao economiza — MULTIPLICA
   o custo total, e e isso que decide se da pra rodar durante uma reuniao.
2. Pontuacao (sobretudo '?') depende de contexto. Quanto menor o segmento, menos
   contexto, e o modelo tende a devolver frases sem pontuacao final.

Referencia = o que o app faz hoje (janelas de 30 s). Para cada limiar de silencio,
mede WER contra ela, densidade de pontuacao e custo de compute.
"""
import re, sys, time, unicodedata
from pathlib import Path
import numpy as np
import av

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reco import ensure_ov_model, _user_data_dir, load_config

SR = 16000
FRAME = int(0.03 * SR)          # 30 ms — resolucao do VAD


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


def trecho_falado(a, seg=180.0):
    """A janela de `seg` segundos com mais energia — para medir sobre fala real,
    nao sobre silencio."""
    step = int(seg * SR)
    if len(a) <= step:
        return a
    melhor, best = 0, -1.0
    for i in range(0, len(a) - step, step // 2):
        e = float(np.mean(a[i:i + step] ** 2))
        if e > best:
            best, melhor = e, i
    return a[melhor:melhor + step]


def vad(a, sil_s):
    """Segmenta em trechos de fala separados por >= sil_s de silencio.

    Limiar adaptativo: o piso de ruido e estimado pelo percentil 20 da energia dos
    quadros, e fala e o que passa de 3x esse piso (com minimo absoluto, para audio
    muito limpo nao virar tudo fala)."""
    nf = len(a) // FRAME
    e = np.array([np.sqrt(np.mean(a[i*FRAME:(i+1)*FRAME] ** 2)) for i in range(nf)])
    piso = max(float(np.percentile(e, 20)), 1e-5)
    lim = max(piso * 3.0, 0.0035)
    fala = e >= lim
    min_sil = max(1, int(sil_s / 0.03))

    segs, ini, ultimo, sil = [], None, None, 0
    for i, f in enumerate(fala):
        if f:
            if ini is None:
                ini = i
            ultimo, sil = i, 0
        elif ini is not None:
            sil += 1
            if sil >= min_sil:
                segs.append((ini * FRAME, (ultimo + 1) * FRAME))
                ini = None
    if ini is not None:
        segs.append((ini * FRAME, (ultimo + 1) * FRAME))
    return [(s, t) for s, t in segs if t - s >= int(0.3 * SR)]


def norm(t):
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]", " ", t).split()


def wer(ref, hyp):
    r, h = norm(ref), norm(hyp)
    if not r:
        return None
    d = np.arange(len(h) + 1)
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            cur = d[j]
            d[j] = min(d[j] + 1, d[j-1] + 1, prev + (r[i-1] != h[j-1]))
            prev = cur
    return float(d[len(h)]) / len(r)


def pontuacao(txt):
    p = len(norm(txt)) or 1
    return {
        "interrog_por_100p": round(txt.count("?") / p * 100, 2),
        "virgula_por_100p": round(txt.count(",") / p * 100, 2),
        "ponto_por_100p": round(txt.count(".") / p * 100, 2),
        "reticencias": txt.count("..."),
    }


def main():
    mp3 = Path(sys.argv[1])
    cfg = load_config()
    modelo = cfg.get("model")
    dev = sys.argv[2] if len(sys.argv) > 2 else "GPU"

    a = trecho_falado(decode_mic(mp3))
    dur = len(a) / SR
    print(f"[audio] {mp3.name} — trecho de {dur:.0f}s | {modelo} @ {dev}\n", flush=True)

    import openvino_genai as og
    pipe = og.WhisperPipeline(str(ensure_ov_model(modelo)), dev,
                              CACHE_DIR=str(_user_data_dir() / "ovcache"))
    c = pipe.get_generation_config()
    c.language, c.task, c.return_timestamps = "<|pt|>", "transcribe", True

    def fala(x):
        r = pipe.generate(x, c)
        ch = getattr(r, "chunks", None)
        return (" ".join((k.text or "").strip() for k in ch) if ch
                else " ".join(getattr(r, "texts", []) or [])).strip()

    # Referencia: exatamente o que o app faz hoje — janelas de 30 s.
    t0 = time.perf_counter()
    ref = " ".join(fala(a[i:i + 30*SR]) for i in range(0, len(a), 30*SR)).strip()
    t_ref = time.perf_counter() - t0
    n_ref = -(-len(a) // (30*SR))
    print(f"REFERENCIA (janelas de 30 s, como hoje)")
    print(f"   {n_ref} chamadas | {t_ref:.1f}s de compute | {len(ref)} chars")
    print(f"   {pontuacao(ref)}\n", flush=True)

    for sil in (0.4, 0.8, 1.5):
        segs = vad(a, sil)
        if not segs:
            print(f"silencio {sil}s: nenhum segmento\n")
            continue
        t0 = time.perf_counter()
        partes = [fala(a[s:t]) for s, t in segs]
        el = time.perf_counter() - t0
        txt = " ".join(p for p in partes if p).strip()
        durs = [(t - s) / SR for s, t in segs]
        print(f"AO VIVO — corta com {sil}s de silencio")
        print(f"   {len(segs)} chamadas ({len(segs)/max(n_ref,1):.1f}x a referencia)"
              f" | {el:.1f}s de compute ({el/max(t_ref,1e-6):.1f}x)")
        print(f"   segmento medio {np.mean(durs):.1f}s (min {min(durs):.1f}, "
              f"max {max(durs):.1f}) -> latencia tipica ~{np.median(durs)+sil:.1f}s")
        print(f"   WER vs referencia: {wer(ref, txt):.1%} | {len(txt)} chars")
        print(f"   {pontuacao(txt)}")
        print(f"   amostra: {txt[:160]!r}\n", flush=True)


if __name__ == "__main__":
    main()
