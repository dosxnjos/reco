"""Checagens de transcrição (passo 8, `--transcrever`) e das CLIs herdadas (passo 12, `--cli`).

Tudo em cópias do MP3 numa pasta temporária (o original nunca é tocado), com o mesmo `USERPROFILE`
temporário para o motor e para a referência (`reco.py --transcribe <cópia> --diarize`): modelo,
device, AEC e idioma saem do mesmo config. Precisam da GPU livre e de minutos: fora da rodada padrão.
Se a GPU não for determinística (duas referências diferentes), a régua vira "motor × app não difere
mais que referência × referência".
"""
from __future__ import annotations

import difflib
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from engine_harness import (CREATE_NO_WINDOW, ENGINE_DIR, RAIZ, Engine, check, child_env, engine_cmd,
                            make_home)

TR_TIMEOUT_S = 900
LOG = Path(tempfile.gettempdir()) / "reco_transcribe_log.txt"
SELFTEST = Path(tempfile.gettempdir()) / "reco_selftest.txt"


def _copia(src: Path, pasta: Path, nome: str = "amostra_reco.mp3") -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    dst = pasta / nome
    shutil.copy2(src, dst)
    return dst


def _reco_py(args: list, home: Path) -> subprocess.CompletedProcess:
    """`reco.py` só com `--transcribe`/`--selftest`: sem eles cairia no mutex e no broadcast Reco.Show."""
    check(args[0] in ("--transcribe", "--selftest"), "reco.py sem --transcribe/--selftest")
    return subprocess.run([sys.executable, "reco.py", *args], cwd=str(RAIZ), env=child_env(home),
                          capture_output=True, timeout=TR_TIMEOUT_S, creationflags=CREATE_NO_WINDOW,
                          check=False)


def _referencia(mp3: Path, pasta: Path, home: Path) -> bytes:
    alvo = _copia(mp3, pasta)
    r = _reco_py(["--transcribe", str(alvo), "--diarize"], home)
    check(r.returncode == 0, f"referência reco.py saiu {r.returncode}: {LOG.read_text(encoding='utf-8')}")
    return alvo.with_suffix(".txt").read_bytes()


def _igual_ou_regua(nome: str, motor: bytes, ref1: bytes, ref2: bytes | None) -> str:
    if motor == ref1:
        return "igual byte a byte"
    check(ref2 is not None and ref2 != ref1, f"{nome}: .txt do motor difere da referência determinística")
    r_ref = difflib.SequenceMatcher(None, ref1, ref2).ratio()
    r_mot = difflib.SequenceMatcher(None, ref1, motor).ratio()
    check(motor == ref2 or r_mot >= r_ref, f"{nome}: motor×app {r_mot:.4f} < ref×ref {r_ref:.4f}")
    return f"GPU não determinística: motor×app {r_mot:.4f} ≥ ref×ref {r_ref:.4f}"


def _progressos(eng: Engine, rid, start: int) -> int:
    pcts = [m["pct"] for _, m in eng.events("progress", start, rid=rid) if m.get("pct") is not None]
    check(pcts, "nenhum evento de progresso trouxe pct")
    check(all(b >= a for a, b in zip(pcts, pcts[1:], strict=False)), f"pct não crescente: {pcts}")
    return len(eng.events("progress", start, rid=rid))


def _cancelar(eng: Engine, alvo: Path) -> None:
    start = eng.mark()
    rid = eng.send("transcribe.file", {"path": str(alvo)}, rid="tr-cancel")
    ev = eng.wait_for(lambda m: m.get("id") == rid and m.get("pct") is not None, 120, start)
    check(ev is not None, "segunda transcrição não deu progresso com pct")
    dup = eng.request("transcribe.file", {"path": str(alvo)}, rid=rid, timeout=10)
    check(not dup["ok"] and dup["error"]["code"] == "internal", f"id repetido: {dup}")
    depois = eng.mark()              # a resposta do id repetido também tem esse id: olhar só depois dela
    check(eng.error("transcribe.file", {"path": str(alvo)}) == "busy", "segunda transcrição sem busy")
    check(eng.ok("transcribe.cancel")["found"] is True, "cancel não achou a transcrição")
    r = eng.response(rid, 120, depois)
    check(not r["ok"] and r["error"]["code"] == "cancelled", f"cancelado respondeu {r}")
    check(not alvo.with_suffix(".txt").exists(), ".txt nasceu de transcrição cancelada")


def run_transcrever(mp3: str, exe: str | None = None) -> None:
    src = Path(mp3).resolve()
    check(src.is_file(), f"MP3 não encontrado: {src}")
    work = Path(tempfile.mkdtemp(prefix="reco_engine_tr_"))
    home = make_home({"_migracao": 2}, work)
    ref1 = _referencia(src, work / "ref1", home)
    ref2 = _referencia(src, work / "ref2", home)
    eng = Engine(home, exe)
    try:
        eng.wait_ready(60)
        alvo = _copia(src, work / "motor")
        start = eng.mark()
        t0 = time.perf_counter()
        r = eng.request("transcribe.file", {"path": str(alvo)}, timeout=TR_TIMEOUT_S, rid="tr-1")
        check(r["ok"], f"transcribe.file falhou: {r.get('error')}")
        dt = time.perf_counter() - t0
        n = _progressos(eng, "tr-1", start)
        regua = _igual_ou_regua("transcrição", Path(r["data"]["txt"]).read_bytes(), ref1, ref2)
        _cancelar(eng, _copia(src, work / "motor2"))
        check(eng.shutdown(10) == 0, "exit != 0")
        eng.assert_clean_stdout()
    finally:
        eng.kill()
    shutil.rmtree(work, ignore_errors=True)
    print(f"OK transcrição: .txt igual ao do app ({regua}; refs iguais={ref1 == ref2}; {dt:.1f} s), "
          f"{n} progressos, pct crescente; cancel → cancelled; id repetido → internal")


# ------------------------------------------------------------------ --cli
def _cli_motor(exe: str | None, args: list, home: Path) -> subprocess.CompletedProcess:
    return subprocess.run([*engine_cmd(exe), *args], cwd=str(ENGINE_DIR), env=child_env(home),
                          capture_output=True, timeout=TR_TIMEOUT_S, creationflags=CREATE_NO_WINDOW,
                          check=False)


def _cli_transcribe(src: Path, work: Path, home: Path, exe: str | None) -> str:
    a = _copia(src, work, "a_reco.mp3")
    r = _cli_motor(exe, ["--transcribe", str(a), "--diarize"], home)
    log = LOG.read_text(encoding="utf-8").strip()
    check(r.returncode == 0, f"motor --transcribe saiu {r.returncode}: {log}")
    check(r.stdout == b"", f"motor escreveu no stdout: {r.stdout[:200]!r}")
    check(log == f"OK -> {a.with_suffix('.txt')}", f"log do motor: {log}")
    ref1 = _referencia(src, work / "b", home)
    motor = a.with_suffix(".txt").read_bytes()
    ref2 = None if motor == ref1 else _referencia(src, work / "c", home)
    return _igual_ou_regua("cli", motor, ref1, ref2)


def _cli_selftest(home: Path) -> None:
    r = _cli_motor(None, ["--selftest"], home)
    check(r.returncode == 0 and r.stdout == b"", f"motor --selftest: exit {r.returncode}, {r.stdout[:100]!r}")
    motor = SELFTEST.read_bytes()
    r = _reco_py(["--selftest"], home)
    check(r.returncode == 0, f"reco.py --selftest saiu {r.returncode}")
    check(SELFTEST.read_bytes() == motor, f"selftest difere:\n{motor!r}\n{SELFTEST.read_bytes()!r}")


def run_cli(mp3: str, exe: str | None = None) -> None:
    src = Path(mp3).resolve()
    check(src.is_file(), f"MP3 não encontrado: {src}")
    work = Path(tempfile.mkdtemp(prefix="reco_engine_cli_"))
    home = make_home({"_migracao": 2}, work)
    regua = _cli_transcribe(src, work / "a", home, exe)
    _cli_selftest(home)
    shutil.rmtree(work, ignore_errors=True)
    print(f"OK cli: exit 0, stdout vazio, log OK, .txt igual ({regua}); OK selftest igual")
