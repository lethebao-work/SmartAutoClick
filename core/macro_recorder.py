"""
Macro Recorder & Player
Cho phép người dùng ghi lại chuỗi click chuột thực tế và phát lại tự động
với tốc độ tùy chỉnh (0.5x, 1x, 2x, 5x) và số lần lặp lại.
"""

import time
import json
import threading
from typing import List, Dict, Any, Optional, Callable
import pyautogui

try:
    from pynput import mouse
except ImportError:
    mouse = None


class MacroRecorder:
    """Ghi lại các thao tác click chuột cùng khoảng cách thời gian giữa các lần bấm."""

    def __init__(self):
        self.is_recording = False
        self.events: List[Dict[str, Any]] = []
        self._last_time: Optional[float] = None
        self._listener: Optional[Any] = None
        self.on_event_recorded: Optional[Callable[[Dict[str, Any]], None]] = None

    def start(self):
        """Bắt đầu ghi lại thao tác click chuột."""
        if mouse is None:
            raise RuntimeError("Thư viện pynput chưa được cài đặt.")
        self.events = []
        self._last_time = time.time()
        self.is_recording = True

        def on_click(x, y, button, pressed):
            if not self.is_recording:
                return False
            # Chỉ ghi nhận sự kiện nhả chuột hoặc ấn xuống (chọn ấn xuống để bắt điểm chính xác)
            if pressed:
                now = time.time()
                delay_ms = int((now - self._last_time) * 1000) if self._last_time else 0
                self._last_time = now

                btn_name = "left"
                if button == mouse.Button.right:
                    btn_name = "right"
                elif button == mouse.Button.middle:
                    btn_name = "middle"

                event = {
                    "type": "click",
                    "x": int(x),
                    "y": int(y),
                    "button": btn_name,
                    "delay_ms": max(50, delay_ms)
                }
                self.events.append(event)
                if self.on_event_recorded:
                    try:
                        self.on_event_recorded(event)
                    except Exception:
                        pass

        self._listener = mouse.Listener(on_click=on_click)
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> List[Dict[str, Any]]:
        """Dừng ghi và trả về danh sách thao tác."""
        self.is_recording = False
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
        return self.events


class MacroPlayer:
    """Phát lại chuỗi thao tác chuột đã ghi."""

    def __init__(self):
        self.is_playing = False
        self._stop_flag = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.on_step_played: Optional[Callable[[int, Dict[str, Any]], None]] = None
        self.on_finished: Optional[Callable[[], None]] = None

    def play(
        self,
        steps: List[Dict[str, Any]],
        speed: float = 1.0,
        loop_count: int = 1,
        infinite: bool = False
    ):
        """Phát chuỗi macro trong một background thread."""
        if self.is_playing:
            return
        if not steps:
            return

        self.is_playing = True
        self._stop_flag.clear()

        def _worker():
            try:
                current_loop = 0
                while not self._stop_flag.is_set():
                    current_loop += 1
                    for idx, step in enumerate(steps):
                        if self._stop_flag.is_set():
                            break

                        # Tính thời gian chờ theo hệ số tốc độ speed
                        delay_ms = step.get("delay_ms", 300)
                        wait_sec = (delay_ms / 1000.0) / max(0.1, speed)
                        
                        # Chờ ngắt quãng để phản hồi dừng nhanh
                        waited = 0.0
                        chunk = 0.05
                        while waited < wait_sec and not self._stop_flag.is_set():
                            time.sleep(min(chunk, wait_sec - waited))
                            waited += chunk

                        if self._stop_flag.is_set():
                            break

                        x = step.get("x", 0)
                        y = step.get("y", 0)
                        btn = step.get("button", "left")

                        # Thực hiện click
                        try:
                            pyautogui.click(x=x, y=y, button=btn)
                        except pyautogui.FailSafeException:
                            print("[Macro] FailSafe kích hoạt! Dừng khẩn cấp.")
                            self._stop_flag.set()
                            break
                        except Exception as e:
                            print(f"[Macro] Lỗi khi click bước {idx}: {e}")

                        if self.on_step_played:
                            try:
                                self.on_step_played(idx, step)
                            except Exception:
                                pass

                    if not infinite and current_loop >= loop_count:
                        break
            finally:
                self.is_playing = False
                if self.on_finished:
                    try:
                        self.on_finished()
                    except Exception:
                        pass

        self._thread = threading.Thread(target=_worker, daemon=True)
        self._thread.start()

    def stop(self):
        """Dừng phát lại macro."""
        self._stop_flag.set()
        if self._thread is not None and self._thread.is_alive() and self._thread != threading.current_thread():
            self._thread.join(timeout=1.0)
        self.is_playing = False


def save_macro(filepath: str, steps: List[Dict[str, Any]]) -> bool:
    """Lưu danh sách thao tác macro ra file JSON."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({"version": "1.0", "steps": steps}, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Lỗi khi lưu macro: {e}")
        return False


def load_macro(filepath: str) -> List[Dict[str, Any]]:
    """Đọc danh sách thao tác macro từ file JSON."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("steps", [])
    except Exception as e:
        print(f"Lỗi khi đọc macro: {e}")
        return []
