"""`rec.conclude` (o que fazer com a última gravação) e o ao vivo durante a gravação.

Ações sobre o `last_rec`, espelhando o App:
- `save` (`_conclude_save`; o casco copia `"<path>"` entre aspas, o clipboard é dele);
- `delete` (`_conclude_delete`, Lixeira por `reco._excluir_gravacao`);
- `transcribe` / `transcribe_delete` (`_transcribe_recording`: estado vai a `idle` na hora; o áudio só
  sai depois do `.txt` salvo; cancelado ou erro preserva o mp3);
- `final_pass` (`_run_live_final_pass`, quando o ao vivo ligou no start);
- `nota` (`_run_nota_final_pass`: `.md` em `nota_dir` ou na pasta de saída e o mp3 à Lixeira; erro
  preserva o mp3).
O casco chama `final_pass`/`nota` logo depois do `rec.stop` quando `auto` vier preenchido (F2-D12).
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path

from . import boot
from .errors import EngineError, short
from .transcribe import SEM_CONTEUDO, autosave_txt, run_transcription

log = logging.getLogger("reco_engine.conclude")

ACTIONS = ("save", "delete", "transcribe", "transcribe_delete", "final_pass", "nota")


# ------------------------------------------------------------ ao vivo (rec.start)
def make_live(core, reco, cfg: dict) -> tuple:
    """(live, on_pair, live_suprimido) como `_start_rec` (reco.py:3766-3783): liga se `cfg["live"]`
    e não há transcrição no mesmo pipeline (senão seriam dois `pipe.generate` ao mesmo tempo)."""
    tr = core.transcriber(reco) if cfg.get("live") else None
    if tr is None:
        return None, None, False
    with core.lock:                 # confere e reserva juntos: nenhuma transcrição entra no meio
        if core.transcribing or core.live_active:   # live_active aqui = worker anterior ainda gerando
            return None, None, True
        core.live_active = True
        core.live_gen += 1
    # modelo e device do config, como o App faz no __init__ (reco.py:2881-2882)
    tr.set_model(cfg.get("model", reco._CFG_DEFAULTS["model"]))
    tr.set_device(cfg.get("device", "AUTO"))
    me = reco._spk_me()

    def on_text(spk, texto) -> None:
        core.emit("live.text", channel="mic" if spk == me else "sys", speaker=spk, text=texto)

    def on_warn(msg) -> None:
        # vem da thread do codificador (feed_pair): escrever no stdout ali poderia travar o MP3
        threading.Thread(target=core.emit, args=("live.warn",), kwargs={"text": msg},
                         daemon=True).start()

    try:
        live = reco.LiveTranscriber(tr, lang="pt" if reco.LANG == "pt" else "en")
        live.start(on_text=on_text, on_warn=on_warn)
    except BaseException:
        with core.lock:
            core.live_active = False
        raise
    return live, live.feed_pair, False


# ------------------------------------------------------------ rec.conclude
def _last_rec(core) -> Path:
    with core.lock:
        path, state = core.last_rec, core.rec_state
    if path is None or not path.exists():
        if state == "stopped":       # sumiu (library.delete, Explorer): não prender o estado em stopped
            _to_idle(core, forget=True)
        raise EngineError("not_found", "nenhuma gravação para concluir")
    if state != "stopped":
        raise EngineError("refused", f"nada a concluir no estado {state}")
    return path


def _to_idle(core, forget: bool = False) -> None:
    with core.lock:
        if forget:
            core.last_rec = None
        core.last_auto = None
    core.set_state("idle")


def _save(core, rid, reco, path: Path) -> dict:
    _to_idle(core)
    return {"path": str(path)}


def _delete(core, rid, reco, path: Path) -> dict:
    try:
        ok = reco._excluir_gravacao(path)
    except Exception as e:  # noqa: BLE001
        raise EngineError("refused", f"não foi possível excluir: {short(e)}") from e
    if not ok:
        raise EngineError("refused", "não foi possível excluir")
    _to_idle(core, forget=True)
    return {"path": str(path), "deleted": True}


def _transcribe_then(core, rid, reco, path: Path, delete_after: bool) -> dict:
    text = run_transcription(core, rid, path, on_claimed=lambda: _to_idle(core))
    txt = autosave_txt(path, text)
    deleted = False
    if delete_after:
        try:
            reco._excluir_gravacao(path)
        except Exception as e:  # noqa: BLE001
            log.warning("transcrito, mas o áudio não saiu: %s", short(e))
        deleted = not path.exists()
        if deleted:
            with core.lock:
                if core.last_rec == path:
                    core.last_rec = None
    return {"txt": str(txt), "deleted": deleted}


def _transcribe(core, rid, reco, path: Path) -> dict:
    return _transcribe_then(core, rid, reco, path, delete_after=False)


def _transcribe_delete(core, rid, reco, path: Path) -> dict:
    return _transcribe_then(core, rid, reco, path, delete_after=True)


def _passada_final(core, rid, reco, path: Path) -> dict:
    text = run_transcription(core, rid, path)
    try:
        txt = str(autosave_txt(path, text))
    except EngineError as e:      # o App mostra o texto mesmo sem o .txt: não perder a transcrição
        log.warning("passada final sem .txt: %s", e.detail)
        txt = None
    return {"txt": txt, "text": text}


def _nota_dir(reco) -> Path:
    cfg = reco.load_config()
    if cfg.get("nota_dir"):
        return Path(cfg["nota_dir"])
    return Path(cfg["output_dir"]) if cfg.get("output_dir") else reco.default_output_dir()


def _nota(core, rid, reco, path: Path) -> dict:
    try:
        text = run_transcription(core, rid, path)
    except EngineError:
        _to_idle(core)               # nota preservada: o mp3 fica (reco.py:4033-4038)
        raise
    try:
        dest = _nota_dir(reco)
        dest.mkdir(parents=True, exist_ok=True)
        md = dest / f"{path.stem}.md"
        md.write_text(text or SEM_CONTEUDO, encoding="utf-8")
    except OSError as e:
        _to_idle(core)
        raise EngineError("save_failed", f"nota preservada, falha ao salvar: {short(e)}") from e
    try:
        reco._excluir_gravacao(path)
    except Exception as e:  # noqa: BLE001
        log.warning("nota salva, mas o mp3 não saiu: %s", short(e))
    _to_idle(core, forget=True)
    return {"md": str(md)}


# mesma ordem de ACTIONS
_HANDLERS = dict(zip(ACTIONS, (_save, _delete, _transcribe, _transcribe_delete, _passada_final,
                               _nota), strict=True))


def cmd_conclude(core, rid, args) -> dict:
    action = args.get("action")
    if action not in _HANDLERS:
        raise EngineError("bad_args", f"action tem de ser um de {', '.join(ACTIONS)}")
    reco = boot.reco()
    path = _last_rec(core)
    return _HANDLERS[action](core, rid, reco, path)


COMMANDS = {"rec.conclude": cmd_conclude}
