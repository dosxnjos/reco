"""Checagens da biblioteca (passo 10) e dos extras (passo 11). Fixtures geradas na hora, numa pasta
temporária; o `claude` de verdade nunca é chamado (um `claude.cmd` falso grava o argv)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from engine_harness import RAIZ, Engine, check, make_home

sys.path.insert(0, str(RAIZ))
import reco  # noqa: E402  (só MP3Writer/av; importar não grava o config, persist=False)

LIXEIRA_PS = ("(New-Object -ComObject Shell.Application).NameSpace(10).Items() "
              "| ForEach-Object Name")


def lixeira_nomes() -> list:
    r = subprocess.run(["powershell", "-NoProfile", "-Command", LIXEIRA_PS], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=60, check=False)
    return [s.strip() for s in r.stdout.splitlines() if s.strip()]


def mp3_1s(path: Path, freq: float = 440.0) -> None:
    t = np.arange(48000, dtype=np.float32) / 48000
    tom = (0.2 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    w = reco.MP3Writer(path, 48000, reco.OUT_SR, reco.OUT_CH, reco.MP3_BR)
    w.feed(tom, tom)
    w.close()


def _fixtures(pasta: Path) -> dict:
    nomes = {k: pasta / f"gravacao_reco_2026-01-0{i}_10-00-00.mp3" for i, k in enumerate("abc", 1)}
    for i, p in enumerate(nomes.values()):
        mp3_1s(p, 300.0 + 100 * i)
        os.utime(p, (1_700_000_000 + i * 60, 1_700_000_000 + i * 60))    # c mais novo
    nomes["a"].with_suffix(".txt").write_text("Eu: falamos do abacaxi.\n", encoding="utf-8")
    Path(str(nomes["b"]) + ".txt").write_text("Interlocutor(es): jabuticaba madura.\n",
                                              encoding="utf-8")
    return nomes


def _list_checks(eng: Engine, nomes: dict) -> None:
    items = eng.ok("library.list")["items"]
    check([i["name"] for i in items] == [nomes[k].name for k in "cba"], f"ordem/itens: {items}")
    check(all(i["duration_s"] is not None and round(i["duration_s"]) == 1 for i in items),
          f"duração: {[i['duration_s'] for i in items]}")
    por = {i["name"]: i for i in items}
    check(por[nomes["a"].name]["txt"].endswith(".txt") and not por[nomes["a"].name]["txt"].endswith(".mp3.txt"),
          "x.txt não achado")
    check(por[nomes["b"].name]["txt"] and por[nomes["b"].name]["txt"].endswith(".mp3.txt"),
          "x.mp3.txt não achado (o app deixava invisível)")
    check(por[nomes["c"].name]["txt"] is None, "item sem transcrição com txt")


def _search_checks(eng: Engine, nomes: dict) -> None:
    def nomes_de(q):
        return [i["name"] for i in eng.ok("library.search", {"q": q})["items"]]
    check(nomes_de("ABACAXI") == [nomes["a"].name], "busca no x.txt")
    check(nomes_de("jabuticaba") == [nomes["b"].name], "busca no x.mp3.txt")
    check(nomes_de("01-03") == [nomes["c"].name], "busca por nome")
    check(len(nomes_de("")) == 3, "busca vazia")


def _delete_checks(eng: Engine, home: Path, nomes: dict, lixeira: bool) -> None:
    fora = home / "fora_reco.mp3"
    mp3_1s(fora)
    check(eng.error("library.delete", {"path": str(fora)}) == "refused", "delete fora da pasta aceito")
    txt = nomes["a"].with_suffix(".txt")
    check(eng.error("library.delete", {"path": str(txt)}) == "refused", "delete de .txt aceito")
    check(fora.exists() and txt.exists(), "arquivo recusado sumiu")
    if lixeira:
        data = eng.ok("library.delete", {"path": str(nomes["c"])})
        check(data["deleted"] and not nomes["c"].exists(), "delete real não tirou o arquivo")
        check(nomes["c"].stem in [Path(n).stem for n in lixeira_nomes()], "não está na Lixeira")


def run_library(exe: str | None = None, lixeira: bool = False) -> None:
    home = make_home({"_migracao": 2})
    nomes = _fixtures(home / "Documents" / "Reco")
    eng = Engine(home, exe)
    try:
        eng.wait_ready(60)
        _list_checks(eng, nomes)
        _search_checks(eng, nomes)
        _delete_checks(eng, home, nomes, lixeira)
        check(eng.shutdown(10) == 0, "exit != 0")
        eng.assert_clean_stdout()
    finally:
        eng.kill()
    extra = " (delete real: na Lixeira)" if lixeira else ""
    print("OK biblioteca: 3 itens, duração 1 s, x.txt e x.mp3.txt achados, busca por conteúdo nas "
          f"duas convenções, delete fora da pasta recusado{extra}")


# ------------------------------------------------------------------ extras
def _wav_tom(path: Path) -> None:
    import av
    with av.open(str(path), "w") as c:
        st = c.add_stream("pcm_s16le", rate=44100, layout="stereo")
        sinal = (8000 * np.sin(2 * np.pi * 440 * np.arange(44100) / 44100)).astype(np.int16)
        fr = av.AudioFrame.from_ndarray(np.stack([sinal, sinal], axis=1).reshape(1, -1), format="s16",
                                        layout="stereo")
        fr.sample_rate = 44100
        for pkt in st.encode(fr):
            c.mux(pkt)
        for pkt in st.encode(None):
            c.mux(pkt)


def _mp4_sem_audio(path: Path) -> None:
    import av
    with av.open(str(path), "w") as c:
        st = c.add_stream("mpeg4", rate=10)
        st.width, st.height, st.pix_fmt = 64, 64, "yuv420p"
        for _ in range(10):
            fr = av.VideoFrame.from_ndarray(np.zeros((64, 64, 3), np.uint8), format="rgb24")
            for pkt in st.encode(fr):
                c.mux(pkt)
        for pkt in st.encode(None):
            c.mux(pkt)


def _convert_checks(eng: Engine, home: Path) -> None:
    import av
    wav, mp4 = home / "tom.wav", home / "so_video.mp4"
    _wav_tom(wav)
    _mp4_sem_audio(mp4)
    data = eng.ok("convert.extract_mp3", {"path": str(wav)}, timeout=120)
    with av.open(data["path"]) as c:
        a = c.streams.audio[0]
        check(a.rate == 16000 and a.channels == 1, f"convertido: {a.rate} Hz, {a.channels} canais")
    check(data["src_bytes"] > 0 and data["dst_bytes"] > 0, f"tamanhos: {data}")
    check(eng.error("convert.extract_mp3", {"path": str(mp4)}) == "no_audio_stream", "sem trilha")
    check(eng.ok("hello")["ready"], "motor caiu depois do vídeo sem som")
    up = eng.ok("app.update_check", timeout=30)
    check(up is None or set(up) == {"tag", "url"}, f"app.update_check: {up}")


def _sem_claude_path() -> str:
    exts = ("", ".exe", ".cmd", ".bat", ".ps1")
    dirs = [d for d in os.environ.get("PATH", "").split(os.pathsep)
            if d and not any((Path(d) / f"claude{e}").exists() for e in exts)]
    return os.pathsep.join(dirs)


def _claude_falso(pasta: Path) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    script = pasta / "claude_falso.py"
    script.write_text(
        "import json, sys\nfrom pathlib import Path\n"
        "dados = sys.stdin.buffer.read()\n"
        "Path(__file__).with_name('argv.json').write_text(json.dumps({'argv': sys.argv[1:], "
        "'stdin_bytes': len(dados)}), encoding='utf-8')\n"
        "print('## Resumo\\n\\nresumo falso do teste')\n", encoding="utf-8")
    (pasta / "claude.cmd").write_text(f'@"{sys.executable}" "{script}" %*\r\n', encoding="utf-8")
    return pasta / "argv.json"


def _resumo_checks(home: Path, exe: str | None) -> None:
    pasta = home / "Documents" / "Reco"
    alvo = pasta / "gravacao_reco_2026-02-01_10-00-00.mp3"
    alvo.with_suffix(".txt").write_text("Eu: decidimos o prazo.\n", encoding="utf-8")
    eng = Engine(home, exe, path_env=_sem_claude_path())
    try:
        eng.wait_ready(60)
        check(eng.error("resumo.ia", {"path": str(alvo)}) == "claude_missing", "sem claude no PATH")
        check(eng.error("resumo.ia", {"path": str(pasta / "x_reco.mp3")}) == "not_found", "sem .txt")
        check(eng.shutdown(10) == 0, "exit != 0")
    finally:
        eng.kill()
    argv_json = _claude_falso(home / "bin_falso")
    eng = Engine(home, exe, path_env=str(home / "bin_falso") + os.pathsep + _sem_claude_path())
    try:
        eng.wait_ready(60)
        data = eng.ok("resumo.ia", {"path": str(alvo)}, timeout=120)
        check(data["existia"] is False and "## Resumo" in Path(data["path"]).read_text(encoding="utf-8"),
              f"resumo: {data}")
        argv = json.loads(argv_json.read_text(encoding="utf-8"))["argv"]
        check(argv[0] == "-p" and argv[-2:] == ["--model", "sonnet"], f"argv do claude falso: {argv}")
        check(eng.ok("resumo.ia", {"path": str(alvo)})["existia"] is True, "resumo existente")
        check(eng.shutdown(10) == 0, "exit != 0")
        eng.assert_clean_stdout()
    finally:
        eng.kill()


def run_extras(exe: str | None = None) -> None:
    home = make_home({"_migracao": 2})
    eng = Engine(home, exe)
    try:
        eng.wait_ready(60)
        _convert_checks(eng, home)
        check(eng.shutdown(10) == 0, "exit != 0")
        eng.assert_clean_stdout()
    finally:
        eng.kill()
    _resumo_checks(home, exe)
    shutil.rmtree(home, ignore_errors=True)
    print("OK extras: convert 16 kHz mono, sem trilha = no_audio_stream, app.update_check, "
          "claude_missing, claude falso recebeu --model sonnet")
