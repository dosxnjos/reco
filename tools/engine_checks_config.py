"""Checagens de config (passo 4) e dispositivos (passo 5). O config real nunca é escrito: o motor roda
com `USERPROFILE` temporário e o teste compara o sha256 do real no fim."""
from __future__ import annotations

from engine_harness import Engine, RealConfigGuard, check, make_home, read_config, write_config

# chaves legadas que o config real do Gabriel ainda tem (sem uso no reco.py de hoje)
LEGADO = {"channels": 2, "mp3_bitrate": 128, "sample_rate": 48000}
SEED_1 = {"_migracao": 2, **LEGADO, "mic_gain": 1.0, "language": "pt"}
SEED_2 = {"_migracao": 1, "model": "small", "mic_gain": 1.0}     # sem `live`: pega merge sobre load_config


def _caso_migracao_2(eng: Engine, home) -> None:
    got = eng.ok("config.get")
    check(got["config"]["mic_gain"] == 1.0 and got["lang_efetivo"] == "pt", f"config.get: {got}")
    check(got["output_dir_efetivo"] == str(home / "Documents" / "Reco"), "output_dir_efetivo")
    eng.ok("config.set", {"changes": {"mic_gain": 2.5}})
    eng.ok("config.set", {"changes": {"casco_teste": True}})
    antes = (home / ".reco_config.json").read_bytes()
    check(eng.error("config.set", {"changes": {"chave_inventada": 1}}) == "bad_args",
          "chave inventada aceita")
    check(eng.error("config.set", {"changes": {"mic_gain": "alto"}}) == "bad_args", "tipo errado")
    check((home / ".reco_config.json").read_bytes() == antes, "set recusado mudou o arquivo")
    disco = read_config(home)
    esperado = {**SEED_1, "mic_gain": 2.5, "casco_teste": True}
    check(disco == esperado, f"config temporário diverge: {disco} != {esperado}")


def _caso_migracao_1(eng: Engine, home) -> None:
    write_config(home, SEED_2)
    eng.ok("config.set", {"changes": {"mic_gain": 1.5}})
    disco = read_config(home)
    check(disco.get("_migracao") == 1, f"migração persistida: {disco}")
    check("live" not in disco and disco.get("model") == "small", f"defaults/migração gravados: {disco}")
    check(disco == {**SEED_2, "mic_gain": 1.5}, f"config temporário diverge: {disco}")
    got = eng.ok("config.get")["config"]
    check(got["_migracao"] == 2 and got["mic_device"] == "auto:console" and got["live"] is False,
          f"get sem migração/defaults em memória: {got}")
    check(read_config(home) == disco, "config.get gravou o arquivo")


def _dispositivos(eng: Engine) -> str:
    d = eng.ok("devices.list", timeout=30)
    mics, spks = d["microphone"]["devs"], d["speaker"]["devs"]
    check(mics and spks, f"listas vazias: {len(mics)} mics, {len(spks)} saídas (thread do COM?)")
    cm, cs = d["microphone"]["console"], d["speaker"]["console"]
    check(cm and cs, f"console nulo: mic={cm} saída={cs}")
    nomes = [x["name"] for x in mics + spks]
    check(not any("?" in n or "�" in n for n in nomes), f"nome com ? (encoding): {nomes}")
    check(set(d["missing"]) == {"mic", "sys"} and "selected" in d, f"formato: {list(d)}")
    check(eng.ok("devices.refresh", timeout=30)["speaker"]["console"] == cs, "refresh diverge")
    return f"{len(mics)} mics, {len(spks)} saídas, console mic={cm}, console saída={cs}"


def run(guard: RealConfigGuard, exe: str | None = None) -> None:
    home = make_home(SEED_1)
    eng = Engine(home, exe)
    try:
        eng.wait_ready(60)
        _caso_migracao_2(eng, home)
        _caso_migracao_1(eng, home)
        devs = _dispositivos(eng)
        check(eng.shutdown(10) == 0, "exit != 0")
        eng.assert_clean_stdout()
    finally:
        eng.kill()
    check(guard.intact(), "o sha256 do ~/.reco_config.json real MUDOU")
    print("OK config: get, set mic_gain=2.5, chave legada preservada, migração não persistida, "
          "config real intocado (sha256 igual)")
    print(f"OK dispositivos: {devs}")
