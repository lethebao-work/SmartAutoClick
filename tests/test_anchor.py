"""
Unit tests cho Visual Recognition Engine & Observation Layer (Phase 3).

Kiểm thử:
- V3-T1: AnchorMatcher.find() trả về AnchorResult (vị trí, confidence, bounding_box).
- V3-T3: ROI Caching: lần đầu tìm toàn khung, lần sau dùng ROI Cache quanh vị trí cũ.
- V3-T4: Match score dưới ngưỡng confidence -> báo mất neo (found=False), không đoán mò.
- V3-T5: Tính vị trí slot và điểm click dựa trên offset anchor.
- V3-T8 & V3-T9: ColorDetector.observe() chuẩn hóa thành Observation dataclass.
- V3-T10: Observation liên kết đúng frame_id và geometry_version.
- V3-T11: Kèm confidence và evidence trong Observation.
- V3-T12: Đa detector (Anchor + Color) trên cùng một frame.
- V3-T13: Bộ ảnh kiểm thử có nhãn đo false positive và false negative.
"""
import unittest
import numpy as np
import time

from core.capture_interface import Frame
from core.observation import Observation, ObservationStatus, DetectedObject, AnchorResult
from core.anchor import AnchorMatcher
from core.detector import ColorDetector
from tests.test_dataset import create_normal_slot_frame, create_black_frame


class TestVisualRecognitionEngine(unittest.TestCase):

    def setUp(self):
        # Tạo ảnh giả lập giao diện có anchor tại (50, 50) và slot item tại (200, 200)
        self.canvas = np.full((600, 800, 3), 50, dtype=np.uint8)

        # Mẫu anchor (icon 40x40 có sọc đặc trưng)
        self.anchor_template = np.full((40, 40, 3), 100, dtype=np.uint8)
        self.anchor_template[10:30, 10:30] = (255, 200, 0) # Vàng cam

        # Đặt anchor vào canvas tại (50, 50)
        self.canvas[50:90, 50:90] = self.anchor_template.copy()

        # Đặt slot đồ tím tại (200, 200) kích thước 100x100
        slot_img = create_normal_slot_frame(color_bgr=(180, 20, 140), shape=(100, 100))
        self.canvas[200:300, 200:300] = slot_img

        self.matcher = AnchorMatcher(
            name="test_anchor",
            template=self.anchor_template,
            confidence_threshold=0.85,
            roi_margin=30,
        )
        self.color_detector = ColorDetector()

    def test_anchor_matcher_find_full_and_cached(self):
        # Lần 1: tìm toàn khung (cached_used = False)
        res1 = self.matcher.find(self.canvas)
        self.assertTrue(res1.found)
        self.assertEqual(res1.client_pos, (50, 50))
        self.assertGreaterEqual(res1.confidence, 0.95)
        self.assertFalse(res1.cached_used)

        # Lần 2: tìm trong ROI Cache quanh (50, 50) -> cached_used = True
        res2 = self.matcher.find(self.canvas)
        self.assertTrue(res2.found)
        self.assertEqual(res2.client_pos, (50, 50))
        self.assertTrue(res2.cached_used)

    def test_anchor_lost_when_covered_or_absent(self):
        # Canvas bị che mất anchor
        blank_canvas = np.full((600, 800, 3), 30, dtype=np.uint8)
        res = self.matcher.find(blank_canvas)
        self.assertFalse(res.found)
        self.assertEqual(res.client_pos, (0, 0))

    def test_anchor_offset_calculation(self):
        # Vị trí anchor (50, 50)
        res = self.matcher.find(self.canvas)
        self.assertTrue(res.found)

        # Slot ở (200, 200) -> offset_x = 150, offset_y = 150
        slot_rect = self.matcher.calculate_offset_region(res.client_pos, 150, 150, 100, 100)
        self.assertEqual(slot_rect, (200, 200, 100, 100))

        click_target = self.matcher.calculate_offset_target(res.client_pos, 450, 450)
        self.assertEqual(click_target, (500, 500))

    def test_color_detector_observe_contract(self):
        frame = Frame(
            image=self.canvas,
            frame_id=42,
            geometry_version=2,
            timestamp=100.5,
            backend="test",
        )
        obs = self.color_detector.observe(
            frame=frame,
            target_colors=["purple"],
            region=(200, 200, 100, 100),
        )

        self.assertIsInstance(obs, Observation)
        self.assertEqual(obs.frame_id, 42)
        self.assertEqual(obs.geometry_version, 2)
        self.assertEqual(obs.status, ObservationStatus.VALID)
        self.assertTrue(obs.is_reliable)
        self.assertEqual(len(obs.detected_objects), 1)

        purple_obj = obs.get_object_by_label("purple")
        self.assertIsNotNone(purple_obj)
        self.assertGreater(purple_obj.coverage_percent, 30.0)
        self.assertIn("matched_color", obs.evidence)

    def test_multi_detector_on_same_frame(self):
        # V3-T12: Chạy song song AnchorMatcher và ColorDetector trên cùng frame
        frame = Frame(image=self.canvas, frame_id=99, geometry_version=1)

        # 1. Detector 1: Anchor
        anchor_res = self.matcher.find(frame)
        self.assertTrue(anchor_res.found)

        # 2. Detector 2: Color trên vùng tính theo offset của anchor
        slot_box = self.matcher.calculate_offset_region(anchor_res.client_pos, 150, 150, 100, 100)
        obs = self.color_detector.observe(frame, target_colors=["purple"], region=slot_box)
        obs.anchor = anchor_res

        self.assertTrue(obs.anchor.found)
        self.assertEqual(obs.status, ObservationStatus.VALID)
        self.assertEqual(obs.frame_id, 99)

    def test_labeled_dataset_false_positive_negative(self):
        # V3-T13: Đo lường False Positive và False Negative trên tập ảnh nhãn
        # Positive: Slot tím
        pos_img = create_normal_slot_frame(color_bgr=(180, 20, 140))
        # Negative: Slot đen và xám không có tím
        neg_black = create_black_frame()
        neg_gray = np.full((100, 100, 3), 70, dtype=np.uint8)

        # Test positive
        obs_pos = self.color_detector.observe(pos_img, target_colors=["purple"])
        self.assertEqual(obs_pos.status, ObservationStatus.VALID)

        # Test negative (không được báo tím)
        obs_neg1 = self.color_detector.observe(neg_black, target_colors=["purple"])
        self.assertNotEqual(obs_neg1.status, ObservationStatus.VALID)

        obs_neg2 = self.color_detector.observe(neg_gray, target_colors=["purple"])
        self.assertNotEqual(obs_neg2.status, ObservationStatus.VALID)


if __name__ == "__main__":
    unittest.main()
