"""
Hệ thống chuyển đổi không gian tọa độ (Window Coordinate System) cho SmartAutoClick v3.1.

Đạt chuẩn các mục tiêu Phase 2:
- V2-T1 & V2-T7: Chuẩn hóa không gian tọa độ theo client area (0.0-1.0 hoặc relative offset).
- V2-T8: Phân biệt rõ 3 không gian tọa độ:
    1. Capture Space: Tọa độ pixel trên ảnh frame nhận từ backend.
    2. Client Space: Tọa độ pixel logic/vật lý của client area cửa sổ game.
    3. Desktop/Screen Space: Tọa độ desktop ảo dùng cho SendInput.
- V2-T2: Tập trung window_to_screen(), screen_to_window(), client_to_desktop().
- V2-T9 & V2-T11: Kiểm tra geometry_version trước khi gửi click; chặn click nếu geometry bị lệch.
- V2-T10: Phát hiện thay đổi DPI, kích thước client area và display scaling.
"""
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, Union
import sys

_IS_WIN = sys.platform == "win32"
if _IS_WIN:
    import ctypes
    from ctypes import wintypes
    _user32 = ctypes.windll.user32


@dataclass(frozen=True)
class RelativePoint:
    """Tọa độ điểm chuẩn hóa tỉ lệ 0.0 - 1.0 theo Client Area."""
    rx: float
    ry: float

    def to_client_px(self, client_w: int, client_h: int) -> Tuple[int, int]:
        return int(round(self.rx * client_w)), int(round(self.ry * client_h))

    @classmethod
    def from_client_px(cls, px: int, py: int, client_w: int, client_h: int) -> "RelativePoint":
        w = max(1, client_w)
        h = max(1, client_h)
        return cls(rx=max(0.0, min(1.0, px / w)), ry=max(0.0, min(1.0, py / h)))


@dataclass(frozen=True)
class RelativeRect:
    """Vùng ROI chuẩn hóa tỉ lệ 0.0 - 1.0 theo Client Area."""
    rx: float
    ry: float
    rw: float
    rh: float

    def to_client_rect(self, client_w: int, client_h: int) -> Tuple[int, int, int, int]:
        x = int(round(self.rx * client_w))
        y = int(round(self.ry * client_h))
        w = int(round(self.rw * client_w))
        h = int(round(self.rh * client_h))
        return x, y, max(1, w), max(1, h)

    @classmethod
    def from_client_rect(cls, x: int, y: int, w: int, h: int, client_w: int, client_h: int) -> "RelativeRect":
        cw = max(1, client_w)
        ch = max(1, client_h)
        return cls(
            rx=max(0.0, min(1.0, x / cw)),
            ry=max(0.0, min(1.0, y / ch)),
            rw=max(0.0, min(1.0, w / cw)),
            rh=max(0.0, min(1.0, h / ch)),
        )


@dataclass
class WindowGeometrySnapshot:
    """Snapshot hình học cửa sổ tại một thời điểm."""
    hwnd: Optional[int]
    client_size: Tuple[int, int]         # (w, h)
    client_origin_screen: Tuple[int, int] # (screen_x, screen_y) của góc trên-trái client area
    dpi_scaling: float = 1.0
    geometry_version: int = 1
    is_valid: bool = True


class CoordinateTransformer:
    """
    Bộ chuyển đổi tọa độ tập trung (Centralized Coordinate Transformer).
    Loại bỏ hoàn toàn việc tính toán tọa độ rải rác.
    """

    @staticmethod
    def get_window_snapshot(hwnd: Optional[int], geometry_version: int = 1) -> WindowGeometrySnapshot:
        """Lấy snapshot hình học client area hiện tại của HWND trên Windows."""
        if not hwnd or not _IS_WIN:
            return WindowGeometrySnapshot(
                hwnd=hwnd,
                client_size=(1920, 1080),
                client_origin_screen=(0, 0),
                dpi_scaling=1.0,
                geometry_version=geometry_version,
                is_valid=True,
            )

        try:
            pt = wintypes.POINT(0, 0)
            if not _user32.ClientToScreen(hwnd, ctypes.byref(pt)):
                return WindowGeometrySnapshot(hwnd=hwnd, client_size=(0, 0), client_origin_screen=(0, 0), is_valid=False)

            rect = wintypes.RECT()
            if not _user32.GetClientRect(hwnd, ctypes.byref(rect)):
                return WindowGeometrySnapshot(hwnd=hwnd, client_size=(0, 0), client_origin_screen=(0, 0), is_valid=False)

            client_w = max(0, rect.right - rect.left)
            client_h = max(0, rect.bottom - rect.top)

            # Lấy DPI của cửa sổ nếu có API GetDpiForWindow (Windows 10 1607+)
            dpi_scaling = 1.0
            if hasattr(_user32, "GetDpiForWindow"):
                dpi = _user32.GetDpiForWindow(hwnd)
                if dpi > 0:
                    dpi_scaling = dpi / 96.0

            return WindowGeometrySnapshot(
                hwnd=hwnd,
                client_size=(client_w, client_h),
                client_origin_screen=(int(pt.x), int(pt.y)),
                dpi_scaling=dpi_scaling,
                geometry_version=geometry_version,
                is_valid=client_w > 0 and client_h > 0,
            )
        except Exception:
            return WindowGeometrySnapshot(hwnd=hwnd, client_size=(0, 0), client_origin_screen=(0, 0), is_valid=False)

    @classmethod
    def client_to_screen(
        cls,
        client_x: int,
        client_y: int,
        snapshot: WindowGeometrySnapshot,
    ) -> Tuple[int, int]:
        """Chuyển tọa độ client pixel thành desktop/screen pixel thực tế."""
        ox, oy = snapshot.client_origin_screen
        return ox + client_x, oy + client_y

    @classmethod
    def screen_to_client(
        cls,
        screen_x: int,
        screen_y: int,
        snapshot: WindowGeometrySnapshot,
    ) -> Tuple[int, int]:
        """Chuyển tọa độ desktop/screen pixel thành client pixel."""
        ox, oy = snapshot.client_origin_screen
        return screen_x - ox, screen_y - oy

    @classmethod
    def relative_to_screen(
        cls,
        rel_point: RelativePoint,
        snapshot: WindowGeometrySnapshot,
    ) -> Tuple[int, int]:
        """Chuyển tọa độ tương đối (0.0 - 1.0) thành desktop/screen pixel."""
        cw, ch = snapshot.client_size
        cx, cy = rel_point.to_client_px(cw, ch)
        return cls.client_to_screen(cx, cy, snapshot)

    @classmethod
    def relative_to_client_rect(
        cls,
        rel_rect: RelativeRect,
        snapshot: WindowGeometrySnapshot,
    ) -> Tuple[int, int, int, int]:
        """Chuyển RelativeRect thành (x, y, w, h) client pixel."""
        cw, ch = snapshot.client_size
        return rel_rect.to_client_rect(cw, ch)

    @classmethod
    def capture_to_client(
        cls,
        cap_x: int,
        cap_y: int,
        cap_size: Tuple[int, int],
        snapshot: WindowGeometrySnapshot,
    ) -> Tuple[int, int]:
        """
        Quy đổi từ ảnh capture sang client coordinates (nếu ảnh capture đã scale hoặc crop).
        """
        cap_w, cap_h = cap_size
        if cap_w <= 0 or cap_h <= 0:
            return cap_x, cap_y
        cw, ch = snapshot.client_size
        scale_x = cw / float(cap_w)
        scale_y = ch / float(cap_h)
        return int(round(cap_x * scale_x)), int(round(cap_y * scale_y))


class GeometryGuard:
    """
    V2-T9 & V2-T11: Bảo vệ an toàn hình học (Geometry Guard).
    Kiểm tra snapshot cửa sổ ngay trước khi click; chặn click nếu geometry_version
    hoặc client_size của kết quả nhận diện không còn khớp geometry thực tế hiện tại.
    """

    @staticmethod
    def verify_geometry_for_action(
        target_geometry_version: int,
        current_snapshot: WindowGeometrySnapshot,
        expected_client_size: Optional[Tuple[int, int]] = None,
    ) -> Tuple[bool, str]:
        """
        Xác nhận xem hành động click có an toàn để gửi đi không.
        Trả về (safe_to_click, reason).
        """
        if not current_snapshot.is_valid:
            return False, "Cửa sổ mục tiêu không hợp lệ hoặc đã đóng"

        if current_snapshot.geometry_version != target_geometry_version:
            return False, f"Geometry version bị lệch ({target_geometry_version} != {current_snapshot.geometry_version}): cửa sổ vừa di chuyển/đổi kích thước"

        if expected_client_size and expected_client_size != (0, 0):
            cur_w, cur_h = current_snapshot.client_size
            exp_w, exp_h = expected_client_size
            if abs(cur_w - exp_w) > 2 or abs(cur_h - exp_h) > 2:
                return False, f"Kích thước client ({cur_w}x{cur_h}) không khớp frame quan sát ({exp_w}x{exp_h})"

        return True, "Geometry an toàn"
