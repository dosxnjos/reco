"""Guarda de eco do transcritor (issue dosxnjos/reco#31), fora do reco.py pela trava de tamanho.

A defesa por janela (`OVTranscriber._degenerado` / `_generate_sem_loop`, no reco.py) olha uma
janela por vez e só acima de 40 caracteres. Ela não vê dois casos medidos em gravações reais:
- a repetição ENTRE janelas: cada janela do VAD (3 a 4 s) sai curta e limpa, uma frase de
  enchimento, mas dezenas de janelas seguidas dizem a mesma coisa, porque o contexto
  (`initial_prompt` com as últimas ~30 palavras) carrega a frase para a janela seguinte;
- o loop dentro de uma janela curta (a mesma palavra quatro vezes em menos de 40 caracteres).

`sem_eco` tira da transcrição, fala a fala (a mesma unidade da régua `tools/paridade.py`), as
cópias de um n-grama de 1 a 8 palavras que passam de `REPETICOES_MAX` seguidas, dentro de um trecho
ou emendadas no texto já aceito da mesma fala; as palavras que não são cópia ficam (medido: trecho
que começa com o enchimento e segue com fala de verdade). Trecho que fica vazio sai. A fala do outro
canal no meio recomeça a conta: "sim" em quatro turnos não é loop.

Ela só TIRA texto pronto: roda depois da transcrição dos dois canais, não muda o que o Whisper vê
nem acrescenta nada. Três alternativas foram medidas em cópias e descartadas, todas porque mudam
o prompt ou o refazer de uma janela, e isso muda o texto de TODAS as janelas seguintes (o Whisper
é sensível ao prompt):
- limpar o eco do contexto: apagou frases reais em janelas longe do loop;
- tirar o piso de 40 do `_degenerado`: o refazer com temperatura das janelas curtas mudou o resto
  de uma gravação de 106 min, com frases reais trocadas e perdidas;
- refazer sem prompt a janela barrada: nos dois casos conferidos, o texto que voltava no canal do
  mic era a fala do interlocutor vazando no mic, atribuída a "Eu".
Teste sem hardware: `python tools/test_eco_janelas.py`.

Filtro de escrita (issue dosxnjos/reco#34): numa língua de escrita latina (pt, en, pl, as do app),
o Whisper às vezes devolve um trecho em escrita asiática (medido: ideograma ou katakana sozinho numa
gravação longa só de mic). `na_escrita` tira desse trecho a letra que não é latina (e a pontuação
larga, 。、「」); o trecho que fica sem letra nem dígito sai, e o trecho só de pontuação também. Letra
latina nunca sai. Roda dentro do `sem_eco`, ANTES da conta de cópias: depois dela, tirar o trecho
encostaria cópias que ela contou separadas e deixaria passar mais de 3 seguidas (medido no #31).
Sem `lingua` (ou outra língua, como `transcrever.py --lang ja`) não há filtro. Não resolve o
enchimento em português que sobra em trincas: esse continua (o critério do `sem_eco` é mais de 3).
"""
import unicodedata

REPETICOES_MAX = 3      # o mesmo n-grama seguido mais vezes que isso = loop (régua da issue)
CAUDA_PALAVRAS = 40     # quanto da fala a guarda lembra (8 palavras x 4 repetições = 32)
LINGUAS_LATINAS = {"pt", "en", "pl"}   # as do app (`App._whisper_lang`); outra língua passa sem filtro
LATINAS_SEM_NOME = set("ªºµ")          # letras do texto latino sem "LATIN" no nome Unicode ("1º", "2ª")


def _so_latina(palavra: str) -> str:
    """A palavra sem as letras de outra escrita (e as marcas presas a elas) nem a pontuação larga
    do texto asiático (East Asian Width W/F: 。、「」 e afins). Marca combinante segue a letra de antes."""
    fica, sai = [], False
    for c in palavra:
        if c.isalpha():
            sai = c not in LATINAS_SEM_NOME and "LATIN" not in unicodedata.name(c, "")
        elif not unicodedata.category(c).startswith("M"):
            sai = unicodedata.east_asian_width(c) in "WF"
        if not sai:
            fica.append(c)
    return "".join(fica)


def na_escrita(texto: str, lingua: str | None) -> str:
    """O trecho sem o que não é da escrita latina, se `lingua` é latina; "" se não sobra letra nem
    dígito (trecho de outra escrita ou só pontuação). Palavra que perdeu tudo menos pontuação sai;
    trecho intacto volta com o espaçamento original. Outra língua: o texto como veio."""
    if lingua not in LINGUAS_LATINAS:
        return texto
    ws, mudou = [], False
    for w in texto.split():
        limpa = _so_latina(w)
        if limpa != w:
            mudou = True
            if not any(c.isalnum() for c in limpa):
                continue
        ws.append(limpa)
    if not any(c.isalnum() for w in ws for c in w):
        return ""
    return " ".join(ws) if mudou else texto


def _so_digitos(ng: list[str]) -> bool:
    """N-grama feito só de número em dígitos ("0 0 0 0 7", "1, 1, 1, 1"): código ou telefone ditado
    fica inteiro. Nenhuma alucinação medida era numérica; número por extenso não é isento."""
    return all(w.strip(".,;:!?-–—()").isdigit() for w in ng)


def _corrida_longa(ws: list[str], desde: int, lim: int) -> tuple[int, int, int] | None:
    """(início, n, vezes) da primeira repetição seguida de um n-grama com mais de `lim` cópias que
    termina depois da palavra `desde`; None se não houver. Testa TODA posição de início, então vê
    repetição que começa dentro da última cópia de outra; a régua `tools/test_antiloop.pior` pula
    a corrida inteira e pode não ver. Guarda mais rigorosa que a régua é o lado seguro."""
    for n in range(1, 9):
        for i in range(len(ws) - n + 1):
            k = 1
            while ws[i + k * n:i + (k + 1) * n] == ws[i:i + n]:
                k += 1
            if k > lim and i + k * n > desde and not _so_digitos(ws[i:i + n]):
                return i, n, k
    return None


def texto_corrido(segs: list[tuple], lingua: str | None = None) -> str:
    """Caminho sem diarização (OV e MLX): os trechos `(início, texto)` de um canal, sem o eco (e,
    com `lingua`, sem a outra escrita), uma linha por trecho. A gravação inteira é uma fala só."""
    return "\n".join(tx for _, _, tx in sem_eco([(t, "", tx) for t, tx in segs], lingua=lingua))


def sem_copias(cauda: list[str], ws: list[str], lim: int = REPETICOES_MAX) -> list[str]:
    """As palavras novas `ws` sem as cópias que fariam um n-grama passar de `lim` seguidas, contando
    a `cauda` já aceita (que não muda). Só sai palavra que é cópia além da `lim`-ésima."""
    tudo = cauda + ws
    while (c := _corrida_longa(tudo, len(cauda), lim)) is not None:
        i, n, k = c
        tudo = tudo[:max(len(cauda), i + lim * n)] + tudo[i + k * n:]
    return tudo[len(cauda):]


def sem_eco(itens: list[tuple], repeticoes_max: int = REPETICOES_MAX,
            lingua: str | None = None) -> list[tuple]:
    """Os itens `(início, falante, texto)`, já em ordem de tempo, sem o eco; a fala recomeça quando
    o falante muda (como no `_merge`). Caminho sem diarização: o mesmo falante em todos. A fala é a
    da SAÍDA: item tirado não separa falas (senão duas metades da mesma fala escapariam da conta).
    Com `lingua` latina, o filtro de escrita (`na_escrita`, #34) roda antes da conta."""
    if lingua in LINGUAS_LATINAS:
        itens = [(*it[:-1], tx) for it in itens if (tx := na_escrita(it[-1], lingua))]
    ok, cauda, falante = [], [], object()
    for item in itens:
        base = cauda if item[1] == falante else []
        ws = item[-1].split()
        if _corrida_longa(base + ws, len(base), repeticoes_max) is not None:
            ws = sem_copias(base, ws, repeticoes_max)
            if not ws:
                continue
            item = (*item[:-1], " ".join(ws))     # só o trecho mexido perde o espaçamento original
        ok.append(item)
        cauda, falante = (base + ws)[-CAUDA_PALAVRAS:], item[1]
    return ok
