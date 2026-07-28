"""Conserta a duração de MP3 gravados pelo Reco antes de 28/07/2026.

Aqueles arquivos saíram sem o header Xing/Info, então todo player estima a
duração pelo bitrate dos primeiros frames — uma gravação que começa em silêncio
lê ~8x mais longa e o VLC mostra o tempo restante pulando.

O conserto é um *remux*: os frames MP3 são copiados byte a byte para um container
novo, que escreve o header. Não há re-encode — o áudio é idêntico.

    python tools/reparar_duracao.py <pasta> [--aplicar]

Sem --aplicar só relata o que seria feito. Cada arquivo só substitui o original
depois de validar que o novo tem a mesma quantidade de amostras e uma duração
declarada coerente. A data de modificação é preservada.
"""
import os, shutil, sys
from pathlib import Path

import av


def declared_and_real(path):
    """(duração no header, duração real decodificando, nº de amostras)."""
    with av.open(str(path)) as c:
        declared = c.duration / av.time_base if c.duration else 0.0
        st = c.streams.audio[0]
        n = sum(f.samples for f in c.decode(st))
        real = n / st.sample_rate
    return declared, real, n


def remux(src: Path, dst: Path):
    with av.open(str(src)) as ic:
        ist = ic.streams.audio[0]
        with av.open(str(dst), "w") as oc:
            ost = oc.add_stream_from_template(ist)   # PyAV 17: não é add_stream(template=)
            for pkt in ic.demux(ist):
                if pkt.dts is None:          # flush packet
                    continue
                pkt.stream = ost
                oc.mux(pkt)


def main(folder: Path, apply: bool):
    files = sorted(p for p in folder.glob("*.mp3"))
    if not files:
        print(f"nenhum .mp3 em {folder}"); return 1
    print(f"{len(files)} arquivo(s) em {folder}\n")
    print(f"{'arquivo':52s} {'declarado':>10s} {'real':>10s}  ação")
    fixed = skipped = failed = 0
    for src in files:
        try:
            declared, real, n = declared_and_real(src)
        except Exception as e:
            print(f"{src.name[:52]:52s} {'?':>10s} {'?':>10s}  ERRO ao ler: {e}")
            failed += 1
            continue
        off = abs(declared - real)
        label = f"{declared:9.0f}s {real:9.0f}s"
        if off <= max(1.0, real * 0.01):
            print(f"{src.name[:52]:52s} {label}  já correto")
            skipped += 1
            continue
        if not apply:
            print(f"{src.name[:52]:52s} {label}  seria corrigido ({declared/real:.1f}x)")
            fixed += 1
            continue
        tmp = src.with_name(src.stem + ".__fix.mp3")
        try:
            remux(src, tmp)
            d2, r2, n2 = declared_and_real(tmp)
            # O remux copia os frames intactos, mas o arquivo novo decodifica
            # ~500 amostras (30 ms) a menos: com o header presente o decodificador
            # passa a descartar o encoder delay do LAME, que antes virava silêncio
            # no começo. Perder mais que ~0,1 s seria outra coisa — aí aborta.
            if abs(n2 - n) > 0.1 * 16000:
                raise ValueError(f"amostras mudaram demais: {n} -> {n2}")
            if abs(d2 - r2) > max(1.0, r2 * 0.01):
                raise ValueError(f"duração ainda errada: {d2:.0f}s vs {r2:.0f}s")
            st = src.stat()
            shutil.move(str(tmp), str(src))          # substitui só após validar
            os.utime(src, (st.st_atime, st.st_mtime))
            print(f"{src.name[:52]:52s} {label}  corrigido -> {d2:.0f}s")
            fixed += 1
        except Exception as e:
            Path(tmp).unlink(missing_ok=True)
            print(f"{src.name[:52]:52s} {label}  FALHOU: {e}")
            failed += 1
    print(f"\n{fixed} corrigido(s), {skipped} já correto(s), {failed} falha(s)")
    if not apply:
        print("(simulação — rode com --aplicar para gravar)")
    return 1 if failed else 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    target = Path(args[0]) if args else Path.home() / "Documents" / "Reco"
    sys.exit(main(target, "--aplicar" in sys.argv))
