"""
Engine + đồng bộ khung hình + xác nhận nhiều khung + chính sách UNCERTAIN.
"""
import os
import shutil
import tempfile
import time
import unittest

import numpy as np

from core.engine import AutoClickEngine, EngineState
from tests.fakes import FakeFrameSource, FakeInputSink
from tests.test_engine_loop import make_test_config, make_blank_frame, make_colored_frame


def run_engine(cfg, frames, timeout=4.0):
    cap, inp = FakeFrameSource(), FakeInputSink()
    cap.enqueue_frames(frames)
    reasons = []
    eng = AutoClickEngine(cfg, capture=cap, clicker=inp)
    eng.on_finished = lambda r: reasons.append(r)
    eng.start()
    t0 = time.time()
    while eng.state == EngineState.RUNNING and time.time() - t0 < timeout:
        time.sleep(0.01)
    finished = list(reasons)      # chụp lý do TRƯỚC khi stop() (stop() bắn thêm 'user_stopped')
    if eng.state == EngineState.RUNNING:
        eng.stop()
    return finished, inp


def small_patch_frame(px=4):
    """Mảng màu tím chỉ ~0.64% diện tích: dưới ngưỡng 1% nhưng trên 40% ngưỡng -> UNCERTAIN."""
    f = make_blank_frame()
    f[20:20 + px, 20:20 + px] = (180, 20, 140)
    return f


class TestFrameGating(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def anim_cfg(self, **over):
        cfg = make_test_config(self.tmp, max_rolls=5, target_colors=["purple"], action_rules={"purple": "stop"})
        cfg.set("use_animation_detection", True)
        cfg.set("anim_max_wait", 3.0)
        cfg.set("anim_stable_ms", 100)
        cfg.set("settle_poll_ms", 5)
        cfg.set("anim_post_delay", 0.0)
        for k, v in over.items():
            cfg.set(k, v)
        cfg.save()
        return cfg

    def test_slow_game_response_is_not_read_as_stale_frame(self):
        """Game trễ ~100ms: phải chờ kết quả MỚI, chỉ click đúng 1 lần (bản cũ click lần 2 vì đọc ảnh cũ)."""
        cfg = self.anim_cfg()
        frames = [make_blank_frame()] + [make_blank_frame()] * 20 \
            + [np.full((50, 50, 3), 150, np.uint8)] + [make_colored_frame()] * 3
        reasons, inp = run_engine(cfg, frames)
        self.assertEqual(len(inp.clicks), 1)
        self.assertEqual(reasons, ["target_color_found"])

    def test_no_response_after_click_stops_instead_of_rolling_blind(self):
        cfg = self.anim_cfg(anim_first_change_timeout=0.2)
        reasons, inp = run_engine(cfg, [make_blank_frame()])
        self.assertEqual(reasons, ["no_response"])
        self.assertEqual(len(inp.clicks), 1)

    def test_no_response_policy_scan_keeps_old_behaviour(self):
        cfg = self.anim_cfg(anim_first_change_timeout=0.1, on_settle_failure="scan")
        cfg.set("max_rolls", 2); cfg.save()
        reasons, inp = run_engine(cfg, [make_blank_frame()])
        self.assertEqual(reasons, ["max_rolls_reached"])
        self.assertEqual(len(inp.clicks), 2)

    def test_settle_timeout_stops_instead_of_clicking_over_result(self):
        cfg = self.anim_cfg(anim_max_wait=0.3)
        spin = [np.full((50, 50, 3), 60 + (i % 2) * 120, np.uint8) for i in range(400)]
        reasons, inp = run_engine(cfg, [make_blank_frame()] + spin)
        self.assertEqual(reasons, ["settle_timeout"])
        self.assertEqual(len(inp.clicks), 1)

    def test_uncertain_color_stops_for_manual_check(self):
        cfg = make_test_config(self.tmp, max_rolls=5, target_colors=["purple"], action_rules={"purple": "stop"})
        reasons, inp = run_engine(cfg, [small_patch_frame()])
        self.assertEqual(reasons, ["uncertain_detection"])
        self.assertEqual(len(inp.clicks), 0)

    def test_uncertain_policy_ignore_keeps_rolling(self):
        cfg = make_test_config(self.tmp, max_rolls=2, target_colors=["purple"], action_rules={"purple": "stop"})
        cfg.set("uncertain_policy", "ignore"); cfg.save()
        reasons, inp = run_engine(cfg, [small_patch_frame()])
        self.assertEqual(reasons, ["max_rolls_reached"])

    def test_flickering_detection_is_not_trusted(self):
        """Khung 1 thấy tím, khung xác nhận không thấy -> không nhất quán -> dừng, không click đè."""
        cfg = make_test_config(self.tmp, max_rolls=5, target_colors=["purple"], action_rules={"purple": "stop"})
        cfg.set("confirm_frames", 2); cfg.save()
        reasons, inp = run_engine(cfg, [make_blank_frame(), make_colored_frame(), make_blank_frame()])
        self.assertEqual(reasons, ["uncertain_detection"])
        self.assertEqual(len(inp.clicks), 1)

    def test_confirmed_detection_stops_normally(self):
        cfg = make_test_config(self.tmp, max_rolls=5, target_colors=["purple"], action_rules={"purple": "stop"})
        cfg.set("confirm_frames", 3); cfg.save()
        reasons, inp = run_engine(cfg, [make_blank_frame(), make_colored_frame(), make_colored_frame(), make_colored_frame()])
        self.assertEqual(reasons, ["target_color_found"])


if __name__ == "__main__":
    unittest.main()
