# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 6+ spec for Reco.  Build with:  .\build.ps1 -Clean
#
# ONEDIR build (dist/Reco/Reco.exe + _internal/). The OpenVINO runtime is large
# (~0.5 GB with the NPU/iGPU/CPU plugins), so a onefile build would unpack that
# to %TEMP% on every launch — onedir keeps startup instant. The Whisper model
# (INT8 IR) is downloaded from Hugging Face on first use, not bundled.

import os
from PyInstaller.utils.hooks import collect_all, collect_data_files

datas, binaries, hiddenimports = [], [], []

# Bundle the Whisper model (INT8 IR) for a fully-offline first run. The model
# updates rarely, so we ship it; if the folder isn't present at build time the app
# falls back to download-on-first-use. build.ps1 fetches it before building.
_model = os.path.join("models", "whisper-small-int8-ov")
if os.path.isfile(os.path.join(_model, "openvino_encoder_model.xml")):
    datas += [(_model, _model)]

# soundcard loads cffi at runtime — collect package data + binaries.
for pkg in ("soundcard", "openvino", "openvino_genai", "openvino_tokenizers",
            "av", "huggingface_hub"):
    d, b, h = collect_all(pkg)
    datas += d; binaries += b; hiddenimports += h

# OpenVINO discovers its device plugins through libs/cache.json (no plugins.xml
# in recent builds) — make sure it travels with the DLLs.
datas += collect_data_files("openvino", includes=["libs/cache.json"])

hiddenimports += [
    "soundcard", "cffi", "_cffi_backend", "lameenc",
    "scipy.signal", "scipy.io",
    "openvino", "openvino_genai", "openvino_tokenizers",
    # huggingface_hub pulls these lazily during snapshot_download
    "huggingface_hub", "requests", "tqdm", "filelock", "fsspec",
    "packaging", "yaml",
]

a = Analysis(
    ['reco.py'],
    pathex=[],
    binaries=binaries,
    datas=datas + [('logo/logo_symbol_1x1.ico', 'logo')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # we don't use these transcription stacks (OpenVINO replaces them)
        'faster_whisper', 'ctranslate2', 'tokenizers', 'onnxruntime',
        # heavy libs we don't use
        'matplotlib', 'PIL', 'cv2', 'pandas', 'IPython',
        'PyQt5', 'PyQt6', 'wx',
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
    name='Reco',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,                # windowed (no console)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='logo/logo_symbol_1x1.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Reco',
)
