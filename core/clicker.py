import random
import time
from typing import Tuple

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
except ImportError:
    pyautogui = None


class InputSimulator:
    """Mô phỏng thao tác chuột và bàn phím an toàn."""

    def __init__(self, randomize_offset: bool = True):
        self.randomize_offset = randomize_offset

    @staticmethod
    def get_mouse_position() -> Tuple[int, int]:
        """Lấy tọa độ hiện tại của con trỏ chuột."""
        if pyautogui is None:
            return (0, 0)
        pos = pyautogui.position()
        return (int(pos.x), int(pos.y))

    def click(self, x: int, y: int, button: str = "left", duration: float = 0.08) -> bool:
        """
        Click vào tọa độ (x, y).
        Có thêm độ lệch ngẫu nhiên 1-2 pixel để tránh bị anti-bot cố định tọa độ.
        """
        if pyautogui is None:
            print(f"[InputSimulator] Chưa cài pyautogui. Bỏ qua click ({x}, {y})")
            return False

        try:
            target_x = x
            target_y = y
            if self.randomize_offset:
                target_x += random.randint(-2, 2)
                target_y += random.randint(-2, 2)

            pyautogui.moveTo(target_x, target_y, duration=duration)
            time.sleep(0.02)
            pyautogui.click(target_x, target_y, button=button)
            return True
        except Exception as e:
            print(f"[InputSimulator] Lỗi click ({x}, {y}): {e}")
            return False
