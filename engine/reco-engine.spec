# -*- mode: python ; coding: utf-8 -*-
# PyInstaller (onedir) do motor do Reco: engine/dist/reco-engine/reco-engine.exe.
# Build: python engine/build.py  (nunca rodar o PyInstaller da raiz: o padrão escreveria em ./dist,
# onde mora o Reco.exe do app velho). Caminhos derivados de SPECPATH.
#
# - Mesmo collect_all e hiddenimports do reco.spec: o motor importa o reco.py inteiro (tkinter e
#   PIL.ImageTk sem guarda, F2-D9), então NÃO se copiam os EXCLUDES do Lacre (tkinter, av, PIL).
# - Fora: pyarrow e duckdb (~116 MB que o app velho leva sem usar) e os excludes do reco.spec.
# - Sem o modelo `small` bundlado (F2-D8) e sem ícones/assets: o motor não tem janela.
# - console=True (F2-D10): quem sobe (casco, teste) usa CREATE_NO_WINDOW, e nenhuma janela aparece.

import os
from PyInstaller.utils.hooks import collect_all, collect_data_files

ENGINE = os.path.abspath(SPECPATH)
RAIZ = os.path.dirname(ENGINE)

datas, binaries, hiddenimports = [], [], []
for pkg in ("soundcard", "openvino", "openvino_genai", "openvino_tokenizers",
            "av", "huggingface_hub"):
    d, b, h = collect_all(pkg)
    datas += d; binaries += b; hiddenimports += h

# O OpenVINO acha os plugins de device pelo libs/cache.json.
datas += collect_data_files("openvino", includes=["libs/cache.json"])

hiddenimports += [
    "reco", "tray",
    "reco_engine", "reco_engine.server", "reco_engine.cli",
    "soundcard", "cffi", "_cffi_backend",
    "scipy.signal", "scipy.io",
    "openvino", "openvino_genai", "openvino_tokenizers",
    "huggingface_hub", "requests", "tqdm", "filelock", "fsspec",
    "packaging", "yaml",
    "PIL.Image", "PIL.ImageTk", "PIL._tkinter_finder",
]

a = Analysis(
    [os.path.join(ENGINE, "reco_engine", "__main__.py")],
    pathex=[RAIZ, ENGINE],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pyarrow", "duckdb",
        "faster_whisper", "ctranslate2", "tokenizers", "onnxruntime",
        "matplotlib", "cv2", "pandas", "IPython",
        "PyQt5", "PyQt6", "wx",
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="reco-engine",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="reco-engine",
)
