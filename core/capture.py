"""
Screen capture cho SmartAutoClick.

Chuỗi backend (tự chọn, tự hạ cấp, luôn log backend đang dùng):

    dxgi  (dxcam / DXGI Desktop Duplication)  - nhanh nhất, hợp windowed + borderless
    mss   (GDI BitBlt)                        - dự phòng ổn định
    pil   (ImageGrab)                         - dự phòng cuối, chậm

Nguyên tắc:
- Backend nào ném lỗi 3 lần liên tiếp bị "nghỉ" 5 giây rồi thử lại.
- Backend trả ảnh đen thuần bị coi là KHÔNG nhìn thấy gì (exclusive fullscreen,
  khóa màn hình, nội dung được bảo vệ) và chuyển sang backend kế tiếp.
- Tất cả backend đều ảnh đen / lỗi -> CaptureError (không bao giờ trả ảnh đen im lặng).
- Tọa độ là PIXEL VẬT LÝ của desktop ảo (process phải DPI-aware, xem main.py).
"""
import logging
import os
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

try:
    import mss
except ImportError:
    mss = None

try:
    from PIL import ImageGrab
except ImportError:
    ImageGrab = None

dxcam = None
if sys.platform == "win32":
    try:
        import dxcam  # type: ignore
    except Exception:  # ImportError hoặc lỗi nạp DLL
        dxcam = None

log = logging.getLogger("smartautoclick.capture")

Rect = Tuple[int, int, int, int]  # x, y, w, h


class CaptureError(Exception):
    """Chụp màn hình thất bại hoặc chỉ nhận được ảnh đen thuần."""
    pass


class BackendUnavailable(Exception):
    """Backend không phục vụ được yêu cầu này (không tính là lỗi, không bị phạt)."""
    pass


# ──────────────────────────────────────────────────────────────────────────────
# Backends
# ──────────────────────────────────────────────────────────────────────────────

class _Backend:
    name = "base"

    def available(self) -> bool:
        return False

    def grab(self, x: int, y: int, w: int, h: int) -> np.ndarray:
        raise NotImplementedError

    def close(self) -> None:
        pass


class MssBackend(_Backend):
    """GDI BitBlt qua mss. Mỗi thread có instance riêng (handle GDI gắn với thread)."""
    name = "mss"

    def __init__(self):
        self._local = threading.local()
        self._all: List[Any] = []
        self._lock = threading.Lock()

    def available(self) -> bool:
        return mss is not None

    def _sct(self):
        sct = getattr(self._local, "sct", None)
        if sct is None:
            sct = mss.mss()
            self._local.sct = sct
            with self._lock:
                self._all.append(sct)
        return sct

    def grab(self, x, y, w, h):
        shot = self._sct().grab({"left": int(x), "top": int(y), "width": int(w), "height": int(h)})
        arr = np.frombuffer(shot.bgra, dtype=np.uint8).reshape(shot.height, shot.width, 4)
        if arr.shape[0] != h or arr.shape[1] != w:
            raise RuntimeError(f"mss trả kích thước {arr.shape[1]}x{arr.shape[0]}, cần {w}x{h}")
        if cv2 is not None:
            return cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
        return np.ascontiguousarray(arr[:, :, :3])

    def close(self):
        with self._lock:
            sessions, self._all = self._all, []
        for s in sessions:
            try:
                s.close()
            except Exception:
                pass
        self._local = threading.local()


class DxgiBackend(_Backend):
    """
    DXGI Desktop Duplication qua dxcam. Chỉ phục vụ màn hình CHÍNH
    (gốc tọa độ (0,0) trong desktop ảo của Windows). Vùng nằm ngoài màn hình chính
    -> BackendUnavailable để chuỗi chuyển sang mss.

    dxcam có thể trả None khi màn hình không đổi kể từ lần grab trước. Ta chỉ dùng
    lại khung cũ khi lần grab trước là CÙNG một vùng (nếu khác vùng thì khung cũ
    có thể đã lỗi thời -> BackendUnavailable).
    """
    name = "dxgi"

    def __init__(self, output_idx: int = 0):
        self.output_idx = output_idx
        self._lock = threading.Lock()
        self._cam = None
        self._size: Optional[Tuple[int, int]] = None
        self._last_key: Optional[Rect] = None
        self._last_frame: Optional[np.ndarray] = None

    def available(self) -> bool:
        return dxcam is not None

    def _ensure(self):
        if self._cam is None:
            self._cam = dxcam.create(output_idx=self.output_idx, output_color="BGR")
            if self._cam is None:
                raise RuntimeError("dxcam.create trả None")
            self._size = (int(self._cam.width), int(self._cam.height))

    def grab(self, x, y, w, h):
        with self._lock:
            self._ensure()
            W, H = self._size
            if x < 0 or y < 0 or x + w > W or y + h > H:
                raise BackendUnavailable("vùng nằm ngoài màn hình chính")
            key = (x, y, w, h)
            deadline = time.perf_counter() + 0.05
            while True:
                frame = self._cam.grab(region=(x, y, x + w, y + h))
                if frame is not None:
                    frame = np.ascontiguousarray(frame)
                    self._last_key, self._last_frame = key, frame
                    return frame
                if key == self._last_key and self._last_frame is not None:
                    return self._last_frame  # màn hình không đổi kể từ lần grab cùng vùng
                if time.perf_counter() > deadline:
                    raise BackendUnavailable("DXGI chưa có khung mới cho vùng này")
                time.sleep(0.002)

    def close(self):
        with self._lock:
            cam, self._cam = self._cam, None
            self._last_key = self._last_frame = None
        if cam is not None:
            try:
                cam.release()
            except Exception:
                pass


class WgcBackend(_Backend):
    """
    Windows Graphics Capture qua windows_capture (V1-T6).
    Chụp trực tiếp cửa sổ/màn hình bằng Windows Modern Graphics Capture API.
    """
    name = "wgc"

    def __init__(self, hwnd: Optional[int] = None):
        self.hwnd = hwnd
        self._source = None
        self._lock = threading.Lock()

    def available(self) -> bool:
        if sys.platform != "win32":
            return False
        try:
            from core.capture_wgc import WgcSource
            return WgcSource.is_available()
        except Exception:
            return False

    def grab(self, x: int, y: int, w: int, h: int) -> np.ndarray:
        with self._lock:
            if self._source is None:
                from core.capture_wgc import WgcSource
                self._source = WgcSource(window_hwnd=self.hwnd)
                if not self._source.start():
                    raise BackendUnavailable("WGC start thất bại hoặc không tìm thấy cửa sổ")
                # Cho thời gian nhận khung đầu
                time.sleep(0.05)

            frame = self._source.latest()
            if not frame.is_valid or frame.image is None:
                raise BackendUnavailable(f"WGC chưa có khung hợp lệ ({frame.status})")
            img = frame.image
            fh, fw = img.shape[:2]
            x0, y0 = max(0, int(x)), max(0, int(y))
            x1, y1 = min(fw, x0 + int(w)), min(fh, y0 + int(h))
            if x1 <= x0 or y1 <= y0:
                raise BackendUnavailable("Vùng nằm ngoài kích thước ảnh WGC")
            return np.ascontiguousarray(img[y0:y1, x0:x1])

    def close(self) -> None:
        with self._lock:
            if self._source is not None:
                try:
                    self._source.stop()
                except Exception:
                    pass
                self._source = None


class PilBackend(_Backend):
    name = "pil"

    def available(self) -> bool:
        return ImageGrab is not None

    def grab(self, x, y, w, h):
        try:
            img = ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True)
        except TypeError:  # nền tảng không có all_screens
            img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
        arr = np.array(img.convert("RGB"))
        if cv2 is not None:
            return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        return np.ascontiguousarray(arr[:, :, ::-1])


# ──────────────────────────────────────────────────────────────────────────────
# ScreenCapture (API cũ giữ nguyên: capture_region / capture_fullscreen / save_image / close)
# ──────────────────────────────────────────────────────────────────────────────

from core.capture_interface import FrameSource, Frame, FrameStatus, to_frame

_FAIL_LIMIT = 3
_COOLDOWN_S = 5.0


class ScreenCapture(FrameSource):
    def __init__(self, backend: str = "auto", backends: Optional[Sequence[_Backend]] = None):
        """
        backend: "auto" | "dxgi" | "mss" | "pil" (backend ưu tiên; phần còn lại là dự phòng).
        backends: chuỗi backend tự cung cấp (dùng cho test).
        """
        self.requested_backend = (backend or "auto").lower()
        self._chain: List[_Backend] = list(backends) if backends is not None else self._build_chain(self.requested_backend)
        self._st: Dict[str, Dict[str, float]] = {
            b.name: {"fails": 0, "skip_until": 0.0, "ok": 0, "black": 0, "total_ms": 0.0, "last_ms": 0.0}
            for b in self._chain
        }
        self.active_backend: Optional[str] = None
        self._stat_lock = threading.Lock()
        self._frame_id: int = 0
        self._is_running: bool = False

    def start(self) -> bool:
        self._is_running = True
        return len(self._chain) > 0

    def stop(self) -> None:
        self._is_running = False
        self.close()

    def latest(self) -> Frame:
        """Trả về Frame Contract toàn màn hình hoặc frame gần nhất."""
        w, h = self._primary_size()
        t_capture = time.monotonic()
        try:
            img = self.capture_region(0, 0, w, h)
            self._frame_id += 1
            return Frame(
                image=img,
                frame_id=self._frame_id,
                timestamp=t_capture,
                backend=self.active_backend or "unknown",
                status=FrameStatus.VALID,
                client_size=(w, h),
                geometry_version=1,
            )
        except Exception as e:
            self._frame_id += 1
            return Frame(
                image=None,
                frame_id=self._frame_id,
                timestamp=t_capture,
                backend=self.active_backend or "unknown",
                status=FrameStatus.CAPTURE_ERROR,
                client_size=(w, h),
                metadata={"error": str(e)},
            )

    # ── chuỗi backend ────────────────────────────────────────────────────────
    @staticmethod
    def _build_chain(pref: str) -> List[_Backend]:
        all_be = {"wgc": WgcBackend, "dxgi": DxgiBackend, "mss": MssBackend, "pil": PilBackend}
        order = {
            "auto": ["wgc", "dxgi", "mss", "pil"],
            "wgc": ["wgc", "dxgi", "mss", "pil"],
            "dxgi": ["dxgi", "mss", "pil"],
            "mss": ["mss", "pil"],
            "pil": ["pil"],
        }.get(pref, ["wgc", "dxgi", "mss", "pil"])
        chain = []
        for name in order:
            be = all_be[name]()
            if be.available():
                chain.append(be)
        return chain

    @property
    def backend_names(self) -> List[str]:
        return [b.name for b in self._chain]

    # ── chụp một vùng ────────────────────────────────────────────────────────
    def capture_region(self, x: int, y: int, w: int, h: int, allow_blank: bool = False) -> np.ndarray:
        """
        Trả mảng BGR uint8 (h, w, 3). Ném CaptureError nếu mọi backend lỗi hoặc chỉ ra ảnh đen.
        """
        x, y, w, h = int(x), int(y), int(w), int(h)
        if w <= 0 or h <= 0:
            raise ValueError(f"Invalid region dimensions: w={w}, h={h}")

        errors: List[str] = []
        saw_black = False
        for be in self._chain:
            st = self._st[be.name]
            if time.monotonic() < st["skip_until"]:
                continue
            t0 = time.perf_counter()
            try:
                img = be.grab(x, y, w, h)
            except BackendUnavailable as e:
                errors.append(f"{be.name}: {e}")
                continue
            except Exception as e:
                with self._stat_lock:
                    st["fails"] += 1
                    if st["fails"] >= _FAIL_LIMIT:
                        st["skip_until"] = time.monotonic() + _COOLDOWN_S
                        st["fails"] = 0
                        log.warning("Backend %s lỗi %d lần liên tiếp, tạm nghỉ %.0fs: %s", be.name, _FAIL_LIMIT, _COOLDOWN_S, e)
                errors.append(f"{be.name}: {e}")
                continue
            ms = (time.perf_counter() - t0) * 1000.0

            if not allow_blank and not img.any():  # ảnh đen thuần (nhanh hơn mean/std ~13 lần)
                with self._stat_lock:
                    st["black"] += 1
                saw_black = True
                errors.append(f"{be.name}: ảnh đen thuần")
                continue

            with self._stat_lock:
                st["fails"] = 0
                st["ok"] += 1
                st["last_ms"] = ms
                st["total_ms"] += ms
            if self.active_backend != be.name:
                log.info("Backend chụp màn hình: %s (trước đó: %s)", be.name, self.active_backend)
                print(f"[ScreenCapture] Backend: {be.name}")
                self.active_backend = be.name
            return img

        if allow_blank:
            return np.zeros((h, w, 3), dtype=np.uint8)
        hint = ""
        if saw_black:
            hint = " Gợi ý: nếu game chạy Exclusive Fullscreen hãy chuyển sang Borderless/Windowed; nếu không, màn hình có thể đang khóa/ngủ."
        raise CaptureError(
            f"Không chụp được vùng ({x}, {y}, {w}, {h}). Chi tiết: {'; '.join(errors) or 'không có backend khả dụng'}.{hint}"
        )

    def capture_regions(self, rects: Sequence[Rect]) -> List[np.ndarray]:
        """
        Chụp nhiều vùng từ CÙNG MỘT khung hình (nhất quán thời điểm, ít lần grab hơn).
        Nếu các vùng nằm quá xa nhau (hình chữ nhật bao > 2.5x tổng diện tích) thì chụp riêng lẻ.
        """
        rects = [(int(a), int(b), int(c), int(d)) for a, b, c, d in rects]
        if not rects:
            return []
        if len(rects) == 1:
            return [self.capture_region(*rects[0])]
        x0 = min(r[0] for r in rects)
        y0 = min(r[1] for r in rects)
        x1 = max(r[0] + r[2] for r in rects)
        y1 = max(r[1] + r[3] for r in rects)
        union_area = (x1 - x0) * (y1 - y0)
        sum_area = sum(r[2] * r[3] for r in rects)
        if union_area > 2.5 * sum_area:
            return [self.capture_region(*r) for r in rects]
        big = self.capture_region(x0, y0, x1 - x0, y1 - y0)
        return [np.ascontiguousarray(big[ry - y0: ry - y0 + rh, rx - x0: rx - x0 + rw]) for rx, ry, rw, rh in rects]

    # ── toàn màn hình chính ─────────────────────────────────────────────────
    @staticmethod
    def _primary_size() -> Tuple[int, int]:
        if sys.platform == "win32":
            try:
                import ctypes
                return int(ctypes.windll.user32.GetSystemMetrics(0)), int(ctypes.windll.user32.GetSystemMetrics(1))
            except Exception:
                pass
        if mss is not None:
            try:
                with mss.mss() as s:
                    m = s.monitors[1] if len(s.monitors) > 1 else s.monitors[0]
                    return int(m["width"]), int(m["height"])
            except Exception:
                pass
        if ImageGrab is not None:
            try:
                return ImageGrab.grab().size
            except Exception:
                pass
        return 1920, 1080

    def capture_fullscreen(self) -> np.ndarray:
        """Ảnh bằng chứng: không ném lỗi, trả ảnh đen nếu không chụp được."""
        w, h = self._primary_size()
        try:
            return self.capture_region(0, 0, w, h, allow_blank=True)
        except Exception:
            return np.zeros((h, w, 3), dtype=np.uint8)

    # ── thống kê / tiện ích ──────────────────────────────────────────────────
    def stats(self) -> Dict[str, Dict[str, float]]:
        out = {}
        with self._stat_lock:
            for name, st in self._st.items():
                n = st["ok"]
                out[name] = {
                    "ok": n,
                    "black": st["black"],
                    "last_ms": round(st["last_ms"], 2),
                    "avg_ms": round(st["total_ms"] / n, 2) if n else 0.0,
                }
        return out

    def save_image(self, img_bgr: np.ndarray, file_path: str) -> bool:
        try:
            dir_name = os.path.dirname(file_path)
            if dir_name and not os.path.exists(dir_name):
                os.makedirs(dir_name, exist_ok=True)
            if cv2 is not None:
                return bool(cv2.imwrite(file_path, img_bgr))
            return False
        except Exception as e:
            print(f"[ScreenCapture] Save error: {e}")
            return False

    def close(self):
        for be in self._chain:
            try:
                be.close()
            except Exception:
                pass


# ──────────────────────────────────────────────────────────────────────────────
# Instance dùng chung (một camera DXGI / một bộ handle cho cả GUI và engine)
# ──────────────────────────────────────────────────────────────────────────────

_shared: Optional[ScreenCapture] = None
_shared_lock = threading.Lock()


def get_shared_capture(backend: Optional[str] = None) -> ScreenCapture:
    """
    Trả ScreenCapture dùng chung toàn app. Lần gọi đầu quyết định backend ưu tiên
    (mặc định: biến môi trường SMARTAUTOCLICK_BACKEND hoặc "auto").
    """
    global _shared
    with _shared_lock:
        if _shared is None:
            _shared = ScreenCapture(backend or os.environ.get("SMARTAUTOCLICK_BACKEND", "auto"))
        return _shared


def reset_shared_capture() -> None:
    global _shared
    with _shared_lock:
        if _shared is not None:
            _shared.close()
        _shared = None
