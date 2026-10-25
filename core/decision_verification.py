"""
Xác minh hành động và kiểm chứng theo thời gian (Action Verification & Temporal Confirmation)
cho SmartAutoClick v3.1 (Phase 4).

Nhiệm vụ:
- Action Verification (V4-T15 đến V4-T19):
    * Gắn action_id riêng cho mỗi lần gửi thao tác.
    * Lưu giữ Observation trước khi thực hiện hành động.
    * Sau khi gửi hành động, chờ và xác minh bằng chứng phản hồi thực tế từ game.
    * Phân biệt rõ giữa "gửi input thành công" và "game thực sự tiếp nhận hành động".
    * Chặn lặp lại hành động khi chưa xác định kết quả lần trước.
- Temporal Confirmation (V4-T9 đến V4-T13):
    * Xác nhận kết quả qua nhiều frame MỚI hợp lệ (dựa trên frame_id và timestamp).
    * Không đếm lại một frame cũ nhiều lần.
    * Đạt ngưỡng tin cậy (confidence) và số lần xác nhận nhất quán trước khi chốt quyết định.
    * Phát hiện mâu thuẫn giữa các frame liên tiếp (ví dụ hiệu ứng chớp sáng).
"""
import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from core.capture_interface import Frame
from core.observation import Observation, ObservationStatus
from core.frame_sync import change_percent


class ActionRecord:
    """Bản ghi chi tiết một hành động được gửi đi."""
    def __init__(
        self,
        action_id: str,
        action_type: str,
        params: Dict[str, Any],
        pre_observation: Optional[Observation] = None,
        sent_timestamp: float = 0.0,
    ):
        self.action_id = action_id
        self.action_type = action_type
        self.params = params
        self.pre_observation = pre_observation
        self.sent_timestamp = sent_timestamp or time.monotonic()
        self.verified: bool = False
        self.verification_reason: str = ""
        self.response_timestamp: Optional[float] = None


class ActionVerifier:
    """
    Quản lý và kiểm chứng kết quả thực tế của hành động (Action Verification).
    """

    def __init__(self, response_timeout_s: float = 2.0, min_change_pct: float = 0.5):
        self.response_timeout_s = response_timeout_s
        self.min_change_pct = min_change_pct
        self._action_counter: int = 0
        self._active_action: Optional[ActionRecord] = None
        self._history: List[ActionRecord] = []

    def register_action(
        self,
        action_type: str,
        params: Dict[str, Any],
        pre_obs: Optional[Observation] = None,
    ) -> ActionRecord:
        """
        V4-T15 & V4-T16: Ghi nhận Observation trước hành động và cấp action_id duy nhất.
        """
        self._action_counter += 1
        aid = f"act_{self._action_counter}_{int(time.monotonic() * 1000)}"
        rec = ActionRecord(
            action_id=aid,
            action_type=action_type,
            params=params,
            pre_observation=pre_obs,
            sent_timestamp=time.monotonic(),
        )
        self._active_action = rec
        self._history.append(rec)
        if len(self._history) > 50:
            self._history.pop(0)
        return rec

    def can_dispatch_new_action(self) -> Tuple[bool, str]:
        """
        V4-T19: Không lặp lại action mới khi chưa xác định hoặc timeout kết quả lần trước.
        """
        if self._active_action is None:
            return True, "Ready"
        if self._active_action.verified:
            return True, "Previous action verified"
        elapsed = time.monotonic() - self._active_action.sent_timestamp
        if elapsed > self.response_timeout_s:
            return True, f"Previous action timed out after {elapsed:.2f}s"
        return False, f"Action {self._active_action.action_id} vẫn đang chờ phản hồi từ game"

    def verify_response(
        self,
        pre_frame_img: Optional[np.ndarray],
        current_frame: Frame,
        roi: Optional[Tuple[int, int, int, int]] = None,
    ) -> Tuple[bool, str]:
        """
        V4-T17 & V4-T18: Kiểm tra bằng chứng game đã phản hồi bằng sự thay đổi pixel thực tế.
        """
        if self._active_action is None:
            return False, "Không có active action để verify"

        if current_frame.image is None or pre_frame_img is None:
            return False, "Thiếu ảnh để so sánh phản hồi"

        # Cắt ROI nếu có
        if roi:
            rx, ry, rw, rh = roi
            img1 = pre_frame_img[ry:ry + rh, rx:rx + rw]
            img2 = current_frame.image[ry:ry + rh, rx:rx + rw]
        else:
            img1 = pre_frame_img
            img2 = current_frame.image

        diff_pct = change_percent(img1, img2)
        if diff_pct >= self.min_change_pct:
            self._active_action.verified = True
            self._active_action.response_timestamp = time.monotonic()
            self._active_action.verification_reason = f"Game phản hồi với chênh lệch {diff_pct:.2f}% pixel"
            return True, self._active_action.verification_reason

        elapsed = time.monotonic() - self._active_action.sent_timestamp
        if elapsed >= self.response_timeout_s:
            self._active_action.verified = False
            self._active_action.verification_reason = f"Timeout ({elapsed:.2f}s) không thấy game đổi ảnh"
            return False, self._active_action.verification_reason

        return False, "Đang chờ game hiển thị thay đổi"


class TemporalConfirmationEngine:
    """
    Xác nhận kết quả qua nhiều frame MỚI hợp lệ (Temporal Confirmation - V4-T9 đến V4-T13).
    """

    def __init__(
        self,
        required_confirm_frames: int = 2,
        min_confidence: float = 0.70,
        max_conflict_tolerance: int = 0,
    ):
        self.required_confirm_frames = max(1, required_confirm_frames)
        self.min_confidence = min_confidence
        self.max_conflict_tolerance = max_conflict_tolerance

        self._observations: List[Observation] = []
        self._seen_frame_ids: set = set()

    def reset(self) -> None:
        self._observations.clear()
        self._seen_frame_ids.clear()

    def add_observation(self, obs: Observation) -> Tuple[bool, Optional[str]]:
        """
        Thêm observation từ frame mới.
        Trả về (confirmed, primary_label).
        - confirmed = True khi đạt đủ số frame đồng thuận không mâu thuẫn.
        - confirmed = False khi chưa đủ bằng chứng hoặc có mâu thuẫn (tiếp tục quan sát).
        """
        # V4-T10: Khung hình phải mới, không đếm lại frame_id cũ
        if obs.frame_id in self._seen_frame_ids and obs.frame_id != 0:
            return False, None

        self._seen_frame_ids.add(obs.frame_id)
        self._observations.append(obs)

        if len(self._observations) < self.required_confirm_frames:
            # V4-T13: Chưa đủ số lần xác nhận -> tiếp tục quan sát
            return False, None

        # Chỉ xét N observation mới nhất
        recent = self._observations[-self.required_confirm_frames:]

        # Trích xuất nhãn đối tượng chính từ mỗi observation
        labels = []
        for o in recent:
            if not o.is_reliable or o.confidence < self.min_confidence:
                # Frame có độ tin cậy thấp hoặc không hợp lệ -> loại
                return False, None
            primary_obj = o.detected_objects[0] if o.detected_objects else None
            if primary_obj is None:
                return False, None
            labels.append(primary_obj.label)

        # V4-T12: Xử lý mâu thuẫn giữa các frame liên tiếp
        first_label = labels[0]
        is_consistent = all(l == first_label for l in labels)

        if is_consistent:
            return True, first_label
        else:
            # Có mâu thuẫn (nhấp nháy / animation chưa dứt) -> chưa chốt
            return False, None
