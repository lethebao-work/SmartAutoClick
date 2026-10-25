# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets')],
    hiddenimports=['PySide6', 'pynput', 'pynput.keyboard', 'pynput.mouse', 'pynput.mouse._win32', 'pynput.keyboard._win32', 'pyautogui', 'cv2', 'numpy', 'mss', 'PIL', 'dxcam', 'windows_capture', 'psutil', 'win32gui', 'win32ui', 'win32con'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SmartAutoClick',
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
    icon=['C:\\Users\\lethe\\Downloads\\FreeTime\\SmartAutoClick\\assets\\icon.ico'],
)
