"""Define a LOGICA da transcricao ao vivo por medicao, nao por gosto.

Tres perguntas que o desenho precisa responder, e que so o dado resolve:

A) ACUMULO — segmento curto do VAD basta, ou e preciso juntar fala ate uma
   duracao alvo antes de mandar? Isso e o trade-off central: latencia menor
   custa qualidade e custa compute. Mede a curva inteira.

B) CONTEXTO — passar o texto anterior como `initial_prompt` melhora pontuacao?
   (O codigo avisa que isso estoura o decoder estatico da NPU; na iGPU deve
   funcionar — verificar antes de desenhar em cima.)

C) MARGEM DE AUDIO — incluir ~1 s de audio ANTES do segmento ajuda o modelo a
   acertar o comeco da frase?

Referencia de qualidade = janelas de 30 s (o que o app faz hoje, com todo o
contexto disponivel). WER contra ela mede divergencia, nao erro absoluto.
"""
import re, sys, time, unicodedata
from pathlib import Path
import numpy as np
import av

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reco import ensure_ov_model, _user_data_dir, load_config

SR = 16000
FRAME = int(0.03 * SR)


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
    step = int(seg * SR)
    if len(a) <= step:
        return a
    best, onde = -1.0, 0
    for i in range(0, len(a) - step, step // 2):
        e = float(np.mean(a[i:i+step] ** 2))
        if e > best:
            best, onde = e, i
    return a[onde:onde+step]


def vad(a, sil_s=0.8, max_s=28.0, min_s=0.3):
    nf = len(a) // FRAME
    e = np.array([np.sqrt(np.mean(a[i*FRAME:(i+1)*FRAME] ** 2)) for i in range(nf)])
    piso = max(float(np.percentile(e, 20)), 1e-5)
    lim = max(piso * 3.0, 0.0035)
    fala = e >= lim
    min_sil = max(1, int(sil_s / 0.03))
    segs, ini, ult, sil = [], None, None, 0
    for i, f in enumerate(fala):
        if f:
            if ini is None:
                ini = i
            ult, sil = i, 0
        elif ini is not None:
            sil += 1
            if sil >= min_sil:
                segs.append((ini*FRAME, (ult+1)*FRAME))
                ini = None
    if ini is not None:
        segs.append((ini*FRAME, (ult+1)*FRAME))
    # parte a forca o que passa de max_s (o Whisper trunca acima de 30 s)
    out = []
    for s, t in segs:
        if t - s < int(min_s * SR):
            continue
        while t - s > int(max_s * SR):
            out.append((s, s + int(max_s * SR)))
            s += int(max_s * SR)
        out.append((s, t))
    return out


def agrupar(segs, alvo_s):
    """Junta segmentos consecutivos ate somar `alvo_s` de fala. alvo_s=0 -> nao
    agrupa (cada segmento do VAD vai sozinho, latencia minima)."""
    if alvo_s <= 0:
        return [[s] for s in segs]
    grupos, atual, acc = [], [], 0.0
    for s, t in segs:
        atual.append((s, t))
        acc += (t - s) / SR
        if acc >= alvo_s:
            grupos.append(atual)
            atual, acc = [], 0.0
    if atual:
        grupos.append(atual)
    return grupos


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


def pont(t):
    p = len(norm(t)) or 1
    return (round(t.count("?") / p * 100, 2), round(t.count(",") / p * 100, 2))


def main():
    mp3 = Path(sys.argv[1])
    dev = sys.argv[2] if len(sys.argv) > 2 else "GPU"
    modelo = load_config().get("model")
    a = trecho_falado(decode_mic(mp3))
    print(f"[audio] {mp3.name} — {len(a)/SR:.0f}s | {modelo} @ {dev}\n", flush=True)

    import openvino_genai as og
    pipe = og.WhisperPipeline(str(ensure_ov_model(modelo)), dev,
                              CACHE_DIR=str(_user_data_dir() / "ovcache"))

    def cfg_novo(prompt=None):
        c = pipe.get_generation_config()
        c.language, c.task, c.return_timestamps = "<|pt|>", "transcribe", True
        if prompt:
            c.initial_prompt = prompt
        return c

    def fala(x, prompt=None):
        r = pipe.generate(x, cfg_novo(prompt))
        ch = getattr(r, "chunks", None)
        return (" ".join((k.text or "").strip() for k in ch) if ch
                else " ".join(getattr(r, "texts", []) or [])).strip()

    # ── Referencia: janelas de 30 s, como hoje
    t0 = time.perf_counter()
    ref = " ".join(fala(a[i:i+30*SR]) for i in range(0, len(a), 30*SR)).strip()
    t_ref = time.perf_counter() - t0
    print(f"REFERENCIA 30s: {t_ref:.1f}s compute | {len(ref)} chars | "
          f"?={pont(ref)[0]} ,={pont(ref)[1]}\n", flush=True)

    segs = vad(a)
    print(f"VAD (0,8s): {len(segs)} segmentos, "
          f"media {np.mean([(t-s)/SR for s,t in segs]):.1f}s\n", flush=True)

    # ── A) curva de acumulo
    print("A) ACUMULO — quanto juntar antes de mandar")
    print(f"{'alvo':>6} {'envios':>7} {'compute':>8} {'latencia':>9} {'WER':>7} {'?':>6} {',':>6}")
    for alvo in (0, 5, 10, 15, 20):
        grupos = agrupar(segs, alvo)
        t0 = time.perf_counter()
        partes = []
        for g in grupos:
            partes.append(fala(np.concatenate([a[s:t] for s, t in g])))
        el = time.perf_counter() - t0
        txt = " ".join(p for p in partes if p).strip()
        durs = [sum((t-s)/SR for s, t in g) for g in grupos]
        lat = np.median(durs) + 0.8
        q, v = pont(txt)
        rot = "sem agrupar" if alvo == 0 else f"{alvo}s"
        print(f"{rot:>6} {len(grupos):>7} {el:>7.1f}s {lat:>8.1f}s "
              f"{wer(ref, txt):>6.1%} {q:>6} {v:>6}", flush=True)

    # ── B) contexto via initial_prompt
    print("\nB) CONTEXTO — initial_prompt com o texto anterior")
    grupos = agrupar(segs, 10)
    try:
        t0 = time.perf_counter()
        partes, ctx = [], None
        for g in grupos:
            x = np.concatenate([a[s:t] for s, t in g])
            p = fala(x, prompt=ctx)
            partes.append(p)
            ctx = " ".join((" ".join(partes)).split()[-30:]) or None
        el = time.perf_counter() - t0
        txt = " ".join(p for p in partes if p).strip()
        q, v = pont(txt)
        print(f"   COM contexto : {el:.1f}s | WER {wer(ref, txt):.1%} | ?={q} ,={v}")
    except Exception as e:
        print(f"   FALHOU em {dev}: {str(e)[:160]}")

    # ── C) margem de audio antes do segmento
    print("\nC) MARGEM — 1 s de audio antes de cada envio")
    grupos = agrupar(segs, 10)
    t0 = time.perf_counter()
    partes = []
    for g in grupos:
        ini = max(0, g[0][0] - SR)
        partes.append(fala(a[ini:g[-1][1]]))
    el = time.perf_counter() - t0
    txt = " ".join(p for p in partes if p).strip()
    q, v = pont(txt)
    print(f"   COM margem   : {el:.1f}s | WER {wer(ref, txt):.1%} | ?={q} ,={v}")
    print("   (WER maior aqui pode ser repeticao de borda — a margem reintroduz "
          "audio ja transcrito)")


if __name__ == "__main__":
    main()
