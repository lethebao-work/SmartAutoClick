"""
Bộ đối sánh và theo dõi điểm neo (Anchor Matcher) cho SmartAutoClick v3.1.

Theo định hướng kiến trúc Visual Automation:
- V3-T1: AnchorMatcher.find(frame/image) -> AnchorResult(pos, confidence, bounding_box)
- V3-T3: Cơ chế ROI Cache: lần đầu quét toàn khung để tìm anchor, sau khi tìm thấy sẽ ưu tiên
  quét trong ROI mở rộng quanh vị trí cũ (tìm nhanh hơn gấp 10-20 lần).
- V3-T4: Nếu match score dưới ngưỡng tin cậy (threshold), báo mất neo (found=False), không đoán mò.
- V3-T5: Tính toán vị trí các slot và điểm click dựa trên offset tương đối so với anchor.
- Hỗ trợ lưu và nạp template ảnh neo từ file (PNG / BGR).
"""
import os
import cv2
import numpy as np
import time
from typing import Dict, List, Optional, Tuple, Any

from core.capture_interface import Frame
from core.observation import AnchorResult


class AnchorMatcher:
    """
    Tìm kiếm và bám điểm neo giao diện (UI Anchor) qua Template Matching.
    Tự động sử dụng ROI Caching để tối ưu tốc độ CPU.
    """

    def __init__(
        self,
        name: str = "main_anchor",
        template: Optional[np.ndarray] = None,
        confidence_threshold: float = 0.80,
        roi_margin: int = 40,
    ):
        """
        :param name: Tên định danh của anchor
        :param template: Mảng ảnh mẫu BGR của neo
        :param confidence_threshold: Ngưỡng match score tối thiểu để xác nhận neo (0.0 - 1.0)
        :param roi_margin: Khoảng đệm pixel mở rộng quanh vị trí cũ khi dùng ROI Cache
        """
        self.name = name
        self.template = template
        self.confidence_threshold = confidence_threshold
        self.roi_margin = roi_margin

        self._last_pos: Optional[Tuple[int, int]] = None  # (x, y)
        self._last_confidence: float = 0.0
        self._template_h: int = 0
        self._template_w: int = 0
        if self.template is not None and self.template.size > 0:
            self._template_h, self._template_w = self.template.shape[:2]

    def load_template_file(self, file_path: str) -> bool:
        """Nạp ảnh neo từ đường dẫn file."""
        if not os.path.exists(file_path):
            return False
        img = cv2.imread(file_path, cv2.IMREAD_COLOR)
        if img is None or img.size == 0:
            return False
        self.template = img
        self._template_h, self._template_w = img.shape[:2]
        self._last_pos = None
        return True

    def reset_cache(self) -> None:
        """Xóa cache vị trí neo cũ để bắt buộc tìm toàn khung ở lần tiếp theo."""
        self._last_pos = None
        self._last_confidence = 0.0

    def find(self, frame_or_img: Any) -> AnchorResult:
        """
        Tìm kiếm vị trí neo trên Frame hoặc numpy BGR image.
        Ưu tiên tìm trong ROI cache trước; nếu không thấy hoặc rớt ngưỡng thì tìm toàn khung.
        """
        if self.template is None or self.template.size == 0:
            return AnchorResult(found=False, name=self.name, confidence=0.0)

        # Lấy mảng ảnh BGR
        if isinstance(frame_or_img, Frame):
            if not frame_or_img.is_valid or frame_or_img.image is None:
                return AnchorResult(found=False, name=self.name, confidence=0.0)
            img = frame_or_img.image
        elif isinstance(frame_or_img, np.ndarray):
            img = frame_or_img
        else:
            return AnchorResult(found=False, name=self.name, confidence=0.0)

        h, w = img.shape[:2]
        th, tw = self._template_h, self._template_w
        if h < th or w < tw:
            return AnchorResult(found=False, name=self.name, confidence=0.0)

        # 1. Thử tìm trong ROI Cache quanh vị trí cũ (V3-T3)
        if self._last_pos is not None:
            lx, ly = self._last_pos
            x0 = max(0, lx - self.roi_margin)
            y0 = max(0, ly - self.roi_margin)
            x1 = min(w, lx + tw + self.roi_margin)
            y1 = min(h, ly + th + self.roi_margin)

            if (x1 - x0) >= tw and (y1 - y0) >= th:
                roi = img[y0:y1, x0:x1]
                res = cv2.matchTemplate(roi, self.template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                if max_val >= self.confidence_threshold:
                    found_x = x0 + max_loc[0]
                    found_y = y0 + max_loc[1]
                    self._last_pos = (found_x, found_y)
                    self._last_confidence = float(max_val)
                    return AnchorResult(
                        found=True,
                        name=self.name,
                        client_pos=(found_x, found_y),
                        confidence=round(float(max_val), 3),
                        bounding_box=(found_x, found_y, tw, th),
                        cached_used=True,
                    )

        # 2. Không thấy trong cache -> Tìm kiếm toàn khung hình (Full-frame search)
        res_full = cv2.matchTemplate(img, self.template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res_full)

        if max_val >= self.confidence_threshold:
            found_x, found_y = max_loc
            found_patch = img[found_y:found_y + th, found_x:found_x + tw]
            # Xác nhận thêm: ảnh tìm được không được là ảnh đen/đồng màu nếu template có độ lệch chuẩn
            tmpl_std = float(self.template.std())
            patch_std = float(found_patch.std())
            mean_diff = float(np.abs(found_patch.astype(float) - self.template.astype(float)).mean())
            if tmpl_std > 5.0 and patch_std < 2.0:
                # Patch đồng màu nhưng template có chi tiết -> False positive do chuẩn hóa mẫu số 0
                max_val = 0.0
            elif mean_diff > 40.0:
                max_val = 0.0
            else:
                self._last_pos = (found_x, found_y)
                self._last_confidence = float(max_val)
                return AnchorResult(
                    found=True,
                    name=self.name,
                    client_pos=(found_x, found_y),
                    confidence=round(float(max_val), 3),
                    bounding_box=(found_x, found_y, tw, th),
                    cached_used=False,
                )

        # V3-T4: Dưới ngưỡng confidence -> báo mất neo, không đoán mò
        self._last_pos = None
        self._last_confidence = float(max_val)
        return AnchorResult(
            found=False,
            name=self.name,
            client_pos=(0, 0),
            confidence=round(float(max_val), 3),
            bounding_box=(0, 0, 0, 0),
            cached_used=False,
        )

    @staticmethod
    def calculate_offset_target(
        anchor_pos: Tuple[int, int],
        offset_x: int,
        offset_y: int,
    ) -> Tuple[int, int]:
        """V3-T5: Tính tọa độ mục tiêu (nút hoặc slot) dựa trên offset từ neo."""
        ax, ay = anchor_pos
        return ax + offset_x, ay + offset_y

    @staticmethod
    def calculate_offset_region(
        anchor_pos: Tuple[int, int],
        offset_x: int,
        offset_y: int,
        region_w: int,
        region_h: int,
    ) -> Tuple[int, int, int, int]:
        """V3-T5: Tính hình chữ nhật ROI (slot) dựa trên offset từ neo."""
        ax, ay = anchor_pos
        return ax + offset_x, ay + offset_y, region_w, region_h
