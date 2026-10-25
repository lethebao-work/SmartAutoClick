"""
Benchmark hoàn chỉnh một chu trình Auto Roll (Phase 0 - V0-T9).
Đo lường toàn diện chu trình:
  Observe/Capture -> Frame Validation -> Settle/Gating -> Color Detection -> Rule Evaluation -> Action Dispatch

Đo các chỉ số baseline:
- Thời gian trọn vòng (Cycle latency)
- Thời gian từng công đoạn (Capture, Settle, Detect, Rule)
- Tỉ lệ thành công, sai số, FPS xử lý logic
"""
import os
import sys
import time
import json
import statistics as st
from typing import Dict, Any, List
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.capture_interface import Frame, FrameStatus
from core.detector import ColorDetector
from core.frame_sync import TwoPhaseSettle, SettleState
from tests.fakes import FakeFrameSource, FakeInputSink, FakeClock
from tests.test_dataset import create_normal_slot_frame, create_motion_sequence


def pct(vals: List[float], p: float) -> float:
    if not vals:
        return 0.0
    sorted_v = sorted(vals)
    idx = min(len(sorted_v) - 1, int(round((p / 100.0) * (len(sorted_v) - 1))))
    return sorted_v[idx]


def summarize(ms_list: List[float]) -> Dict[str, float]:
    if not ms_list:
        return {}
    return {
        "n": len(ms_list),
        "mean_ms": round(st.mean(ms_list), 3),
        "p50_ms": round(pct(ms_list, 50), 3),
        "p95_ms": round(pct(ms_list, 95), 3),
        "p99_ms": round(pct(ms_list, 99), 3),
        "max_ms": round(max(ms_list), 3),
    }


def run_autoroll_cycle_benchmark(cycles: int = 100) -> Dict[str, Any]:
    detector = ColorDetector()
    target_colors = ["purple"]
    input_sink = FakeInputSink()

    total_cycle_times = []
    capture_times = []
    settle_times = []
    detect_times = []
    action_times = []

    for c in range(cycles):
        t_start = time.perf_counter()

        # 1. Action: Click roll
        t_act_start = time.perf_counter()
        input_sink.click(500, 500)
        action_times.append((time.perf_counter() - t_act_start) * 1000)

        # 2. Capture baseline & settle animation sequence
        t_cap_start = time.perf_counter()
        source = FakeFrameSource(default_shape=(100, 100, 3))
        # 3 motion frames then 1 final target frame
        motion = create_motion_sequence(num_frames=4, final_color_bgr=(180, 20, 140))
        source.enqueue_frames(motion)
        capture_times.append((time.perf_counter() - t_cap_start) * 1000)

        # 3. TwoPhaseSettle evaluation
        t_settle_start = time.perf_counter()
        base_frame = motion[0]
        now = time.monotonic()
        settler = TwoPhaseSettle([base_frame], start_time=now, stable_s=0.01)
        res = None
        for frame in motion:
            now += 0.02
            res = settler.feed([frame], now=now)
            if res == SettleState.SETTLED:
                break
        settle_times.append((time.perf_counter() - t_settle_start) * 1000)

        # 4. Color Detection on final frame
        t_det_start = time.perf_counter()
        final_frame = motion[-1]
        analysis = detector.analyze_image(final_frame, target_colors=target_colors)
        detect_times.append((time.perf_counter() - t_det_start) * 1000)

        total_cycle_times.append((time.perf_counter() - t_start) * 1000)

    res = {
        "benchmark": "complete_autoroll_cycle",
        "cycles": cycles,
        "total_cycle": summarize(total_cycle_times),
        "action_dispatch": summarize(action_times),
        "capture_adapter": summarize(capture_times),
        "settle_sync": summarize(settle_times),
        "vision_detect": summarize(detect_times),
        "throughput_cycles_per_sec": round(1000.0 / st.mean(total_cycle_times), 1) if total_cycle_times else 0,
    }
    return res


if __name__ == "__main__":
    result = run_autoroll_cycle_benchmark(150)
    print(json.dumps(result, indent=2))
    out_file = os.path.join(os.path.dirname(__file__), "benchmark_autoroll_baseline.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\n[OK] Baseline Auto Roll benchmark written to: {out_file}")
