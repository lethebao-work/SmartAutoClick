import os
import time
import copy
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Tuple

import numpy as np

from core.capture import ScreenCapture
from core.detector import ColorDetector
from core.clicker import InputSimulator
from core.config_manager import ConfigManager, get_data_dir
from core.window_guard import WindowGuard

try:
    import winsound
except ImportError:
    winsound = None


class EngineState:
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"


# ──────────────────────────────────────────────────────────────────────────────
# Animation Detector — so sánh frame để biết animation đã kết thúc chưa
# ──────────────────────────────────────────────────────────────────────────────

class AnimationDetector:
    """
    So sánh 2 frame liên tiếp của một vùng màn hình.
    Nếu mức độ thay đổi pixel < stable_threshold → màn hình đã tĩnh (animation xong).
    Nếu vẫn còn thay đổi → đang animation → tiếp tục chờ.
    """

    def __init__(self, stable_threshold: float = 1.5, min_stable_frames: int = 2):
        """
        stable_threshold: % pixel thay đổi tối đa để coi là "đã tĩnh"
        min_stable_frames: bao nhiêu frame liên tiếp tĩnh mới xác nhận xong
        """
        self.stable_threshold = stable_threshold
        self.min_stable_frames = min_stable_frames
        self._prev_frame: Optional[np.ndarray] = None
        self._stable_count: int = 0

    def reset(self):
        self._prev_frame = None
        self._stable_count = 0

    def feed(self, frame: np.ndarray) -> Tuple[bool, float]:
        """
        Nhận frame mới. Trả về (is_stable, change_percent).
        is_stable=True nghĩa là animation đã kết thúc.
        """
        if self._prev_frame is None:
            self._prev_frame = frame.copy()
            self._stable_count = 0
            return False, 100.0

        # Convert to grayscale for comparison
        import cv2
        if len(frame.shape) == 3:
            gray_cur = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray_prev = cv2.cvtColor(self._prev_frame, cv2.COLOR_BGR2GRAY)
        else:
            gray_cur = frame
            gray_prev = self._prev_frame

        # Absolute difference
        diff = cv2.absdiff(gray_cur, gray_prev)
        # Count pixels that changed significantly (>15 intensity)
        changed = np.count_nonzero(diff > 15)
        total = diff.size
        change_pct = (changed / total) * 100.0 if total > 0 else 0.0

        self._prev_frame = frame.copy()

        if change_pct < self.stable_threshold:
            self._stable_count += 1
        else:
            self._stable_count = 0

        is_stable = self._stable_count >= self.min_stable_frames
        return is_stable, round(change_pct, 2)


# ──────────────────────────────────────────────────────────────────────────────
# Budget Guard — phát hiện nút Roll bị mờ/disabled (hết tiền)
# ──────────────────────────────────────────────────────────────────────────────

class BudgetGuard:
    """
    Kiểm tra nút Roll có bị "disabled" (hết tiền) không bằng cách:
    So sánh độ sáng trung bình pixel của vùng nút Roll với lần đầu chạy.
    Nếu vùng nút tối hơn ngưỡng → coi như nút đã bị mờ → hết tiền.

    Cũng hỗ trợ cấu hình một màu "indicator" riêng để kiểm tra.
    """

    def __init__(
        self,
        enabled: bool = False,
        btn_x: int = 0, btn_y: int = 0,
        btn_w: int = 80, btn_h: int = 30,
        brightness_drop_threshold: float = 30.0,
    ):
        self.enabled = enabled
        self.btn_x = btn_x
        self.btn_y = btn_y
        self.btn_w = btn_w
        self.btn_h = btn_h
        self.brightness_drop_threshold = brightness_drop_threshold  # absolute V drop
        self._baseline_brightness: Optional[float] = None

    def calibrate(self, capture: ScreenCapture):
        """Chụp và ghi nhận độ sáng ban đầu của nút Roll để so sánh sau."""
        if not self.enabled:
            return
        import cv2
        frame = capture.capture_region(self.btn_x, self.btn_y, self.btn_w, self.btn_h)
        if frame is None or frame.size == 0:
            raise RuntimeError(f"BudgetGuard không thể chụp vùng nút Roll ({self.btn_x}, {self.btn_y})")
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        self._baseline_brightness = float(hsv[:, :, 2].mean())

    def is_out_of_budget(self, capture: ScreenCapture) -> bool:
        """
        Trả về True nếu phát hiện nút Roll bị tối đi đáng kể → hết tiền.
        """
        if not self.enabled:
            return False
        if self._baseline_brightness is None:
            # Enabled nhưng không có baseline -> fail-safe dừng để bảo vệ tài khoản
            return True
        try:
            import cv2
            frame = capture.capture_region(self.btn_x, self.btn_y, self.btn_w, self.btn_h)
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            current_brightness = float(hsv[:, :, 2].mean())
            drop = self._baseline_brightness - current_brightness
            return drop > self.brightness_drop_threshold
        except Exception:
            return True


# ──────────────────────────────────────────────────────────────────────────────
# Multi-Action Rule Engine — IF color → action per slot
# ──────────────────────────────────────────────────────────────────────────────

class SlotAction:
    """Hành động áp dụng cho từng slot khi phát hiện màu."""
    STOP = "stop"            # Dừng toàn bộ
    LOCK = "lock"            # Khóa slot này, tiếp tục roll


class RuleEngine:
    """
    Xử lý logic đa điều kiện theo từng vùng slot.
    Rules: dict của color_key → SlotAction
    VD: {"red": "stop", "purple": "lock"}
    """

    def __init__(self, rules: Dict[str, str]):
        self.rules = rules  # {"color_key": "stop"|"lock"}

    def evaluate(self, analysis: Dict[str, Any]) -> Optional[str]:
        """
        Nhận kết quả phân tích từ detector.
        Trả về action ("stop" / "lock" / None).
        """
        if not analysis.get("detected"):
            return None
        matched = analysis.get("matched_color")
        if matched and matched in self.rules:
            return self.rules[matched]
        # Default: stop if any color detected and no specific rule
        return SlotAction.STOP

    @staticmethod
    def from_config(config_manager: ConfigManager) -> "RuleEngine":
        rules = config_manager.get("action_rules", {})
        return RuleEngine(rules)


# ──────────────────────────────────────────────────────────────────────────────
# Main Engine
# ──────────────────────────────────────────────────────────────────────────────

class AutoClickEngine:
    """
    Quy trình điều khiển chính với đầy đủ tính năng:
    1. Chụp từng vùng (slot) theo dõi độc lập
    2. Phân tích màu sắc & áp dụng Action Rules (lock/stop per color)
    3. Animation detection: chờ màn hình tĩnh sau mỗi roll
    4. Budget guard: dừng nếu nút Roll bị disabled
    5. Screenshot + Sound khi tìm thấy đồ hiếm
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        capture: Optional[Any] = None,
        detector: Optional[Any] = None,
        clicker: Optional[Any] = None,
        animation_detector: Optional[Any] = None,
        clock: Optional[Any] = None,
    ):
        self.config_manager = config_manager
        self._custom_capture = capture is not None
        self._custom_detector = detector is not None
        self._custom_clicker = clicker is not None
        self._custom_animation_detector = animation_detector is not None
        self.clock = clock

        self.capture = capture or ScreenCapture()
        self.detector = detector or ColorDetector(
            color_definitions=self.config_manager.get("color_definitions", {}),
            default_threshold_percent=self.config_manager.get("match_threshold_percent", 1.0)
        )
        self.clicker = clicker or InputSimulator()
        self.animation_detector = animation_detector or AnimationDetector(
            stable_threshold=self.config_manager.get("anim_stable_threshold", 1.5),
            min_stable_frames=self.config_manager.get("anim_stable_frames", 2)
        )
        self.budget_guard = self._build_budget_guard()
        self.rule_engine = RuleEngine.from_config(config_manager)

        self.state = EngineState.IDLE
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()

        self.current_roll_count = 0
        self._consecutive_capture_errors = 0
        # Tracks which slot IDs are locked (discovered Purple etc., skip them)
        self._locked_slots: set = set()

        # Callbacks
        self.on_log: Optional[Callable[[str, str], None]] = None
        self.on_status_change: Optional[Callable[[str], None]] = None
        self.on_roll_attempt: Optional[Callable[[int, Dict[str, Any]], None]] = None
        self.on_target_found: Optional[Callable[[str, float, Optional[str]], None]] = None
        self.on_slot_locked: Optional[Callable[[str, str], None]] = None   # slot_id, color_name
        self.on_finished: Optional[Callable[[str], None]] = None

    def _build_budget_guard(self) -> BudgetGuard:
        cfg = self.config_manager.get("budget_guard", {})
        roll_btn = self.config_manager.get_roll_button()
        return BudgetGuard(
            enabled=bool(cfg.get("enabled", False)),
            btn_x=int(cfg.get("x", roll_btn.get("x", 0) - 40)),
            btn_y=int(cfg.get("y", roll_btn.get("y", 0) - 15)),
            btn_w=int(cfg.get("w", 90)),
            btn_h=int(cfg.get("h", 30)),
            brightness_drop_threshold=float(cfg.get("brightness_drop", 30.0)),
        )

    def log(self, message: str, level: str = "INFO"):
        prefix = f"[{datetime.now().strftime('%H:%M:%S')}][{level}]"
        print(f"{prefix} {message}")
        if self.on_log:
            try:
                self.on_log(message, level)
            except Exception:
                pass

    def set_state(self, new_state: str):
        self.state = new_state
        if self.on_status_change:
            try:
                self.on_status_change(new_state)
            except Exception:
                pass

    def reload_config(self):
        """Reload runtime config từ ConfigManager."""
        if not self._custom_detector:
            self.detector.update_definitions(
                self.config_manager.get("color_definitions", {}),
                self.config_manager.get("match_threshold_percent", 1.0)
            )
        self.rule_engine = RuleEngine.from_config(self.config_manager)
        if not self._custom_animation_detector:
            self.animation_detector = AnimationDetector(
                stable_threshold=self.config_manager.get("anim_stable_threshold", 1.5),
                min_stable_frames=self.config_manager.get("anim_stable_frames", 2)
            )
        old_guard = getattr(self, "budget_guard", None)
        new_guard = self._build_budget_guard()
        if old_guard and old_guard._baseline_brightness is not None:
            if (old_guard.btn_x, old_guard.btn_y) == (new_guard.btn_x, new_guard.btn_y):
                new_guard._baseline_brightness = old_guard._baseline_brightness
        self.budget_guard = new_guard

    def start(self):
        if self.state == EngineState.RUNNING:
            self.log("Engine da dang chay roi.", "WARN")
            return
        if self.state == EngineState.PAUSED:
            self.resume()
            return

        targets = self.config_manager.get_target_colors()
        if not targets:
            self.log("Loi: Chua chon mau muc tieu (target_colors)! Dung an toan.", "ERROR")
            self.set_state(EngineState.STOPPED)
            if self.on_finished:
                try:
                    self.on_finished("no_target_color")
                except Exception:
                    pass
            return

        regions = self.config_manager.get_watch_regions()
        if not regions:
            self.log("Loi: Chua cau hinh vung quan sat (watch_regions)! Dung an toan.", "ERROR")
            self.set_state(EngineState.STOPPED)
            if self.on_finished:
                try:
                    self.on_finished("no_region_configured")
                except Exception:
                    pass
            return

        # Snapshot config at start time to ensure immutable execution run
        self.active_config = copy.deepcopy(self.config_manager.data)
        self._last_click_pos = None

        # Join old thread if still running (prevent race conditions)
        if self._thread is not None and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=2.0)

        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()

        self.current_roll_count = 0
        self._consecutive_capture_errors = 0
        self._locked_slots.clear()
        self.animation_detector.reset()
        self.set_state(EngineState.RUNNING)
        self.reload_config()

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self.log("Khoi dong Auto Clicker thanh cong!", "SUCCESS")

    def pause(self):
        if self.state == EngineState.RUNNING:
            self._pause_event.clear()
            self.set_state(EngineState.PAUSED)
            self.log("Da tam dung Auto Clicker.", "INFO")

    def resume(self):
        if self.state == EngineState.PAUSED:
            self._pause_event.set()
            self.set_state(EngineState.RUNNING)
            self.log("Tiep tuc chay Auto Clicker.", "INFO")

    def toggle_pause(self):
        if self.state in (EngineState.IDLE, EngineState.STOPPED):
            self.start()
        elif self.state == EngineState.RUNNING:
            self.pause()
        elif self.state == EngineState.PAUSED:
            self.resume()

    def stop(self, reason: str = "user_stopped"):
        self._stop_event.set()
        self._pause_event.set()
        self.set_state(EngineState.STOPPED)
        self.log(f"Da dung Auto Clicker. Ly do: {reason}", "INFO")
        if self.on_finished:
            try:
                self.on_finished(reason)
            except Exception:
                pass

    def _sleep_interruptible(self, seconds: float) -> bool:
        if self.clock is not None:
            return self.clock.sleep_interruptible(seconds, self._stop_event)
        end_time = time.monotonic() + seconds
        while time.monotonic() < end_time:
            if self._stop_event.is_set():
                return False
            time.sleep(min(0.01, seconds))
        return True

    def _wait_for_animation_end(
        self, region: Dict[str, Any], max_wait: float = 8.0, poll_interval: float = 0.05
    ) -> bool:
        """
        Chờ đến khi vùng màn hình tĩnh lại (animation kết thúc) hoặc timeout.
        Trả về True nếu tĩnh, False nếu timeout hoặc bị dừng.
        """
        rx, ry, rw, rh = int(region["x"]), int(region["y"]), int(region["w"]), int(region["h"])
        self.animation_detector.reset()
        start_time = time.monotonic()
        while time.monotonic() - start_time < max_wait:
            if self._stop_event.is_set():
                return False
            try:
                frame = self.capture.capture_region(rx, ry, rw, rh)
                is_stable, change_pct = self.animation_detector.feed(frame)
                if is_stable:
                    elapsed = time.monotonic() - start_time
                    self.log(f"Animation xong sau {elapsed:.2f}s (change={change_pct:.1f}%)", "DEBUG")
                    return True
            except Exception as e:
                self.log(f"Animation capture check error: {e}", "DEBUG")
            if not self._sleep_interruptible(poll_interval):
                return False
        self.log(f"Animation timeout sau {max_wait}s, tiep tuc...", "WARN")
        return True  # timeout but continue anyway

    def _play_alert_sound(self):
        try:
            if winsound is not None:
                winsound.Beep(880, 150)
                time.sleep(0.05)
                winsound.Beep(1100, 150)
                time.sleep(0.05)
                winsound.Beep(1320, 300)
        except Exception:
            pass

    def _save_match_screenshot(self, color_name: str) -> Optional[str]:
        try:
            screenshots_dir = os.path.join(get_data_dir(), "screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = "".join(c if c.isalnum() else "_" for c in color_name)
            path = os.path.abspath(os.path.join(screenshots_dir, f"match_{safe_name}_{timestamp}.png"))
            full_img = self.capture.capture_fullscreen()
            self.capture.save_image(full_img, path)
            self.log(f"Da luu anh chup tai: {path}", "INFO")
            return path
        except Exception as e:
            self.log(f"Khong the luu anh: {e}", "WARN")
            return None

    def _fire_target_found(self, color_name: str, percent: float, save: bool, play_sound: bool):
        path = None
        self.log(f"TIM THAY DO HIEM: {color_name} ({percent}% dien tich)!", "SUCCESS")
        if save:
            path = self._save_match_screenshot(color_name)
        if play_sound:
            self._play_alert_sound()
        if self.on_target_found:
            try:
                self.on_target_found(color_name, percent, path)
            except Exception:
                pass

    # ──────────────────────────────────────────────────────────────────────────
    # Main Loop
    # ──────────────────────────────────────────────────────────────────────────

    def _run_loop(self):
        active_cfg = getattr(self, "active_config", None) or copy.deepcopy(self.config_manager.data)
        roll_btn = active_cfg.get("roll_button", {"x": 1000, "y": 600})
        max_rolls = int(active_cfg.get("max_rolls", 100))
        delay = float(active_cfg.get("delay_between_rolls", 1.5))
        play_sound = bool(active_cfg.get("play_sound", True))
        save_screenshot = bool(active_cfg.get("save_screenshot", True))
        use_anim_detect = bool(active_cfg.get("use_animation_detection", False))
        anim_max_wait = float(active_cfg.get("anim_max_wait", 6.0))
        border_only = bool(active_cfg.get("border_only", False))
        target_window = str(active_cfg.get("target_window_title", "")).strip()
        guard_mouse = bool(active_cfg.get("guard_mouse_move", True))

        self.log(
            f"Bat dau vong lap | Roll: ({roll_btn.get('x', 0)},{roll_btn.get('y', 0)}) "
            f"| Gioi han: {max_rolls} | Cho: {delay}s "
            f"| Anim detect: {use_anim_detect}",
            "INFO"
        )

        finish_reason = "normal_exit"

        try:
            # Budget guard calibration (record baseline brightness of Roll button area)
            if self.budget_guard.enabled:
                try:
                    self.budget_guard.calibrate(self.capture)
                    self.log("Budget guard: Da ghi nhan do sang ban dau cua nut Roll.", "INFO")
                except Exception as e:
                    self.log(f"Budget guard calibrate that bai: {e}", "WARN")

            regions = active_cfg.get("watch_regions", [])
            if not regions:
                self.log("Chua cau hinh vung quan sat! Dung tien trinh.", "ERROR")
                finish_reason = "no_region_configured"
                return

            self._consecutive_capture_errors = 0

            while not self._stop_event.is_set():
                # ── Handle pause ──
                self._pause_event.wait()
                if self._stop_event.is_set():
                    finish_reason = "user_stopped"
                    break

                # ── Check foreground window if configured ──
                if target_window and not WindowGuard.is_target_window_active(target_window):
                    self.log(f"Cua so game '{target_window}' khong con o Foreground. Tu dong tam dung an toan.", "WARN")
                    self.pause()
                    continue

                # ── Check user mouse manual intervention ──
                if guard_mouse and self._last_click_pos is not None:
                    curr_mouse = self.clicker.get_mouse_position()
                    if WindowGuard.is_user_interfering(self._last_click_pos, curr_mouse):
                        self.log("Phat hien nguoi dung dang di chuot! Tu dong tam dung de tranh xung dot.", "WARN")
                        self.pause()
                        continue

                # ── 1. MULTI-SLOT SCAN (Always scan before checking limits or rolling) ──
                target_colors = active_cfg.get("target_colors", [])
                should_stop = False
                capture_failed_this_cycle = False

                for region in regions:
                    slot_id = region.get("id", "slot_0")

                    # Skip already locked slots
                    if slot_id in self._locked_slots:
                        continue

                    rx, ry, rw, rh = int(region["x"]), int(region["y"]), int(region["w"]), int(region["h"])
                    try:
                        img_bgr = self.capture.capture_region(rx, ry, rw, rh)
                        self._consecutive_capture_errors = 0
                    except Exception as e:
                        self._consecutive_capture_errors += 1
                        self.log(f"Loi chup man hinh slot {slot_id} ({self._consecutive_capture_errors}/3): {e}", "ERROR")
                        if self._consecutive_capture_errors >= 3:
                            self.log("Mat thi giac/chup man hinh that bai lien tiep. Dung an toan fail-safe!", "ERROR")
                            finish_reason = "capture_failed"
                            should_stop = True
                            break
                        capture_failed_this_cycle = True
                        continue

                    analysis = self.detector.analyze_image(img_bgr, target_colors=target_colors, border_only=border_only)

                    if self.on_roll_attempt:
                        try:
                            self.on_roll_attempt(self.current_roll_count, analysis)
                        except Exception:
                            pass

                    if not analysis["detected"]:
                        continue

                    # ── Color detected in this slot — evaluate rule ──
                    action = self.rule_engine.evaluate(analysis)
                    color_name = analysis.get("matched_name") or analysis.get("matched_color", "unknown")
                    percent = analysis.get("matched_percent", 0.0)

                    if action == SlotAction.STOP:
                        self._fire_target_found(color_name, percent, save_screenshot, play_sound)
                        finish_reason = "target_color_found"
                        should_stop = True
                        break

                    elif action == SlotAction.LOCK:
                        self._locked_slots.add(slot_id)
                        self.log(f"LOCK slot {slot_id}: Phat hien {color_name} ({percent}%). Giu slot nay, tiep tuc roll cac slot con lai.", "SUCCESS")
                        if play_sound:
                            try:
                                if winsound:
                                    winsound.Beep(800, 200)
                            except Exception:
                                pass
                        if self.on_slot_locked:
                            try:
                                self.on_slot_locked(slot_id, color_name)
                            except Exception:
                                pass
                        if save_screenshot:
                            self._save_match_screenshot(f"lock_{slot_id}_{color_name}")

                if should_stop:
                    break

                if capture_failed_this_cycle:
                    if not self._sleep_interruptible(0.2):
                        finish_reason = "user_stopped"
                        break
                    continue

                # ── 2. RE-CALCULATE all_locked IMMEDIATELY AFTER SCANNING ──
                all_locked_now = len(regions) > 0 and all(r.get("id", f"slot_{i}") in self._locked_slots for i, r in enumerate(regions))
                if all_locked_now:
                    self.log("Tat ca cac slot da bi LOCK! Dung hoat dong.", "SUCCESS")
                    self._fire_target_found("all_slots_locked", 100.0, save_screenshot, play_sound)
                    finish_reason = "all_slots_locked"
                    break

                # ── 3. CHECK LIMITS AFTER SCAN (budget & max_rolls) ──
                if self.budget_guard.enabled and self.budget_guard.is_out_of_budget(self.capture):
                    self.log("CANH BAO: Phat hien nut Roll bi mo/disabled! Co the het tien. Dung an toan.", "WARN")
                    finish_reason = "out_of_budget"
                    break

                if self.current_roll_count >= max_rolls:
                    self.log(f"Da dat so lan roll toi da ({max_rolls}). Dung an toan.", "WARN")
                    finish_reason = "max_rolls_reached"
                    break

                # ── 4. CLICK ROLL ──
                self.current_roll_count += 1
                self.log(f"Roll lan {self.current_roll_count}/{max_rolls} -> Click Roll...", "DEBUG")

                click_success = self.clicker.click(roll_btn["x"], roll_btn["y"])
                if not click_success:
                    self.log("Khong the click vao nut Roll. Dung an toan.", "ERROR")
                    finish_reason = "click_failed"
                    break
                self._last_click_pos = (int(roll_btn["x"]), int(roll_btn["y"]))

                # ── 5. WAIT SETTLED (Animation or delay) ──
                random_offset_ms = float(active_cfg.get("delay_random_offset_ms", 0))

                if use_anim_detect and regions:
                    settled = self._wait_for_animation_end(regions[0], max_wait=anim_max_wait)
                    if not settled and self._stop_event.is_set():
                        finish_reason = "user_stopped"
                        break
                    extra = 0.2
                    if random_offset_ms > 0:
                        import random
                        extra = max(0.05, 0.2 + random.uniform(-random_offset_ms / 2, random_offset_ms / 2) / 1000.0)
                    if not self._sleep_interruptible(extra):
                        finish_reason = "user_stopped"
                        break
                else:
                    actual_delay = delay
                    if random_offset_ms > 0:
                        import random
                        jitter = random.uniform(-random_offset_ms, random_offset_ms) / 1000.0
                        actual_delay = max(0.05, delay + jitter)
                    if not self._sleep_interruptible(actual_delay):
                        finish_reason = "user_stopped"
                        break

        except Exception as e:
            self.log(f"Loi nghiem trong trong vong lap Engine: {e}", "ERROR")
            finish_reason = f"error: {e}"
        finally:
            self.set_state(EngineState.STOPPED)
            self._stop_event.set()
            self._pause_event.set()
            if self.on_finished:
                try:
                    self.on_finished(finish_reason)
                except Exception:
                    pass
            self.log(f"Tien trinh ket thuc. Ly do: {finish_reason}", "INFO")

