"""
Lớp quan sát hình ảnh (Observation Layer) cho SmartAutoClick v3.1.

Theo nguyên tắc kiến trúc:
Observe -> Understand -> Decide -> Act -> Verify
Detector chỉ báo cáo đặc điểm nhận diện và mức độ tin cậy. Decision Engine mới là nơi
đưa ra quyết định (chuyển trạng thái, dừng, lock slot hay tiếp tục click).

Nhiệm vụ (Phase 3):
- V3-T8: Tạo dataclass Observation chuẩn hóa.
- V3-T9: Detector trả về Observation thay vì quyết định click.
- V3-T10: Liên kết chặt chẽ với frame_id và geometry_version.
- V3-T11: Kèm theo confidence (0.0-1.0) và evidence (thông số, bounding boxes, percent...).
- V3-T12: Hỗ trợ nhiều detector (Color, Anchor, Template, Motion...) trên cùng một frame.
"""
from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


class ObservationStatus(str, Enum):
    VALID = "valid"
    UNCERTAIN = "uncertain"
    NOT_FOUND = "not_found"
    ANCHOR_LOST = "anchor_lost"
    FRAME_INVALID = "frame_invalid"


@dataclass
class DetectedObject:
    """Đối tượng phát hiện được trong vùng ROI."""
    label: str                       # Tên đối tượng hoặc màu sắc (ví dụ: 'purple', 'roll_btn', 'anchor')
    confidence: float = 0.0          # Mức độ tin cậy từ 0.0 đến 1.0
    bounding_box: Tuple[int, int, int, int] = (0, 0, 0, 0) # (x, y, w, h)
    relative_box: Optional[Tuple[float, float, float, float]] = None # (rx, ry, rw, rh)
    coverage_percent: float = 0.0   # Tỉ lệ diện tích màu / khớp
    raw_data: Dict[str, Any] = field(default_factory=dict) # Metadata bổ sung của detector


@dataclass
class AnchorResult:
    """Kết quả xác định điểm neo UI (Anchor)."""
    found: bool = False
    name: str = ""
    client_pos: Tuple[int, int] = (0, 0) # (x, y) trên client area
    confidence: float = 0.0
    bounding_box: Tuple[int, int, int, int] = (0, 0, 0, 0)
    cached_used: bool = False


@dataclass
class Observation:
    """
    Observation Data Contract chuẩn v3.1:
    - frame_id: liên kết trực tiếp với frame gốc
    - geometry_version: phiên bản hình học tại thời điểm quan sát
    - timestamp: mốc thời gian monotonic
    - anchor: kết quả phát hiện điểm neo (nếu workflow dùng anchor)
    - detected_objects: danh sách đối tượng / màu nhận diện được
    - confidence: độ tin cậy tổng thể (0.0 - 1.0)
    - evidence: bằng chứng quan sát (ảnh crop, histogram, mask stats...)
    - status: trạng thái quan sát (VALID / UNCERTAIN / NOT_FOUND / ANCHOR_LOST)
    - metadata: thông tin bổ sung (tên detector, thời gian xử lý ms...)
    """
    frame_id: int
    geometry_version: int = 1
    timestamp: float = field(default_factory=time.monotonic)
    anchor: Optional[AnchorResult] = None
    detected_objects: List[DetectedObject] = field(default_factory=list)
    confidence: float = 0.0
    evidence: Dict[str, Any] = field(default_factory=dict)
    status: ObservationStatus = ObservationStatus.VALID
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_reliable(self) -> bool:
        """Kiểm tra xem quan sát có đáng tin cậy để đưa vào Decision Engine không."""
        return self.status == ObservationStatus.VALID and self.confidence >= 0.5

    def get_object_by_label(self, label: str) -> Optional[DetectedObject]:
        for obj in self.detected_objects:
            if obj.label == label:
                return obj
        return None
