"""Validacao ponta a ponta: arquivo INTEIRO pelo caminho real do app.

Todas as medidas anteriores foram em janelas isoladas (4 ou 6 de 30 s). Este roda
o `OVTranscriber.transcribe` de verdade — decodifica o MP3, diariza por canal,
cancela eco, aplica a defesa anti-loop — e verifica o criterio de pronto do
roadmap num arquivo completo.
"""
import sys, time, zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reco import OVTranscriber, load_config, decode_16k


def pior_loop(txt):
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


def main():
    mp3 = Path(sys.argv[1])
    cfg = load_config()
    print(f"config em uso: model={cfg.get('model')} device={cfg.get('device')} "
          f"diarize={cfg.get('diarize')} aec={cfg.get('aec')}")

    dur = len(decode_16k(mp3)[0]) / 16000.0
    print(f"[audio] {mp3.name} — {dur/60:.1f} min\n")

    tr = OVTranscriber()
    tr.set_model(cfg.get("model"))
    tr.set_device(cfg.get("device", "AUTO"))

    saida = {}
    pronto = []

    def done(texto, err):
        saida["texto"], saida["err"] = texto, err
        pronto.append(True)

    ultimo = [""]

    def prog(msg):
        if msg != ultimo[0]:
            ultimo[0] = msg
            print(f"   {msg}", flush=True)

    t0 = time.perf_counter()
    tr.transcribe(mp3, lang="pt", diarize=True, aec=True,
                  progress_cb=prog, done_cb=done)
    while not pronto:
        time.sleep(0.5)
    el = time.perf_counter() - t0

    if saida.get("err"):
        print(f"\nERRO: {saida['err']}")
        return 1
    txt = saida["texto"] or ""
    # Medir a compressao no texto final MONTADO seria comparar coisa diferente:
    # ele repete os rotulos "Eu:" / "Interlocutor(es):" a cada troca de turno, e
    # so isso ja empurra a razao acima de 2,4 num texto perfeitamente saudavel.
    # O detector real (_degenerado) roda por janela, no texto cru do Whisper —
    # entao aqui tiramos os rotulos antes de medir.
    import re
    cru = re.sub(r"(?m)^[^:\n]{1,20}:\s*", "", txt)
    p, alvo = pior_loop(cru)
    cr = len(cru.encode()) / max(1, len(zlib.compress(cru.encode())))
    print(f"\n[tempo] {el:.0f}s para {dur:.0f}s de audio = {dur/el:.1f}x tempo real")
    print(f"        extrapolado: 2 h de audio em {7200/(dur/el)/60:.0f} min")
    print(f"[texto] {len(txt)} chars | compressao {cr:.2f} | pior repeticao {p}x {alvo!r}")
    print(f"\n--- primeiros 400 chars ---\n{txt[:400]}")
    ok = p <= 3 and cr <= 2.4
    print(f"\n{'PASSOU' if ok else 'FALHOU'}: criterio = repeticao <= 3x e compressao <= 2,4")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
