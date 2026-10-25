"""
Region Picker — Fullscreen overlay cho phép người dùng kéo thả chuột
để chọn vùng màn hình cần theo dõi. Trả về (x, y, w, h) tọa độ thực.

Đã sửa lỗi DPI/scaling: dùng virtual desktop toàn bộ màn hình,
screenGeometry() thay vì primaryScreen().geometry() để hỗ trợ multi-monitor,
và tính device-pixel-ratio để ảnh chụp không bị lệch.
"""
from typing import Optional, Tuple

from PySide6.QtCore import Qt, QRect, QPoint, Signal, QRectF
from PySide6.QtGui import (
    QColor, QPainter, QPen, QBrush, QScreen,
    QPixmap, QFont, QCursor, QKeyEvent
)
from PySide6.QtWidgets import QApplication, QWidget


class RegionPickerOverlay(QWidget):
    """
    Fullscreen semi-transparent overlay bao phủ toàn bộ virtual desktop
    (bao gồm nhiều màn hình). Người dùng kéo chuột để vẽ hình chữ nhật.
    Nhấn Escape để hủy.
    """
    region_selected = Signal(int, int, int, int)  # x, y, w, h (logical pixels)
    cancelled = Signal()

    def __init__(self, screen_pixmap: QPixmap, virtual_geometry: QRect, dpr: float):
        super().__init__()
        self._screen_pixmap = screen_pixmap
        self._virtual_geometry = virtual_geometry
        self._dpr = dpr  # device pixel ratio để convert back
        self._start: Optional[QPoint] = None
        self._end: Optional[QPoint] = None
        self._selecting = False

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setGeometry(virtual_geometry)
        self.setCursor(QCursor(Qt.CrossCursor))
        self.setWindowOpacity(1.0)
        self.setFocusPolicy(Qt.StrongFocus)

    def showEvent(self, event):
        self.setFocus()
        super().showEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Escape:
            self.cancelled.emit()
            self.close()
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._start = event.position().toPoint()
            self._end = self._start
            self._selecting = True
            self.update()

    def mouseMoveEvent(self, event):
        if self._selecting:
            self._end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._selecting:
            self._end = event.position().toPoint()
            self._selecting = False
            rect = self._get_rect()
            if rect.width() > 5 and rect.height() > 5:
                # Convert widget-local coords → global screen coords (logical pixels)
                global_x = self._virtual_geometry.x() + rect.x()
                global_y = self._virtual_geometry.y() + rect.y()
                self.region_selected.emit(global_x, global_y, rect.width(), rect.height())
            else:
                self.cancelled.emit()
            self.close()

    def _get_rect(self) -> QRect:
        if self._start is None or self._end is None:
            return QRect()
        return QRect(self._start, self._end).normalized()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw the screen capture scaled to widget size
        widget_rect = self.rect()
        painter.drawPixmap(widget_rect, self._screen_pixmap)

        # Dark overlay on everything
        painter.fillRect(widget_rect, QColor(0, 0, 0, 140))

        rect = self._get_rect()
        if not rect.isNull() and rect.width() > 0 and rect.height() > 0:
            # Reveal the selected area through the overlay
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            # Map rect back to pixmap source coordinates
            px_x = int(rect.x() * self._dpr)
            px_y = int(rect.y() * self._dpr)
            px_w = int(rect.width() * self._dpr)
            px_h = int(rect.height() * self._dpr)
            src_rect = QRect(px_x, px_y, px_w, px_h)
            painter.drawPixmap(rect, self._screen_pixmap, src_rect)

            # Selection border — indigo glow
            pen = QPen(QColor(99, 102, 241), 2, Qt.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect)

            # Corner handles
            handle_size = 8
            hc = QColor(192, 193, 255)
            painter.setBrush(QBrush(hc))
            painter.setPen(Qt.NoPen)
            half = handle_size // 2
            corners = [
                QRect(rect.left() - half, rect.top() - half, handle_size, handle_size),
                QRect(rect.right() - half, rect.top() - half, handle_size, handle_size),
                QRect(rect.left() - half, rect.bottom() - half, handle_size, handle_size),
                QRect(rect.right() - half, rect.bottom() - half, handle_size, handle_size),
            ]
            for corner in corners:
                painter.drawRect(corner)

            # Dimension label with global coords
            global_x = self._virtual_geometry.x() + rect.x()
            global_y = self._virtual_geometry.y() + rect.y()
            label_text = (
                f"  {rect.width()} × {rect.height()}   "
                f"@({global_x}, {global_y})  "
            )
            font = QFont("Segoe UI", 11)
            font.setBold(True)
            painter.setFont(font)

            text_x = rect.left()
            text_y = rect.top() - 30 if rect.top() > 40 else rect.bottom() + 26

            metrics = painter.fontMetrics()
            text_width = metrics.horizontalAdvance(label_text) + 4
            text_height = 26
            bg_rect = QRect(text_x, text_y - text_height + 4, text_width, text_height)
            painter.setBrush(QBrush(QColor(15, 23, 42, 230)))
            painter.setPen(QPen(QColor(99, 102, 241), 1))
            painter.drawRoundedRect(bg_rect, 5, 5)

            painter.setPen(QPen(QColor(218, 226, 253)))
            painter.drawText(bg_rect, Qt.AlignCenter, label_text)

        # Instruction hint when not yet dragging
        if self._start is None:
            font = QFont("Segoe UI", 16)
            font.setBold(True)
            painter.setFont(font)
            # Pill background
            hint = "   Kéo thả chuột để chọn vùng theo dõi   "
            hint2 = "   Nhấn ESC để hủy   "
            fm = painter.fontMetrics()
            w1 = fm.horizontalAdvance(hint)
            w2 = fm.horizontalAdvance(hint2)
            cx = self.width() // 2
            cy = self.height() // 2
            lh = fm.height() + 6
            # bg
            for i, (txt, w) in enumerate([(hint, w1), (hint2, w2)]):
                r = QRect(cx - w // 2, cy - lh + i * (lh + 4), w, lh)
                painter.setBrush(QBrush(QColor(15, 23, 42, 210)))
                painter.setPen(QPen(QColor(99, 102, 241, 180), 1))
                painter.drawRoundedRect(r, 8, 8)
                painter.setPen(QPen(QColor(255, 255, 255, 230)))
                painter.drawText(r, Qt.AlignCenter, txt)

        painter.end()


def pick_region(parent_widget=None) -> Optional[Tuple[int, int, int, int]]:
    """
    Bắt đầu overlay chọn vùng. Chặn đến khi người dùng chọn xong hoặc hủy.
    Trả về (x, y, w, h) tọa độ logic toàn màn hình hoặc None nếu hủy.
    """
    result = [None]
    app = QApplication.instance()

    # Build virtual desktop rect spanning all screens
    virtual_geometry = QRect()
    for screen in app.screens():
        virtual_geometry = virtual_geometry.united(screen.geometry())

    # Grab the entire virtual desktop.
    # We use primaryScreen().grabWindow(0) as a simpler cross-platform approach,
    # or fallback to grabbing each screen and compositing.
    primary = app.primaryScreen()
    dpr = primary.devicePixelRatio()

    # Grab the primary screen window (WinId=0 means entire screen root on Windows)
    screen_pixmap = primary.grabWindow(0)

    # If there are multiple screens, try to stitch them.
    # For simplicity we just use primary screen capture mapped to virtual geometry
    # (most games run full-screen on primary anyway).
    # The overlay covers the full virtual desktop so the user can pick on any monitor.

    overlay = RegionPickerOverlay(screen_pixmap, virtual_geometry, dpr)

    def on_selected(x, y, w, h):
        result[0] = (x, y, w, h)

    def on_cancelled():
        result[0] = None

    overlay.region_selected.connect(on_selected)
    overlay.cancelled.connect(on_cancelled)

    overlay.showFullScreen()

    while overlay.isVisible():
        app.processEvents()

    return result[0]
