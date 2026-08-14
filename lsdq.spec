# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['desktop.py'],
    pathex=['D:\\LSDQ'],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
    ],
    hiddenimports=[
        'ollama',
        'requests',
        'numpy',
        'pypdf',
        'docx',
        'pptx',
        'openpyxl',
        'webview',
        'webview.platforms.winforms',
        'webview.platforms.edgechromium',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='LSDQ',
    debug=False,
    console=False,
)