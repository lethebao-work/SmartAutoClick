"""
Color Sampler — Công cụ hút màu HSV từ màn hình hoặc từ Slot.
Được thiết kế chính xác, kính lúp cố định ở panel bên phải, hỗ trợ phóng to và chọn vùng Slot trực tiếp.
"""
from typing import Optional, Tuple, List, Dict, Any
import cv2
import numpy as np

from PySide6.QtCore import Qt, QPoint, QRect, Signal
from PySide6.QtGui import (
    QPixmap, QImage, QPainter, QPen, QBrush, QColor,
    QCursor
)
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QScrollArea, QComboBox, QSpinBox,
    QFormLayout, QGroupBox, QLineEdit, QMessageBox, QFrame
)


def bgr_to_qpixmap(img_bgr: np.ndarray) -> QPixmap:
    """Convert BGR numpy array to QPixmap."""
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


def bgr_to_hsv_values(bgr: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """Convert a single BGR pixel to OpenCV HSV (H: 0-180, S: 0-255, V: 0-255)."""
    pixel = np.array([[list(bgr)]], dtype=np.uint8)
    hsv = cv2.cvtColor(pixel, cv2.COLOR_BGR2HSV)
    return int(hsv[0, 0, 0]), int(hsv[0, 0, 1]), int(hsv[0, 0, 2])


class ScreenCanvas(QLabel):
    """
    Widget hiển thị ảnh.
    Di chuột -> emit pixel_hovered.
    Click -> emit pixel_clicked.
    """
    pixel_hovered = Signal(int, int, tuple)    # ix, iy, bgr
    pixel_clicked = Signal(int, int, tuple)    # ix, iy, bgr

    def __init__(self, img_bgr: np.ndarray, scale: float = 1.0):
        super().__init__()
        self._img_bgr = img_bgr
        self._scale = scale
        self.setMouseTracking(True)
        self.setCursor(QCursor(Qt.CrossCursor))
        self._hover_pos: Optional[QPoint] = None
        self._sample_points: List[Tuple[int, int, tuple]] = []  # (ix, iy, bgr)
        self._display_pixmap = QPixmap()
        self._refresh_pixmap()

    def set_image(self, img_bgr: np.ndarray, scale: Optional[float] = None):
        self._img_bgr = img_bgr
        if scale is not None:
            self._scale = scale
        self._sample_points.clear()
        self._hover_pos = None
        self._refresh_pixmap()

    def set_scale(self, scale: float):
        self._scale = max(0.1, min(scale, 5.0))
        self._refresh_pixmap()

    def _refresh_pixmap(self):
        if self._img_bgr is None or self._img_bgr.size == 0:
            return
        h, w = self._img_bgr.shape[:2]
        new_w = max(1, int(w * self._scale))
        new_h = max(1, int(h * self._scale))
        resized = cv2.resize(self._img_bgr, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        self._display_pixmap = bgr_to_qpixmap(resized)
        self.setFixedSize(new_w, new_h)
        self.update()

    def _widget_to_img(self, wx: int, wy: int) -> Tuple[int, int]:
        """Convert widget coords to original image coords."""
        h, w = self._img_bgr.shape[:2]
        ix = int(wx / self._scale)
        iy = int(wy / self._scale)
        return max(0, min(ix, w - 1)), max(0, min(iy, h - 1))

    def mouseMoveEvent(self, event):
        self._hover_pos = event.position().toPoint()
        ix, iy = self._widget_to_img(self._hover_pos.x(), self._hover_pos.y())
        bgr = tuple(int(v) for v in self._img_bgr[iy, ix])
        self.pixel_hovered.emit(ix, iy, bgr)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.position().toPoint()
            ix, iy = self._widget_to_img(pos.x(), pos.y())
            bgr = tuple(int(v) for v in self._img_bgr[iy, ix])
            self._sample_points.append((ix, iy, bgr))
            self.pixel_clicked.emit(ix, iy, bgr)
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        if not self._display_pixmap.isNull():
            painter.drawPixmap(0, 0, self._display_pixmap)

        # Draw sampled points
        for (sx, sy, _) in self._sample_points:
            wx = int(sx * self._scale)
            wy = int(sy * self._scale)
            painter.setPen(QPen(QColor(0, 255, 120), 2))
            painter.drawEllipse(QPoint(wx, wy), 7, 7)
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.drawEllipse(QPoint(wx, wy), 4, 4)

        # Crosshair lines at cursor
        if self._hover_pos:
            x, y = self._hover_pos.x(), self._hover_pos.y()
            painter.setPen(QPen(QColor(255, 80, 80, 160), 1, Qt.DashLine))
            painter.drawLine(0, y, self.width(), y)
            painter.drawLine(x, 0, x, self.height())

        painter.end()

    def clear_samples(self):
        self._sample_points.clear()
        self.update()


class ColorSamplerDialog(QDialog):
    """
    Dialog hút màu chuyên nghiệp:
    - Kính lúp (Magnifier) cố định 160x160 ở panel bên phải (không che mắt, không trôi).
    - Hỗ trợ đổi nguồn ảnh: Toàn màn hình hoặc từng Slot cụ thể.
    - Hỗ trợ Zoom 50%, 100%, 150%, 200% hoặc Vừa khung.
    - Tính toán dải HSV chính xác từ các điểm click mẫu.
    """
    color_sampled = Signal(str, dict)  # key, color_def

    def __init__(self, img_bgr: np.ndarray, slots: Optional[List[Dict[str, Any]]] = None,
                 default_slot_idx: Optional[int] = None, parent=None):
        super().__init__(parent)
        self._fullscreen_bgr = img_bgr
        self._active_bgr = img_bgr
        self._slots = slots or []
        if isinstance(default_slot_idx, bool):
            default_slot_idx = None
        self._default_slot_idx = default_slot_idx
        self._samples_hsv: List[Tuple[int, int, int]] = []
        self._current_bgr: Tuple[int, int, int] = (128, 128, 128)

        self.setWindowTitle("🎨 Hút Màu HSV Chính Xác (Color Sampler)")
        self.resize(1100, 720)
        self.setMinimumSize(960, 600)
        self._init_stylesheet()
        self._build_ui()

        # Load default slot if specified
        if self._default_slot_idx is not None and not isinstance(self._default_slot_idx, bool) and 0 <= self._default_slot_idx < len(self._slots):
            self.cmb_source.setCurrentIndex(self._default_slot_idx + 1)

    def _init_stylesheet(self):
        self.setStyleSheet("""
            QDialog { background-color: #11141c; color: #e2e8f0; font-family: 'Segoe UI', sans-serif; }
            QLabel { color: #94a3b8; font-size: 12px; }
            QGroupBox {
                background-color: #171c26;
                border: 1px solid #232b3a;
                border-radius: 8px;
                margin-top: 10px;
                font-weight: bold;
                padding-top: 12px;
                color: #38bdf8;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
            QLineEdit, QSpinBox, QComboBox {
                background-color: #0b0f17; border: 1px solid #283347;
                border-radius: 5px; padding: 4px 8px; color: #f8fafc;
            }
            QComboBox::drop-down { border: none; }
            QPushButton {
                background-color: #1e2638; border: 1px solid #334155;
                border-radius: 6px; padding: 6px 12px; color: #f1f5f9; font-weight: 600;
            }
            QPushButton:hover { background-color: #2a364f; border-color: #475569; }
            QScrollArea { border: 1px solid #232b3a; background-color: #080b11; border-radius: 8px; }
        """)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ── Toolbar trên cùng ────────────────────────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        toolbar.addWidget(QLabel("Nguồn ảnh:"))
        self.cmb_source = QComboBox()
        self.cmb_source.addItem("🖥️ Toàn màn hình (Fullscreen)", -1)
        for i, s in enumerate(self._slots):
            s_name = s.get("name", f"Slot {i+1}")
            self.cmb_source.addItem(f"📦 {s_name} ({s.get('w',0)}x{s.get('h',0)})", i)
        self.cmb_source.currentIndexChanged.connect(self._on_source_changed)
        toolbar.addWidget(self.cmb_source)

        toolbar.addWidget(QLabel("Tỉ lệ Zoom:"))
        self.cmb_zoom = QComboBox()
        self.cmb_zoom.addItem("50%", 0.5)
        self.cmb_zoom.addItem("75%", 0.75)
        self.cmb_zoom.addItem("100% (Gốc)", 1.0)
        self.cmb_zoom.addItem("150%", 1.5)
        self.cmb_zoom.addItem("200%", 2.0)
        self.cmb_zoom.addItem("300%", 3.0)
        self.cmb_zoom.setCurrentIndex(2)  # 100%
        self.cmb_zoom.currentIndexChanged.connect(self._on_zoom_changed)
        toolbar.addWidget(self.cmb_zoom)

        toolbar.addStretch()
        lbl_hint = QLabel("💡 Di chuột để soi kính lúp. Click chuột trái vào vật phẩm để lấy mẫu màu.")
        lbl_hint.setStyleSheet("color: #38bdf8; font-style: italic;")
        toolbar.addWidget(lbl_hint)
        root.addLayout(toolbar)

        # ── Khu vực thân chính: Canvas + Right Panel ─────────────────────────
        content = QHBoxLayout()
        content.setSpacing(12)

        # Left: Scroll area with canvas
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(False)
        self.canvas = ScreenCanvas(self._active_bgr, scale=1.0)
        self.canvas.pixel_hovered.connect(self._on_pixel_hover)
        self.canvas.pixel_clicked.connect(self._on_pixel_click)
        self.scroll.setWidget(self.canvas)
        content.addWidget(self.scroll, 1)

        # Right: Control Panel
        right_panel = QWidget()
        right_panel.setFixedWidth(320)
        lay_right = QVBoxLayout(right_panel)
        lay_right.setContentsMargins(0, 0, 0, 0)
        lay_right.setSpacing(8)

        # 1. Kính lúp (Fixed Magnifier Panel)
        grp_mag = QGroupBox("🔍 Kính Lúp Phóng Đại (8x)")
        vmag = QVBoxLayout(grp_mag)
        vmag.setSpacing(8)

        mag_row = QHBoxLayout()
        # Magnifier screen preview
        self.lbl_mag = QLabel()
        self.lbl_mag.setFixedSize(160, 160)
        self.lbl_mag.setStyleSheet("""
            background-color: #0b0f17;
            border: 2px solid #38bdf8;
            border-radius: 8px;
        """)
        self.lbl_mag.setAlignment(Qt.AlignCenter)
        mag_row.addWidget(self.lbl_mag)

        # Color patch + HEX
        v_patch = QVBoxLayout()
        self.lbl_patch = QLabel()
        self.lbl_patch.setFixedSize(70, 70)
        self.lbl_patch.setStyleSheet("""
            background-color: #888888;
            border: 2px solid #64748b;
            border-radius: 8px;
        """)
        v_patch.addWidget(self.lbl_patch)

        self.lbl_hex = QLabel("#888888")
        self.lbl_hex.setStyleSheet("font-weight: bold; font-family: monospace; color: #f8fafc;")
        v_patch.addWidget(self.lbl_hex)
        v_patch.addStretch()
        mag_row.addLayout(v_patch)
        vmag.addLayout(mag_row)

        # Pixel coords & info
        self.lbl_coords = QLabel("Tọa độ: (0, 0)")
        self.lbl_rgb = QLabel("RGB: -")
        self.lbl_hsv = QLabel("HSV: -")
        vmag.addWidget(self.lbl_coords)
        vmag.addWidget(self.lbl_rgb)
        vmag.addWidget(self.lbl_hsv)
        lay_right.addWidget(grp_mag)

        # 2. Danh sách mẫu đã click
        grp_samples = QGroupBox("Điểm Đã Lấy Mẫu")
        vsamp = QVBoxLayout(grp_samples)
        self.lbl_samples = QLabel("Chưa có mẫu nào.\nClick vào vùng cần hút màu.")
        self.lbl_samples.setWordWrap(True)
        self.lbl_samples.setStyleSheet("color: #cbd5e1; font-family: monospace; font-size: 11px;")
        vsamp.addWidget(self.lbl_samples)

        self.btn_clear = QPushButton("🗑 Xóa hết mẫu")
        self.btn_clear.clicked.connect(self._clear_samples)
        vsamp.addWidget(self.btn_clear)
        lay_right.addWidget(grp_samples)

        # 3. Dải HSV tính toán
        grp_hsv = QGroupBox("Dải HSV Tính Toán")
        fhsv = QFormLayout(grp_hsv)
        fhsv.setSpacing(4)
        self.spin_h_min = QSpinBox(); self.spin_h_min.setRange(0, 180)
        self.spin_h_max = QSpinBox(); self.spin_h_max.setRange(0, 180)
        self.spin_s_min = QSpinBox(); self.spin_s_min.setRange(0, 255)
        self.spin_s_max = QSpinBox(); self.spin_s_max.setRange(0, 255)
        self.spin_v_min = QSpinBox(); self.spin_v_min.setRange(0, 255)
        self.spin_v_max = QSpinBox(); self.spin_v_max.setRange(0, 255)
        self.spin_tol = QSpinBox(); self.spin_tol.setRange(1, 60); self.spin_tol.setValue(15)
        self.spin_tol.valueChanged.connect(self._recalculate_range)

        fhsv.addRow("Hue (H):", self._make_pair(self.spin_h_min, self.spin_h_max))
        fhsv.addRow("Sat (S):", self._make_pair(self.spin_s_min, self.spin_s_max))
        fhsv.addRow("Val (V):", self._make_pair(self.spin_v_min, self.spin_v_max))
        fhsv.addRow("Dung sai (±):", self.spin_tol)
        lay_right.addWidget(grp_hsv)

        # 4. Lưu màu
        grp_save = QGroupBox("Lưu Màu Mới")
        fsave = QFormLayout(grp_save)
        fsave.setSpacing(4)
        self.txt_key = QLineEdit(); self.txt_key.setPlaceholderText("VD: purple_dark")
        self.txt_name = QLineEdit(); self.txt_name.setPlaceholderText("VD: Tím Huyền Bí")
        fsave.addRow("Mã key:", self.txt_key)
        fsave.addRow("Tên hiển thị:", self.txt_name)

        self.btn_save = QPushButton("💾 Thêm Vào Cấu Hình")
        self.btn_save.setStyleSheet("background-color: #059669; border-color: #10b981; color: white;")
        self.btn_save.clicked.connect(self._save_color)
        fsave.addRow(self.btn_save)
        lay_right.addWidget(grp_save)

        lay_right.addStretch()
        btn_close = QPushButton("Đóng")
        btn_close.clicked.connect(self.accept)
        lay_right.addWidget(btn_close)

        content.addWidget(right_panel)
        root.addLayout(content)

    def _make_pair(self, s1: QSpinBox, s2: QSpinBox) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(4)
        h.addWidget(s1)
        lbl = QLabel("→")
        lbl.setStyleSheet("color: #64748b;")
        h.addWidget(lbl)
        h.addWidget(s2)
        return w

    def _on_source_changed(self, idx: int):
        slot_idx = self.cmb_source.currentData()
        if slot_idx == -1 or slot_idx is None or slot_idx >= len(self._slots):
            # Fullscreen
            self._active_bgr = self._fullscreen_bgr
            scale = 1.0 if self.cmb_zoom.currentIndex() == 2 else self.cmb_zoom.currentData()
            self.canvas.set_image(self._active_bgr, scale=scale)
        else:
            # Slot crop
            s = self._slots[slot_idx]
            x, y, w, h = s.get("x", 0), s.get("y", 0), s.get("w", 100), s.get("h", 100)
            img_h, img_w = self._fullscreen_bgr.shape[:2]
            x1 = max(0, min(x, img_w - 1))
            y1 = max(0, min(y, img_h - 1))
            x2 = max(x1 + 1, min(x + w, img_w))
            y2 = max(y1 + 1, min(y + h, img_h))
            crop = self._fullscreen_bgr[y1:y2, x1:x2].copy()
            self._active_bgr = crop
            # Tự động zoom 200% nếu slot nhỏ
            auto_scale = 2.0 if (w < 400 and h < 400) else 1.5
            self.canvas.set_image(self._active_bgr, scale=auto_scale)

    def _on_zoom_changed(self):
        scale = self.cmb_zoom.currentData()
        if scale:
            self.canvas.set_scale(scale)

    def _on_pixel_hover(self, ix: int, iy: int, bgr: tuple):
        self._current_bgr = bgr
        b, g, r = bgr
        h, s, v = bgr_to_hsv_values(bgr)
        hex_code = f"#{r:02X}{g:02X}{b:02X}"

        self.lbl_coords.setText(f"Tọa độ: ({ix}, {iy})")
        self.lbl_rgb.setText(f"RGB: ({r}, {g}, {b})")
        self.lbl_hsv.setText(f"HSV: (H={h}, S={s}, V={v})")
        self.lbl_hex.setText(hex_code)
        self.lbl_patch.setStyleSheet(
            f"background-color: {hex_code}; border: 2px solid #38bdf8; border-radius: 8px;"
        )

        # Update fixed magnifier panel
        mag_rad = 12
        h_img, w_img = self._active_bgr.shape[:2]
        x1 = max(0, ix - mag_rad)
        y1 = max(0, iy - mag_rad)
        x2 = min(w_img, ix + mag_rad + 1)
        y2 = min(h_img, iy + mag_rad + 1)
        patch = self._active_bgr[y1:y2, x1:x2]

        if patch.size > 0:
            mag_w = 160
            mag_h = 160
            zoomed = cv2.resize(patch, (mag_w, mag_h), interpolation=cv2.INTER_NEAREST)
            pix = bgr_to_qpixmap(zoomed)

            # Draw crosshair directly on magnifier pixmap
            painter = QPainter(pix)
            painter.setPen(QPen(QColor(239, 68, 68), 2))  # red crosshair
            cx, cy = mag_w // 2, mag_h // 2
            painter.drawLine(cx - 15, cy, cx + 15, cy)
            painter.drawLine(cx, cy - 15, cx, cy + 15)
            # Center target box
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.drawRect(cx - 3, cy - 3, 6, 6)
            painter.end()

            self.lbl_mag.setPixmap(pix)

    def _on_pixel_click(self, ix: int, iy: int, bgr: tuple):
        h, s, v = bgr_to_hsv_values(bgr)
        self._samples_hsv.append((h, s, v))
        self._update_samples_list()
        self._recalculate_range()

    def _update_samples_list(self):
        if not self._samples_hsv:
            self.lbl_samples.setText("Chưa có mẫu nào.\nClick vào vùng cần hút màu.")
            return
        lines = [f"#{i+1}: H={h:3d}, S={s:3d}, V={v:3d}" for i, (h, s, v) in enumerate(self._samples_hsv)]
        self.lbl_samples.setText("\n".join(lines[-8:]))  # hiện 8 mẫu gần nhất

    def _recalculate_range(self):
        if not self._samples_hsv:
            return
        tol = self.spin_tol.value()
        arr = np.array(self._samples_hsv)
        h_mean, s_mean, v_mean = arr.mean(axis=0)

        self.spin_h_min.setValue(max(0, int(h_mean - tol)))
        self.spin_h_max.setValue(min(180, int(h_mean + tol)))
        self.spin_s_min.setValue(max(0, int(s_mean - tol * 3)))
        self.spin_s_max.setValue(min(255, int(s_mean + tol * 3)))
        self.spin_v_min.setValue(max(0, int(v_mean - tol * 3)))
        self.spin_v_max.setValue(min(255, int(v_mean + tol * 3)))

    def _clear_samples(self):
        self._samples_hsv.clear()
        self.canvas.clear_samples()
        self._update_samples_list()

    def _save_color(self):
        key = self.txt_key.text().strip()
        name = self.txt_name.text().strip()
        if not key:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập Mã key màu (VD: purple_dark)")
            return
        if not self._samples_hsv:
            QMessageBox.warning(self, "Lỗi", "Vui lòng click vào ảnh để lấy ít nhất 1 mẫu màu")
            return

        color_def = {
            "name": name if name else key,
            "h_min": self.spin_h_min.value(),
            "h_max": self.spin_h_max.value(),
            "s_min": self.spin_s_min.value(),
            "s_max": self.spin_s_max.value(),
            "v_min": self.spin_v_min.value(),
            "v_max": self.spin_v_max.value(),
        }
        self.color_sampled.emit(key, color_def)
        QMessageBox.information(
            self, "Thành công",
            f"Đã lưu màu '{name or key}'!\nKey: {key}\nH: [{color_def['h_min']}-{color_def['h_max']}], "
            f"S: [{color_def['s_min']}-{color_def['s_max']}], V: [{color_def['v_min']}-{color_def['v_max']}]"
        )
