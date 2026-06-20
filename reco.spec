# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 6+ spec for Reco.  Build with:  .\build.ps1 -Clean
# Add an icon later with:  .\build.ps1 -Icon reco.ico

from PyInstaller.utils.hooks import collect_all

# soundcard loads cffi at runtime — collect package data + binaries.
_sc_datas, _sc_binaries, _sc_hidden = collect_all('soundcard')

a = Analysis(
    ['reco.py'],
    pathex=[],
    binaries=_sc_binaries,
    datas=_sc_datas + [('logo/logo_symbol_1x1.ico', 'logo')],
    hiddenimports=[
        *_sc_hidden,
        'soundcard',
        'cffi',
        '_cffi_backend',
        'lameenc',
        'scipy.signal',
        'scipy.io',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # faster-whisper is NOT bundled (huge). In the .exe, transcription is
        # delegated to the system Python; the in-app installer sets it up.
        'faster_whisper', 'ctranslate2', 'huggingface_hub',
        'tokenizers', 'onnxruntime',
        # av (PyAV) only powers the MP3 duration column; falls back to "—".
        'av',
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
    a.binaries,
    a.datas,
    [],
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
