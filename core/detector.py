import cv2
import numpy as np
from typing import Dict, Any, List, Optional, Tuple


BUILTIN_COLORS = {
    "purple": {"name": "Tím (Epic)", "h_min": 125, "h_max": 160, "s_min": 50, "s_max": 255, "v_min": 50, "v_max": 255},
    "red": {"name": "Đỏ (Mythic)", "h_min": 0, "h_max": 10, "h2_min": 170, "h2_max": 180, "s_min": 70, "s_max": 255, "v_min": 50, "v_max": 255},
    "gold": {"name": "Vàng (Legendary)", "h_min": 18, "h_max": 35, "s_min": 75, "s_max": 255, "v_min": 75, "v_max": 255},
    "blue": {"name": "Xanh dương (Rare)", "h_min": 95, "h_max": 125, "s_min": 60, "s_max": 255, "v_min": 50, "v_max": 255},
    "green": {"name": "Xanh lá (Uncommon)", "h_min": 35, "h_max": 85, "s_min": 60, "s_max": 255, "v_min": 50, "v_max": 255},
}


class ColorDetector:
    """
    Detects target colors in an image using OpenCV and HSV color space.
    Supports border-only filtering for card rarity outlines and custom sampled colors.
    """

    def __init__(self, color_definitions: Optional[Dict[str, Dict[str, Any]]] = None,
                 default_threshold_percent: float = 1.0, custom_colors: Optional[dict] = None):
        self.threshold_percent = default_threshold_percent
        self.color_definitions = dict(BUILTIN_COLORS)
        extra = color_definitions or custom_colors or {}
        self.color_definitions.update(extra)

    def update_definitions(self, color_definitions: Dict[str, Dict[str, Any]], threshold_percent: Optional[float] = None):
        self.color_definitions.update(color_definitions)
        if threshold_percent is not None:
            self.threshold_percent = threshold_percent

    def _create_color_mask(self, hsv_img: np.ndarray, color_rule: Dict[str, Any]) -> np.ndarray:
        """Creates a binary mask where pixels matching the HSV range are 255."""
        h_min = int(color_rule.get("h_min", 0))
        h_max = int(color_rule.get("h_max", 180))
        s_min = int(color_rule.get("s_min", 0))
        s_max = int(color_rule.get("s_max", 255))
        v_min = int(color_rule.get("v_min", 0))
        v_max = int(color_rule.get("v_max", 255))

        lower = np.array([h_min, s_min, v_min], dtype=np.uint8)
        upper = np.array([h_max, s_max, v_max], dtype=np.uint8)
        mask = cv2.inRange(hsv_img, lower, upper)

        # Handling wrap-around for colors like Red (0-10 and 170-180)
        if "h2_min" in color_rule and "h2_max" in color_rule:
            h2_min = int(color_rule["h2_min"])
            h2_max = int(color_rule["h2_max"])
            lower2 = np.array([h2_min, s_min, v_min], dtype=np.uint8)
            upper2 = np.array([h2_max, s_max, v_max], dtype=np.uint8)
            mask2 = cv2.inRange(hsv_img, lower2, upper2)
            mask = cv2.bitwise_or(mask, mask2)

        return mask

    def detect_colors(
        self,
        img_bgr: np.ndarray,
        target_colors: List[str],
        threshold_percent: float = 1.0,
        border_only: bool = False,
        border_ratio: float = 0.18
    ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, np.ndarray]]:
        """
        Detect colors and return matches dict + masks dict (used by TestInspectorDialog).
        Supports border_only mode to isolate card frames from inner illustrations.
        """
        matches: Dict[str, Dict[str, Any]] = {}
        masks: Dict[str, np.ndarray] = {}

        if img_bgr is None or img_bgr.size == 0:
            return matches, masks

        h, w = img_bgr.shape[:2]
        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

        # Tạo mặt nạ viền ngoài nếu border_only được bật
        border_mask = None
        if border_only and h > 10 and w > 10:
            border_mask = np.zeros((h, w), dtype=np.uint8)
            bw = max(2, int(w * border_ratio))
            bh = max(2, int(h * border_ratio))
            border_mask[:bh, :] = 255
            border_mask[-bh:, :] = 255
            border_mask[:, :bw] = 255
            border_mask[:, -bw:] = 255
            total_active_pixels = cv2.countNonZero(border_mask)
        else:
            total_active_pixels = h * w

        if total_active_pixels == 0:
            total_active_pixels = 1

        for color_key in target_colors:
            if color_key not in self.color_definitions:
                continue

            rule = self.color_definitions[color_key]
            mask = self._create_color_mask(hsv, rule)

            if border_mask is not None:
                mask = cv2.bitwise_and(mask, border_mask)

            matched_count = cv2.countNonZero(mask)
            percent = (matched_count / total_active_pixels) * 100.0

            matches[color_key] = {
                "matched": (percent >= threshold_percent),
                "percent": round(percent, 2),
                "count": matched_count,
                "name": rule.get("name", color_key),
            }
            masks[color_key] = mask

        return matches, masks

    def analyze_image(
        self,
        img_bgr: np.ndarray,
        target_colors: List[str],
        threshold_percent: Optional[float] = None,
        border_only: bool = False
    ) -> Dict[str, Any]:
        """
        Analyzes an image and checks if any of the target colors exceed the threshold.
        """
        threshold = self.threshold_percent if threshold_percent is None else threshold_percent

        if img_bgr is None or img_bgr.size == 0:
            return {
                "detected": False,
                "matched_color": None,
                "matched_name": None,
                "matched_percent": 0.0,
                "all_percentages": {},
                "total_pixels": 0
            }

        matches, _ = self.detect_colors(img_bgr, target_colors, threshold, border_only=border_only)

        all_percentages = {}
        detected = False
        primary_match_color = None
        primary_match_name = None
        highest_percent = 0.0

        for color_key, m in matches.items():
            pct = m["percent"]
            all_percentages[color_key] = pct
            if m["matched"]:
                detected = True
                if pct > highest_percent:
                    highest_percent = pct
                    primary_match_color = color_key
                    primary_match_name = m["name"]

        h, w = img_bgr.shape[:2]
        return {
            "detected": detected,
            "matched_color": primary_match_color,
            "matched_name": primary_match_name,
            "matched_percent": round(highest_percent, 2),
            "all_percentages": all_percentages,
            "total_pixels": h * w
        }

    def get_annotated_result(self, img_bgr: np.ndarray, matched_color: str) -> np.ndarray:
        """Returns image with bounding boxes around detected color patches for visual proof."""
        if matched_color not in self.color_definitions or img_bgr is None:
            return img_bgr

        annotated = img_bgr.copy()
        hsv = cv2.cvtColor(annotated, cv2.COLOR_BGR2HSV)
        rule = self.color_definitions[matched_color]
        mask = self._create_color_mask(hsv, rule)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        mask_clean = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            if cv2.contourArea(cnt) > 20:
                x, y, w, h = cv2.boundingRect(cnt)
                cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 2)

        return annotated
