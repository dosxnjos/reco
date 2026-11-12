"""Régua de paridade por MP3: junta as réguas que leem o disco numa linha por gravação.

Fase 4 do Reco em Rust (roadmap/2026-11-11-melhoria-reco-em-rust-fase-4.md, passo 4); vira o gate da Fase 5.
Só lê o MP3 e o `x.txt` ao lado. Nada é reescrito; `--txt-contra-script` trabalha numa cópia em pasta temporária.

    python tools/paridade.py <mp3> [<mp3> ...] [--sem-sistema] [--exigir-txt] [--txt-contra-script] [--anonimo]

Uma linha por arquivo:

    <nome> dur= xing= r_zero_inicio= mic_zero_max= alinhamento= txt= pior= [script=] -> ok|ALERTA|FALHOU [(motivos)]

- `xing`: o cabeçalho declara a duração real, pelo critério do `reparar_duracao.py`: |declarado - real| <= max(1, 1% do real).
- `r_zero_inicio` / `mic_zero_max`: segundos em zero exato (`varrer_silencio.medir`): sistema antes do 1º som e maior
  sequência do mic.
- `alinhamento`: veredito do `varrer_acervo` (`ok`, `salto`, `desalinhado`, `sem correlacao`), janela de 15 s.
- `txt`: `diarizado`, `corrido`, `vazio` (o app grava "(no content recognized)") ou `ausente`; `pior`: maior repetição
  consecutiva de um n-grama no `x.txt`, fala a fala e sem os rótulos (`test_antiloop.pior`; só o número, nunca o texto).
- `script`: com `--txt-contra-script`, o `x.txt` do app comparado byte a byte com o que o `tools/transcrever.py` gera
  da mesma gravação, com o modelo, o device e o idioma do app (o script ignora os do config, por isso as flags).

FALHOU: Xing errado; não estéreo; sistema em zero o arquivo inteiro (sem `--sem-sistema`); mic em zero o arquivo inteiro
("inteiro" = todos os segundos menos 1, pelo vazamento do encoder no 1º frame: `limiar_mudo`); erro de leitura (o arquivo
cortado no meio de um frame sai `leitura=ERRO`, com o Xing medido mesmo assim); `pior` > 3; com `--txt-contra-script`,
`script` diferente de `igual` (`DIFERENTE`, `erro`, `sem-txt`); com `--exigir-txt`, `x.txt` ausente, corrido ou vazio.
ALERTA (não reprova): `r_zero_inicio` >= 60 s (o maior em reunião boa foi 73 s); alinhamento `salto` ou `desalinhado`.
Limite conhecido: com o mic falando desde o 1º frame, o mesmo vazamento zera o `r_zero_inicio` e esse ALERTA não sai.
Teste da régua (MP3 sintéticos, sem gravação de ninguém): `python tools/test_paridade.py`.
`--anonimo` troca o nome por G01, G02… na ordem dada (para relatório em repo público).
Saída: 0 = PASSOU, 1 = alguma FALHOU, 2 = uso errado.
"""
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

import av

sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # console cp1252 (ARMADILHAS 19/08)

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "tools"))
sys.path.insert(0, str(RAIZ))
import reco                                                  # noqa: E402
import transcrever                                           # noqa: E402
from reparar_duracao import declared_and_real                # noqa: E402
from test_antiloop import pior                               # noqa: E402
from varrer_acervo import mede, resume                       # noqa: E402
from varrer_silencio import medir                            # noqa: E402

SEM_CONTEUDO = "(no content recognized)"   # o que o app grava em transcrição vazia (reco.py:4184)
R_ZERO_ALERTA_S = 60                        # tools/varrer_silencio.py:20-22
PIOR_MAX = 3                                # critério do test_antiloop
JANELA_S = 15.0
FLAGS = {"--sem-sistema", "--exigir-txt", "--txt-contra-script", "--anonimo"}


def duracao_tolerante(mp3: Path) -> tuple[float, float]:
    """(declarado, real) pulando pacote que não decodifica. Arquivo cortado no meio de um frame (processo morto
    escrevendo, `head -c`) tem só o último pacote ruim, e o `declared_and_real` desiste nele (medido em 12/11/2026)."""
    with av.open(str(mp3)) as c:
        declarado = c.duration / av.time_base if c.duration else 0.0
        st = c.streams.audio[0]
        n = 0
        for pkt in c.demux(st):
            try:
                n += sum(f.samples for f in pkt.decode())
            except av.InvalidDataError:
                continue
        return declarado, n / st.sample_rate


def medir_audio(mp3: Path) -> dict:
    """Duração, Xing, zeros por canal e alinhamento. Cauda corrompida vira `erro_leitura` depois do Xing medido;
    arquivo que nem abre sobe como exceção."""
    m = {}
    try:
        declarado, real, _n = declared_and_real(mp3)
    except av.InvalidDataError:
        declarado, real = duracao_tolerante(mp3)
        m["erro_leitura"] = "cauda-corrompida"
    m.update(dur=real, xing_ok=abs(declarado - real) <= max(1.0, real * 0.01))
    if m.get("erro_leitura"):
        return m
    zeros = medir(str(mp3))
    if zeros.get("nao_estereo"):
        m["nao_estereo"] = True
        return m
    # `medir` conta segundos inteiros (`dur` = piso; `r_ini` = `dur` se o sistema nunca tocou): compara-se com ele
    m.update(r_ini=zeros["r_ini"], r_total=zeros["r_total"], mic_maior=zeros["mic_maior"], seg=zeros["dur"])
    serie, n, dur_s = mede(mp3, JANELA_S)
    m["alinhamento"] = resume(mp3.name, serie, n, dur_s)["veredito"]
    return m


def ler_txt(mp3: Path) -> tuple[str, int | None]:
    """(estado do x.txt, pior repetição sem os rótulos de quem fala)."""
    txt = mp3.with_suffix(".txt")
    if not txt.exists():
        return "ausente", None
    texto = txt.read_text(encoding="utf-8", errors="replace")
    if texto.strip() in ("", SEM_CONTEUDO):
        return "vazio", 1
    estado = "diarizado" if transcrever.diarizada(txt) else "corrido"
    if estado == "corrido":
        return estado, pior(texto)[0]
    # Diarizado: uma fala por linha. Mede-se fala a fala (o `test_antiloop` vê um canal só), senão "sim" / "sim" / "sim" /
    # "sim" em quatro turnos contaria como loop. diarizada() já montou o regex dos rótulos do app.
    falas = transcrever.RE_DIARIZADA.sub("", texto).splitlines()
    return estado, max((pior(f)[0] for f in falas if f.strip()), default=1)


def idioma() -> str:
    """O que o app passa ao Whisper (`_whisper_lang`, reco.py:3743-3744): pt ou en."""
    return "pt" if reco.LANG == "pt" else "en"


def contra_script(mp3: Path) -> str:
    """Transcreve uma cópia (fora da pasta do app sai `x.mp3.txt`) e compara com o `x.txt` do app."""
    txt_app = mp3.with_suffix(".txt")
    if not txt_app.exists():
        return "sem-txt"
    cfg = reco.load_config()   # só lê (armadilha 029)
    with tempfile.TemporaryDirectory(prefix="reco_paridade_") as tmp:
        copia = Path(tmp) / mp3.name
        shutil.copy2(mp3, copia)
        cmd = [sys.executable, str(RAIZ / "tools" / "transcrever.py"), str(copia),
               "--modelo", str(cfg.get("model")), "--device", str(cfg.get("device")), "--lang", idioma()]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        saida = copia.with_name(copia.name + ".txt")
        if r.returncode != 0 or not saida.exists():
            return "erro"
        a = txt_app.read_bytes()
        b = saida.read_bytes()
    vazio = (SEM_CONTEUDO.encode(), b"")
    return "igual" if a == b or (a.strip() in vazio and b.strip() in vazio) else "DIFERENTE"


def limiar_mudo(seg: int) -> int:
    """Segundos em zero que contam como "mudo do começo ao fim". O encoder (libmp3lame, também pelo `reco.MP3Writer`)
    vaza ~21 ms do canal com som para o mudo no 1º frame: com som desde o início, o 1º segundo do lado mudo não é zero
    exato e a conta do arquivo inteiro nunca fecha (revisão da Fase 4, 12/11/2026; medido até com ruído saturado). Tolera
    1 s; arquivo de menos de 2 s exige todos."""
    return seg - 1 if seg >= 2 else seg


def julgar_canais(m: dict, flags: set, falhas: list, alertas: list) -> None:
    """Regras dos dois canais (só em arquivo estéreo lido inteiro)."""
    limiar = limiar_mudo(m["seg"])
    if m["r_total"] >= limiar and "--sem-sistema" not in flags:
        falhas.append("sistema-mudo")
    if m["mic_maior"] >= limiar:
        falhas.append("mic-mudo")
    if m["r_ini"] >= R_ZERO_ALERTA_S and "sistema-mudo" not in falhas:
        alertas.append("r_zero_inicio")
    if m["alinhamento"] in ("salto", "desalinhado"):
        alertas.append(m["alinhamento"])


def julgar(m: dict, txt: str, p: int | None, script: str | None, flags: set) -> tuple[str, list]:
    """(veredito, motivos) pelas regras do passo 4."""
    falhas, alertas = [], []
    if not m["xing_ok"]:
        falhas.append("xing")
    if m.get("erro_leitura"):
        falhas.append(m["erro_leitura"])
    elif m.get("nao_estereo"):
        falhas.append("nao-estereo")
    else:
        julgar_canais(m, flags, falhas, alertas)
    if p is not None and p > PIOR_MAX:
        falhas.append("loop")
    if script is not None and script != "igual":   # DIFERENTE, ou a comparação pedida não rodou (erro, sem-txt)
        falhas.append(f"script-{script}")
    if "--exigir-txt" in flags and txt in ("ausente", "corrido", "vazio"):
        falhas.append(f"txt-{txt}")
    if falhas:
        return "FALHOU", falhas
    return ("ALERTA", alertas) if alertas else ("ok", [])


def linha(nome: str, mp3: Path, flags: set) -> tuple[str, str, str]:
    """(veredito, alinhamento, linha) de um arquivo."""
    try:
        m = medir_audio(mp3)
    except Exception as e:  # noqa: BLE001  (arquivo corrompido, codec, caminho)
        return "FALHOU", "-", f"{nome} ERRO {type(e).__name__}: {e} -> FALHOU (leitura)"
    txt, p = ler_txt(mp3)
    script = contra_script(mp3) if "--txt-contra-script" in flags else None
    veredito, motivos = julgar(m, txt, p, script, flags)
    if m.get("erro_leitura"):
        meio = "leitura=ERRO"
    elif m.get("nao_estereo"):
        meio = "canais=nao-estereo"
    else:
        meio = (f"r_zero_inicio={m['r_ini']} mic_zero_max={m['mic_maior']} "
                f"alinhamento={m['alinhamento'].replace(' ', '_')}")
    s = (f"{nome} dur={m['dur']:.1f} xing={'ok' if m['xing_ok'] else 'ERRADO'} {meio} "
         f"txt={txt} pior={'-' if p is None else p}" + (f" script={script}" if script else ""))
    alin = m.get("alinhamento", "-").replace(" ", "_")
    return veredito, alin, f"{s} -> {veredito}" + (f" ({', '.join(motivos)})" if motivos else "")


def main(argv: list[str]) -> int:
    flags = {a for a in argv if a.startswith("--")}
    arquivos = [Path(a) for a in argv if not a.startswith("--")]
    if not arquivos or flags - FLAGS:
        print(__doc__)
        return 2
    cont, alins = Counter(), Counter()
    for i, mp3 in enumerate(arquivos, 1):
        nome = f"G{i:02d}" if "--anonimo" in flags else mp3.name
        veredito, alin, texto = linha(nome, mp3, flags)
        cont[veredito] += 1
        alins[alin] += 1
        print(texto, flush=True)
    print("vereditos: " + ", ".join(f"{k}={cont[k]}" for k in ("ok", "ALERTA", "FALHOU"))
          + " | alinhamento: " + ", ".join(f"{k}={v}" for k, v in sorted(alins.items())))
    ok = cont["FALHOU"] == 0
    print("PASSOU" if ok else "REPROVOU")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
