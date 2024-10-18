# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ("pyarmor_runtime_000000", "pyarmor_runtime_000000"),
        ("gustavotube", "gustavotube")
    ],
    hiddenimports=[
        "gustavotube",
        "tkinter",
        "tkinter.filedialog",
        "tkinter.ttk",
        "tkinter.messagebox",
        "yt_dlp",
        "brotli",
        "brotlicffi",
        "certifi",
        "cffi",
        "charset-normalizer",
        "idna",
        "mutagen",
        "pycparser",
        "pycryptodomex",
        "requests",
        "urllib3",
        "websockets"
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='GustavoTube',
    icon='.pyinstaller/gustavotube.ico',
    version='.pyinstaller/versionfile.txt',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=False
)

block_cipher = None
