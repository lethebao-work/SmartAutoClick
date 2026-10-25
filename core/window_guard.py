"""
Window and Foreground Safety Guard for SmartAutoClick.
Ensures clicks are only sent when the target game window is in foreground,
and detects user manual mouse intervention.
"""
import sys
import ctypes
from typing import Tuple, Optional


class WindowGuard:
    @staticmethod
    def get_foreground_window_title() -> str:
        """Returns the title of the currently focused/active window."""
        if sys.platform != "win32":
            return ""
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                return ""
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return ""
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            return buf.value
        except Exception:
            return ""

    @staticmethod
    def is_target_window_active(target_title: Optional[str]) -> bool:
        """
        Returns True if the target window is active/focused.
        If target_title is empty or None, returns True (no restriction).
        """
        if not target_title or not target_title.strip():
            return True
        current_title = WindowGuard.get_foreground_window_title()
        return target_title.strip().lower() in current_title.lower()

    @staticmethod
    def is_user_interfering(last_bot_pos: Optional[Tuple[int, int]], current_pos: Tuple[int, int], threshold: int = 60) -> bool:
        """
        Detects if user actively moved mouse far from where the bot last clicked.
        """
        if last_bot_pos is None:
            return False
        bx, by = last_bot_pos
        cx, cy = current_pos
        dist_sq = (cx - bx) ** 2 + (cy - by) ** 2
        return dist_sq > (threshold ** 2)
