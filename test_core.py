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
from core.capture import ScreenCapture
from core.detector import ColorDetector
from core.clicker import InputSimulator
from core.engine import AutoClickEngine

def test_config():
    print("[TEST] Testing ConfigManager...")
    cfg = ConfigManager("config.json")
    assert cfg.get("version") in ("1.0", "2.0")
    assert cfg.get("delay_random_offset_ms") is not None
    btn = cfg.get_roll_button()
    assert "x" in btn and "y" in btn
    print(" -> ConfigManager OK!")

def test_capture_and_detector():
    print("[TEST] Testing ScreenCapture & ColorDetector...")
    cap = ScreenCapture()
    frame = cap.capture_region(100, 100, 150, 150)
    assert frame is not None
    assert frame.shape == (150, 150, 3)
    print(f" -> ScreenCapture OK! Frame shape: {frame.shape}")

    # Create synthetic test image with pure purple box
    test_img = np.zeros((100, 100, 3), dtype=np.uint8)
    # Purple in BGR: B=180, G=20, R=140
    test_img[20:80, 20:80] = [180, 20, 140]

    cfg = ConfigManager("config.json")
    detector = ColorDetector(cfg.get("color_definitions"), default_threshold_percent=1.0)
    res = detector.analyze_image(test_img, target_colors=["purple", "red"])
    print(f" -> Synthetic analysis result: {res}")
    assert res["detected"] is True
    assert res["matched_color"] == "purple"
    print(" -> ColorDetector OK!")

def test_clicker():
    print("[TEST] Testing InputSimulator...")
    x, y = InputSimulator.get_mouse_position()
    print(f" -> Current mouse position: ({x}, {y})")
    print(" -> InputSimulator OK!")

def test_engine_init():
    print("[TEST] Testing Engine...")
    cfg = ConfigManager("config.json")
    engine = AutoClickEngine(cfg)
    assert engine.state == "IDLE"
    print(" -> AutoClickEngine OK!")

if __name__ == "__main__":
    test_config()
    test_capture_and_detector()
    test_clicker()
    test_engine_init()
    print("\n✅ TẤT CẢ TEST CORE ĐÃ VƯỢT QUA!")
