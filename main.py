import sys
import os

# ── DPI awareness: PHẢI chạy trước mọi import khác ────────────────────────────────────────────
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # PER_MONITOR_AWARE_V2
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_AWARE (Win 8.1)
        except Exception:
            pass

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
from version import APP_VERSION, APP_NAME, APP_BUILD_DATE

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
            window.validate_and_toggle_pause()

        def on_f7():
            print(f"[Hotkey] Đã nhấn {key_stop.upper()} -> Dừng khẩn cấp")
            window.engine.stop(f"Phím tắt khẩn cấp {key_stop.upper()}")

        keyboard.add_hotkey(key_start_pause, on_f6)
        keyboard.add_hotkey(key_stop, on_f7)
        print(f"[Hotkey] Đã kích hoạt phím tắt toàn cục: {key_start_pause.upper()} (Start/Pause), {key_stop.upper()} (Emergency Stop)")
    except Exception as e:
        print(f"[Hotkey] Cảnh báo khi đăng ký phím tắt (yêu cầu quyền Admin trên một số máy Windows): {e}")


def get_resource_path(relative_path: str) -> str:
    """Trả về đường dẫn tài nguyên (tương thích cả khi chạy script và đóng gói PyInstaller)."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(get_base_dir(), relative_path)


def main():
    # (DPI awareness đã được đặt ở đầu file, trước mọi import)
    print(f"{'='*50}")
    print(f"  {APP_NAME} v{APP_VERSION}  (build {APP_BUILD_DATE})")
    print(f"{'='*50}")

    app = QApplication(sys.argv)
    app.setApplicationName("Smart Auto Click")
    app.setOrganizationName("SmartAutoClick")
    # Cho phép ứng dụng tiếp tục chạy ngầm trong khay hệ thống khi ẩn cửa sổ
    app.setQuitOnLastWindowClosed(False)

    base_dir = get_base_dir()
    ico_path = get_resource_path(os.path.join("assets", "icon.ico"))
    if os.path.exists(ico_path):
        app.setWindowIcon(QIcon(ico_path))

    config_path = os.path.join(base_dir, "config.json")
    config_manager = ConfigManager(config_path)

    window = MainWindow(config_manager)
    window.show()

    # Kiểm tra quyền Admin (UIPI) để cảnh báo người dùng nếu game chạy Admin
    if sys.platform == "win32":
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            if not is_admin:
                window.append_log(
                    "[LƯU Ý QUYỀN] Ứng dụng đang chạy ở quyền User thường. Nếu Game của bạn chạy bằng 'Run as Administrator', hãy mở SmartAutoClick bằng Administrator để không bị Windows UIPI chặn click chuột.",
                    "WARN"
                )
            else:
                window.append_log("Đang chạy với quyền Administrator (Toàn quyền tương tác phím/chuột).", "INFO")
        except Exception:
            pass

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
