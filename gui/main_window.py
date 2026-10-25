import os
import sys
import time
import json
from typing import Dict, Any, List, Optional

import numpy as np

from PySide6.QtCore import Qt, QTimer, Signal, QObject, Slot, QSize
from PySide6.QtGui import (
    QFont, QColor, QTextCursor, QIcon, QPixmap, QImage, QPainter, QPen, QBrush
)
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QTabWidget,
    QLabel, QPushButton, QLineEdit, QSpinBox, QDoubleSpinBox,
    QCheckBox, QTextEdit, QGroupBox, QFrame, QMessageBox, QFileDialog,
    QComboBox, QScrollArea, QSizePolicy, QDialog, QFormLayout,
    QListWidget, QListWidgetItem, QInputDialog, QSplitter, QApplication,
    QSystemTrayIcon, QMenu
)
from PySide6.QtGui import QAction

from core.config_manager import ConfigManager
from core.engine import AutoClickEngine, EngineState, SlotAction
from core.clicker import InputSimulator
from core.capture import ScreenCapture, get_shared_capture
from core.macro_recorder import MacroRecorder, MacroPlayer, save_macro, load_macro
from gui.compact_window import CompactWindow
from gui.test_inspector import TestInspectorDialog
from gui.scenario_builder import ScenarioBuilderWidget
from version import APP_VERSION, APP_NAME



DARK_STYLESHEET = """
QMainWindow, QDialog {
    background-color: #0F172A;
}
QWidget {
    color: #F8FAFC;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, "Roboto", sans-serif;
    font-size: 13px;
}
QTabWidget::pane {
    border: 1px solid #334155;
    background-color: #1E293B;
    border-radius: 8px;
    top: -1px;
}
QTabBar::tab {
    background-color: #0F172A;
    color: #94A3B8;
    border: 1px solid #334155;
    border-bottom: none;
    padding: 8px 18px;
    border-radius: 6px 6px 0 0;
    margin-right: 3px;
    font-weight: 500;
}
QTabBar::tab:selected {
    background-color: #1E293B;
    color: #C0C1FF;
    border-top: 2px solid #6366F1;
    font-weight: 600;
}
QTabBar::tab:hover {
    background-color: #1E293B;
    color: #F8FAFC;
}
QGroupBox {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 10px;
    margin-top: 14px;
    font-weight: 600;
    padding: 16px 12px 12px 12px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 8px;
    color: #C0C1FF;
    font-size: 13px;
    font-weight: 600;
}
QLabel {
    color: #CBD5E1;
}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #0F172A;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 5px 8px;
    color: #F8FAFC;
    selection-background-color: #6366F1;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #6366F1;
}
QComboBox::drop-down {
    border: none;
    padding-right: 6px;
}
QComboBox QAbstractItemView {
    background-color: #1E293B;
    border: 1px solid #334155;
    selection-background-color: #334155;
    color: #F8FAFC;
}
QPushButton {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 7px 14px;
    color: #F8FAFC;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #334155;
    border-color: #475569;
}
QPushButton:pressed {
    background-color: #0F172A;
}
QPushButton:disabled {
    background-color: #0F172A;
    color: #475569;
    border-color: #1E293B;
}
QPushButton#btn_start {
    background-color: #4F46E5;
    border: 1px solid #6366F1;
    color: #FFFFFF;
    font-weight: bold;
}
QPushButton#btn_start:hover {
    background-color: #4338CA;
}
QPushButton#btn_stop {
    background-color: #7F1D1D;
    border: 1px solid #DC2626;
    color: #FCA5A5;
    font-weight: bold;
}
QPushButton#btn_stop:hover {
    background-color: #991B1B;
    color: #FFFFFF;
}
QPushButton#btn_test {
    background-color: #1E293B;
    border: 1px solid #6366F1;
    color: #C0C1FF;
}
QPushButton#btn_test:hover {
    background-color: #312E81;
}
QPushButton#btn_region {
    background-color: #1E293B;
    border: 1px solid #6366F1;
    color: #C0C1FF;
}
QPushButton#btn_region:hover {
    background-color: #312E81;
}
QPushButton#btn_sampler {
    background-color: #312E81;
    border: 1px solid #6366F1;
    color: #C0C1FF;
}
QPushButton#btn_sampler:hover {
    background-color: #3730A3;
}
QCheckBox {
    spacing: 8px;
    color: #CBD5E1;
}
QCheckBox::indicator {
    width: 17px;
    height: 17px;
    border: 1px solid #334155;
    border-radius: 4px;
    background-color: #0F172A;
}
QCheckBox::indicator:checked {
    background-color: #6366F1;
    border-color: #818CF8;
}
QTextEdit {
    background-color: #0B132B;
    border: 1px solid #334155;
    border-radius: 6px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    color: #CBD5E1;
    padding: 8px;
}
QListWidget {
    background-color: #0F172A;
    border: 1px solid #334155;
    border-radius: 6px;
    color: #F8FAFC;
}
QListWidget::item:selected {
    background-color: #334155;
    color: #FFFFFF;
}
QScrollArea {
    border: none;
    background: transparent;
}
QScrollBar:vertical {
    background: #0F172A;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #475569;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QSplitter::handle {
    background-color: #334155;
    width: 3px;
}
"""


class EngineBridge(QObject):
    sig_log = Signal(str, str)
    sig_status = Signal(str)
    sig_roll = Signal(int, dict)
    sig_target_found = Signal(str, float, str)
    sig_slot_locked = Signal(str, str)
    sig_finished = Signal(str)


class RegionRowWidget(QWidget):
    """Row widget quản lý 1 slot quan sát với preview thumbnail thực và layout 2x2 compact."""
    request_pick = Signal(object)         # row instance
    request_delete = Signal(object)       # row instance
    request_sample_color = Signal(object) # row instance
    changed = Signal()

    def __init__(self, index: int, region: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.index = index
        self._region_name = region.get("name", f"Slot {index + 1}")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 2, 0, 4)

        # Outer card frame
        card = QFrame()
        card.setObjectName("slot_card")
        card.setStyleSheet("""
            QFrame#slot_card {
                background-color: #131B2E;
                border: 1px solid #334155;
                border-left: 3px solid #6366F1;
                border-radius: 8px;
            }
        """)
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 8, 10, 8)
        card_layout.setSpacing(12)

        # ── Column 1: Slot Indicator & Thumbnail ──
        col_preview = QVBoxLayout()
        col_preview.setSpacing(4)
        col_preview.setAlignment(Qt.AlignCenter)

        # Header Badge
        self.lbl_badge = QLabel(f"● {self._region_name}")
        self.lbl_badge.setStyleSheet("""
            background-color: #1E293B;
            color: #C0C1FF;
            font-size: 11px;
            font-weight: bold;
            padding: 2px 8px;
            border-radius: 4px;
            border: 1px solid #334155;
        """)
        self.lbl_badge.setAlignment(Qt.AlignCenter)
        col_preview.addWidget(self.lbl_badge)

        # Thumbnail Image Label (Enlarged to 140x90 for clear visibility)
        self.lbl_thumbnail = QLabel()
        self.lbl_thumbnail.setFixedSize(140, 90)
        self.lbl_thumbnail.setAlignment(Qt.AlignCenter)
        self.lbl_thumbnail.setCursor(Qt.PointingHandCursor)
        self.lbl_thumbnail.setToolTip("Click vào ảnh để phóng to xem chi tiết")
        self.lbl_thumbnail.setStyleSheet("""
            QLabel {
                background-color: #0F172A;
                border: 2px solid #334155;
                border-radius: 6px;
            }
            QLabel:hover {
                border-color: #6366F1;
            }
        """)
        self.lbl_thumbnail.mousePressEvent = self._on_thumbnail_clicked
        self._last_img_bgr = None
        col_preview.addWidget(self.lbl_thumbnail)

        # Coordinate string summary
        self.lbl_coord_info = QLabel("Chưa chụp")
        self.lbl_coord_info.setFont(QFont("Segoe UI", 9))
        self.lbl_coord_info.setStyleSheet("color: #94A3B8; font-size: 11px;")
        self.lbl_coord_info.setAlignment(Qt.AlignCenter)
        col_preview.addWidget(self.lbl_coord_info)

        card_layout.addLayout(col_preview)

        # ── Column 2: 2x2 Grid for Coordinates ──
        grid_coords = QGridLayout()
        grid_coords.setHorizontalSpacing(8)
        grid_coords.setVerticalSpacing(6)

        lbl_x = QLabel("X:")
        lbl_x.setStyleSheet("color: #94A3B8; font-weight: 600; font-size: 11px;")
        self.spin_x = QSpinBox()
        self.spin_x.setRange(0, 7680)
        self.spin_x.setValue(int(region.get("x", 400)))
        self.spin_x.setFixedWidth(78)
        grid_coords.addWidget(lbl_x, 0, 0)
        grid_coords.addWidget(self.spin_x, 0, 1)

        lbl_y = QLabel("Y:")
        lbl_y.setStyleSheet("color: #94A3B8; font-weight: 600; font-size: 11px;")
        self.spin_y = QSpinBox()
        self.spin_y.setRange(0, 4320)
        self.spin_y.setValue(int(region.get("y", 300)))
        self.spin_y.setFixedWidth(78)
        grid_coords.addWidget(lbl_y, 0, 2)
        grid_coords.addWidget(self.spin_y, 0, 3)

        lbl_w = QLabel("W:")
        lbl_w.setStyleSheet("color: #94A3B8; font-weight: 600; font-size: 11px;")
        self.spin_w = QSpinBox()
        self.spin_w.setRange(5, 3840)
        self.spin_w.setValue(int(region.get("w", 200)))
        self.spin_w.setFixedWidth(78)
        grid_coords.addWidget(lbl_w, 1, 0)
        grid_coords.addWidget(self.spin_w, 1, 1)

        lbl_h = QLabel("H:")
        lbl_h.setStyleSheet("color: #94A3B8; font-weight: 600; font-size: 11px;")
        self.spin_h = QSpinBox()
        self.spin_h.setRange(5, 2160)
        self.spin_h.setValue(int(region.get("h", 200)))
        self.spin_h.setFixedWidth(78)
        grid_coords.addWidget(lbl_h, 1, 2)
        grid_coords.addWidget(self.spin_h, 1, 3)

        card_layout.addLayout(grid_coords)
        card_layout.addStretch()

        # ── Column 3: Action Buttons ──
        col_actions = QVBoxLayout()
        col_actions.setSpacing(6)
        col_actions.setAlignment(Qt.AlignCenter)

        btn_pick = QPushButton("📍 Chọn vùng")
        btn_pick.setObjectName("btn_region")
        btn_pick.setFixedWidth(110)
        btn_pick.setFixedHeight(30)
        btn_pick.clicked.connect(lambda: self.request_pick.emit(self))
        col_actions.addWidget(btn_pick)

        btn_sample = QPushButton("🎨 Hút màu")
        btn_sample.setFixedWidth(110)
        btn_sample.setFixedHeight(28)
        btn_sample.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                border: 1px solid #334155;
                color: #38BDF8;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0369A1;
                border-color: #38BDF8;
                color: #FFFFFF;
            }
        """)
        btn_sample.clicked.connect(lambda: self.request_sample_color.emit(self))
        col_actions.addWidget(btn_sample)

        btn_del = QPushButton("✕ Xóa Slot")
        btn_del.setFixedWidth(110)
        btn_del.setFixedHeight(26)
        btn_del.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                border: 1px solid #334155;
                color: #94A3B8;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #7F1D1D;
                border-color: #EF4444;
                color: #FFFFFF;
            }
        """)
        btn_del.clicked.connect(lambda: self.request_delete.emit(self))
        col_actions.addWidget(btn_del)

        card_layout.addLayout(col_actions)
        main_layout.addWidget(card)

        # Wire spinbox updates to debounce preview refresh & notify changes
        self.spin_x.editingFinished.connect(self.update_preview)
        self.spin_y.editingFinished.connect(self.update_preview)
        self.spin_w.editingFinished.connect(self.update_preview)
        self.spin_h.editingFinished.connect(self.update_preview)

        self.spin_x.valueChanged.connect(self.changed.emit)
        self.spin_y.valueChanged.connect(self.changed.emit)
        self.spin_w.valueChanged.connect(self.changed.emit)
        self.spin_h.valueChanged.connect(self.changed.emit)

        # Initial preview after GUI is shown
        QTimer.singleShot(200, self.update_preview)

    def set_index(self, new_index: int):
        self.index = new_index
        self._region_name = f"Slot {new_index + 1}"
        self.lbl_badge.setText(f"● {self._region_name}")

    def update_preview(self):
        x = self.spin_x.value()
        y = self.spin_y.value()
        w = self.spin_w.value()
        h = self.spin_h.value()
        self.lbl_coord_info.setText(f"{x}, {y} · {w}×{h}")

        if w <= 5 or h <= 5:
            return

        # Ưu tiên dùng ScreenCapture (mss / PIL fallback) để lấy mảng numpy BGR chuẩn xác
        try:
            cap = get_shared_capture()
            img_bgr = cap.capture_region(x, y, w, h)
            if img_bgr is not None and img_bgr.size > 0:
                self._last_img_bgr = img_bgr.copy()
                ih, iw = img_bgr.shape[:2]
                import cv2
                img_rgb = cv2.cvtColor(self._last_img_bgr, cv2.COLOR_BGR2RGB)
                # Dùng format QImage.Format_RGB888 với bytesPerLine chuẩn và copy() để sở hữu bộ nhớ riêng
                qimg = QImage(img_rgb.data, iw, ih, iw * 3, QImage.Format_RGB888).copy()
                pix = QPixmap.fromImage(qimg)
                self.lbl_thumbnail.setPixmap(
                    pix.scaled(140, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                self.lbl_coord_info.setStyleSheet("color: #10B981; font-size: 11px; font-weight: bold;")
                return
        except Exception:
            pass

        # Fallback dùng Qt primaryScreen nếu ScreenCapture không khả dụng
        try:
            app = QApplication.instance()
            screen = app.primaryScreen() if app else None
            if screen is not None and w > 0 and h > 0:
                pix = screen.grabWindow(0, x, y, w, h)
                if not pix.isNull() and pix.width() > 0 and pix.height() > 0:
                    self.lbl_thumbnail.setPixmap(
                        pix.scaled(140, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    )
                    self.lbl_coord_info.setStyleSheet("color: #10B981; font-size: 11px; font-weight: bold;")
                    try:
                        import cv2
                        qimg = pix.toImage().convertToFormat(QImage.Format_RGBA8888)
                        ih, iw = qimg.height(), qimg.width()
                        bpl = qimg.bytesPerLine()
                        ptr = qimg.constBits()
                        raw_buf = np.frombuffer(ptr, dtype=np.uint8).reshape((ih, bpl))
                        arr_rgba = raw_buf[:, :iw * 4].reshape((ih, iw, 4))
                        self._last_img_bgr = cv2.cvtColor(arr_rgba, cv2.COLOR_RGBA2BGR)
                    except Exception:
                        pass
                    return
        except Exception:
            pass

        # Fallback placeholder pixmap nếu cả hai cách chụp đều chưa có hình
        pix = QPixmap(140, 90)
        pix.fill(QColor(15, 23, 42))
        p = QPainter(pix)
        p.setPen(QColor(148, 163, 184))
        p.setFont(QFont("Segoe UI", 9))
        p.drawText(pix.rect(), Qt.AlignCenter, f"Vùng {w}×{h}\n(Click để chụp)")
        p.end()
        self.lbl_thumbnail.setPixmap(pix)
        self.lbl_coord_info.setStyleSheet("color: #94A3B8; font-size: 10px;")

    def set_captured_image(self, img_bgr):
        """Cập nhật trực tiếp ảnh đã chụp từ region picker mà không cần chụp lại."""
        if img_bgr is None or img_bgr.size == 0:
            return
        self._last_img_bgr = img_bgr.copy()
        try:
            import cv2
            ok, buf = cv2.imencode(".png", self._last_img_bgr)
            if ok:
                pix = QPixmap()
                pix.loadFromData(buf.tobytes())
                self.lbl_thumbnail.setPixmap(
                    pix.scaled(140, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                self.lbl_coord_info.setStyleSheet("color: #10B981; font-size: 11px; font-weight: bold;")
        except Exception as e:
            print(f"[RegionRow] Lỗi set_captured_image: {e}")

    def _on_thumbnail_clicked(self, event):
        """Click thumbnail to view full resolution image in popup dialog."""
        img_bgr = self._last_img_bgr
        if img_bgr is None or img_bgr.size == 0:
            self.update_preview()
            img_bgr = self._last_img_bgr
        if img_bgr is None or img_bgr.size == 0:
            return

        try:
            w = self.spin_w.value()
            h = self.spin_h.value()

            dlg = QDialog(self)
            region_name = getattr(self, "_region_name", f"Slot {self.index + 1}")
            dlg.setWindowTitle(f"🔍 Ảnh Gốc Chi Tiết — {region_name} ({w}×{h})")
            dlg.setStyleSheet("background-color: #0B0F17; color: #E2E8F0;")
            v = QVBoxLayout(dlg)
            v.setContentsMargins(12, 12, 12, 12)

            lbl = QLabel()
            lbl.setAlignment(Qt.AlignCenter)

            import cv2
            # Mã hóa PNG để Qt load trực tiếp vào bộ nhớ pixmap riêng,
            # tránh tuyệt đối mọi lỗi GC buffer hoặc sai stride/DPI dẫn đến ảnh trắng
            ok, buf = cv2.imencode(".png", img_bgr)
            if not ok:
                return
            pix = QPixmap()
            pix.loadFromData(buf.tobytes())

            ih, iw = img_bgr.shape[:2]
            # Nếu ảnh nhỏ hơn 300px, phóng to 2x cho dễ nhìn
            if iw < 300 and ih < 300:
                pix = pix.scaled(iw * 2, ih * 2, Qt.KeepAspectRatio, Qt.FastTransformation)

            lbl.setPixmap(pix)
            v.addWidget(lbl)

            btn = QPushButton("Đóng")
            btn.setFixedHeight(32)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1E293B;
                    border: 1px solid #475569;
                    font-weight: bold;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #334155;
                }
            """)
            btn.clicked.connect(dlg.accept)
            v.addWidget(btn)

            dlg.exec()
        except Exception as e:
            print(f"[Thumbnail] Lỗi khi mở ảnh xem trước chi tiết: {e}")

    def get_data(self) -> Dict[str, Any]:
        return {
            "id": f"slot_{self.index + 1}",
            "name": getattr(self, "_region_name", f"Slot {self.index + 1}"),
            "x": self.spin_x.value(),
            "y": self.spin_y.value(),
            "w": self.spin_w.value(),
            "h": self.spin_h.value(),
        }

    def get_region_data(self) -> Dict[str, Any]:
        return {
            "x": self.spin_x.value(),
            "y": self.spin_y.value(),
            "w": self.spin_w.value(),
            "h": self.spin_h.value(),
        }


class MainWindow(QMainWindow):
    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.engine = AutoClickEngine(self.config_manager)

        self.bridge = EngineBridge()
        self._region_rows: List[RegionRowWidget] = []
        self._wire_engine_events()

        self._countdown_timer = QTimer(self)
        self._countdown_seconds = 0
        self._countdown_target = ""
        self._countdown_timer.timeout.connect(self._handle_countdown_tick)

        self._is_really_quitting = False
        self.compact_window: Optional[CompactWindow] = None
        self.macro_recorder = MacroRecorder()
        self.macro_player = MacroPlayer()
        self.macro_steps: List[Dict[str, Any]] = []

        self._setup_macro_events()
        self.init_ui()
        self._setup_assets_and_tray()
        self.load_config_to_ui()

    def _wire_engine_events(self):
        self.engine.on_log = lambda msg, lvl: self.bridge.sig_log.emit(msg, lvl)
        self.engine.on_status_change = lambda st: self.bridge.sig_status.emit(st)
        self.engine.on_roll_attempt = lambda cnt, res: self.bridge.sig_roll.emit(cnt, res)
        self.engine.on_target_found = lambda c, p, s: self.bridge.sig_target_found.emit(c, p, s or "")
        self.engine.on_slot_locked = lambda sid, cname: self.bridge.sig_slot_locked.emit(sid, cname)
        self.engine.on_finished = lambda r: self.bridge.sig_finished.emit(r)

        self.bridge.sig_log.connect(self.append_log)
        self.bridge.sig_status.connect(self.update_status_ui)
        self.bridge.sig_roll.connect(self.on_roll_update)
        self.bridge.sig_target_found.connect(self.on_target_found_alert)
        self.bridge.sig_slot_locked.connect(self.on_slot_locked_alert)
        self.bridge.sig_finished.connect(self.on_engine_finished)

    # ──────────────────────────────────────────────────────────────────────────
    # UI Construction
    # ──────────────────────────────────────────────────────────────────────────

    def init_ui(self):
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION} — Conditional Auto Clicker")
        self.resize(1020, 850)
        self.setMinimumSize(940, 740)
        self.setStyleSheet(DARK_STYLESHEET)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(12)
        root.setContentsMargins(16, 14, 16, 14)

        # ── Header ──
        header = QHBoxLayout()
        header.setSpacing(10)

        title_box = QHBoxLayout()
        title_box.setSpacing(8)
        lbl_title = QLabel("🎯 SMART AUTO CLICK")
        lbl_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        lbl_title.setStyleSheet("color: #C0C1FF; letter-spacing: 0.5px;")
        title_box.addWidget(lbl_title)

        lbl_ver = QLabel(f"v{APP_VERSION}")
        lbl_ver.setStyleSheet("background-color: #312E81; color: #C0C1FF; font-size: 10px; font-weight: bold; padding: 2px 7px; border-radius: 4px;")
        title_box.addWidget(lbl_ver)
        header.addLayout(title_box)

        header.addStretch()

        # Compact Window Button
        btn_compact = QPushButton("📐 Giao diện gọn")
        btn_compact.setToolTip("Thu nhỏ thành mini widget nổi trên cùng khi chơi game")
        btn_compact.clicked.connect(self.show_compact_mode)
        header.addWidget(btn_compact)

        # Profile selector
        lbl_prof = QLabel("Profile:")
        lbl_prof.setStyleSheet("color: #94A3B8; font-weight: 600;")
        header.addWidget(lbl_prof)
        self.cmb_profile = QComboBox()
        self.cmb_profile.setFixedWidth(130)
        self.cmb_profile.currentTextChanged.connect(self._on_profile_changed)
        header.addWidget(self.cmb_profile)
        btn_save_profile = QPushButton("+ Lưu")
        btn_save_profile.setToolTip("Lưu cấu hình hiện tại thành Profile mới")
        btn_save_profile.clicked.connect(self._save_current_as_profile)
        header.addWidget(btn_save_profile)

        btn_del_profile = QPushButton("✕ Xóa")
        btn_del_profile.setToolTip("Xóa profile đang chọn")
        btn_del_profile.clicked.connect(self._delete_current_profile)
        header.addWidget(btn_del_profile)

        # Save Config Button in Header
        self.btn_save_cfg = QPushButton("💾 Lưu cấu hình")
        self.btn_save_cfg.setToolTip("Lưu toàn bộ thiết lập hiện tại vào file config")
        self.btn_save_cfg.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                border: 1px solid #3B82F6;
                color: #60A5FA;
                font-weight: 600;
                padding: 4px 10px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #2563EB;
                color: #FFFFFF;
            }
        """)
        self.btn_save_cfg.clicked.connect(lambda: self.save_ui_to_config(show_msg=True))
        header.addWidget(self.btn_save_cfg)

        # Pill Status Badge
        self.lbl_status = QLabel("● SẴN SÀNG")
        self.lbl_status.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.lbl_status.setStyleSheet("""
            background-color: #1E293B;
            color: #94A3B8;
            padding: 5px 14px;
            border-radius: 9999px;
            border: 1px solid #334155;
        """)
        header.addWidget(self.lbl_status)
        root.addLayout(header)

        # ── Tabs ──
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        tab_click = self._build_tab_click()
        self.tab_scenario = ScenarioBuilderWidget(
            slots=[r.get_data() for r in self._region_rows],
            roll_coord={"x": self.spin_roll_x.value(), "y": self.spin_roll_y.value()},
            parent=self
        )
        self.tab_scenario.request_test.connect(self.on_btn_test_single)
        self.tab_scenario.request_start.connect(self.on_btn_start_clicked)

        self.tabs.addTab(self.tab_scenario, "📋 1. Kịch bản (Scenario)")
        self.tabs.addTab(tab_click, "📦 2. Quản lý Slot & Roll")
        self.tabs.addTab(self._build_tab_colors(), "🎨 3. Màu & Cài đặt Thủ công")
        self.tabs.addTab(self._build_tab_advanced(), "⚙️ 4. Nâng cao")
        self.tabs.addTab(self._build_tab_macro(), "🎬 5. Macro Chuột")
        self.tabs.addTab(self._build_tab_log(), "📝 6. Nhật ký")

        # Wire coordinate changes to scenario update
        self.spin_roll_x.valueChanged.connect(self._sync_slots_to_scenario)
        self.spin_roll_y.valueChanged.connect(self._sync_slots_to_scenario)

        # ── Compact Bottom Bar (Single slim row, ~30px height) ──
        act = QHBoxLayout()
        act.setContentsMargins(2, 2, 2, 2)
        act.setSpacing(8)

        self.btn_start = QPushButton("▶ Bắt đầu (F6)")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.btn_start.setFixedHeight(30)
        self.btn_start.clicked.connect(self.on_btn_start_clicked)
        act.addWidget(self.btn_start, 2)

        self.btn_pause = QPushButton("⏸ Tạm dừng (F6)")
        self.btn_pause.setFixedHeight(30)
        self.btn_pause.clicked.connect(self.on_btn_pause_clicked)
        act.addWidget(self.btn_pause, 1)

        self.btn_stop = QPushButton("🛑 Dừng khẩn cấp (F7)")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.btn_stop.setFixedHeight(30)
        self.btn_stop.clicked.connect(self.on_btn_stop_clicked)
        act.addWidget(self.btn_stop, 2)

        lbl_tip = QLabel("💡 F6: Start/Pause  ·  F7: Dừng khẩn cấp")
        lbl_tip.setStyleSheet("color: #64748B; font-size: 11px;")
        lbl_tip.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        act.addWidget(lbl_tip, 2)

        root.addLayout(act)

    # ── Tab 1: Click & Vùng ──────────────────────────────────────────────────

    def _build_tab_click(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)
        lay.setContentsMargins(12, 12, 12, 12)

        # Roll button
        grp_roll = QGroupBox("Vị trí nút ROLL trong Game")
        g = QGridLayout(grp_roll)
        g.addWidget(QLabel("Tọa độ X:"), 0, 0)
        self.spin_roll_x = QSpinBox(); self.spin_roll_x.setRange(0, 7680)
        g.addWidget(self.spin_roll_x, 0, 1)
        g.addWidget(QLabel("Tọa độ Y:"), 0, 2)
        self.spin_roll_y = QSpinBox(); self.spin_roll_y.setRange(0, 4320)
        g.addWidget(self.spin_roll_y, 0, 3)
        self.btn_pick_roll = QPushButton("📍 Lấy tọa độ chuột (sau 3s)")
        self.btn_pick_roll.clicked.connect(lambda: self.start_coord_countdown("roll"))
        g.addWidget(self.btn_pick_roll, 1, 0, 1, 4)
        lay.addWidget(grp_roll)

        # Multi-slot regions
        grp_regions = QGroupBox("Vùng quan sát kết quả (Multi-Slot)")
        vr = QVBoxLayout(grp_regions)
        vr.setSpacing(8)

        btn_row = QHBoxLayout()
        self.btn_add_slot = QPushButton("+ Thêm Slot")
        self.btn_add_slot.clicked.connect(lambda: self._add_region_slot())
        btn_row.addWidget(self.btn_add_slot)
        self.btn_pick_region_overlay = QPushButton("🖱️ Kéo thả chọn vùng trên màn hình")
        self.btn_pick_region_overlay.setObjectName("btn_region")
        self.btn_pick_region_overlay.clicked.connect(lambda: self._open_region_picker(0))
        btn_row.addWidget(self.btn_pick_region_overlay)
        btn_row.addStretch()
        vr.addLayout(btn_row)

        self._regions_container = QWidget()
        self._regions_vbox = QVBoxLayout(self._regions_container)
        self._regions_vbox.setSpacing(6)
        self._regions_vbox.setContentsMargins(0, 0, 0, 0)

        scroll_r = QScrollArea()
        scroll_r.setWidgetResizable(True)
        scroll_r.setWidget(self._regions_container)
        scroll_r.setMinimumHeight(170)
        scroll_r.setMaximumHeight(280)
        vr.addWidget(scroll_r)
        lay.addWidget(grp_regions)

        # Test button
        self.btn_test = QPushButton("🔍 Test nhận diện 1 lần (không click Roll)")
        self.btn_test.setObjectName("btn_test")
        self.btn_test.setFixedHeight(38)
        self.btn_test.clicked.connect(self.on_btn_test_single)
        lay.addWidget(self.btn_test)
        lay.addStretch()
        return w

    # ── Tab 2: Màu & Điều kiện ───────────────────────────────────────────────

    def _build_tab_colors(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)
        lay.setContentsMargins(12, 12, 12, 12)

        # Target colors
        grp_targets = QGroupBox("Màu sắc cần Dừng khi phát hiện (Target Colors)")
        vt = QVBoxLayout(grp_targets)
        row1 = QHBoxLayout()
        self.chk_purple = QCheckBox("🟣 Tím (Purple / Epic)")
        self.chk_red = QCheckBox("🔴 Đỏ (Red / Mythic)")
        self.chk_gold = QCheckBox("🟡 Vàng (Gold / Legendary)")
        row1.addWidget(self.chk_purple)
        row1.addWidget(self.chk_red)
        row1.addWidget(self.chk_gold)
        row2 = QHBoxLayout()
        self.chk_blue = QCheckBox("🔵 Xanh dương (Blue / Rare)")
        self.chk_green = QCheckBox("🟢 Xanh lá (Green / Uncommon)")
        row2.addWidget(self.chk_blue)
        row2.addWidget(self.chk_green)
        row2.addStretch()
        vt.addLayout(row1)
        vt.addLayout(row2)

        # Threshold
        thr_row = QHBoxLayout()
        thr_row.addWidget(QLabel("Ngưỡng diện tích tối thiểu (%):"))
        self.spin_threshold = QDoubleSpinBox()
        self.spin_threshold.setRange(0.1, 100.0)
        self.spin_threshold.setSingleStep(0.5)
        self.spin_threshold.setValue(1.0)
        self.spin_threshold.setToolTip("Phần trăm pixel trong vùng phải khớp màu để được coi là 'phát hiện'")
        thr_row.addWidget(self.spin_threshold)
        thr_row.addStretch()
        vt.addLayout(thr_row)
        lay.addWidget(grp_targets)

        # Action rules per color
        grp_rules = QGroupBox("Hành động theo từng màu (Action Rules)")
        gr = QGridLayout(grp_rules)
        gr.addWidget(QLabel("Màu"), 0, 0)
        gr.addWidget(QLabel("Hành động khi phát hiện"), 0, 1)
        gr.addWidget(QLabel("Áp dụng"), 0, 2)

        self._rule_combos: Dict[str, QComboBox] = {}
        self._rule_active: Dict[str, QCheckBox] = {}
        colors_info = [
            ("purple", "Tím (Purple)", "#9b59b6"),
            ("red", "Đỏ (Red)", "#e74c3c"),
            ("gold", "Vàng (Gold)", "#f39c12"),
            ("blue", "Xanh dương (Blue)", "#2980b9"),
            ("green", "Xanh lá (Green)", "#27ae60"),
        ]
        for i, (key, label, color) in enumerate(colors_info):
            lbl = QLabel(f"● {label}")
            lbl.setStyleSheet(f"color: {color}; font-weight: bold;")
            gr.addWidget(lbl, i+1, 0)

            cmb = QComboBox()
            cmb.addItem("stop — Dừng ngay lập tức (Khuyến nghị)", "stop")
            cmb.addItem("skip/lock — Bỏ qua slot này phía bot (Tiếp tục roll các ô khác)", "lock")
            cmb.setToolTip(
                "Lưu ý với 'skip/lock': Bot chỉ bỏ qua việc quét ô này và roll các ô còn lại.\n"
                "Game vẫn có thể ghi đè nếu game roll đồng thời cả bộ slot!\n"
                "Hãy chọn 'stop' nếu game không hỗ trợ khóa từng ô riêng biệt."
            )
            self._rule_combos[key] = cmb
            gr.addWidget(cmb, i+1, 1)

            chk = QCheckBox()
            chk.setChecked(True)
            self._rule_active[key] = chk
            gr.addWidget(chk, i+1, 2)

        lay.addWidget(grp_rules)

        # Color sampler button
        grp_custom = QGroupBox("Màu tùy chỉnh (Custom Color Sampler)")
        vc = QVBoxLayout(grp_custom)
        lbl_hint = QLabel("Bấm nút bên dưới để chụp màn hình và click vào vùng đồ để hút màu HSV chính xác.")
        lbl_hint.setWordWrap(True)
        vc.addWidget(lbl_hint)
        self.btn_sampler = QPushButton("🎨 Mở Color Sampler (hút màu từ màn hình)")
        self.btn_sampler.setObjectName("btn_sampler")
        self.btn_sampler.clicked.connect(lambda: self._open_color_sampler())
        vc.addWidget(self.btn_sampler)
        self.lbl_custom_colors = QLabel("Chưa có màu tùy chỉnh.")
        self.lbl_custom_colors.setWordWrap(True)
        vc.addWidget(self.lbl_custom_colors)
        lay.addWidget(grp_custom)
        lay.addStretch()
        return w

    # ── Tab 3: Nâng cao ──────────────────────────────────────────────────────

    def _build_tab_advanced(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)
        lay.setContentsMargins(12, 12, 12, 12)

        # Timing
        grp_timing = QGroupBox("Thiết lập thời gian")
        gtime = QGridLayout(grp_timing)
        gtime.addWidget(QLabel("Chờ giữa mỗi lần Roll (s):"), 0, 0)
        self.spin_delay = QDoubleSpinBox()
        self.spin_delay.setRange(0.2, 60.0)
        self.spin_delay.setSingleStep(0.1)
        self.spin_delay.setValue(1.5)
        gtime.addWidget(self.spin_delay, 0, 1)

        gtime.addWidget(QLabel("Độ lệch ngẫu nhiên (± ms):"), 0, 2)
        self.spin_delay_jitter = QSpinBox()
        self.spin_delay_jitter.setRange(0, 5000)
        self.spin_delay_jitter.setSingleStep(50)
        self.spin_delay_jitter.setValue(100)
        self.spin_delay_jitter.setToolTip("Tự động cộng/trừ ngẫu nhiên một khoảng mili-giây giữa các click để giả lập người thật và chống anti-macro của game.")
        gtime.addWidget(self.spin_delay_jitter, 0, 3)

        gtime.addWidget(QLabel("Số lần Roll tối đa:"), 1, 0)
        self.spin_max_rolls = QSpinBox()
        self.spin_max_rolls.setRange(1, 1000000)
        self.spin_max_rolls.setValue(100)
        gtime.addWidget(self.spin_max_rolls, 1, 1)
        lay.addWidget(grp_timing)

        # Animation Detection
        grp_anim = QGroupBox("Phát hiện Animation kết thúc (thay thế chờ cố định)")
        ganim = QGridLayout(grp_anim)
        self.chk_anim = QCheckBox("Bật tính năng phát hiện animation kết thúc tự động")
        self.chk_anim.setToolTip(
            "Thay vì chờ cố định X giây sau mỗi click Roll, phần mềm sẽ theo dõi màn hình\n"
            "và tự biết khi animation (hiệu ứng roll) đã xong để tiếp tục ngay."
        )
        ganim.addWidget(self.chk_anim, 0, 0, 1, 4)
        ganim.addWidget(QLabel("Ngưỡng ổn định (%px thay đổi):"), 1, 0)
        self.spin_anim_thresh = QDoubleSpinBox()
        self.spin_anim_thresh.setRange(0.1, 20.0)
        self.spin_anim_thresh.setSingleStep(0.5)
        self.spin_anim_thresh.setValue(1.5)
        self.spin_anim_thresh.setToolTip("% pixel thay đổi tối đa giữa 2 frame để coi là 'đã tĩnh'. Thấp hơn = nhạy hơn.")
        ganim.addWidget(self.spin_anim_thresh, 1, 1)
        ganim.addWidget(QLabel("Số frame tĩnh tối thiểu:"), 1, 2)
        self.spin_anim_frames = QSpinBox()
        self.spin_anim_frames.setRange(1, 10)
        self.spin_anim_frames.setValue(2)
        ganim.addWidget(self.spin_anim_frames, 1, 3)
        ganim.addWidget(QLabel("Timeout tối đa (s):"), 2, 0)
        self.spin_anim_wait = QDoubleSpinBox()
        self.spin_anim_wait.setRange(1.0, 30.0)
        self.spin_anim_wait.setSingleStep(0.5)
        self.spin_anim_wait.setValue(6.0)
        ganim.addWidget(self.spin_anim_wait, 2, 1)
        lay.addWidget(grp_anim)

        # Budget Guard
        grp_budget = QGroupBox("Budget Guard — Dừng khi hết tiền")
        gbud = QGridLayout(grp_budget)
        self.chk_budget = QCheckBox("Bật Budget Guard (theo dõi độ sáng nút Roll)")
        self.chk_budget.setToolTip(
            "Phát hiện khi nút Roll bị mờ/disabled (hết tiền) bằng cách so sánh\n"
            "độ sáng vùng nút Roll với giá trị ban đầu khi bắt đầu chạy."
        )
        gbud.addWidget(self.chk_budget, 0, 0, 1, 4)
        gbud.addWidget(QLabel("Vùng nút Roll X:"), 1, 0)
        self.spin_bg_x = QSpinBox(); self.spin_bg_x.setRange(0, 7680)
        gbud.addWidget(self.spin_bg_x, 1, 1)
        gbud.addWidget(QLabel("Y:"), 1, 2)
        self.spin_bg_y = QSpinBox(); self.spin_bg_y.setRange(0, 4320)
        gbud.addWidget(self.spin_bg_y, 1, 3)
        gbud.addWidget(QLabel("Rộng:"), 2, 0)
        self.spin_bg_w = QSpinBox(); self.spin_bg_w.setRange(10, 500); self.spin_bg_w.setValue(100)
        gbud.addWidget(self.spin_bg_w, 2, 1)
        gbud.addWidget(QLabel("Cao:"), 2, 2)
        self.spin_bg_h = QSpinBox(); self.spin_bg_h.setRange(10, 500); self.spin_bg_h.setValue(35)
        gbud.addWidget(self.spin_bg_h, 2, 3)
        gbud.addWidget(QLabel("Ngưỡng độ tối (0-255):"), 3, 0)
        self.spin_bg_drop = QDoubleSpinBox()
        self.spin_bg_drop.setRange(5.0, 200.0)
        self.spin_bg_drop.setSingleStep(5.0)
        self.spin_bg_drop.setValue(30.0)
        self.spin_bg_drop.setToolTip("Nút Roll tối hơn ban đầu bao nhiêu thì coi là 'disabled'")
        gbud.addWidget(self.spin_bg_drop, 3, 1)
        self.btn_pick_budget = QPushButton("📍 Lấy góc trên-trái vùng nút Roll (3s)")
        self.btn_pick_budget.clicked.connect(lambda: self.start_coord_countdown("budget"))
        gbud.addWidget(self.btn_pick_budget, 4, 0, 1, 4)
        lay.addWidget(grp_budget)

        # Misc
        grp_misc = QGroupBox("Tuỳ chọn thêm")
        gm = QHBoxLayout(grp_misc)
        self.chk_play_sound = QCheckBox("🔔 Phát âm thanh khi tìm thấy")
        self.chk_save_screenshot = QCheckBox("📸 Tự động lưu ảnh màn hình")
        gm.addWidget(self.chk_play_sound)
        gm.addWidget(self.chk_save_screenshot)
        self.btn_open_shots = QPushButton("📂 Mở thư mục Screenshots")
        self.btn_open_shots.clicked.connect(self.open_screenshots_dir)
        gm.addWidget(self.btn_open_shots)
        lay.addWidget(grp_misc)
        lay.addStretch()
        return w

    # ── Tab 4: Macro Chuột ───────────────────────────────────────────────────

    def _build_tab_macro(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)
        lay.setContentsMargins(12, 12, 12, 12)

        # Macro controls header
        grp_ctrl = QGroupBox("Điều khiển Ghi & Phát Macro Thao Tác Chuột")
        gc = QVBoxLayout(grp_ctrl)

        row_btns = QHBoxLayout()
        self.btn_macro_rec = QPushButton("🔴 Bắt đầu Ghi (Record)")
        self.btn_macro_rec.setStyleSheet("QPushButton { background-color: #8c252a; border-color: #dc3545; } QPushButton:hover { background-color: #b02a31; }")
        self.btn_macro_rec.clicked.connect(self._toggle_macro_record)
        row_btns.addWidget(self.btn_macro_rec, 2)

        self.btn_macro_play = QPushButton("▶ Phát lại Macro")
        self.btn_macro_play.setObjectName("btn_start")
        self.btn_macro_play.clicked.connect(self._toggle_macro_play)
        row_btns.addWidget(self.btn_macro_play, 2)

        self.btn_macro_stop = QPushButton("⏹ Dừng")
        self.btn_macro_stop.clicked.connect(self._stop_macro_all)
        row_btns.addWidget(self.btn_macro_stop, 1)

        gc.addLayout(row_btns)

        # Options
        row_opt = QHBoxLayout()
        row_opt.addWidget(QLabel("Tốc độ phát:"))
        self.cmb_macro_speed = QComboBox()
        self.cmb_macro_speed.addItem("0.5x (Chậm)", 0.5)
        self.cmb_macro_speed.addItem("1.0x (Chuẩn)", 1.0)
        self.cmb_macro_speed.addItem("2.0x (Nhanh gấp đôi)", 2.0)
        self.cmb_macro_speed.addItem("5.0x (Siêu tốc)", 5.0)
        self.cmb_macro_speed.setCurrentIndex(1)
        row_opt.addWidget(self.cmb_macro_speed)

        row_opt.addWidget(QLabel("Số vòng lặp:"))
        self.spin_macro_loop = QSpinBox()
        self.spin_macro_loop.setRange(1, 99999)
        self.spin_macro_loop.setValue(1)
        row_opt.addWidget(self.spin_macro_loop)

        self.chk_macro_inf = QCheckBox("Lặp vô hạn")
        row_opt.addWidget(self.chk_macro_inf)
        row_opt.addStretch()
        gc.addLayout(row_opt)

        lay.addWidget(grp_ctrl)

        # Steps list
        grp_list = QGroupBox("Danh sách các bước thao tác đã ghi")
        gl = QVBoxLayout(grp_list)

        bar_file = QHBoxLayout()
        self.lbl_macro_count = QLabel("Tổng số bước: 0")
        bar_file.addWidget(self.lbl_macro_count)
        bar_file.addStretch()

        btn_macro_clear = QPushButton("🗑 Xóa hết")
        btn_macro_clear.clicked.connect(self._clear_macro_steps)
        bar_file.addWidget(btn_macro_clear)

        btn_macro_save = QPushButton("💾 Lưu File .json")
        btn_macro_save.clicked.connect(self._save_macro_file)
        bar_file.addWidget(btn_macro_save)

        btn_macro_load = QPushButton("📂 Nạp File .json")
        btn_macro_load.clicked.connect(self._load_macro_file)
        bar_file.addWidget(btn_macro_load)

        gl.addLayout(bar_file)

        self.lst_macro = QListWidget()
        gl.addWidget(self.lst_macro)

        lay.addWidget(grp_list)
        return w

    # ── Tab 5: Log ───────────────────────────────────────────────────────────

    def _build_tab_log(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 10, 12, 10)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("📋 Nhật ký hoạt động:"))
        bar.addStretch()
        self.btn_clear_log = QPushButton("Xóa Log")
        bar.addWidget(self.btn_clear_log)
        lay.addLayout(bar)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.btn_clear_log.clicked.connect(self.log_text.clear)
        lay.addWidget(self.log_text)
        return w

    # ──────────────────────────────────────────────────────────────────────────
    # Config load / save
    # ──────────────────────────────────────────────────────────────────────────

    def load_config_to_ui(self):
        btn = self.config_manager.get_roll_button()
        self.spin_roll_x.setValue(btn.get("x", 1000))
        self.spin_roll_y.setValue(btn.get("y", 600))

        # Regions
        for rw in self._region_rows:
            rw.setParent(None)
        self._region_rows.clear()
        for region in self.config_manager.get_watch_regions():
            self._add_region_slot(region)
        if not self._region_rows:
            self._add_region_slot()

        targets = self.config_manager.get_target_colors()
        self.chk_purple.setChecked("purple" in targets)
        self.chk_red.setChecked("red" in targets)
        self.chk_gold.setChecked("gold" in targets)
        self.chk_blue.setChecked("blue" in targets)
        self.chk_green.setChecked("green" in targets)

        self.spin_threshold.setValue(float(self.config_manager.get("match_threshold_percent", 1.0)))
        self.spin_delay.setValue(float(self.config_manager.get("delay_between_rolls", 1.5)))
        self.spin_delay_jitter.setValue(int(self.config_manager.get("delay_random_offset_ms", 100)))
        self.spin_max_rolls.setValue(int(self.config_manager.get("max_rolls", 100)))
        self.chk_play_sound.setChecked(bool(self.config_manager.get("play_sound", True)))
        self.chk_save_screenshot.setChecked(bool(self.config_manager.get("save_screenshot", True)))

        # Action rules
        rules = self.config_manager.get("action_rules", {})
        for key, cmb in self._rule_combos.items():
            rule_val = rules.get(key, "stop")
            idx = cmb.findData(rule_val)
            if idx >= 0:
                cmb.setCurrentIndex(idx)
            self._rule_active[key].setChecked(key in targets or key in rules)

        # Advanced
        self.chk_anim.setChecked(bool(self.config_manager.get("use_animation_detection", False)))
        self.spin_anim_thresh.setValue(float(self.config_manager.get("anim_stable_threshold", 1.5)))
        self.spin_anim_frames.setValue(int(self.config_manager.get("anim_stable_frames", 2)))
        self.spin_anim_wait.setValue(float(self.config_manager.get("anim_max_wait", 6.0)))

        bg = self.config_manager.get("budget_guard", {})
        roll_btn = self.config_manager.get_roll_button()
        self.chk_budget.setChecked(bool(bg.get("enabled", False)))
        self.spin_bg_x.setValue(int(bg.get("x", roll_btn.get("x", 920))))
        self.spin_bg_y.setValue(int(bg.get("y", roll_btn.get("y", 585))))
        self.spin_bg_w.setValue(int(bg.get("w", 100)))
        self.spin_bg_h.setValue(int(bg.get("h", 35)))
        self.spin_bg_drop.setValue(float(bg.get("brightness_drop", 30.0)))

        # Profiles
        self._refresh_profiles_combo()

        # Custom colors
        self._refresh_custom_colors_label()
        self.append_log("Da tai cau hinh thanh cong.", "INFO")

    def save_ui_to_config(self, show_msg: bool = False):
        # Đồng bộ các bước từ Scenario Builder vào UI controls
        if hasattr(self, "tab_scenario"):
            try:
                steps = self.tab_scenario.get_scenario_data()
                for st in steps:
                    stype = st.get("type")
                    if stype == "click":
                        target = st.get("target", "roll")
                        if target.startswith("slot_"):
                            s_idx = int(target.replace("slot_", ""))
                            if s_idx < len(self._region_rows):
                                r = self._region_rows[s_idx]
                                self.spin_roll_x.setValue(r.spin_x.value() + r.spin_w.value() // 2)
                                self.spin_roll_y.setValue(r.spin_y.value() + r.spin_h.value() // 2)
                    elif stype == "wait":
                        if "delay" in st:
                            self.spin_delay.setValue(st["delay"])
                        if "jitter" in st:
                            self.spin_delay_jitter.setValue(st["jitter"])
                        if "mode" in st:
                            self.chk_anim.setChecked(st["mode"] == "animation")
                    elif stype == "check_color":
                        if "threshold" in st:
                            self.spin_threshold.setValue(st["threshold"])
                        if "rules" in st:
                            rules = st["rules"]
                            for ck, act in rules.items():
                                if ck in self._rule_combos:
                                    idx = self._rule_combos[ck].findData(act)
                                    if idx >= 0:
                                        self._rule_combos[ck].setCurrentIndex(idx)
                                    if ck in self._rule_active:
                                        self._rule_active[ck].setChecked(act != "ignore")
                    elif stype == "loop":
                        if "max_loop" in st:
                            self.spin_max_rolls.setValue(st["max_loop"])
            except Exception:
                pass

        self.config_manager.set_roll_button(self.spin_roll_x.value(), self.spin_roll_y.value(), auto_save=False)

        # Regions from rows
        regions = self.config_manager.get_watch_regions()
        for i, row in enumerate(self._region_rows):
            rd = row.get_region_data()
            if i < len(regions):
                regions[i].update(rd)
            else:
                regions.append({**rd, "id": f"slot_{i+1}", "name": f"Slot {i+1}"})
        # Truncate if rows were deleted
        while len(regions) > len(self._region_rows):
            regions.pop()
        self.config_manager.data["watch_regions"] = regions

        targets = []
        if self.chk_purple.isChecked(): targets.append("purple")
        if self.chk_red.isChecked(): targets.append("red")
        if self.chk_gold.isChecked(): targets.append("gold")
        if self.chk_blue.isChecked(): targets.append("blue")
        if self.chk_green.isChecked(): targets.append("green")

        # Also add custom colors from definitions that are active
        for key in list(self.config_manager.get("color_definitions", {}).keys()):
            if key not in ("purple", "red", "gold", "blue", "green"):
                if key not in targets:
                    targets.append(key)

        self.config_manager.set_target_colors(targets, auto_save=False)
        self.config_manager.set("match_threshold_percent", self.spin_threshold.value(), auto_save=False)
        self.config_manager.set("delay_between_rolls", self.spin_delay.value(), auto_save=False)
        self.config_manager.set("delay_random_offset_ms", self.spin_delay_jitter.value(), auto_save=False)
        self.config_manager.set("max_rolls", self.spin_max_rolls.value(), auto_save=False)
        self.config_manager.set("play_sound", self.chk_play_sound.isChecked(), auto_save=False)
        self.config_manager.set("save_screenshot", self.chk_save_screenshot.isChecked(), auto_save=False)

        # Action rules
        rules = {}
        for key, cmb in self._rule_combos.items():
            if self._rule_active[key].isChecked():
                rules[key] = cmb.currentData()
        self.config_manager.set("action_rules", rules, auto_save=False)

        # Advanced
        self.config_manager.set("use_animation_detection", self.chk_anim.isChecked(), auto_save=False)
        self.config_manager.set("anim_stable_threshold", self.spin_anim_thresh.value(), auto_save=False)
        self.config_manager.set("anim_stable_frames", self.spin_anim_frames.value(), auto_save=False)
        self.config_manager.set("anim_max_wait", self.spin_anim_wait.value(), auto_save=False)

        self.config_manager.set("budget_guard", {
            "enabled": self.chk_budget.isChecked(),
            "x": self.spin_bg_x.value(),
            "y": self.spin_bg_y.value(),
            "w": self.spin_bg_w.value(),
            "h": self.spin_bg_h.value(),
            "brightness_drop": self.spin_bg_drop.value(),
        }, auto_save=False)

        saved = self.config_manager.save()
        if show_msg:
            if saved:
                QMessageBox.information(self, "OK", "Da luu cau hinh thanh cong!")
            else:
                QMessageBox.warning(self, "Loi", "Khong the luu cau hinh.")

    # ──────────────────────────────────────────────────────────────────────────
    # Slot / Region management
    # ──────────────────────────────────────────────────────────────────────────

    def _add_region_slot(self, region: Optional[Dict[str, Any]] = None):
        idx = len(self._region_rows)
        if not isinstance(region, dict):
            region = None
        if region is None:
            region = {"id": f"slot_{idx+1}", "name": f"Slot {idx+1}", "x": 400, "y": 300, "w": 200, "h": 200}
        row = RegionRowWidget(idx, region)
        row.request_pick.connect(self._open_region_picker)
        row.request_delete.connect(self._delete_region_slot)
        row.request_sample_color.connect(self._on_row_sample_color_requested)
        row.changed.connect(self._sync_slots_to_scenario)
        self._region_rows.append(row)
        self._regions_vbox.addWidget(row)
        self.save_ui_to_config(show_msg=False)
        self._sync_slots_to_scenario()

    def _on_row_sample_color_requested(self, row: Any):
        if isinstance(row, RegionRowWidget) and row in self._region_rows:
            idx = self._region_rows.index(row)
            self._open_color_sampler(default_slot_idx=idx)
        elif isinstance(row, int):
            self._open_color_sampler(default_slot_idx=row)
        else:
            self._open_color_sampler()

    def _delete_region_slot(self, target: Any):
        if len(self._region_rows) <= 1:
            QMessageBox.warning(self, "Cảnh báo", "Phải giữ lại ít nhất 1 slot!")
            return

        if isinstance(target, RegionRowWidget) and target in self._region_rows:
            row = target
            self._region_rows.remove(row)
        elif isinstance(target, int) and 0 <= target < len(self._region_rows):
            row = self._region_rows.pop(target)
        else:
            return

        row.setParent(None)
        row.deleteLater()

        # Re-index và CẬP NHẬT LẠI PREVIEW cho tất cả các slot còn lại khi bị đẩy lên
        for i, r in enumerate(self._region_rows):
            r.set_index(i)
            r.update_preview()

        # Lưu ngay vào config và cập nhật sang kịch bản
        self.save_ui_to_config(show_msg=False)
        self._sync_slots_to_scenario()

    def _sync_slots_to_scenario(self):
        if hasattr(self, "tab_scenario") and hasattr(self, "_region_rows"):
            slots = [r.get_data() for r in self._region_rows]
            rx = self.spin_roll_x.value() if hasattr(self, "spin_roll_x") else 960
            ry = self.spin_roll_y.value() if hasattr(self, "spin_roll_y") else 540
            self.tab_scenario.update_slots(slots, {"x": rx, "y": ry})

    def _open_region_picker(self, target: Any):
        """Open fullscreen overlay and let user drag-select the region."""
        slot_idx = 0
        if isinstance(target, RegionRowWidget) and target in self._region_rows:
            slot_idx = self._region_rows.index(target)
        elif isinstance(target, int):
            slot_idx = target

        try:
            from gui.region_picker import pick_region
            self.hide()
            QApplication.processEvents()
            time.sleep(0.15)
            result, cropped_bgr = pick_region()
            self.show()
            self.raise_()
            if result and slot_idx < len(self._region_rows):
                x, y, w, h = result
                row = self._region_rows[slot_idx]
                row.spin_x.setValue(x)
                row.spin_y.setValue(y)
                row.spin_w.setValue(w)
                row.spin_h.setValue(h)
                if cropped_bgr is not None and cropped_bgr.size > 0:
                    row.set_captured_image(cropped_bgr)
                else:
                    row.update_preview()
                self.save_ui_to_config(show_msg=False)
                self._sync_slots_to_scenario()
                self.append_log(f"Đã chọn vùng Slot {slot_idx+1}: ({x}, {y}, {w}×{h})", "SUCCESS")
        except Exception as e:
            self.show()
            self.append_log(f"Lỗi Region Picker: {e}", "ERROR")

    # ──────────────────────────────────────────────────────────────────────────
    # Color Sampler
    # ──────────────────────────────────────────────────────────────────────────

    def _open_color_sampler(self, default_slot_idx: Optional[int] = None):
        if isinstance(default_slot_idx, bool):
            default_slot_idx = None
        try:
            from gui.color_sampler import ColorSamplerDialog
            cap = get_shared_capture()
            self.hide()
            QApplication.processEvents()
            time.sleep(0.15)
            img_bgr = cap.capture_fullscreen()
            self.show()
            self.raise_()

            slots = [r.get_data() for r in self._region_rows]
            dlg = ColorSamplerDialog(img_bgr, slots=slots, default_slot_idx=default_slot_idx, parent=self)
            dlg.color_sampled.connect(self._on_color_sampled)
            dlg.exec()
        except Exception as e:
            self.show()
            self.append_log(f"Lỗi Color Sampler: {e}", "ERROR")

    def _on_color_sampled(self, key: str, color_def: dict):
        """Add a new custom color from sampler into config."""
        defs = self.config_manager.get("color_definitions", {})
        defs[key] = color_def
        self.config_manager.set("color_definitions", defs, auto_save=True)
        self._refresh_custom_colors_label()
        self.append_log(f"Da them mau tuy chinh: {key} ({color_def.get('name', key)})", "SUCCESS")

    def _refresh_custom_colors_label(self):
        defs = self.config_manager.get("color_definitions", {})
        builtin = {"purple", "red", "gold", "blue", "green"}
        customs = [f"{k} ({v.get('name', k)})" for k, v in defs.items() if k not in builtin]
        if customs:
            self.lbl_custom_colors.setText("Mau tuy chinh da them:\n" + "\n".join(f"  • {c}" for c in customs))
        else:
            self.lbl_custom_colors.setText("Chua co mau tuy chinh.")

    # ──────────────────────────────────────────────────────────────────────────
    # Profile management
    # ──────────────────────────────────────────────────────────────────────────

    def _refresh_profiles_combo(self):
        profiles = self.config_manager.list_profiles()
        self.cmb_profile.blockSignals(True)
        self.cmb_profile.clear()
        for name in profiles:
            self.cmb_profile.addItem(name)
        active = self.config_manager.get("active_profile", "default")
        idx = self.cmb_profile.findText(active)
        if idx >= 0:
            self.cmb_profile.setCurrentIndex(idx)
        self.cmb_profile.blockSignals(False)

    def _on_profile_changed(self, name: str):
        if not name:
            return
        loaded = self.config_manager.load_profile(name)
        if loaded:
            self.load_config_to_ui()
            self.append_log(f"Da chuyen sang profile: {name} (tai day du thong so)", "INFO")

    def _save_current_as_profile(self):
        name, ok = QInputDialog.getText(self, "Luu Profile", "Nhap ten profile moi:")
        if not ok or not name.strip():
            return
        name = name.strip()
        # Lưu giao diện hiện tại vào cấu hình trước
        self.save_ui_to_config(show_msg=False)
        success = self.config_manager.save_profile(name)
        if success:
            self._refresh_profiles_combo()
            idx = self.cmb_profile.findText(name)
            if idx >= 0:
                self.cmb_profile.setCurrentIndex(idx)
            self.append_log(f"Da luu toan bo cau hinh vao profile: {name}", "SUCCESS")
        else:
            self.append_log(f"Khong the luu profile: {name}", "ERROR")

    def _delete_current_profile(self):
        name = self.cmb_profile.currentText()
        if not name or name == "default":
            QMessageBox.information(self, "Thong bao", "Khong the xoa profile mac dinh (default).")
            return
        reply = QMessageBox.question(self, "Xac nhan", f"Ban co chac muon xoa profile '{name}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.config_manager.delete_profile(name)
            self._refresh_profiles_combo()
            self.load_config_to_ui()
            self.append_log(f"Da xoa profile: {name}", "INFO")

    # ──────────────────────────────────────────────────────────────────────────
    # Countdown (pick mouse position)
    # ──────────────────────────────────────────────────────────────────────────

    def start_coord_countdown(self, target_type: str):
        self._countdown_target = target_type
        self._countdown_seconds = 3
        self._update_countdown_btn_text()
        self._set_countdown_btn_enabled(False)
        self._countdown_timer.start(1000)

    def _update_countdown_btn_text(self):
        s = self._countdown_seconds
        if self._countdown_target == "roll":
            self.btn_pick_roll.setText(f"Di chuot vao nut Roll... ({s}s)")
        elif self._countdown_target == "budget":
            self.btn_pick_budget.setText(f"Di chuot vao vung nut Roll... ({s}s)")

    def _set_countdown_btn_enabled(self, enabled: bool):
        if self._countdown_target == "roll":
            self.btn_pick_roll.setEnabled(enabled)
        elif self._countdown_target == "budget":
            self.btn_pick_budget.setEnabled(enabled)

    def _handle_countdown_tick(self):
        self._countdown_seconds -= 1
        if self._countdown_seconds > 0:
            self._update_countdown_btn_text()
        else:
            self._countdown_timer.stop()
            pos_x, pos_y = InputSimulator.get_mouse_position()
            if self._countdown_target == "roll":
                self.spin_roll_x.setValue(pos_x)
                self.spin_roll_y.setValue(pos_y)
                self.btn_pick_roll.setEnabled(True)
                self.btn_pick_roll.setText("📍 Lay toa do chuot (sau 3s)")
                self.append_log(f"Da bat toa do nut Roll: ({pos_x}, {pos_y})", "SUCCESS")
            elif self._countdown_target == "budget":
                self.spin_bg_x.setValue(pos_x)
                self.spin_bg_y.setValue(pos_y)
                self.btn_pick_budget.setEnabled(True)
                self.btn_pick_budget.setText("📍 Lay goc tren-trai vung nut Roll (3s)")
                self.append_log(f"Da bat toa do Budget Guard: ({pos_x}, {pos_y})", "SUCCESS")
            self.save_ui_to_config(show_msg=False)

    # ──────────────────────────────────────────────────────────────────────────
    # Engine control buttons
    # ──────────────────────────────────────────────────────────────────────────

    @Slot()
    def on_btn_test_single(self):
        self.save_ui_to_config(show_msg=False)
        self.append_log("--- Mở Kiểm Tra Nhận Diện Trực Quan (Test Inspector) ---", "INFO")

        slots = [r.get_data() for r in self._region_rows]
        targets = self.config_manager.get_target_colors()
        if not targets:
            targets = ["purple", "red", "gold"]
        thresh = self.spin_threshold.value() if hasattr(self, "spin_threshold") else 1.0
        rules = self.config_manager.get("action_rules", {})
        c_defs = self.config_manager.get("color_definitions", {})

        dlg = TestInspectorDialog(
            slots=slots,
            target_colors=targets,
            threshold=thresh,
            rules=rules,
            color_definitions=c_defs,
            parent=self
        )
        dlg.exec()

    def validate_and_start(self) -> bool:
        """Kiểm tra cấu hình, lưu UI và khởi động Engine nếu hợp lệ."""
        if hasattr(self, "macro_player") and self.macro_player.is_playing:
            QMessageBox.warning(self, "Xung đột tiến trình", "Macro đang phát lại! Vui lòng dừng Macro trước khi khởi động Auto Clicker.")
            return False

        self.save_ui_to_config(show_msg=False)
        targets = self.config_manager.get_target_colors()
        if not targets:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn ít nhất 1 màu mục tiêu!")
            return False
        regions = self.config_manager.get_watch_regions()
        if not regions:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng cấu hình ít nhất 1 vùng quan sát!")
            return False
        self.engine.start()
        return True

    def validate_and_toggle_pause(self):
        """Dùng chung cho phím tắt F6 và nút Start/Pause trên GUI."""
        if self.engine.state in (EngineState.IDLE, EngineState.STOPPED):
            self.validate_and_start()
        elif self.engine.state == EngineState.RUNNING:
            self.engine.pause()
        elif self.engine.state == EngineState.PAUSED:
            self.engine.resume()

    @Slot()
    def on_btn_start_clicked(self):
        self.validate_and_start()

    @Slot()
    def on_btn_pause_clicked(self):
        if self.engine.state == EngineState.RUNNING:
            self.engine.pause()
        elif self.engine.state == EngineState.PAUSED:
            self.engine.resume()

    @Slot()
    def on_btn_stop_clicked(self):
        self.engine.stop("Bam nut dung")

    # ──────────────────────────────────────────────────────────────────────────
    # Engine event slots
    # ──────────────────────────────────────────────────────────────────────────

    @Slot(str, str)
    def append_log(self, message: str, level: str = "INFO"):
        color_map = {
            "INFO": "#abb6c8", "SUCCESS": "#2ecc71",
            "WARN": "#f39c12", "ERROR": "#e74c3c", "DEBUG": "#5a6880"
        }
        color = color_map.get(level.upper(), "#c9d1d9")
        ts = time.strftime("%H:%M:%S")
        html = (
            f'<span style="color:#657388;">[{ts}]</span> '
            f'<b style="color:{color};">[{level}]</b> '
            f'<span style="color:{color};">{message}</span>'
        )
        self.log_text.append(html)
        self.log_text.moveCursor(QTextCursor.End)

    @Slot(str)
    def update_status_ui(self, status: str):
        st_map = {
            EngineState.IDLE:    ("● SẴN SÀNG",           "#94A3B8", "#1E293B", "#334155"),
            EngineState.RUNNING: ("● ĐANG AUTO ROLL...",  "#10B981", "rgba(16, 185, 129, 0.15)", "#10B981"),
            EngineState.PAUSED:  ("● TẠM DỪNG (F6)",      "#F59E0B", "rgba(245, 158, 11, 0.15)", "#F59E0B"),
            EngineState.STOPPED: ("● ĐÃ DỪNG",            "#EF4444", "rgba(239, 68, 68, 0.15)", "#EF4444"),
        }
        text, fg, bg, border = st_map.get(status, (f"● {status}", "#FFFFFF", "#1E293B", "#6366F1"))
        self.lbl_status.setText(text)
        self.lbl_status.setStyleSheet(
            f"background-color: {bg}; color: {fg}; padding: 6px 16px; "
            f"border-radius: 9999px; border: 1px solid {border}; font-weight: bold;"
        )
        is_running = (status == EngineState.RUNNING)
        if is_running:
            self.btn_start.setText("● ĐANG CHẠY...")
            self.btn_start.setStyleSheet("background-color: #10B981; border: 1px solid #34D399; color: #FFFFFF; font-weight: bold;")
        else:
            self.btn_start.setText("▶  BẮT ĐẦU  (F6)")
            self.btn_start.setStyleSheet("")

        self.btn_start.setEnabled(status not in (EngineState.RUNNING,))
        self.btn_pause.setText(
            "▶  TIẾP TỤC  (F6)" if status == EngineState.PAUSED else "⏸  TẠM DỪNG  (F6)"
        )
        self.btn_pause.setEnabled(status in (EngineState.RUNNING, EngineState.PAUSED))

        # Cập nhật icon khay hệ thống theo trạng thái (chạy/nghỉ)
        if hasattr(self, "tray_icon") and self.tray_icon:
            if is_running and os.path.exists(self.tray_running_path):
                self.tray_icon.setIcon(QIcon(self.tray_running_path))
            elif not is_running and os.path.exists(self.tray_idle_path):
                self.tray_icon.setIcon(QIcon(self.tray_idle_path))

    @Slot(int, dict)
    def on_roll_update(self, roll_count: int, analysis: dict):
        max_r = self.spin_max_rolls.value()
        self.lbl_status.setText(f"● ĐANG CHẠY: ROLL {roll_count}/{max_r}")
        self.lbl_status.setStyleSheet(
            "background-color: rgba(16, 185, 129, 0.15); color: #10B981; padding: 6px 16px; "
            "border-radius: 9999px; border: 1px solid #10B981; font-weight: bold;"
        )

    @Slot(str, float, str)
    def on_target_found_alert(self, color_name: str, percent: float, screenshot_path: str):
        self.lbl_status.setText(f"★ TÌM THẤY: {color_name.upper()}")
        self.lbl_status.setStyleSheet(
            "background-color: rgba(99, 102, 241, 0.25); color: #C0C1FF; padding: 6px 16px; "
            "border-radius: 9999px; border: 1px solid #6366F1; font-weight: bold;"
        )
        msg = f"Tìm thấy vật phẩm có màu: {color_name} ({percent}% diện tích)!\n\nTiến trình tự động dừng lại."
        if screenshot_path:
            msg += f"\nẢnh chụp: {os.path.basename(screenshot_path)}"
        QMessageBox.information(self, "Chúc Mừng!", msg)

    @Slot(str, str)
    def on_slot_locked_alert(self, slot_id: str, color_name: str):
        self.append_log(f"LOCK {slot_id}: {color_name} — Slot nay da bi khoa, tiep tuc roll cac slot con lai.", "WARN")

    @Slot(str)
    def on_engine_finished(self, reason: str):
        self.update_status_ui(EngineState.STOPPED)

    def open_screenshots_dir(self):
        shots_dir = os.path.abspath("screenshots")
        os.makedirs(shots_dir, exist_ok=True)
        try:
            os.startfile(shots_dir)
        except Exception as e:
            self.append_log(f"Khong the mo thu muc: {e}", "WARN")

    # ──────────────────────────────────────────────────────────────────────────
    # System Tray & Compact Mode
    # ──────────────────────────────────────────────────────────────────────────

    def _setup_assets_and_tray(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.assets_dir = os.path.join(base_dir, "assets")
        self.icon_ico_path = os.path.join(self.assets_dir, "icon.ico")
        self.icon_png_path = os.path.join(self.assets_dir, "icon.png")
        self.tray_idle_path = os.path.join(self.assets_dir, "tray_idle.png")
        self.tray_running_path = os.path.join(self.assets_dir, "tray_running.png")

        # Set window icon
        if os.path.exists(self.icon_ico_path):
            self.setWindowIcon(QIcon(self.icon_ico_path))
        elif os.path.exists(self.icon_png_path):
            self.setWindowIcon(QIcon(self.icon_png_path))

        # Setup System Tray Icon
        self.tray_icon = QSystemTrayIcon(self)
        if os.path.exists(self.tray_idle_path):
            self.tray_icon.setIcon(QIcon(self.tray_idle_path))
        elif os.path.exists(self.icon_ico_path):
            self.tray_icon.setIcon(QIcon(self.icon_ico_path))

        self.tray_icon.setToolTip(f"{APP_NAME} v{APP_VERSION}")

        # Tray context menu
        tray_menu = QMenu()
        act_show = tray_menu.addAction("⛶ Hiển thị cửa sổ chính")
        act_show.triggered.connect(self.restore_from_tray)

        act_compact = tray_menu.addAction("📐 Chế độ thu gọn (Mini)")
        act_compact.triggered.connect(self.show_compact_mode)

        tray_menu.addSeparator()
        act_start = tray_menu.addAction("▶ Bắt đầu (F6)")
        act_start.triggered.connect(self.on_btn_start_clicked)

        act_pause = tray_menu.addAction("⏸ Tạm dừng (F6)")
        act_pause.triggered.connect(self.on_btn_pause_clicked)

        act_stop = tray_menu.addAction("🛑 Dừng lại (F7)")
        act_stop.triggered.connect(self.on_btn_stop_clicked)

        tray_menu.addSeparator()
        act_quit = tray_menu.addAction("❌ Thoát hoàn toàn")
        act_quit.triggered.connect(self.real_quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            if self.isVisible():
                self.hide()
            else:
                self.restore_from_tray()

    def restore_from_tray(self):
        if self.compact_window and self.compact_window.isVisible():
            self.compact_window.hide()
        self.showNormal()
        self.activateWindow()

    def show_compact_mode(self):
        if not self.compact_window:
            self.compact_window = CompactWindow(self)
        self.hide()
        self.compact_window.show()
        self.compact_window.activateWindow()

    def real_quit(self):
        """Thoát hoàn toàn ứng dụng từ menu khay Taskbar."""
        self._is_really_quitting = True
        if self.engine.state == EngineState.RUNNING:
            self.engine.stop("Thoat ung dung")
        if self.macro_player.is_playing:
            self.macro_player.stop()
        if self.compact_window:
            self.compact_window.close()
        if hasattr(self, "tray_icon") and self.tray_icon:
            self.tray_icon.hide()
        self.close()
        QApplication.quit()

    # ──────────────────────────────────────────────────────────────────────────
    # Macro Recorder & Player Logic
    # ──────────────────────────────────────────────────────────────────────────

    def _setup_macro_events(self):
        self.macro_recorder.on_event_recorded = self._on_macro_event_recorded
        self.macro_player.on_step_played = self._on_macro_step_played
        self.macro_player.on_finished = self._on_macro_finished

    def _toggle_macro_record(self):
        if not self.macro_recorder.is_recording:
            try:
                self.macro_recorder.start()
                self.btn_macro_rec.setText("⏹ Dừng Ghi (Đang ghi...)")
                self.btn_macro_rec.setStyleSheet("QPushButton { background-color: #d32f2f; border-color: #ff5252; color: #ffffff; }")
                self.append_log("Dang ghi thao tac chuot... Hay click tren man hinh de ghi lai.", "WARN")
            except Exception as e:
                QMessageBox.warning(self, "Loi", f"Khong the bat dau ghi: {e}")
        else:
            steps = self.macro_recorder.stop()
            self.macro_steps = steps
            self.btn_macro_rec.setText("🔴 Bắt đầu Ghi (Record)")
            self.btn_macro_rec.setStyleSheet("QPushButton { background-color: #8c252a; border-color: #dc3545; } QPushButton:hover { background-color: #b02a31; }")
            self._refresh_macro_list()
            self.append_log(f"Da ghi xong {len(steps)} buoc thao tac chuot.", "SUCCESS")

    def _on_macro_event_recorded(self, event: Dict[str, Any]):
        QTimer.singleShot(0, lambda: self._add_macro_item_to_list(event))

    def _add_macro_item_to_list(self, step: Dict[str, Any]):
        idx = self.lst_macro.count() + 1
        btn = step.get("button", "left").upper()
        x, y = step.get("x", 0), step.get("y", 0)
        delay = step.get("delay_ms", 0)
        text = f"Buoc #{idx:02d}: Click {btn} tai ({x}, {y}) — Cho {delay}ms"
        item = QListWidgetItem(text)
        self.lst_macro.addItem(item)
        self.lst_macro.scrollToBottom()
        self.lbl_macro_count.setText(f"Tong so buoc: {self.lst_macro.count()}")

    def _refresh_macro_list(self):
        self.lst_macro.clear()
        for idx, step in enumerate(self.macro_steps, start=1):
            btn = step.get("button", "left").upper()
            x, y = step.get("x", 0), step.get("y", 0)
            delay = step.get("delay_ms", 0)
            self.lst_macro.addItem(f"Buoc #{idx:02d}: Click {btn} tai ({x}, {y}) — Cho {delay}ms")
        self.lbl_macro_count.setText(f"Tong so buoc: {len(self.macro_steps)}")

    def _toggle_macro_play(self):
        if self.engine.state == EngineState.RUNNING:
            QMessageBox.warning(self, "Xung đột tiến trình", "Auto Clicker đang chạy! Vui lòng dừng Engine trước khi phát macro.")
            return

        if not self.macro_steps:
            QMessageBox.warning(self, "Thông báo", "Chưa có thao tác nào để phát! Hãy bấm Ghi hoặc Nạp từ file.")
            return

        if not self.macro_player.is_playing:
            speed = float(self.cmb_macro_speed.currentData())
            loops = self.spin_macro_loop.value()
            inf = self.chk_macro_inf.isChecked()
            self.btn_macro_play.setText("⏸ Tạm dừng phát")
            self.append_log(f"Bắt đầu phát lại macro (Tốc độ {speed}x, Lặp: {'Vô hạn' if inf else loops} lần)...", "INFO")
            self.macro_player.play(self.macro_steps, speed=speed, loop_count=loops, infinite=inf)
        else:
            self.macro_player.stop()
            self.btn_macro_play.setText("▶ Phát lại Macro")
            self.append_log("Đã dừng phát lại macro.", "WARN")

    def _on_macro_step_played(self, idx: int, step: Dict[str, Any]):
        QTimer.singleShot(0, lambda: self.lst_macro.setCurrentRow(idx % max(1, self.lst_macro.count())))

    def _on_macro_finished(self):
        QTimer.singleShot(0, lambda: self.btn_macro_play.setText("▶ Phát lại Macro"))
        self.append_log("Đã hoàn thành chuỗi phát macro.", "SUCCESS")

    def _stop_macro_all(self):
        if self.macro_recorder.is_recording:
            self._toggle_macro_record()
        if self.macro_player.is_playing:
            self.macro_player.stop()
            self.btn_macro_play.setText("▶ Phát lại Macro")
            self.append_log("Đã dừng phát macro.", "INFO")

    def _clear_macro_steps(self):
        self._stop_macro_all()
        self.macro_steps.clear()
        self._refresh_macro_list()
        self.append_log("Đã xóa toàn bộ các bước macro.", "INFO")

    def _save_macro_file(self):
        if not self.macro_steps:
            QMessageBox.warning(self, "Thông báo", "Không có bước nào để lưu!")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Lưu Macro Thao Tác", "macro.json", "JSON Files (*.json)")
        if path:
            if save_macro(path, self.macro_steps):
                self.append_log(f"Đã lưu macro vào: {path}", "SUCCESS")
                QMessageBox.information(self, "Thành công", "Đã lưu macro thành công!")

    def _load_macro_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Mở Macro Thao Tác", "", "JSON Files (*.json)")
        if path:
            steps = load_macro(path)
            if steps:
                self.macro_steps = steps
                self._refresh_macro_list()
                self.append_log(f"Đã nạp {len(steps)} bước macro từ: {path}", "SUCCESS")
            else:
                QMessageBox.warning(self, "Lỗi", "File macro rỗng hoặc không đúng định dạng!")

    def closeEvent(self, event):
        if not self._is_really_quitting:
            if self.engine.state == EngineState.RUNNING:
                reply = QMessageBox.question(
                    self,
                    "Cảnh báo: Clicker đang chạy ngầm",
                    "Auto Clicker vẫn ĐANG CHẠY ngầm và gửi click vào màn hình!\n\n"
                    "Bạn có chắc muốn ẩn xuống khay hệ thống và TIẾP TỤC chạy không?\n"
                    "(Bấm 'No' để DỪNG clicker an toàn trước khi ẩn)",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                if reply == QMessageBox.No:
                    self.engine.stop("Người dùng dừng khi đóng cửa sổ")

            event.ignore()
            self.hide()
            if hasattr(self, "tray_icon") and self.tray_icon:
                self.tray_icon.showMessage(
                    "Smart Auto Click",
                    "Ứng dụng đang chạy ở khay hệ thống (Taskbar).\nBấm vào biểu tượng để mở lại.",
                    QSystemTrayIcon.Information,
                    2000
                )
        else:
            if self.engine.state == EngineState.RUNNING:
                self.engine.stop("Đóng ứng dụng")
            if self.macro_player.is_playing:
                self.macro_player.stop()
            self.engine.capture.close()
            event.accept()
