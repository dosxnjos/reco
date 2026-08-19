"""Gravacao REAL com audio tocando: confere se os canais saem alinhados.

E a prova ponta a ponta da Fase 1 (roadmap 2026-08-19-melhoria-antieco-de-verdade).
Sem audio tocando pelos alto-falantes nao existe conteudo comum entre mic e
loopback, e nao ha o que medir — por isso este teste TOCA som na maquina.

    python tools/test_gravacao_alinhada.py [segundos] [arquivo_de_fala.mp3] [--guardar]

Toca fala (por padrao, o canal do sistema da gravacao mais recente do Reco) pelo
alto-falante padrao enquanto grava pelos dispositivos padrao, e no fim mede o
atraso entre os canais do MP3 gerado.

Gate: |atraso residual| < 160 amostras @16 kHz (10 ms). Antes da Fase 1 o mesmo
arquivo dava 3241 amostras (203 ms), e outra gravacao dava -6385 (-399 ms).

Apaga o MP3 no fim (passe --guardar para manter).

Nada de emoji nos prints: o console desta maquina e cp1252 e um caractere fora
dele derruba o script com UnicodeEncodeError no meio do teste.
"""
import sys
import threading
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import av                                                          # noqa: E402
import soundcard as sc                                             # noqa: E402

import reco                                                        # noqa: E402

SECS = 50.0
if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
    try:
        SECS = float(sys.argv[1])
    except ValueError:
        pass
GUARDAR = "--guardar" in sys.argv
OUT = Path(__file__).resolve().parents[1] / "temp"
OUT.mkdir(exist_ok=True)
GATE = 160          # amostras @16 kHz = 10 ms


def fala_para_tocar(dur_s):
    """Fala real: o canal do sistema (R) de uma gravacao existente do Reco."""
    fonte = None
    for arg in sys.argv[1:]:
        if arg.lower().endswith((".mp3", ".wav", ".m4a")):
            fonte = Path(arg)
            break
    if fonte is None:
        pasta = Path.home() / "Documents" / "Reco"
        cands = sorted(pasta.glob("gravacao_reco_*.mp3"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        if not cands:
            return None, None
        fonte = cands[0]
    n_alvo = int(dur_s * 48000)
    blocos, got = [], 0
    with av.open(str(fonte)) as cont:
        rs = av.audio.resampler.AudioResampler(format="fltp", layout="stereo", rate=48000)
        cont.seek(int(300 * av.time_base))      # 5 min adentro: ja ha conversa
        for frame in cont.decode(audio=0):
            for r_ in rs.resample(frame):
                a = r_.to_ndarray().astype(np.float32)
                blocos.append(a[1] if a.shape[0] > 1 else a[0])     # canal do sistema
                got += a.shape[1]
            if got >= n_alvo:
                break
    if not blocos:
        return None, None
    x = np.concatenate(blocos)[:n_alvo]
    pico = float(np.max(np.abs(x))) or 1.0
    return (x / pico * 0.5).astype(np.float32), fonte     # -6 dBFS: audivel, sem clip


def toca(x, parar):
    spk = sc.default_speaker()
    with spk.player(samplerate=48000, channels=1, blocksize=2048) as pl:
        i = 0
        while not parar.is_set() and i < len(x):
            pl.play(x[i:i + 4800])
            i += 4800


def atraso_do_mp3(path, jan_s=15.0):
    """Atraso residual POR JANELA, e as janelas com correlacao confiavel.

    Medir o arquivo inteiro de uma vez borra o resultado quando houve correcao no
    meio (trechos com atrasos diferentes viram um pico intermediario). O que
    interessa e o pior trecho: e ele que se ouve como eco.
    """
    with av.open(str(path)) as cont:
        rs = av.audio.resampler.AudioResampler(format="fltp", layout="stereo", rate=16000)
        m, s = [], []
        for frame in cont.decode(audio=0):
            for r_ in rs.resample(frame):
                a = r_.to_ndarray().astype(np.float32)
                m.append(a[0])
                s.append(a[1])
    if not m:
        return None, []
    mic, sistema = np.concatenate(m), np.concatenate(s)
    n = min(len(mic), len(sistema))
    mic, sistema = mic[:n], sistema[:n]
    passo = int(jan_s * 16000)
    saida = []
    for i in range(0, n, passo):
        j = min(n, i + passo)
        if j - i < 5 * 16000:
            break
        d, q = reco.estimar_offset(mic[i:j], sistema[i:j], sr=16000)
        saida.append((i / 16000.0, d, q))
    return saida, [x for x in saida if x[2] >= reco.ALIGN_Q_MIN]


def main():
    x, fonte = fala_para_tocar(SECS + 5)
    if x is None:
        print("sem arquivo de fala para tocar — passe um .mp3 como argumento")
        return 2
    mics, spks = reco.list_capture_devices()
    mic_id, sys_id = reco.default_mic_id(), reco.default_speaker_id()
    print(f"fala      : {fonte.name} ({len(x)/48000:.0f}s, canal do sistema, -6 dBFS)")
    print(f"mic       : {reco.name_for_id(mics, mic_id)}")
    print(f"sys       : {reco.name_for_id(spks, sys_id)}")
    print(f"\n*** vai TOCAR som pelo alto-falante por ~{SECS:.0f}s "
          f"- e o que gera o eco ***\n")

    r = reco.DualRecorder()
    r.start(mic_id, sys_id, on_error=lambda k, m: print(f"  [erro {k}] {m}"),
            out_sr=reco.OUT_SR, out_channels=reco.OUT_CH, bitrate=reco.MP3_BR,
            out_dir=OUT)
    if not r.recording:
        print("nao iniciou")
        return 1

    parar = threading.Event()
    threading.Thread(target=toca, args=(x, parar), daemon=True).start()
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < SECS:
        time.sleep(1.0)
        resto = SECS - (time.perf_counter() - t0)
        print(f"  gravando... {resto:4.0f}s   align={r.alinhamento()['estado']}",
              end="\r")
    parar.set()
    path = r.stop()
    print(" " * 60, end="\r")

    info = r.alinhamento()
    print(f"\narquivo    : {path.name} ({path.stat().st_size/1024:.0f} KB)")
    print(f"alinhamento: estado={info['estado']} offset={info['offset_amostras']:+d} "
          f"amostras ({info['offset_ms']:+.0f} ms) | deriva: "
          f"{info['ajustes_deriva']} ajuste(s), {info['deriva_amostras']:+d} amostras")
    todas, confiaveis = atraso_do_mp3(path)
    if todas is None:
        print("MP3 vazio - nada a medir")
        return 1
    print("residual por janela de 15 s:")
    for t, d, q in todas:
        marca = "" if q >= reco.ALIGN_Q_MIN else "   (q baixo, ignorada)"
        print(f"  {t:5.0f}s  {d:+6d} amostras  ({d/16000*1000:+6.1f} ms)  "
              f"q={q:.3f}{marca}")
    if not GUARDAR:
        path.unlink(missing_ok=True)
    if not confiaveis:
        print("")
        print("! nenhuma janela com correlacao confiavel: alto-falante mudo? "
              "medida inconclusiva")
        return 2
    pior = max(confiaveis, key=lambda x: abs(x[1]))
    print("")
    print(f"pior janela: {pior[1]:+d} amostras ({pior[1]/16000*1000:+.1f} ms) "
          f"em {pior[0]:.0f}s")
    passou = abs(pior[1]) < GATE
    print(f"\nGATE (|atraso| < {GATE} amostras = 10 ms): "
          f"{'PASSOU' if passou else 'REPROVOU'}")
    return 0 if passou else 1


if __name__ == "__main__":
    sys.exit(main())
