"""Eixo 3, medido direito: quanto a transcricao atrapalha OUTRO APP.

A primeira tentativa media isso com um 'vizinho' feito de numpy @ numpy — que
aciona BLAS multi-thread e ocupa todos os nucleos. Aquilo nao simula um app
interativo, simula um segundo job pesado; deu resultado incoerente (combinacoes
aparecendo MAIS rapidas que a maquina ociosa) e foi descartado.

Aqui o vizinho e um PROCESSO separado (temp/vizinho.py), single-thread, que acorda
a cada 50 ms e faz um trabalho fixo — o perfil de um app de interface. A metrica e
LATENCIA: quantas vezes mais devagar esse trabalho fica durante a transcricao.
Um app que engasga e um trabalho de 3 ms virando 30 ms; e isso que se ve na tela.
"""
import json, os, subprocess, sys, threading, time
from pathlib import Path
import numpy as np
import av
import openvino as ov
import openvino_genai as og

SR = 16000
WIN = 30.0
SILENCE_RMS = 0.0035


class VizinhoProc:
    def __init__(self):
        self.linhas = []
        self._p = subprocess.Popen(
            [sys.executable, "-u", str(Path(__file__).with_name("vizinho.py"))],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        self._t = threading.Thread(target=self._ler, daemon=True)
        self._t.start()

    def _ler(self):
        for ln in self._p.stdout:
            try:
                d = json.loads(ln)
                d["wall"] = time.perf_counter()
                self.linhas.append(d)
            except Exception:
                pass

    def marca(self):
        return time.perf_counter()

    def entre(self, t0, t1):
        sel = [d for d in self.linhas if t0 <= d["wall"] <= t1]
        if not sel:
            return None
        return {
            "trabalho_p50": round(float(np.median([d["trabalho_p50"] for d in sel])), 1),
            "trabalho_p95": round(float(np.median([d["trabalho_p95"] for d in sel])), 1),
            "acorda_p95": round(float(np.median([d["acorda_p95"] for d in sel])), 1),
            "janelas": len(sel),
        }

    def parar(self):
        self._p.terminate()


def decode(path):
    with av.open(str(path)) as cont:
        rs = av.audio.resampler.AudioResampler(format="fltp", layout="stereo", rate=SR)
        buf = []
        for fr in cont.decode(audio=0):
            for r in rs.resample(fr):
                buf.append(r.to_ndarray())
        for r in rs.resample(None) or []:
            buf.append(r.to_ndarray())
    a = np.concatenate(buf, axis=1).astype(np.float32)
    return a[0]


def janelas(audio, n_max):
    step = int(WIN * SR)
    out = []
    for i in range(0, len(audio), step):
        w = audio[i:i + step]
        if w.size >= step // 2 and float(np.sqrt(np.mean(w ** 2))) >= SILENCE_RMS:
            out.append(w)
        if len(out) >= n_max:
            break
    return out


def main():
    mp3 = Path(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    jans = janelas(decode(mp3), n)
    audio_s = sum(len(w) for w in jans) / SR
    print(f"[audio] {mp3.name} -> {len(jans)} janelas ({audio_s:.0f}s)\n", flush=True)

    viz = VizinhoProc()
    print("[baseline] maquina ociosa, 10 s…", flush=True)
    t0 = viz.marca()
    time.sleep(10)
    base = viz.entre(t0, viz.marca())
    print(f"[baseline] trabalho p50={base['trabalho_p50']}ms p95={base['trabalho_p95']}ms"
          f" | acorda p95={base['acorda_p95']}ms\n", flush=True)

    cache = Path.home() / "AppData/Local/Reco/ovcache"
    modelos = {"small": Path("models/whisper-small-int8-ov")}
    extra = Path.home() / "AppData/Local/Reco/models"
    for d in sorted(extra.iterdir()) if extra.is_dir() else []:
        if (d / "openvino_encoder_model.xml").exists():
            modelos[d.name.replace("whisper-", "").replace("-int8-ov", "")] = d
    so_mod = [s for s in os.environ.get("BENCH_MODELOS", "").split(",") if s]
    if so_mod:
        modelos = {k: v for k, v in modelos.items() if k in so_mod}
    devices = [d for d in ov.Core().available_devices if d in ("NPU", "GPU", "CPU")]

    res = {"_baseline": base}
    for nome, mdir in modelos.items():
        for dev in devices:
            k = f"{nome} | {dev}"
            try:
                pipe = og.WhisperPipeline(str(mdir), dev, CACHE_DIR=str(cache))
                cfg = pipe.get_generation_config()
                cfg.language, cfg.task = "<|pt|>", "transcribe"
                cfg.return_timestamps = True
                time.sleep(2)                       # deixa o vizinho estabilizar
                ini = viz.marca()
                for w in jans:
                    pipe.generate(w, cfg)
                fim = viz.marca()
                del pipe
                v = viz.entre(ini + 1, fim)         # descarta o 1o segundo (warm-up)
                gen = fim - ini
                lentidao = v["trabalho_p50"] / base["trabalho_p50"]
                res[k] = {"gen_s": round(gen, 1),
                          "x_tempo_real": round(audio_s / gen, 1),
                          "min_para_2h": round(7200 / (audio_s / gen) / 60, 1),
                          "vizinho": v, "lentidao_vizinho": round(lentidao, 2)}
                print(f"{k}\n   {res[k]['x_tempo_real']}x tempo real "
                      f"| 2h em {res[k]['min_para_2h']} min\n"
                      f"   vizinho: trabalho {v['trabalho_p50']}ms "
                      f"(ocioso {base['trabalho_p50']}ms) -> "
                      f"{lentidao:.1f}x mais lento | acorda p95={v['acorda_p95']}ms",
                      flush=True)
                time.sleep(3)
            except Exception as e:
                res[k] = {"erro": str(e)[:200]}
                print(f"{k}\n   ERRO: {str(e)[:200]}", flush=True)

    viz.parar()
    Path("temp/convivencia.json").write_text(
        json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n[ok] temp/convivencia.json", flush=True)


if __name__ == "__main__":
    main()
