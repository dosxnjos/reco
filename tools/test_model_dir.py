"""Testa _find_model_dir sem hardware nem download real (F5).

Monta uma árvore fake com só o `small` "instalado" e confere:
  - pedido 'small'            -> acha o dir certo
  - pedido 'large-v3-turbo'   -> None (NÃO cai em silêncio no small)

Rodar sempre que mexer em _find_model_dir/ensure_ov_model.
"""
import shutil
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


def main():
    tmp = Path(tempfile.mkdtemp(prefix="reco_test_model_dir_"))
    try:
        import reco

        bundled = tmp / "bundled"
        user = tmp / "user"
        modelo = bundled / "whisper-small-int8-ov"
        modelo.mkdir(parents=True)
        (modelo / reco.MODEL_SENTINEL).write_text("fake", encoding="utf-8")
        user.mkdir(parents=True)   # existe, mas vazio — sem modelo de usuário

        reco._bundled_models_dir = lambda: bundled
        reco._user_data_dir = lambda: user

        achou_small = reco._find_model_dir("small")
        assert achou_small == modelo, f"esperado {modelo}, veio {achou_small}"

        achou_turbo = reco._find_model_dir("large-v3-turbo")
        assert achou_turbo is None, f"esperado None, veio {achou_turbo}"

        # sem `size`, ainda deve achar QUALQUER modelo válido (comportamento antigo).
        achou_qualquer = reco._find_model_dir(None)
        assert achou_qualquer == modelo, f"esperado {modelo}, veio {achou_qualquer}"

        print("OK")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
