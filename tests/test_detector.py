"""
Unit tests for ColorDetector:
- Speckle noise rejection via morphology
- Tier rarity priority when multiple colors match
- Border-only vs full frame detection
- Confidence score and decision levels
"""
import unittest
import numpy as np
import cv2

from core.detector import ColorDetector
from core.config_manager import DEFAULT_COLOR_DEFINITIONS


class TestColorDetector(unittest.TestCase):
    def setUp(self):
        self.detector = ColorDetector(DEFAULT_COLOR_DEFINITIONS, default_threshold_percent=1.0)

    def test_single_color_detection(self):
        # 100x100 canvas, purple box in center (50x50 = 25%)
        # Purple in BGR: B=180, G=20, R=140
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[25:75, 25:75] = [180, 20, 140]

        res = self.detector.analyze_image(img, target_colors=["purple", "red"])
        self.assertTrue(res["detected"])
        self.assertEqual(res["matched_color"], "purple")
        self.assertGreater(res["matched_percent"], 20.0)
        self.assertEqual(res["decision"], "CONFIDENT")
        self.assertGreaterEqual(res["confidence"], 0.8)

    def test_speckle_noise_filtering(self):
        # 100x100 canvas with a few scattered single pixels of purple (noise)
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        # 4 isolated single pixels
        img[10, 10] = [180, 20, 140]
        img[30, 70] = [180, 20, 140]
        img[80, 20] = [180, 20, 140]
        img[90, 90] = [180, 20, 140]

        res = self.detector.analyze_image(img, target_colors=["purple"], threshold_percent=0.01)
        # Morphology 3x3 open should completely wipe single-pixel noise
        self.assertFalse(res["detected"])
        self.assertEqual(res["matched_percent"], 0.0)

    def test_rarity_priority_when_multiple_colors_match(self):
        # Image contains both:
        # - Red (Mythic / Priority 1): 5% area (20x25 = 500 px)
        # - Blue (Rare / Priority 4): 20% area (40x50 = 2000 px)
        # In BGR: Red = [0, 0, 220], Blue = [200, 100, 20]
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        # Blue patch
        img[10:50, 10:60] = [200, 100, 20]
        # Red patch
        img[60:80, 60:85] = [0, 0, 220]

        res = self.detector.analyze_image(img, target_colors=["blue", "red"])
        self.assertTrue(res["detected"])
        # Even though blue has much more area (20%), Red is Mythic (Priority 1) so it MUST be selected!
        self.assertEqual(res["matched_color"], "red")

    def test_border_only_mode(self):
        # Card with illustration in center (purple) and green border
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        # Center has purple (30:70, 30:70)
        img[30:70, 30:70] = [180, 20, 140]

        # 1. Without border_only: purple is detected
        res_full = self.detector.analyze_image(img, target_colors=["purple"], border_only=False)
        self.assertTrue(res_full["detected"])

        # 2. With border_only: center illustration is ignored!
        res_border = self.detector.analyze_image(img, target_colors=["purple"], border_only=True)
        self.assertFalse(res_border["detected"])


if __name__ == "__main__":
    unittest.main()
