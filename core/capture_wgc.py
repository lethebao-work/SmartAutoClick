"""
Bộ adapter Windows Graphics Capture (WGC) cho SmartAutoClick v3.1.

Tính năng (Phase 1):
- V1-T1: Tích hợp thư viện windows-capture (WGC) trên Windows.
- V1-T2: WgcSource gắn theo HWND hoặc Window Title, callback ghi vào bộ đệm 1 ô (single-slot buffer).
- V1-T3: Gắn frame_id tăng dần và monotonic timestamp cho mỗi frame.
- V1-T4: Kiểm tra trạng thái cửa sổ (tồn tại, minimized, đổi kích thước, geometry_version).
- V1-T5: Fail-safe lỗi liên tiếp -> FrameStatus.CAPTURE_ERROR / SOURCE_LOST.
- Kế thừa FrameSource interface chuẩn v3.1.
"""
import logging
import threading
import time
from typing import Any, Dict, Optional, Tuple
import numpy as np

from core.capture_interface import Frame, FrameSource, FrameStatus

log = logging.getLogger("smartautoclick.wgc")

try:
    import windows_capture
    WGC_AVAILABLE = True
except Exception as e:
    windows_capture = None
    WGC_AVAILABLE = False


class WindowGeometryTracker:
    """Theo dõi kích thước và trạng thái của cửa sổ mục tiêu trên Windows."""

    @staticmethod
    def get_window_info(hwnd: int) -> Tuple[bool, bool, Tuple[int, int]]:
        """
        Trả về (exists, is_minimized, client_size).
        """
        if not hwnd:
            return False, False, (0, 0)
        try:
            import win32gui
            if not win32gui.IsWindow(hwnd):
                return False, False, (0, 0)
            is_min = bool(win32gui.IsIconic(hwnd))
            rect = win32gui.GetClientRect(hwnd)
            w = max(0, rect[2] - rect[0])
            h = max(0, rect[3] - rect[1])
            return True, is_min, (w, h)
        except Exception:
            return True, False, (0, 0)

    @staticmethod
    def find_window(title_substring: str) -> Optional[int]:
        """Tìm HWND theo chuỗi tiêu đề."""
        try:
            import win32gui
            found_hwnd = None

            def enum_cb(h, _):
                nonlocal found_hwnd
                if win32gui.IsWindowVisible(h):
                    t = win32gui.GetWindowText(h)
                    if title_substring.lower() in t.lower():
                        found_hwnd = h
                        return False
                return True

            win32gui.EnumWindows(enum_cb, None)
            return found_hwnd
        except Exception:
            return None


class WgcSource(FrameSource):
    """
    Adapter capture Windows Graphics Capture (WGC).
    Capture trực tiếp cửa sổ mục tiêu (HWND), không phụ thuộc vào che khuất desktop.
    Sử dụng kiến trúc single-slot buffer (bộ đệm 1 ô), callback chỉ cập nhật frame mới nhất.
    """

    def __init__(
        self,
        window_hwnd: Optional[int] = None,
        window_title: Optional[str] = None,
        cursor_capture: bool = False,
        draw_border: bool = False,
    ):
        self.window_hwnd = window_hwnd
        self.window_title = window_title
        self.cursor_capture = cursor_capture
        self.draw_border = draw_border

        self._lock = threading.Lock()
        self._latest_image: Optional[np.ndarray] = None
        self._latest_source_ts: Optional[float] = None
        self._frame_id: int = 0
        self._geometry_version: int = 1
        self._last_client_size: Tuple[int, int] = (0, 0)

        self._is_running = False
        self._capture_control: Optional[Any] = None
        self._thread: Optional[threading.Thread] = None
        self._error_count = 0
        self._last_error: Optional[str] = None

    @classmethod
    def is_available(cls) -> bool:
        return WGC_AVAILABLE and windows_capture is not None

    def start(self) -> bool:
        if not self.is_available():
            log.warning("[WgcSource] windows-capture không khả dụng trên hệ thống.")
            return False

        if self.window_hwnd is None and self.window_title is not None:
            self.window_hwnd = WindowGeometryTracker.find_window(self.window_title)

        if not self.window_hwnd:
            log.warning(f"[WgcSource] Không tìm thấy HWND cho cửa sổ: {self.window_title}")
            return False

        # Kiểm tra cửa sổ tồn tại
        exists, is_min, csize = WindowGeometryTracker.get_window_info(self.window_hwnd)
        if not exists:
            log.error(f"[WgcSource] Cửa sổ HWND={self.window_hwnd} không tồn tại.")
            return False

        self._last_client_size = csize
        self._is_running = True
        self._error_count = 0

        # Khởi chạy luồng capture WGC
        self._thread = threading.Thread(target=self._run_capture_loop, daemon=True, name="WgcCaptureThread")
        self._thread.start()
        return True

    def _run_capture_loop(self) -> None:
        try:
            wgc = windows_capture.WindowsCapture(
                cursor_capture=self.cursor_capture,
                draw_border=self.draw_border,
                window_hwnd=self.window_hwnd,
            )

            @wgc.event
            def on_frame_arrived(frame, capture_control):
                if not self._is_running:
                    capture_control.stop()
                    return
                try:
                    arr = frame.to_ndarray()
                    t_now = time.monotonic()
                    with self._lock:
                        self._latest_image = arr
                        self._latest_source_ts = t_now
                        self._frame_id += 1
                        self._error_count = 0
                except Exception as e:
                    with self._lock:
                        self._error_count += 1
                        self._last_error = str(e)

            @wgc.event
            def on_closed():
                log.info("[WgcSource] Luồng capture WGC đã đóng.")
                with self._lock:
                    self._is_running = False

            wgc.start()
        except Exception as e:
            log.error(f"[WgcSource] Khởi động WGC thất bại: {e}")
            with self._lock:
                self._error_count += 1
                self._last_error = str(e)
                self._is_running = False

    def stop(self) -> None:
        self._is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None

    def latest(self) -> Frame:
        """
        Lấy frame mới nhất từ bộ đệm 1 ô (V1-T2 & V1-T3).
        Kiểm tra trạng thái geometry cửa sổ và trả Frame Contract tương ứng.
        """
        t_call = time.monotonic()

        # Kiểm tra cửa sổ mục tiêu
        if self.window_hwnd:
            exists, is_min, csize = WindowGeometryTracker.get_window_info(self.window_hwnd)
            if not exists:
                return Frame(
                    image=None,
                    frame_id=self._frame_id,
                    timestamp=t_call,
                    backend="wgc",
                    status=FrameStatus.SOURCE_LOST,
                    metadata={"error": "Window lost / closed"},
                )
            if is_min:
                return Frame(
                    image=None,
                    frame_id=self._frame_id,
                    timestamp=t_call,
                    backend="wgc",
                    status=FrameStatus.UNRELIABLE,
                    metadata={"error": "Window minimized"},
                )
            # Kiểm tra kích thước client area thay đổi
            if csize != (0, 0) and csize != self._last_client_size:
                self._geometry_version += 1
                self._last_client_size = csize

        with self._lock:
            if self._error_count >= 3:
                return Frame(
                    image=None,
                    frame_id=self._frame_id,
                    timestamp=t_call,
                    backend="wgc",
                    status=FrameStatus.CAPTURE_ERROR,
                    metadata={"error": self._last_error or "Consecutive capture failures"},
                )

            if self._latest_image is None:
                return Frame(
                    image=None,
                    frame_id=self._frame_id,
                    timestamp=t_call,
                    backend="wgc",
                    status=FrameStatus.EMPTY if self._is_running else FrameStatus.SOURCE_LOST,
                )

            img_copy = self._latest_image.copy()
            fid = self._frame_id
            src_ts = self._latest_source_ts

        return Frame(
            image=img_copy,
            frame_id=fid,
            timestamp=src_ts or t_call,
            source_timestamp=src_ts,
            window_id=self.window_hwnd,
            client_size=self._last_client_size,
            geometry_version=self._geometry_version,
            backend="wgc",
            status=FrameStatus.VALID,
        )
