"""Entrada do motor: `python -m reco_engine` (do fonte, com cwd=engine/) ou `reco-engine.exe` (congelado).

`--transcribe <áudio> [--diarize]` e `--selftest` são as CLIs herdadas do `reco.py` (cli.py); sem elas,
sobe o servidor JSON Lines (server.py). Imports absolutos: este arquivo é a entrada do PyInstaller.
"""
import sys
from pathlib import Path

if not getattr(sys, "frozen", False):
    # Do fonte: a raiz do repo (pai de engine/) tem o reco.py e o tray.py.
    _raiz = str(Path(__file__).resolve().parent.parent.parent)
    if _raiz not in sys.path:
        sys.path.insert(0, _raiz)


def run() -> int:
    if "--transcribe" in sys.argv or "--selftest" in sys.argv:
        from reco_engine import cli
        return cli.main(sys.argv)
    from reco_engine import server
    return server.main()


if __name__ == "__main__":
    sys.exit(run())
