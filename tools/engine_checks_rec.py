"""Checagens que GRAVAM dos dispositivos reais: `--gravar N` (passo 6), `--eof N` (passo 7, D11) e a
gravação de 30 s pelo exe com `--saida-real` (passo 15).

Guardas, nesta ordem e antes de subir o motor ou tocar som (`guardas()`):
1. aborta se o mutex `Local\\Reco.SingleInstance` existe (app velho aberto, talvez numa reunião; D7);
2. exige `temp/bench-voz/clip10.wav` (fala, fora do git), que toca em laço no alto-falante padrão
   durante a gravação: o canal R tem fala sem ninguém por perto, o L tem pelo menos o ruído do mic.
"""
from __future__ import annotations

import ctypes
import json
import shutil
import sys
import threading
import time
from ctypes import wintypes
from pathlib import Path

import numpy as np
from engine_harness import RAIZ, REAL_CONFIG, Engine, check, make_home

sys.path.insert(0, str(RAIZ))
import reco  # noqa: E402  (decode_16k e soundcard no processo do teste)

MUTEX = "Local\\Reco.SingleInstance"
SYNCHRONIZE = 0x00100000
CLIP = RAIZ / "temp" / "bench-voz" / "clip10.wav"
LEVEL_MAX_HZ = 20.0


# ------------------------------------------------------------------ guardas
def app_aberto() -> bool:
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenMutexW.restype = wintypes.HANDLE
    k32.OpenMutexW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
    h = k32.OpenMutexW(SYNCHRONIZE, False, MUTEX)
    if h:
        k32.CloseHandle(h)
        return True
    return False


def guardas() -> None:
    check(not app_aberto(),
          f"o Reco está aberto (mutex {MUTEX} existe): feche-o pela bandeja (Sair) e rode de novo. "
          "Nada foi gravado nem tocado.")
    check(CLIP.is_file(), f"clipe de fala ausente: {CLIP} (temp/ fica fora do git; copie de outra "
          "máquina ou gere um .wav de 16 kHz com fala)")


class Clipe:
    """Toca o clipe em laço no alto-falante padrão (soundcard; `winsound` se o soundcard falhar)."""

    def __init__(self) -> None:
        self.dados = reco.decode_16k(CLIP)[0].astype(np.float32)
        self.parar = threading.Event()
        self.via = "soundcard"
        self._th = threading.Thread(target=self._laco, daemon=True)

    def _laco(self) -> None:
        try:
            with reco.sc.default_speaker().player(samplerate=16000, channels=1) as p:
                while not self.parar.is_set():
                    for i in range(0, len(self.dados), 8000):
                        if self.parar.is_set():
                            return
                        p.play(self.dados[i:i + 8000])
        except Exception:  # noqa: BLE001  (premissa não verificada: cai no winsound)
            import winsound
            self.via = "winsound"
            winsound.PlaySound(str(CLIP), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
            self.parar.wait()
            winsound.PlaySound(None, 0)

    def __enter__(self):
        self._th.start()
        time.sleep(1.0)
        return self

    def __exit__(self, *exc) -> None:
        self.parar.set()
        self._th.join(5)


# ------------------------------------------------------------------ arquivo
def medir(path: Path) -> dict:
    """Duração declarada (header) × decodificada, canais, taxa e RMS por canal."""
    import av
    with av.open(str(path)) as c:
        declarada = c.duration / av.time_base if c.duration else 0.0
        st = c.streams.audio[0]
        canais, taxa = st.channels, st.rate
        n = sum(f.samples for f in c.decode(st))
    lados = reco.decode_16k(path, split=True)
    rms = [float(np.sqrt(np.mean(x ** 2))) if len(x) else 0.0 for x in lados]
    return {"declarada": declarada, "decodificada": n / taxa if taxa else 0.0, "canais": canais,
            "taxa": taxa, "rms": rms}


def _envelope(x: np.ndarray, quadro: int = 1600) -> np.ndarray:
    """RMS por quadro de 100 ms a 16 kHz."""
    n = len(x) // quadro
    return np.sqrt(np.mean(x[:n * quadro].reshape(n, quadro) ** 2, axis=1)) if n else np.zeros(1)


def _pearson(a: np.ndarray, b: np.ndarray) -> float:
    a, b = a - a.mean(), b - b.mean()
    den = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b)) / den if den else 0.0


def lados(path: Path) -> tuple:
    """Maior correlação do envelope do clipe (em laço) com o de L e o de R, em qualquer atraso.

    O clipe só sai no alto-falante: R (sistema, loopback) segue o envelope dele; L (mic) só pega o
    que vaza pela sala. Lados trocados dão L alto e R baixo (Fase 2, passo 15: lados por dado)."""
    mic, sis = reco.decode_16k(path, split=True)
    clip = reco.decode_16k(CLIP)[0].astype(np.float32)
    ref = _envelope(np.tile(clip, len(sis) // max(len(clip), 1) + 2))
    corr = []
    for lado in (mic, sis):
        e = _envelope(lado)
        passos = range(0, max(len(ref) - len(e), 0) + 1)
        corr.append(max((_pearson(e, ref[k:k + len(e)]) for k in passos), default=0.0))
    return corr[0], corr[1]


def mais_novo(pasta: Path) -> Path:
    mp3s = sorted(pasta.glob("gravacao_reco_*.mp3"), key=lambda p: p.stat().st_mtime)
    check(mp3s, f"nenhuma gravação em {pasta}")
    return mp3s[-1]


def pasta_real() -> str:
    """`output_dir` do config real (só leitura) ou `Documents\\Reco` do usuário."""
    try:
        cfg = json.loads(REAL_CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cfg = {}
    return cfg.get("output_dir") or str(REAL_CONFIG.parent / "Documents" / "Reco")


# ------------------------------------------------------------------ --gravar
def _taxas(eng: Engine, start: int) -> tuple:
    st = eng.events("state", start)
    t_rec = next(t for t, m in st if m["state"] == "recording")
    t_stop = next(t for t, m in st if m["state"] == "stopping")
    janela = max(t_stop - t_rec, 1e-3)
    n_level = sum(1 for t, _ in eng.events("level", start) if t_rec <= t <= t_stop)
    n_timer = sum(1 for t, _ in eng.events("timer", start) if t_rec <= t <= t_stop)
    return n_level / janela, n_timer / janela


def gravar(eng: Engine, segundos: float, mode: str = "rec") -> dict:
    start = eng.mark()
    ini = eng.ok("rec.start", {"mode": mode}, timeout=30)
    time.sleep(segundos)
    fim = eng.ok("rec.stop", timeout=60)
    return {"start": start, "ini": ini, "fim": fim}


def _conferir_gravacao(eng: Engine, segundos: float, g: dict) -> str:
    m = medir(Path(g["fim"]["path"]))
    check(abs(m["declarada"] - segundos) <= 0.5, f"duração {m['declarada']:.2f} s fora de {segundos}±0,5")
    check(abs(m["declarada"] - m["decodificada"]) <= 1.0,
          f"header mente: declarada {m['declarada']:.2f} × decodificada {m['decodificada']:.2f}")
    check(m["canais"] == 2 and m["taxa"] == 16000, f"formato: {m['canais']} canais, {m['taxa']} Hz")
    check(m["rms"][0] > 0 and m["rms"][1] > 1e-4, f"RMS L/R: {m['rms']}")
    lv, tm = _taxas(eng, g["start"])
    check(lv <= LEVEL_MAX_HZ, f"level a {lv:.1f}/s (teto {LEVEL_MAX_HZ})")
    check(0.5 <= tm <= 1.5, f"timer a {tm:.2f}/s")
    return (f"{m['declarada']:.1f} s (decodificada {m['decodificada']:.1f}), 2 canais, 16000 Hz, "
            f"level {lv:.1f}/s, timer {tm:.2f}/s, L e R com sinal (RMS {m['rms'][0]:.4f}/{m['rms'][1]:.4f})")


def run_gravar(segundos: float, exe: str | None, saida_real: bool) -> None:
    seed = {"_migracao": 2, "live": False}
    if saida_real:
        seed["output_dir"] = pasta_real()
    home = make_home(seed)
    eng = Engine(home, exe)
    try:
        eng.wait_ready(60)
        with Clipe() as clipe:
            g = gravar(eng, segundos)
        resumo = _conferir_gravacao(eng, segundos, g)
        check(eng.shutdown(10) == 0, "exit != 0")
        eng.assert_clean_stdout()
    finally:
        eng.kill()
    print(f"OK gravação: {resumo} (clipe via {clipe.via})")
    if segundos >= 10:
        c_l, c_r = lados(Path(g["fim"]["path"]))
        check(c_r >= 0.5 and c_r > c_l, f"lados: clipe×R {c_r:.2f}, clipe×L {c_l:.2f} (R devia seguir o clipe)")
        print(f"OK lados: clipe×R {c_r:.2f} > clipe×L {c_l:.2f} (voz do PC no canal direito)")
    if saida_real:
        print(f"PARA OUVIR (Gabriel): {g['fim']['path']}")
    else:
        shutil.rmtree(home, ignore_errors=True)


# ------------------------------------------------------------------ --eof (D11)
def _caso_saida(segundos: float, exe: str | None, por_shutdown: bool) -> str:
    home = make_home({"_migracao": 2, "live": False})
    eng = Engine(home, exe)
    try:
        eng.wait_ready(60)
        with Clipe():
            eng.ok("rec.start", {"mode": "rec"}, timeout=30)
            time.sleep(segundos)
            t0 = time.perf_counter()
            if por_shutdown:
                eng.ok("shutdown", timeout=8)
            else:
                eng.close_stdin()
            code = eng.wait_exit(8)
            saiu = time.perf_counter() - t0
        check(code is not None, "o motor não saiu em 8 s")
    finally:
        eng.kill()
    m = medir(mais_novo(home / "Documents" / "Reco"))
    check(abs(m["declarada"] - m["decodificada"]) <= 1.0,
          f"header sem a contagem: declarada {m['declarada']:.2f} × decodificada {m['decodificada']:.2f}")
    check(abs(m["decodificada"] - segundos) <= 1.0, f"decodificada {m['decodificada']:.2f} fora de {segundos}±1")
    shutil.rmtree(home, ignore_errors=True)
    return f"declarada {m['declarada']:.1f} s, decodificada {m['decodificada']:.1f} s, saiu em {saiu:.1f} s"


def run_eof(segundos: float, exe: str | None) -> None:
    eof = _caso_saida(segundos, exe, por_shutdown=False)
    sd = _caso_saida(segundos, exe, por_shutdown=True)
    print(f"OK eof: {eof}; OK shutdown no meio: {sd}")
