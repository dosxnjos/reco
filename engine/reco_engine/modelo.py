"""`model.update_check`: consulta se há revisão nova do modelo e só então troca a pasta.

Defeito 1 do teste real (passo 17 da Fase 3): o casco pede esta checagem 1,5 s depois do primeiro `ready`, e ela
ocupava a vaga da transcrição durante a consulta inteira ao Hugging Face. O `rec.start {mode: nota}` recusa com
`busy` enquanto há transcrição (a nota transcreve ao parar), então "Gravar nota" logo depois de abrir não gravava.

Agora:
- a consulta (só leitura: a revisão do repo no hub × o `.hf_revision` local) roda sem ocupar nada;
- sem revisão nova (o caso de quase todo dia) ou sem resposta do hub, termina aí;
- com revisão nova, espera o motor ficar ocioso (sem gravação, nota parada à espera da conclusão, transcrição ou
  ao vivo), ocupa a vaga e chama `reco.update_model_if_newer`, que consulta de novo, baixa e troca no lugar
  (`reco.py:1230-1264`, que não muda). Durante o download a vaga fica ocupada: uma nota pedida nessa janela
  leva `busy`, e a tela mostra o motivo.
"""
from __future__ import annotations

import logging
from collections.abc import Callable

from . import boot
from .errors import short

log = logging.getLogger("reco_engine.modelo")

ESPERA_PASSO_S = 1.0


def revisao_nova(reco) -> bool:
    """A mesma consulta do começo do `update_model_if_newer` (`reco.py:1235-1244`), sem trocar nada.
    Fail-safe como ele: sem pasta de modelo, sem rede ou hub com erro = sem revisão nova."""
    try:
        d = reco._find_model_dir()
        if d is None:
            return False
        from huggingface_hub import HfApi  # noqa: PLC0415  (pesado: só quando a checagem roda)
        latest = HfApi().model_info(reco._repo_for_dir(d)).sha
        rev = d / ".hf_revision"
        local = rev.read_text(encoding="utf-8").strip() if rev.exists() else None
        return bool(latest) and latest != local
    except Exception as e:  # noqa: BLE001
        log.info("checagem do modelo sem resposta: %s", short(e))
        return False


def _ocupar_se_ocioso(core) -> bool:
    """Ocupa a vaga da transcrição só com o motor ocioso; a checagem e a marca andam juntas, no lock."""
    with core.lock:
        if core.rec_state != "idle" or core.transcribing or core.live_active:
            return False
        core.transcribing = True
        core.cancel_pending = False
        return True


def esperar_vaga(core, passo: float = ESPERA_PASSO_S) -> bool:
    """Espera o motor ficar ocioso e ocupa a vaga (true); false se o motor está encerrando."""
    while not core.stop_ev.is_set():
        if _ocupar_se_ocioso(core):
            return True
        core.stop_ev.wait(passo)
    return False


def atualizar(core, reco, status_cb: Callable[[str], None] | None,
              consultar: Callable = revisao_nova, passo: float = ESPERA_PASSO_S) -> dict:
    if not consultar(reco):
        return {}
    log.info("modelo com revisão nova: a troca espera o motor ficar ocioso")
    if not esperar_vaga(core, passo):
        return {}
    try:
        reco.update_model_if_newer(status_cb)
    finally:
        core.release_transcription()
    return {}


def cmd_model_update(core, rid, args) -> dict:
    reco = boot.reco()
    return atualizar(core, reco, lambda m: core.emit("progress", rid, pct=None, text=m))


COMMANDS = {"model.update_check": cmd_model_update}
