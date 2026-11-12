"""Extras: `convert.extract_mp3`, `resumo.ia`, `model.update_check`, `app.update_check`.

- conversão espelha `_cv_convert` (reco.py:4783-4824) sobre `reco.extract_mp3`;
- resumo espelha `_lib_resumo` (reco.py:4663-4711): `claude -p <prompt> --model sonnet` (flag cravada),
  transcrição no stdin, timeout de 900 s, saída em `<gravação>.resumo.md`; o `.txt` segue as duas
  convenções da biblioteca (`x.txt`, senão `x.mp3.txt`);
- `model.update_check` troca a pasta do modelo no lugar: ocupa o lugar da transcrição (`busy`).
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from . import boot
from .core import arg_path, claim_flag, release_flag
from .errors import EngineError, short
from .library import txt_for

RESUMO_TIMEOUT_S = 900


def cmd_extract_mp3(core, rid, args) -> dict:
    path = arg_path(args)
    reco = boot.reco()
    if not path.is_file():
        raise EngineError("not_found", str(path))
    if not reco.HAS_AV:
        raise EngineError("unavailable", "conversão indisponível (av)")
    claim_flag(core, "extracting", "uma conversão")
    try:
        src_bytes = path.stat().st_size
        out = reco.extract_mp3(path, progress=lambda p: core.emit("progress", rid, pct=int(p),
                                                                    text=None))
    except reco.NoAudioStream as e:
        raise EngineError("no_audio_stream", "o arquivo não tem faixa de áudio") from e
    except Exception as e:
        raise EngineError("internal", f"falha ao converter: {short(e)}") from e
    finally:
        release_flag(core, "extracting")
    return {"path": str(out), "src_bytes": src_bytes, "dst_bytes": Path(out).stat().st_size}


def _run_claude(reco, cli: str, texto: str) -> str:
    lang = "pt" if reco.LANG == "pt" else "en"
    r = subprocess.run(  # noqa: S603  (argv fixo; o texto vai pelo stdin)
        [cli, "-p", reco.PROMPT_RESUMO[lang], "--model", "sonnet"],
        input=texto, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=RESUMO_TIMEOUT_S, check=False, **reco._no_window_kwargs())
    out = (r.stdout or "").strip()
    if r.returncode != 0 or not out:
        raise EngineError("internal", (r.stderr or "").strip()[:200] or f"código {r.returncode}")
    return out


def cmd_resumo(core, rid, args) -> dict:
    path = arg_path(args)
    reco = boot.reco()
    txt = txt_for(path)
    if txt is None:
        raise EngineError("not_found", "sem transcrição (.txt) para resumir")
    resumo = path.with_suffix(".resumo.md")
    if resumo.exists():
        return {"path": str(resumo), "existia": True}      # o casco abre
    claim_flag(core, "resumindo", "um resumo")
    try:
        cli = shutil.which("claude")
        if not cli:
            raise EngineError("claude_missing", "comando 'claude' fora do PATH")
        texto = txt.read_text(encoding="utf-8", errors="ignore")
        core.emit("progress", rid, pct=None, text=reco.t("Gerando resumo com o Claude…"))
        out = _run_claude(reco, cli, texto)
        resumo.write_text(out + "\n", encoding="utf-8")
    except subprocess.TimeoutExpired as e:
        raise EngineError("internal", f"claude passou de {RESUMO_TIMEOUT_S} s") from e
    except OSError as e:
        raise EngineError("save_failed", short(e)) from e
    finally:
        release_flag(core, "resumindo")
    return {"path": str(resumo), "existia": False}


def cmd_model_update(core, rid, args) -> dict:
    reco = boot.reco()
    core.claim_transcription()          # troca a pasta do modelo no lugar: nada transcreve junto
    try:
        reco.update_model_if_newer(lambda m: core.emit("progress", rid, pct=None, text=m))
    finally:
        core.release_transcription()
    return {}


def cmd_app_update(core, rid, args):
    reco = boot.reco()
    r = reco.check_app_update()
    return {"tag": r[0], "url": r[1]} if r else None


COMMANDS = {
    "convert.extract_mp3": cmd_extract_mp3,
    "resumo.ia": cmd_resumo,
    "model.update_check": cmd_model_update,
    "app.update_check": cmd_app_update,
}
