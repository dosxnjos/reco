"""Confirma o alvo de acumulo em MAIS DE UM arquivo — separando escolha de validacao.

O alvo de 5 s foi escolhido medindo um unico trecho de 180 s. Escolher e validar
no mesmo dado e o garden-of-forking-paths que `C:\\Dev\\CLAUDE.md` § Decidir por
evidencia manda evitar: a regra roda sobre um dado, a confirmacao sobre outro que
ela nunca viu.

Aqui a REGRA congelada e: "alvo = o que maximiza pontuacao de interrogacao sem
piorar o WER". O que varia e o dado. Se o vencedor mudar de arquivo para arquivo,
o parametro nao e robusto e o desenho deve usar o mais conservador.
"""
import sys, time
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from exp_contexto import decode_mic, trecho_falado, vad, agrupar, wer, pont, SR
from reco import ensure_ov_model, _user_data_dir, load_config
import openvino_genai as og

ALVOS = (0, 3, 5, 7, 10)


def main():
    modelo = load_config().get("model")
    pipe = og.WhisperPipeline(str(ensure_ov_model(modelo)), "GPU",
                              CACHE_DIR=str(_user_data_dir() / "ovcache"))

    def fala(x, prompt=None):
        c = pipe.get_generation_config()
        c.language, c.task, c.return_timestamps = "<|pt|>", "transcribe", True
        if prompt:
            c.initial_prompt = prompt
        r = pipe.generate(x, c)
        ch = getattr(r, "chunks", None)
        return (" ".join((k.text or "").strip() for k in ch) if ch
                else " ".join(getattr(r, "texts", []) or [])).strip()

    vencedores = []
    for nome in sys.argv[1:]:
        mp3 = Path.home() / "Documents/Reco" / nome
        a = trecho_falado(decode_mic(mp3))
        ref = " ".join(fala(a[i:i+30*SR]) for i in range(0, len(a), 30*SR)).strip()
        segs = vad(a)
        print(f"\n=== {mp3.stem} === ({len(a)/SR:.0f}s, {len(segs)} segmentos VAD)")
        print(f"{'alvo':>6} {'envios':>7} {'compute':>8} {'latencia':>9} "
              f"{'WER':>7} {'?':>6} {',':>6}")
        linhas = []
        for alvo in ALVOS:
            grupos = agrupar(segs, alvo)
            t0 = time.perf_counter()
            partes, ctx = [], None
            for g in grupos:
                x = np.concatenate([a[s:t] for s, t in g])
                p = fala(x, prompt=ctx)
                partes.append(p)
                ctx = " ".join((" ".join(partes)).split()[-30:]) or None
            el = time.perf_counter() - t0
            txt = " ".join(p for p in partes if p).strip()
            lat = float(np.median([sum((t-s)/SR for s, t in g) for g in grupos])) + 0.8
            w = wer(ref, txt)
            q, v = pont(txt)
            linhas.append((alvo, w, q))
            rot = "0 (nenhum)" if alvo == 0 else f"{alvo}s"
            print(f"{rot:>6} {len(grupos):>7} {el:>7.1f}s {lat:>8.1f}s "
                  f"{w:>6.1%} {q:>6} {v:>6}", flush=True)
        # regra congelada: maior '?' entre os que nao pioram o WER mais que 1 ponto
        melhor_wer = min(l[1] for l in linhas)
        eleg = [l for l in linhas if l[1] <= melhor_wer + 0.01]
        venc = max(eleg, key=lambda l: l[2])
        vencedores.append(venc[0])
        print(f"   -> vencedor pela regra: alvo={venc[0]}s "
              f"(WER {venc[1]:.1%}, ?={venc[2]})")

    print(f"\nVENCEDORES por arquivo: {vencedores}")
    if len(set(vencedores)) == 1:
        print(f"CONSISTENTE — alvo = {vencedores[0]}s se sustenta fora do dado de escolha.")
    else:
        print(f"INCONSISTENTE — usar o mais conservador: {min(vencedores)}s "
              f"(menor latencia, menor risco de misturar falas).")


if __name__ == "__main__":
    main()
