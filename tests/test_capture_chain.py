"""Chuỗi backend chụp màn hình: hạ cấp, ảnh đen, nghỉ khi lỗi, chụp gộp nhiều slot."""
import unittest
import numpy as np

from core.capture import ScreenCapture, CaptureError, BackendUnavailable, _Backend


class FakeBackend(_Backend):
    def __init__(self, name, mode="ok"):
        self.name = name
        self.mode = mode          # ok | black | raise | unavailable
        self.calls = 0
        self.screen = np.random.default_rng(1).integers(1, 255, (400, 600, 3), dtype=np.uint8)

    def available(self):
        return True

    def grab(self, x, y, w, h):
        self.calls += 1
        if self.mode == "raise":
            raise RuntimeError("boom")
        if self.mode == "unavailable":
            raise BackendUnavailable("ngoài màn hình chính")
        if self.mode == "black":
            return np.zeros((h, w, 3), np.uint8)
        return self.screen[y:y + h, x:x + w].copy()


class TestCaptureChain(unittest.TestCase):
    def test_black_frame_falls_back_to_next_backend(self):
        a, b = FakeBackend("dxgi", "black"), FakeBackend("mss", "ok")
        cap = ScreenCapture(backends=[a, b])
        img = cap.capture_region(10, 10, 50, 50)
        self.assertTrue(img.any())
        self.assertEqual(cap.active_backend, "mss")
        self.assertEqual(cap.stats()["dxgi"]["black"], 1)

    def test_all_black_raises_with_exclusive_fullscreen_hint(self):
        cap = ScreenCapture(backends=[FakeBackend("dxgi", "black"), FakeBackend("mss", "black")])
        with self.assertRaises(CaptureError) as cm:
            cap.capture_region(0, 0, 20, 20)
        self.assertIn("Borderless", str(cm.exception))

    def test_unavailable_is_not_penalised(self):
        a, b = FakeBackend("dxgi", "unavailable"), FakeBackend("mss", "ok")
        cap = ScreenCapture(backends=[a, b])
        for _ in range(10):
            cap.capture_region(0, 0, 20, 20)
        self.assertEqual(a.calls, 10)            # vẫn được thử mỗi lần (không bị nghỉ)

    def test_failing_backend_gets_cooldown_after_3_errors(self):
        a, b = FakeBackend("dxgi", "raise"), FakeBackend("mss", "ok")
        cap = ScreenCapture(backends=[a, b])
        for _ in range(8):
            cap.capture_region(0, 0, 20, 20)
        self.assertEqual(a.calls, 3)             # sau 3 lỗi liên tiếp bị nghỉ, không bị gọi nữa
        self.assertEqual(b.calls, 8)

    def test_capture_regions_crops_from_single_grab_and_matches_individual(self):
        be = FakeBackend("mss", "ok")
        cap = ScreenCapture(backends=[be])
        rects = [(100, 100, 80, 80), (200, 100, 80, 80)]
        imgs = cap.capture_regions(rects)
        self.assertEqual(be.calls, 1)            # MỘT lần grab cho hai slot
        for (x, y, w, h), im in zip(rects, imgs):
            np.testing.assert_array_equal(im, be.screen[y:y + h, x:x + w])
            self.assertTrue(im.flags["C_CONTIGUOUS"])

    def test_far_apart_regions_are_grabbed_separately(self):
        be = FakeBackend("mss", "ok")
        cap = ScreenCapture(backends=[be])
        cap.capture_regions([(0, 0, 30, 30), (560, 360, 30, 30)])
        self.assertEqual(be.calls, 2)

    def test_invalid_region_raises_value_error(self):
        cap = ScreenCapture(backends=[FakeBackend("mss")])
        with self.assertRaises(ValueError):
            cap.capture_region(0, 0, 0, 10)


if __name__ == "__main__":
    unittest.main()
