"""
Unit tests cho Phase 4: Event-driven Decision Engine.
Kiểm thử:
- V4-T1: VisualStateMachine chuyển đổi trạng thái hợp lệ và từ chối chuyển đổi sai.
- V4-T14: Timeout kiểm tra theo từng trạng thái FSM.
- V4-T15 & V4-T16: ActionVerifier đăng ký action kèm pre-observation và ID duy nhất.
- V4-T17 & V4-T18: verify_response phân biệt input gửi đi và game phản hồi thực sự (pixel change).
- V4-T19: can_dispatch_new_action ngăn chặn click đè khi action cũ chưa xác minh.
- V4-T9 đến V4-T13: TemporalConfirmationEngine xác nhận qua frame mới, lọc mâu thuẫn, chống đếm lại frame cũ.
"""
import unittest
import numpy as np
import time

from core.decision_fsm import (
    VisualStateMachine,
    FSMState,
    InvalidStateTransitionError,
)
from core.decision_verification import (
    ActionVerifier,
    ActionRecord,
    TemporalConfirmationEngine,
)
from core.observation import Observation, ObservationStatus, DetectedObject
from core.capture_interface import Frame, FrameStatus
from tests.test_dataset import create_normal_slot_frame


class TestDecisionEngine(unittest.TestCase):

    def test_fsm_valid_transitions(self):
        fsm = VisualStateMachine(initial_state=FSMState.READY)
        self.assertEqual(fsm.current_state, FSMState.READY)

        # READY -> PRECHECK -> ACTION_SENT -> WAIT_RESPONSE -> WAIT_SETTLE -> OBSERVE -> CONFIRM -> DECIDE -> READY
        fsm.transition_to(FSMState.PRECHECK, "Window & budget check")
        self.assertEqual(fsm.current_state, FSMState.PRECHECK)

        fsm.transition_to(FSMState.ACTION_SENT, "Click roll sent")
        self.assertEqual(fsm.current_state, FSMState.ACTION_SENT)

        fsm.transition_to(FSMState.WAIT_RESPONSE, "Awaiting screen diff")
        self.assertEqual(fsm.current_state, FSMState.WAIT_RESPONSE)

        fsm.transition_to(FSMState.WAIT_SETTLE, "Animation running")
        self.assertEqual(fsm.current_state, FSMState.WAIT_SETTLE)

        fsm.transition_to(FSMState.OBSERVE, "Screen settled")
        self.assertEqual(fsm.current_state, FSMState.OBSERVE)

        fsm.transition_to(FSMState.CONFIRM, "Candidate color found")
        self.assertEqual(fsm.current_state, FSMState.CONFIRM)

        fsm.transition_to(FSMState.DECIDE, "Consistent frames verified")
        self.assertEqual(fsm.current_state, FSMState.DECIDE)

        fsm.transition_to(FSMState.READY, "Cycle finished, continue")
        self.assertEqual(fsm.current_state, FSMState.READY)

    def test_fsm_invalid_transition_rejected(self):
        fsm = VisualStateMachine(initial_state=FSMState.READY)
        # Không được nhảy cóc từ READY thẳng sang CONFIRM
        with self.assertRaises(InvalidStateTransitionError):
            fsm.transition_to(FSMState.CONFIRM, "Invalid jump")

    def test_fsm_emergency_stop_anywhere(self):
        fsm = VisualStateMachine(initial_state=FSMState.READY)
        fsm.transition_to(FSMState.PRECHECK)
        fsm.transition_to(FSMState.ACTION_SENT)
        # Emergency stop từ bất kỳ đâu
        fsm.transition_to(FSMState.STOPPED, "User abort")
        self.assertEqual(fsm.current_state, FSMState.STOPPED)

    def test_fsm_state_timeout(self):
        fsm = VisualStateMachine(
            initial_state=FSMState.ACTION_SENT,
            state_timeouts={FSMState.ACTION_SENT: 0.1},
        )
        self.assertFalse(fsm.check_timeout())
        time.sleep(0.15)
        self.assertTrue(fsm.check_timeout())

    def test_action_verifier_lifecycle(self):
        verifier = ActionVerifier(response_timeout_s=0.3, min_change_pct=1.0)

        # 1. Ban đầu sẵn sàng dispatch
        can_act, _ = verifier.can_dispatch_new_action()
        self.assertTrue(can_act)

        # 2. Đăng ký action (click roll)
        rec = verifier.register_action("click_roll", {"x": 500, "y": 500})
        self.assertFalse(rec.verified)

        # Ngay sau đó: chưa verify -> chặn action tiếp theo (V4-T19)
        can_act2, reason = verifier.can_dispatch_new_action()
        self.assertFalse(can_act2)
        self.assertIn("vẫn đang chờ phản hồi", reason)

        # 3. Game phản hồi (pixel thay đổi)
        f_before = np.full((100, 100, 3), 50, dtype=np.uint8)
        f_after = np.full((100, 100, 3), 150, dtype=np.uint8)
        frame_after = Frame(image=f_after, frame_id=2)

        verified, vreason = verifier.verify_response(f_before, frame_after)
        self.assertTrue(verified)
        self.assertTrue(rec.verified)
        self.assertIn("Game phản hồi", vreason)

        # Đã verify -> cho phép dispatch action tiếp theo
        can_act3, _ = verifier.can_dispatch_new_action()
        self.assertTrue(can_act3)

    def test_temporal_confirmation_engine(self):
        engine = TemporalConfirmationEngine(required_confirm_frames=3, min_confidence=0.7)

        # Frame 1: Tím
        obj_p = DetectedObject(label="purple", confidence=0.85, coverage_percent=30.0)
        obs1 = Observation(frame_id=1, detected_objects=[obj_p], confidence=0.85, status=ObservationStatus.VALID)
        confirmed, _ = engine.add_observation(obs1)
        self.assertFalse(confirmed)  # 1/3 -> chưa xác nhận

        # Đếm lại cùng frame_id=1 -> phải bị bỏ qua (V4-T10)
        confirmed_dup, _ = engine.add_observation(obs1)
        self.assertFalse(confirmed_dup)

        # Frame 2: Tím
        obs2 = Observation(frame_id=2, detected_objects=[obj_p], confidence=0.90, status=ObservationStatus.VALID)
        confirmed2, _ = engine.add_observation(obs2)
        self.assertFalse(confirmed2)  # 2/3 -> chưa xác nhận

        # Frame 3: Tím -> đủ 3 frame đồng thuận
        obs3 = Observation(frame_id=3, detected_objects=[obj_p], confidence=0.88, status=ObservationStatus.VALID)
        confirmed3, label = engine.add_observation(obs3)
        self.assertTrue(confirmed3)
        self.assertEqual(label, "purple")

    def test_temporal_confirmation_rejects_conflicting_frames(self):
        engine = TemporalConfirmationEngine(required_confirm_frames=2, min_confidence=0.7)

        # Frame 1: Tím
        obj_p = DetectedObject(label="purple", confidence=0.85)
        obs1 = Observation(frame_id=1, detected_objects=[obj_p], confidence=0.85)
        engine.add_observation(obs1)

        # Frame 2: Mâu thuẫn (nhãn đỏ do hiệu ứng lóe sáng)
        obj_r = DetectedObject(label="red", confidence=0.85)
        obs2 = Observation(frame_id=2, detected_objects=[obj_r], confidence=0.85)
        confirmed, _ = engine.add_observation(obs2)

        # Có mâu thuẫn -> không được xác nhận (V4-T12)
        self.assertFalse(confirmed)


if __name__ == "__main__":
    unittest.main()
