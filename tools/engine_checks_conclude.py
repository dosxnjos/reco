"""`--gravar N --concluir` (passo 9): grava oito vezes e conclui cada uma de um jeito.

save, delete (confere a Lixeira por comando), transcribe, transcribe_delete, nota, final_pass (ao
vivo ligado, 30 s, depois do transcribe para o pipeline estar quente) e dois cancelados
(transcribe_delete e nota) que têm de deixar o mp3 no disco. Precisa do app velho fechado e da GPU
livre; as guardas de `engine_checks_rec.guardas()` rodam antes.
"""
from __future__ import annotations

import shutil
import time
from pathlib import Path

from engine_checks_lib import lixeira_nomes
from engine_checks_rec import Clipe, gravar
from engine_harness import Engine, check, make_home

TR_TIMEOUT_S = 900
FINAL_PASS_S = 30.0


def _concluir(eng: Engine, action: str) -> dict:
    return eng.ok("rec.conclude", {"action": action}, timeout=TR_TIMEOUT_S)


def _estado(eng: Engine) -> str:
    return eng.ok("state")["rec_state"]


def _simples(eng: Engine, s: float) -> list:
    feitos = []
    p = Path(gravar(eng, s)["fim"]["path"])
    check(_concluir(eng, "save")["path"] == str(p) and p.exists() and _estado(eng) == "idle", "save")
    feitos.append("save")
    p = Path(gravar(eng, s)["fim"]["path"])
    check(_concluir(eng, "delete")["deleted"] and not p.exists(), "delete não tirou o arquivo")
    check(p.stem in [Path(n).stem for n in lixeira_nomes()], f"{p.name} não está na Lixeira")
    feitos.append("delete (Lixeira)")
    p = Path(gravar(eng, s)["fim"]["path"])
    d = _concluir(eng, "transcribe")
    check(Path(d["txt"]).is_file() and p.exists() and not d["deleted"], f"transcribe: {d}")
    feitos.append("transcribe")
    p = Path(gravar(eng, s)["fim"]["path"])
    d = _concluir(eng, "transcribe_delete")
    check(Path(d["txt"]).is_file() and d["deleted"] and not p.exists(), f"transcribe_delete: {d}")
    feitos.append("transcribe_delete")
    return feitos


def _nota(eng: Engine, s: float) -> str:
    g = gravar(eng, s, mode="nota")
    check(g["fim"]["auto"] == "nota", f"auto da nota: {g['fim']}")
    p = Path(g["fim"]["path"])
    d = _concluir(eng, "nota")
    check(Path(d["md"]).is_file() and not p.exists() and _estado(eng) == "idle", f"nota: {d}")
    return "nota"


def _final_pass(eng: Engine) -> str:
    eng.ok("config.set", {"changes": {"live": True}})
    try:
        g = gravar(eng, FINAL_PASS_S)
    finally:
        eng.ok("config.set", {"changes": {"live": False}})
    check(g["ini"]["live"] is True and g["fim"]["auto"] == "final_pass", f"ao vivo: {g['ini']} {g['fim']}")
    textos = eng.events("live.text", g["start"])
    check(textos, "nenhum live.text chegou em 30 s de gravação com o ao vivo ligado")
    d = _concluir(eng, "final_pass")
    check(Path(d["txt"]).is_file() and d["text"], f"final_pass: {d}")
    # a passada final mantém `stopped` (como o App): o casco ainda conclui com save ou delete
    check(_estado(eng) == "stopped", "final_pass deveria manter o estado stopped")
    _concluir(eng, "save")
    return f"final_pass ({len(textos)} live.text)"


def _cancelado(eng: Engine, s: float, mode: str, action: str) -> None:
    p = Path(gravar(eng, s, mode=mode)["fim"]["path"])
    start = eng.mark()
    rid = eng.send("rec.conclude", {"action": action})
    achou, limite = False, time.perf_counter() + 10
    while not achou and time.perf_counter() < limite:   # cancel pegajoso: vale logo depois do claim
        achou = eng.ok("transcribe.cancel")["found"]
    check(achou, f"{action}: transcribe.cancel não achou a transcrição")
    r = eng.response(rid, TR_TIMEOUT_S, start)
    check(not r["ok"] and r["error"]["code"] == "cancelled", f"{action} cancelado respondeu {r}")
    check(p.exists(), f"{action} cancelado removeu o áudio")
    check(_estado(eng) == "idle", f"{action} cancelado não voltou a idle")


def run(segundos: float, exe: str | None = None) -> None:
    home = make_home({"_migracao": 2, "live": False})
    eng = Engine(home, exe)
    try:
        eng.wait_ready(60)
        with Clipe():
            feitos = _simples(eng, segundos)
            feitos.append(_nota(eng, segundos))
            feitos.append(_final_pass(eng))
            _cancelado(eng, segundos, "rec", "transcribe_delete")
            _cancelado(eng, segundos, "nota", "nota")
        check(eng.shutdown(10) == 0, "exit != 0")
        eng.assert_clean_stdout()
    finally:
        eng.kill()
    shutil.rmtree(home, ignore_errors=True)
    print(f"OK conclusões: {', '.join(feitos)}, 2 cancelados com mp3")
