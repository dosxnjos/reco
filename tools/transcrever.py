"""Transcreve qualquer áudio/vídeo para .txt pelo pipeline real do Reco.

Feito para AGENTES (Claude Code) lerem áudio/vídeo: roda síncrono, imprime no
stdout o caminho de cada .txt gerado, exit code != 0 em erro. Reusa o caminho
real do app (decode PyAV → VAD → anti-loop → OpenVINO Whisper), sem UI.

Uso:
    python tools/transcrever.py ARQUIVO [ARQUIVO2 ...]
        [--lang pt] [--modelo large-v3-turbo] [--device AUTO]
        [--diarizar] [--aec] [--texto-corrido] [--forcar]

Gravação do próprio Reco (`gravacao_reco_*.mp3`, etiqueta `reco` no nome):
sai IGUAL ao botão "Salvar + transcrever" do app — diarizada por canal
(`Eu:` / `Interlocutor(es):`) e com cancelamento de eco, conforme `diarize` e
`aec` do `~/.reco_config.json`. Sem flag nenhuma. Na pasta de gravações do app
sai em `x.txt` (o nome que o app grava e a biblioteca lê); fora dela, em
`x.mp3.txt` (contrato dos chamadores). Até 11/11/2026 o padrão era texto corrido
em `x.mp3.txt`: um antigo assim não conta como pronto e o `x.txt` nasce ao lado,
sem apagar nada; um antigo já diarizado (feito com --diarizar) é aproveitado.
Modelo e dispositivo NÃO seguem a config do app (NPU quebra aqui): AUTO.

Qualquer outro áudio (WhatsApp, vídeo, Instagram): texto corrido em
`<arquivo>.txt` ao lado do original (ex.: PTT-x.opus -> PTT-x.opus.txt).

--texto-corrido força texto corrido numa gravação do Reco (só o conteúdo, sem
autoria; sai em `x.mp3.txt` para não colidir com o `x.txt` do app).
--diarizar/--aec forçam a separação em arquivo sem a etiqueta (estéreo L=mic,
R=sistema). Saída já existente é pulada (use --forcar para refazer).
"""

import argparse
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import reco  # noqa: E402


def sem_trilha_de_audio(src: Path) -> bool:
    """Vídeo sem som (ex.: o GIF que o WhatsApp manda como mp4) não tem o que
    transcrever, e o decode do app quebra com `IndexError` em
    `streams.audio[0]`. Medido em 25/09/2026 nos 2 vídeos do coletor da central.
    Na dúvida devolve False e deixa o pipeline real dizer o que houve."""
    try:
        import av
        with av.open(str(src)) as cont:
            return not cont.streams.audio
    except Exception:
        return False


def canais(src: Path) -> int | None:
    """Canais da 1ª trilha de áudio, só para a mensagem de modo; None se não der."""
    try:
        import av
        with av.open(str(src)) as cont:
            return cont.streams.audio[0].codec_context.channels
    except Exception:
        return None


def opcoes(src: Path, cfg: dict, args) -> tuple[bool, bool]:
    """(diarize, aec) com a MESMA regra de `App._run_transcriber` (reco.py):
    gravação do Reco (etiqueta no nome) segue `diarize`/`aec` da config; qualquer
    outro arquivo sai texto corrido. As flags forçam; `--texto-corrido` desliga.
    Sem isso, sessões que rodavam o script sem flag (como mandam as docs)
    gravavam texto corrido onde o app teria diarizado (11/11/2026)."""
    if args.texto_corrido:
        return False, False
    reco_rec = reco.is_reco_recording(src)
    diarize = args.diarizar or (reco_rec and bool(cfg.get("diarize")))
    aec = args.aec or (reco_rec and bool(cfg.get("aec")))
    # o AEC só existe dentro da diarização (ref = canal do sistema), como no app
    return diarize, aec and diarize


def na_pasta_do_reco(src: Path, cfg: dict) -> bool:
    """O arquivo está na pasta de gravações do app (`output_dir` ou Documents\\Reco)?"""
    pasta = Path(cfg["output_dir"]) if cfg.get("output_dir") else reco.default_output_dir()
    try:
        return src.resolve().parent == pasta.resolve()
    except OSError:
        return False


def destino(src: Path, args, cfg: dict) -> Path:
    """Gravação do Reco NA PASTA DO APP → `x.txt`, o nome do `_autosave_txt` e o
    único que a biblioteca lê. Todo o resto → `<arquivo>.<ext>.txt`, o contrato
    dos chamadores (coletor e importador do WhatsApp, `instagram_post.py`), que
    calculam `midia + ".txt"` — inclusive uma gravação do Reco que chegue a eles
    como anexo com o nome original."""
    if (reco.is_reco_recording(src) and not args.texto_corrido
            and na_pasta_do_reco(src, cfg)):
        return src.with_suffix(".txt")
    return src.with_name(src.name + ".txt")


RE_DIARIZADA = None


def diarizada(p: Path) -> bool:
    """O .txt já separa quem falou (linhas `Eu:`/`Interlocutor(es):` do `_merge`)?"""
    global RE_DIARIZADA
    if RE_DIARIZADA is None:
        import re
        rotulos = "|".join(re.escape(s) for s in {reco._spk_me(), reco._spk_them(),
                                                   "Eu", "Interlocutor(es)"})
        RE_DIARIZADA = re.compile(rf"^({rotulos}): ", re.M)
    try:
        return bool(RE_DIARIZADA.search(p.read_text(encoding="utf-8", errors="replace")))
    except OSError:
        return False


def transcrever_um(tr, src: Path, args, cfg: dict) -> Path:
    dst = destino(src, args, cfg)
    if dst.exists() and not args.forcar:
        print(f"[pulado, já existe] {dst}")
        if opcoes(src, cfg, args)[0] and not diarizada(dst):
            print(f"  [{src.name}] {dst.name} está em texto corrido (feito antes de "
                  "11/11/2026?); --forcar refaz separado por quem falou",
                  file=sys.stderr, flush=True)
        return dst
    antigo = src.with_name(src.name + ".txt")
    if antigo != dst and antigo.exists():
        # `x.mp3.txt` do script antigo: a maioria é texto corrido (o padrão era sem
        # flag), mas há os feitos com --diarizar. Diarizado já serve; corrido não.
        if diarizada(antigo) and not args.forcar:
            print(f"[pulado, já existe diarizado no nome antigo] {antigo}")
            return antigo
        print(f"  [{src.name}] {antigo.name} (nome antigo) é texto corrido; "
              f"gerando {dst.name} ao lado", file=sys.stderr, flush=True)
    if sem_trilha_de_audio(src):
        # .txt vazio é a resposta verdadeira ("nada foi dito") e para a
        # retentativa: o coletor mantém a mídia com .txt vazio e não a reenvia
        dst.write_text("", encoding="utf-8")
        print(f"[sem trilha de áudio, .txt vazio] {dst}")
        return dst
    diarize, aec = opcoes(src, cfg, args)
    modo = ("diarizado + AEC" if aec else "diarizado") if diarize else "texto corrido"
    if diarize and canais(src) == 1:   # decode_16k devolve 1 canal: sai corrido
        modo = "texto corrido (arquivo mono, sem canal para separar)"
    print(f"  [{src.name}] modo: {modo}", file=sys.stderr, flush=True)
    fim = threading.Event()
    resultado = {}

    def done_cb(texto, erro):
        resultado["texto"], resultado["erro"] = texto, erro
        fim.set()

    tr.transcribe(src, lang=args.lang, diarize=diarize, aec=aec,
                  progress_cb=lambda m: print(f"  [{src.name}] {m}",
                                              file=sys.stderr, flush=True),
                  done_cb=done_cb)
    fim.wait()
    if resultado.get("erro"):
        raise RuntimeError(f"{src.name}: {resultado['erro']}")
    dst.write_text(resultado.get("texto") or "", encoding="utf-8")
    print(dst)
    return dst


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("arquivos", nargs="+")
    ap.add_argument("--lang", default="pt")
    ap.add_argument("--modelo", default=None,
                    help="ex.: large-v3-turbo, small (default: padrão de fábrica)")
    ap.add_argument("--device", default=None,
                    help="AUTO | GPU | NPU | CPU (default: AUTO; NPU quebra aqui)")
    ap.add_argument("--diarizar", action="store_true",
                    help="força a separação por canal (gravação do Reco já "
                         "diariza sozinha, como no app)")
    ap.add_argument("--aec", action="store_true",
                    help="força o cancelamento de eco (só vale com diarização)")
    ap.add_argument("--texto-corrido", action="store_true",
                    help="gravação do Reco sem separar quem falou (sai x.mp3.txt)")
    ap.add_argument("--forcar", action="store_true",
                    help="refaz mesmo se o .txt já existir")
    args = ap.parse_args()
    if args.texto_corrido and (args.diarizar or args.aec):
        ap.error("--texto-corrido não combina com --diarizar/--aec")

    tr = reco.make_transcriber()
    if tr is None:
        sys.exit("transcrição indisponível: instale openvino-genai (ou mlx no mac)")
    cfg = reco.load_config()   # persist=False: só lê (armadilha 029)
    # Modelo e dispositivo NÃO vêm da config do app, de propósito: NPU escolhida no
    # app quebra este script (armadilha 028) e os lotes de fundo (instagram_post,
    # importador do WhatsApp) não passam --device. Padrão de fábrica: AUTO.
    if args.modelo:
        tr.set_model(args.modelo)
    if args.device:
        tr.set_device(args.device)

    erros = 0
    for f in args.arquivos:
        src = Path(f)
        if not src.exists():
            print(f"[não existe] {src}", file=sys.stderr)
            erros += 1
            continue
        try:
            transcrever_um(tr, src, args, cfg)
        except Exception as e:  # segue o lote; relata no fim
            print(f"[erro] {e}", file=sys.stderr)
            erros += 1
    sys.exit(1 if erros else 0)


if __name__ == "__main__":
    main()
