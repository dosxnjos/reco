"""Checagem do modelo (`model.update_check`) sem travar a nota: defeito 1 do teste real (passo 17 da Fase 3).

O casco pede `model.update_check` 1,5 s depois do primeiro `ready`. Antes do conserto, o motor ocupava a vaga da
transcrição durante a consulta inteira ao Hugging Face, e o `rec.start {mode: nota}` recusava com `busy`
(`recording._check_can_start` lê `core.transcribing`). Depois, a revisão adversarial achou o mesmo defeito por outro
caminho: com revisão nova, a vaga ficava presa durante o **download** inteiro. Nenhuma prova grava nem troca o
modelo de verdade:

- **em voo (processo real):** um hub falso local (`HF_ENDPOINT`) segura a consulta; com ela parada lá, o `state` tem
  de dizer `transcribing: false` (é o que a nota lê); o hub responde 500 e a checagem falha calada. Na 2ª rodada o
  hub diz que há revisão nova e segura o **download**: `transcribing: false` de novo; o download falha, a pasta do
  modelo fica intacta e a temporária some. `LOCALAPPDATA` e `TEMP` temporários com um modelo de mentira (só o
  arquivo sentinela): a pasta de modelos do usuário e a `models/` do repo nunca são o alvo, e o motor congelado
  (`--exe`, sem modelo dentro) também consulta.
- **troca espera a vaga (no processo do teste):** o download roda com a vaga livre; a troca de pasta só ocupa a vaga
  com o motor ocioso (sem gravação, start, stop, pausa, nota parada, transcrição ou ao vivo).
- **troca de pasta:** a nova entra com o `.hf_revision`; se a troca falha no meio, a antiga volta ao lugar; a
  temporária sai em todo caminho.
- **consulta com prazo:** o `model_info` vai com `timeout` (conexão travada não segura o `app.update_check`).
- **ao vivo solto no fim:** parar o ao vivo sem esperar (abort) só solta `live_active` quando o worker termina.
"""
from __future__ import annotations

import json
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
REVISAO_NOVA = "revisao-nova-do-teste"


class _Hub(BaseHTTPRequestHandler):
    """Hub falso. `segura`: anota a chegada e só responde (500) quando o teste soltar. `nova`: a consulta diz que há
    revisão nova; o download (rota `/revision/`) fica preso até o teste soltar e então falha (500)."""

    def do_GET(self) -> None:  # noqa: N802  (nome da API do http.server)
        srv = self.server
        if srv.modo == "nova" and "/revision/" not in self.path:
            corpo = json.dumps({"id": "OpenVINO/whisper-teste-int8-ov", "sha": REVISAO_NOVA}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)
            return
        (srv.baixando if srv.modo == "nova" else srv.chegou).set()
        srv.solta.wait(SEGURA_S)
        self.send_response(500)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *a) -> None:  # silêncio no console do teste
        pass


def _hub_falso() -> ThreadingHTTPServer:
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Hub)
    srv.modo, srv.chegou, srv.baixando, srv.solta = "segura", threading.Event(), threading.Event(), threading.Event()
    threading.Thread(target=srv.serve_forever, name="hub-falso", daemon=True).start()
    return srv


def _rodada(eng, srv, evento: threading.Event, oque: str, local: Path, falso: Path, temp: Path) -> None:
    start = eng.mark()
    rid = eng.send("model.update_check")
    check(evento.wait(30), f"{oque} não chegou ao hub falso (HF_ENDPOINT ignorado?)")
    st = eng.ok("state")
    srv.solta.set()
    r = eng.response(rid, 90, start)
    check(not st["transcribing"], f"{oque} em voo ocupa a vaga da transcrição (a nota levaria busy): {st}")
    check(st["rec_state"] == "idle", f"state durante {oque}: {st}")
    check(r["ok"], f"model.update_check com o hub fora do ar não respondeu ok: {r}")
    check(eng.ok("state")["transcribing"] is False, f"a vaga ficou ocupada depois de {oque}")
    check(sorted(p.name for p in falso.iterdir()) == [".hf_revision", "openvino_encoder_model.xml"],
          f"{oque} com o hub fora do ar mexeu na pasta do modelo")
    check(sorted(p.name for p in falso.parent.iterdir()) == [falso.name], "sobrou pasta ao lado do modelo")
    sobra = [p.name for p in temp.iterdir() if p.name.startswith("reco_model_")]
    check(not sobra, f"a pasta temporária do download ficou: {sobra}")


def run_em_voo(exe: str | None = None) -> None:
    srv = _hub_falso()
    home = make_home({"_migracao": 2})
    local = Path(tempfile.mkdtemp(prefix="reco_localappdata_"))
    temp = Path(tempfile.mkdtemp(prefix="reco_temp_"))
    # modelo de mentira na pasta do usuário (vence a busca do `_find_model_dir`): o congelado não traz modelo, e o
    # fonte nunca chega a consultar pela pasta `models/` real do repo
    falso = local / "Reco" / "models" / "whisper-teste-int8-ov"
    falso.mkdir(parents=True)
    (falso / "openvino_encoder_model.xml").write_text("", encoding="utf-8")
    (falso / ".hf_revision").write_text("revisao-local-do-teste", encoding="utf-8")
    env = {"HF_ENDPOINT": f"http://127.0.0.1:{srv.server_address[1]}", "HF_HUB_OFFLINE": None,
           "LOCALAPPDATA": str(local), "TEMP": str(temp), "TMP": str(temp)}
    eng = Engine(home, exe, env_extra=env)
    try:
        eng.wait_ready(60)
        _rodada(eng, srv, srv.chegou, "a consulta", local, falso, temp)
        srv.modo = "nova"
        srv.solta.clear()
        _rodada(eng, srv, srv.baixando, "o download da revisão nova", local, falso, temp)
        check(eng.shutdown(10) == 0, "exit != 0")
        eng.assert_clean_stdout()
    finally:
        srv.solta.set()
        eng.kill()
        srv.shutdown()
        for p in (local, temp, home):
            shutil.rmtree(p, ignore_errors=True)
    print("OK modelo em voo: com a consulta e com o download da revisão nova presos no hub falso, "
          "state.transcribing=false (a nota não leva busy); hub fora do ar → ok calado, pasta intacta, sem temporária")


def _esperar(cond, s: float = 2.0) -> bool:
    fim = time.perf_counter() + s
    while time.perf_counter() < fim:
        if cond():
            return True
        time.sleep(0.02)
    return False


def _motor():
    sys.path.insert(0, str(ENGINE_DIR))
    from reco_engine import modelo, recording  # noqa: PLC0415
    from reco_engine.core import Core  # noqa: PLC0415
    return modelo, recording, Core


def _atualizar_em_fundo(modelo, core, reco, baixou: list, trocou: list, solta: threading.Event):
    tmp = Path(tempfile.mkdtemp(prefix="reco_model_teste_"))

    def baixar(repo, latest):
        baixou.append(core.transcribing)
        solta.wait(5)
        return tmp

    th = threading.Thread(target=modelo.atualizar, args=(core, reco, None), daemon=True,
                          kwargs={"consultar": lambda r: (Path("x"), "repo", "rev"), "baixar_fn": baixar,
                                  "trocar_fn": lambda r, d, t, v: trocou.append(core.transcribing), "passo": 0.02})
    th.start()
    return th, tmp


def run_espera_vaga() -> None:
    modelo, _, Core = _motor()
    core = Core(lambda m: None)
    reco = SimpleNamespace(t=str)
    baixou: list = []
    trocou: list = []
    # sem revisão nova: nada baixa, nada ocupa a vaga
    check(modelo.atualizar(core, reco, None, consultar=lambda r: None,
                           baixar_fn=lambda *a: baixou.append(1)) == {}, "resposta sem revisão nova")
    check(not baixou and not core.transcribing, "sem revisão nova, baixou ou a vaga ficou ocupada")
    # o download roda com a vaga livre: uma transcrição (ou a nota) entra no meio dele
    solta = threading.Event()
    th, tmp = _atualizar_em_fundo(modelo, core, reco, baixou, trocou, solta)
    check(_esperar(lambda: bool(baixou)), "o download não começou")
    check(baixou == [False], f"o download ocupou a vaga da transcrição: {baixou}")
    core.claim_transcription()          # levantaria busy se a vaga estivesse presa
    solta.set()
    check(not _esperar(lambda: bool(trocou), 0.3), "a troca rodou no meio de uma transcrição")
    core.release_transcription()
    th.join(3)
    check(trocou == [True] and not core.transcribing, f"a troca não rodou com a vaga, ou não a soltou: {trocou}")
    check(not tmp.exists(), "a pasta temporária ficou depois da troca")
    # cada estado não ocioso segura a troca (o ao vivo também, mesmo com rec_state idle)
    for estado, ao_vivo in (("recording", False), ("starting", False), ("paused", False), ("stopping", False),
                            ("stopped", False), ("idle", True)):
        baixou.clear()
        trocou.clear()
        core.rec_state, core.live_active = estado, ao_vivo
        baixado = threading.Event()
        baixado.set()
        th, tmp = _atualizar_em_fundo(modelo, core, reco, baixou, trocou, baixado)
        check(not _esperar(lambda: bool(trocou), 0.3), f"a troca rodou com o motor em {estado}, ao vivo={ao_vivo}")
        check(not core.transcribing, f"a espera ocupou a vaga com o motor em {estado}, ao vivo={ao_vivo}")
        core.rec_state, core.live_active = "idle", False
        th.join(8)
        check(trocou == [True] and not core.transcribing, f"ocioso depois de {estado}: {trocou}")
        check(not tmp.exists(), f"a pasta temporária ficou ({estado})")
    print("OK modelo troca: o download corre com a vaga livre; a troca só com o motor ocioso (gravando, start, "
          "pausa, stop, nota parada, transcrição ou ao vivo, espera) e a temporária sempre sai")


def run_troca_de_pasta() -> None:
    modelo, _, _ = _motor()
    raiz = Path(tempfile.mkdtemp(prefix="reco_troca_"))
    try:
        reco = SimpleNamespace(_dir_writable=lambda d: True, _user_data_dir=lambda: raiz / "user")
        d = raiz / "models" / "whisper-teste-int8-ov"
        d.mkdir(parents=True)
        (d / "velho.bin").write_text("v", encoding="utf-8")

        def nova(nome: str) -> Path:
            t = raiz / f"tmp_{nome}"
            t.mkdir()
            (t / f"{nome}.bin").write_text(nome, encoding="utf-8")
            return t

        modelo.trocar(reco, d, nova("novo"), "rev1")
        check(sorted(p.name for p in d.iterdir()) == [".hf_revision", "novo.bin"], f"troca: {list(d.iterdir())}")
        check((d / ".hf_revision").read_text(encoding="utf-8") == "rev1", "o .hf_revision não é a revisão nova")
        check(not d.with_name(d.name + ".old").exists(), "a .old ficou depois da troca")
        try:                            # temporária que sumiu: o move falha depois de renomear a atual
            modelo.trocar(reco, d, raiz / "nao-existe", "rev2")
            check(False, "a troca com a temporária ausente não falhou")
        except FileNotFoundError:
            pass
        check(sorted(p.name for p in d.iterdir()) == [".hf_revision", "novo.bin"], "a pasta antiga não voltou")
        check(not d.with_name(d.name + ".old").exists(), "a .old ficou depois da falha")
    finally:
        shutil.rmtree(raiz, ignore_errors=True)
    print("OK modelo pasta: a nova entra com o .hf_revision; troca que falha no meio devolve a antiga")


def run_consulta_com_prazo() -> None:
    modelo, _, _ = _motor()
    import huggingface_hub  # noqa: PLC0415
    visto: dict = {}

    class _Api:
        def model_info(self, repo, **kw):
            visto.update(kw, repo=repo)
            return SimpleNamespace(sha="r")

    raiz = Path(tempfile.mkdtemp(prefix="reco_prazo_"))
    original = huggingface_hub.HfApi
    huggingface_hub.HfApi = _Api
    try:
        reco = SimpleNamespace(_find_model_dir=lambda: raiz, _repo_for_dir=lambda d: "OpenVINO/x")
        check(modelo.revisao_nova(reco) == (raiz, "OpenVINO/x", "r"), "sem .hf_revision local, não viu revisão nova")
    finally:
        huggingface_hub.HfApi = original
        shutil.rmtree(raiz, ignore_errors=True)
    prazo = visto.get("timeout")
    check(isinstance(prazo, (int, float)) and 0 < prazo <= 30, f"model_info sem prazo curto: {visto}")
    print(f"OK modelo prazo: a consulta vai com timeout={prazo:g} s")


class _VivoFalso:
    def __init__(self) -> None:
        self.solta = threading.Event()
        self._thread = threading.Thread(target=self.solta.wait, args=(10,), daemon=True)
        self._thread.start()
        self.parou: dict = {}

    def stop(self, **kw) -> None:
        self.parou = kw


def run_ao_vivo_solta_no_fim() -> None:
    _, recording, Core = _motor()
    core = Core(lambda m: None)
    vivo = _VivoFalso()
    core.live, core.live_active, core.live_gen = vivo, True, 1
    recording._stop_live(core, wait=False)
    check(vivo.parou.get("discard") is True and vivo.parou.get("wait") is False, f"stop: {vivo.parou}")
    check(not _esperar(lambda: not core.live_active, 0.3), "live_active caiu com o worker do ao vivo ainda gerando")
    vivo.solta.set()
    check(_esperar(lambda: not core.live_active), "live_active não caiu depois que o worker terminou")
    # um ao vivo novo ligado antes de o velho terminar não perde a marca
    velho = _VivoFalso()
    core.live, core.live_active = velho, True
    recording._stop_live(core, wait=False)
    core.live_active, core.live_gen = True, core.live_gen + 1
    velho.solta.set()
    time.sleep(0.3)
    check(core.live_active, "a soltura atrasada do ao vivo velho apagou a marca do novo")
    print("OK ao vivo solto no fim: sem esperar (abort), live_active só cai quando o worker termina, e não apaga o novo")
