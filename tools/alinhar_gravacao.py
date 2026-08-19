"""Alinha os canais de gravacoes JA FEITAS (item 1.3 do roadmap 2026-08-19).

As gravacoes anteriores a 19/08/2026 tem os dois canais defasados por centenas de
milissegundos (latencia de buffer entre os streams do WASAPI, nao acustica): +203 ms
num arquivo medido, -399 ms noutro, e a defasagem AINDA VARIA dentro do mesmo
arquivo (deriva de clock). Acima de ~50 ms o ouvido deixa de integrar a copia como
reverberacao e ouve eco separado — foi a queixa que abriu o roadmap.

    python tools/alinhar_gravacao.py <mp3|pasta> [--aplicar] [--janela 30]

Sem `--aplicar`, so RELATA (atraso por trecho, mediana e faixa). Com `--aplicar`,
escreve `<nome>_alinhado.mp3` ao lado do original — **nunca sobrescreve**, ao
contrario de `tools/reparar_duracao.py`: aqui o audio e re-encodado (deslocar um
canal nao da por remux), entao o original tem que sobreviver para comparacao.

O deslocamento e reestimado a cada `--janela` segundos, o que corrige a deriva
dentro do proprio arquivo. Trecho sem correlacao confiavel herda o ultimo
deslocamento valido (nao inventa).

⚠️ Streaming, um passe so, sem `seek`: decodificar 32 min de estereo de uma vez sao
249 MB e ja estourou a memoria desta maquina; e reposicionar por `seek` em MP3 e
aproximado, o que emendaria os trechos com salto/repeticao. O buffer guarda apenas
janela + folga.

Formato de saida: o da gravacao (16 kHz estereo, 96 kbps ABR, header Xing pelo
container — regra "MP3 sempre por container" do CLAUDE.md).
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import av                                                          # noqa: E402

import reco                                                        # noqa: E402

SR = reco.OUT_SR
FOLGA_S = 0.6          # > ALIGN_MAXLAG_S (0.5): o quanto o mic pode ser puxado


def blocos_do_mp3(path):
    """Gera (mic, sistema) em float32 16 kHz, quadro a quadro."""
    with av.open(str(path)) as cont:
        rs = av.audio.resampler.AudioResampler(format="fltp", layout="stereo", rate=SR)
        for frame in cont.decode(audio=0):
            for r_ in rs.resample(frame):
                a = r_.to_ndarray().astype(np.float32)
                yield a[0], (a[1] if a.shape[0] > 1 else a[0])


def processa(path, aplicar, janela_s):
    """Percorre o arquivo uma vez; relata e (se aplicar) escreve o alinhado."""
    J = int(janela_s * SR)
    F = int(FOLGA_S * SR)
    destino = path.with_name(path.stem + "_alinhado.mp3")
    writer = (reco.MP3Writer(destino, SR, SR, 2, reco.MP3_BR) if aplicar else None)

    buf_m = np.zeros(0, np.float32)
    buf_s = np.zeros(0, np.float32)
    inicio = 0            # índice global da amostra 0 dos buffers
    pos = 0               # próxima amostra global a escrever
    ultimo_d = 0
    medidos, usados, n_trechos = [], [], 0

    def trata(fim_global, final=False):
        """Processa janelas completas disponíveis nos buffers."""
        nonlocal buf_m, buf_s, inicio, pos, ultimo_d, n_trechos
        while True:
            # a janela [pos, pos+J) precisa de folga à frente, salvo no fim
            precisa = pos + J + (0 if final else F)
            if fim_global < precisa and not final:
                return
            j = min(pos + J, fim_global)
            if j - pos < 5 * SR:                  # cauda curta: sai com o resto
                if final and j > pos:
                    escreve_trecho(pos, j, ultimo_d)
                    pos = j
                return
            a, b = pos - inicio, j - inicio
            d, q = reco.estimar_offset(buf_m[a:b], buf_s[a:b], sr=SR)
            n_trechos += 1
            if q >= reco.ALIGN_Q_MIN:
                medidos.append((pos / SR, d, q))
                ultimo_d = d
            escreve_trecho(pos, j, ultimo_d)
            pos = j
            # descarta o que já saiu, guardando a folga de trás
            corta = max(0, (pos - F) - inicio)
            if corta > 0:
                buf_m = buf_m[corta:]
                buf_s = buf_s[corta:]
                inicio += corta

    def escreve_trecho(ini, fim, d):
        usados.append(d)
        if writer is None:
            return
        sistema = buf_s[ini - inicio:fim - inicio]
        # o mic que corresponde a [ini, fim) do sistema começa em ini + d
        alvo = np.zeros(fim - ini, np.float32)
        a, b = ini + d - inicio, fim + d - inicio
        lo, hi = max(a, 0), min(b, len(buf_m))
        if hi > lo:
            alvo[lo - a:hi - a] = buf_m[lo:hi]
        writer.feed(alvo, sistema, 1.0, 1.0)

    total = 0
    for m, s in blocos_do_mp3(path):
        buf_m = np.concatenate([buf_m, m])
        buf_s = np.concatenate([buf_s, s])
        total += len(m)
        trata(total)
    trata(total, final=True)
    if writer is not None:
        writer.close()

    print(f"[{path.name}] {total/SR/60:.1f} min | "
          f"{len(medidos)}/{n_trechos} trechos com correlacao confiavel")
    if not medidos:
        print("   sem eco medivel (gravacao de fone?) — nada a alinhar")
        if writer is not None:
            destino.unlink(missing_ok=True)
        return False
    ds = np.array([d for _, d, _ in medidos])
    print(f"   atraso: mediana {np.median(ds):+.0f} amostras "
          f"({np.median(ds)/SR*1000:+.0f} ms), faixa {ds.min():+d}..{ds.max():+d} "
          f"({ds.min()/SR*1000:+.0f}..{ds.max()/SR*1000:+.0f} ms)")
    if writer is None:
        print("   (sem --aplicar: nada foi escrito)")
        return True
    print(f"   escrito: {destino.name} ({destino.stat().st_size/1024:.0f} KB)")
    return destino


def confere(destino, janela_s):
    """Mede o residual no arquivo escrito, por janela, sem carregar tudo."""
    J = int(janela_s * SR)
    buf_m = np.zeros(0, np.float32)
    buf_s = np.zeros(0, np.float32)
    res = []
    for m, s in blocos_do_mp3(destino):
        buf_m = np.concatenate([buf_m, m])
        buf_s = np.concatenate([buf_s, s])
        while len(buf_m) >= J:
            d, q = reco.estimar_offset(buf_m[:J], buf_s[:J], sr=SR)
            if q >= reco.ALIGN_Q_MIN:
                res.append(d)
            buf_m, buf_s = buf_m[J:], buf_s[J:]
    if not res:
        return None
    return max(res, key=abs)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    alvo = Path(argv[1])
    aplicar = "--aplicar" in argv
    janela_s = 30.0
    if "--janela" in argv:
        janela_s = float(argv[argv.index("--janela") + 1])
    arquivos = ([alvo] if alvo.is_file()
                else sorted(p for p in alvo.glob("*.mp3")
                            if "_alinhado" not in p.stem))
    if not arquivos:
        print(f"nada para processar em {alvo}")
        return 2
    for p in arquivos:
        try:
            saida = processa(p, aplicar, janela_s)
            if aplicar and isinstance(saida, Path):
                pior = confere(saida, janela_s)
                if pior is None:
                    print("   ! nao deu para conferir (correlacao fraca depois)")
                else:
                    print(f"   residual: pior trecho {pior:+d} amostras "
                          f"({pior/SR*1000:+.1f} ms)")
        except Exception as e:                     # arquivo corrompido, disco cheio…
            print(f"[{p.name}] FALHOU: {e}")
        print()
    if not aplicar:
        print("Rode de novo com --aplicar para escrever os *_alinhado.mp3 "
              "(o original nunca e sobrescrito).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
