"""Teste sem hardware da régua local da rede de segurança do `cancel_echo` (issue dosxnjos/reco#21, E4a/E4b).

Sinal sintético (ruído filtrado ligado e desligado em pedaços de 0,25 s; nenhuma gravação de ninguém, nenhum
som na caixa, nenhum microfone). Cada cenário tem semente fixa. A voz do usuário (`near`) e o eco (a referência
atrasada e atenuada pelo acoplamento) são conhecidos amostra a amostra, então as máscaras saem do sinal:
"só o eco" = eco ligado e voz desligada; "só a voz" = voz ligada e eco e referência desligados.

Régua por cenário, sempre o par (ERLE em "só o eco", dano em "só a voz", em dB; CLAUDE.md item 4). "Sem régua"
é o `cancel_echo` de antes do conserto, reproduzido trocando `reco.sem_piora` pela identidade; "com régua" é o
código como está.

1. E4a, em sinal sintético: no cenário de acoplamento baixo (o mic quase não ouve a caixa, como no arquivo de
   21/08 15:00) o ERLE sem régua sai negativo e a rede global de 1,05 não dispara (saída diferente do mic e
   `r_out/r_in` < 1,05).
2. A régua por bloco do roadmap de 30/08 (resíduo do bloco > entrada do bloco) não passa de 1 + 1e-6 em nenhum
   bloco de nenhum cenário: mínimos quadrados com `h = 0` como candidato não deixa o bloco piorar. Por isso a
   régua é por quadro (`aec_guarda.py`).
3. Acoplamento baixo, janela contígua de 30 s e o regime do app (janelas de ~3 s feitas de retalhos de 1 s,
   como as `partes` de `_transcribe_channel`): ERLE com régua >= sem régua + 6 dB (+3 dB nos retalhos), dano
   com régua <= sem régua + 0,5 dB. Medido a 50 ms ou mais da voz (a janela da STFT tem 64 ms), o ERLE com
   régua fica >= -0,5 dB (o quadro volta a ser o mic) e o sem régua < -10 dB; o ERLE negativo que sobra na
   máscara inteira é vazamento da janela nas bordas da voz. (Este critério de 50 ms entrou DEPOIS de ver o
   -7,3 dB da máscara inteira, para testar essa hipótese; não é régua fixada antes.)
4. Cenários sãos (acoplamento -12 dB alinhado, salto de 300 ms, fala dupla pesada), contíguo e em retalhos: ERLE
   com régua >= sem régua - 0,5 dB e dano com régua <= sem régua + 0,5 dB (não regride).
   Fala dupla (voz e eco juntos, o único lugar em que devolver o quadro do mic pode custar, porque põe o eco
   de volta debaixo da voz), nos quatro cenários: o eco que volta (`eco_na_dupla`, dB do eco de entrada) com
   régua <= max(sem régua + 0,5 dB, -30 dB); imprime voz/resto e a fração de quadros devolvidos ao mic.
   Correção de 16/11 (revisão): a régua antiga (voz/resto com régua >= sem - 0,5 dB) não discriminava: com o
   AEC desligado o voz/resto fica igual ou melhor e passava. A tolerância de -30 dB foi posta DEPOIS de ver os
   números (fala dupla pesada: -41,2 sem régua, -34,9 com), perto da projeção ao acaso do estimador (eco de
   outra semente: -31,4 a -43,0 dB; na fala dupla pesada, -43,0, ou seja, o -34,9 está ~8 dB acima dele).
   Entre sementes a diferença com-sem na fala dupla pesada troca de sinal (-13,3 a +13,8 dB), sempre a -25 dB
   ou menos: nesse nível o teste não prova custo nem ausência de custo.
   4c. Controle negativo dentro do teste: o mutante "AEC desligado" (régua devolve sempre o mic) reprova a
   checagem 4b nos três cenários sãos (dá ~0 dB). No acoplamento baixo ela não discrimina por natureza (o
   AEC sem régua só tira -0,7 dB de eco).
5. Referência muda: saída com régua idêntica à sem régua.
6. `sem_piora`: sem quadro pior devolve o próprio objeto; zera só os quadros piores; não altera a entrada.

    python tools/test_aec_guarda.py   →  última linha "guard do cancel_echo: falhas 0" (saída 0)

Controle negativo: com o `reco.py` de antes do conserto (sem `sem_piora`), os itens 3 e 6 falham.
O que este teste NÃO prova: o número em gravação real (`tools/medir_aec.py` no arquivo de 21/08 15:00, ERLE
mediano >= 0, e `tools/varrer_aec.py` nos 13 de § 8.5 do roadmap do salto). Isso pede ler `Documents/Reco`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_erosion
from scipy.signal import lfilter, stft

sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # console cp1252 (ARMADILHAS 19/08)
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
import reco                                       # noqa: E402

SR = 16000
PEDACO = SR // 4                                  # liga/desliga a cada 0,25 s
falhas: list[str] = []


def check(ok: bool, msg: str) -> None:
    if not ok:
        falhas.append(msg)
        print(f"FALHA: {msg}")


def _portao(rng, n: int, p: float) -> np.ndarray:
    return np.repeat((rng.random(-(-n // PEDACO)) < p).astype(np.float64), PEDACO)[:n]


def _atrasa(x: np.ndarray, d: int) -> np.ndarray:
    out = np.zeros_like(x)
    out[d:] = x[:len(x) - d]
    return out


def cenario(semente: int, acopl_db: float, salto_ms: float = 0.0, p_ref: float = 0.6, p_voz: float = 0.4,
            mudo: bool = False, dur: float = 30.0) -> dict:
    rng = np.random.default_rng(semente)
    n = int(dur * SR)
    som = lambda: lfilter([1.0], [1.0, -0.95], rng.standard_normal(n)) * 0.3
    g_ref, g_voz = _portao(rng, n, p_ref), _portao(rng, n, p_voz)
    ref = som() * g_ref * (0.0 if mudo else 1.0)
    voz = som() * g_voz
    d1, d2 = int(0.15 * SR), int((0.15 + salto_ms / 1000) * SR)
    meio = n // 2
    eco, g_eco = _atrasa(ref, d1), _atrasa(g_ref, d1)
    eco[meio:], g_eco[meio:] = _atrasa(ref, d2)[meio:], _atrasa(g_ref, d2)[meio:]
    mic = voz + 10 ** (acopl_db / 20) * eco + 1e-4 * rng.standard_normal(n)
    so_eco = (g_eco > 0) & (g_voz == 0)
    so_voz = (g_voz > 0) & (g_eco == 0) & (g_ref == 0)
    return {"mic": mic.astype(np.float32), "ref": ref.astype(np.float32), "so_eco": so_eco, "so_voz": so_voz,
            "voz": voz, "dupla": (g_voz > 0) & (g_eco > 0)}


def voz_na_dupla(c: dict, out: np.ndarray) -> float:
    """Na fala dupla (voz e eco juntos), a voz sobre tudo o que não é voz na saída, em dB (maior = melhor).
    É o único lugar em que devolver o quadro do mic pode custar: põe o eco de volta debaixo da voz."""
    v, o = c["voz"][c["dupla"]], out[c["dupla"]].astype(np.float64)
    return float(10 * np.log10(np.sum(v ** 2) / (np.sum((o - v) ** 2) + 1e-20)))


PISO_ECO_DB = -30.0     # projeção ao acaso do estimador abaixo: -31,4 a -43,0 dB medidos (eco de outra semente)


def eco_na_dupla(c: dict, out: np.ndarray) -> float:
    """Na fala dupla, quanto do eco que entrou no mic sobra na saída, em dB do eco de entrada (0 = AEC
    desligado; menor = melhor). Mínimos quadrados da saída sobre [voz, eco] nos trechos de fala dupla; o
    coeficiente do eco é o que voltou. O `voz_na_dupla` não serve para isso: com o AEC desligado ele fica
    igual ou melhor (+12,4 -> +36,1 dB no acoplamento baixo), porque mede também o dano na voz."""
    d = c["dupla"]
    eco = c["mic"][d].astype(np.float64) - c["voz"][d]
    coef = np.linalg.lstsq(np.stack([c["voz"][d], eco], 1), out[d].astype(np.float64), rcond=None)[0]
    return float(20 * np.log10(abs(coef[1]) + 1e-12))


def eco_ok(sem: float, com: float) -> bool:
    """Com a régua, o eco que volta na fala dupla não sobe mais de 0,5 dB (a tolerância das outras
    checagens), salvo abaixo de -30 dB: tolerância posta DEPOIS de ver os números. Abaixo dela a
    diferença com-sem troca de sinal entre sementes (-13,3 a +13,8 dB na fala dupla pesada), mas não está
    provado que seja ruído do estimador (o acaso dele ali foi -43 dB, e o com régua deu -34,9)."""
    return com <= max(sem + 0.5, PISO_ECO_DB)


def aec_desligado(mic: np.ndarray, ref: np.ndarray) -> np.ndarray:
    """Mutante do controle negativo: a régua devolve sempre o quadro do mic (o AEC desligado). No código de
    antes do conserto (sem `sem_piora`) não há onde injetar: devolve o próprio mic, que é o mesmo mutante."""
    original = getattr(reco, "sem_piora", None)
    if original is None:
        return mic.copy()
    reco.sem_piora = lambda M, E: M
    try:
        return reco.cancel_echo(mic, ref)
    finally:
        reco.sem_piora = original


def _db(a: np.ndarray, b: np.ndarray) -> float:
    return float(10 * np.log10(np.mean(a.astype(np.float64) ** 2) / (np.mean(b.astype(np.float64) ** 2) + 1e-20)))


def par(c: dict, out: np.ndarray) -> tuple[float, float]:
    """(ERLE em "só o eco", dano em "só a voz"), em dB."""
    return _db(c["mic"][c["so_eco"]], out[c["so_eco"]]), abs(_db(c["mic"][c["so_voz"]], out[c["so_voz"]]))


TROCA = {"quadros": 0, "trocados": 0}           # quadros que a régua devolveu ao mic (só informa)


def _contando(original):
    def sem_piora(M, E):
        F = original(M, E)
        TROCA["quadros"] += E.shape[1]
        TROCA["trocados"] += int(np.sum(np.any(F != E, axis=0)))
        return F
    return sem_piora


def aec(mic: np.ndarray, ref: np.ndarray, com_regua: bool) -> np.ndarray:
    original = getattr(reco, "sem_piora", None)
    if original is not None:
        reco.sem_piora = _contando(original) if com_regua else (lambda M, E: E)
    try:
        return reco.cancel_echo(mic, ref)
    finally:
        if original is not None:
            reco.sem_piora = original


def retalhos(c: dict, semente: int, n_janelas: int = 8) -> dict:
    """Janelas de ~3 s, cada uma com 3 retalhos de 1 s de lugares diferentes (o regime das `partes`)."""
    rng = np.random.default_rng(semente)
    n = len(c["mic"])
    inicios = rng.integers(0, n - SR, size=(n_janelas, 3))
    return {"janelas": [[(int(s), int(s) + SR) for s in linha] for linha in inicios], "base": c}


def par_retalhos(r: dict, com_regua: bool) -> tuple[float, float]:
    c = r["base"]
    mics, outs, eco, voz = [], [], [], []
    for partes in r["janelas"]:
        m = np.concatenate([c["mic"][s:t] for s, t in partes])
        f = np.concatenate([c["ref"][s:t] for s, t in partes])
        mics.append(m)
        outs.append(aec(m, f, com_regua))
        eco.append(np.concatenate([c["so_eco"][s:t] for s, t in partes]))
        voz.append(np.concatenate([c["so_voz"][s:t] for s, t in partes]))
    junto = {"mic": np.concatenate(mics), "so_eco": np.concatenate(eco), "so_voz": np.concatenate(voz)}
    return par(junto, np.concatenate(outs))


def razao_bloco_max(mic: np.ndarray, ref: np.ndarray, nfft: int = 1024, hop: int = 256, taps: int = 6,
                    bloco_s: float = 2.0, lam: float = 1e-3) -> float:
    """Espelho do laço do `cancel_echo` (sem a régua): o maior resíduo/entrada POR BLOCO."""
    m, r = reco._alinhar_canais(mic, ref, SR, maxlag_s=0.5)
    _, _, M = stft(m, fs=SR, nperseg=nfft, noverlap=nfft - hop)
    _, _, S = stft(r, fs=SR, nperseg=nfft, noverlap=nfft - hop)
    nb, nt = M.shape
    X = np.zeros((nb, nt, taps), np.complex128)
    for p in range(taps):
        X[:, p:, p] = S[:, :nt - p]
    passo, pior = max(1, int(bloco_s * SR / hop)), 0.0
    for t0 in range(0, nt, passo):
        Xb, Mb = X[:, t0:t0 + passo, :], M[:, t0:t0 + passo]
        A = np.einsum("btp,btq->bpq", np.conj(Xb), Xb)
        b = np.einsum("btp,bt->bp", np.conj(Xb), Mb)
        tr = np.trace(A, axis1=1, axis2=2).real / taps
        A += (lam * np.maximum(tr, 1e-12))[:, None, None] * np.eye(taps)
        h = np.linalg.solve(A, b[:, :, None])[:, :, 0]
        y = np.einsum("btp,bp->bt", Xb, h)
        ent = float(np.sum(np.abs(Mb) ** 2))
        if ent > 0:
            pior = max(pior, float(np.sum(np.abs(Mb - y) ** 2)) / ent)
    return pior


def _linha(nome: str, sem: tuple, com: tuple) -> None:
    print(f"{nome:<32} sem régua: ERLE {sem[0]:+6.1f} dano {sem[1]:4.1f} | com régua: ERLE {com[0]:+6.1f} dano {com[1]:4.1f}")


def teste_cenarios() -> None:
    baixo = cenario(21, -36.0)
    saos = {"são (-12 dB, alinhado)": cenario(11, -12.0),
            "salto de 300 ms (-12 dB)": cenario(12, -12.0, salto_ms=300),
            "fala dupla pesada (-12 dB)": cenario(13, -12.0, p_ref=0.8, p_voz=0.8)}
    # 1. E4a em sintético: sem régua, o ERLE é negativo e a rede global não dispara
    out = aec(baixo["mic"], baixo["ref"], com_regua=False)
    r = float(np.sqrt(np.mean(out.astype(np.float64) ** 2)) / np.sqrt(np.mean(baixo["mic"].astype(np.float64) ** 2)))
    sem = par(baixo, out)
    print(f"E4a sintético: rede global disparou={np.array_equal(out, baixo['mic'])} r_out/r_in={r:.3f} ERLE={sem[0]:+.1f}")
    check(sem[0] < 0 and not np.array_equal(out, baixo["mic"]) and r < 1.05,
          f"E4a: esperava ERLE < 0 com a rede global calada (ERLE {sem[0]:+.1f}, razão {r:.3f})")
    # 2. a régua por bloco do roadmap de 30/08 não dispara
    pior_bloco = max(razao_bloco_max(c["mic"], c["ref"]) for c in [baixo, *saos.values()])
    print(f"régua por bloco (roadmap de 30/08): maior resíduo/entrada = {pior_bloco:.9f}")
    check(pior_bloco <= 1 + 1e-6, f"régua por bloco passou de 1: {pior_bloco}")
    # 3. acoplamento baixo: a régua por quadro tira o dano
    com = par(baixo, aec(baixo["mic"], baixo["ref"], com_regua=True))
    _linha("acoplamento baixo (-36 dB)", sem, com)
    check(com[0] >= sem[0] + 6 and com[1] <= sem[1] + 0.5, f"acoplamento baixo: {sem} -> {com}")
    # longe das bordas da voz (>= 50 ms, a janela da STFT tem 64 ms), o quadro volta a ser o mic: ERLE ~0
    k = int(0.05 * SR)
    longe = dict(baixo, so_eco=binary_erosion(baixo["so_eco"], structure=np.ones(2 * k + 1)))
    s_l, c_l = par(longe, aec(baixo["mic"], baixo["ref"], False)), par(longe, aec(baixo["mic"], baixo["ref"], True))
    _linha("  só o eco a 50 ms da voz", s_l, c_l)
    check(c_l[0] >= -0.5 and s_l[0] < -10, f"acoplamento baixo longe das bordas: {s_l} -> {c_l}")
    rb = retalhos(baixo, 31)
    sem_r, com_r = par_retalhos(rb, False), par_retalhos(rb, True)
    _linha("  em retalhos de ~3 s", sem_r, com_r)
    check(com_r[0] >= sem_r[0] + 3 and com_r[1] <= sem_r[1] + 0.5, f"acoplamento baixo em retalhos: {sem_r} -> {com_r}")
    # 4. cenários sãos não regridem
    for i, (nome, c) in enumerate(saos.items()):
        s, k = par(c, aec(c["mic"], c["ref"], False)), par(c, aec(c["mic"], c["ref"], True))
        _linha(nome, s, k)
        check(k[0] >= s[0] - 0.5 and k[1] <= s[1] + 0.5, f"{nome}: {s} -> {k}")
        rr = retalhos(c, 40 + i)
        s, k = par_retalhos(rr, False), par_retalhos(rr, True)
        _linha("  em retalhos de ~3 s", s, k)
        check(k[0] >= s[0] - 0.5 and k[1] <= s[1] + 0.5, f"{nome} em retalhos: {s} -> {k}")
    # 4b. fala dupla (voz e eco juntos), o único lugar em que devolver o quadro do mic pode custar:
    # o eco que volta (voz/resto só informa: não discrimina, ver eco_na_dupla)
    eco_sem = {}
    for nome, c in {"acoplamento baixo (-36 dB)": baixo, **saos}.items():
        TROCA.update(quadros=0, trocados=0)
        o_s, o_k = aec(c["mic"], c["ref"], False), aec(c["mic"], c["ref"], True)
        s, k = voz_na_dupla(c, o_s), voz_na_dupla(c, o_k)
        eco_sem[nome], ek = eco_na_dupla(c, o_s), eco_na_dupla(c, o_k)
        fr = TROCA["trocados"] / max(1, TROCA["quadros"])
        print(f"fala dupla, {nome:<28} eco que volta sem régua {eco_sem[nome]:+6.1f} dB | com régua {ek:+6.1f} dB"
              f" | voz/resto {s:+.1f} -> {k:+.1f} dB | quadros devolvidos ao mic {fr:5.1%}")
        check(eco_ok(eco_sem[nome], ek), f"fala dupla, {nome}: eco que volta {eco_sem[nome]:+.1f} -> {ek:+.1f} dB")
    # 4c. controle negativo: com o AEC desligado (mutante), a checagem 4b reprova onde o AEC tira eco
    # (no acoplamento baixo o AEC quase não tira eco: -0,7 dB, e ali ela não discrimina por natureza)
    for nome, c in saos.items():
        em = eco_na_dupla(c, aec_desligado(c["mic"], c["ref"]))
        print(f"fala dupla, {nome:<28} mutante (AEC desligado): eco que volta {em:+6.1f} dB")
        check(not eco_ok(eco_sem[nome], em), f"controle negativo: o mutante passou em {nome} ({em:+.1f} dB)")
    # 5. referência muda: nada muda
    mudo = cenario(14, -12.0, mudo=True)
    a, b = aec(mudo["mic"], mudo["ref"], False), aec(mudo["mic"], mudo["ref"], True)
    check(np.array_equal(a, b), "referência muda: a régua mudou a saída")
    print(f"referência muda: saída igual à sem régua = {np.array_equal(a, b)}")


def teste_sem_piora() -> None:
    sp = getattr(reco, "sem_piora", None)
    if sp is None:
        check(False, "reco.sem_piora não existe (código de antes do conserto)")
        return
    rng = np.random.default_rng(7)
    M = rng.standard_normal((5, 6)) + 1j * rng.standard_normal((5, 6))
    bom = 0.5 * M                                   # saída = metade da entrada em todo quadro
    check(sp(M, bom) is bom, "sem quadro pior, sem_piora não devolveu o próprio E")
    ruim = bom.copy()
    ruim[:, 2] = -3 * M[:, 2]                       # quadro 2: saída com 9x a energia da entrada
    copia = ruim.copy()
    E = sp(M, ruim)
    check(np.array_equal(ruim, copia), "sem_piora alterou o E recebido")
    check(np.array_equal(E[:, 2], M[:, 2]) and np.array_equal(np.delete(E, 2, axis=1), np.delete(bom, 2, axis=1)),
          "sem_piora não trocou só o quadro pior pelo do mic")
    print("sem_piora: identidade sem quadro pior, troca só o quadro pior pelo do mic, não altera a entrada")


if __name__ == "__main__":
    teste_cenarios()
    teste_sem_piora()
    print(f"guard do cancel_echo: falhas {len(falhas)}")
    sys.exit(1 if falhas else 0)
