"""
Compact Window (Chế độ thu gọn mini widget)
Kích thước nhỏ gọn, luôn nổi trên cùng màn hình (Always on Top),
hiển thị trạng thái realtime và nút bấm điều khiển nhanh cho game thủ.
"""

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox, QFrame
)
from core.engine import EngineState


COMPACT_STYLESHEET = """
QWidget#compact_root {
    background-color: #0F172A;
    border: 1px solid #334155;
    border-radius: 10px;
}
QLabel {
    color: #F8FAFC;
    font-family: "Segoe UI", Arial, sans-serif;
}
QPushButton {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 12px;
    color: #F8FAFC;
    font-weight: 600;
    font-size: 12px;
}
QPushButton:hover {
    background-color: #334155;
    border-color: #475569;
}
QPushButton#btn_start {
    background-color: #4F46E5;
    border: 1px solid #6366F1;
    color: #FFFFFF;
}
QPushButton#btn_start:hover {
    background-color: #4338CA;
}
QPushButton#btn_stop {
    background-color: #7F1D1D;
    border: 1px solid #DC2626;
    color: #FCA5A5;
}
QPushButton#btn_stop:hover {
    background-color: #991B1B;
    color: #FFFFFF;
}
QCheckBox {
    color: #94A3B8;
    font-size: 11px;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #334155;
    border-radius: 3px;
    background-color: #0F172A;
}
QCheckBox::indicator:checked {
    background-color: #6366F1;
    border-color: #818CF8;
}
"""


class CompactWindow(QWidget):
    """Mini widget nổi tiện dụng khi chơi game."""
    sig_expand = Signal()

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.engine = main_window.engine
        self.init_ui()
        self._connect_signals()

    def init_ui(self):
        self.setObjectName("compact_root")
        self.setWindowTitle("Smart Auto Click — Mini")
        self.setFixedSize(330, 220)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setStyleSheet(COMPACT_STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # ── Header bar (Custom drag bar) ──
        header = QHBoxLayout()
        header.setSpacing(6)

        lbl_app = QLabel("🎯 Smart Auto Click")
        lbl_app.setFont(QFont("Segoe UI", 10, QFont.Bold))
        lbl_app.setStyleSheet("color: #4da6ff;")
        header.addWidget(lbl_app)
        header.addStretch()

        self.chk_ontop = QCheckBox("Ghim")
        self.chk_ontop.setChecked(True)
        self.chk_ontop.toggled.connect(self._toggle_always_on_top)
        header.addWidget(self.chk_ontop)

        btn_expand = QPushButton("⛶ Mở rộng")
        btn_expand.setToolTip("Mở lại giao diện đầy đủ")
        btn_expand.setFixedHeight(24)
        btn_expand.clicked.connect(self.expand_to_main)
        header.addWidget(btn_expand)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(24, 24)
        btn_close.setStyleSheet("QPushButton { padding: 0; background: #351a1d; border-color: #6d282f; } QPushButton:hover { background: #b02a31; }")
        btn_close.clicked.connect(self.hide_to_tray_or_main)
        header.addWidget(btn_close)

        layout.addLayout(header)

        # ── Status Badge ──
        self.lbl_status = QLabel("SẴN SÀNG")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.lbl_status.setStyleSheet(
            "background-color: #202738; color: #5bc0be; padding: 6px; "
            "border-radius: 5px; border: 1px solid #313d59;"
        )
        layout.addWidget(self.lbl_status)

        # ── Stats line (Rolls & Found) ──
        stats_layout = QHBoxLayout()
        self.lbl_rolls = QLabel("Rolls: 0")
        self.lbl_rolls.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.lbl_rolls.setStyleSheet("color: #abb6c8;")
        stats_layout.addWidget(self.lbl_rolls)
        stats_layout.addStretch()

        self.lbl_target = QLabel("Mục tiêu: Đang quét...")
        self.lbl_target.setFont(QFont("Segoe UI", 9))
        self.lbl_target.setStyleSheet("color: #8a97ab;")
        stats_layout.addWidget(self.lbl_target)
        layout.addLayout(stats_layout)

        # ── Quick Action Buttons ──
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        self.btn_start = QPushButton("▶ Bắt đầu (F6)")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.setFixedHeight(36)
        self.btn_start.clicked.connect(self.main_window.on_btn_start_clicked)
        btn_layout.addWidget(self.btn_start, 2)

        self.btn_pause = QPushButton("⏸ Tạm dừng")
        self.btn_pause.setFixedHeight(36)
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self.main_window.on_btn_pause_clicked)
        btn_layout.addWidget(self.btn_pause, 1)

        self.btn_stop = QPushButton("🛑 Dừng (F7)")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setFixedHeight(36)
        self.btn_stop.clicked.connect(self.main_window.on_btn_stop_clicked)
        btn_layout.addWidget(self.btn_stop, 2)

        layout.addLayout(btn_layout)

        # Cho phép kéo thả di chuyển cửa sổ frameless
        self._drag_pos = None

    def _connect_signals(self):
        """Kết nối các signal từ bridge của MainWindow để đồng bộ trạng thái."""
        self.main_window.bridge.sig_status.connect(self.on_status_changed)
        self.main_window.bridge.sig_roll.connect(self.on_roll_updated)
        self.main_window.bridge.sig_target_found.connect(self.on_target_found)

    def _toggle_always_on_top(self, checked: bool):
        flags = self.windowFlags()
        if checked:
            flags |= Qt.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def expand_to_main(self):
        """Ẩn compact mode và hiện lại MainWindow."""
        self.hide()
        self.main_window.showNormal()
        self.main_window.activateWindow()

    def hide_to_tray_or_main(self):
        """Đóng compact mode -> mở lại main window."""
        self.expand_to_main()

    @Slot(str)
    def on_status_changed(self, status: str):
        st_map = {
            EngineState.IDLE:    ("SẴN SÀNG",           "#5bc0be", "#202738", "#313d59"),
            EngineState.RUNNING: ("ĐANG AUTO ROLL...",  "#2ecc71", "#143321", "#28a745"),
            EngineState.PAUSED:  ("TẠM DỪNG (F6)",      "#f39c12", "#3a2a12", "#f39c12"),
            EngineState.STOPPED: ("ĐÃ DỪNG",            "#e74c3c", "#3d191d", "#dc3545"),
        }
        text, fg, bg, border = st_map.get(status, (status, "#ffffff", "#202738", "#4da6ff"))
        self.lbl_status.setText(text)
        self.lbl_status.setStyleSheet(
            f"background-color: {bg}; color: {fg}; padding: 6px; "
            f"border-radius: 5px; border: 1px solid {border}; font-weight: bold;"
        )
        self.btn_start.setEnabled(status != EngineState.RUNNING)
        self.btn_pause.setEnabled(status in (EngineState.RUNNING, EngineState.PAUSED))
        self.btn_pause.setText("▶ Tiếp tục" if status == EngineState.PAUSED else "⏸ Tạm dừng")

    @Slot(int, dict)
    def on_roll_updated(self, roll_count: int, analysis: dict):
        self.lbl_rolls.setText(f"Rolls: {roll_count}")

    @Slot(str, float, str)
    def on_target_found(self, color_name: str, percent: float, screenshot_path: str):
        self.lbl_target.setText(f"✨ Tìm thấy: {color_name} ({percent}%)")
        self.lbl_target.setStyleSheet("color: #ffe74c; font-weight: bold;")
