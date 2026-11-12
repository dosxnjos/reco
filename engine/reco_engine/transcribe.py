"""`transcribe.file` e `transcribe.cancel`, e o miolo comum às passadas finais (conclude.py).

Espelha `_run_transcriber` (reco.py:4196-4227): um transcritor por processo, um `pipe.generate` por vez
(`busy`), modelo e device do config a cada pedido, diarização e AEC só em gravação do Reco (etiqueta no
nome). O `.txt` sai como `_autosave_txt`: `with_suffix(".txt")`, com o literal quando vazio.

Progresso (F2-D5): o `OVTranscriber` só entrega texto traduzido; o `pct` sai de `(\\d+)%` apenas no texto
de `tf("Transcrevendo… {p}%")`. As outras mensagens (modelo, "Carregando áudio…") vão com `pct: null`.
"""
from __future__ import annotations

import re
import threading
from pathlib import Path
from collections.abc import Callable

from . import boot
from .core import arg_path
from .errors import EngineError

SEM_CONTEUDO = "(no content recognized)"
_PCT = re.compile(r"(\d+)%")


def progress_emitter(core, rid, reco) -> Callable[[str], None]:
    head = reco.t("Transcrevendo… {p}%").split("{p}")[0]

    def cb(msg: str) -> None:
        pct = None
        if head and msg.startswith(head):
            m = _PCT.search(msg)
            pct = int(m.group(1)) if m else None
        core.emit("progress", rid, pct=pct, text=msg)
    return cb


def _options(reco, path: Path) -> dict:
    cfg = reco.load_config()
    reco_rec = reco.is_reco_recording(path)
    return {"model": cfg.get("model", reco._CFG_DEFAULTS["model"]), "device": cfg.get("device", "AUTO"),
            "diarize": bool(cfg.get("diarize")) and reco_rec, "aec": bool(cfg.get("aec")) and reco_rec}


def run_transcription(core, rid, path: Path, on_claimed: Callable[[], None] | None = None) -> str:
    """Transcreve `path` e devolve o texto (literal quando vazio). Levanta `cancelled` ou `internal`."""
    reco = boot.reco()
    if not path.exists():
        raise EngineError("not_found", str(path))
    tr = core.transcriber(reco)
    if tr is None:
        raise EngineError("unavailable", "transcrição indisponível (openvino-genai)")
    core.claim_transcription()
    try:
        if on_claimed:
            on_claimed()
        return _transcribe(core, rid, reco, tr, path)
    finally:
        core.release_transcription()


def _transcribe(core, rid, reco, tr, path: Path) -> str:
    opt = _options(reco, path)
    tr.set_model(opt["model"])
    tr.set_device(opt["device"])
    done = threading.Event()
    out: dict = {}

    def done_cb(text, err) -> None:
        out.update(text=text, err=err)
        done.set()

    tr.transcribe(path, lang="pt" if reco.LANG == "pt" else "en", diarize=opt["diarize"],
                  aec=opt["aec"], progress_cb=progress_emitter(core, rid, reco), done_cb=done_cb)
    if core.cancel_pending:          # cancel chegou antes do transcribe() limpar o sinal
        tr.cancel()
    done.wait()
    if out.get("err") == reco.CANCELLED:
        raise EngineError("cancelled", "transcrição cancelada")
    if out.get("err"):
        raise EngineError("internal", f"erro na transcrição: {out['err']}"[:300])
    return out.get("text") or SEM_CONTEUDO


def autosave_txt(path: Path, text: str) -> Path:
    """Como `_autosave_txt`: `x.txt` ao lado do áudio; falha vira `save_failed`."""
    txt = path.with_suffix(".txt")
    try:
        txt.write_text(text or SEM_CONTEUDO, encoding="utf-8")
    except OSError as e:
        raise EngineError("save_failed", f"transcrito, mas o .txt não gravou: {e}") from e
    return txt


def cmd_file(core, rid, args) -> dict:
    path = arg_path(args)
    text = run_transcription(core, rid, path)
    return {"txt": str(autosave_txt(path, text))}


def cmd_cancel(core, rid, args) -> dict:
    """O pedido em curso responde `cancelled` na fronteira do próximo grupo de VAD."""
    return {"found": core.cancel_transcription()}


COMMANDS = {"transcribe.file": cmd_file, "transcribe.cancel": cmd_cancel}
