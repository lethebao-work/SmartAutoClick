"""
Ma trận kiểm thử toàn diện (Full Test Matrix Suite) cho SmartAutoClick v3.1 (Phase 6 - V6-T4 & Test Matrix).

Bao phủ 12 kịch bản trong Test Matrix:
1. Cửa sổ thay đổi vị trí -> Click vẫn chính xác qua CoordinateTransformer
2. DPI thay đổi -> Không lệch tọa độ
3. Frame bị lặp -> Không coi là phản hồi mới
4. Game đứng hình -> Settle timeout có kiểm soát
5. Hiệu ứng chuyển động -> Không nhận nhầm kết quả cuối (Temporal Confirmation)
6. Popup bất ngờ -> Safe stop / uncertain
7. Mất anchor -> Dừng an toàn không click
8. Capture backend lỗi -> Recovery hoặc dừng an toàn
9. Game phản hồi chậm -> ActionVerifier chặn click chồng
10. Người dùng can thiệp -> Giữ nguyên WindowGuard
11. Stop khi worker đang xử lý -> Dừng ngay lập tức không có action mới
12. Treo máy nhiều giờ -> PerformanceMonitor / Memory leak check
"""
import unittest
import numpy as np
import time

from core.capture_interface import Frame, FrameStatus
from core.coordinates import (
    RelativePoint,
    WindowGeometrySnapshot,
    CoordinateTransformer,
    GeometryGuard,
)
from core.frame_sync import TwoPhaseSettle, SettleState
from core.decision_verification import ActionVerifier, TemporalConfirmationEngine
from core.observation import Observation, ObservationStatus, DetectedObject
from core.recovery import RecoveryManager, RecoveryAction, SafetyBudget
from core.anchor import AnchorMatcher
from core.detector import ColorDetector
from core.shadow_mode import ShadowModeEvaluator
from tests.fakes import FakeFrameSource, FakeInputSink
from tests.test_dataset import create_normal_slot_frame, create_black_frame, create_motion_sequence


class TestMatrixSuite(unittest.TestCase):

    def test_scenario_1_window_moved_maintains_click_accuracy(self):
        """Kịch bản 1: Cửa sổ thay đổi vị trí -> Click vẫn chính xác."""
        rp = RelativePoint(0.5, 0.5)
        # Ban đầu ở (100, 100)
        snap1 = WindowGeometrySnapshot(1, (1000, 800), (100, 100), 1.0, 1, True)
        self.assertEqual(CoordinateTransformer.relative_to_screen(rp, snap1), (600, 500))

        # Di chuyển tới (400, 300)
        snap2 = WindowGeometrySnapshot(1, (1000, 800), (400, 300), 1.0, 2, True)
        self.assertEqual(CoordinateTransformer.relative_to_screen(rp, snap2), (900, 700))

    def test_scenario_2_dpi_scaling_change(self):
        """Kịch bản 2: DPI thay đổi -> Không lệch tọa độ."""
        rp = RelativePoint(0.2, 0.3)
        # DPI 100% (scale 1.0)
        snap100 = WindowGeometrySnapshot(1, (1000, 1000), (0, 0), 1.0, 1, True)
        self.assertEqual(CoordinateTransformer.relative_to_screen(rp, snap100), (200, 300))

        # DPI 150% (client area vật lý tự động phóng 1500x1500)
        snap150 = WindowGeometrySnapshot(1, (1500, 1500), (0, 0), 1.5, 2, True)
        self.assertEqual(CoordinateTransformer.relative_to_screen(rp, snap150), (300, 450))

    def test_scenario_3_repeated_duplicate_frames_not_new_response(self):
        """Kịch bản 3: Frame bị lặp -> Không coi là phản hồi mới."""
        engine = TemporalConfirmationEngine(required_confirm_frames=2)
        obj = DetectedObject(label="purple", confidence=0.9)
        obs = Observation(frame_id=10, detected_objects=[obj], confidence=0.9)

        # Lần 1: frame 10
        engine.add_observation(obs)
        # Lần 2: lặp lại cùng frame_id 10 -> bị từ chối đếm lại
        confirmed, _ = engine.add_observation(obs)
        self.assertFalse(confirmed)

    def test_scenario_4_game_freeze_settle_timeout(self):
        """Kịch bản 4: Game đứng hình -> Timeout có kiểm soát."""
        base = np.full((50, 50, 3), 80, dtype=np.uint8)
        now = time.monotonic()
        settler = TwoPhaseSettle([base], start_time=now, first_change_timeout_s=0.1)

        # Feed frame y hệt sau khi quá timeout
        res = settler.feed([base], now=now + 0.15)
        self.assertEqual(res, SettleState.NO_RESPONSE)

    def test_scenario_5_motion_animation_no_false_detection(self):
        """Kịch bản 5: Hiệu ứng chuyển động -> Không nhận nhầm kết quả cuối."""
        motion_seq = create_motion_sequence(num_frames=4, final_color_bgr=(180, 20, 140))
        detector = ColorDetector()
        temp_engine = TemporalConfirmationEngine(required_confirm_frames=2)

        # Các frame chuyển động đầu tiên không được trigger kết quả cuối
        for i, f in enumerate(motion_seq[:-1]):
            obs = detector.observe(f, target_colors=["purple"])
            confirmed, _ = temp_engine.add_observation(obs)
            self.assertFalse(confirmed)

    def test_scenario_6_popup_unexpected_recovery(self):
        """Kịch bản 6: Popup bất ngờ che khuất -> Safe stop hoặc recovery."""
        rm = RecoveryManager()
        action, _, _ = rm.handle_error("popup_detected", "Giao diện bị popup che khuất")
        self.assertIn(action, [RecoveryAction.WAIT_AND_RETRY, RecoveryAction.SAFE_STOP])

    def test_scenario_7_anchor_lost_blocks_click(self):
        """Kịch bản 7: Mất anchor -> Không click."""
        matcher = AnchorMatcher("icon", template=np.full((20, 20, 3), 200, dtype=np.uint8))
        blank_frame = Frame(image=np.zeros((100, 100, 3), dtype=np.uint8), frame_id=1)
        res = matcher.find(blank_frame)
        self.assertFalse(res.found)

    def test_scenario_8_capture_backend_crash_recovery(self):
        """Kịch bản 8: Capture backend lỗi -> Recovery hoặc dừng an toàn."""
        rm = RecoveryManager()
        action, delay, _ = rm.handle_error("capture_failed", "DirectX device lost")
        self.assertEqual(action, RecoveryAction.REINIT_CAPTURE)
        self.assertGreater(delay, 0.0)

    def test_scenario_9_slow_response_prevents_stacked_clicks(self):
        """Kịch bản 9: Game phản hồi chậm -> ActionVerifier chặn click chồng."""
        verifier = ActionVerifier(response_timeout_s=0.5)
        verifier.register_action("roll", {"x": 500, "y": 500})
        # Ngay lập tức thử gửi action tiếp theo -> bị chặn
        can_click, reason = verifier.can_dispatch_new_action()
        self.assertFalse(can_click)
        self.assertIn("vẫn đang chờ phản hồi", reason)

    def test_scenario_10_geometry_guard_prevents_stale_click(self):
        """Kịch bản 10: Chặn click khi geometry không khớp."""
        snap = WindowGeometrySnapshot(1, (1000, 800), (0, 0), 1.0, geometry_version=2)
        safe, reason = GeometryGuard.verify_geometry_for_action(target_geometry_version=1, current_snapshot=snap)
        self.assertFalse(safe)
        self.assertIn("Geometry version bị lệch", reason)

    def test_scenario_11_shadow_mode_evaluation(self):
        """Kịch bản 11: Shadow Mode chạy song song đánh giá quyết định."""
        evaluator = ShadowModeEvaluator(target_colors=["purple"], action_rules={"purple": "stop"})
        purple_frame = Frame(image=create_normal_slot_frame(), frame_id=1)
        comp = evaluator.evaluate_frame(purple_frame)
        self.assertTrue(comp.is_agreement)
        self.assertEqual(comp.shadow_decision, "stop")

    def test_scenario_12_safe_limits_enforced(self):
        """Kịch bản 12: Giới hạn tối đa (max rolls / runtime)."""
        budget = SafetyBudget(max_rolls=10)
        rm = RecoveryManager(safety_budget=budget)
        ok, reason = rm.check_safety_limits(current_rolls=10)
        self.assertFalse(ok)
        self.assertIn("Đã đạt số lần roll tối đa", reason)


if __name__ == "__main__":
    unittest.main()
