"""Import do `reco` em segundo plano, evento `ready` e aquecimento dos imports pesados.

⚠️ A thread que faz o `import reco` NUNCA termina (medido em 11/11/2026): o `soundcard` liga o COM do
Windows na thread que o importa; se ela acaba, toda enumeração em outra thread falha com
`Error 0x800401f0` e listas vazias, sem exceção. Por isso ela importa, sinaliza e fica parada num
`Event().wait()` (daemon) enquanto o motor vive. Ver docs/ARMADILHAS.md.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

from .errors import EngineError, short

log = logging.getLogger("reco_engine.boot")

READY_TIMEOUT_S = 60.0
WARM_MODULES = ("scipy.signal", "av", "openvino", "openvino_genai")

_ready = threading.Event()
_state: dict[str, Any] = {"mod": None, "error": None, "import_s": None}


def start(core) -> None:
    threading.Thread(target=_import_thread, args=(core,), name="reco-import", daemon=True).start()


def _import_thread(core) -> None:
    t0 = time.perf_counter()
    try:
        import reco  # noqa: PLC0415  (de propósito fora do topo: hello antes do import, F2-D3)
        _state["mod"] = reco
    except BaseException as e:  # noqa: BLE001  (SystemExit/ImportError viram `unavailable`)
        _state["error"] = short(e)
        log.exception("import reco falhou")
    _state["import_s"] = round(time.perf_counter() - t0, 3)
    _ready.set()
    _announce(core)
    if _state["mod"] is not None:
        threading.Thread(target=_warm, name="warm-imports", daemon=True).start()
    threading.Event().wait()   # mantém viva a thread dona do COM do soundcard


def _announce(core) -> None:
    reco = _state["mod"]
    if reco is None:
        core.emit("ready", import_s=_state["import_s"], error=_state["error"])
        return
    has = {"sc": bool(reco.HAS_SC), "np": bool(reco.HAS_NP), "av": bool(reco.HAS_AV),
           "ov": bool(reco.HAS_OV)}
    log.info("reco importado em %.2f s", _state["import_s"])
    core.emit("ready", import_s=_state["import_s"], has=has, lang=reco.LANG,
              reco_version=reco.APP_VERSION)
    # Marca do D12 (Fase 4, passo 14): o casco anexa o stderr ao engine.log, e a medição casa esta linha.
    log.info("ready em %.2f s", _state["import_s"])


def _warm() -> None:
    """Só imports (F2-D4): nunca cria o WhisperPipeline (14,6 s e 1,35 GB num app de bandeja)."""
    import importlib  # noqa: PLC0415
    t0 = time.perf_counter()
    for mod in WARM_MODULES:
        try:
            importlib.import_module(mod)
        except Exception as e:  # noqa: BLE001
            log.warning("aquecimento: %s falhou: %s", mod, short(e))
    log.info("aquecimento pronto em %.2f s", time.perf_counter() - t0)


def is_ready() -> bool:
    return _ready.is_set() and _state["mod"] is not None


def reco_version() -> str | None:
    mod = _state["mod"]
    return mod.APP_VERSION if (_ready.is_set() and mod is not None) else None


def reco(timeout: float = READY_TIMEOUT_S):
    """O módulo `reco`, esperando o import em segundo plano (teto de 60 s, senão `unavailable`)."""
    if not _ready.wait(timeout):
        raise EngineError("unavailable", f"reco não importou em {timeout:.0f} s")
    if _state["mod"] is None:
        raise EngineError("unavailable", f"import reco falhou: {_state['error']}")
    return _state["mod"]
