"""
Test Inspector Dialog — Cửa sổ kiểm tra nhận diện màu sắc trực quan:
- Hiển thị ảnh chụp thực của từng Slot
- Hiển thị ảnh Mask trực quan (vùng pixel khớp màu được tô sáng)
- Bảng tỷ lệ % khớp màu so với ngưỡng
- Kết luận hành động rõ ràng (DỪNG / KHÓA / TIẾP TỤC)
- Nút Test lại tức thì không cần đóng dialog
"""
from typing import List, Dict, Any, Optional
import cv2
import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QScrollArea, QGroupBox, QGridLayout, QFrame,
    QProgressBar, QTabWidget
)

from core.capture import ScreenCapture, get_shared_capture
from core.detector import ColorDetector


def bgr_to_qpixmap(img_bgr: np.ndarray) -> QPixmap:
    if img_bgr is None or img_bgr.size == 0:
        return QPixmap()
    h, w = img_bgr.shape[:2]
    ch = img_bgr.shape[2] if len(img_bgr.shape) > 2 else 1
    if ch == 3:
        rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
    else:
        qimg = QImage(img_bgr.data, w, h, w, QImage.Format_Grayscale8)
    return QPixmap.fromImage(qimg).copy()


COLOR_HEX = {
    "purple": "#a855f7",
    "red": "#ef4444",
    "gold": "#eab308",
    "blue": "#3b82f6",
    "green": "#22c55e",
}

COLOR_NAMES = {
    "purple": "Tím (Epic)",
    "red": "Đỏ (Mythic)",
    "gold": "Vàng (Legendary)",
    "blue": "Xanh dương (Rare)",
    "green": "Xanh lá (Uncommon)",
}


class SlotTestCard(QGroupBox):
    """Card hiển thị kết quả kiểm tra cho một Slot cụ thể."""

    def __init__(self, slot_info: Dict[str, Any], result: Dict[str, Any],
                 threshold: float, rules: Dict[str, str], parent=None):
        name = slot_info.get("name", "Slot")
        x, y, w, h = slot_info.get("x", 0), slot_info.get("y", 0), slot_info.get("w", 0), slot_info.get("h", 0)
        super().__init__(f"📦 {name} — ({x}, {y}) · {w}×{h}", parent)
        self.slot_info = slot_info
        self.result = result
        self.threshold = threshold
        self.rules = rules

        self.setStyleSheet("""
            QGroupBox {
                background-color: #171c26;
                border: 1px solid #283347;
                border-radius: 8px;
                margin-top: 10px;
                font-weight: bold;
                padding-top: 14px;
                color: #38bdf8;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
        """)
        self._build_ui()

    def _build_ui(self):
        lay = QHBoxLayout(self)
        lay.setSpacing(14)
        lay.setContentsMargins(12, 10, 12, 10)

        img_bgr = self.result.get("image")
        masks = self.result.get("masks", {})
        matches = self.result.get("matches", {})

        # Cột 1: Ảnh chụp thực tế của Slot
        v_img = QVBoxLayout()
        v_img.setSpacing(4)
        v_img.setAlignment(Qt.AlignCenter)
        lbl_t1 = QLabel("Ảnh thực tế")
        lbl_t1.setStyleSheet("color: #94a3b8; font-size: 11px;")
        v_img.addWidget(lbl_t1)

        lbl_img = QLabel()
        lbl_img.setFixedSize(110, 80)
        lbl_img.setAlignment(Qt.AlignCenter)
        lbl_img.setStyleSheet("background-color: #0b0f17; border: 1px solid #334155; border-radius: 6px;")
        if img_bgr is not None and img_bgr.size > 0:
            pix = bgr_to_qpixmap(img_bgr)
            lbl_img.setPixmap(pix.scaled(110, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            lbl_img.setText("Không chụp\nđược")
        v_img.addWidget(lbl_img)
        lay.addLayout(v_img)

        # Cột 2: Ảnh Mask tổng hợp (highlight pixel trùng màu)
        v_mask = QVBoxLayout()
        v_mask.setSpacing(4)
        v_mask.setAlignment(Qt.AlignCenter)
        lbl_t2 = QLabel("Vùng nhận diện (Mask)")
        lbl_t2.setStyleSheet("color: #94a3b8; font-size: 11px;")
        v_mask.addWidget(lbl_t2)

        lbl_mask = QLabel()
        lbl_mask.setFixedSize(110, 80)
        lbl_mask.setAlignment(Qt.AlignCenter)
        lbl_mask.setStyleSheet("background-color: #0b0f17; border: 1px solid #334155; border-radius: 6px;")

        # Tạo ảnh composite highlight
        mask_pix = self._create_mask_composite(img_bgr, masks)
        if mask_pix and not mask_pix.isNull():
            lbl_mask.setPixmap(mask_pix.scaled(110, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            lbl_mask.setText("Trống")
        v_mask.addWidget(lbl_mask)
        lay.addLayout(v_mask)

        # Cột 3: Bảng danh sách % màu và kết quả ĐẠT / CHƯA
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(4)
        grid.addWidget(QLabel("Màu mục tiêu"), 0, 0)
        grid.addWidget(QLabel("Tỷ lệ khớp (%)"), 0, 1)
        grid.addWidget(QLabel("Ngưỡng"), 0, 2)
        grid.addWidget(QLabel("Đánh giá"), 0, 3)

        row = 1
        for color_key, match_info in matches.items():
            pct = match_info.get("percent", 0.0)
            is_match = match_info.get("matched", False)
            c_name = COLOR_NAMES.get(color_key, color_key)
            c_hex = COLOR_HEX.get(color_key, "#ffffff")

            lbl_color = QLabel(f"● {c_name}")
            lbl_color.setStyleSheet(f"color: {c_hex}; font-weight: bold; font-size: 11px;")
            grid.addWidget(lbl_color, row, 0)

            # Bar + text
            pct_lbl = QLabel(f"{pct:.2f}%")
            pct_lbl.setStyleSheet("font-family: monospace; font-weight: bold; font-size: 11px;")
            grid.addWidget(pct_lbl, row, 1)

            lbl_thr = QLabel(f"≥ {self.threshold:.1f}%")
            lbl_thr.setStyleSheet("color: #64748b; font-size: 11px;")
            grid.addWidget(lbl_thr, row, 2)

            if is_match:
                badge = QLabel("✅ ĐẠT NGƯỠNG")
                badge.setStyleSheet("""
                    background-color: #064e3b; color: #34d399; font-weight: bold;
                    padding: 2px 6px; border-radius: 4px; font-size: 10px;
                """)
            else:
                badge = QLabel("❌ Chưa đạt")
                badge.setStyleSheet("color: #64748b; font-size: 10px;")
            grid.addWidget(badge, row, 3)
            row += 1

        lay.addLayout(grid, 1)

    def _create_mask_composite(self, img_bgr: Optional[np.ndarray], masks: Dict[str, np.ndarray]) -> Optional[QPixmap]:
        if img_bgr is None or img_bgr.size == 0:
            return None
        h, w = img_bgr.shape[:2]
        # Tạo ảnh nền tối (grayscale mờ)
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        canvas = cv2.cvtColor(gray // 2, cv2.COLOR_GRAY2BGR)

        # Tô màu nổi bật cho từng mask
        has_mask = False
        color_bgr_map = {
            "purple": (200, 50, 200),
            "red": (50, 50, 240),
            "gold": (0, 215, 255),
            "blue": (240, 150, 50),
            "green": (50, 220, 50),
        }
        for c_key, mask in masks.items():
            if mask is not None and np.any(mask > 0):
                has_mask = True
                bgr_tint = color_bgr_map.get(c_key, (255, 255, 255))
                canvas[mask > 0] = bgr_tint

        return bgr_to_qpixmap(canvas)


class TestInspectorDialog(QDialog):
    """Dialog toàn diện kiểm tra nhận diện màu sắc của các Slot."""

    def __init__(self, slots: List[Dict[str, Any]], target_colors: List[str],
                 threshold: float, rules: Dict[str, str], color_definitions: Optional[dict] = None, parent=None):
        super().__init__(parent)
        self.slots = slots
        self.target_colors = target_colors
        self.threshold = threshold
        self.rules = rules
        self.color_defs = color_definitions or {}

        self.setWindowTitle("🔍 Test Nhận Diện Màu Sắc Trực Quan (Test Inspector)")
        self.resize(850, 580)
        self.setMinimumSize(750, 480)
        self._init_stylesheet()
        self._build_ui()
        self.run_test()

    def _init_stylesheet(self):
        self.setStyleSheet("""
            QDialog { background-color: #11141c; color: #e2e8f0; font-family: 'Segoe UI', sans-serif; }
            QLabel { color: #cbd5e1; }
            QPushButton {
                background-color: #1e2638; border: 1px solid #334155;
                border-radius: 6px; padding: 7px 16px; color: #f1f5f9; font-weight: 600;
            }
            QPushButton:hover { background-color: #2a364f; border-color: #475569; }
            QScrollArea { border: 1px solid #232b3a; background-color: #0b0f17; border-radius: 8px; }
        """)

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(12)

        # Header Info
        top_box = QHBoxLayout()
        self.lbl_summary_title = QLabel("Kiểm tra ảnh chụp thực tế từ màn hình và so khớp với bộ màu đã cấu hình.")
        self.lbl_summary_title.setStyleSheet("color: #94a3b8; font-size: 12px;")
        top_box.addWidget(self.lbl_summary_title)
        top_box.addStretch()

        btn_retest = QPushButton("🔄 Chụp & Test Lại")
        btn_retest.setStyleSheet("background-color: #0284c7; border-color: #0ea5e9; color: white;")
        btn_retest.clicked.connect(self.run_test)
        top_box.addWidget(btn_retest)
        lay.addLayout(top_box)

        # Scroll area for Slot results
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.cards_container = QWidget()
        self.cards_lay = QVBoxLayout(self.cards_container)
        self.cards_lay.setSpacing(8)
        self.cards_lay.setContentsMargins(8, 8, 8, 8)
        self.scroll.setWidget(self.cards_container)
        lay.addWidget(self.scroll, 1)

        # Bottom Conclusion Box
        self.box_conclusion = QFrame()
        self.box_conclusion.setStyleSheet("""
            QFrame {
                background-color: #171c26;
                border: 2px solid #334155;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        lay_conc = QHBoxLayout(self.box_conclusion)
        lay_conc.setContentsMargins(10, 6, 10, 6)
        self.lbl_conclusion = QLabel("Đang phân tích...")
        self.lbl_conclusion.setFont(QFont("Segoe UI", 11, QFont.Bold))
        lay_conc.addWidget(self.lbl_conclusion, 1)

        btn_close = QPushButton("Đóng")
        btn_close.clicked.connect(self.accept)
        lay_conc.addWidget(btn_close)
        lay.addWidget(self.box_conclusion)

    def run_test(self):
        """Chụp màn hình và chạy nhận diện trên từng Slot."""
        # Xóa các card cũ
        while self.cards_lay.count():
            item = self.cards_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        cap = get_shared_capture()
        detector = ColorDetector(custom_colors=self.color_defs)

        overall_matched = False
        matched_details = []

        if not self.slots:
            lbl_empty = QLabel("Chưa có Slot quan sát nào được thiết lập!")
            lbl_empty.setAlignment(Qt.AlignCenter)
            lbl_empty.setStyleSheet("color: #ef4444; font-size: 14px; padding: 30px;")
            self.cards_lay.addWidget(lbl_empty)
            self._update_conclusion(False, [])
            return

        for i, s in enumerate(self.slots):
            x, y, w, h = s.get("x", 0), s.get("y", 0), s.get("w", 100), s.get("h", 100)
            img = cap.capture_region(x, y, w, h)
            if img is None or img.size == 0:
                continue

            matches, masks = detector.detect_colors(img, self.target_colors, self.threshold)
            result = {
                "image": img,
                "matches": matches,
                "masks": masks
            }

            card = SlotTestCard(s, result, self.threshold, self.rules, parent=self.cards_container)
            self.cards_lay.addWidget(card)

            # Check if any matched in this slot
            for color_key, m_info in matches.items():
                if m_info.get("matched", False):
                    overall_matched = True
                    act = self.rules.get(color_key, "stop")
                    matched_details.append({
                        "slot": s.get("name", f"Slot {i+1}"),
                        "color": color_key,
                        "pct": m_info.get("percent", 0.0),
                        "action": act
                    })

        self.cards_lay.addStretch()
        self._update_conclusion(overall_matched, matched_details)

    def _update_conclusion(self, matched: bool, details: List[dict]):
        if matched and details:
            parts = []
            for d in details:
                c_name = COLOR_NAMES.get(d["color"], d["color"])
                act_str = "DỪNG LẠI (STOP)" if d["action"] == "stop" else "KHÓA SLOT (LOCK)"
                parts.append(f"<b>{d['slot']}</b> thấy <b>{c_name}</b> ({d['pct']:.1f}%) → <b>{act_str}</b>")

            self.box_conclusion.setStyleSheet("""
                QFrame {
                    background-color: #064e3b;
                    border: 2px solid #10b981;
                    border-radius: 8px;
                }
            """)
            self.lbl_conclusion.setText("🎉 KẾT QUẢ: PHÁT HIỆN MÀU MỤC TIÊU!\n" + " • ".join(parts))
            self.lbl_conclusion.setStyleSheet("color: #ecfdf5;")
        else:
            self.box_conclusion.setStyleSheet("""
                QFrame {
                    background-color: #1e293b;
                    border: 2px solid #475569;
                    border-radius: 8px;
                }
            """)
            self.lbl_conclusion.setText("🔍 KẾT QUẢ: Chưa có màu nào đạt ngưỡng tối thiểu. Nếu roll thực tế sẽ tiếp tục Roll.")
            self.lbl_conclusion.setStyleSheet("color: #94a3b8;")
