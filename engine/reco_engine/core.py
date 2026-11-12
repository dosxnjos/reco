"""Estado compartilhado do motor: saída do protocolo, estado da gravação, transcritor único.

Um `Core` por processo. Os comandos recebem `(core, rid, args)` e devolvem o `data` da resposta, ou
levantam `EngineError`. Nada aqui importa `reco` no topo (o `hello` responde antes do import, F2-D3).
"""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any
from collections.abc import Callable

from .errors import EngineError

PROTOCOL_VERSION = 1
REC_STATES = ("idle", "recording", "paused", "stopping", "stopped")


class Core:
    def __init__(self, send: Callable[[dict], None]) -> None:
        self._send = send
        self.t0 = time.monotonic()
        self.lock = threading.RLock()
        self.stop_ev = threading.Event()        # shutdown ou EOF no stdin
        self.stop_reason = ""
        # gravação (recording.py)
        self.rec_state = "idle"
        self.recorder = None                    # reco.DualRecorder, criado no 1º rec.start
        self.rec_mode: str | None = None     # "rec" | "nota"
        self.rec_path: Path | None = None    # arquivo que está sendo gravado
        self.live = None                        # reco.LiveTranscriber durante a gravação
        self.live_was_on = False
        self.live_active = False                # ao vivo ligado: nenhuma outra transcrição entra
        self.live_gen = 0                       # sobe a cada ao vivo ligado: a soltura atrasada não apaga o novo
        self.early_errors: list = []            # erros de canal antes do estado `recording`
        self.start_ts = 0.0
        self.accum = 0.0
        self.stopped_ev = threading.Event()     # o rec.stop terminou de fechar o arquivo
        self.stopped_ev.set()
        self.last_rec: Path | None = None
        self.last_auto: str | None = None
        # transcrição (transcribe.py): um `make_transcriber()` por processo, como o App
        self._tr = None
        self.transcribing = False
        self.cancel_pending = False
        # extras
        self.extracting = False
        self.resumindo = False

    # ------------------------------------------------------------ saída
    def send(self, msg: dict) -> None:
        self._send({"v": PROTOCOL_VERSION, **msg})

    def emit(self, event: str, rid: Any = None, **fields: Any) -> None:
        msg: dict = {"event": event}
        if rid is not None:
            msg["id"] = rid
        msg.update(fields)
        self.send(msg)

    def request_stop(self, reason: str) -> None:
        if not self.stop_ev.is_set():
            self.stop_reason = reason
            self.stop_ev.set()

    # ------------------------------------------------------------ gravação
    def elapsed(self) -> int:
        """Segundos gravados; o tempo pausado não conta (como `App._elapsed`)."""
        run = (time.monotonic() - self.start_ts) if self.rec_state == "recording" else 0.0
        return int(self.accum + run)

    def set_state(self, state: str) -> None:
        with self.lock:
            self.rec_state = state
        self.emit_state()

    def emit_state(self) -> None:
        """Emite o estado atual. Quem troca o estado junto com a checagem (dentro do lock) chama isto
        depois de soltar o lock: nada escreve no stdout segurando o `core.lock`."""
        with self.lock:
            state, elapsed = self.rec_state, self.elapsed()
        self.emit("state", state=state, elapsed_s=elapsed)

    # ------------------------------------------------------------ transcrição
    def transcriber(self, reco):
        """O transcritor único do processo, compartilhado com o ao vivo e as passadas finais."""
        with self.lock:
            if self._tr is None:
                self._tr = reco.make_transcriber()
            return self._tr

    def claim_transcription(self) -> None:
        """Um `pipe.generate` por vez: recusa com `busy` se já há transcrição (ou troca de modelo)."""
        with self.lock:
            if self.transcribing:
                raise EngineError("busy", "já há uma transcrição em andamento")
            if self.live_active:      # o ao vivo usa o mesmo pipeline até o dreno do rec.stop
                raise EngineError("busy", "transcrição ao vivo em andamento")
            self.transcribing = True
            self.cancel_pending = False

    def release_transcription(self) -> None:
        with self.lock:
            self.transcribing = False
            self.cancel_pending = False

    def cancel_transcription(self) -> bool:
        """Cancelamento pegajoso: o `OVTranscriber.transcribe()` limpa o próprio sinal ao começar, então
        um cancel que chega entre o `claim` e o `transcribe()` é reaplicado depois (transcribe.py)."""
        with self.lock:
            tr, busy = self._tr, self.transcribing
            if busy:
                self.cancel_pending = True
        if busy and tr is not None:
            tr.cancel()
            return True
        return False


def claim_flag(core: Core, attr: str, what: str) -> None:
    """Liga um sinalizador de trabalho único (`extracting`, `resumindo`) ou recusa com `busy`."""
    with core.lock:
        if getattr(core, attr):
            raise EngineError("busy", f"já há {what} em andamento")
        setattr(core, attr, True)


def release_flag(core: Core, attr: str) -> None:
    with core.lock:
        setattr(core, attr, False)


def arg_path(args: dict, key: str = "path") -> Path:
    v = args.get(key)
    if not isinstance(v, str) or not v.strip():
        raise EngineError("bad_args", f"{key} (texto) é obrigatório")
    return Path(v)
