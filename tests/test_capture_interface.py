"""
Unit tests cho Frame Contract và FrameSource interface (Phase 0 - V0-T6).
Kiểm thử tính đúng đắn của Frame, FrameStatus, to_frame helper, và sự tuân thủ
của ScreenCapture cùng FakeFrameSource đối với FrameSource interface.
"""
import unittest
import numpy as np
import time

from core.capture_interface import Frame, FrameSource, FrameStatus, to_frame
from tests.fakes import FakeFrameSource
from core.capture import ScreenCapture, _Backend


class DummyBackend(_Backend):
    name = "dummy"

    def available(self) -> bool:
        return True

    def grab(self, x: int, y: int, w: int, h: int) -> np.ndarray:
        return np.full((h, w, 3), 120, dtype=np.uint8)


class TestCaptureInterface(unittest.TestCase):

    def test_frame_contract_creation(self):
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        frame = Frame(
            image=img,
            frame_id=1,
            timestamp=123.456,
            client_size=(200, 100),
            geometry_version=1,
            backend="test",
            status=FrameStatus.VALID,
        )
        self.assertTrue(frame.is_valid)
        self.assertEqual(frame.shape, (100, 200, 3))
        self.assertEqual(frame.frame_id, 1)
        self.assertEqual(frame.backend, "test")

    def test_frame_contract_invalid_empty(self):
        frame = Frame(image=None, frame_id=2, status=FrameStatus.CAPTURE_ERROR)
        self.assertFalse(frame.is_valid)
        self.assertEqual(frame.shape, (0, 0, 0))

    def test_to_frame_helper(self):
        img = np.ones((50, 60, 3), dtype=np.uint8) * 200
        f = to_frame(img, frame_id=10, backend="wgc", client_size=(60, 50))
        self.assertTrue(f.is_valid)
        self.assertEqual(f.frame_id, 10)
        self.assertEqual(f.client_size, (60, 50))

        empty_f = to_frame(None, frame_id=11)
        self.assertFalse(empty_f.is_valid)
        self.assertEqual(empty_f.status, FrameStatus.EMPTY)

    def test_fake_frame_source_compliance(self):
        source = FakeFrameSource(default_shape=(60, 80, 3))
        self.assertIsInstance(source, FrameSource)
        self.assertTrue(source.start())

        # Test latest()
        f1 = source.latest()
        self.assertIsInstance(f1, Frame)
        self.assertTrue(f1.is_valid)
        self.assertEqual(f1.shape, (60, 80, 3))
        self.assertEqual(f1.frame_id, 1)

        # Enqueue custom frame
        custom = np.full((60, 80, 3), 255, dtype=np.uint8)
        source.enqueue_frame(custom)
        f2 = source.latest()
        self.assertEqual(f2.frame_id, 2)
        self.assertEqual(int(f2.image[0, 0, 0]), 255)

        # Test capture_region backward compatibility (FakeFrameSource returns default_shape or custom frame)
        crop = source.capture_region(10, 10, 20, 20)
        self.assertEqual(crop.shape, (60, 80, 3))

        source.stop()

    def test_screen_capture_compliance(self):
        cap = ScreenCapture(backends=[DummyBackend()])
        self.assertIsInstance(cap, FrameSource)
        self.assertTrue(cap.start())

        # latest()
        frame = cap.latest()
        self.assertIsInstance(frame, Frame)
        self.assertTrue(frame.is_valid)
        self.assertGreater(frame.frame_id, 0)

        # capture_region legacy API
        crop = cap.capture_region(0, 0, 50, 50)
        self.assertEqual(crop.shape, (50, 50, 3))

        cap.stop()


if __name__ == "__main__":
    unittest.main()
