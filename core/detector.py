import cv2
import numpy as np
import time
from typing import Dict, Any, List, Optional, Tuple


from core.config_manager import DEFAULT_COLOR_DEFINITIONS as BUILTIN_COLORS


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
        h_min = max(0, min(179, int(color_rule.get("h_min", 0))))
        h_max = max(0, min(179, int(color_rule.get("h_max", 179))))
        s_min = max(0, min(255, int(color_rule.get("s_min", 0))))
        s_max = max(0, min(255, int(color_rule.get("s_max", 255))))
        v_min = max(0, min(255, int(color_rule.get("v_min", 0))))
        v_max = max(0, min(255, int(color_rule.get("v_max", 255))))

        lower = np.array([h_min, s_min, v_min], dtype=np.uint8)
        upper = np.array([h_max, s_max, v_max], dtype=np.uint8)
        mask = cv2.inRange(hsv_img, lower, upper)

        # Handling wrap-around for colors like Red (0-10 and 170-179)
        if "h2_min" in color_rule and "h2_max" in color_rule:
            h2_min = max(0, min(179, int(color_rule["h2_min"])))
            h2_max = max(0, min(179, int(color_rule["h2_max"])))
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

            # Filter out single-pixel noise / small speckles
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            mask_clean = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

            matched_count = cv2.countNonZero(mask_clean)
            percent = (matched_count / total_active_pixels) * 100.0

            # Confidence calculation (0.0 to 1.0)
            confidence = min(1.0, percent / max(0.1, threshold_percent * 2.0))
            if percent >= threshold_percent:
                decision = "CONFIDENT"
            elif percent >= threshold_percent * 0.4:
                decision = "UNCERTAIN"
            else:
                decision = "NO"

            matches[color_key] = {
                "matched": (percent >= threshold_percent),
                "percent": round(percent, 2),
                "count": matched_count,
                "confidence": round(confidence, 2),
                "decision": decision,
                "name": rule.get("name", color_key),
            }
            masks[color_key] = mask_clean

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
                "confidence": 0.0,
                "decision": "NO",
                "uncertain_color": None,
                "uncertain_name": None,
                "uncertain_percent": 0.0,
                "all_percentages": {},
                "total_pixels": 0
            }

        matches, _ = self.detect_colors(img_bgr, target_colors, threshold, border_only=border_only)

        all_percentages = {}
        detected = False
        primary_match_color = None
        primary_match_name = None
        highest_percent = 0.0
        best_priority = 999
        primary_confidence = 0.0
        primary_decision = "NO"
        # Màu chưa đủ ngưỡng nhưng đáng ngờ (>= 40% ngưỡng): KHÔNG được coi là "không có"
        uncertain_color = None
        uncertain_name = None
        uncertain_percent = 0.0

        # Tier priority: lower number = rarer = higher priority
        COLOR_PRIORITY = {
            "red": 1,
            "gold": 2,
            "purple": 3,
            "blue": 4,
            "green": 5
        }

        for color_key, m in matches.items():
            pct = m["percent"]
            all_percentages[color_key] = pct
            if not m["matched"] and m["decision"] == "UNCERTAIN":
                if uncertain_color is None or COLOR_PRIORITY.get(color_key, 50) < COLOR_PRIORITY.get(uncertain_color, 50):
                    uncertain_color, uncertain_name, uncertain_percent = color_key, m["name"], pct
            if m["matched"]:
                detected = True
                prio = COLOR_PRIORITY.get(color_key, 50)
                # Select rarer tier first; if same tier, select higher percentage
                if prio < best_priority or (prio == best_priority and pct > highest_percent):
                    best_priority = prio
                    highest_percent = pct
                    primary_match_color = color_key
                    primary_match_name = m["name"]
                    primary_confidence = m["confidence"]
                    primary_decision = m["decision"]

        if not detected and uncertain_color is not None:
            primary_decision = "UNCERTAIN"

        h, w = img_bgr.shape[:2]
        return {
            "uncertain_color": uncertain_color,
            "uncertain_name": uncertain_name,
            "uncertain_percent": round(uncertain_percent, 2),
            "detected": detected,
            "matched_color": primary_match_color,
            "matched_name": primary_match_name,
            "matched_percent": round(highest_percent, 2),
            "confidence": primary_confidence,
            "decision": primary_decision,
            "all_percentages": all_percentages,
            "total_pixels": h * w
        }

    def get_annotated_result(self, img_bgr: np.ndarray, matched_color: str, border_only: bool = False) -> np.ndarray:
        """Returns image with bounding boxes around detected color patches for visual proof."""
        if matched_color not in self.color_definitions or img_bgr is None:
            return img_bgr

        annotated = img_bgr.copy()
        matches, masks = self.detect_colors(img_bgr, [matched_color], threshold_percent=0.1, border_only=border_only)
        mask_clean = masks.get(matched_color)
        if mask_clean is None:
            return annotated

        contours, _ = cv2.findContours(mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            if cv2.contourArea(cnt) >= 15:
                x, y, w, h = cv2.boundingRect(cnt)
                cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 2)

        return annotated

    def observe(
        self,
        frame: Any,
        target_colors: List[str],
        region: Optional[Tuple[int, int, int, int]] = None,
        threshold_percent: Optional[float] = None,
        border_only: bool = False,
    ) -> "Observation":
        """
        Quan sát hình ảnh và chuyển đổi kết quả nhận diện thành Observation Contract (V3-T9 & V3-T10).
        Không quyết định click hay dừng (để cho Decision Engine).
        """
        from core.capture_interface import Frame
        from core.observation import Observation, ObservationStatus, DetectedObject

        if isinstance(frame, Frame):
            frame_id = frame.frame_id
            geom_ver = frame.geometry_version
            ts = frame.timestamp
            img = frame.image
        else:
            frame_id = 0
            geom_ver = 1
            ts = time.monotonic()
            img = frame

        if img is None or img.size == 0:
            return Observation(
                frame_id=frame_id,
                geometry_version=geom_ver,
                timestamp=ts,
                status=ObservationStatus.FRAME_INVALID,
                confidence=0.0,
            )

        # Cắt ROI nếu được yêu cầu
        if region is not None:
            rx, ry, rw, rh = region
            h, w = img.shape[:2]
            x0, y0 = max(0, rx), max(0, ry)
            x1, y1 = min(w, x0 + rw), min(h, y0 + rh)
            if x1 <= x0 or y1 <= y0:
                crop = img
            else:
                crop = img[y0:y1, x0:x1]
        else:
            crop = img

        analysis = self.analyze_image(crop, target_colors=target_colors, threshold_percent=threshold_percent, border_only=border_only)

        detected_objects = []
        if analysis["detected"] and analysis["matched_color"]:
            color = analysis["matched_color"]
            obj = DetectedObject(
                label=color,
                confidence=analysis["confidence"],
                coverage_percent=analysis["matched_percent"],
                bounding_box=region or (0, 0, crop.shape[1], crop.shape[0]),
                raw_data={"color_name": analysis["matched_name"], "percentages": analysis["all_percentages"]},
            )
            detected_objects.append(obj)
            status = ObservationStatus.VALID
        elif analysis["decision"] == "UNCERTAIN":
            color = analysis.get("uncertain_color", "unknown")
            obj = DetectedObject(
                label=str(color),
                confidence=0.4,
                coverage_percent=analysis.get("uncertain_percent", 0.0),
                bounding_box=region or (0, 0, crop.shape[1], crop.shape[0]),
                raw_data={"color_name": analysis.get("uncertain_name", ""), "uncertain": True},
            )
            detected_objects.append(obj)
            status = ObservationStatus.UNCERTAIN
        else:
            status = ObservationStatus.NOT_FOUND

        return Observation(
            frame_id=frame_id,
            geometry_version=geom_ver,
            timestamp=ts,
            detected_objects=detected_objects,
            confidence=analysis["confidence"] if detected_objects else 0.0,
            status=status,
            evidence={
                "all_percentages": analysis.get("all_percentages", {}),
                "matched_color": analysis.get("matched_color"),
                "matched_percent": analysis.get("matched_percent", 0.0),
            },
        )
