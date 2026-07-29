"""Remedida do orcamento de device (Dec1) com o pipeline REAL de hoje —
nao o pipe.generate() cru de bench_convivencia.py.

Por que remedir: Dec1 mediu "iGPU ~20% de ocupacao" no pipeline ANTERIOR as
Fases 1/2 (roadmap 2026-07-29-melhoria-transcricao-ao-vivo-vad-diarizacao.md).
Hoje o caminho tem VAD+agrupamento+contexto (Fase 1) e dominancia de canal com
realinhamento a cada 30s (Fase 2), medido mais lento que o legado num arquivo
real. O modo ao vivo (Fase 3) tem que caber no custo de HOJE, nao no de antes.

Reusa VizinhoProc de bench_convivencia.py (processo separado, single-thread,
mede latencia — nao throughput). Roda OVTranscriber.transcribe() de verdade
(diarize+aec, o preset que o modo ao vivo vai usar) sobre um trecho real,
medindo a latencia do vizinho durante a transcricao.
"""
import sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bench_convivencia import VizinhoProc
from reco import OVTranscriber, load_config


def main():
    mp3 = Path(sys.argv[1])
    cfg = load_config()

    viz = VizinhoProc()
    print("[baseline] maquina ociosa, 10 s...", flush=True)
    t0 = viz.marca()
    time.sleep(10)
    base = viz.entre(t0, viz.marca())
    print(f"[baseline] trabalho p50={base['trabalho_p50']}ms p95={base['trabalho_p95']}ms"
          f" | acorda p95={base['acorda_p95']}ms\n", flush=True)

    tr = OVTranscriber()
    tr.set_model(cfg.get("model"))
    tr.set_device("GPU")   # Dec1: modo ao vivo é sempre iGPU

    saida = {}
    pronto = []
    def done(t, e):
        saida["t"], saida["e"] = t, e
        pronto.append(True)

    time.sleep(2)   # deixa o vizinho estabilizar
    ini = viz.marca()
    tr.transcribe(mp3, lang="pt", diarize=True, aec=True, progress_cb=None, done_cb=done)
    while not pronto:
        time.sleep(0.2)
    fim = viz.marca()

    v = viz.entre(ini + 1, fim)   # descarta o 1o segundo (warm-up)
    lentidao = v["trabalho_p50"] / base["trabalho_p50"] if v else float("nan")
    print(f"\n[transcricao] {fim - ini:.1f}s | erro={saida.get('e')}")
    if v:
        print(f"[vizinho] trabalho {v['trabalho_p50']}ms (ocioso {base['trabalho_p50']}ms) "
              f"-> {lentidao:.1f}x mais lento | acorda p95={v['acorda_p95']}ms "
              f"(ocioso {base['acorda_p95']}ms)")
    else:
        print("[vizinho] sem amostras na janela — vizinho pode ter travado")
    viz.parar()


if __name__ == "__main__":
    main()
