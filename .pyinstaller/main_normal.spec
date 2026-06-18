# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files

# Resolve the icon path relative to the spec invocation so PyInstaller finds it
# Use sys.argv[0] because __file__ may be undefined when PyInstaller executes the spec
ICON_PATH = os.path.normpath(os.path.join(os.path.dirname(sys.argv[0]), '..', 'gustavotube.ico'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ("gustavotube", "gustavotube"),
        (ICON_PATH, "."),
        *collect_data_files('yt_dlp_ejs'),
    ],
    hiddenimports=[
        "gustavotube",
        "yt_dlp_ejs",
        "webbrowser",
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
        "websockets",
        "webbrowser"
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
    icon=ICON_PATH,
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
