"""
Giao diện và hợp đồng dữ liệu khung hình (Frame Contract) cho SmartAutoClick v3.1.

Theo định hướng kiến trúc Visual Automation Engine:
- Mọi backend capture cung cấp hoặc chuyển đổi dữ liệu thành Frame.
- Frame mang metadata: frame_id, monotonic timestamp, client_size, geometry_version, status, backend.
- FrameSource định nghĩa interface chuẩn start(), stop(), latest(), capture_region().
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Dict, Optional, Sequence, Tuple
import numpy as np

Rect = Tuple[int, int, int, int]  # x, y, w, h


class FrameStatus(str, Enum):
    VALID = "valid"
    EMPTY = "empty"
    SOURCE_LOST = "source_lost"
    CAPTURE_ERROR = "capture_error"
    UNRELIABLE = "unreliable"
    TIMEOUT = "timeout"


@dataclass
class Frame:
    """
    Frame Contract chuẩn v3.1:
    - image: numpy array ảnh (BGR format uint8) hoặc None nếu lỗi
    - frame_id: định danh tăng dần theo số khung thực sự tiếp nhận từ backend
    - timestamp: thời gian monotonic tại thời điểm tạo/nhận khung
    - source_timestamp: thời gian nguồn (từ OS/API capture nếu có, float)
    - window_id: handle hoặc ID của cửa sổ (HWND trên Windows)
    - client_size: kích thước client area (width, height)
    - geometry_version: tăng khi kích thước hoặc hệ tọa độ cửa sổ thay đổi
    - backend: tên backend đã tạo ra khung (wgc, dxgi, mss, pil, fake...)
    - status: trạng thái hợp lệ của khung
    - metadata: thông tin bổ sung tùy chọn (ROI offset, latency, v.v.)
    """
    image: Optional[np.ndarray]
    frame_id: int = 0
    timestamp: float = field(default_factory=time.monotonic)
    source_timestamp: Optional[float] = None
    window_id: Optional[int] = None
    client_size: Tuple[int, int] = (0, 0)
    geometry_version: int = 1
    backend: str = "unknown"
    status: FrameStatus = FrameStatus.VALID
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return self.status == FrameStatus.VALID and self.image is not None and self.image.size > 0

    @property
    def shape(self) -> Tuple[int, ...]:
        if self.image is not None:
            return self.image.shape
        return (0, 0, 0)


class FrameSource(ABC):
    """
    Giao diện trừu tượng nguồn cấp khung hình (FrameSource).
    Tất cả các adapter capture (WgcSource, ScreenCapture, FakeFrameSource)
    phải tuân theo interface này.
    """

    @abstractmethod
    def start(self) -> bool:
        """Bắt đầu nguồn capture (cấp phát tài nguyên / stream)."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Dừng nguồn capture và dọn dẹp tài nguyên."""
        pass

    @abstractmethod
    def latest(self) -> Frame:
        """
        Trả về khung hình mới nhất hiện có kèm Frame Contract.
        Nếu nguồn chưa sẵn sàng hoặc lỗi, trả Frame với status tương ứng.
        """
        pass

    def capture_region(self, x: int, y: int, w: int, h: int) -> np.ndarray:
        """
        Phương thức tương thích ngược với API v2/v3.0.
        Mặc định crop từ latest().image hoặc backend cài đặt riêng.
        """
        frame = self.latest()
        if not frame.is_valid or frame.image is None:
            raise RuntimeError(f"Không thể chụp vùng ({x}, {y}, {w}, {h}): frame không hợp lệ ({frame.status})")
        img = frame.image
        fh, fw = img.shape[:2]
        x0, y0 = max(0, int(x)), max(0, int(y))
        x1, y1 = min(fw, x0 + int(w)), min(fh, y0 + int(h))
        if x1 <= x0 or y1 <= y0:
            return np.zeros((h, w, 3), dtype=np.uint8)
        return np.ascontiguousarray(img[y0:y1, x0:x1])

    def capture_fullscreen(self) -> np.ndarray:
        """Phương thức tương thích ngược chụp toàn bộ khung."""
        frame = self.latest()
        if frame.is_valid and frame.image is not None:
            return frame.image.copy()
        return np.zeros((1080, 1920, 3), dtype=np.uint8)

    def close(self) -> None:
        self.stop()


def to_frame(
    img: Optional[np.ndarray],
    frame_id: int = 1,
    backend: str = "legacy",
    status: FrameStatus = FrameStatus.VALID,
    client_size: Optional[Tuple[int, int]] = None,
    geometry_version: int = 1,
    window_id: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Frame:
    """Helper bọc numpy ndarray thành Frame Contract."""
    if img is None or img.size == 0:
        actual_status = FrameStatus.EMPTY if status == FrameStatus.VALID else status
        return Frame(
            image=None,
            frame_id=frame_id,
            backend=backend,
            status=actual_status,
            client_size=client_size or (0, 0),
            geometry_version=geometry_version,
            window_id=window_id,
            metadata=metadata or {},
        )
    h, w = img.shape[:2]
    c_size = client_size or (w, h)
    return Frame(
        image=img,
        frame_id=frame_id,
        backend=backend,
        status=status,
        client_size=c_size,
        geometry_version=geometry_version,
        window_id=window_id,
        metadata=metadata or {},
    )
