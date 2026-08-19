"""Mede o par (ERLE, dano na voz) do `cancel_echo`, em audio real.

Por que este script existe: ERLE sozinho e indistinguivel de "abaixei o volume".
Todo numero de AEC deste projeto passa a sair em par:

  ERLE     — quanto de eco saiu, nos blocos em que so o far-end (PC) chega ao mic
  dano_voz — quanto da voz do usuario saiu, nos blocos em que so ele fala
             (quanto MENOR melhor; acima de 2 dB e defeito, nao trade-off)

⚠️ A ROTULAGEM E ALINHADA, e isso nao e detalhe (19/08/2026). O eco chega ao mic
~200 ms depois (latencia de buffer entre os streams, nao acustica). Rotular por
energia SIMULTANEA — o que `tools/medir_eco.py` faz — classifica o rabo do eco,
que toca quando o sistema ja silenciou, como "so o usuario falando": nessa
metrica o `cancel_echo` aparecia destruindo 28 dB da voz do usuario, quando o que
ele removia ali era eco de verdade. Com o sistema alinhado antes de comparar
energias, o mesmo codigo mede +15 dB de ERLE com <= 0,5 dB de dano na voz.
Rotulagem simultanea + canais desalinhados = medicao invalida. Ver
`docs/ARMADILHAS.md` e roadmap/2026-08-19-melhoria-antieco-de-verdade.md.

Compara duas configuracoes na mesma janela: `maxlag_s=0.5` (vigente) contra
`maxlag_s=0.2` (o valor de antes de 19/08, que saturava — o atraso real chega a
3370 amostras).

Uso:
    python tools/medir_aec.py <mp3> [n_janelas] [dur_janela_s]

Sai com codigo 1 se o gate nao passar (dano_voz <= 2 dB em TODAS as janelas e
ERLE mediano >= 5 dB), 0 se passar. Serve como guarda de regressao do AEC.

⚠️ Trabalha por janelas com `seek`: decodificar 30 min inteiros (249 MB em
float32) ja estourou a memoria desta maquina.
"""
import sys
from pathlib import Path

import numpy as np
import av

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reco import cancel_echo, _alinhar_canais                   # noqa: E402

SR = 16000
B = int(0.1 * SR)          # bloco de rotulagem: 100 ms
LIM = 0.0035               # mesmo limiar de tools/medir_eco.py
GATE_DANO = 2.0            # dB — teto do dano na voz
GATE_ERLE = 5.0            # dB — piso do ERLE mediano


def db(x):
    return 20 * np.log10(max(float(x), 1e-12))


def rms(x):
    x = np.asarray(x, np.float64)
    return float(np.sqrt(np.mean(x ** 2))) if x.size else 0.0


def fmt(v):
    return f"{v:+7.1f}" if v is not None else "      -"


def perfil(path):
    """Uma passada em streaming: RMS por bloco de 100 ms dos dois canais."""
    m, s = [], []
    resto_m = np.zeros(0, np.float32)
    resto_s = np.zeros(0, np.float32)
    with av.open(str(path)) as cont:
        rsp = av.audio.resampler.AudioResampler(format="fltp", layout="stereo", rate=SR)
        for frame in cont.decode(audio=0):
            for r in rsp.resample(frame):
                a = r.to_ndarray().astype(np.float32)
                resto_m = np.concatenate([resto_m, a[0]])
                resto_s = np.concatenate([resto_s, a[1]])
                nb = len(resto_m) // B
                if nb:
                    for i in range(nb):
                        m.append(rms(resto_m[i * B:(i + 1) * B]))
                        s.append(rms(resto_s[i * B:(i + 1) * B]))
                    resto_m = resto_m[nb * B:].copy()
                    resto_s = resto_s[nb * B:].copy()
    return np.array(m), np.array(s)


def ler_janela(path, ini_s, dur_s):
    n_alvo = int(dur_s * SR)
    m, s = [], []
    with av.open(str(path)) as cont:
        rsp = av.audio.resampler.AudioResampler(format="fltp", layout="stereo", rate=SR)
        cont.seek(int(ini_s * av.time_base))
        got = 0
        for frame in cont.decode(audio=0):
            for r in rsp.resample(frame):
                a = r.to_ndarray().astype(np.float32)
                m.append(a[0])
                s.append(a[1])
                got += a.shape[1]
            if got >= n_alvo:
                break
    if not m:
        return np.zeros(0, np.float32), np.zeros(0, np.float32)
    return np.concatenate(m)[:n_alvo], np.concatenate(s)[:n_alvo]


def escolhe_janelas(bm, bs, n_janelas, dur_s):
    """As janelas com mais material para medir os DOIS lados do par.

    Escolher por posicao (linspace) desperdicou 6 de 8 janelas na primeira
    medicao de 19/08 — janela sem bloco de fala isolada nao mede dano na voz, e
    sem bloco de eco isolado nao mede ERLE. Aqui a rotulagem e a crua (sem
    alinhar), o que basta para ACHAR janelas; a medida usa a alinhada.
    """
    largura = int(dur_s * 10)
    so_sys = (bs >= LIM) & (bm < LIM * 3)
    so_mic = (bm >= LIM) & (bs < LIM)
    cand = []
    for i in range(0, max(1, len(bm) - largura), largura // 2):
        js, jm = int(so_sys[i:i + largura].sum()), int(so_mic[i:i + largura].sum())
        if js >= 10 and jm >= 5:
            cand.append((min(js, jm * 2), i * 0.1, js, jm))
    cand.sort(reverse=True)
    escolhidas, usados = [], []
    for _, t, js, jm in cand:
        if all(abs(t - u) >= dur_s for u in usados):
            escolhidas.append((t, js, jm))
            usados.append(t)
        if len(escolhidas) >= n_janelas:
            break
    return sorted(escolhidas)


def atraso_alinhamento(mic, sysc, maxlag_s):
    """Deslocamento que `_alinhar_canais` aplica, e se ele saturou a busca."""
    from scipy.signal import correlate
    _, ref_al = _alinhar_canais(mic, sysc, SR, maxlag_s=maxlag_s)
    n = min(len(ref_al), len(sysc))
    c = correlate(ref_al[:n].astype(np.float64), sysc[:n].astype(np.float64),
                  mode="full", method="fft")
    d = int(np.arange(-n + 1, n)[int(np.argmax(np.abs(c)))])
    return d, abs(d) >= int(maxlag_s * SR) - 1


def rotula(mic, sysc):
    """Blocos far-end-only e near-end-only, com o sistema ALINHADO ao mic."""
    _, ref_al = _alinhar_canais(mic, sysc, SR)
    n = min(len(mic), len(ref_al))
    nb = n // B
    bm = np.array([rms(mic[i * B:(i + 1) * B]) for i in range(nb)])
    bs = np.array([rms(ref_al[i * B:(i + 1) * B]) for i in range(nb)])
    return (bs >= LIM) & (bm < LIM * 3), (bm >= LIM) & (bs < LIM)


def mede(mic, sysc, so_sys, so_mic, **kw):
    limpo = cancel_echo(mic.astype(np.float32), sysc.astype(np.float32), **kw)

    def dif(mask):
        idx = [j for j in np.flatnonzero(mask) if (j + 1) * B <= len(limpo)]
        if len(idx) < 5:
            return None
        antes = np.mean([rms(mic[j * B:(j + 1) * B]) for j in idx])
        dep = np.mean([rms(limpo[j * B:(j + 1) * B]) for j in idx])
        return db(antes) - db(dep)

    return dif(so_sys), dif(so_mic)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    path = Path(argv[1])
    n_janelas = int(argv[2]) if len(argv) > 2 else 6
    dur = float(argv[3]) if len(argv) > 3 else 15.0

    bm, bs = perfil(path)
    print(f"[{path.name}] {len(bm) * 0.1 / 60:.1f} min | "
          f"mic {db(np.sqrt(np.mean(bm ** 2))):.1f} dBFS | "
          f"sistema {db(np.sqrt(np.mean(bs ** 2))):.1f} dBFS")
    janelas = escolhe_janelas(bm, bs, n_janelas, dur)
    if not janelas:
        print("  ! nenhuma janela com os dois tipos de trecho — medida impossivel")
        return 2

    print("\n                          maxlag 0.5 s (vigente)  maxlag 0.2 s (antigo)")
    print("janela  atraso so_sys so_mic |   ERLE   dano_voz |   ERLE   dano_voz")
    erles, danos, saturou = [], [], 0
    for t, _, _ in janelas:
        mic, sysc = ler_janela(path, t, dur)
        n = min(len(mic), len(sysc))
        if n < SR:
            continue
        mic, sysc = mic[:n], sysc[:n]
        try:
            so_sys, so_mic = rotula(mic, sysc)
            d, sat = atraso_alinhamento(mic, sysc, 0.5)
            erle, dano = mede(mic, sysc, so_sys, so_mic)
            erle0, dano0 = mede(mic, sysc, so_sys, so_mic, maxlag_s=0.2)
        except MemoryError:
            print(f"{t/60:6.1f}m  (sem memoria para esta janela — reduza a duracao)")
            continue
        saturou += int(sat)
        print(f"{t/60:6.1f}m {d:6d} {int(so_sys.sum()):6d} {int(so_mic.sum()):6d} | "
              f"{fmt(erle)}  {fmt(dano)} | {fmt(erle0)}  {fmt(dano0)}"
              f"{'  <- busca saturada' if sat else ''}")
        if erle is not None:
            erles.append(erle)
        if dano is not None:
            danos.append(dano)

    if not erles or not danos:
        print("\n  ! medida inconclusiva")
        return 2
    erle_med, dano_max = float(np.median(erles)), float(np.max(danos))
    print(f"\nERLE mediano      {erle_med:+.1f} dB   (gate: >= {GATE_ERLE:+.1f})")
    print(f"dano na voz PIOR  {dano_max:+.1f} dB   (gate: <= {GATE_DANO:+.1f})")
    print(f"janelas com a busca de atraso saturada: {saturou} (gate: 0)")
    ok = (erle_med >= GATE_ERLE) and (dano_max <= GATE_DANO) and saturou == 0
    print(f"\nGATE: {'PASSOU' if ok else 'REPROVOU'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
