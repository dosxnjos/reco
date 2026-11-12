"""Gravação: `rec.start/pause/resume/stop/set_gain`, `state`, e os eventos `level`, `timer`, `state`,
`rec.error`. Espelha os métodos do App (`_start_rec`, `_start_nota`, `_resolve_devices`,
`_on_stream_error`, `_abort_to_idle`, `_stop_rec`, `_pause_rec`, `_resume_rec`, `_quit`) sobre o
`reco.DualRecorder`, sem mudar captura, MP3 nem alinhamento.

D11: gravando, o `shutdown` ou o EOF do stdin fecham o MP3 antes do `os._exit` (`close_for_exit`).
"""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from . import boot, conclude
from .errors import EngineError, short

log = logging.getLogger("reco_engine.recording")

LEVEL_TICK_S = 0.05        # F2-D13: um evento `level` a cada 50 ms, só gravando
ACTIVE = ("recording", "paused")
_peaks: dict = {"mic": None, "sys": None}
_peaks_lk = threading.Lock()
_ticker: dict = {"thread": None}


# ------------------------------------------------------------ eventos de nível e tempo
def _on_level(src: str, rms: float) -> None:
    """Callback das threads de captura (≈47 Hz por canal): só guarda o maior RMS da janela."""
    with _peaks_lk:
        cur = _peaks.get(src)
        _peaks[src] = rms if cur is None or rms > cur else cur


def _take_peaks() -> tuple:
    with _peaks_lk:
        mic, sys_ = _peaks["mic"], _peaks["sys"]
        _peaks["mic"] = _peaks["sys"] = None
    return mic, sys_


def _tick_loop(core) -> None:
    last_sec = -1
    while True:
        time.sleep(LEVEL_TICK_S)
        if core.rec_state != "recording":
            _take_peaks()
            last_sec = -1
            continue
        mic, sys_ = _take_peaks()
        core.emit("level", mic=mic, sys=sys_)
        sec = core.elapsed()
        if sec != last_sec:
            last_sec = sec
            core.emit("timer", elapsed_s=sec)


def _ensure_ticker(core) -> None:
    th = _ticker["thread"]
    if th is None or not th.is_alive():
        th = threading.Thread(target=_tick_loop, args=(core,), name="level-timer", daemon=True)
        _ticker["thread"] = th
        th.start()


# ------------------------------------------------------------ erros de captura
def _on_error(core, src: str, msg: str) -> None:
    """Espelha `_on_stream_error`: `save` ou todas as fontes mortas abortam e voltam a `idle`."""
    with core.lock:
        if core.rec_state == "starting":       # antes do `recording`: repassado depois do start
            core.early_errors.append((src, msg))
            return
        if core.rec_state != "recording":      # como o App: só age gravando
            return
        rec = core.recorder
        fatal = src == "save" or (rec is not None and rec.all_failed())
        if fatal:
            core.rec_state = "stopping"        # reserva: rec.stop e a saída não correm com o abort
    core.emit("rec.error", channel=src, detail=str(msg)[:200], fatal=fatal)
    if fatal:
        core.emit_state()
        # Nunca abortar na própria thread de captura: o `_wind_down` faria join nela mesma.
        threading.Thread(target=_abort_to_idle, args=(core,), name="rec-abort", daemon=True).start()


def _abort_to_idle(core) -> None:
    rec = core.recorder
    try:
        if rec is not None and rec.recording:
            rec.abort()
        _stop_live(core, wait=False)
    finally:
        with core.lock:
            core.rec_path = None
        core.stopped_ev.set()
        core.set_state("idle")


def _stop_live(core, wait: bool) -> None:
    """Para o ao vivo. Com `wait`, drena (até 15 s) e solta a vaga, como antes. Sem `wait` (abort, falha no start
    ou no stop, saída), descarta a fila e só solta `live_active` quando o worker termina o `generate` em curso:
    soltar antes deixava a troca do modelo ou um `transcribe.file` entrarem no mesmo pipeline com ele gerando."""
    with core.lock:
        live, core.live = core.live, None
        gen = core.live_gen
    if live is None:
        return
    try:
        if wait:
            live.stop(wait=True, timeout=15.0, discard=True)
        else:
            live.stop(wait=False, discard=True)
    except Exception as e:  # noqa: BLE001
        log.warning("ao vivo não parou limpo: %s", short(e))
    th = getattr(live, "_thread", None)
    if not wait and th is not None and th.is_alive():
        threading.Thread(target=_soltar_live_depois, args=(core, th, gen), name="live-solta", daemon=True).start()
    else:
        _soltar_live(core, gen)


LIVE_SOLTA_MAX_S = 120.0     # worker travado não prende a vaga para sempre


def _soltar_live(core, gen: int) -> None:
    with core.lock:
        if core.live_gen == gen:            # um ao vivo ligado depois (outro rec.start) segue com a marca
            core.live_active = False


def _soltar_live_depois(core, th, gen: int) -> None:
    th.join(LIVE_SOLTA_MAX_S)
    _soltar_live(core, gen)


# ------------------------------------------------------------ rec.start
def _dev(t: tuple) -> dict:
    return {"id": t[0], "name": t[1], "via": t[2]}


def _resolve(reco, cfg: dict, nota: bool) -> tuple:
    """Como `_resolve_devices`: pelo config (a única fonte), com enumeração fresca e síncrona."""
    mic = reco.resolve_audio_device(cfg.get("mic_device"), "microphone")
    sys_ = (None, None, "auto") if nota else reco.resolve_audio_device(cfg.get("sys_device"), "speaker")
    if mic[0] is None and sys_[0] is None:
        raise EngineError("no_device", "nenhuma fonte de áudio resolvida")
    if nota and mic[0] is None:
        raise EngineError("no_device", "nenhum microfone resolvido")
    return mic, sys_


def _check_can_start(core, reco, mode: str) -> None:
    if mode not in ("rec", "nota"):
        raise EngineError("bad_args", "mode tem de ser 'rec' ou 'nota'")
    if not (reco.HAS_SC and reco.HAS_NP and reco.HAS_AV):
        raise EngineError("unavailable", "captura indisponível (soundcard, numpy e av)")
    if core.rec_state != "idle":
        raise EngineError("busy", f"estado atual: {core.rec_state}")
    if mode == "nota" and core.transcribing:
        raise EngineError("busy", "transcrição em andamento")


def _recorder(core, reco, cfg: dict):
    if core.recorder is None:
        core.recorder = reco.DualRecorder()
    # o ganho do config vai ao gravador antes do start (reco.py:2876-2878)
    core.recorder.set_gain(mic=cfg.get("mic_gain", 1.0), sys=cfg.get("sys_gain", 1.0))
    return core.recorder


def _start_kwargs(core, reco, cfg: dict, nota: bool, on_pair) -> dict:
    out_dir = Path(cfg["output_dir"]) if cfg.get("output_dir") else reco.default_output_dir()
    kw = {"on_level": _on_level, "on_error": lambda s, m: _on_error(core, s, m),
          "on_pair": on_pair, "out_sr": reco.OUT_SR, "out_channels": reco.OUT_CH,
          "bitrate": reco.MP3_BR, "out_dir": out_dir}
    if nota:   # nota: mono, prefixo próprio, nunca ao vivo (reco.py:3836-3856)
        kw.update(out_channels=1, on_pair=None, prefix="nota" if reco.LANG == "pt" else "note")
    return kw


def cmd_start(core, rid, args) -> dict:
    reco = boot.reco()
    mode = args.get("mode", "rec")
    with core.lock:
        _check_can_start(core, reco, mode)
        core.rec_state = "starting"          # reserva: outro rec.start em paralelo leva `busy`
    try:
        return _start(core, reco, mode)
    except BaseException:
        _stop_live(core, wait=False)
        with core.lock:
            if core.rec_state == "starting":
                core.rec_state = "idle"
        raise


def _start(core, reco, mode: str) -> dict:
    nota = mode == "nota"
    cfg = reco.load_config()
    mic, sys_ = _resolve(reco, cfg, nota)
    rec = _recorder(core, reco, cfg)
    live, on_pair, suprimido = (None, None, False) if nota else conclude.make_live(core, reco, cfg)
    core.live, core.live_was_on, core.rec_mode = live, live is not None, mode
    core.early_errors = []
    _take_peaks()
    rec.start(mic[0], sys_[0], **_start_kwargs(core, reco, cfg, nota, on_pair))
    if not rec.recording:                       # não abriu o arquivo
        detail = "; ".join(m for _, m in core.early_errors) or "MP3 não criado na pasta de saída"
        raise EngineError("save_failed", detail[:200])
    with core.lock:
        core.rec_path = getattr(getattr(rec, "_writer", None), "path", None)
        core.start_ts, core.accum = time.monotonic(), 0.0
        core.stopped_ev.clear()
    core.set_state("recording")
    _ensure_ticker(core)
    for src, msg in core.early_errors:          # falha de abertura de canal antes do `recording`
        _on_error(core, src, msg)
    return {"mic": _dev(mic), "sys": _dev(sys_), "live": live is not None,
            "live_suprimido": suprimido}


# ------------------------------------------------------------ pause / resume / gain / state
def cmd_pause(core, rid, args) -> dict:
    with core.lock:
        if core.rec_state != "recording" or core.recorder is None:
            raise EngineError("refused", f"não está gravando (estado: {core.rec_state})")
        core.accum += time.monotonic() - core.start_ts      # congela o relógio
        core.recorder.pause()
        core.rec_state = "paused"
    core.emit_state()
    return {"elapsed_s": core.elapsed()}


def cmd_resume(core, rid, args) -> dict:
    with core.lock:
        if core.rec_state != "paused" or core.recorder is None:
            raise EngineError("refused", f"não está pausado (estado: {core.rec_state})")
        core.start_ts = time.monotonic()
        core.recorder.resume()
        core.rec_state = "recording"
    core.emit_state()
    return {"elapsed_s": core.elapsed()}


def _gain_arg(args: dict, key: str):
    v = args.get(key)
    if v is None:
        return None
    if not isinstance(v, (int, float)) or isinstance(v, bool) or not 0.0 <= float(v) <= 10.0:
        raise EngineError("bad_args", f"{key} tem de ser número entre 0 e 10")
    return float(v)


def cmd_set_gain(core, rid, args) -> dict:
    """Ganho ao vivo no arrasto, sem gravar config (`_on_gain`); o `config.set` vem ao soltar."""
    mic, sys_ = _gain_arg(args, "mic"), _gain_arg(args, "sys")
    if mic is None and sys_ is None:
        raise EngineError("bad_args", "informe mic e/ou sys")
    rec = core.recorder
    if rec is not None:
        rec.set_gain(mic=mic, sys=sys_)
    return {"applied": rec is not None}


def cmd_state(core, rid, args) -> dict:
    with core.lock:
        last = core.last_rec
        return {"ready": boot.is_ready(), "rec_state": core.rec_state, "elapsed_s": core.elapsed(),
                "transcribing": core.transcribing, "live": core.live is not None,
                "last_rec": str(last) if last else None, "auto": core.last_auto}


# ------------------------------------------------------------ rec.stop
def _auto(core) -> str | None:
    """`_after_stop`: nota → "nota"; ao vivo ligado no start → "final_pass"; senão nada (F2-D12)."""
    if core.rec_mode == "nota":
        return "nota"
    return "final_pass" if core.live_was_on else None


def _begin_stop(core) -> None:
    with core.lock:
        if core.rec_state not in ACTIVE or core.recorder is None:
            raise EngineError("refused", f"não está gravando (estado: {core.rec_state})")
        if core.rec_state == "recording":     # guarda o trecho corrente primeiro
            core.accum += time.monotonic() - core.start_ts
        core.rec_state = "stopping"           # na mesma trava: um 2º rec.stop leva `refused`
    core.emit_state()


def cmd_stop(core, rid, args) -> dict:
    reco = boot.reco()
    _begin_stop(core)
    try:
        path = core.recorder.stop()
        _stop_live(core, wait=True)          # drena antes de qualquer passada final (reco.py:3944-3951)
    except reco.NoAudioCaptured as e:
        _stop_live(core, wait=False)
        _finish_stop(core, None)
        raise EngineError("no_audio", "nenhum áudio capturado") from e
    except Exception as e:
        _stop_live(core, wait=False)
        _finish_stop(core, None)
        raise EngineError("save_failed", short(e)) from e
    return _finish_stop(core, Path(path))


def _finish_stop(core, path: Path | None) -> dict:
    with core.lock:
        core.rec_path = None
        duration = int(core.accum)
        if path is not None:
            core.last_rec, core.last_auto = path, _auto(core)
        auto = core.last_auto if path is not None else None
    core.stopped_ev.set()
    core.set_state("stopped" if path is not None else "idle")
    return {"path": str(path) if path else None, "duration_s": duration, "auto": auto}


# ------------------------------------------------------------ saída (D11)
EXIT_JOIN_S = 1.5    # por thread: 3 joins (2 canais + codificador) cabem nos 8 s do casco


def _stop_quiet(rec) -> None:
    try:
        # o stop() do DualRecorder espera até 3 s por thread; na saída o prazo é curto, então o
        # wind-down vem antes com teto menor (o stop() seguinte acha tudo parado e só fecha o arquivo)
        wind_down = getattr(rec, "_wind_down", None)
        if wind_down is not None:
            wind_down(timeout=EXIT_JOIN_S)
        rec.stop()
    except Exception as e:  # noqa: BLE001  (nada capturado / encode falhou: só sai)
        log.warning("stop na saída: %s", short(e))


def _claim_exit(core, deadline: float) -> str:
    """Espera um `rec.start` em curso decidir e reserva a gravação para a saída. Devolve
    "mine" (a saída fecha o arquivo), "other" (um rec.stop/abort já fecha) ou "none"."""
    while core.rec_state == "starting" and time.monotonic() < deadline:
        time.sleep(0.05)
    with core.lock:
        rec = core.recorder
        if core.rec_state == "stopping":
            return "other"
        if core.rec_state in ACTIVE and rec is not None and rec.recording:
            core.rec_state = "stopping"
            return "mine"
    return "none"


def close_for_exit(core, timeout: float) -> None:
    """Espelha `_quit`: gravando, fecha o MP3 numa thread e só então deixa o processo sair.
    O ao vivo para sem esperar (o casco mata o motor 8 s depois); transcrição em curso é cancelada."""
    deadline = time.monotonic() + timeout
    core.cancel_transcription()
    _stop_live(core, wait=False)
    who = _claim_exit(core, deadline)
    left = max(0.1, deadline - time.monotonic())
    if who == "other":
        core.stopped_ev.wait(left)          # um rec.stop (ou o abort) já está fechando o arquivo
    elif who == "mine":
        log.info("gravando na saída: fechando o MP3")
        th = threading.Thread(target=_stop_quiet, args=(core.recorder,), name="exit-save", daemon=True)
        th.start()
        th.join(left)


COMMANDS = {
    "rec.start": cmd_start,
    "rec.pause": cmd_pause,
    "rec.resume": cmd_resume,
    "rec.stop": cmd_stop,
    "rec.set_gain": cmd_set_gain,
    "state": cmd_state,
}
