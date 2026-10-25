"""
Unit tests cho Phase 5: Performance, Reliability & Recovery Policy.

Kiểm thử:
- V5-T13: Phân loại lỗi (TRANSIENT, RECOVERABLE, FATAL).
- V5-T14: Exponential backoff & retry limits.
- V5-T15: Dừng an toàn khi gặp lỗi nghiêm trọng (window closed, max consecutive errors).
- V5-T16 & V5-T17: Recovery cho anchor (REFIND_ANCHOR) và capture (REINIT_CAPTURE).
- V5-T22: SafetyBudget kiểm tra giới hạn max_rolls và runtime_s.
- V5-T5 & V5-T11: PerformanceMonitor ghi nhận độ trễ và thống kê CPU, RAM, FPS.
"""
import unittest
import time

from core.recovery import (
    RecoveryManager,
    RecoveryAction,
    ErrorSeverity,
    SafetyBudget,
)
from core.performance import PerformanceMonitor


class TestRecoveryAndPerformance(unittest.TestCase):

    def test_error_classification(self):
        rm = RecoveryManager()

        # Fatal
        self.assertEqual(rm.classify_issue("window_lost"), ErrorSeverity.FATAL)
        self.assertEqual(rm.classify_issue("budget_exceeded"), ErrorSeverity.FATAL)
        self.assertEqual(rm.classify_issue("user_intervened"), ErrorSeverity.FATAL)

        # Recoverable
        self.assertEqual(rm.classify_issue("capture_failed"), ErrorSeverity.RECOVERABLE)
        self.assertEqual(rm.classify_issue("anchor_lost"), ErrorSeverity.RECOVERABLE)
        self.assertEqual(rm.classify_issue("geometry_mismatch"), ErrorSeverity.RECOVERABLE)

        # Transient
        self.assertEqual(rm.classify_issue("empty_frame"), ErrorSeverity.TRANSIENT)
        self.assertEqual(rm.classify_issue("network_lag"), ErrorSeverity.TRANSIENT)

    def test_exponential_backoff_and_consecutive_limit(self):
        budget = SafetyBudget(max_consecutive_errors=3)
        rm = RecoveryManager(base_backoff_s=0.1, max_backoff_s=1.0, safety_budget=budget)

        # Lần 1: transient -> wait 0.1s
        act1, delay1, _ = rm.handle_error("empty_frame")
        self.assertEqual(act1, RecoveryAction.WAIT_AND_RETRY)
        self.assertAlmostEqual(delay1, 0.1)

        # Lần 2: transient -> wait 0.2s
        act2, delay2, _ = rm.handle_error("empty_frame")
        self.assertEqual(act2, RecoveryAction.WAIT_AND_RETRY)
        self.assertAlmostEqual(delay2, 0.2)

        # Lần 3: transient -> wait 0.4s
        act3, delay3, _ = rm.handle_error("empty_frame")
        self.assertEqual(act3, RecoveryAction.WAIT_AND_RETRY)
        self.assertAlmostEqual(delay3, 0.4)

        # Lần 4: vượt max_consecutive_errors (3) -> SAFE_STOP (V5-T15)
        act4, _, reason = rm.handle_error("empty_frame")
        self.assertEqual(act4, RecoveryAction.SAFE_STOP)
        self.assertIn("Vượt quá giới hạn lỗi liên tiếp", reason)

    def test_recoverable_actions(self):
        rm = RecoveryManager()

        # Mất neo -> REFIND_ANCHOR
        act_anchor, _, _ = rm.handle_error("anchor_lost")
        self.assertEqual(act_anchor, RecoveryAction.REFIND_ANCHOR)

        # Lỗi capture -> REINIT_CAPTURE
        act_cap, _, _ = rm.handle_error("capture_failed")
        self.assertEqual(act_cap, RecoveryAction.REINIT_CAPTURE)

    def test_safety_budget_limits(self):
        budget = SafetyBudget(max_rolls=5, max_runtime_s=0.2)
        rm = RecoveryManager(safety_budget=budget)

        # Dưới giới hạn
        ok, _ = rm.check_safety_limits(current_rolls=2)
        self.assertTrue(ok)

        # Đạt max rolls -> dừng an toàn (V5-T22)
        ok_roll, reason_roll = rm.check_safety_limits(current_rolls=5)
        self.assertFalse(ok_roll)
        self.assertIn("Đã đạt số lần roll tối đa", reason_roll)

        # Đạt runtime limit
        time.sleep(0.25)
        ok_time, reason_time = rm.check_safety_limits(current_rolls=1)
        self.assertFalse(ok_time)
        self.assertIn("Đã đạt thời gian chạy tối đa", reason_time)

    def test_performance_monitor_metrics(self):
        perf = PerformanceMonitor(sample_window=10)

        # Ghi nhận frame
        perf.record_frame()
        perf.record_frame()

        # Ghi nhận latency
        perf.record_stage_latency(capture_ms=1.5, vision_ms=2.0, decision_ms=0.5, total_cycle_ms=4.0)
        perf.record_stage_latency(capture_ms=2.5, vision_ms=2.0, decision_ms=0.5, total_cycle_ms=5.0)

        stats = perf.get_stats()
        self.assertIn("fps", stats)
        self.assertIn("cpu_percent", stats)
        self.assertIn("ram_mb", stats)
        self.assertEqual(stats["latency_ms"]["capture"], 2.0)
        self.assertEqual(stats["latency_ms"]["total_cycle"], 4.5)


if __name__ == "__main__":
    unittest.main()
