"""`config.get` e `config.set`: o motor é o dono do `~/.reco_config.json` (D6); o casco nunca o grava.

Regras (F2-D6): o motor nunca chama `load_config(persist=True)` (ARMADILHAS § migração persistida);
o `set` relê o arquivo CRU (não o `load_config()`, que traz defaults e migração em memória), faz merge
sem apagar chave desconhecida, aceita só chaves de `_CFG_DEFAULTS` ou com o prefixo `casco_` (F2-D16),
grava com `reco.save_config` e relê para conferir, porque o `save_config` engole toda exceção.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import boot
from .errors import EngineError, short

CASCO_PREFIX = "casco_"
GAIN_KEYS = ("mic_gain", "sys_gain")
BOOL_KEYS = ("diarize", "aec", "live")
PATH_KEYS = ("output_dir", "nota_dir", "mic_device", "sys_device", "language")


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _valid(key: str, v) -> bool:
    if key.startswith(CASCO_PREFIX):
        return True
    if key in GAIN_KEYS:
        return _num(v) and 0.0 <= float(v) <= 10.0
    if key in BOOL_KEYS:
        return isinstance(v, bool)
    if key == "language":
        return v in (None, "pt", "en")
    if key in PATH_KEYS:
        return v is None or isinstance(v, str)
    return isinstance(v, str)


def _effective_dir(reco, cfg: dict) -> Path:
    return Path(cfg["output_dir"]) if cfg.get("output_dir") else reco.default_output_dir()


def cmd_get(core, rid, args) -> dict:
    reco = boot.reco()
    cfg = reco.load_config()            # persist=False: nunca grava a migração (F2-D6)
    return {"config": cfg, "output_dir_efetivo": str(_effective_dir(reco, cfg)),
            "lang_efetivo": reco.LANG}


def _read_raw(reco) -> dict:
    p = Path(reco.CONFIG_PATH)
    if not p.exists():
        return {}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise EngineError("save_failed", f"config ilegível, nada gravado: {short(e)}") from e
    if not isinstance(raw, dict):
        raise EngineError("save_failed", "config não é um objeto, nada gravado")
    return raw


def _check_changes(reco, changes) -> dict:
    if not isinstance(changes, dict) or not changes:
        raise EngineError("bad_args", "changes (objeto não vazio) é obrigatório")
    for key, v in changes.items():
        if key not in reco._CFG_DEFAULTS and not key.startswith(CASCO_PREFIX):
            raise EngineError("bad_args", f"chave desconhecida: {key}")
        if not _valid(key, v):
            raise EngineError("bad_args", f"valor inválido para {key}: {v!r}")
    out = dict(changes)
    for key in GAIN_KEYS:
        if key in out:
            out[key] = round(float(out[key]), 4)     # como _on_gain_release
    return out


def _guard_language(core, changes: dict) -> None:
    if "language" not in changes:
        return
    with core.lock:
        busy = core.rec_state in ("recording", "paused", "stopping") or core.transcribing
    if busy:
        raise EngineError("busy", "idioma não muda durante gravação ou transcrição")


def _apply_side_effects(core, reco, changes: dict) -> None:
    """O que o App faz além de gravar: idioma em `reco.LANG` (_set_language) e ganho no gravador
    ativo (_on_gain)."""
    if changes.get("language") in ("pt", "en"):
        reco.LANG = changes["language"]
    rec = core.recorder
    if rec is not None and any(k in changes for k in GAIN_KEYS):
        rec.set_gain(mic=changes.get("mic_gain"), sys=changes.get("sys_gain"))


def cmd_set(core, rid, args) -> dict:
    reco = boot.reco()
    changes = _check_changes(reco, args.get("changes"))
    _guard_language(core, changes)
    with core.lock:
        merged = _read_raw(reco)
        merged.update(changes)
        reco.save_config(merged)
        again = _read_raw(reco)
        diverge = [k for k, v in changes.items() if again.get(k, object()) != v]
    if diverge:
        raise EngineError("save_failed", f"config não gravou: {', '.join(diverge)}")
    _apply_side_effects(core, reco, changes)
    return cmd_get(core, rid, {})


COMMANDS = {"config.get": cmd_get, "config.set": cmd_set}
