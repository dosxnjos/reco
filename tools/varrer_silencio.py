"""Varre MP3 estéreo do Reco atrás de canal em silêncio digital (zero exato).

Somente leitura. Zero exato é a assinatura do endpoint que não entrega pacote:
o `soundcard` fabrica `numpy.zeros` pelo relógio quando o loopback está mudo
(docs/ARMADILHAS.md § "O `soundcard` fabrica silêncio…"). Foi assim que o PDI de
29/09/2026 saiu sem a voz da Andressa: R (sistema) com 424 de 424 s em zero.

Uso:
    python tools/varrer_silencio.py [arquivos ou pastas ...]

Sem argumento varre `~/Documents/Reco` (`*reco*.mp3`, ignorando `_alinhado`; o
filtro vale só para pasta, arquivo passado pelo nome é sempre lido). `dur` é o
piso em segundos inteiros (a janela final parcial não conta). ⚠️ "zero exato"
depende do encoder: um MP3 sintético com R zerado deixou resíduo de 0,001–0,006
nas janelas de borda; nos arquivos reais do Reco isso não apareceu.
Uma linha por arquivo (segundos inteiros, janelas de 1 s):

    <nome> dur=<s> r_zero_inicio=<s> r_zero_total=<s> r_maior_seq=<s> mic_maior_seq_zero=<s>

- `r_zero_inicio`: segundos de R em zero exato antes do 1º som (= `dur` se R
  nunca tocou). É o número que separa o incidente de reunião boa: nas gravações
  boas medidas em 30/09/2026 o maior foi 73 s; no PDI, 424 s.
- `r_zero_total` / `r_maior_seq`: total e maior sequência de segundos de R em
  zero (comum em gravação boa: até 622 s seguidos, por isso não alarma sozinho).
- `mic_maior_seq_zero`: maior sequência de segundos de L (mic) em zero.

Lê em streaming (memória constante): o arquivo de 7,7 h de 13/09 não cabe
decodificado inteiro. Arquivo que não é estéreo vira `nao-estereo`; falha de
leitura vira `ERRO <motivo>`.
"""
import glob
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

import av
import numpy as np


def medir(path: str) -> dict:
    """Mede o zero exato por canal em janelas de 1 s. Streaming, um passe."""
    c = av.open(path)
    try:
        if not c.streams.audio:
            raise ValueError("sem stream de áudio")
        st = c.streams.audio[0]
        sr, ch = st.rate, st.channels
        if ch != 2:
            return {"nao_estereo": True}
        n = r_total = r_seq = r_maior = m_seq = m_maior = 0
        r_ini = None                      # índice do 1º segundo com som em R
        resto = np.empty((2, 0), dtype=np.float32)

        def segundo(bloco):
            nonlocal n, r_total, r_seq, r_maior, m_seq, m_maior, r_ini
            r_zero = not bloco[1].any()
            m_zero = not bloco[0].any()
            if r_ini is None and not r_zero:
                r_ini = n
            r_total += r_zero
            r_seq = r_seq + 1 if r_zero else 0
            r_maior = max(r_maior, r_seq)
            m_seq = m_seq + 1 if m_zero else 0
            m_maior = max(m_maior, m_seq)
            n += 1

        for f in c.decode(st):
            x = f.to_ndarray()
            if not f.format.is_planar:    # intercalado: (1, amostras*canais)
                x = x.reshape(-1, ch).T
            resto = np.concatenate([resto, x], axis=1) if resto.size else x
            while resto.shape[1] >= sr:
                segundo(resto[:, :sr])
                resto = resto[:, sr:]
        return {"dur": n, "r_ini": n if r_ini is None else r_ini,
                "r_total": r_total, "r_maior": r_maior, "mic_maior": m_maior}
    finally:
        c.close()


def linha(path: str) -> str:
    nome = os.path.basename(path)
    try:
        m = medir(path)
    except Exception as e:
        return f"{nome} ERRO {e}"
    if m.get("nao_estereo"):
        return f"{nome} nao-estereo"
    return (f"{nome} dur={m['dur']} r_zero_inicio={m['r_ini']} "
            f"r_zero_total={m['r_total']} r_maior_seq={m['r_maior']} "
            f"mic_maior_seq_zero={m['mic_maior']}")


def listar(alvos: list[str]) -> list[str]:
    if not alvos:
        alvos = [os.path.expanduser("~/Documents/Reco")]
    arquivos = []
    for a in alvos:
        a = os.path.expanduser(a)
        if os.path.isdir(a):
            # só a varredura de pasta pula os `_alinhado` (re-encode, não é captura)
            arquivos += [f for f in glob.glob(os.path.join(a, "*reco*.mp3"))
                         if "_alinhado" not in os.path.basename(f)]
        else:
            arquivos.append(a)
    return sorted(arquivos)


def main(argv: list[str]) -> int:
    arquivos = listar(argv)
    if not arquivos:
        print("nenhum arquivo", file=sys.stderr)
        return 1
    # as_completed (não map): um arquivo de horas não trava a fila das linhas
    # prontas; cada linha traz o nome, então a ordem de saída não importa.
    with ProcessPoolExecutor(min(6, len(arquivos))) as ex:
        futs = {ex.submit(linha, a): a for a in arquivos}
        for fut in as_completed(futs):
            try:
                print(fut.result(), flush=True)
            except Exception as e:      # worker morto (OOM, crash do libav)
                print(f"{os.path.basename(futs[fut])} ERRO {e!r}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
