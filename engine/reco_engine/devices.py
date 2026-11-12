"""`devices.list` e `devices.refresh` (sinônimos, F2-D11): a enumeração do soundcard já é fresca.

Fonte: `reco.scan_device_state()`, na thread do pedido. Só funciona com a thread do import viva
(boot.py): se ela morrer, as listas voltam vazias sem exceção. O motor não monta rótulo traduzido
("Auto: padrão do Windows (…)"): quem rotula é a interface.
"""
from __future__ import annotations

from . import boot


def _missing(reco, devs: list, saved) -> bool:
    """Mesma regra do `device_options`: id salvo fora da lista = ausente."""
    if saved in (None, "", reco.AUTO_CONSOLE, reco.AUTO_COMM):
        return False
    return saved not in [i for i, _ in devs]


def cmd_list(core, rid, args) -> dict:
    reco = boot.reco()
    state = reco.scan_device_state()
    cfg = reco.load_config()
    out: dict = {}
    for kind, st in state.items():
        out[kind] = {"devs": [{"id": i, "name": n} for i, n in st["devs"]],
                     "console": st.get("console"), "comm": st.get("comm")}
    sel = {"mic_device": cfg.get("mic_device"), "sys_device": cfg.get("sys_device")}
    out["selected"] = sel
    out["missing"] = {"mic": _missing(reco, state["microphone"]["devs"], sel["mic_device"]),
                      "sys": _missing(reco, state["speaker"]["devs"], sel["sys_device"])}
    return out


COMMANDS = {"devices.list": cmd_list, "devices.refresh": cmd_list}
