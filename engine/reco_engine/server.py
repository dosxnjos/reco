"""Servidor JSON Lines (docs/PROTOCOL.md): um pedido por linha no stdin; respostas e eventos no stdout.

Concorrência (F2-D1): uma thread lê o stdin, cada pedido roda numa thread própria e a escrita no
stdout passa por um lock. O stdout do processo é isolado no descritor (F2-D7): o canal do protocolo é
um `os.dup(1)`, e o fd 1 passa a apontar para o stderr, para que nem `print` do `reco.py` nem escrita
nativa (OpenVINO, ffmpeg) quebrem o parse do casco.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import threading
from typing import Any
from collections.abc import Callable

from . import (__version__, boot, conclude, config_cmd, devices, extras, library, modelo,
               recording, transcribe)
from .core import PROTOCOL_VERSION, Core
from .errors import EngineError, short

log = logging.getLogger("reco_engine.server")

# O casco mata o motor 8 s depois do `shutdown`: fechar o MP3 tem de caber nisso.
EXIT_SAVE_TIMEOUT_S = 6.0


def cmd_hello(core: Core, rid, args) -> dict:
    import time  # noqa: PLC0415
    return {"engine_version": __version__, "reco_version": boot.reco_version(),
            "protocol": PROTOCOL_VERSION, "platform": sys.platform, "ready": boot.is_ready(),
            "uptime_s": round(time.monotonic() - core.t0, 3)}


def cmd_shutdown(core: Core, rid, args) -> dict:
    return {}   # o encerramento acontece depois que a resposta sai (Server._run)


COMMANDS: dict[str, Callable] = {
    "hello": cmd_hello,
    "shutdown": cmd_shutdown,
    **config_cmd.COMMANDS,
    **devices.COMMANDS,
    **recording.COMMANDS,
    **conclude.COMMANDS,
    **transcribe.COMMANDS,
    **library.COMMANDS,
    **extras.COMMANDS,
    **modelo.COMMANDS,
}


class Server:
    def __init__(self, core: Core) -> None:
        self.core = core
        self._inflight: set[str] = set()
        self._lk = threading.Lock()

    def ok(self, rid: Any, data: Any) -> None:
        self.core.send({"id": rid, "ok": True, "data": data})

    def fail(self, rid: Any, code: str, detail: str = "") -> None:
        self.core.send({"id": rid, "ok": False, "error": {"code": code, "detail": detail}})

    def handle_line(self, raw: bytes) -> None:
        text = raw.decode("utf-8", "replace").strip().lstrip("﻿")
        if not text:
            return
        try:
            req = json.loads(text)
            if not isinstance(req, dict):
                raise ValueError("o pedido não é um objeto")
        except ValueError as e:
            self.fail(None, "internal", f"linha ilegível: {short(e)}")
            return
        self._dispatch(req)

    def _dispatch(self, req: dict) -> None:
        rid, cmd, args = req.get("id"), req.get("cmd"), req.get("args") or {}
        problem = self._validate(rid, cmd, args)
        if problem:
            self.fail(rid, "internal", problem)
            return
        if self.core.stop_ev.is_set():      # encerrando: nada novo (um rec.start deixaria órfão)
            self.fail(rid, "refused", "motor encerrando")
            return
        with self._lk:
            if rid in self._inflight:
                self.fail(rid, "internal", "id repetido em andamento")
                return
            self._inflight.add(rid)
        threading.Thread(target=self._run, args=(rid, cmd, COMMANDS[cmd], args),
                         name=f"cmd:{cmd}", daemon=True).start()

    @staticmethod
    def _validate(rid, cmd, args) -> str:
        if not isinstance(rid, str) or not rid:
            return "id tem de ser texto não vazio"
        if not isinstance(args, dict):
            return "args tem de ser objeto"
        if not isinstance(cmd, str) or cmd not in COMMANDS:
            return f"cmd desconhecido: {cmd!r}"
        return ""

    def _run(self, rid: str, cmd: str, fn: Callable, args: dict) -> None:
        try:
            self.ok(rid, fn(self.core, rid, args))
        except EngineError as e:
            self.fail(rid, e.code, e.detail)
        except Exception as e:  # noqa: BLE001
            log.exception("%s falhou", cmd)
            self.fail(rid, "internal", short(e))
        finally:
            with self._lk:
                self._inflight.discard(rid)
        if cmd == "shutdown":
            self.core.request_stop("shutdown")


def _isolate_stdin():
    """O pipe do stdin sai do fd 0 (e do STD_INPUT_HANDLE) e o fd 0 vira NUL.

    ⚠️ Medido em 11/11/2026: com uma thread presa no `readline()` do pipe, carregar DLL nativa em outra
    thread (numpy no `import reco`, openvino no aquecimento) trava até chegar a próxima linha: a
    inicialização da DLL consulta o handle padrão do stdin, e o Windows serializa I/O síncrono no
    mesmo objeto de arquivo (import de 0,4 s virou 12 a 20 s). O `dup2` da UCRT também troca o
    STD_INPUT_HANDLE, então a DLL passa a consultar o NUL. Ver docs/ARMADILHAS.md.
    """
    src = os.dup(0)
    nul = os.open(os.devnull, os.O_RDONLY)
    os.dup2(nul, 0)
    os.close(nul)
    sys.stdin = open(os.devnull, encoding="utf-8")  # noqa: SIM115  (vive o processo inteiro)
    return os.fdopen(src, "rb")


def _isolate_stdout() -> Callable[[bytes], None]:
    """Canal do protocolo = cópia do fd 1; depois o fd 1 vira o stderr (F2-D7)."""
    try:
        sys.stderr.reconfigure(encoding="utf-8")
        sys.stdout.flush()
    except Exception:  # noqa: BLE001
        pass
    out = os.fdopen(os.dup(1), "wb")
    os.dup2(2, 1)
    sys.stdout = sys.stderr
    lock = threading.Lock()

    def write(b: bytes) -> None:
        with lock:
            out.write(b)
            out.flush()
    return write


def _reader(server: Server, core: Core, inp) -> None:
    try:
        while True:
            line = inp.readline()
            if not line:
                break
            server.handle_line(line)
    except Exception as e:  # noqa: BLE001
        log.warning("leitura do stdin parou: %s", short(e))
    core.request_stop("eof")


def main() -> int:
    write = _isolate_stdout()
    inp = _isolate_stdin()
    logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    def send(msg: dict) -> None:
        line = json.dumps(msg, ensure_ascii=False, separators=(",", ":"), default=str)
        write(line.encode("utf-8") + b"\n")

    core = Core(send)
    server = Server(core)
    boot.start(core)
    threading.Thread(target=_reader, args=(server, core, inp), name="stdin-reader",
                     daemon=True).start()
    log.info("motor %s no ar (%s)", __version__, sys.platform)
    core.stop_ev.wait()
    log.info("encerrando (%s)", core.stop_reason)
    code = 0
    try:
        recording.close_for_exit(core, EXIT_SAVE_TIMEOUT_S)
    except Exception:  # noqa: BLE001
        log.exception("falha ao fechar a gravação na saída")
        code = 1
    try:
        sys.stderr.flush()
    except Exception:  # noqa: BLE001
        pass
    # Saída dura: threads nativas (OpenVINO, WASAPI) e a leitora presa no readline seguram o processo
    # (como Lacre server.py:343-350 e reco.py:5124-5128).
    os._exit(code)
