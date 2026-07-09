# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for ZAI Coder CLI — Windows Build
Run: pyinstaller zai-coder.spec

Creates a standalone .exe with all modules bundled.
Supports: Windows 10/11 x64
"""
import os
import sys

block_cipher = None

# ── Version info for Windows executable properties ───────────────────────
VERSION = '1.23.0'
VERSION_TUPLE = (1, 23, 0, 0)

# ── All project modules that need to be hidden imports ────────────────────
HIDDEN_IMPORTS = [
    # Core
    'anthropic',
    'anthropic.types',
    'anthropic.resources',
    'anthropic.resources.beta',
    'anthropic.resources.messages',
    'httpx',
    'httpcore',
    'anyio',
    'sniffio',
    'certifi',
    'h11',
    'distro',
    'jiter',
    'pydantic',
    'pydantic.deprecated',
    'pydantic.v1',
    'dotenv',
    'json',
    'urllib.request',
    'urllib.parse',
    'urllib.error',
    'html.parser',
    'base64',
    'hashlib',
    'hmac',
    'secrets',
    'pathlib',
    'argparse',
    'textwrap',
    'logging',
    'logging.handlers',
    'threading',
    'concurrent.futures',
    'asyncio',
    'dataclasses',
    'typing_extensions',

    # TUI (Textual)
    'textual',
    'textual.app',
    'textual.widgets',
    'textual.containers',
    'textual.binding',
    'textual.reactive',
    'textual.css',
    'rich',
    'rich.console',
    'rich.markdown',
    'rich.syntax',
    'rich.table',
    'rich.panel',
    'rich.live',
    'rich.progress',
    'rich.spinner',
    'markdown_it',
    'linkify_it',

    # Optional deps
    'pandas',
    'openpyxl',
    'pptx',
]

# ── Data files to bundle ─────────────────────────────────────────────────
DATAS = []

# Include any .md files in docs/ for --help reference
docs_dir = os.path.join(os.path.dirname(os.path.abspath(SPECPATH)), 'docs')
if os.path.isdir(docs_dir):
    DATAS.append((docs_dir, 'docs'))

# ── Analysis ─────────────────────────────────────────────────────────────
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=DATAS,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy.distutils',
        'scipy',
        'PIL',
        'IPython',
        'jupyter',
        'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── Executable ───────────────────────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='zai-coder',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Windows version info
    version=os.path.join(os.path.dirname(os.path.abspath(SPECPATH)), 'version_info.txt')
        if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(SPECPATH)), 'version_info.txt'))
        else None,
)
