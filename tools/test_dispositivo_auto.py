"""Guard do "Auto" de dispositivo (roadmap 2026-09-30-melhoria-dispositivo-auto.md).

Sem janela e sem gravar nada: confere que `default_endpoint_id` (papel 0 =
console, 2 = comunicação) bate com o `soundcard`, que roda em outra thread, que é
barato (a resolução roda síncrona no clique de Gravar, fora da regra "COM fora do
Tk") e que `resolve_device` trata os 4 casos: Auto padrão, Auto comunicação, id
manual presente e id manual ausente (nunca devolve id morto).

    python tools/test_dispositivo_auto.py            # roda os guards
    python tools/test_dispositivo_auto.py --listar   # endpoints + padrão por papel
                                                     # (passo 4.1, com o fone)

Exit code ≠ 0 na primeira falha. Se a API privada do `soundcard` mudar
(`mediafoundation._DeviceEnumerator`/`_ffi`/`_com`), é aqui que aparece: conferir o
pin `soundcard==0.4.6`.
"""
import sys
import threading
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import reco  # noqa: E402

KINDS = ("speaker", "microphone")
LIMITE_4_CHAMADAS_MS = 50
LIMITE_RESOLVE_MS = 250       # 2 resolve_device (mic + sistema) = o clique de Gravar


def _falha(msg: str):
    print(f"FALHOU {msg}")
    sys.exit(1)


def _enumera(kind: str) -> list:
    sc = reco.sc
    return list(sc.all_speakers() if kind == "speaker"
                else sc.all_microphones(include_loopback=False))


def listar():
    print("endpoints ativos e padrão por papel (0 = console, 2 = comunicação)")
    for kind in KINDS:
        p0 = reco.default_endpoint_id(kind, 0)
        p2 = reco.default_endpoint_id(kind, 2)
        print(f"\n[{kind}]")
        for d in _enumera(kind):
            marca = ("C" if d.id == p0 else " ") + ("M" if d.id == p2 else " ")
            print(f"  {marca}  {d.name}   {d.id}")
        print(f"  papel 0 = {p0}\n  papel 2 = {p2}"
              f"{'   (diverge do 0)' if p0 != p2 else ''}")
    print("\nC = padrão (console), M = padrão de comunicação")


def teste_endpoint():
    sc = reco.sc
    esperado = {"speaker": sc.default_speaker().id,
                "microphone": sc.default_microphone().id}
    for kind in KINDS:
        got = reco.default_endpoint_id(kind, 0)
        if got != esperado[kind]:
            _falha(f"console≠soundcard ({kind}): {got!r} ≠ {esperado[kind]!r}")
    comm = {k: reco.default_endpoint_id(k, 2) for k in KINDS}
    for kind, v in comm.items():
        if not v:
            _falha(f"papel 2 não resolveu ({kind})")
    # outra thread: o COM do soundcard é por thread, e a vigia da Fase 2 roda fora do Tk
    saida: dict = {}

    def na_thread():
        try:
            saida.update({(k, r): reco.default_endpoint_id(k, r)
                          for k in KINDS for r in (0, 2)})
        except Exception as e:        # noqa: BLE001
            saida["erro"] = repr(e)

    th = threading.Thread(target=na_thread)
    th.start()
    th.join(10)
    if th.is_alive() or "erro" in saida:
        _falha(f"thread: {saida.get('erro', 'travou')}")
    for kind in KINDS:
        if saida[(kind, 0)] != esperado[kind] or saida[(kind, 2)] != comm[kind]:
            _falha(f"thread devolveu id diferente ({kind})")
    t0 = time.perf_counter()
    for kind in KINDS:
        for role in (0, 2):
            reco.default_endpoint_id(kind, role)
    ms = (time.perf_counter() - t0) * 1000
    if ms >= LIMITE_4_CHAMADAS_MS:
        _falha(f"4 chamadas levaram {ms:.1f} ms (limite {LIMITE_4_CHAMADAS_MS})")
    print("OK console==soundcard (speaker, microphone) · comm resolvido · thread ok · "
          f"4 chamadas < {LIMITE_4_CHAMADAS_MS} ms")
    print(f"   (medido: 4 chamadas {ms:.1f} ms)")


def teste_resolve():
    for kind in KINDS:
        devs = _enumera(kind)
        ids = {d.id: d.name for d in devs}
        p0 = reco.default_endpoint_id(kind, 0)
        p2 = reco.default_endpoint_id(kind, 2)
        # 1. Auto padrão (e None, que vem de config antigo sem a chave)
        for valor in (reco.AUTO_CONSOLE, None):
            id_, nome, via = reco.resolve_device(valor, kind)
            if (id_, via) != (p0, "auto") or nome != ids.get(p0):
                _falha(f"auto:console ({kind}, valor={valor!r}): {(id_, nome, via)}")
        # 2. Auto comunicação
        id_, nome, via = reco.resolve_device(reco.AUTO_COMM, kind)
        if (id_, via) != (p2, "auto") or nome != ids.get(p2):
            _falha(f"auto:comm ({kind}): {(id_, nome, via)}")
        # 3. id manual presente: o próprio id, mesmo que o padrão seja outro
        alvo = next((d for d in devs if d.id != p0), devs[0])
        id_, nome, via = reco.resolve_device(alvo.id, kind)
        if (id_, nome, via) != (alvo.id, alvo.name, "manual"):
            _falha(f"manual presente ({kind}): {(id_, nome, via)}")
        # 4. id manual ausente (fone desligado): cai no padrão, jamais devolve o id morto
        morto = "{0.0.0.00000000}.{00000000-dead-beef-0000-000000000000}"
        id_, nome, via = reco.resolve_device(morto, kind)
        if (id_, via) != (p0, "ausente") or id_ == morto:
            _falha(f"manual ausente ({kind}): {(id_, nome, via)}")
    t0 = time.perf_counter()
    reco.resolve_device(reco.AUTO_CONSOLE, "microphone")
    reco.resolve_device(reco.AUTO_COMM, "speaker")
    ms = (time.perf_counter() - t0) * 1000
    if ms >= LIMITE_RESOLVE_MS:
        _falha(f"resolve_device (mic + sistema) levou {ms:.1f} ms (limite {LIMITE_RESOLVE_MS})")
    print("OK resolve_device (4 casos)")
    print(f"   (medido: mic + sistema no clique de Gravar {ms:.1f} ms)")


def main():
    if not reco.HAS_SC:
        _falha("soundcard indisponível")
    if "--listar" in sys.argv:
        listar()
        return
    teste_endpoint()
    teste_resolve()


if __name__ == "__main__":
    main()
