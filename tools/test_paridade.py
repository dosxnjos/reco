"""Teste da régua `tools/paridade.py` com MP3 sintéticos (nenhuma gravação de ninguém), repetível por qualquer um.

Revisão da Fase 4 do Reco em Rust (12/11/2026): a prova negativa do passo 5 conferia só o veredito e o rc, e duas
mutações de uma linha na régua (Xing desligado, estéreo desligado) passavam nela. Aqui cada caso casa o veredito **e a
lista exata de motivos**. Os MP3 saem pelo `reco.MP3Writer` (o mesmo container do app; regra do CLAUDE.md), numa pasta
temporária que some no fim.

Casos: bom; sistema mudo e mic mudo com o outro lado soando desde o 1º frame (o encoder vaza ~21 ms para o lado mudo);
sistema mudo só depois de 1,5 s; `--sem-sistema`; arquivo de 1 s; mono; corte em fronteira de frame (`xing` sozinho);
corte com o cabeçalho do último frame incompleto (`xing, cauda-corrompida`); `x.txt` vazio, corrido, ausente, em loop e com turnos curtos
iguais; o código de saída do `main` (0, 1 e 2).

    python tools/test_paridade.py [--regua <cópia mutada do paridade.py>]  →  última linha "paridade: falhas 0" (saída 0)

O `--regua` existe para provar o próprio teste: uma cópia da régua com uma checagem desligada tem de fazê-lo falhar.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import re
import sys
import tempfile
from pathlib import Path

import av
import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # console cp1252 (ARMADILHAS 19/08)

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "tools"))
sys.path.insert(0, str(RAIZ))
import reco                                                  # noqa: E402

SR = 16000
DUR_S = 60
RE_FIM = re.compile(r"-> (ok|ALERTA|FALHOU)(?: \((.*)\))?$")
FALHAS: list[str] = []


def carregar_regua(caminho: Path):
    spec = importlib.util.spec_from_file_location("paridade_em_teste", caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def escrever(path: Path, mic: np.ndarray, sis: np.ndarray, canais: int = 2) -> Path:
    """Pelo container do app, em blocos de 0,1 s como a captura."""
    w = reco.MP3Writer(path, SR, SR, canais, 96)
    for i in range(0, len(mic), SR // 10):
        w.feed(mic[i:i + SR // 10], sis[i:i + SR // 10])
    w.close()
    return path


def sinais(dur_s: int = DUR_S) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(voz, ruído, silêncio): seno de 300 Hz no "mic", ruído de banda larga no "sistema", zero exato."""
    n = SR * dur_s
    t = np.arange(n) / SR
    voz = (0.1 * np.sin(2 * np.pi * 300 * t)).astype(np.float32)
    ruido = np.clip(0.3 * np.random.default_rng(1).standard_normal(n), -1, 1).astype(np.float32)
    return voz, ruido, np.zeros(n, np.float32)


def cortar(origem: Path, destino: Path, no_meio: bool) -> Path:
    """Corta o arquivo na metade, no começo de um pacote (fronteira de frame) ou 2 bytes depois (cabeçalho do frame
    incompleto). O Xing do começo segue declarando a duração inteira. Medido em 12/11/2026: só o cabeçalho incompleto
    (1 a 3 bytes) derruba a leitura (`InvalidDataError`); com o cabeçalho inteiro o decoder aceita o frame curto. O
    truncado real da prova antiga (`head -c 3000000`) terminava num pacote de 3 bytes."""
    with av.open(str(origem)) as c:
        posicoes = [p.pos for p in c.demux(audio=0) if p.pos is not None and p.size]
    pos = posicoes[len(posicoes) // 2] + (2 if no_meio else 0)
    destino.write_bytes(origem.read_bytes()[:pos])
    return destino


def com_txt(origem: Path, destino: Path, texto: str | None) -> Path:
    destino.write_bytes(origem.read_bytes())
    if texto is not None:
        destino.with_suffix(".txt").write_text(texto, encoding="utf-8")
    return destino


def confere(regua, nome: str, mp3: Path, flags: set, veredito: str, motivos: list[str], tem: str = "") -> None:
    _v, _a, texto = regua.linha(nome, mp3, flags)
    m = RE_FIM.search(texto)
    achado = (m.group(1), m.group(2).split(", ") if m and m.group(2) else []) if m else ("?", [])
    certo = achado == (veredito, motivos) and tem in texto
    print(f"{'OK ' if certo else 'ERRO'} {nome}: {texto}")
    if not certo:
        FALHAS.append(f"{nome}: esperado {veredito} {motivos}{' com ' + tem if tem else ''}, veio {texto}")


def casos_de_audio(regua, d: Path) -> Path:
    voz, ruido, zero = sinais()
    bom = escrever(d / "gravacao_reco_bom.mp3", voz, ruido)
    confere(regua, "bom", bom, set(), "ok", [])
    rmudo = escrever(d / "gravacao_reco_rmudo.mp3", voz, zero)
    confere(regua, "sistema-mudo-desde-o-1o-frame", rmudo, set(), "FALHOU", ["sistema-mudo"])
    confere(regua, "sistema-mudo-com-sem-sistema", rmudo, {"--sem-sistema"}, "ok", [])
    tarde = voz * (np.arange(len(voz)) >= int(1.5 * SR))
    confere(regua, "sistema-mudo-mic-depois-de-1,5-s",
            escrever(d / "gravacao_reco_rmudo_tarde.mp3", tarde, zero), set(), "FALHOU", ["sistema-mudo"])
    confere(regua, "mic-mudo-desde-o-1o-frame",
            escrever(d / "gravacao_reco_micmudo.mp3", zero, ruido), set(), "FALHOU", ["mic-mudo"])
    v1, r1, _z = sinais(1)
    confere(regua, "curto-1-s", escrever(d / "gravacao_reco_curto.mp3", v1, r1), set(), "ok", [])
    confere(regua, "mono", escrever(d / "gravacao_reco_mono.mp3", voz, ruido, canais=1), set(),
            "FALHOU", ["nao-estereo"], tem="canais=nao-estereo")
    confere(regua, "corte-em-fronteira-de-frame", cortar(bom, d / "gravacao_reco_corte.mp3", no_meio=False), set(),
            "FALHOU", ["xing"], tem="xing=ERRADO")
    confere(regua, "corte-no-meio-de-frame", cortar(bom, d / "gravacao_reco_corte_meio.mp3", no_meio=True), set(),
            "FALHOU", ["xing", "cauda-corrompida"], tem="leitura=ERRO")
    return bom


def casos_de_txt(regua, d: Path, bom: Path) -> None:
    eu, eles = reco._spk_me(), reco._spk_them()
    exigir = {"--exigir-txt"}
    vazio = com_txt(bom, d / "gravacao_reco_vazio.mp3", "(no content recognized)\n")
    confere(regua, "txt-vazio-com-exigir", vazio, exigir, "FALHOU", ["txt-vazio"], tem="txt=vazio")
    confere(regua, "txt-vazio-sem-exigir", vazio, set(), "ok", [], tem="txt=vazio")
    confere(regua, "txt-ausente-com-exigir", com_txt(bom, d / "gravacao_reco_sem.mp3", None), exigir,
            "FALHOU", ["txt-ausente"])
    confere(regua, "txt-corrido-com-exigir", com_txt(bom, d / "gravacao_reco_corrido.mp3", "texto corrido sem rótulo\n"),
            exigir, "FALHOU", ["txt-corrido"])
    turnos = "".join(f"{eu if i % 2 else eles}: sim\n" for i in range(4))
    confere(regua, "turnos-curtos-iguais", com_txt(bom, d / "gravacao_reco_turnos.mp3", turnos), exigir,
            "ok", [], tem="txt=diarizado pior=1")
    confere(regua, "loop-numa-fala", com_txt(bom, d / "gravacao_reco_loop.mp3", f"{eu}: a b a b a b a b\n"), exigir,
            "FALHOU", ["loop"], tem="pior=4")


def casos_de_saida(regua, d: Path) -> None:
    bom, mono = d / "gravacao_reco_bom.mp3", d / "gravacao_reco_mono.mp3"
    for nome, argv, rc in (("rc-passou", [str(bom)], 0), ("rc-reprovou", [str(bom), str(mono)], 1),
                           ("rc-uso", [], 2), ("rc-flag-desconhecida", [str(bom), "--nada"], 2)):
        with contextlib.redirect_stdout(io.StringIO()):
            veio = regua.main(argv)
        print(f"{'OK ' if veio == rc else 'ERRO'} {nome}: rc {veio}")
        if veio != rc:
            FALHAS.append(f"{nome}: rc esperado {rc}, veio {veio}")


def main(argv: list[str]) -> int:
    caminho = Path(argv[argv.index("--regua") + 1]) if "--regua" in argv else RAIZ / "tools" / "paridade.py"
    regua = carregar_regua(caminho)
    with tempfile.TemporaryDirectory(prefix="reco_test_paridade_") as tmp:
        d = Path(tmp)
        bom = casos_de_audio(regua, d)
        casos_de_txt(regua, d, bom)
        casos_de_saida(regua, d)
    for f in FALHAS:
        print(f"FALHA {f}")
    print(f"paridade: falhas {len(FALHAS)}")
    return 1 if FALHAS else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
