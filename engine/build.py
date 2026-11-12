"""Congela o motor com PyInstaller (onedir) -> engine/dist/reco-engine/reco-engine.exe, e o smoke dele.

    python engine/build.py            # build + smoke
    python engine/build.py --smoke    # só o smoke de um build existente

Saída em engine/dist e engine/build (caminhos absolutos daqui: nunca o ./dist da raiz, onde mora o
Reco.exe do app velho, que pode estar aberto). Molde: lacre/engine/build.py.

O smoke sobe o exe como o casco (CREATE_NO_WINDOW, pipes) três vezes e mede spawn → `hello` e
spawn → `ready`; na última rodada espera o aquecimento, mede o `devices.list` e a memória do processo,
manda `shutdown` e confere o exit 0. Só leitura: nada grava o config.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIST = HERE / "dist"
WORK = HERE / "build"
NAME = "reco-engine"
EXE = DIST / NAME / f"{NAME}.exe"
SPEC = HERE / "reco-engine.spec"
CREATE_NO_WINDOW = 0x08000000


def build() -> None:
    import PyInstaller.__main__  # noqa: PLC0415  (só o build precisa)

    PyInstaller.__main__.run([str(SPEC), "--noconfirm", "--clean", "--log-level", "WARN",
                              "--distpath", str(DIST), "--workpath", str(WORK)])
    if not EXE.exists():
        raise SystemExit(f"build falhou: {EXE} não existe")
    size = sum(p.stat().st_size for p in (DIST / NAME).rglob("*") if p.is_file())
    print(f"built {EXE} ({size / 1e6:.0f} MB in {DIST / NAME})")


class _Proc:
    def __init__(self, cmd: list) -> None:
        self.t0 = time.perf_counter()
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        self.err: list = []
        threading.Thread(target=self._drain, daemon=True).start()

    def _drain(self) -> None:
        for raw in iter(self.p.stderr.readline, b""):
            self.err.append(raw.decode("utf-8", "replace"))

    def send(self, rid: str, cmd: str) -> None:
        self.p.stdin.write(json.dumps({"v": 1, "id": rid, "cmd": cmd, "args": {}}).encode() + b"\n")
        self.p.stdin.flush()

    def until(self, pred) -> tuple:
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise SystemExit(f"o motor fechou o stdout; stderr: {''.join(self.err[-5:])}")
            msg = json.loads(line)
            if pred(msg):
                return msg, time.perf_counter() - self.t0

    def memory_mb(self) -> str:
        r = subprocess.run(["tasklist", "/fi", f"PID eq {self.p.pid}", "/fo", "csv", "/nh"],
                           capture_output=True, text=True, check=False)
        row = next(csv.reader(io.StringIO(r.stdout)), None)
        return row[4] if row and len(row) > 4 else "?"

    def wait_warm(self, timeout: float = 60.0) -> None:
        deadline = time.perf_counter() + timeout
        while time.perf_counter() < deadline and not any("aquecimento pronto" in s for s in self.err):
            time.sleep(0.1)


def _last_run(pr: _Proc) -> tuple:
    pr.wait_warm()
    t1 = time.perf_counter()
    pr.send("d", "devices.list")
    dev, _ = pr.until(lambda m: m.get("id") == "d")
    n = (len(dev["data"]["microphone"]["devs"]), len(dev["data"]["speaker"]["devs"])) if dev["ok"] else dev
    # só ASCII no que o app/build.ps1 julga (o stdout redirecionado sai em cp1252)
    return dev["ok"], f"; devices ok={dev['ok']} {n} em {time.perf_counter() - t1:.2f} s; memoria {pr.memory_mb()}"


def _ready_txt(ready: dict) -> tuple:
    """O `ready` responde depois do `import reco`: com `error`, o motor sobe mas todo comando dá `unavailable`."""
    erro = ready.get("error")
    return not erro, ("ready ok=True" if not erro else f"ready ok=False error={erro!r}")


def smoke(cmd: list, runs: int = 3) -> bool:
    """Imprime uma linha por rodada e devolve se tudo passou: hello, ready sem erro, devices (última) e shutdown."""
    tudo_ok = True
    for i in range(runs):
        pr = _Proc(cmd)
        pr.send("h", "hello")
        hello, t_hello = pr.until(lambda m: m.get("id") == "h")
        ready, t_ready = pr.until(lambda m: m.get("event") == "ready")
        ready_ok, ready_txt = _ready_txt(ready)
        dev_ok, extra = _last_run(pr) if i == runs - 1 and ready_ok else (True, "")
        pr.send("s", "shutdown")
        bye, _ = pr.until(lambda m: m.get("id") == "s")
        code = pr.p.wait(timeout=30)
        print(f"run {i + 1}: hello ok={hello['ok']} em {t_hello:.2f} s; {ready_txt} em {t_ready:.2f} s"
              f"{extra}; shutdown ok={bye['ok']} exit={code}")
        tudo_ok = tudo_ok and hello["ok"] and ready_ok and dev_ok and bye["ok"] and code == 0
    return tudo_ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="só o smoke de um build existente")
    ap.add_argument("--motor", nargs="+", help="smoke contra outro comando (prova do julgamento com motor falso)")
    a = ap.parse_args()
    if not a.smoke and not a.motor:
        build()
    ok = smoke(a.motor or [str(EXE)])
    if not ok:
        print("SMOKE REPROVADO: hello, ready sem erro, devices.list e shutdown precisam passar")
    sys.exit(0 if ok else 1)
