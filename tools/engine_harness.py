"""Cliente do motor para `tools/test_engine_protocol.py`: sobe o motor como o casco sobe, lê o stdout em
JSON Lines, drena o stderr numa thread (senão o pipe enche e trava, Lacre engine.rs:315) e espera
respostas e eventos. Também isola o config: `USERPROFILE` temporário e a guarda do config real.

Todos os caminhos saem de `__file__`: uma cópia do repo testa a si mesma.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ENGINE_DIR = RAIZ / "engine"
CREATE_NO_WINDOW = 0x08000000
REAL_CONFIG = Path(os.environ.get("USERPROFILE") or Path.home()) / ".reco_config.json"


class Falha(Exception):
    """Checagem reprovada: o teste imprime `FALHOU: <motivo>` e sai com 1."""


def check(cond, msg: str) -> None:
    if not cond:
        raise Falha(msg)


def sha256(p: Path) -> str | None:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


class RealConfigGuard:
    """Guarda os bytes do `~/.reco_config.json` real antes de subir qualquer filho e confere no fim."""

    def __init__(self) -> None:
        self.before = sha256(REAL_CONFIG)

    def intact(self) -> bool:
        return sha256(REAL_CONFIG) == self.before


def make_home(seed: dict | None = None, base: Path | None = None) -> Path:
    """Pasta temporária que faz o papel de `%USERPROFILE%` do motor (config e `Documents\\Reco`)."""
    home = Path(tempfile.mkdtemp(prefix="reco_engine_", dir=base))
    (home / "Documents" / "Reco").mkdir(parents=True)
    if seed is not None:
        write_config(home, seed)
    return home


def write_config(home: Path, cfg: dict) -> None:
    (home / ".reco_config.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False),
                                            encoding="utf-8")


def read_config(home: Path) -> dict:
    return json.loads((home / ".reco_config.json").read_text(encoding="utf-8"))


def child_env(home: Path, path_env: str | None = None, extra: dict | None = None) -> dict:
    """Ambiente do motor de teste; em `extra`, valor `None` tira a variável (ex.: `HF_HUB_OFFLINE`)."""
    env = dict(os.environ)
    env.update(PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8", PYTHONUTF8="1", USERPROFILE=str(home))
    if path_env is not None:
        env["PATH"] = path_env
    for k, v in (extra or {}).items():
        if v is None:
            env.pop(k, None)
        else:
            env[k] = v
    return env


def engine_cmd(exe: str | None) -> list:
    return [str(Path(exe).resolve())] if exe else [sys.executable, "-m", "reco_engine"]


class Engine:
    def __init__(self, home: Path, exe: str | None = None, path_env: str | None = None,
                 env_extra: dict | None = None) -> None:
        self.t0 = time.perf_counter()
        self.p = subprocess.Popen(engine_cmd(exe), cwd=str(ENGINE_DIR), stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  creationflags=CREATE_NO_WINDOW,
                                  env=child_env(home, path_env, env_extra))
        self.msgs: list = []           # (t, msg) de tudo que veio no stdout
        self.bad: list = []            # linhas do stdout que não são JSON (reprova sempre)
        self.stderr: list = []
        self.cv = threading.Condition()
        self._n = 0
        threading.Thread(target=self._read_out, daemon=True).start()
        threading.Thread(target=self._read_err, daemon=True).start()

    # ------------------------------------------------------------ leitura
    def _read_out(self) -> None:
        for raw in iter(self.p.stdout.readline, b""):
            try:
                msg = json.loads(raw.decode("utf-8"))
            except ValueError:
                self.bad.append(raw[:200])
                continue
            with self.cv:
                self.msgs.append((time.perf_counter(), msg))
                self.cv.notify_all()

    def _read_err(self) -> None:
        for raw in iter(self.p.stderr.readline, b""):
            self.stderr.append(raw.decode("utf-8", "replace").rstrip())

    # ------------------------------------------------------------ escrita
    def send_raw(self, data: bytes) -> None:
        self.p.stdin.write(data)
        self.p.stdin.flush()

    def send(self, cmd: str, args: dict | None = None, rid=None):
        if rid is None:
            self._n += 1
            rid = f"t{self._n}"
        line = json.dumps({"v": 1, "id": rid, "cmd": cmd, "args": args or {}}, ensure_ascii=False)
        self.send_raw(line.encode("utf-8") + b"\n")
        return rid

    # ------------------------------------------------------------ espera
    def mark(self) -> int:
        with self.cv:
            return len(self.msgs)

    def wait_for(self, pred, timeout: float, start: int = 0):
        deadline = time.perf_counter() + timeout
        i = start
        with self.cv:
            while True:
                while i < len(self.msgs):
                    if pred(self.msgs[i][1]):
                        return self.msgs[i][1]
                    i += 1
                left = deadline - time.perf_counter()
                if left <= 0 or self.p.poll() is not None and i >= len(self.msgs):
                    return None
                self.cv.wait(min(left, 0.2))

    def response(self, rid, timeout: float = 60.0, start: int = 0):
        msg = self.wait_for(lambda m: m.get("id") == rid and "ok" in m, timeout, start)
        check(msg is not None, f"sem resposta para {rid} em {timeout:.0f} s; stderr: {self.tail()}")
        return msg

    def request(self, cmd: str, args: dict | None = None, timeout: float = 60.0, rid=None):
        start = self.mark()
        rid = self.send(cmd, args, rid)
        return self.response(rid, timeout, start)

    def ok(self, cmd: str, args: dict | None = None, timeout: float = 60.0):
        r = self.request(cmd, args, timeout)
        check(r["ok"], f"{cmd} falhou: {r.get('error')}")
        return r["data"]

    def error(self, cmd: str, args: dict | None = None, timeout: float = 60.0) -> str:
        r = self.request(cmd, args, timeout)
        check(not r["ok"], f"{cmd} deveria falhar e respondeu ok: {r.get('data')}")
        return r["error"]["code"]

    def event(self, name: str, timeout: float, start: int = 0, rid=None):
        return self.wait_for(lambda m: m.get("event") == name and (rid is None or m.get("id") == rid),
                             timeout, start)

    def events(self, name: str, start: int = 0, end: int | None = None, rid=None) -> list:
        with self.cv:
            sel = self.msgs[start:end]
        return [(t, m) for t, m in sel if m.get("event") == name and (rid is None or m.get("id") == rid)]

    def wait_ready(self, timeout: float = 60.0):
        ev = self.event("ready", timeout)
        check(ev is not None, f"evento ready não chegou em {timeout:.0f} s; stderr: {self.tail()}")
        check("error" not in ev, f"ready com erro: {ev.get('error')}")
        return ev

    # ------------------------------------------------------------ fim
    def close_stdin(self) -> None:
        try:
            self.p.stdin.close()
        except OSError:
            pass

    def wait_exit(self, timeout: float):
        try:
            return self.p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            return None

    def shutdown(self, timeout: float = 10.0) -> int:
        self.ok("shutdown", timeout=timeout)
        code = self.wait_exit(timeout)
        check(code is not None, f"o motor não saiu em {timeout:.0f} s após shutdown")
        return code

    def kill(self) -> None:
        if self.p.poll() is None:
            self.p.kill()

    def wait_stderr(self, needle: str, timeout: float) -> str | None:
        deadline = time.perf_counter() + timeout
        while time.perf_counter() < deadline:
            hit = next((s for s in list(self.stderr) if needle in s), None)
            if hit is not None:
                return hit
            time.sleep(0.05)
        return None

    def tail(self, n: int = 8) -> str:
        return " | ".join(self.stderr[-n:])

    def assert_clean_stdout(self) -> None:
        check(not self.bad, f"stdout com linha que não é JSON: {self.bad[:2]}")
