"""Teste sem hardware da guarda de eco entre janelas (issue dosxnjos/reco#31), com Whisper falso.

A causa medida em gravações: janela de ruído (ou de voz do interlocutor vazando no mic) devolve uma frase curta de
enchimento, o contexto (`initial_prompt` com as últimas ~30 palavras) carrega a frase, e janelas seguidas repetem a
mesma coisa. Cada janela isolada é curta e limpa, então o `_degenerado` (uma janela só, e só acima de 40 caracteres)
não via nada. O conserto (`antiloop.sem_eco`, chamado pelo `OVTranscriber._merge`) tira a repetição fala a fala.

O pipe falso reproduz esse comportamento no caminho real (`_transcribe_channel`: VAD, agrupamento, contexto,
`_generate_sem_loop`; depois `_merge`), com áudio sintético: cada trecho de "fala" é um seno cuja amplitude diz ao
pipe falso qual janela é. O texto é inventado (nenhuma gravação de ninguém). Casos:

1. loop entre janelas: `pior` por fala (régua `test_antiloop.pior`, como o `tools/paridade.py`) <= 3, a fala real fica
   inteira e na ordem, o Whisper vê o mesmo prompt de antes do conserto e não há chamada extra;
2. canal limpo: a saída é a de sempre;
3. a mesma resposta curta três vezes na mesma fala fica; a quarta seguida sai (custo declarado do critério > 3);
4. a mesma resposta curta quatro vezes, com o interlocutor falando entre elas, fica inteira ("sim" em quatro turnos
   não é loop);
5. janela curta com loop dentro (quatro vezes a mesma palavra, abaixo do piso do `_degenerado`) fica com três, sem
   refazer a janela (refazer mudaria o contexto das janelas seguintes);
6. trecho que começa com a 4a cópia do enchimento e segue com fala: sai só a cópia, a fala fica.

    python tools/test_eco_janelas.py   →  última linha "eco entre janelas: falhas 0" (saída 0)

Controle negativo: com o `reco.py` de antes do conserto, os casos 1, 3, 5 e 6 falham.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # console cp1252 (ARMADILHAS 19/08)
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "tools"))
sys.path.insert(0, str(RAIZ))
import reco                                       # noqa: E402
from test_antiloop import pior                    # noqa: E402

SR = 16000
FALA_S, PAUSA_S = 3.5, 1.5                        # 3,5 s de "fala" = um grupo (ALVO_ACUMULO_S = 3 s)
ENCHIMENTO = "Valeu."
OUTRO = SimpleNamespace(me=reco._spk_me(), them=reco._spk_them())


def amp(k: int) -> float:
    return 0.02 + 0.004 * k


def audio_de(n: int) -> np.ndarray:
    """n trechos de seno separados por silêncio; o trecho k tem amplitude amp(k)."""
    t = np.arange(int(FALA_S * SR)) / SR
    partes = [np.zeros(int(PAUSA_S * SR), np.float32)]
    for k in range(n):
        partes += [(amp(k) * np.sin(2 * np.pi * 220 * t)).astype(np.float32),
                   np.zeros(int(PAUSA_S * SR), np.float32)]
    return np.concatenate(partes)


class PipeFalso:
    """`roteiro[k]`: "ruido" (sempre diz o enchimento), "envenenada" (fala que o prompt com o enchimento faz sair
    enchimento), ou o texto da janela. Registra as chamadas (janela, prompt)."""

    def __init__(self, roteiro: list[str]):
        self.roteiro = roteiro
        self.chamadas: list[tuple[int, str]] = []

    def generate(self, window, cfg):
        rms = float(np.sqrt(np.mean(window ** 2)))
        k = round((rms * np.sqrt(2) - 0.02) / 0.004)
        prompt = getattr(cfg, "initial_prompt", "") or ""
        self.chamadas.append((k, prompt))
        papel = self.roteiro[k]
        if papel == "ruido":
            txt = ENCHIMENTO
        elif papel == "envenenada":
            txt = ENCHIMENTO if ENCHIMENTO in prompt else f"fala da janela {k} sem prompt envenenado"
        else:
            txt = papel
        return SimpleNamespace(chunks=[SimpleNamespace(start_ts=0.0, end_ts=FALA_S, text=" " + txt)])


def canal(roteiro: list[str]) -> tuple[list[tuple[float, str]], PipeFalso]:
    tr = reco.OVTranscriber()
    tr._key = ("falso", "GPU")                    # contexto ligado (só a NPU desliga)
    pipe = PipeFalso(roteiro)
    cfg = SimpleNamespace(initial_prompt="", do_sample=False, temperature=1.0)
    segs, _ = tr._transcribe_channel(pipe, cfg, audio_de(len(roteiro)), 0, 1, None)
    return segs, pipe


def falas(texto: str) -> list[str]:
    """Corpo de cada linha do _merge, sem o rótulo de quem fala."""
    return [ln.split(": ", 1)[1] for ln in texto.splitlines() if ": " in ln]


def main() -> int:
    falhas = []

    def checa(ok: bool, nome: str, detalhe: str = "") -> None:
        print(f"[{'ok' if ok else 'FALHOU'}] {nome}{(': ' + detalhe) if detalhe else ''}")
        if not ok:
            falhas.append(nome)

    # 1. loop entre janelas (o prompt envenenado faz até a janela "envenenada" sair enchimento)
    roteiro = ["primeira frase de teste aqui", *["ruido"] * 6, "envenenada",
               "outra frase depois do trecho ruim", "e a frase final do teste"]
    segs, pipe = canal(roteiro)
    texto = reco.OVTranscriber._merge(segs, [])
    p = max(pior(f)[0] for f in falas(texto))
    checa(p <= 3, "loop entre janelas: pior por fala <= 3", f"pior={p}")
    ws = texto.split(": ", 1)[1].split()
    checa([w for w in ws if w != ENCHIMENTO] == " ".join([roteiro[0], roteiro[8], roteiro[9]]).split(),
          "fala real inteira e na ordem")
    cru = " ".join([roteiro[0], *[ENCHIMENTO] * 7, roteiro[8]]).split()[-30:]
    checa(pipe.chamadas[-1] == (9, " ".join(cru)), "Whisper vê o mesmo prompt de antes (contexto cru)")
    checa(len(pipe.chamadas) == len(roteiro), "nenhuma chamada extra ao Whisper", f"{len(pipe.chamadas)} chamadas")

    # 2. canal limpo: mesma saída
    limpo = [f"frase limpa número {k} sem repetir nada" for k in range(6)]
    segs, _ = canal(limpo)
    checa(reco.OVTranscriber._merge(segs, []) == f"{OUTRO.me}: " + " ".join(limpo), "canal limpo: saída igual")

    # 3. resposta curta na mesma fala: três ficam, a quarta seguida sai
    me = [(1.0, "pergunta de teste"), (2.0, "Sim."), (3.0, "Sim."), (4.0, "Sim."), (5.0, "Sim."), (6.0, "fim")]
    checa(reco.OVTranscriber._merge(me, []) == f"{OUTRO.me}: pergunta de teste Sim. Sim. Sim. fim",
          "mesma fala: três ficam, a quarta repetição seguida sai")

    # 4. a mesma resposta curta em quatro turnos, com o interlocutor no meio: fica inteira
    me = [(t, "Sim.") for t in (1.0, 3.0, 5.0, 7.0)]
    them = [(t, f"pergunta {k} do interlocutor") for k, t in enumerate((0.5, 2.0, 4.0, 6.0))]
    linhas = reco.OVTranscriber._merge(me, them).splitlines()
    checa(sum(ln == f"{OUTRO.me}: Sim." for ln in linhas) == 4 and len(linhas) == 8,
          "quatro turnos com 'Sim.' ficam inteiros")

    # 5. loop curto dentro de uma janela (abaixo do piso de 40 do _degenerado): não entra, sem chamada extra
    curto = ["começo da conversa de teste", "Oi Oi Oi Oi", "Sim, sim. Tá bom.", "fim da conversa"]
    segs, pipe = canal(curto)
    checa(reco.OVTranscriber._merge(segs, []) == f"{OUTRO.me}: " + " ".join([curto[0], "Oi Oi Oi", curto[2], curto[3]]),
          "loop curto dentro da janela fica com três")
    checa(len(pipe.chamadas) == len(curto), "loop curto: nenhuma chamada extra", f"{len(pipe.chamadas)} chamadas")

    # 6. trecho que começa com o enchimento e segue com fala: só as cópias saem, a fala fica
    me = [(1.0, ENCHIMENTO), (2.0, ENCHIMENTO), (3.0, ENCHIMENTO), (4.0, f"{ENCHIMENTO} e aqui segue uma frase real")]
    checa(reco.OVTranscriber._merge(me, []) == f"{OUTRO.me}: " + " ".join([ENCHIMENTO] * 3) + " e aqui segue uma frase real",
          "trecho misto: sai só a cópia, a fala fica")

    # 7. número ditado em dígitos fica inteiro (código, telefone); com vírgula também
    me = [(1.0, "o código é 0 0 0 0 7"), (2.0, "e o outro é 1, 1, 1, 1, 2")]
    checa(reco.OVTranscriber._merge(me, []) == f"{OUTRO.me}: o código é 0 0 0 0 7 e o outro é 1, 1, 1, 1, 2",
          "número em dígitos fica inteiro")

    # 8. repetição que começa dentro da última cópia de outra ("a b a b c b c b c b c": "b c" 4x)
    me = [(1.0, "a b a b c b c b c b c fim")]
    p = max(pior(f)[0] for f in falas(reco.OVTranscriber._merge(me, [])))
    tudo = reco.OVTranscriber._merge(me, []).split(": ", 1)[1].split()
    forca = max((k for n in range(1, 9) for i in range(len(tudo)) for k in range(1, len(tudo) // n + 1)
                 if tudo[i:i + k * n] == tudo[i:i + n] * k and i + k * n <= len(tudo)), default=1)
    checa(forca <= 3 and p <= 3, "repetição sobreposta: força bruta <= 3", f"força bruta={forca}")

    # 9. caminho sem diarização (OV e MLX: `texto_corrido` sobre trechos `(início, texto)`), com remoção de verdade
    segs = [(1.0, "começo do áudio"), *[(2.0 + k, ENCHIMENTO) for k in range(5)], (8.0, "e o fim do áudio")]
    checa(reco.texto_corrido(segs) == "\n".join(["começo do áudio", *[ENCHIMENTO] * 3, "e o fim do áudio"]),
          "sem diarização: sai a 4a e a 5a cópia, uma linha por trecho")

    print(f"eco entre janelas: falhas {len(falhas)}")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
