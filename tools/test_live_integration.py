"""Integra DualRecorder + LiveTranscriber de ponta a ponta, como a Fase 3 faz
de verdade (nao com MP3 simulado) — grava por dispositivos reais por alguns
segundos, com o modo ao vivo ligado, e confere:
  (a) o rascunho produz texto incremental durante a gravacao;
  (b) drain-then-start: live.stop(wait=True) esvazia a fila antes de retornar;
  (c) o MP3 final tem duracao correta (o modo ao vivo nao atrasa a captura);
  (d) a passada final (OVTranscriber.transcribe) roda depois, sem conflito.

    python tools/test_live_integration.py [segundos]
"""
import sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import av
import reco

SECS = float(sys.argv[1]) if len(sys.argv) > 1 else 20.0
OUT = Path(__file__).resolve().parent


def main():
    mics, spks = reco.list_capture_devices()
    mic_id = reco.default_mic_id()
    sys_id = reco.default_speaker_id()
    print(f"mic = {reco.name_for_id(mics, mic_id)}")
    print(f"sys = {reco.name_for_id(spks, sys_id)}")

    cfg = reco.load_config()
    tr = reco.make_transcriber()
    tr.set_model(cfg.get("model"))
    tr.set_device("GPU")

    t0 = time.perf_counter()
    textos = []
    def on_text(spk, txt):
        textos.append((time.perf_counter(), spk, txt))
        print(f"  [{time.perf_counter()-t0:.1f}s] {spk}: {txt[:70]}", flush=True)

    def on_warn(msg):
        print(f"  [warn] {msg}", flush=True)

    live = reco.LiveTranscriber(tr, lang="pt")
    live.start(on_text=on_text, on_warn=on_warn)

    rec = reco.DualRecorder()
    rec.start(mic_id, sys_id, on_pair=live.feed_pair, out_dir=OUT)
    if not rec.recording:
        print("gravacao nao iniciou"); return 1

    print(f"gravando {SECS:.0f}s com modo ao vivo ligado...")
    time.sleep(SECS)
    t_rec = time.perf_counter() - t0

    print("parando: drain-then-start...")
    path = rec.stop()
    t_drain0 = time.perf_counter()
    live.stop(wait=True, timeout=15.0)
    t_drain = time.perf_counter() - t_drain0
    print(f"  drain levou {t_drain:.1f}s (fila esvaziada antes de liberar a thread)")

    with av.open(str(path)) as c:
        declared = c.duration / av.time_base
    print(f"\n[mp3] gravado={t_rec:.2f}s declarado={declared:.2f}s "
          f"(erro {declared - t_rec:+.2f}s)")
    print(f"[rascunho] {len(textos)} trechos produzidos durante a gravacao")

    print("\n[passada final] rodando apos o drain (nao deve conflitar)...")
    saida = {}
    pronto = []
    def done(txt, err):
        saida["t"], saida["e"] = txt, err
        pronto.append(True)
    t0f = time.perf_counter()
    tr.transcribe(path, lang="pt", diarize=True, aec=True, progress_cb=None, done_cb=done)
    while not pronto:
        time.sleep(0.2)
    print(f"[passada final] {time.perf_counter()-t0f:.1f}s | erro={saida.get('e')} | "
          f"{len(saida.get('t') or '')} chars")

    ok = abs(declared - t_rec) < 1.0 and saida.get("e") is None
    print("\n" + ("PASSOU" if ok else "FALHOU"))
    path.unlink(missing_ok=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
