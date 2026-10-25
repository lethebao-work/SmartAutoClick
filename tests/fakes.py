"""
Test Harness Fakes & Mock adapters for SmartAutoClick.
Provides test doubles for ScreenCapture, InputSimulator, and Clock.
"""
import time
import threading
from typing import List, Tuple, Dict, Any, Optional, Callable
import numpy as np


from core.capture_interface import FrameSource, Frame, FrameStatus, to_frame


class FakeFrameSource(FrameSource):
    """Fake capture device allowing scripted frames or simulated errors."""
    def __init__(self, default_shape: Tuple[int, int, int] = (100, 100, 3)):
        self.default_shape = default_shape
        self.frames_queue: List[np.ndarray] = []
        self.calls: List[Tuple[int, int, int, int]] = []
        self.raise_on_capture: Optional[Exception] = None
        self.fail_count_before_ok: int = 0
        self.fail_forever: bool = False
        self.return_black_frame: bool = False
        self.last_frame: Optional[np.ndarray] = None
        self.frame_id: int = 0
        self.is_running: bool = False

    def start(self) -> bool:
        self.is_running = True
        return True

    def stop(self) -> None:
        self.is_running = False
        self.close()

    def latest(self) -> Frame:
        """Trả về Frame Contract mô phỏng theo hàng đợi."""
        self.frame_id += 1
        t_now = time.monotonic()
        if self.fail_forever:
            return Frame(image=None, frame_id=self.frame_id, timestamp=t_now, backend="fake", status=FrameStatus.CAPTURE_ERROR)
        if self.fail_count_before_ok > 0:
            self.fail_count_before_ok -= 1
            return Frame(image=None, frame_id=self.frame_id, timestamp=t_now, backend="fake", status=FrameStatus.CAPTURE_ERROR)
        if self.raise_on_capture:
            return Frame(image=None, frame_id=self.frame_id, timestamp=t_now, backend="fake", status=FrameStatus.CAPTURE_ERROR, metadata={"error": str(self.raise_on_capture)})
        if self.return_black_frame:
            black = np.zeros(self.default_shape, dtype=np.uint8)
            return Frame(image=black, frame_id=self.frame_id, timestamp=t_now, backend="fake", status=FrameStatus.VALID, client_size=(self.default_shape[1], self.default_shape[0]))

        if self.frames_queue:
            self.last_frame = self.frames_queue.pop(0)
            return Frame(image=self.last_frame.copy(), frame_id=self.frame_id, timestamp=t_now, backend="fake", status=FrameStatus.VALID, client_size=(self.last_frame.shape[1], self.last_frame.shape[0]))

        if self.last_frame is not None:
            return Frame(image=self.last_frame.copy(), frame_id=self.frame_id, timestamp=t_now, backend="fake", status=FrameStatus.VALID, client_size=(self.last_frame.shape[1], self.last_frame.shape[0]))

        blank = np.zeros(self.default_shape, dtype=np.uint8)
        return Frame(image=blank, frame_id=self.frame_id, timestamp=t_now, backend="fake", status=FrameStatus.VALID, client_size=(self.default_shape[1], self.default_shape[0]))

    def enqueue_frame(self, frame: np.ndarray):
        self.frames_queue.append(frame)

    def enqueue_frames(self, frames: List[np.ndarray]):
        self.frames_queue.extend(frames)

    def capture_region(self, x: int, y: int, w: int, h: int) -> np.ndarray:
        self.calls.append((x, y, w, h))
        if self.fail_forever:
            raise RuntimeError("Fake capture hardware failure")
        if self.fail_count_before_ok > 0:
            self.fail_count_before_ok -= 1
            raise RuntimeError("Fake intermittent capture failure")
        if self.raise_on_capture:
            raise self.raise_on_capture
        if self.return_black_frame:
            return np.zeros((h, w, 3), dtype=np.uint8)

        if self.frames_queue:
            self.last_frame = self.frames_queue.pop(0)
            return self.last_frame.copy()

        if self.last_frame is not None:
            return self.last_frame.copy()

        # Default blank frame
        return np.zeros((h, w, 3), dtype=np.uint8)

    def capture_fullscreen(self) -> np.ndarray:
        return np.zeros((1080, 1920, 3), dtype=np.uint8)

    def close(self):
        pass


class FakeInputSink:
    """Fake input sink recording click events without controlling OS mouse."""
    def __init__(self):
        self.clicks: List[Tuple[int, int]] = []
        self.fail_next_click: bool = False
        self.current_pos: Tuple[int, int] = (0, 0)

    def click(self, x: int, y: int) -> bool:
        if self.fail_next_click:
            return False
        self.clicks.append((int(x), int(y)))
        self.current_pos = (int(x), int(y))
        return True

    def get_mouse_position(self) -> Tuple[int, int]:
        return self.current_pos


class FakeClock:
    """Controlled virtual clock for deterministic, fast-forwarding timing tests."""
    def __init__(self, start_time: float = 1000.0):
        self._current_time = start_time

    def time(self) -> float:
        return self._current_time

    def monotonic(self) -> float:
        return self._current_time

    def sleep(self, seconds: float):
        self._current_time += seconds

    def sleep_interruptible(self, seconds: float, stop_event: threading.Event) -> bool:
        if stop_event.is_set():
            return False
        self._current_time += seconds
        return not stop_event.is_set()
