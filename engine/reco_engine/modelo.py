"""`model.update_check`: consulta se há revisão nova do modelo, baixa sem ocupar a vaga e só então troca a pasta.

Defeito 1 do teste real (passo 17 da Fase 3): o casco pede esta checagem 1,5 s depois do primeiro `ready`, e ela
ocupava a vaga da transcrição durante a consulta inteira ao Hugging Face. O `rec.start {mode: nota}` recusa com
`busy` enquanto há transcrição (a nota transcreve ao parar), então "Gravar nota" logo depois de abrir não gravava.

Agora (o `reco.update_model_if_newer`, `reco.py:1230-1264`, não muda nem é chamado; os passos dele moram aqui):
- a consulta (só leitura: a revisão do repo no hub × o `.hf_revision` local, com prazo de `CONSULTA_TIMEOUT_S`)
  roda sem ocupar nada;
- sem revisão nova (o caso de quase todo dia) ou sem resposta do hub, termina aí;
- com revisão nova, baixa para uma pasta temporária **sem ocupar a vaga** (o download leva minutos; a nota e o
  Transcrever seguem livres), espera o motor ficar ocioso (sem gravação, nota parada à espera da conclusão,
  transcrição ou ao vivo), ocupa a vaga só para a troca de pasta (renomear e mover, segundos) e a solta.
- a pasta temporária sai em todo caminho (download que falha, motor encerrando, troca que falha); se a troca
  falha depois de renomear a pasta atual, ela volta ao lugar (o motor nunca fica sem modelo).
"""
from __future__ import annotations

import logging
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path

from . import boot
from .errors import short

log = logging.getLogger("reco_engine.modelo")

ESPERA_PASSO_S = 1.0
CONSULTA_TIMEOUT_S = 15.0       # conexão travada não segura a checagem (e o `app.update_check` atrás dela)


def revisao_nova(reco) -> tuple | None:
    """A mesma consulta do começo do `update_model_if_newer` (`reco.py:1235-1244`), sem trocar nada.
    Devolve `(pasta, repo, revisão)` quando há revisão nova. Fail-safe como ele: sem pasta de modelo, sem rede ou
    hub com erro = sem revisão nova."""
    try:
        d = reco._find_model_dir()
        if d is None:
            return None
        from huggingface_hub import HfApi  # noqa: PLC0415  (pesado: só quando a checagem roda)
        repo = reco._repo_for_dir(d)
        latest = HfApi().model_info(repo, timeout=CONSULTA_TIMEOUT_S).sha
        rev = d / ".hf_revision"
        local = rev.read_text(encoding="utf-8").strip() if rev.exists() else None
        return (d, repo, latest) if latest and latest != local else None
    except Exception as e:  # noqa: BLE001
        log.info("checagem do modelo sem resposta: %s", short(e))
        return None


def baixar(repo: str, latest: str) -> Path | None:
    """Baixa a revisão numa pasta temporária, sem ocupar nada (`reco.py:1247-1248`). Falhou: apaga e devolve None."""
    tmp = Path(tempfile.mkdtemp(prefix="reco_model_"))
    try:
        from huggingface_hub import snapshot_download  # noqa: PLC0415
        snapshot_download(repo, revision=latest, local_dir=str(tmp))
        return tmp
    except Exception as e:  # noqa: BLE001
        log.info("download do modelo novo falhou; o atual fica: %s", short(e))
        shutil.rmtree(tmp, ignore_errors=True)
        return None


def trocar(reco, d: Path, tmp: Path, latest: str) -> None:
    """A troca de pasta de `reco.py:1249-1260`: a atual vira `.old`, a baixada entra no lugar com o `.hf_revision`.
    Se algo falha depois de renomear, a nova parcial sai e a `.old` volta ao lugar (o motor nunca fica sem modelo)."""
    target = d if reco._dir_writable(d.parent) else reco._user_data_dir() / "models" / d.name
    target.parent.mkdir(parents=True, exist_ok=True)
    bak = target.with_name(target.name + ".old")
    if bak.exists():
        shutil.rmtree(bak, ignore_errors=True)
    tinha = target.exists()
    if tinha:
        target.rename(bak)
    try:
        shutil.move(str(tmp), str(target))
        (target / ".hf_revision").write_text(latest, encoding="utf-8")
    except BaseException:
        shutil.rmtree(target, ignore_errors=True)
        if tinha:
            bak.rename(target)
        raise
    shutil.rmtree(bak, ignore_errors=True)


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


def atualizar(core, reco, status_cb: Callable[[str], None] | None, consultar: Callable = revisao_nova,
              baixar_fn: Callable = baixar, trocar_fn: Callable = trocar, passo: float = ESPERA_PASSO_S) -> dict:
    alvo = consultar(reco)
    if not alvo:
        return {}
    d, repo, latest = alvo
    log.info("modelo com revisão nova: baixando sem ocupar a vaga; a troca espera o motor ficar ocioso")
    if status_cb:
        status_cb(reco.t("Atualizando modelo…"))
    tmp = baixar_fn(repo, latest)
    if tmp is None:
        return {}
    try:
        if not esperar_vaga(core, passo):
            return {}
        try:
            trocar_fn(reco, d, tmp, latest)
        except Exception as e:  # noqa: BLE001  (fail-safe como o reco.py: o modelo atual fica)
            log.warning("troca do modelo falhou; o atual fica: %s", short(e))
            return {}
        finally:
            core.release_transcription()
        if status_cb:
            status_cb(reco.t("Modelo atualizado."))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return {}


def cmd_model_update(core, rid, args) -> dict:
    reco = boot.reco()
    return atualizar(core, reco, lambda m: core.emit("progress", rid, pct=None, text=m))


COMMANDS = {"model.update_check": cmd_model_update}
