"""Checagens de protocolo (passo 2), `ready` (passo 3), estado ocioso e conferência do PROTOCOL.md
(passo 13). Nenhuma delas grava nem toca som."""
from __future__ import annotations

import re
import sys
import time

from engine_harness import ENGINE_DIR, RAIZ, Engine, check, make_home

HELLO_MAX_S = 1.0          # do fonte (passo 3)
HELLO_MAX_EXE_S = 3.0      # congelado (passo 15)
WARM_MAX_S = 30.0


def _hello(eng: Engine) -> float:
    t0 = time.perf_counter()
    data = eng.ok("hello", timeout=10)
    dt = time.perf_counter() - eng.t0
    check(data.get("engine_version") == "0.1.0", f"engine_version: {data}")
    check(data.get("protocol") == 1 and "uptime_s" in data, f"hello incompleto: {data}")
    check(time.perf_counter() - t0 < 10, "hello lento")
    return dt


def _bad_lines(eng: Engine) -> None:
    start = eng.mark()
    eng.send_raw("isto não é json\n".encode())
    r = eng.wait_for(lambda m: "ok" in m and m.get("id") is None, 10, start)
    check(r is not None and r["error"]["code"] == "internal", f"linha inválida: {r}")
    check(eng.error("cmd.que.nao.existe") == "internal", "cmd desconhecido não deu internal")
    start = eng.mark()
    eng.send_raw(b'{"v":1,"id":7,"cmd":"hello","args":{}}\n')
    r = eng.wait_for(lambda m: m.get("id") == 7 and "ok" in m, 10, start)
    check(r is not None and not r["ok"] and r["error"]["code"] == "internal", f"id numérico: {r}")


def _idle_paths(eng: Engine) -> str:
    """Caminhos de gravação/conclusão que não tocam dispositivo (o código dos passos 6, 7 e 9 tem de
    pelo menos importar e responder certo sem o app fechado)."""
    st = eng.ok("state")
    check(st["rec_state"] == "idle" and st["ready"] is True and st["last_rec"] is None, f"state: {st}")
    check(eng.error("rec.stop") == "refused", "rec.stop ocioso não deu refused")
    check(eng.error("rec.pause") == "refused", "rec.pause ocioso não deu refused")
    check(eng.error("rec.conclude", {"action": "save"}) == "not_found", "conclude sem last_rec")
    check(eng.error("rec.conclude", {"action": "voar"}) == "bad_args", "conclude action inválida")
    check(eng.error("rec.start", {"mode": "karaoke"}) == "bad_args", "rec.start mode inválido")
    check(eng.ok("rec.set_gain", {"mic": 1.5}) == {"applied": False}, "set_gain sem gravador")
    check(eng.error("rec.set_gain", {"mic": 99}) == "bad_args", "set_gain fora da faixa")
    check(eng.ok("transcribe.cancel") == {"found": False}, "cancel sem transcrição")
    check(eng.error("transcribe.file", {"path": str(RAIZ / "nao_existe_reco.mp3")}) == "not_found",
          "transcribe.file inexistente")
    return "state idle, rec.stop/pause refused, conclude not_found, set_gain, cancel sem alvo"


def run(exe: str | None = None) -> None:
    eng = Engine(make_home({"_migracao": 2}), exe)
    try:
        t_hello = _hello(eng)
        _bad_lines(eng)
        ready = eng.wait_ready(60)
        # sem mandar linha nenhuma: com a leitora presa no stdin, carregar DLL (openvino) não pode
        # travar (server._isolate_stdin)
        warm = eng.wait_stderr("aquecimento pronto", WARM_MAX_S)
        check(warm is not None, f"aquecimento não terminou em {WARM_MAX_S:.0f} s sem linha no stdin")
        check(eng.ok("hello")["ready"] is True, "hello depois do ready sem ready:true")
        idle = _idle_paths(eng)
        code = eng.shutdown(10)
        check(code == 0, f"exit {code}")
        eng.assert_clean_stdout()
    finally:
        eng.kill()
    print("OK protocolo: hello, linha inválida, cmd desconhecido, id não-string, shutdown (exit 0)")
    teto = HELLO_MAX_EXE_S if exe else HELLO_MAX_S
    check(t_hello < teto, f"hello levou {t_hello:.2f} s (teto {teto} s)")
    has = ",".join(f"{k}:{v}" for k, v in ready["has"].items())
    check(all(ready["has"].values()), f"dependência ausente: {ready['has']}")
    aq = re.search(r"aquecimento pronto em ([\d.]+) s", warm)
    print(f"OK ready: import_s={ready['import_s']} has={{{has}}} lang={ready['lang']} "
          f"(hello em {t_hello:.2f} s; aquecimento {aq.group(1) if aq else '?'} s)")
    print(f"OK ocioso: {idle}")


def conferir_doc() -> None:
    sys.path.insert(0, str(ENGINE_DIR))
    from reco_engine.server import COMMANDS  # noqa: PLC0415
    doc = (RAIZ / "docs" / "PROTOCOL.md").read_text(encoding="utf-8")
    na_tabela = set(re.findall(r"^\| `([a-z0-9_.]+)` \|", doc, flags=re.MULTILINE))
    faltam = sorted(set(COMMANDS) - na_tabela)
    sobram = sorted(na_tabela - set(COMMANDS))
    check(not faltam, f"comandos do motor fora da tabela do PROTOCOL.md: {faltam}")
    check(not sobram, f"PROTOCOL.md cita comando que o motor não tem: {sobram}")
    print(f"OK doc: {len(COMMANDS)} comandos no registro, {len(na_tabela)} na tabela do "
          f"PROTOCOL.md, nenhum faltando")
