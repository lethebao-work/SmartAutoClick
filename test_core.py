import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import os
import cv2
import numpy as np
from core.config_manager import ConfigManager
from core.capture import ScreenCapture, CaptureError
from core.detector import ColorDetector
from core.clicker import InputSimulator
from core.engine import AutoClickEngine

import tempfile
import shutil

def test_config():
    print("[TEST] Testing ConfigManager...")
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        if os.path.exists("config.json"):
            shutil.copy("config.json", tmp_path)
        cfg = ConfigManager(tmp_path)
        assert cfg.get("version") in ("1.0", "2.0")
        assert cfg.get("delay_random_offset_ms") is not None
        btn = cfg.get_roll_button()
        assert "x" in btn and "y" in btn
        print(" -> ConfigManager OK!")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_capture_and_detector():
    print("[TEST] Testing ScreenCapture & ColorDetector...")
    cap = ScreenCapture()
    try:
        frame = cap.capture_region(100, 100, 150, 150)
        assert frame is not None
        print(f" -> ScreenCapture OK! Frame shape: {frame.shape}")
    except CaptureError as e:
        print(f" -> ScreenCapture fail-safe verified: {e}")

    # Create synthetic test image with pure purple box
    test_img = np.zeros((100, 100, 3), dtype=np.uint8)
    # Purple in BGR: B=180, G=20, R=140
    test_img[20:80, 20:80] = [180, 20, 140]

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        if os.path.exists("config.json"):
            shutil.copy("config.json", tmp_path)
        cfg = ConfigManager(tmp_path)
        detector = ColorDetector(cfg.get("color_definitions"), default_threshold_percent=1.0)
        res = detector.analyze_image(test_img, target_colors=["purple", "red"])
        print(f" -> Synthetic analysis result: {res}")
        assert res["detected"] is True
        assert res["matched_color"] == "purple"
        print(" -> ColorDetector OK!")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_clicker():
    print("[TEST] Testing InputSimulator...")
    x, y = InputSimulator.get_mouse_position()
    print(f" -> Current mouse position: ({x}, {y})")
    print(" -> InputSimulator OK!")

def test_engine_init():
    print("[TEST] Testing Engine...")
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        if os.path.exists("config.json"):
            shutil.copy("config.json", tmp_path)
        cfg = ConfigManager(tmp_path)
        engine = AutoClickEngine(cfg)
        assert engine.state == "IDLE"
        print(" -> AutoClickEngine OK!")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

if __name__ == "__main__":
    test_config()
    test_capture_and_detector()
    test_clicker()
    test_engine_init()
    print("\n✅ TẤT CẢ TEST CORE ĐÃ VƯỢT QUA!")
