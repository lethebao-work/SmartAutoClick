"""
Bộ kiểm tra tính hợp lệ của khung hình (Frame Validator) cho SmartAutoClick v3.1.

Nhiệm vụ (Phase 1):
- V1-T10: Kiểm tra độ mới của khung theo timestamp và frame_id (không đếm lại khung cũ/stale).
- V1-T11: Phát hiện kích thước ảnh hoặc geometry bất thường (so với client_size hoặc expected_shape).
- V1-T12: Phát hiện ảnh đen, ảnh rỗng, capture lỗi.
- V1-T13: Phân biệt ảnh tĩnh hợp lệ và capture có dấu hiệu đóng băng (frozen capture).
- V1-T14: Vô hiệu hóa cache khi geometry_version thay đổi hoặc khi backend thay đổi.
"""
import time
from typing import Any, Dict, Optional, Tuple
import numpy as np

from core.capture_interface import Frame, FrameStatus


class ValidationIssue:
    OK = "ok"
    EMPTY = "empty"
    BLACK_FRAME = "black_frame"
    STALE_FRAME = "stale_frame"
    FROZEN_CAPTURE = "frozen_capture"
    GEOMETRY_MISMATCH = "geometry_mismatch"
    BACKEND_ERROR = "backend_error"
    INVALID_SHAPE = "invalid_shape"


class ValidationResult:
    def __init__(
        self,
        is_valid: bool,
        issue: str = ValidationIssue.OK,
        details: str = "",
        frame_id: int = 0,
        timestamp: float = 0.0,
    ):
        self.is_valid = is_valid
        self.issue = issue
        self.details = details
        self.frame_id = frame_id
        self.timestamp = timestamp

    def __repr__(self) -> str:
        return f"<ValidationResult valid={self.is_valid} issue='{self.issue}' details='{self.details}'>"


class FrameValidator:
    """
    Validator độc lập, xác thực từng Frame trước khi chuyển giao cho Visual/Decision Engine.
    """

    def __init__(
        self,
        max_frame_age_s: float = 1.0,
        black_pixel_std_max: float = 1.0,
        black_pixel_mean_max: float = 2.0,
        frozen_frame_count_limit: int = 30,
        expected_shape: Optional[Tuple[int, int]] = None,
    ):
        """
        :param max_frame_age_s: Khung hình cũ hơn thời gian này bị coi là stale.
        :param black_pixel_std_max: Ngưỡng độ lệch chuẩn để xác định ảnh đen tuyệt đối.
        :param black_pixel_mean_max: Ngưỡng giá trị trung bình để xác định ảnh đen.
        :param frozen_frame_count_limit: Số lần liên tiếp nhận cùng frame_id/ảnh khi đang kỳ vọng có thay đổi.
        :param expected_shape: Kích thước kỳ vọng (height, width), nếu có.
        """
        self.max_frame_age_s = max_frame_age_s
        self.black_pixel_std_max = black_pixel_std_max
        self.black_pixel_mean_max = black_pixel_mean_max
        self.frozen_frame_count_limit = frozen_frame_count_limit
        self.expected_shape = expected_shape

        self._last_frame_id: Optional[int] = None
        self._last_timestamp: float = 0.0
        self._last_backend: Optional[str] = None
        self._last_geometry_version: int = 1
        self._identical_frame_count: int = 0
        self._cached_data: Dict[str, Any] = {}

    def reset(self) -> None:
        """Đặt lại trạng thái validator và xóa toàn bộ cache."""
        self._last_frame_id = None
        self._last_timestamp = 0.0
        self._last_backend = None
        self._last_geometry_version = 1
        self._identical_frame_count = 0
        self._cached_data.clear()

    def invalidate_cache_if_needed(self, frame: Frame) -> bool:
        """
        V1-T14: Vô hiệu hóa cache ảnh, neo, geometry cũ khi backend hoặc geometry_version đổi.
        Trả về True nếu cache vừa bị xóa.
        """
        invalidated = False
        if self._last_backend is not None and frame.backend != self._last_backend:
            self._cached_data.clear()
            invalidated = True

        if frame.geometry_version != self._last_geometry_version:
            self._cached_data.clear()
            invalidated = True

        self._last_backend = frame.backend
        self._last_geometry_version = frame.geometry_version
        return invalidated

    def validate(self, frame: Frame, expect_motion: bool = False, now: Optional[float] = None) -> ValidationResult:
        """
        Kiểm tra toàn diện tính hợp lệ của Frame.
        :param frame: Frame cần kiểm tra.
        :param expect_motion: Nếu True, việc nhận cùng 1 frame_id hoặc frame không đổi nhiều lần sẽ cảnh báo frozen.
        :param now: Mốc thời gian hiện tại (mặc định time.monotonic()).
        """
        t_now = time.monotonic() if now is None else now

        # 1. Kiểm tra status cơ bản từ backend (V1-T12)
        if frame.status == FrameStatus.SOURCE_LOST:
            return ValidationResult(False, ValidationIssue.BACKEND_ERROR, "Nguồn capture bị mất hoặc cửa sổ đã đóng", frame.frame_id, frame.timestamp)

        if frame.status == FrameStatus.CAPTURE_ERROR:
            err = frame.metadata.get("error", "Lỗi capture từ backend")
            return ValidationResult(False, ValidationIssue.BACKEND_ERROR, str(err), frame.frame_id, frame.timestamp)

        if frame.image is None or frame.image.size == 0:
            return ValidationResult(False, ValidationIssue.EMPTY, "Ảnh rỗng hoặc None", frame.frame_id, frame.timestamp)

        # 2. Kiểm tra độ mới (Freshness) - V1-T10
        age = t_now - frame.timestamp
        if age > self.max_frame_age_s:
            return ValidationResult(
                False,
                ValidationIssue.STALE_FRAME,
                f"Khung hình quá cũ ({age:.3f}s > {self.max_frame_age_s}s)",
                frame.frame_id,
                frame.timestamp,
            )

        # Kiểm tra lặp frame_id khi đang kỳ vọng khung mới
        if self._last_frame_id is not None and frame.frame_id == self._last_frame_id and expect_motion:
            self._identical_frame_count += 1
            if self._identical_frame_count >= (self.frozen_frame_count_limit - 1):
                return ValidationResult(
                    False,
                    ValidationIssue.FROZEN_CAPTURE,
                    f"Frame id {frame.frame_id} lặp lại liên tiếp {self._identical_frame_count + 1} lần trong trạng thái kỳ vọng chuyển động",
                    frame.frame_id,
                    frame.timestamp,
                )
        else:
            self._identical_frame_count = 0

        self._last_frame_id = frame.frame_id
        self._last_timestamp = frame.timestamp

        # 3. Kiểm tra Geometry & Kích thước bất thường - V1-T11
        h, w = frame.image.shape[:2]
        if h <= 0 or w <= 0:
            return ValidationResult(False, ValidationIssue.INVALID_SHAPE, f"Kích thước ảnh không hợp lệ: {w}x{h}", frame.frame_id, frame.timestamp)

        if self.expected_shape is not None:
            exp_h, exp_w = self.expected_shape
            if (h, w) != (exp_h, exp_w):
                return ValidationResult(
                    False,
                    ValidationIssue.GEOMETRY_MISMATCH,
                    f"Kích thước ảnh {w}x{h} không khớp kỳ vọng {exp_w}x{exp_h}",
                    frame.frame_id,
                    frame.timestamp,
                )

        # 4. Phát hiện ảnh đen / rỗng (Black Frame) - V1-T12
        mean_val = float(frame.image.mean())
        if mean_val <= self.black_pixel_mean_max:
            std_val = float(frame.image.std())
            if std_val <= self.black_pixel_std_max:
                return ValidationResult(
                    False,
                    ValidationIssue.BLACK_FRAME,
                    f"Phát hiện ảnh đen (mean={mean_val:.2f}, std={std_val:.2f})",
                    frame.frame_id,
                    frame.timestamp,
                )

        # 5. Cập nhật cache invalidated nếu cần - V1-T14
        self.invalidate_cache_if_needed(frame)

        return ValidationResult(True, ValidationIssue.OK, "Khung hình hợp lệ", frame.frame_id, frame.timestamp)
