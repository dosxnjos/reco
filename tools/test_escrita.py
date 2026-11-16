"""Teste sem hardware do filtro de escrita (issue dosxnjos/reco#34), com Whisper falso.

Numa gravação longa só de mic (13/11/2026), a transcrição em português trouxe ideogramas e katakana soltos, trechos
inteiros de outra escrita. O conserto (`antiloop.na_escrita`, dentro do `antiloop.sem_eco`, antes da conta de cópias)
tira do texto pronto a letra que não é latina quando a língua é pt, en ou pl; trecho sem letra nem dígito sai.

Os casos 1 e 2 rodam o `OVTranscriber.transcribe` de verdade (o `run` com o `lang` que o app passa), com o pipe falso
de `tools/test_eco_janelas.py` e o `decode_16k` trocado por áudio sintético. O texto é inventado (nenhum caractere de
gravação de ninguém). Casos:

1. diarizado, pt: nenhuma letra de outra escrita na saída, toda palavra latina fica e na ordem, "1º"/"2ª", "café" com
   acento combinante e o trecho só de dígitos ficam, o trecho só de pontuação sai; o Whisper vê o mesmo prompt de antes
   (o contexto continua cru: o filtro nunca mexe no que o Whisper vê) e não há chamada extra;
2. sem diarização (`texto_corrido`), pt: o mesmo filtro;
3. ordem: cópia, cópia, trecho em outra escrita, cópia, cópia na mesma fala. Filtro antes da conta: sobram 3. Filtro
   depois (o que o #31 mediu e descartou): ficam 4, a régua reprova;
4. língua fora do filtro (`ja`, ou sem língua, como os testes antigos chamam o `_merge`): o texto volta como veio;
5. en e pl: diacrítico do polonês fica, cirílico e grego saem.

    python tools/test_escrita.py   →  última linha "filtro de escrita: falhas 0" (saída 0)

Controle negativo: com o `reco.py` e o `antiloop.py` de antes do conserto, os casos 1, 2, 3 e 5 falham.
"""
from __future__ import annotations

import sys
import threading
import unicodedata
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # console cp1252 (ARMADILHAS 19/08)
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "tools"))
sys.path.insert(0, str(RAIZ))
import antiloop                                   # noqa: E402
import reco                                       # noqa: E402
from test_antiloop import pior                    # noqa: E402
from test_eco_janelas import PipeFalso, audio_de  # noqa: E402

ROTEIRO = ["primeira frase de teste aqui", "你好", "fala com 東京 no meio", "...", "привет мир",
           "o 1º lugar e a 2ª vez", "2024", "um café depois", "カタカナ。", "e a frase final"]
LATINAS = "primeira frase de teste aqui fala com no meio o 1º lugar e a 2ª vez 2024 um café depois e a frase final"
LATINAS_SEM_NOME = set("ªºµ")                     # as mesmas do antiloop, escritas aqui para a régua não depender dele
# o código de antes do #34 (controle negativo) não tem o filtro nem o 3º argumento do `_merge`: os casos reprovam, não quebram
NA_ESCRITA = getattr(antiloop, "na_escrita", lambda tx, _lingua: tx)


def merge(me: list, them: list, lang: str | None) -> str:
    try:
        return reco.OVTranscriber._merge(me, them, lang)
    except TypeError:
        return reco.OVTranscriber._merge(me, them)


def fora_da_escrita(texto: str) -> int:
    """Letras que não são da escrita latina (a régua da prova real usa a mesma conta)."""
    return sum(1 for c in texto if c.isalpha() and c not in LATINAS_SEM_NOME
               and "LATIN" not in unicodedata.name(c, ""))


def transcrever(roteiro: list[str], lang: str, diarize: bool) -> tuple[str, PipeFalso]:
    """O `transcribe` real (thread do app) sobre o pipe falso; devolve (texto, pipe)."""
    tr = reco.OVTranscriber()
    pipe = PipeFalso(roteiro)
    pipe.get_generation_config = lambda: SimpleNamespace(initial_prompt="", do_sample=False, temperature=1.0)
    tr._pipeline = lambda _cb: pipe
    tr._key = ("falso", "GPU")                    # contexto ligado (só a NPU desliga)
    audio = audio_de(len(roteiro))
    original = reco.decode_16k
    reco.decode_16k = lambda _p, split=False: [audio, np.zeros_like(audio)] if split else [audio]
    fim, res = threading.Event(), {}
    try:
        tr.transcribe("falso.mp3", lang=lang, diarize=diarize, aec=False,
                      done_cb=lambda t, e: (res.update(t=t, e=e), fim.set()))
        fim.wait(30)
    finally:
        reco.decode_16k = original
    if res.get("e"):
        raise RuntimeError(res["e"])
    return res.get("t") or "", pipe


def main() -> int:
    falhas = []

    def checa(ok: bool, nome: str, detalhe: str = "") -> None:
        print(f"[{'ok' if ok else 'FALHOU'}] {nome}{(': ' + detalhe) if detalhe else ''}")
        if not ok:
            falhas.append(nome)

    # 1. diarizado, pt, pelo transcribe real
    texto, pipe = transcrever(ROTEIRO, "pt", diarize=True)
    corpo = texto.split(": ", 1)[-1]
    checa(fora_da_escrita(texto) == 0, "diarizado pt: nenhuma letra de outra escrita", f"{fora_da_escrita(texto)} letras")
    checa(corpo.split() == LATINAS.split(), "diarizado pt: toda palavra latina fica, na ordem", corpo)
    checa("..." not in corpo, "diarizado pt: trecho só de pontuação sai")
    _, pipe_sem = transcrever(ROTEIRO, "ja", diarize=True)
    checa(pipe.chamadas == pipe_sem.chamadas and "你好" in pipe.chamadas[2][1],
          "Whisper vê o mesmo prompt com e sem filtro (contexto cru)")
    checa(len(pipe.chamadas) == len(ROTEIRO), "nenhuma chamada extra ao Whisper", f"{len(pipe.chamadas)} chamadas")

    # 2. sem diarização (texto corrido), pt
    texto, _ = transcrever(ROTEIRO, "pt", diarize=False)
    checa(fora_da_escrita(texto) == 0 and texto.split() == LATINAS.split(),
          "texto corrido pt: sem outra escrita, latinas inteiras", texto.replace("\n", " | "))

    # 3. ordem: o filtro antes da conta deixa 3 cópias; depois dela ficariam 4
    copia = "Valeu."
    me = [(1.0, copia), (2.0, copia), (3.0, "嗯"), (4.0, copia), (5.0, copia), (6.0, "fim")]
    antes = merge(me, [], "pt").split(": ", 1)[1]
    checa(pior(antes)[0] == 3 and antes == " ".join([copia] * 3 + ["fim"]), "ordem: filtro antes da conta, 3 cópias",
          antes)
    depois = " ".join(NA_ESCRITA(tx, "pt") for _t, _f, tx in antiloop.sem_eco([(t, "", x) for t, x in me]))
    checa(pior(depois)[0] == 4, "ordem: filtro depois da conta deixaria 4 (o descartado)", f"pior={pior(depois)[0]}")

    # 4. língua fora do filtro: nada muda
    texto, _ = transcrever(ROTEIRO, "ja", diarize=True)
    checa(texto.split(": ", 1)[-1] == " ".join(ROTEIRO), "ja: o texto volta como veio")
    checa(reco.OVTranscriber._merge([(1.0, "你好"), (2.0, "...")], []) == f"{reco._spk_me()}: 你好 ...",
          "sem língua (chamada antiga do _merge): o texto volta como veio")

    # 5. en e pl
    checa(NA_ESCRITA("żółć łąka Ελλάδα", "pl") == "żółć łąka", "pl: diacrítico fica, grego sai")
    checa(NA_ESCRITA("hello мир 3", "en") == "hello 3", "en: cirílico sai, dígito fica")
    checa(NA_ESCRITA("กิน", "pt") == "" and NA_ESCRITA("。", "pt") == "",
          "tailandês com marca e pontuação larga sozinhos saem")

    print(f"filtro de escrita: falhas {len(falhas)}")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
