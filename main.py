import sys
import os

# Ensure UTF-8 output encoding for Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from core.config_manager import ConfigManager, get_base_dir
from gui.main_window import MainWindow

try:
    import keyboard
except ImportError:
    keyboard = None


def setup_global_hotkeys(window: MainWindow):
    """Đăng ký phím tắt toàn cục F6 và F7."""
    if keyboard is None:
        print("[Hotkey] Thư viện keyboard chưa sẵn sàng. Bỏ qua phím tắt toàn cục.")
        return

    try:
        hotkeys = window.config_manager.get("hotkeys", {})
        key_start_pause = hotkeys.get("start_pause", "f6").lower()
        key_stop = hotkeys.get("stop", "f7").lower()

        def on_f6():
            print(f"[Hotkey] Đã nhấn {key_start_pause.upper()} -> Bật/Tạm dừng")
            window.engine.toggle_pause()

        def on_f7():
            print(f"[Hotkey] Đã nhấn {key_stop.upper()} -> Dừng khẩn cấp")
            window.engine.stop(f"Phím tắt khẩn cấp {key_stop.upper()}")

        keyboard.add_hotkey(key_start_pause, on_f6)
        keyboard.add_hotkey(key_stop, on_f7)
        print(f"[Hotkey] Đã kích hoạt phím tắt toàn cục: {key_start_pause.upper()} (Start/Pause), {key_stop.upper()} (Emergency Stop)")
    except Exception as e:
        print(f"[Hotkey] Cảnh báo khi đăng ký phím tắt (yêu cầu quyền Admin trên một số máy Windows): {e}")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Smart Auto Click")
    app.setOrganizationName("SmartAutoClick")
    # Cho phép ứng dụng tiếp tục chạy ngầm trong khay hệ thống khi ẩn cửa sổ
    app.setQuitOnLastWindowClosed(False)

    base_dir = get_base_dir()
    ico_path = os.path.join(base_dir, "assets", "icon.ico")
    if os.path.exists(ico_path):
        app.setWindowIcon(QIcon(ico_path))

    config_path = os.path.join(base_dir, "config.json")
    config_manager = ConfigManager(config_path)

    window = MainWindow(config_manager)
    window.show()

    # Thiết lập phím tắt toàn cục F6/F7
    setup_global_hotkeys(window)

    # Dọn dẹp phím tắt khi thoát app
    def on_exit():
        if keyboard is not None:
            try:
                keyboard.unhook_all()
            except Exception:
                pass

    app.aboutToQuit.connect(on_exit)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
