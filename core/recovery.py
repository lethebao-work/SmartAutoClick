"""
Chính sách phục hồi lỗi và an toàn (Recovery Policy & Safety) cho SmartAutoClick v3.1 (Phase 5).

Nhiệm vụ:
- V5-T13: Phân loại lỗi thành 3 cấp:
    1. TRANSIENT: Lỗi tạm thời (ví dụ frame rỗng, lag nhẹ) -> Retry ngắn, backoff.
    2. RECOVERABLE: Lỗi có thể phục hồi (capture reset, mất anchor tạm thời) -> Khởi tạo lại capture, tìm lại anchor.
    3. FATAL: Lỗi nghiêm trọng (mất cửa sổ game, hết ngân sách, can thiệp chuột, lỗi liên tiếp vượt ngưỡng) -> Dừng an toàn (Emergency Safe Stop).
- V5-T14: Retry Limit + Exponential Backoff có giới hạn trần.
- V5-T15 & V5-T18: Dừng hành động ngay khi dữ liệu không đáng tin cậy; tuyệt đối KHÔNG tự ý gửi lại các hành động tiêu hao tài nguyên khi chưa xác nhận trạng thái game.
- V5-T16 & V5-T17: Sau recovery -> Quan sát lại trạng thái game rồi mới cho phép tiếp tục chu trình.
- V5-T22: Quản lý giới hạn an toàn (BudgetLimit, MaxRollsLimit, MaxRuntimeLimit).
"""
from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Dict, Optional, Tuple


class ErrorSeverity(str, Enum):
    TRANSIENT = "transient"      # Lỗi tạm thời: retry ngay hoặc nghỉ nhẹ
    RECOVERABLE = "recoverable"  # Có thể phục hồi: re-init capture, re-find anchor
    FATAL = "fatal"              # Nghiêm trọng: bắt buộc dừng an toàn (Safe Stop)


class RecoveryAction(str, Enum):
    RETRY_NOW = "retry_now"
    WAIT_AND_RETRY = "wait_and_retry"
    REINIT_CAPTURE = "reinit_capture"
    REFIND_ANCHOR = "refind_anchor"
    SAFE_STOP = "safe_stop"


@dataclass
class SafetyBudget:
    """Quản lý các giới hạn an toàn khi bot chạy lâu dài (V5-T22)."""
    max_rolls: int = 100
    max_runtime_s: float = 3600.0 * 8 # Tối đa 8 tiếng
    max_consecutive_errors: int = 3
    enforce_budget_guard: bool = True


class RecoveryManager:
    """
    Quản lý chính sách phục hồi lỗi và đảm bảo an toàn vận hành.
    """

    def __init__(
        self,
        max_transient_retries: int = 3,
        base_backoff_s: float = 0.2,
        max_backoff_s: float = 2.0,
        safety_budget: Optional[SafetyBudget] = None,
    ):
        self.max_transient_retries = max_transient_retries
        self.base_backoff_s = base_backoff_s
        self.max_backoff_s = max_backoff_s
        self.safety_budget = safety_budget or SafetyBudget()

        self.consecutive_errors: int = 0
        self.total_recoveries: int = 0
        self.start_time: float = time.monotonic()
        self._last_error: Optional[str] = None

    def classify_issue(self, error_type: str, details: str = "") -> ErrorSeverity:
        """
        V5-T13: Phân loại mức độ nghiêm trọng của lỗi.
        """
        fatal_keywords = [
            "window_lost", "window_closed", "budget_exceeded", "user_intervened",
            "max_rolls_reached", "runtime_limit_exceeded", "auth_failed"
        ]
        recoverable_keywords = [
            "capture_failed", "backend_crash", "anchor_lost", "geometry_mismatch",
            "frozen_capture", "stale_frame"
        ]

        lower_err = error_type.lower()
        for kw in fatal_keywords:
            if kw in lower_err:
                return ErrorSeverity.FATAL

        for kw in recoverable_keywords:
            if kw in lower_err:
                return ErrorSeverity.RECOVERABLE

        return ErrorSeverity.TRANSIENT

    def handle_error(self, error_type: str, details: str = "") -> Tuple[RecoveryAction, float, str]:
        """
        V5-T14 & V5-T15: Quyết định hành động phục hồi và thời gian chờ (backoff).
        Trả về (action, delay_s, reason).
        """
        self.consecutive_errors += 1
        self._last_error = f"{error_type}: {details}"

        # Kiểm tra vượt ngưỡng lỗi liên tiếp tối đa
        if self.consecutive_errors > self.safety_budget.max_consecutive_errors:
            return (
                RecoveryAction.SAFE_STOP,
                0.0,
                f"Vượt quá giới hạn lỗi liên tiếp ({self.consecutive_errors} > {self.safety_budget.max_consecutive_errors}): {details}",
            )

        severity = self.classify_issue(error_type, details)

        if severity == ErrorSeverity.FATAL:
            return RecoveryAction.SAFE_STOP, 0.0, f"Lỗi nghiêm trọng không thể phục hồi: {details}"

        if severity == ErrorSeverity.RECOVERABLE:
            self.total_recoveries += 1
            if "anchor" in error_type.lower():
                return RecoveryAction.REFIND_ANCHOR, 0.5, "Mất neo: tạm dừng action, tìm lại anchor toàn khung"
            return RecoveryAction.REINIT_CAPTURE, 1.0, "Lỗi capture: tạm dừng action, khởi tạo lại capture adapter"

        # TRANSIENT: Tính exponential backoff
        backoff = min(self.max_backoff_s, self.base_backoff_s * (2 ** (self.consecutive_errors - 1)))
        return RecoveryAction.WAIT_AND_RETRY, backoff, f"Lỗi tạm thời ({self.consecutive_errors}/{self.max_transient_retries}): {details}"

    def reset_error_count(self) -> None:
        """Gọi khi quan sát hoặc hành động thành công để reset bộ đếm lỗi."""
        self.consecutive_errors = 0

    def check_safety_limits(self, current_rolls: int) -> Tuple[bool, str]:
        """
        V5-T22: Kiểm tra ngân sách / số lượt / thời gian chạy an toàn.
        """
        if current_rolls >= self.safety_budget.max_rolls:
            return False, f"Đã đạt số lần roll tối đa ({current_rolls}/{self.safety_budget.max_rolls})"

        elapsed = time.monotonic() - self.start_time
        if elapsed >= self.safety_budget.max_runtime_s:
            return False, f"Đã đạt thời gian chạy tối đa ({elapsed / 3600.0:.1f} giờ)"

        return True, "Safety limits OK"
