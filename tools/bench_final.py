"""Benchmark definitivo: device x modelo, nos TRES eixos que importam.

1. VELOCIDADE  - x tempo real, e a extrapolacao para 10 min / 1 h / 2 h de audio.
2. QUALIDADE   - divergencia (WER) contra a melhor transcricao disponivel como
                 referencia, + deteccao de loop degenerado (taxa de compressao).
3. CONVIVENCIA - quanto o resto do computador sofre. Medido como o atraso de um
                 tick de 10 ms (o que qualquer UI faz) e a queda de throughput de
                 um trabalho leve de CPU, durante a transcricao. E a resposta
                 direta a "sem estragar minha experiencia em outros apps".

Uso:
  BENCH_MODELOS=small,large-v3-turbo BENCH_DEVICES=NPU,GPU,CPU \
  python temp/bench_final.py <mp3> [n_janelas]
"""
import os, sys, json, time, threading, zlib
from pathlib import Path
import numpy as np
import av
import openvino as ov
import openvino_genai as og

SR = 16000
WIN = 30.0
SILENCE_RMS = 0.0035


# ── audio ──────────────────────────────────────────────────────────────────────
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


def janelas(audio, n_max, modo):
    step = int(WIN * SR)
    cand = []
    for i in range(0, len(audio), step):
        w = audio[i:i + step]
        if w.size < step // 2:
            continue
        r = float(np.sqrt(np.mean(w ** 2)))
        if r >= SILENCE_RMS:
            cand.append((r, i / SR, w))
    if modo == "fracas":            # as mais silenciosas: onde o Whisper degenera
        cand.sort(key=lambda x: x[0])
    return [(o, w) for _r, o, w in cand[:n_max]]


# ── eixo 3: convivencia ────────────────────────────────────────────────────────
class Vizinho:
    """Simula 'outro app aberto': um tick de 10 ms + um trabalho leve de CPU.

    Registra o atraso de cada tick (jitter) e quantas iteracoes do trabalho
    completou por segundo. Comparado contra um baseline medido com a maquina
    ociosa, isso e o custo real que a transcricao impoe ao resto do sistema."""

    def __init__(self):
        self.atrasos, self.iters = [], 0
        self._parar = threading.Event()
        self._m = np.random.rand(128, 128).astype(np.float32)

    def _tick(self):
        while not self._parar.is_set():
            t0 = time.perf_counter()
            time.sleep(0.01)
            self.atrasos.append((time.perf_counter() - t0 - 0.01) * 1000)

    def _work(self):
        while not self._parar.is_set():
            self._m @ self._m
            self.iters += 1

    def __enter__(self):
        self._t0 = time.perf_counter()
        self._th = [threading.Thread(target=self._tick, daemon=True),
                    threading.Thread(target=self._work, daemon=True)]
        for t in self._th:
            t.start()
        return self

    def __exit__(self, *a):
        self._parar.set()
        for t in self._th:
            t.join(timeout=2)
        self.dur = time.perf_counter() - self._t0

    @property
    def stats(self):
        at = np.array(self.atrasos) if self.atrasos else np.array([0.0])
        return {"atraso_p50_ms": round(float(np.percentile(at, 50)), 1),
                "atraso_p95_ms": round(float(np.percentile(at, 95)), 1),
                "iters_por_s": round(self.iters / max(self.dur, 1e-6), 1)}


def baseline_vizinho(seg=6.0):
    with Vizinho() as v:
        time.sleep(seg)
    return v.stats


# ── eixo 2: qualidade ──────────────────────────────────────────────────────────
def norm(txt):
    import re, unicodedata
    t = unicodedata.normalize("NFD", txt.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]", " ", t).split()


def wer(ref, hyp):
    """Taxa de erro de palavra de hyp contra ref (0 = identico)."""
    r, h = norm(ref), norm(hyp)
    if not r:
        return None
    d = np.arange(len(h) + 1)
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            cur = d[j]
            d[j] = min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1]))
            prev = cur
    return round(float(d[len(h)]) / len(r), 3)


def compressao(txt):
    b = txt.encode("utf-8")
    return round(len(b) / max(1, len(zlib.compress(b))), 2)


def pior_loop(txt):
    """Maior numero de repeticoes consecutivas de um mesmo trecho (1..8 palavras)."""
    ws = txt.split()
    pior, alvo = 1, ""
    for n in range(1, 9):
        i = 0
        while i + n <= len(ws):
            g = ws[i:i + n]
            c = 1
            while ws[i + c * n:i + (c + 1) * n] == g:
                c += 1
            if c > pior:
                pior, alvo = c, " ".join(g)
            i += 1 if c == 1 else c * n
    return pior, alvo[:60]


# ── execucao ───────────────────────────────────────────────────────────────────
def roda(model_dir, device, jans, cache, medir_vizinho=True):
    t0 = time.perf_counter()
    pipe = og.WhisperPipeline(str(model_dir), device, CACHE_DIR=str(cache))
    t_load = time.perf_counter() - t0

    cfg = pipe.get_generation_config()
    cfg.language, cfg.task, cfg.return_timestamps = "<|pt|>", "transcribe", True

    textos, t_gen = [], 0.0
    ctx = Vizinho() if medir_vizinho else None
    if ctx:
        ctx.__enter__()
    for _off, w in jans:
        t1 = time.perf_counter()
        res = pipe.generate(w, cfg)
        t_gen += time.perf_counter() - t1
        ch = getattr(res, "chunks", None)
        textos.append(" ".join((c.text or "").strip() for c in ch) if ch
                      else " ".join(getattr(res, "texts", []) or []))
    if ctx:
        ctx.__exit__()
    del pipe

    txt = " ".join(textos).strip()
    audio_s = sum(len(w) for _o, w in jans) / SR
    rep, alvo = pior_loop(txt)
    out = {"load_s": round(t_load, 1), "gen_s": round(t_gen, 1),
           "audio_s": round(audio_s, 1),
           "x_tempo_real": round(audio_s / max(t_gen, 1e-6), 1),
           "min_para_2h": round(7200 / max(audio_s / t_gen, 1e-6) / 60, 1),
           "min_para_10min": round(600 / max(audio_s / t_gen, 1e-6) / 60, 1),
           "chars": len(txt), "compressao": compressao(txt),
           "loop_max": rep, "loop_trecho": alvo, "texto": txt}
    if ctx:
        out["vizinho"] = ctx.stats
    return out


def main():
    mp3 = Path(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    modo = os.environ.get("BENCH_MODO", "primeiras")
    saida = os.environ.get("BENCH_SAIDA", "temp/bench_final.json")
    so_mod = [s for s in os.environ.get("BENCH_MODELOS", "").split(",") if s]
    so_dev = [s for s in os.environ.get("BENCH_DEVICES", "").split(",") if s]

    mic, _ = decode(mp3)
    jans = janelas(mic, n, modo)
    print(f"[audio] {mp3.name} {len(mic)/SR:.0f}s -> {len(jans)} janelas (modo={modo})",
          flush=True)

    print("[baseline] medindo a maquina ociosa…", flush=True)
    base = baseline_vizinho()
    print(f"[baseline] tick p50={base['atraso_p50_ms']}ms p95={base['atraso_p95_ms']}ms "
          f"| {base['iters_por_s']} it/s\n", flush=True)

    cache = Path.home() / "AppData/Local/Reco/ovcache"
    cache.mkdir(parents=True, exist_ok=True)
    modelos = {"small": Path("models/whisper-small-int8-ov")}
    extra = Path.home() / "AppData/Local/Reco/models"
    if extra.is_dir():
        for d in sorted(extra.iterdir()):
            if (d / "openvino_encoder_model.xml").exists():
                modelos[d.name.replace("whisper-", "").replace("-int8-ov", "")] = d
    if so_mod:
        modelos = {k: v for k, v in modelos.items() if k in so_mod}
    devices = [d for d in ov.Core().available_devices if d in ("NPU", "GPU", "CPU")]
    if so_dev:
        devices = [d for d in devices if d in so_dev]

    res = {"_baseline": base}
    for nome, mdir in modelos.items():
        for dev in devices:
            k = f"{nome} | {dev}"
            try:
                r = roda(mdir, dev, jans, cache)
                res[k] = r
                v = r["vizinho"]
                print(f"{k}\n   {r['x_tempo_real']}x tempo real "
                      f"| 2h de audio em {r['min_para_2h']} min "
                      f"| load {r['load_s']}s\n"
                      f"   vizinho: tick p50={v['atraso_p50_ms']}ms "
                      f"p95={v['atraso_p95_ms']}ms ({base['atraso_p95_ms']} ocioso) "
                      f"| {v['iters_por_s']} it/s ({base['iters_por_s']} ocioso)\n"
                      f"   texto: {r['chars']} chars compr={r['compressao']} "
                      f"loop_max={r['loop_max']}x {r['loop_trecho']!r}", flush=True)
            except Exception as e:
                res[k] = {"erro": str(e)[:300]}
                print(f"{k}\n   ERRO: {str(e)[:300]}", flush=True)

    # qualidade relativa: melhor modelo disponivel como referencia
    ref_k = next((k for k in res if k.startswith("large-v3-turbo") and "texto" in res[k]), None)
    if ref_k:
        ref = res[ref_k]["texto"]
        print(f"\n[qualidade] divergencia contra {ref_k} (referencia):", flush=True)
        for k, v in res.items():
            if k.startswith("_") or "texto" not in v or k == ref_k:
                continue
            v["wer_vs_ref"] = wer(ref, v["texto"])
            print(f"   {k}: WER {v['wer_vs_ref']:.1%}", flush=True)

    Path(saida).write_text(json.dumps(res, indent=2, ensure_ascii=False),
                           encoding="utf-8")
    print(f"\n[ok] {saida}", flush=True)


if __name__ == "__main__":
    main()
