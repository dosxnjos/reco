"""Transcreve qualquer áudio/vídeo para .txt pelo pipeline real do Reco.

Feito para AGENTES (Claude Code) lerem áudio/vídeo: roda síncrono, imprime no
stdout o caminho de cada .txt gerado, exit code != 0 em erro. Reusa o caminho
real do app (decode PyAV → VAD → anti-loop → OpenVINO Whisper), sem UI.

Uso:
    python tools/transcrever.py ARQUIVO [ARQUIVO2 ...]
        [--lang pt] [--modelo large-v3-turbo] [--device AUTO]
        [--diarizar] [--aec] [--forcar]

Saída: <arquivo>.txt ao lado do original (ex.: PTT-x.opus -> PTT-x.opus.txt).
Arquivo de saída já existente é pulado (use --forcar para refazer).
--diarizar/--aec só fazem sentido em gravações estéreo do próprio Reco
(L=mic/R=sistema); áudio comum (WhatsApp, vídeo) fica mono, sem as flags.
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


def transcrever_um(tr, src: Path, args) -> Path:
    dst = src.with_suffix(src.suffix + ".txt")
    if dst.exists() and not args.forcar:
        print(f"[pulado, já existe] {dst}")
        return dst
    if sem_trilha_de_audio(src):
        # .txt vazio é a resposta verdadeira ("nada foi dito") e para a
        # retentativa: o coletor mantém a mídia com .txt vazio e não a reenvia
        dst.write_text("", encoding="utf-8")
        print(f"[sem trilha de áudio, .txt vazio] {dst}")
        return dst
    fim = threading.Event()
    resultado = {}

    def done_cb(texto, erro):
        resultado["texto"], resultado["erro"] = texto, erro
        fim.set()

    tr.transcribe(src, lang=args.lang, diarize=args.diarizar, aec=args.aec,
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
                    help="ex.: large-v3-turbo, small (default: config do app)")
    ap.add_argument("--device", default=None,
                    help="AUTO | GPU | NPU | CPU (default: config do app)")
    ap.add_argument("--diarizar", action="store_true",
                    help="só p/ gravações estéreo do Reco (L=mic, R=sistema)")
    ap.add_argument("--aec", action="store_true",
                    help="cancela eco do sistema no mic (exige --diarizar)")
    ap.add_argument("--forcar", action="store_true",
                    help="refaz mesmo se o .txt já existir")
    args = ap.parse_args()

    tr = reco.make_transcriber()
    if tr is None:
        sys.exit("transcrição indisponível: instale openvino-genai (ou mlx no mac)")
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
            transcrever_um(tr, src, args)
        except Exception as e:  # segue o lote; relata no fim
            print(f"[erro] {e}", file=sys.stderr)
            erros += 1
    sys.exit(1 if erros else 0)


if __name__ == "__main__":
    main()
