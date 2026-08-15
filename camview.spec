# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller specification file for CamView.

Supports building standalone executables for:
  - Linux (ELF binary)
  - Windows (.exe)
  - macOS (.app bundle)
"""

import sys
import os
from pathlib import Path

block_cipher = None

# Base path
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))

# Data files to bundle: (source_path, target_subfolder)
datas = [
    (os.path.join(ROOT_DIR, 'src', 'assets'), os.path.join('src', 'assets')),
]

# Hidden imports to ensure PySide6 and OpenCV DNN submodules are included
hiddenimports = [
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'cv2',
    'numpy',
    'sqlite3',
    'urllib.request',
    'json',
    'dataclasses',
    'threading',
    'queue',
    'src.core.connection',
    'src.core.stream_worker',
    'src.core.ai_detector',
    'src.core.event_db',
    'src.core.config_store',
    'src.core.resource_path',
    'src.styles.theme',
    'src.views.login_window',
    'src.views.viewer_window',
    'src.views.settings_dialog',
    'src.views.events_window',
]

# Exclude unnecessary heavy packages if present in environment
excludes = [
    'tkinter',
    'matplotlib',
    'scipy',
    'torch',
    'torchvision',
    'IPython',
    'unittest',
    'pytest',
]

a = Analysis(
    ['main.py'],
    pathex=[ROOT_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Windows / macOS icon resolution
icon_path = None
if sys.platform == 'win32':
    ico_candidate = os.path.join(ROOT_DIR, 'src', 'assets', 'icon.ico')
    if os.path.exists(ico_candidate):
        icon_path = ico_candidate
elif sys.platform == 'darwin':
    icns_candidate = os.path.join(ROOT_DIR, 'src', 'assets', 'icon.icns')
    if os.path.exists(icns_candidate):
        icon_path = icns_candidate

exe_name = 'CamView'
if sys.platform == 'win32':
    exe_name = 'CamView.exe'

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=exe_name,
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
    icon=icon_path,
)

# On macOS, generate standard .app Bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='CamView.app',
        icon=icon_path,
        bundle_identifier='com.camview.dvr',
        info_plist={
            'CFBundleDisplayName': 'CamView',
            'CFBundleName': 'CamView',
            'CFBundlePackageType': 'APPL',
            'CFBundleShortVersionString': '0.1.0',
            'CFBundleVersion': '0.1.0',
            'NSHighResolutionCapable': 'True',
            'NSRequiresAquaSystemAppearance': 'False',
            'NSCameraUsageDescription': 'CamView accesses network DVR RTSP video streams.',
        },
    )
