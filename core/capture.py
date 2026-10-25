import os
import sys
from typing import Optional, Tuple, Dict, Any
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import mss
    import cv2
except ImportError:
    mss = None
    cv2 = None

try:
    from PIL import ImageGrab
except ImportError:
    ImageGrab = None


class ScreenCapture:
    """
    Fast screen capture using mss with PIL fallback and graceful headless handling.
    """

    def __init__(self):
        self._sct = None

    @property
    def sct(self):
        if self._sct is None and mss is not None:
            try:
                self._sct = mss.mss()
            except Exception as e:
                self._sct = None
        return self._sct

    def capture_region(self, x: int, y: int, w: int, h: int) -> np.ndarray:
        """
        Captures a specific rectangle region of the screen.
        Returns a BGR numpy array (ready for OpenCV).
        """
        if w <= 0 or h <= 0:
            raise ValueError(f"Invalid region dimensions: w={w}, h={h}")

        # Method 1: MSS (Fastest, ~3ms)
        if self.sct is not None:
            try:
                monitor = {
                    "top": int(y),
                    "left": int(x),
                    "width": int(w),
                    "height": int(h)
                }
                sct_img = self.sct.grab(monitor)
                img_np = np.array(sct_img)
                if cv2 is not None:
                    return cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)
                return img_np[:, :, :3]
            except Exception:
                pass

        # Method 2: PIL ImageGrab fallback
        if ImageGrab is not None:
            try:
                pil_img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
                img_np = np.array(pil_img)
                if cv2 is not None:
                    return cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
                return img_np[:, :, ::-1]
            except Exception:
                pass

        # Method 3: Fallback simulated blank frame for testing / headless environments
        return np.zeros((int(h), int(w), 3), dtype=np.uint8)

    def capture_fullscreen(self) -> np.ndarray:
        """Captures primary monitor."""
        if self.sct is not None:
            try:
                primary = self.sct.monitors[1] if len(self.sct.monitors) > 1 else self.sct.monitors[0]
                sct_img = self.sct.grab(primary)
                img_np = np.array(sct_img)
                if cv2 is not None:
                    return cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)
                return img_np[:, :, :3]
            except Exception:
                pass

        if ImageGrab is not None:
            try:
                pil_img = ImageGrab.grab()
                img_np = np.array(pil_img)
                if cv2 is not None:
                    return cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
                return img_np[:, :, ::-1]
            except Exception:
                pass

        return np.zeros((1080, 1920, 3), dtype=np.uint8)

    def save_image(self, img_bgr: np.ndarray, file_path: str) -> bool:
        """Saves a BGR image to disk."""
        try:
            dir_name = os.path.dirname(file_path)
            if dir_name and not os.path.exists(dir_name):
                os.makedirs(dir_name, exist_ok=True)
            if cv2 is not None:
                return cv2.imwrite(file_path, img_bgr)
            return False
        except Exception as e:
            print(f"[ScreenCapture] Save error: {e}")
            return False

    def close(self):
        if self._sct is not None:
            try:
                self._sct.close()
            except Exception:
                pass
            self._sct = None
