"""Checagem do modelo (`model.update_check`) sem travar a nota: defeito 1 do teste real (passo 17 da Fase 3).

O casco pede `model.update_check` 1,5 s depois do primeiro `ready`. Antes do conserto, o motor ocupava a vaga da
transcrição durante a consulta inteira ao Hugging Face, e o `rec.start {mode: nota}` recusava com `busy`
(`recording._check_can_start` lê `core.transcribing`). Duas provas, nenhuma grava nem troca modelo:

- **em voo (processo real):** o motor consulta um servidor local (`HF_ENDPOINT`) que segura a resposta; com a
  consulta parada lá, o `state` tem de dizer `transcribing: false` (é o que a nota lê). Depois o servidor
  responde 500: a checagem falha calada (fail-safe do `reco.py`) e nada é baixado. `LOCALAPPDATA` temporário, para
  a pasta de modelos do usuário não entrar na busca.
- **troca espera a vaga (no processo do teste):** com revisão nova, `modelo.atualizar` só ocupa a vaga e chama
  `reco.update_model_if_newer` quando o motor está ocioso (sem gravação, nota parada, transcrição ou ao vivo).
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

from engine_harness import ENGINE_DIR, Engine, check, make_home

SEGURA_S = 30.0


class _Segura(BaseHTTPRequestHandler):
    """Hub falso: anota a chegada e só responde (500) quando o teste soltar."""

    def do_GET(self) -> None:  # noqa: N802  (nome da API do http.server)
        self.server.chegou.set()
        self.server.solta.wait(SEGURA_S)
        self.send_response(500)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *a) -> None:  # silêncio no console do teste
        pass


def _hub_falso() -> ThreadingHTTPServer:
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Segura)
    srv.chegou, srv.solta = threading.Event(), threading.Event()
    threading.Thread(target=srv.serve_forever, name="hub-falso", daemon=True).start()
    return srv


def run_em_voo(exe: str | None = None) -> None:
    srv = _hub_falso()
    home = make_home({"_migracao": 2})
    local = Path(tempfile.mkdtemp(prefix="reco_localappdata_"))
    env = {"HF_ENDPOINT": f"http://127.0.0.1:{srv.server_address[1]}", "HF_HUB_OFFLINE": None,
           "LOCALAPPDATA": str(local)}
    eng = Engine(home, exe, env_extra=env)
    try:
        eng.wait_ready(60)
        start = eng.mark()
        rid = eng.send("model.update_check")
        check(srv.chegou.wait(30), "a consulta do modelo não chegou ao hub falso (HF_ENDPOINT ignorado?)")
        st = eng.ok("state")
        em_voo = st["transcribing"]
        srv.solta.set()
        r = eng.response(rid, 60, start)
        check(not em_voo, f"checagem do modelo em voo ocupa a vaga da transcrição (a nota levaria busy): {st}")
        check(st["rec_state"] == "idle", f"state durante a checagem: {st}")
        check(r["ok"], f"model.update_check com o hub fora do ar não respondeu ok: {r}")
        check(eng.ok("state")["transcribing"] is False, "a vaga ficou ocupada depois da checagem")
        check(eng.shutdown(10) == 0, "exit != 0")
        eng.assert_clean_stdout()
    finally:
        srv.solta.set()
        eng.kill()
        srv.shutdown()
        shutil.rmtree(local, ignore_errors=True)
        shutil.rmtree(home, ignore_errors=True)
    print("OK modelo em voo: com a consulta presa no hub falso, state.transcribing=false (a nota não leva "
          "busy); hub fora do ar → ok calado")


def _esperar(cond, s: float = 2.0) -> bool:
    fim = time.perf_counter() + s
    while time.perf_counter() < fim:
        if cond():
            return True
        time.sleep(0.02)
    return False


def run_espera_vaga() -> None:
    sys.path.insert(0, str(ENGINE_DIR))
    from reco_engine import modelo  # noqa: PLC0415
    from reco_engine.core import Core  # noqa: PLC0415

    core = Core(lambda m: None)
    vista: list = []
    reco = SimpleNamespace(update_model_if_newer=lambda cb: vista.append(core.transcribing))
    # sem revisão nova: nada ocupa a vaga nem chama o reco
    check(modelo.atualizar(core, reco, None, consultar=lambda r: False) == {}, "resposta sem revisão nova")
    check(not vista and not core.transcribing, "sem revisão nova, a troca rodou ou a vaga ficou ocupada")
    # revisão nova com a nota gravando: a troca espera; com a nota parada (`stopped`) também
    for estado in ("recording", "stopped"):
        core.rec_state = estado
        th = threading.Thread(target=modelo.atualizar, args=(core, reco, None),
                              kwargs={"consultar": lambda r: True, "passo": 0.02}, daemon=True)
        th.start()
        check(not _esperar(lambda: bool(vista), 0.3), f"a troca do modelo rodou com o motor em {estado}")
        check(not core.transcribing, f"a espera ocupou a vaga com o motor em {estado}")
        core.rec_state = "idle"
        th.join(3)
        check(vista == [True], f"ocioso, a troca não rodou com a vaga ocupada: {vista}")
        check(not core.transcribing, "a vaga não foi solta depois da troca")
        vista.clear()
    # transcrição em curso: espera ela soltar a vaga
    core.claim_transcription()
    th = threading.Thread(target=modelo.atualizar, args=(core, reco, None),
                          kwargs={"consultar": lambda r: True, "passo": 0.02}, daemon=True)
    th.start()
    check(not _esperar(lambda: bool(vista), 0.3), "a troca do modelo rodou no meio de uma transcrição")
    core.release_transcription()
    th.join(3)
    check(vista == [True] and not core.transcribing, f"depois da transcrição: {vista}")
    print("OK modelo troca: só com revisão nova, e só com o motor ocioso (gravando, parado à espera da "
          "conclusão ou transcrevendo, espera)")
