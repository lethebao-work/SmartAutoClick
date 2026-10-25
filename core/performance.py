"""
Bộ giám sát hiệu năng thực thi (Performance Monitor) cho SmartAutoClick v3.1 (Phase 5 - V5-T5, V5-T11).

Theo dõi và ghi nhận:
- FPS thực tế (Capture FPS, Decision FPS)
- Độ trễ từng giai đoạn (Latency: Capture -> Vision/Anchor -> Decision -> Action)
- Mức tiêu thụ tài nguyên (CPU %, RAM MB)
- Thống kê tỷ lệ lỗi / recovery
"""
import os
import time
import threading
from typing import Dict, Any, Optional
import psutil


class PerformanceMonitor:
    """
    Theo dõi FPS, CPU, RAM và độ trễ các công đoạn trong thời gian thực.
    """

    def __init__(self, sample_window: int = 50):
        self.sample_window = sample_window
        self._process = psutil.Process(os.getpid())

        self._lock = threading.Lock()
        self._capture_latencies = []
        self._vision_latencies = []
        self._decision_latencies = []
        self._total_cycle_latencies = []

        self._frame_count: int = 0
        self._fps_start_time: float = time.monotonic()
        self._current_fps: float = 0.0

    def record_frame(self) -> None:
        """Đếm frame để tính toán FPS."""
        with self._lock:
            self._frame_count += 1
            now = time.monotonic()
            elapsed = now - self._fps_start_time
            if elapsed >= 1.0:
                self._current_fps = round(self._frame_count / elapsed, 1)
                self._frame_count = 0
                self._fps_start_time = now

    def record_stage_latency(
        self,
        capture_ms: float = 0.0,
        vision_ms: float = 0.0,
        decision_ms: float = 0.0,
        total_cycle_ms: float = 0.0,
    ) -> None:
        """Ghi nhận độ trễ từng giai đoạn (V5-T5, V5-T11)."""
        with self._lock:
            self._capture_latencies.append(capture_ms)
            self._vision_latencies.append(vision_ms)
            self._decision_latencies.append(decision_ms)
            self._total_cycle_latencies.append(total_cycle_ms)

            # Giữ kích thước cửa sổ mẫu cố định (tránh phình RAM)
            if len(self._total_cycle_latencies) > self.sample_window:
                self._capture_latencies.pop(0)
                self._vision_latencies.pop(0)
                self._decision_latencies.pop(0)
                self._total_cycle_latencies.pop(0)

    def get_stats(self) -> Dict[str, Any]:
        """Lấy thông số thống kê CPU, RAM, FPS và độ trễ trung bình."""
        try:
            mem_info = self._process.memory_info()
            ram_mb = round(mem_info.rss / (1024 * 1024), 1)
            cpu_pct = round(self._process.cpu_percent(interval=None), 1)
        except Exception:
            ram_mb = 0.0
            cpu_pct = 0.0

        with self._lock:
            avg_cap = round(sum(self._capture_latencies) / len(self._capture_latencies), 2) if self._capture_latencies else 0.0
            avg_vis = round(sum(self._vision_latencies) / len(self._vision_latencies), 2) if self._vision_latencies else 0.0
            avg_dec = round(sum(self._decision_latencies) / len(self._decision_latencies), 2) if self._decision_latencies else 0.0
            avg_total = round(sum(self._total_cycle_latencies) / len(self._total_cycle_latencies), 2) if self._total_cycle_latencies else 0.0
            fps = self._current_fps

        return {
            "fps": fps,
            "cpu_percent": cpu_pct,
            "ram_mb": ram_mb,
            "latency_ms": {
                "capture": avg_cap,
                "vision": avg_vis,
                "decision": avg_dec,
                "total_cycle": avg_total,
            },
        }
