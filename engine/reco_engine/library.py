"""Biblioteca: `library.list`, `library.search`, `library.delete`. O filesystem é o banco.

`list` espelha `_lib_scan_thread` (reco.py:4492-4529): `AUDIO_EXTS` da pasta de saída, `mtime`
decrescente, duração do container com cache por `(path, mtime)`. Correção sobre o app: a transcrição é
`x.txt` e, se faltar, `x.mp3.txt` (a regra de `tools/transcrever.py`); o app só olhava a primeira e
deixava transcrições invisíveis (ARMADILHAS § a biblioteca não enxerga). `delete` (F2-D15) só aceita
áudio de dentro da pasta da biblioteca e manda só o áudio à Lixeira; `.txt` e `.resumo.md` ficam.
"""
from __future__ import annotations

import threading
from pathlib import Path

from . import boot
from .core import arg_path
from .errors import EngineError, short

_dur_cache: dict = {}
_txt_cache: dict = {}
_cache_lk = threading.Lock()


def folder(reco) -> Path:
    cfg = reco.load_config()
    return Path(cfg["output_dir"]) if cfg.get("output_dir") else reco.default_output_dir()


def txt_for(p: Path) -> Path | None:
    """`x.txt` (app) ou, se faltar, `x.mp3.txt` (`tools/transcrever.py` fora da pasta do app)."""
    for cand in (p.with_suffix(".txt"), p.with_name(p.name + ".txt")):
        if cand.is_file():
            return cand
    return None


def _duration(p: Path, mtime: float) -> float | None:
    key = (str(p), mtime)
    with _cache_lk:
        if key in _dur_cache:
            return _dur_cache[key]
    try:
        import av  # noqa: PLC0415
        with av.open(str(p)) as cont:
            dur = float(cont.duration) / av.time_base if cont.duration else 0.0
    except Exception:  # noqa: BLE001
        dur = None
    with _cache_lk:
        _dur_cache[key] = dur
    return dur


def _item(p: Path) -> dict | None:
    try:
        st = p.stat()
    except OSError:
        return None                       # sumiu entre o listdir e o stat
    txt = txt_for(p)
    resumo = p.with_suffix(".resumo.md")
    dur = _duration(p, st.st_mtime)
    return {"name": p.name, "path": str(p), "mtime": st.st_mtime, "bytes": st.st_size,
            "duration_s": None if dur is None else round(dur, 3),
            "txt": str(txt) if txt else None,
            "resumo": str(resumo) if resumo.is_file() else None}


def scan(reco) -> list:
    base = folder(reco)
    try:
        files = sorted((p for p in base.iterdir() if p.suffix.lower() in reco.AUDIO_EXTS),
                       key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        files = []
    return [it for it in (_item(p) for p in files) if it is not None]


def _txt_content(path: str, mtime: float) -> str:
    key = (path, mtime)
    with _cache_lk:
        if key in _txt_cache:
            return _txt_cache[key]
    try:
        s = Path(path).read_text(encoding="utf-8", errors="ignore").casefold()
    except OSError:
        s = ""
    with _cache_lk:
        _txt_cache[key] = s
    return s


def _hit(item: dict, q: str) -> bool:
    if q in item["name"].casefold():
        return True
    txt = item["txt"]
    if not txt:
        return False
    try:
        mtime = Path(txt).stat().st_mtime
    except OSError:
        return False
    return q in _txt_content(txt, mtime)


def cmd_list(core, rid, args) -> dict:
    reco = boot.reco()
    return {"folder": str(folder(reco)), "items": scan(reco)}


def cmd_search(core, rid, args) -> dict:
    q = args.get("q")
    if not isinstance(q, str):
        raise EngineError("bad_args", "q (texto) é obrigatório")
    reco = boot.reco()
    q = q.strip().casefold()
    items = scan(reco)
    return {"q": q, "items": [it for it in items if not q or _hit(it, q)]}


def _check_deletable(core, reco, p: Path) -> Path:
    base = folder(reco).resolve()
    try:
        rp = p.resolve()
    except OSError as e:
        raise EngineError("refused", short(e)) from e
    if rp.suffix.lower() not in reco.AUDIO_EXTS or rp.parent != base:
        raise EngineError("refused", "só áudio de dentro da pasta da biblioteca")
    if not rp.is_file():
        raise EngineError("not_found", str(p))
    cur = core.rec_path
    if cur is not None and Path(cur).resolve() == rp:
        raise EngineError("refused", "é a gravação em andamento")
    return rp


def cmd_delete(core, rid, args) -> dict:
    reco = boot.reco()
    rp = _check_deletable(core, reco, arg_path(args))
    if not reco._excluir_gravacao(rp):
        raise EngineError("refused", "não foi possível excluir")
    with core.lock:
        if core.last_rec is not None and Path(core.last_rec).resolve() == rp:
            core.last_rec = None
    return {"path": str(rp), "deleted": True}


COMMANDS = {"library.list": cmd_list, "library.search": cmd_search, "library.delete": cmd_delete}
