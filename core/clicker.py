import random
import sys
import time
from typing import Tuple, Optional, Any

_IS_WIN = sys.platform == "win32"

if _IS_WIN:
    import ctypes
    from ctypes import wintypes

    _user32 = ctypes.windll.user32
    _ULONG_PTR = ctypes.c_size_t

    class _MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", _ULONG_PTR)]

    class _INPUT_UNION(ctypes.Union):
        _fields_ = [("mi", _MOUSEINPUT)]

    class _INPUT(ctypes.Structure):
        _anonymous_ = ("u",)
        _fields_ = [("type", wintypes.DWORD), ("u", _INPUT_UNION)]

    _INPUT_MOUSE = 0
    _MOVE, _LDOWN, _LUP, _RDOWN, _RUP, _MDOWN, _MUP = 0x0001, 0x0002, 0x0004, 0x0008, 0x0010, 0x0020, 0x0040
    _ABSOLUTE, _VIRTUALDESK = 0x8000, 0x4000
    _BTN = {"left": (_LDOWN, _LUP), "right": (_RDOWN, _RUP), "middle": (_MDOWN, _MUP)}


class InputSimulator:
    """
    Mô phỏng chuột.

    Windows: SendInput trực tiếp (move tuyệt đối + nhấn trong một lệnh, nhả sau hold_s),
    cỡ <1ms mỗi lệnh; tọa độ là pixel vật lý (process phải DPI-aware).
    Nền tảng khác / SendInput lỗi: dự phòng bằng pyautogui (nạp lười, không ép DPI lúc import).
    """

    def __init__(self, randomize_offset: bool = True, jitter_px: int = 1, hold_s: float = 0.02, failsafe: bool = True):
        self.randomize_offset = randomize_offset
        self.jitter_px = max(0, int(jitter_px))
        self.hold_s = max(0.0, float(hold_s))
        self.failsafe = failsafe  # góc trên-trái (0,0) = hủy, giống pyautogui

    # ── vị trí chuột ─────────────────────────────────────────────────────────
    @staticmethod
    def get_mouse_position() -> Tuple[int, int]:
        if _IS_WIN:
            try:
                pt = wintypes.POINT()
                if _user32.GetCursorPos(ctypes.byref(pt)):
                    return int(pt.x), int(pt.y)
            except Exception:
                pass
        try:
            import pyautogui
            p = pyautogui.position()
            return int(p.x), int(p.y)
        except Exception:
            return (0, 0)

    # ── SendInput ────────────────────────────────────────────────────────────
    @staticmethod
    def _norm(x: int, y: int) -> Tuple[int, int]:
        vx, vy = _user32.GetSystemMetrics(76), _user32.GetSystemMetrics(77)   # SM_X/YVIRTUALSCREEN
        vw, vh = _user32.GetSystemMetrics(78), _user32.GetSystemMetrics(79)   # SM_CX/CYVIRTUALSCREEN
        nx = int(round((x - vx) * 65535 / max(1, vw - 1)))
        ny = int(round((y - vy) * 65535 / max(1, vh - 1)))
        return max(0, min(65535, nx)), max(0, min(65535, ny))

    @staticmethod
    def _send(*events) -> bool:
        arr = (_INPUT * len(events))(*events)
        return _user32.SendInput(len(events), arr, ctypes.sizeof(_INPUT)) == len(events)

    @staticmethod
    def _mouse_event(flags: int, nx: int = 0, ny: int = 0):
        e = _INPUT(type=_INPUT_MOUSE)
        e.mi = _MOUSEINPUT(nx, ny, 0, flags, 0, 0)
        return e

    def _click_sendinput(self, x: int, y: int, button: str) -> bool:
        down, up = _BTN.get(button, _BTN["left"])
        nx, ny = self._norm(x, y)
        move = _MOVE | _ABSOLUTE | _VIRTUALDESK
        if not self._send(self._mouse_event(move | down, nx, ny)):
            return False
        if self.hold_s:
            time.sleep(self.hold_s)
        return self._send(self._mouse_event(up))

    # ── Tọa độ Cửa sổ & Tương đối (Phase 2 - V2-T2, V2-T9, V2-T11) ───────────
    @staticmethod
    def window_to_screen(
        client_x: int,
        client_y: int,
        hwnd: Optional[int] = None,
        snapshot: Optional[Any] = None,
    ) -> Tuple[int, int]:
        """Chuyển tọa độ client pixel của cửa sổ thành screen/desktop pixel."""
        from core.coordinates import CoordinateTransformer
        snap = snapshot or CoordinateTransformer.get_window_snapshot(hwnd)
        return CoordinateTransformer.client_to_screen(client_x, client_y, snap)

    @staticmethod
    def screen_to_window(
        screen_x: int,
        screen_y: int,
        hwnd: Optional[int] = None,
        snapshot: Optional[Any] = None,
    ) -> Tuple[int, int]:
        """Chuyển tọa độ screen/desktop pixel thành client pixel của cửa sổ."""
        from core.coordinates import CoordinateTransformer
        snap = snapshot or CoordinateTransformer.get_window_snapshot(hwnd)
        return CoordinateTransformer.screen_to_client(screen_x, screen_y, snap)

    def click_relative(
        self,
        rx: float,
        ry: float,
        hwnd: Optional[int] = None,
        expected_geometry_version: Optional[int] = None,
        button: str = "left",
    ) -> bool:
        """
        Click theo tọa độ tương đối (0.0 - 1.0) của cửa sổ game (V2-T1 & V2-T7).
        Chặn click an toàn nếu geometry không khớp (V2-T11).
        """
        from core.coordinates import CoordinateTransformer, RelativePoint, GeometryGuard

        snapshot = CoordinateTransformer.get_window_snapshot(hwnd)
        if expected_geometry_version is not None:
            safe, reason = GeometryGuard.verify_geometry_for_action(
                target_geometry_version=expected_geometry_version,
                current_snapshot=snapshot,
            )
            if not safe:
                print(f"[InputSimulator] Chặn click do geometry không an toàn: {reason}")
                return False

        sx, sy = CoordinateTransformer.relative_to_screen(RelativePoint(rx, ry), snapshot)
        return self.click(sx, sy, button=button)

    # ── API chung ────────────────────────────────────────────────────────────
    def click(self, x: int, y: int, button: str = "left", duration: float = 0.0) -> bool:
        """Click tại (x, y) desktop pixel. `duration` giữ để tương thích API cũ."""
        tx, ty = int(x), int(y)
        if self.randomize_offset and self.jitter_px:
            tx += random.randint(-self.jitter_px, self.jitter_px)
            ty += random.randint(-self.jitter_px, self.jitter_px)

        if self.failsafe and self.get_mouse_position() == (0, 0):
            print("[InputSimulator] Con trỏ đang ở góc (0,0): hủy click (fail-safe).")
            return False

        if _IS_WIN:
            try:
                if self._click_sendinput(tx, ty, button):
                    return True
                print("[InputSimulator] SendInput thất bại (có thể game chạy quyền Admin - UIPI). Thử pyautogui...")
            except Exception as e:
                print(f"[InputSimulator] SendInput lỗi: {e}. Thử pyautogui...")

        try:
            import pyautogui
            pyautogui.FAILSAFE = False  # fail-safe đã xử lý ở trên
            pyautogui.PAUSE = 0
            pyautogui.click(tx, ty, button=button)
            return True
        except Exception as e:
            print(f"[InputSimulator] Lỗi click ({x}, {y}): {e}")
            return False
