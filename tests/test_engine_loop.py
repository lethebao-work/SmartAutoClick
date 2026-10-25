"""
Test scenarios for core engine loop:
Test A (E-01): Final roll item detection (quét trước khi check max_rolls)
Test B (E-02): No extra click after locking final slot
Test C (E-03): Animation detection settle handling
Test D (E-04): Consecutive capture failures trigger safe stop with capture_failed
"""
import time
import os
import shutil
import tempfile
import unittest
from pathlib import Path
import numpy as np

from core.config_manager import ConfigManager
from core.engine import AutoClickEngine, EngineState, SlotAction
from core.detector import ColorDetector
from tests.fakes import FakeFrameSource, FakeInputSink, FakeClock


def make_test_config(tmp_dir, max_rolls=2, target_colors=None, action_rules=None, regions=None):
    if target_colors is None:
        target_colors = ["purple"]
    if action_rules is None:
        action_rules = {"purple": "stop"}
    if regions is None:
        regions = [{"id": "slot_0", "name": "Slot 0", "x": 10, "y": 10, "w": 50, "h": 50}]

    cfg_file = os.path.join(tmp_dir, "test_cfg.json")
    cfg = ConfigManager(cfg_file)
    cfg.set("max_rolls", max_rolls)
    cfg.set("delay_between_rolls", 0.01)
    cfg.set("delay_random_offset_ms", 0)
    cfg.set("target_colors", target_colors)
    cfg.set("action_rules", action_rules)
    cfg.set("watch_regions", regions)
    cfg.set("roll_button", {"x": 500, "y": 500})
    cfg.set("play_sound", False)
    cfg.set("save_screenshot", False)
    cfg.set("use_animation_detection", False)
    cfg.save()
    return cfg


def make_colored_frame(color_bgr=(180, 20, 140), h=50, w=50):
    """Creates a frame with the given BGR color in the center (simulating purple/etc)."""
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    frame[10:40, 10:40] = color_bgr
    return frame


def make_blank_frame(h=50, w=50):
    """Non-black background frame that has no target color (e.g. gray background)."""
    frame = np.full((h, w, 3), 80, dtype=np.uint8)
    return frame


class TestEngineLoop(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_scenario_a_final_roll_detected(self):
        """
        Test A (E-01):
        Max rolls = 1.
        Initial frame has no target.
        After roll 1, screen shows Purple (target).
        Engine MUST detect the purple and stop with 'target_color_found',
        NOT stop with 'max_rolls_reached' without checking!
        """
        cfg = make_test_config(self.tmp_dir, max_rolls=1, target_colors=["purple"], action_rules={"purple": "stop"})
        fake_capture = FakeFrameSource()
        fake_input = FakeInputSink()

        # Frame 1: initial screen before roll (blank gray)
        # Frame 2: screen after roll 1 (purple item)
        fake_capture.enqueue_frame(make_blank_frame())
        fake_capture.enqueue_frame(make_colored_frame())

        finish_reason = []
        engine = AutoClickEngine(cfg, capture=fake_capture, clicker=fake_input)
        engine.on_finished = lambda reason: finish_reason.append(reason)

        engine.start()
        t0 = time.time()
        while engine.state == EngineState.RUNNING and time.time() - t0 < 2.0:
            time.sleep(0.02)

        self.assertEqual(len(fake_input.clicks), 1, f"Expected exactly 1 roll click, got {len(fake_input.clicks)}")
        self.assertEqual(finish_reason, ["target_color_found"], f"Expected 'target_color_found', got {finish_reason}")

    def test_scenario_b_no_extra_roll_after_all_locked(self):
        """
        Test B (E-02):
        2 slots. Max rolls = 10.
        Slot 0 locks on roll 1.
        Slot 1 locks on roll 2.
        Engine MUST stop with 'all_slots_locked' with exactly 2 clicks, NOT 3 clicks!
        """
        regions = [
            {"id": "slot_0", "name": "Slot 0", "x": 10, "y": 10, "w": 50, "h": 50},
            {"id": "slot_1", "name": "Slot 1", "x": 70, "y": 10, "w": 50, "h": 50},
        ]
        cfg = make_test_config(
            self.tmp_dir,
            max_rolls=10,
            target_colors=["purple"],
            action_rules={"purple": "lock"},
            regions=regions
        )
        fake_capture = FakeFrameSource()
        fake_input = FakeInputSink()

        # Roll 0 (initial): slot 0 blank, slot 1 blank
        fake_capture.enqueue_frame(make_blank_frame())
        fake_capture.enqueue_frame(make_blank_frame())

        # After Roll 1: slot 0 gets purple, slot 1 blank
        fake_capture.enqueue_frame(make_colored_frame())
        fake_capture.enqueue_frame(make_blank_frame())

        # After Roll 2: slot 0 is already locked (skipped), slot 1 gets purple
        fake_capture.enqueue_frame(make_colored_frame())

        finish_reason = []
        engine = AutoClickEngine(cfg, capture=fake_capture, clicker=fake_input)
        engine.on_finished = lambda reason: finish_reason.append(reason)

        engine.start()
        t0 = time.time()
        while engine.state == EngineState.RUNNING and time.time() - t0 < 2.0:
            time.sleep(0.02)

        self.assertEqual(len(fake_input.clicks), 2, f"Expected exactly 2 clicks, got {len(fake_input.clicks)}")
        self.assertEqual(finish_reason, ["all_slots_locked"], f"Expected 'all_slots_locked', got {finish_reason}")

    def test_scenario_c_animation_wait_single_click_during_delay(self):
        """
        Test C (E-03):
        When animation detection is active and frames are changing (spinning),
        the engine must wait for frames to stabilize before scanning or clicking again.
        """
        cfg = make_test_config(self.tmp_dir, max_rolls=2, target_colors=["purple"])
        cfg.set("use_animation_detection", True)
        cfg.set("anim_max_wait", 1.0)
        cfg.save()

        fake_capture = FakeFrameSource()
        fake_input = FakeInputSink()

        # Initial scan: blank
        fake_capture.enqueue_frame(make_blank_frame())
        # After click 1: animation frames changing
        frame_anim_1 = np.full((50, 50, 3), 100, dtype=np.uint8)
        frame_anim_2 = np.full((50, 50, 3), 150, dtype=np.uint8)
        frame_stable_1 = make_colored_frame()
        frame_stable_2 = make_colored_frame()
        fake_capture.enqueue_frames([frame_anim_1, frame_anim_2, frame_stable_1, frame_stable_2, frame_stable_2])

        finish_reason = []
        engine = AutoClickEngine(cfg, capture=fake_capture, clicker=fake_input)
        engine.on_finished = lambda reason: finish_reason.append(reason)

        engine.start()
        t0 = time.time()
        while engine.state == EngineState.RUNNING and time.time() - t0 < 2.0:
            time.sleep(0.02)

        self.assertEqual(len(fake_input.clicks), 1)
        self.assertEqual(finish_reason, ["target_color_found"])

    def test_scenario_d_capture_failure_safe_stop(self):
        """
        Test D (E-04):
        If capture repeatedly fails or produces black frames,
        engine must stop safely with 'capture_failed' rather than continuing blindly.
        """
        cfg = make_test_config(self.tmp_dir, max_rolls=10)
        fake_capture = FakeFrameSource()
        fake_input = FakeInputSink()
        fake_capture.fail_forever = True

        finish_reason = []
        engine = AutoClickEngine(cfg, capture=fake_capture, clicker=fake_input)
        engine.on_finished = lambda reason: finish_reason.append(reason)

        engine.start()
        t0 = time.time()
        while engine.state == EngineState.RUNNING and time.time() - t0 < 2.0:
            time.sleep(0.02)

        self.assertEqual(finish_reason, ["capture_failed"], f"Expected 'capture_failed', got {finish_reason}")
        self.assertEqual(len(fake_input.clicks), 0, "Should not click roll if capture failed immediately")

    def test_scenario_e_empty_targets_refuses_to_run(self):
        """
        Test E (E-07):
        If target_colors is empty, engine MUST NOT roll blindly.
        It should immediately abort and stop safely.
        """
        cfg = make_test_config(self.tmp_dir, max_rolls=10, target_colors=[])
        fake_capture = FakeFrameSource()
        fake_input = FakeInputSink()

        finish_reason = []
        engine = AutoClickEngine(cfg, capture=fake_capture, clicker=fake_input)
        engine.on_finished = lambda reason: finish_reason.append(reason)

        engine.start()
        time.sleep(0.05)

        self.assertEqual(len(fake_input.clicks), 0, "Engine must not click when target_colors is empty")
        self.assertEqual(engine.state, EngineState.STOPPED)
        self.assertEqual(finish_reason, ["no_target_color"])

    def test_scenario_f_window_guard_inactive_pauses(self):
        """
        Test F (E-10):
        If target_window_title is set and window is not active,
        engine must pause automatically to prevent clicking other apps.
        """
        cfg = make_test_config(self.tmp_dir, max_rolls=10)
        cfg.set("target_window_title", "NonExistentGameWindow123456")
        cfg.save()

        fake_capture = FakeFrameSource()
        fake_input = FakeInputSink()
        fake_capture.enqueue_frame(make_blank_frame())

        engine = AutoClickEngine(cfg, capture=fake_capture, clicker=fake_input)
        engine.start()
        time.sleep(0.08)

        self.assertEqual(engine.state, EngineState.PAUSED)
        self.assertEqual(len(fake_input.clicks), 0, "Engine must pause before clicking if window is inactive")
        engine.stop()

    def test_scenario_g_mouse_interference_pauses(self):
        """
        Test G (E-10):
        If user moves mouse far away while bot is running,
        engine must pause to avoid fighting user for the mouse.
        """
        cfg = make_test_config(self.tmp_dir, max_rolls=5)
        cfg.set("guard_mouse_move", True)
        cfg.save()

        fake_capture = FakeFrameSource()
        fake_input = FakeInputSink()
        # Roll 1: blank -> clicks roll
        fake_capture.enqueue_frame(make_blank_frame())
        fake_capture.enqueue_frame(make_blank_frame())

        engine = AutoClickEngine(cfg, capture=fake_capture, clicker=fake_input)
        engine.start()
        time.sleep(0.05)

        # User moves mouse to (999, 999)
        fake_input.current_pos = (999, 999)
        time.sleep(0.08)

        self.assertEqual(engine.state, EngineState.PAUSED)
        engine.stop()


if __name__ == "__main__":
    unittest.main()
