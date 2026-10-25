"""
Region Picker — Fullscreen overlay cho phép người dùng kéo thả chuột
để chọn vùng màn hình cần theo dõi. Trả về (x, y, w, h) tọa độ thực.

Đã sửa lỗi DPI/scaling: dùng virtual desktop toàn bộ màn hình,
screenGeometry() thay vì primaryScreen().geometry() để hỗ trợ multi-monitor,
và tính device-pixel-ratio để ảnh chụp không bị lệch.
"""
from typing import Optional, Tuple
import ctypes
import logging
import cv2
import numpy as np

from PySide6.QtCore import Qt, QRect, QPoint, Signal, QRectF
from PySide6.QtGui import (
    QColor, QPainter, QPen, QBrush, QScreen,
    QPixmap, QImage, QFont, QCursor, QKeyEvent
)
from PySide6.QtWidgets import QApplication, QWidget

logger = logging.getLogger("SmartAutoClick.RegionPicker")

# Windows Display Affinity Constants (Windows 10 version 2004 / build 19041+)
WDA_NONE = 0x00000000
WDA_EXCLUDEFROMCAPTURE = 0x00000011


def set_window_capture_affinity(hwnd: int, exclude: bool = True) -> bool:
    """
    Đặt hoặc gỡ cờ WDA_EXCLUDEFROMCAPTURE cho cửa sổ Windows (Win10 build 19041+).
    Khi bật (exclude=True), cửa sổ này sẽ hoàn toàn vô hình đối với bất kỳ ảnh chụp màn hình nào (DWM/Qt grabWindow).
    """
    if not hwnd or not hasattr(ctypes, "windll"):
        return False
    try:
        user32 = ctypes.windll.user32
        if hasattr(user32, "SetWindowDisplayAffinity"):
            val = WDA_EXCLUDEFROMCAPTURE if exclude else WDA_NONE
            res = user32.SetWindowDisplayAffinity(hwnd, val)
            return bool(res)
    except Exception as e:
        logger.debug("Khong the dat SetWindowDisplayAffinity: %s", e)
    return False


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
                # Chuyển đổi widget-local coords → tọa độ pixel vật lý thực tế trên màn hình
                phys_x = int(round((self._virtual_geometry.x() + rect.x()) * self._dpr))
                phys_y = int(round((self._virtual_geometry.y() + rect.y()) * self._dpr))
                phys_w = int(round(rect.width() * self._dpr))
                phys_h = int(round(rect.height() * self._dpr))
                self.region_selected.emit(phys_x, phys_y, phys_w, phys_h)
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
            px_x = int(round(rect.x() * self._dpr))
            px_y = int(round(rect.y() * self._dpr))
            px_w = int(round(rect.width() * self._dpr))
            px_h = int(round(rect.height() * self._dpr))
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

            # Dimension label with physical pixel coords (khớp 1:1 với MSS, DXGI, Clicker)
            phys_x = int(round((self._virtual_geometry.x() + rect.x()) * self._dpr))
            phys_y = int(round((self._virtual_geometry.y() + rect.y()) * self._dpr))
            phys_w = int(round(rect.width() * self._dpr))
            phys_h = int(round(rect.height() * self._dpr))
            label_text = (
                f"  {phys_w} × {phys_h}   "
                f"@({phys_x}, {phys_y})  "
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


def pick_region(parent_widget=None) -> Tuple[Optional[Tuple[int, int, int, int]], Optional[np.ndarray]]:
    """
    Bắt đầu overlay chọn vùng. Chặn đến khi người dùng chọn xong hoặc hủy.
    Tự động áp dụng WDA_EXCLUDEFROMCAPTURE cho parent_widget (nếu có) để không cần ẩn tool.
    Hỗ trợ ghép ảnh toàn bộ các màn hình (multi-monitor stitching) và kiểm tra ảnh trắng/đen đồng màu.
    Trả về:
        ((phys_x, phys_y, phys_w, phys_h), cropped_bgr) hoặc (None, None) nếu hủy hoặc ảnh lỗi.
    """
    app = QApplication.instance()
    if not app:
        logger.error("pick_region: QApplication chua duoc khoi tao!")
        return None, None

    # Tự động ẩn cửa sổ tool khỏi tầm chụp bằng SetWindowDisplayAffinity (Windows 10 2004+)
    parent_hwnd = 0
    affinity_applied = False
    if parent_widget is not None and hasattr(parent_widget, "winId"):
        try:
            parent_hwnd = int(parent_widget.winId())
            affinity_applied = set_window_capture_affinity(parent_hwnd, True)
            if affinity_applied:
                app.processEvents()
        except Exception as e:
            logger.debug("Loi khi apply window capture affinity: %s", e)

    try:
        # Build virtual desktop rect spanning all screens
        screens = app.screens()
        virtual_geometry = QRect()
        for screen in screens:
            virtual_geometry = virtual_geometry.united(screen.geometry())

        primary = app.primaryScreen()
        dpr = primary.devicePixelRatio() if primary else 1.0

        # Ghép ảnh chụp của tất cả các màn hình (multi-monitor compositing)
        canvas_w = int(round(virtual_geometry.width() * dpr))
        canvas_h = int(round(virtual_geometry.height() * dpr))
        stitched_pixmap = QPixmap(canvas_w, canvas_h)
        stitched_pixmap.fill(Qt.black)

        painter = QPainter(stitched_pixmap)
        for s in screens:
            try:
                s_pix = s.grabWindow(0)
                s_geo = s.geometry()
                px = int(round((s_geo.x() - virtual_geometry.x()) * dpr))
                py = int(round((s_geo.y() - virtual_geometry.y()) * dpr))
                painter.drawPixmap(px, py, s_pix)
            except Exception as e:
                logger.error("Loi khi grabWindow tren screen %s: %s", s.name(), e)
        painter.end()

        # Kiểm tra tính hợp lệ của ảnh nền (chống ảnh trắng/đen đồng màu std ≈ 0)
        qimg_test = stitched_pixmap.toImage().convertToFormat(QImage.Format_RGBA8888)
        if qimg_test.isNull() or qimg_test.width() <= 0 or qimg_test.height() <= 0:
            logger.error("pick_region: Khong the lay anh chup man hinh hop le.")
            return None, None

        th, tw = qimg_test.height(), qimg_test.width()
        tbpl = qimg_test.bytesPerLine()
        raw_test = np.frombuffer(qimg_test.constBits(), dtype=np.uint8).reshape((th, tbpl))
        bg_rgb_test = raw_test[::8, :tw * 4:8]  # subsample nhanh để đo độ lệch chuẩn
        std_val = float(np.std(bg_rgb_test))
        mean_val = float(np.mean(bg_rgb_test))

        if std_val < 0.8 and (mean_val > 250.0 or mean_val < 2.0):
            logger.error(
                "pick_region: Phat hien anh man hinh bi trang/den dong mau (mean=%.1f, std=%.2f). Huy overlay.",
                mean_val, std_val
            )
            return None, None

        overlay = RegionPickerOverlay(stitched_pixmap, virtual_geometry, dpr)

        result = [None]
        cropped_bgr = [None]

        def on_selected(x, y, w, h):
            result[0] = (x, y, w, h)
            try:
                # Crop trực tiếp từ stitched_pixmap để lưu làm preview chuẩn
                rect = overlay._get_rect()
                if not rect.isNull() and rect.width() > 0 and rect.height() > 0:
                    px_x = int(round(rect.x() * dpr))
                    px_y = int(round(rect.y() * dpr))
                    px_w = int(round(rect.width() * dpr))
                    px_h = int(round(rect.height() * dpr))
                    cropped_pix = stitched_pixmap.copy(px_x, px_y, px_w, px_h)
                    qimg = cropped_pix.toImage().convertToFormat(QImage.Format_RGBA8888)
                    ih, iw = qimg.height(), qimg.width()
                    bpl = qimg.bytesPerLine()
                    raw = np.frombuffer(qimg.constBits(), dtype=np.uint8).reshape((ih, bpl))
                    arr_rgba = raw[:, :iw * 4].reshape((ih, iw, 4))
                    cropped_bgr[0] = cv2.cvtColor(arr_rgba, cv2.COLOR_RGBA2BGR)
            except Exception as e:
                logger.error("Loi khi crop anh xem truoc trong RegionPicker: %s", e)

        def on_cancelled():
            result[0] = None

        overlay.region_selected.connect(on_selected)
        overlay.cancelled.connect(on_cancelled)

        overlay.showFullScreen()

        while overlay.isVisible():
            app.processEvents()

        return result[0], cropped_bgr[0]

    finally:
        # Luôn phục hồi capture affinity cho cửa sổ mẹ nếu đã áp dụng
        if affinity_applied and parent_hwnd:
            try:
                set_window_capture_affinity(parent_hwnd, False)
                app.processEvents()
            except Exception:
                pass

