# build.spec
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Definiere die Ressourcen
added_files = [
    ('fonts/BaiJamjuree-Bold.ttf', 'fonts'),
    ('images/background.png', 'images'),
    ('images/ground.png', 'images'),
    ('images/pipe_down.png', 'images'),
    ('images/pipe_up.png', 'images'),
    ('images/player.png', 'images'),
    ('sounds/score.wav', 'sounds'),
    ('sounds/slap.wav', 'sounds'),
    ('sounds/woosh.wav', 'sounds'),
    ('sounds/select.wav', 'sounds'),
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'pygame._view',
        'tkinter',
        'tkinter.simpledialog',
        'tkinter.messagebox',
        'requests',
        'threading',
        'webbrowser',
        'uuid',
        'numpy',
        'math',
        'json',
        'io',
        'time'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='Flappy-Bird-NSCE',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon='images/icon.ico',
    disable_windowed_traceback=False,
    # version='version_info.txt'  # Auskommentiert falls Probleme
)