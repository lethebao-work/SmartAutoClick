"""
Benchmark chụp màn hình + nhận diện + click cho SmartAutoClick.

Chạy trên MÁY THẬT của bạn (Windows), với game/ứng dụng ở đúng chế độ bạn dùng
(Borderless / Windowed / Exclusive):

    python tools/benchmark_capture.py                       # vùng mặc định 400,300,180x180
    python tools/benchmark_capture.py --region 500 280 180 180 --n 500
    python tools/benchmark_capture.py --click-test 1500 900  # CÓ CLICK THẬT 20 lần tại điểm này

Để kiểm tra "khung hình có thật sự mới không", hãy để một thứ chuyển động (video, đồng hồ
đếm, animation game) trong vùng chụp: cột `uniq_fps` là số khung KHÁC NHAU mỗi giây.
Ghi kết quả ra tools/benchmark_result.json để gửi lại phân tích.

    --synthetic   chạy bằng backend giả (kiểm tra chính script này, không chụp màn hình thật)
"""
import argparse
import json
import os
import statistics as st
import sys
import time
import zlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Cùng thứ tự với main.py: đặt DPI trước khi import thứ gì có thể đụng DPI.
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        pass

import numpy as np

from core.capture import ScreenCapture, _Backend, MssBackend, DxgiBackend, PilBackend
from core.detector import ColorDetector
from core.config_manager import DEFAULT_COLOR_DEFINITIONS


class SyntheticBackend(_Backend):
    name = "synthetic"

    def __init__(self):
        self._i = 0

    def available(self):
        return True

    def grab(self, x, y, w, h):
        self._i += 1
        f = np.full((h, w, 3), 80, np.uint8)
        f[: h // 2, : w // 2] = (self._i * 7 % 255, 60, 200)
        return f


def pct(vals, p):
    vals = sorted(vals)
    return vals[min(len(vals) - 1, int(round((p / 100) * (len(vals) - 1))))]


def summarize(ms):
    return {
        "n": len(ms), "mean": round(st.mean(ms), 2), "p50": round(pct(ms, 50), 2),
        "p95": round(pct(ms, 95), 2), "p99": round(pct(ms, 99), 2), "max": round(max(ms), 2),
    }


def bench_backend(be, region, n, seconds_unique=3.0):
    x, y, w, h = region
    out = {"backend": be.name}
    cap = ScreenCapture(backends=[be])
    try:
        cap.capture_region(x, y, w, h)  # khởi động/warm-up
    except Exception as e:
        out["error"] = str(e)
        return out

    ms, black, errs = [], 0, 0
    for _ in range(n):
        t = time.perf_counter()
        try:
            cap.capture_region(x, y, w, h)
            ms.append((time.perf_counter() - t) * 1000)
        except Exception as e:
            errs += 1
            if "đen" in str(e):
                black += 1
    out["errors"] = errs
    out["black_frames"] = black
    if ms:
        out["capture_ms"] = summarize(ms)

    # đếm số khung KHÁC NHAU mỗi giây (phát hiện ảnh cũ/đứng hình)
    seen, last, t_end = 0, None, time.perf_counter() + seconds_unique
    polls = 0
    while time.perf_counter() < t_end:
        try:
            im = cap.capture_region(x, y, w, h)
        except Exception:
            continue
        polls += 1
        h_ = zlib.crc32(im.tobytes())
        if h_ != last:
            seen += 1
            last = h_
    out["poll_hz"] = round(polls / seconds_unique, 1)
    out["uniq_fps"] = round(seen / seconds_unique, 1)

    # chụp gộp 2 slot cạnh nhau (một lần grab)
    rects = [(x, y, w, h), (x + w + 10, y, w, h)]
    ms2 = []
    for _ in range(max(20, n // 5)):
        t = time.perf_counter()
        try:
            cap.capture_regions(rects)
            ms2.append((time.perf_counter() - t) * 1000)
        except Exception:
            break
    if ms2:
        out["two_slots_ms"] = summarize(ms2)

    # chi phí nhận diện trên khung vừa chụp
    try:
        im = cap.capture_region(x, y, w, h)
        det = ColorDetector(DEFAULT_COLOR_DEFINITIONS)
        dms = []
        for _ in range(200):
            t = time.perf_counter()
            det.analyze_image(im, ["purple", "red"])
            dms.append((time.perf_counter() - t) * 1000)
        out["detect_ms"] = summarize(dms)
    except Exception:
        pass
    cap.close()
    return out


def bench_click(x, y, n=20):
    """So sánh đường click cũ (pyautogui) và mới (SendInput). CÓ CLICK THẬT."""
    from core.clicker import InputSimulator
    res = {}
    new = InputSimulator(randomize_offset=False)
    t = []
    for _ in range(n):
        s = time.perf_counter(); new.click(x, y); t.append((time.perf_counter() - s) * 1000); time.sleep(0.05)
    res["new_sendinput_ms"] = summarize(t)
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0.05
        t = []
        for _ in range(n):
            s = time.perf_counter()
            pyautogui.moveTo(x, y, duration=0.08); time.sleep(0.02); pyautogui.click(x, y)
            t.append((time.perf_counter() - s) * 1000); time.sleep(0.05)
        res["old_pyautogui_ms"] = summarize(t)
    except Exception as e:
        res["old_pyautogui_ms"] = f"không đo được: {e}"
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", type=int, nargs=4, default=[400, 300, 180, 180], metavar=("X", "Y", "W", "H"))
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--click-test", type=int, nargs=2, metavar=("X", "Y"))
    args = ap.parse_args()

    backends = [SyntheticBackend()] if args.synthetic else [DxgiBackend(), MssBackend(), PilBackend()]
    results = {"platform": sys.platform, "python": sys.version.split()[0], "region": args.region, "backends": []}

    for be in backends:
        if not be.available():
            print(f"[{be.name}] không khả dụng (thiếu thư viện/nền tảng)")
            continue
        print(f"[{be.name}] đang đo ({args.n} lần + 3s đếm khung)...")
        r = bench_backend(be, tuple(args.region), args.n, 3.0 if not args.synthetic else 0.3)
        results["backends"].append(r)
        print("   ", json.dumps(r, ensure_ascii=False))

    if args.click_test:
        print("[click] CLICK THẬT 20 lần mỗi cách tại", args.click_test)
        results["click"] = bench_click(*args.click_test)
        print("   ", json.dumps(results["click"], ensure_ascii=False))

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "benchmark_result.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("Đã ghi", out)


if __name__ == "__main__":
    main()
