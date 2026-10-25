"""
Máy trạng thái hữu hạn sự kiện (Finite State Machine - FSM) cho Visual Automation Engine v3.1 (Phase 4).

Chu trình FSM theo tài liệu kiến trúc v3.1:
  READY -> PRECHECK -> ACTION_SENT -> WAIT_RESPONSE -> WAIT_SETTLE -> OBSERVE -> CONFIRM -> DECIDE
        -> READY | COMPLETED | RECOVERY | STOPPED

Nhiệm vụ:
- V4-T1: Định nghĩa các trạng thái FSMState và bảng chuyển trạng thái hợp lệ.
- V4-T14: Timeout riêng cho từng trạng thái.
- Lưu trữ lịch sử chuyển trạng thái phục vụ debug và truy nguyên log.
"""
from enum import Enum
import time
from typing import Any, Dict, List, Optional, Set, Tuple


class FSMState(str, Enum):
    READY = "ready"
    PRECHECK = "precheck"
    ACTION_SENT = "action_sent"
    WAIT_RESPONSE = "wait_response"
    WAIT_SETTLE = "wait_settle"
    OBSERVE = "observe"
    CONFIRM = "confirm"
    DECIDE = "decide"
    COMPLETED = "completed"
    RECOVERY = "recovery"
    STOPPED = "stopped"


# Bảng chuyển trạng thái hợp lệ (Valid State Transitions)
VALID_TRANSITIONS: Dict[FSMState, Set[FSMState]] = {
    FSMState.READY: {FSMState.PRECHECK, FSMState.STOPPED, FSMState.COMPLETED},
    FSMState.PRECHECK: {FSMState.ACTION_SENT, FSMState.RECOVERY, FSMState.STOPPED},
    FSMState.ACTION_SENT: {FSMState.WAIT_RESPONSE, FSMState.RECOVERY, FSMState.STOPPED},
    FSMState.WAIT_RESPONSE: {FSMState.WAIT_SETTLE, FSMState.OBSERVE, FSMState.RECOVERY, FSMState.STOPPED},
    FSMState.WAIT_SETTLE: {FSMState.OBSERVE, FSMState.RECOVERY, FSMState.STOPPED},
    FSMState.OBSERVE: {FSMState.CONFIRM, FSMState.DECIDE, FSMState.RECOVERY, FSMState.STOPPED},
    FSMState.CONFIRM: {FSMState.DECIDE, FSMState.OBSERVE, FSMState.RECOVERY, FSMState.STOPPED},
    FSMState.DECIDE: {FSMState.READY, FSMState.COMPLETED, FSMState.RECOVERY, FSMState.STOPPED},
    FSMState.RECOVERY: {FSMState.READY, FSMState.STOPPED},
    FSMState.COMPLETED: {FSMState.READY, FSMState.STOPPED},
    FSMState.STOPPED: {FSMState.READY},
}


class InvalidStateTransitionError(Exception):
    """Ném khi cố gắng chuyển FSM sang trạng thái không hợp lệ."""
    pass


class StateTimeoutError(Exception):
    """Ném khi một trạng thái bị giữ quá lâu mà không có tiến triển."""
    pass


class VisualStateMachine:
    """
    Bộ quản lý trạng thái FSM điều phối chu trình Visual Automation.
    """

    def __init__(
        self,
        initial_state: FSMState = FSMState.READY,
        state_timeouts: Optional[Dict[FSMState, float]] = None,
    ):
        self._current_state: FSMState = initial_state
        self._state_entered_time: float = time.monotonic()
        self._history: List[Tuple[float, FSMState, str]] = [(self._state_entered_time, initial_state, "init")]

        # Timeout mặc định cho từng trạng thái (V4-T14)
        self.state_timeouts: Dict[FSMState, float] = {
            FSMState.PRECHECK: 3.0,
            FSMState.ACTION_SENT: 2.0,
            FSMState.WAIT_RESPONSE: 2.5,
            FSMState.WAIT_SETTLE: 6.0,
            FSMState.OBSERVE: 2.0,
            FSMState.CONFIRM: 3.0,
            FSMState.DECIDE: 2.0,
            FSMState.RECOVERY: 10.0,
        }
        if state_timeouts:
            self.state_timeouts.update(state_timeouts)

    @property
    def current_state(self) -> FSMState:
        return self._current_state

    @property
    def time_in_current_state(self) -> float:
        return time.monotonic() - self._state_entered_time

    def transition_to(self, new_state: FSMState, reason: str = "") -> None:
        """
        Chuyển trạng thái an toàn. Kiểm tra tính hợp lệ trong bảng chuyển đổi.
        """
        allowed = VALID_TRANSITIONS.get(self._current_state, set())
        # Cho phép ép chuyển về STOPPED ở bất kỳ trạng thái nào (emergency stop)
        if new_state != FSMState.STOPPED and new_state not in allowed:
            raise InvalidStateTransitionError(
                f"Không thể chuyển trạng thái từ '{self._current_state}' sang '{new_state}'. Lý do yêu cầu: '{reason}'"
            )

        now = time.monotonic()
        self._current_state = new_state
        self._state_entered_time = now
        self._history.append((now, new_state, reason))
        if len(self._history) > 100:
            self._history.pop(0)

    def check_timeout(self, now: Optional[float] = None) -> bool:
        """
        Kiểm tra xem trạng thái hiện tại có bị quá hạn không (V4-T14).
        Trả về True nếu bị timeout.
        """
        t = time.monotonic() if now is None else now
        limit = self.state_timeouts.get(self._current_state)
        if limit is not None:
            if (t - self._state_entered_time) > limit:
                return True
        return False

    def get_history(self) -> List[Tuple[float, FSMState, str]]:
        return list(self._history)
