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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def build():
    print("=" * 60)
    print("Bat dau dong goi Smart Auto Click v2.0 thanh file .exe...")
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
        "main.py"
    ]

    print("Dang thuc thi lenh PyInstaller...")
    res = subprocess.run(cmd, cwd=BASE_DIR)

    if res.returncode == 0:
        print("\n" + "=" * 60)
        print("DONG GOI THANH CONG!")
        exe_path = os.path.join(BASE_DIR, "dist", "SmartAutoClick.exe")
        print(f"Duong dan file EXE: {exe_path}")
        
        # Sao chep config.json sang thu muc dist
        dist_config = os.path.join(BASE_DIR, "dist", "config.json")
        src_config = os.path.join(BASE_DIR, "config.json")
        if os.path.exists(src_config) and not os.path.exists(dist_config):
            shutil.copy2(src_config, dist_config)
            print("Da sao chep config.json sang thu muc dist.")
            
        # Sao chep thu muc assets sang dist
        dist_assets = os.path.join(BASE_DIR, "dist", "assets")
        if not os.path.exists(dist_assets):
            shutil.copytree(assets_dir, dist_assets)
            print("Da sao chep thu muc assets sang dist.")

        print("Ban co the click dup vao SmartAutoClick.exe hoac ghim vao Taskbar!")
        print("=" * 60)
    else:
        print("\nQua trinh dong goi gap loi. Vui long kiem tra log o tren.")

if __name__ == "__main__":
    build()
