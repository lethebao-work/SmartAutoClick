"""
Test dataset fixtures cho Visual Automation Engine (Phase 0 - V0-T7).
Cung cấp bộ ảnh kiểm thử mô phỏng các tình huống thực tế:
- Ảnh bình thường (normal game slot)
- Ảnh đen (black/blank capture failure)
- Ảnh cũ / lặp lại (frozen frame)
- Ảnh chuyển động (motion/animation frames)
- Ảnh sai kích thước (geometry mismatch / resized window)
- Ảnh nhiễu / sáng tối bất thường
"""
import numpy as np
from typing import Dict, List, Tuple


def create_normal_slot_frame(
    color_bgr: Tuple[int, int, int] = (180, 20, 140),
    shape: Tuple[int, int] = (100, 100),
    bg_gray: int = 60,
) -> np.ndarray:
    """Tạo frame slot bình thường với màu target ở trung tâm."""
    h, w = shape
    frame = np.full((h, w, 3), bg_gray, dtype=np.uint8)
    # Target item ở giữa chiếm ~36% diện tích
    y1, y2 = int(h * 0.2), int(h * 0.8)
    x1, x2 = int(w * 0.2), int(w * 0.8)
    frame[y1:y2, x1:x2] = color_bgr
    return frame


def create_black_frame(shape: Tuple[int, int] = (100, 100)) -> np.ndarray:
    """Tạo frame đen thuần (mất tín hiệu, capture exclusive fullscreen bị chặn)."""
    return np.zeros((shape[0], shape[1], 3), dtype=np.uint8)


def create_empty_frame() -> np.ndarray:
    """Tạo frame rỗng (kích thước 0)."""
    return np.empty((0, 0, 3), dtype=np.uint8)


def create_motion_sequence(
    num_frames: int = 5,
    final_color_bgr: Tuple[int, int, int] = (180, 20, 140),
    shape: Tuple[int, int] = (100, 100),
) -> List[np.ndarray]:
    """
    Tạo chuỗi frame mô phỏng hiệu ứng cuộn/animation:
    Các frame đầu chuyển động sáng dần/đổi màu ngẫu nhiên, frame cuối cùng ổn định.
    """
    frames = []
    h, w = shape
    for i in range(num_frames - 1):
        f = np.full((h, w, 3), 40 + i * 15, dtype=np.uint8)
        # sọc chuyển động
        offset = (i * 20) % h
        f[offset: min(h, offset + 15), :] = (200, 200, 200)
        frames.append(f)

    # Frame kết quả cuối cùng
    frames.append(create_normal_slot_frame(final_color_bgr, shape=shape))
    return frames


def create_mismatched_size_frame(
    expected_shape: Tuple[int, int] = (100, 100),
    scale: float = 1.25,
) -> np.ndarray:
    """Tạo frame kích thước lệch so với geometry kỳ vọng (do DPI / resize)."""
    h = int(expected_shape[0] * scale)
    w = int(expected_shape[1] * scale)
    return np.full((h, w, 3), 100, dtype=np.uint8)


class TestImageDataset:
    """Tập hợp bộ ảnh kiểm thử chuẩn dùng chung cho validator và detector."""

    def __init__(self):
        self.normal = create_normal_slot_frame()
        self.black = create_black_frame()
        self.empty = create_empty_frame()
        self.motion = create_motion_sequence(num_frames=6)
        self.resized = create_mismatched_size_frame()
