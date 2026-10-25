"""
Script dong goi ung dung Smart Auto Click thanh file .exe doc lap bang PyInstaller.
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import os
import shutil
import subprocess
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from version import APP_VERSION, APP_NAME

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def build():
    print("=" * 60)
    print(f"Bat dau dong goi {APP_NAME} v{APP_VERSION} thanh file .exe...")
    print("=" * 60)

    # 1. Dam bao assets da duoc tao
    assets_dir = os.path.join(BASE_DIR, "assets")
    ico_path = os.path.join(assets_dir, "icon.ico")
    if not os.path.exists(ico_path):
        print("Dang tao icon...")
        subprocess.run([sys.executable, "generate_assets.py"], check=True)

    # 2. Xay dung lenh PyInstaller
    sep = ";" if sys.platform.startswith("win") else ":"
    data_arg = f"assets{sep}assets"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=SmartAutoClick",
        "--noconsole",
        "--clean",
        "--onefile",
        f"--icon={ico_path}",
        f"--add-data={data_arg}",
        "--hidden-import=PySide6",
        "--hidden-import=pynput",
        "--hidden-import=pynput.keyboard",
        "--hidden-import=pynput.mouse",
        "--hidden-import=pynput.mouse._win32",
        "--hidden-import=pynput.keyboard._win32",
        "--hidden-import=pyautogui",
        "--hidden-import=cv2",
        "--hidden-import=numpy",
        "--hidden-import=mss",
        "--hidden-import=PIL",
        "--hidden-import=dxcam",
        "main.py"
    ]

    print("Dang thuc thi lenh PyInstaller...")
    res = subprocess.run(cmd, cwd=BASE_DIR)

    if res.returncode == 0:
        print("\n" + "=" * 60)
        print("DONG GOI THANH CONG!")
        exe_path = os.path.join(BASE_DIR, "dist", "SmartAutoClick.exe")
        print(f"Duong dan file EXE: {exe_path}")
        print(f"[{APP_NAME} v{APP_VERSION}] da duoc bundle toan bo assets va dependencies vao 1 file .exe!")
        print("Ban co the click dup vao SmartAutoClick.exe hoac ghim vao Taskbar!")
        print("=" * 60)
    else:
        print("\nQua trinh dong goi gap loi. Vui long kiem tra log o tren.")

if __name__ == "__main__":
    build()
