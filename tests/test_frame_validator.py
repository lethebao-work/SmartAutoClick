"""
Unit tests cho FrameValidator & WgcSource (Phase 1).
Kiểm thử:
- V1-T10: Kiểm tra độ mới (stale frame, frame_id timestamp).
- V1-T11: Phát hiện geometry mismatch và shape bất thường.
- V1-T12: Phát hiện ảnh đen, ảnh rỗng, capture error.
- V1-T13: Phân biệt ảnh tĩnh và capture đóng băng (frozen capture).
- V1-T14: Vô hiệu hóa cache khi geometry_version hoặc backend đổi.
- V1-T8: Cửa sổ mất / thu nhỏ báo SOURCE_LOST / UNRELIABLE.
"""
import unittest
import numpy as np
import time

from core.capture_interface import Frame, FrameStatus
from core.frame_validator import FrameValidator, ValidationIssue
from tests.test_dataset import (
    create_normal_slot_frame,
    create_black_frame,
    create_empty_frame,
    create_mismatched_size_frame,
)
from core.capture_wgc import WgcSource, WindowGeometryTracker


class TestFrameValidator(unittest.TestCase):

    def setUp(self):
        self.validator = FrameValidator(
            max_frame_age_s=0.5,
            frozen_frame_count_limit=5,
            expected_shape=(100, 100),
        )

    def test_validate_normal_frame(self):
        img = create_normal_slot_frame(shape=(100, 100))
        frame = Frame(image=img, frame_id=1, timestamp=time.monotonic(), backend="wgc")
        res = self.validator.validate(frame)
        self.assertTrue(res.is_valid)
        self.assertEqual(res.issue, ValidationIssue.OK)

    def test_validate_black_frame(self):
        black = create_black_frame(shape=(100, 100))
        frame = Frame(image=black, frame_id=2, timestamp=time.monotonic(), backend="wgc")
        res = self.validator.validate(frame)
        self.assertFalse(res.is_valid)
        self.assertEqual(res.issue, ValidationIssue.BLACK_FRAME)

    def test_validate_empty_frame(self):
        empty = create_empty_frame()
        frame = Frame(image=empty, frame_id=3, timestamp=time.monotonic(), backend="wgc")
        res = self.validator.validate(frame)
        self.assertFalse(res.is_valid)
        self.assertEqual(res.issue, ValidationIssue.EMPTY)

    def test_validate_stale_frame(self):
        img = create_normal_slot_frame()
        old_time = time.monotonic() - 2.0  # cũ 2 giây
        frame = Frame(image=img, frame_id=4, timestamp=old_time, backend="wgc")
        res = self.validator.validate(frame)
        self.assertFalse(res.is_valid)
        self.assertEqual(res.issue, ValidationIssue.STALE_FRAME)

    def test_validate_geometry_mismatch(self):
        mismatched = create_mismatched_size_frame(expected_shape=(100, 100), scale=1.5)
        frame = Frame(image=mismatched, frame_id=5, timestamp=time.monotonic(), backend="wgc")
        res = self.validator.validate(frame)
        self.assertFalse(res.is_valid)
        self.assertEqual(res.issue, ValidationIssue.GEOMETRY_MISMATCH)

    def test_validate_frozen_capture_detection(self):
        img = create_normal_slot_frame()
        # Lặp lại cùng 1 frame_id khi đang kỳ vọng chuyển động
        for i in range(4):
            f = Frame(image=img, frame_id=10, timestamp=time.monotonic(), backend="wgc")
            res = self.validator.validate(f, expect_motion=True)
            self.assertTrue(res.is_valid)

        # Lần thứ 5 đạt limit -> phát hiện đóng băng
        f_freeze = Frame(image=img, frame_id=10, timestamp=time.monotonic(), backend="wgc")
        res = self.validator.validate(f_freeze, expect_motion=True)
        self.assertFalse(res.is_valid)
        self.assertEqual(res.issue, ValidationIssue.FROZEN_CAPTURE)

    def test_cache_invalidation_on_backend_or_geometry_change(self):
        img = create_normal_slot_frame()
        f1 = Frame(image=img, frame_id=1, timestamp=time.monotonic(), backend="wgc", geometry_version=1)
        self.validator._cached_data["anchor_roi"] = (10, 10, 50, 50)
        self.validator.validate(f1)
        self.assertIn("anchor_roi", self.validator._cached_data)

        # Chuyển backend sang dxgi -> cache phải bị xóa
        f2 = Frame(image=img, frame_id=2, timestamp=time.monotonic(), backend="dxgi", geometry_version=1)
        self.validator.validate(f2)
        self.assertEqual(len(self.validator._cached_data), 0)

        # Đổi geometry_version -> cache tiếp tục bị xóa
        self.validator._cached_data["template"] = "mock_template"
        f3 = Frame(image=img, frame_id=3, timestamp=time.monotonic(), backend="dxgi", geometry_version=2)
        self.validator.validate(f3)
        self.assertEqual(len(self.validator._cached_data), 0)


class TestWgcSourceMock(unittest.TestCase):

    def test_wgc_source_instantiation_and_availability(self):
        source = WgcSource(window_hwnd=999999999)
        # Cửa sổ không tồn tại -> start phải an toàn trả False
        self.assertFalse(source.start())

        # latest() khi chưa chạy hoặc cửa sổ mất phải báo SOURCE_LOST
        f = source.latest()
        self.assertEqual(f.status, FrameStatus.SOURCE_LOST)
        self.assertFalse(f.is_valid)


if __name__ == "__main__":
    unittest.main()
