"""
Đồng bộ theo KHUNG HÌNH thay vì theo giờ.

Sau mỗi lần click, ta không biết game phản hồi lúc nào. TwoPhaseSettle quan sát các
slot (so với khung TRƯỚC khi click) theo hai pha:

  Pha 1  "game đã phản hồi":  MỌI slot phải đổi so với khung trước click
         (require_all=True; slot còn ảnh cũ = có thể là kết quả của lần roll trước).
         Không thấy gì sau first_change_timeout -> NO_RESPONSE
         (click trượt, nút bị khóa/hết tiền, game treo ...).
  Pha 2  "đã ổn định":        mọi slot gần như không đổi trong stable_ms liên tục.
         Quá max_wait mà chưa ổn định -> TIMEOUT.

Không đọc kết quả ở bất kỳ trạng thái nào khác SETTLED -> không bao giờ đọc ảnh cũ
hoặc ảnh giữa animation rồi click đè.
Lớp này thuần túy (không chụp, không sleep) nên test được bằng khung tổng hợp.
"""
from typing import List, Optional, Sequence

import numpy as np

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None


class SettleState:
    SETTLED = "settled"
    NO_RESPONSE = "no_response"
    TIMEOUT = "timeout"


def change_percent(a: np.ndarray, b: np.ndarray, pixel_delta: int = 15) -> float:
    """% pixel có chênh lệch (max theo kênh) > pixel_delta giữa hai khung cùng kích thước."""
    if a is None or b is None or a.shape != b.shape or a.size == 0:
        return 100.0
    if cv2 is not None:
        diff = cv2.absdiff(a, b)
    else:
        diff = np.abs(a.astype(np.int16) - b.astype(np.int16)).astype(np.uint8)
    if diff.ndim == 3:
        diff = diff.max(axis=2)
    return float(np.count_nonzero(diff > pixel_delta)) * 100.0 / diff.size


def max_change(frames: Sequence[np.ndarray], refs: Sequence[np.ndarray], pixel_delta: int) -> float:
    if len(frames) != len(refs) or not frames:
        return 100.0
    return max(change_percent(f, r, pixel_delta) for f, r in zip(frames, refs))


class TwoPhaseSettle:
    def __init__(
        self,
        baseline: Sequence[np.ndarray],
        start_time: float,
        *,
        pixel_delta: int = 15,
        change_start_pct: float = 0.5,
        stable_pct: float = 0.5,
        stable_s: float = 0.25,
        first_change_timeout_s: float = 1.5,
        max_wait_s: float = 6.0,
        require_all: bool = True,
    ):
        self.baseline: List[np.ndarray] = [b.copy() for b in baseline]
        self.start_time = start_time
        self.pixel_delta = pixel_delta
        self.change_start_pct = change_start_pct
        self.stable_pct = stable_pct
        self.stable_s = stable_s
        self.first_change_timeout_s = first_change_timeout_s
        self.max_wait_s = max_wait_s
        self.require_all = require_all

        self._slot_changed = [False] * len(self.baseline)
        self.changed = False
        self.t_first_change: Optional[float] = None
        self.last_change_pct = 0.0
        self._prev: List[np.ndarray] = self.baseline
        self._prev_t = start_time
        self._stable_since: Optional[float] = None

    def feed(self, frames: Sequence[np.ndarray], now: float) -> Optional[str]:
        """Nạp khung mới (một ảnh cho mỗi slot, cùng thứ tự baseline). None = tiếp tục chờ."""
        elapsed = now - self.start_time
        if len(frames) != len(self.baseline):
            per_slot = [100.0] * len(self.baseline)
        else:
            per_slot = [change_percent(f, b, self.pixel_delta) for f, b in zip(frames, self.baseline)]
        for i, c in enumerate(per_slot):
            if c >= self.change_start_pct:
                self._slot_changed[i] = True
        ready = all(self._slot_changed) if self.require_all else any(self._slot_changed)
        vs_prev = max_change(frames, self._prev, self.pixel_delta)
        self.last_change_pct = vs_prev
        result: Optional[str] = None

        if not self.changed:
            if ready:
                self.changed = True
                self.t_first_change = now
                self._stable_since = None
            elif elapsed >= self.first_change_timeout_s:
                result = SettleState.NO_RESPONSE
        else:
            if vs_prev <= self.stable_pct:
                if self._stable_since is None:
                    self._stable_since = self._prev_t  # tĩnh kể từ khung trước
                if now - self._stable_since >= self.stable_s:
                    result = SettleState.SETTLED
            else:
                self._stable_since = None

        if result is None and elapsed >= self.max_wait_s:
            result = SettleState.TIMEOUT

        self._prev = [f.copy() for f in frames]
        self._prev_t = now
        return result
