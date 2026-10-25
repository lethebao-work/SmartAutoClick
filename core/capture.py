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


class CaptureError(Exception):
    """Raised when screen capture fails or returns invalid/pure black frames."""
    pass


class ScreenCapture:
    """
    Fast screen capture using mss with PIL fallback and strict fail-safe error handling.
    """

    def __init__(self):
        self._sct = None

    @property
    def sct(self):
        if self._sct is None and mss is not None:
            try:
                self._sct = mss.mss()
            except Exception:
                self._sct = None
        return self._sct

    def capture_region(self, x: int, y: int, w: int, h: int, allow_blank: bool = False) -> np.ndarray:
        """
        Captures a specific rectangle region of the screen.
        Returns a BGR numpy array (ready for OpenCV).
        Raises CaptureError if capture fails or results in pure black frames.
        """
        if w <= 0 or h <= 0:
            raise ValueError(f"Invalid region dimensions: w={w}, h={h}")

        last_error = None
        img_bgr = None

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
                    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)
                else:
                    img_bgr = img_np[:, :, :3]
            except Exception as e:
                last_error = e

        # Method 2: PIL ImageGrab fallback
        if img_bgr is None and ImageGrab is not None:
            try:
                pil_img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
                img_np = np.array(pil_img)
                if cv2 is not None:
                    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
                else:
                    img_bgr = img_np[:, :, ::-1]
            except Exception as e:
                last_error = e

        if img_bgr is None:
            if allow_blank:
                return np.zeros((int(h), int(w), 3), dtype=np.uint8)
            raise CaptureError(f"Screen capture failed for region ({x}, {y}, {w}, {h}): {last_error or 'No capture backend available'}")

        # Check for pure black frame (fail-safe for locked/disconnected screen)
        if not allow_blank and img_bgr.size > 0 and float(img_bgr.mean()) < 0.5 and float(img_bgr.std()) == 0.0:
            raise CaptureError(f"Pure black frame detected in region ({x}, {y}, {w}, {h}) - screen may be locked, asleep, or exclusive fullscreen")

        return img_bgr

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
