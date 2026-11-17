"""Régua local da rede de segurança do `cancel_echo` (issue dosxnjos/reco#21, E4b).

Fora do `reco.py` porque ele não cresce (trava `tools/tamanho.json`); o `cancel_echo` passa a saída
pela `sem_piora` logo antes do `istft`, depois da pós-supressão.

O defeito (E4a, legado-024): a rede de hoje compara o RMS da chamada inteira (`r_out > r_in *
1,05`) e o dano é local. Quando o mic quase não ouve a caixa (acoplamento baixo), o filtro de
mínimos quadrados usa a referência para explicar a voz do usuário e, onde só o interlocutor fala,
SOMA o eco estimado a um mic quase mudo. A voz e o silêncio diluem esse aumento e a razão global
fica abaixo de 1,05. No sintético o ERLE negativo saiu só com acoplamento baixo; um salto de
300 ms com acoplamento de −12 dB deu ERLE positivo. No acervo os 2 casos de ERLE ≤ 0 têm salto
(§ 8.5 do roadmap do salto): se o salto também produz esse dano, só a medição real vai dizer.

Por que por QUADRO e não por bloco de 2 s, como o roadmap de 30/08 desenhou: o filtro do bloco é o
mínimo de `|Mb - Xb h|^2 + lam |h|^2`, e `h = 0` é candidato, então o resíduo do bloco inteiro nunca
passa a entrada do bloco (por bin, por construção). A régua por bloco não dispara nunca (medido em
sinal sintético: no máximo 1 + 3e-8, arredondamento). O aumento mora DENTRO do bloco, nos quadros em
que só o interlocutor fala.

Por que DEPOIS da pós-supressão e não no resíduo linear: medido em sinal sintético, comparar o
resíduo linear (`Mb - y`) com a entrada tirava a supressão de quadros que ela já resolvia e custava
0,5 a 1,2 dB de ERLE nos casos sãos. A saída final é a mesma grandeza da rede global (saída contra
entrada), só que por quadro.

O que faz: em cada quadro da STFT (~16 ms de passo) em que a saída `E` tem mais energia que a
entrada `M` (soma nos bins, margem zero: qualquer aumento), o quadro volta a ser o do mic, como se
o AEC não tivesse passado ali. Custa no máximo o eco que já estava no quadro; a rede global de 1,05
continua por fora (cobre o `istft`).

Prova: `tools/test_aec_guarda.py` (sinal sintético, sem hardware). A prova em gravação real
(`tools/medir_aec.py` no arquivo de 21/08 15:00 e `tools/varrer_aec.py` nos 13 de § 8.5) fica com
o Gabriel. Roadmap: `roadmap/2026-11-16-issues-17-21-22-34.md` (passo 4).
"""
import numpy as np


def sem_piora(M: "np.ndarray", E: "np.ndarray") -> "np.ndarray":
    """`E` (saída do AEC, bins x quadros) com o quadro de `M` (entrada) onde `E` tem mais energia
    que `M`. Não altera o `E` recebido; sem quadro pior, devolve o próprio `E`."""
    pior = np.sum(np.abs(E) ** 2, axis=0) > np.sum(np.abs(M) ** 2, axis=0)
    if not pior.any():
        return E
    E = E.copy()
    E[:, pior] = M[:, pior]
    return E
