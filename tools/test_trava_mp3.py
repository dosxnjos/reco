"""Trava do MP3 (#17, 17/11/2026): fechar o arquivo com o `feed` no meio não pode matar o processo.

    python tools/test_trava_mp3.py

O `stop()` espera o thread do codificador por 3 s e fecha o `MP3Writer`; sob carga o
`feed` ainda está rodando. Sem a trava (`captura.TravaEscrita`) isso dá assert do LAME
(rc 3), falha de memória (rc 139) ou `EOFError`. Cada corrida roda num processo filho,
porque o assert mata o processo. Não toca som nem grava: só codifica ruído sintético num
arquivo temporário. Contra o código sem a trava (`git archive` de antes), reprova.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CORRIDA = """
import sys, threading, time
import numpy as np
sys.path.insert(0, sys.argv[1]); import reco
w = reco.MP3Writer(sys.argv[2], 48000, 16000, 2, 96)
b = np.random.default_rng(1).standard_normal(96000).astype(np.float32) * 0.1
erros = []
def alimenta():
    try:
        for _ in range(200): w.feed(b, b)
    except Exception as e: erros.append(repr(e))
th = threading.Thread(target=alimenta); th.start(); time.sleep(0.3)
try: w.close()
except Exception as e: erros.append(repr(e))
th.join(); print("erros", erros)
"""

falhas = 0
with tempfile.TemporaryDirectory() as tmp:
    for i in range(4):
        p = subprocess.run([sys.executable, "-c", CORRIDA, str(RAIZ), str(Path(tmp) / f"c{i}.mp3")],
                           capture_output=True, text=True, timeout=180)
        bom = p.returncode == 0 and "erros []" in p.stdout
        falhas += not bom
        print(f"{'OK   ' if bom else 'FALHA'} fechar com o feed no meio ({i + 1}/4): "
              f"rc={p.returncode} {p.stdout.strip()[-60:]}")
print(f"trava do MP3: falhas {falhas}")
sys.exit(1 if falhas else 0)
