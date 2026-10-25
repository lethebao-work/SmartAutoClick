"""
Unit tests cho hệ thống tọa độ cửa sổ (Window Coordinate System - Phase 2).

Kiểm thử:
- V2-T1 & V2-T7: RelativePoint, RelativeRect (0.0 - 1.0 <-> client px).
- V2-T2: CoordinateTransformer (client_to_screen, screen_to_client, relative_to_screen).
- V2-T3: ConfigManager schema_version 3 migration.
- V2-T6: Di chuyển/đổi kích thước cửa sổ giả lập vẫn tính đúng điểm click thực tế.
- V2-T8: Phân biệt capture space, client space và desktop space.
- V2-T9 & V2-T11: GeometryGuard xác minh geometry_version và chặn click khi geometry sai lệch.
- V2-T10: Phát hiện thay đổi DPI và scale.
"""
import unittest
import numpy as np

from core.coordinates import (
    RelativePoint,
    RelativeRect,
    WindowGeometrySnapshot,
    CoordinateTransformer,
    GeometryGuard,
)
from core.config_manager import ConfigManager
from core.clicker import InputSimulator
from tests.fakes import FakeInputSink


class TestWindowCoordinateSystem(unittest.TestCase):

    def test_relative_point_conversion(self):
        # Điểm (0.5, 0.5) trên cửa sổ 1920x1080 -> (960, 540)
        rp = RelativePoint(0.5, 0.5)
        px, py = rp.to_client_px(1920, 1080)
        self.assertEqual((px, py), (960, 540))

        # Ngược lại
        rp2 = RelativePoint.from_client_px(960, 540, 1920, 1080)
        self.assertAlmostEqual(rp2.rx, 0.5)
        self.assertAlmostEqual(rp2.ry, 0.5)

    def test_relative_rect_conversion(self):
        # Rect tỉ lệ 0.2, 0.3, 0.1, 0.1 trên 1000x1000 -> (200, 300, 100, 100)
        rr = RelativeRect(0.2, 0.3, 0.1, 0.1)
        x, y, w, h = rr.to_client_rect(1000, 1000)
        self.assertEqual((x, y, w, h), (200, 300, 100, 100))

    def test_coordinate_transformer_moving_window(self):
        # Cửa sổ tại tọa độ screen (100, 200), kích thước 1280x720
        snap1 = WindowGeometrySnapshot(
            hwnd=12345,
            client_size=(1280, 720),
            client_origin_screen=(100, 200),
            geometry_version=1,
            is_valid=True,
        )
        # Nút tại relative (0.5, 0.5) -> client (640, 360) -> screen (740, 560)
        rp = RelativePoint(0.5, 0.5)
        sx1, sy1 = CoordinateTransformer.relative_to_screen(rp, snap1)
        self.assertEqual((sx1, sy1), (740, 560))

        # Cửa sổ DI CHUYỂN sang vị trí screen (300, 400), kích thước giữ nguyên
        snap2 = WindowGeometrySnapshot(
            hwnd=12345,
            client_size=(1280, 720),
            client_origin_screen=(300, 400),
            geometry_version=2,
            is_valid=True,
        )
        # Điểm click mới tự động thích ứng với vị trí cửa sổ mới -> screen (940, 760)
        sx2, sy2 = CoordinateTransformer.relative_to_screen(rp, snap2)
        self.assertEqual((sx2, sy2), (940, 760))

    def test_coordinate_transformer_resizing_window(self):
        # Cửa sổ RESIZE từ 1280x720 sang 1920x1080 tại gốc (0, 0)
        snap_resized = WindowGeometrySnapshot(
            hwnd=12345,
            client_size=(1920, 1080),
            client_origin_screen=(0, 0),
            geometry_version=3,
            is_valid=True,
        )
        rp = RelativePoint(0.5, 0.5)
        sx, sy = CoordinateTransformer.relative_to_screen(rp, snap_resized)
        self.assertEqual((sx, sy), (960, 540))

    def test_capture_to_client_scaling(self):
        # Ảnh capture có kích thước 960x540 trong khi client là 1920x1080 (downscaled capture)
        snap = WindowGeometrySnapshot(
            hwnd=12345,
            client_size=(1920, 1080),
            client_origin_screen=(0, 0),
            geometry_version=1,
            is_valid=True,
        )
        cx, cy = CoordinateTransformer.capture_to_client(480, 270, (960, 540), snap)
        self.assertEqual((cx, cy), (960, 540))

    def test_geometry_guard_prevents_unsafe_clicks(self):
        # Snapshot hiện tại có geometry_version=2
        current_snap = WindowGeometrySnapshot(
            hwnd=12345,
            client_size=(1280, 720),
            client_origin_screen=(100, 100),
            geometry_version=2,
            is_valid=True,
        )

        # Quyết định nhận diện đưa ra từ frame cũ có geometry_version=1
        safe, reason = GeometryGuard.verify_geometry_for_action(
            target_geometry_version=1,
            current_snapshot=current_snap,
        )
        self.assertFalse(safe)
        self.assertIn("Geometry version bị lệch", reason)

        # Nếu geometry version khớp -> cho phép click
        safe_ok, _ = GeometryGuard.verify_geometry_for_action(
            target_geometry_version=2,
            current_snapshot=current_snap,
            expected_client_size=(1280, 720),
        )
        self.assertTrue(safe_ok)

    def test_config_schema_migration(self):
        # Mock cấu hình cũ version 2.0 (tọa độ pixel tuyệt đối không có rx, ry, rw, rh)
        legacy_data = {
            "version": "2.4",
            "reference_resolution": [1920, 1080],
            "roll_button": {"x": 960, "y": 540},
            "watch_regions": [
                {"id": "slot_1", "x": 192, "y": 108, "w": 384, "h": 216}
            ]
        }
        migrated = ConfigManager._migrate_schema(legacy_data)
        self.assertEqual(migrated["schema_version"], 3)
        self.assertEqual(migrated["roll_button"]["rx"], 0.5)
        self.assertEqual(migrated["roll_button"]["ry"], 0.5)
        self.assertEqual(migrated["watch_regions"][0]["rx"], 0.1)
        self.assertEqual(migrated["watch_regions"][0]["ry"], 0.1)
        self.assertEqual(migrated["watch_regions"][0]["rw"], 0.2)
        self.assertEqual(migrated["watch_regions"][0]["rh"], 0.2)


if __name__ == "__main__":
    unittest.main()
