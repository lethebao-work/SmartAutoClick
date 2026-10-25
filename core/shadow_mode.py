"""
Chế độ Shadow Mode & So sánh quyết định song song (Shadow Mode Evaluator)
cho SmartAutoClick v3.1 (Phase 6 - V6-T7 đến V6-T10).

Tính năng:
- V6-T7: Engine mới quan sát & đánh giá quyết định song song với engine cũ nhưng TUYỆT ĐỐI KHÔNG CLICK.
- V6-T8: So sánh quyết định giữa logic cũ (RuleEngine/threshold) và logic mới (Observation/FSM).
- V6-T9: Ghi nhận log chi tiết các trường hợp mâu thuẫn / bất đồng quyết định để phân tích.
- V6-T10: Cho phép fallback / rollback an toàn nếu điều kiện mới không đáp ứng.
"""
from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from core.capture_interface import Frame
from core.observation import Observation
from core.detector import ColorDetector


@dataclass
class ShadowDecisionComparison:
    """Kết quả so sánh giữa engine cũ và engine mới trên cùng frame."""
    frame_id: int
    timestamp: float
    legacy_decision: str       # "stop", "lock", "continue", "uncertain"
    shadow_decision: str       # "stop", "lock", "continue", "uncertain"
    is_agreement: bool
    legacy_color: Optional[str] = None
    shadow_color: Optional[str] = None
    confidence: float = 0.0
    details: str = ""


class ShadowModeEvaluator:
    """
    Chạy engine quan sát ngầm không can thiệp thao tác click thật.
    """

    def __init__(self, target_colors: List[str], action_rules: Dict[str, str]):
        self.target_colors = target_colors
        self.action_rules = action_rules
        self.detector = ColorDetector()
        self.comparison_history: List[ShadowDecisionComparison] = []
        self.disagreements: List[ShadowDecisionComparison] = []

    def evaluate_frame(
        self,
        frame: Frame,
        region: Optional[Tuple[int, int, int, int]] = None,
    ) -> ShadowDecisionComparison:
        """
        Thực hiện đánh giá kép (Dual Evaluation) trên cùng frame.
        """
        img = frame.image
        if img is None or img.size == 0:
            return ShadowDecisionComparison(
                frame_id=frame.frame_id,
                timestamp=time.monotonic(),
                legacy_decision="skip",
                shadow_decision="skip",
                is_agreement=True,
                details="Ảnh rỗng",
            )

        # 1. Logic cũ (legacy analysis)
        if region:
            rx, ry, rw, rh = region
            crop = img[ry:ry + rh, rx:rx + rw]
        else:
            crop = img
        legacy_res = self.detector.analyze_image(crop, target_colors=self.target_colors)

        legacy_color = legacy_res.get("matched_color")
        if legacy_res.get("detected") and legacy_color:
            legacy_action = self.action_rules.get(legacy_color, "stop")
        elif legacy_res.get("decision") == "UNCERTAIN":
            legacy_action = "uncertain"
        else:
            legacy_action = "continue"

        # 2. Logic mới (Observation Layer & Decision Engine - V6-T7)
        obs = self.detector.observe(frame, target_colors=self.target_colors, region=region)
        shadow_obj = obs.detected_objects[0] if obs.detected_objects else None
        if shadow_obj and obs.is_reliable:
            shadow_color = shadow_obj.label
            shadow_action = self.action_rules.get(shadow_color, "stop")
        elif obs.status == "uncertain":
            shadow_color = shadow_obj.label if shadow_obj else None
            shadow_action = "uncertain"
        else:
            shadow_color = None
            shadow_action = "continue"

        # 3. So sánh quyết định (V6-T8, V6-T9)
        agreement = (legacy_action == shadow_action)
        comp = ShadowDecisionComparison(
            frame_id=frame.frame_id,
            timestamp=time.monotonic(),
            legacy_decision=legacy_action,
            shadow_decision=shadow_action,
            is_agreement=agreement,
            legacy_color=legacy_color,
            shadow_color=shadow_color,
            confidence=obs.confidence,
            details="Hoàn toàn đồng thuận" if agreement else f"Bất đồng: legacy={legacy_action} vs shadow={shadow_action}",
        )

        self.comparison_history.append(comp)
        if not agreement:
            self.disagreements.append(comp)

        return comp

    def get_summary(self) -> Dict[str, Any]:
        total = len(self.comparison_history)
        dis = len(self.disagreements)
        rate = round((total - dis) / max(1, total) * 100.0, 2)
        return {
            "total_frames_evaluated": total,
            "agreements": total - dis,
            "disagreements": dis,
            "agreement_rate_pct": rate,
        }
