"""CLIs herdadas do `reco.py`, iguais a `reco.py:5132-5179` (F2-D17): nada de servidor nem mutex.

- `--selftest`: grava `%TEMP%\\reco_selftest.txt` com as 5 linhas de diagnóstico e sai com 0;
- `--transcribe <áudio> [--diarize]`: grava `with_suffix(".txt")`, log em `%TEMP%\\reco_transcribe_log.txt`
  (termina em `OK -> <caminho>`), exit 2 em erro; AEC só com `--diarize`.
O stdout fica vazio: o fd 1 vai para o stderr antes do `import reco`.
"""
from __future__ import annotations

import os
import sys
import tempfile
import threading
from pathlib import Path


def _quiet_stdout() -> None:
    try:
        sys.stdout.flush()
        os.dup2(2, 1)
    except OSError:
        pass
    sys.stdout = sys.stderr


def selftest(reco) -> int:
    has_ov, has_mlx = reco.HAS_OV, reco.HAS_MLX
    devs = reco.ov_available_devices() if has_ov else []
    backend = "mlx-whisper" if has_mlx else "openvino" if has_ov else "none"
    lines = [
        f"frozen={reco.IS_FROZEN} lang={reco.LANG} HAS_SC={reco.HAS_SC} HAS_NP={reco.HAS_NP} "
        f"HAS_OV={has_ov} HAS_AV={reco.HAS_AV} HAS_MLX={has_mlx}",
        f"backend={backend}",
        f"ov_devices={devs}",
        f"resolved(AUTO)={reco.resolve_device('AUTO') if has_ov else 'n/a'}",
        f"transcription_available={(has_ov or has_mlx) and reco.HAS_AV}",
    ]
    Path(tempfile.gettempdir(), "reco_selftest.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")
    return 0


def transcribe(reco, argv: list) -> int:
    i = argv.index("--transcribe")
    audio = Path(argv[i + 1])
    diar = "--diarize" in argv
    log = Path(tempfile.gettempdir()) / "reco_transcribe_log.txt"
    log.write_text("starting\n", encoding="utf-8")
    tr = reco.make_transcriber()
    if tr is None or not reco.HAS_AV:
        log.write_text("ERROR: transcription backend/PyAV unavailable\n", encoding="utf-8")
        return 2
    cfg = reco.load_config()
    tr.set_model(cfg.get("model", reco._CFG_DEFAULTS["model"]))
    tr.set_device(cfg.get("device", "AUTO"))
    ev, out = threading.Event(), {}
    tr.transcribe(
        audio, lang=("pt" if reco.LANG == "pt" else "en"), diarize=diar,
        aec=bool(cfg.get("aec")) and diar,
        progress_cb=lambda m: log.write_text(m + "\n", encoding="utf-8"),
        done_cb=lambda t_, e: (out.update(t=t_, e=e), ev.set()))
    ev.wait(36000)
    if out.get("e"):
        log.write_text(f"ERROR: {out['e']}\n", encoding="utf-8")
        return 2
    txt = audio.with_suffix(".txt")
    txt.write_text(out.get("t") or "", encoding="utf-8")
    log.write_text(f"OK -> {txt}\n", encoding="utf-8")
    return 0


def main(argv: list) -> int:
    _quiet_stdout()
    import reco  # noqa: PLC0415  (só depois do stdout desviado)
    if "--selftest" in argv:
        return selftest(reco)
    return transcribe(reco, argv)
