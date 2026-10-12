"""Visões geradas do Reco: `docs/ARMADILHAS.md` e `roadmap/README.md` a partir de fragmentos.

MOLDE: `cerebro/scripts/visoes_projeto_casca.py` é copiado para `<projeto>/tools/visoes.py` trocando só
`NOME` e `INDICE` (o teste `testar_visoes_projeto.py` roda contra este molde).

Cada armadilha é um arquivo em `docs/armadilhas.d/` (fragmento, imutável depois de commitado); a
visão é GERADA inteira, ignorada pelo git e recompilada pelos hooks post-checkout/post-merge/
post-rewrite/post-commit. O formato e os comandos moram em
`C:/Dev/cerebro/scripts/visoes_projeto.py` (dono único da família "armadilhas de projeto"); aqui só
a tabela do projeto. Fase R4 de `C:/Dev/roadmap/2026-10-01-paralelismo-e-blindagem.md` (12/10/2026).

Uso:
    python tools/visoes.py novo "título curto do sintoma"   # armadilha nova (e visão recompilada)
    python tools/visoes.py compilar --escrever              # o que os hooks rodam
    python tools/visoes.py compilar --verificar             # rc 3 se a visão difere
    python tools/visoes.py validar [arquivos]               # gate-fragmento do pre-commit
    python tools/visoes.py instalar-hooks                   # uma vez por clone/máquina
    python tools/visoes.py resolver-merge                   # merge de branch anterior ao split

Sem o cérebro na máquina (clone fora de C:/Dev, CI), `compilar` avisa e sai 0: hook nunca falha o
git por isso; os outros comandos saem 1.
"""
import importlib.util
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOME = "Reco"
INDICE = True   # True: o projeto tem roadmap/README.md gerado
MODULO = os.path.join("cerebro", "scripts", "visoes_projeto.py")
ENV_MODULO = "VISOES_PROJETO"   # outro visoes_projeto.py (teste)


def modulo():
    """o `visoes_projeto.py` subindo a partir do repo (a principal fica em C:/Dev/<projeto>, um
    worktree em C:/Dev/<projeto>/.claude/worktrees/<x>), ou None."""
    caminho = os.environ.get(ENV_MODULO)
    d = RAIZ
    while not caminho:
        if os.path.isfile(os.path.join(d, MODULO)):
            caminho = os.path.join(d, MODULO)
        elif os.path.dirname(d) == d:
            return None
        d = os.path.dirname(d)
    if not os.path.isfile(caminho):
        return None
    sys.path.insert(0, os.path.dirname(caminho))
    spec = importlib.util.spec_from_file_location("visoes_projeto", caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["visoes_projeto"] = mod
    spec.loader.exec_module(mod)
    return mod


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    vp = modulo()
    if vp is None:
        print(f"aviso: {MODULO} ausente (fora de C:/Dev?): nada feito", file=sys.stderr)
        return 0 if argv[:1] == ["compilar"] else 1
    return vp.main(argv, vp.Projeto(NOME, RAIZ, indice=INDICE))


if __name__ == "__main__":
    sys.exit(main())
