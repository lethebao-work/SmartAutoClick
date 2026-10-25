"""TwoPhaseSettle: đồng bộ theo khung hình (pha 1 phản hồi, pha 2 ổn định)."""
import unittest
import numpy as np

from core.frame_sync import TwoPhaseSettle, SettleState, change_percent

OLD = np.full((60, 60, 3), 90, np.uint8)
NEW = OLD.copy(); NEW[10:50, 10:50] = (200, 60, 180)
MID = OLD.copy(); MID[10:30, 10:50] = (30, 200, 30)


def run(frames_at, **kw):
    """frames_at: list[(t, [frame])]. Trả (kết quả, thời điểm)."""
    sm = TwoPhaseSettle([OLD], 0.0, **kw)
    for t, fr in frames_at:
        r = sm.feed(fr, t)
        if r:
            return r, t, sm
    return None, None, sm


class TestTwoPhaseSettle(unittest.TestCase):
    def test_stale_frames_do_not_count_as_settled(self):
        """Game trễ 400ms: các khung CŨ giống hệt không được coi là 'đã xong' (lỗi cũ E-03)."""
        seq = [(t / 100, [OLD]) for t in range(1, 40)]            # 10..390ms: vẫn ảnh cũ
        seq += [(0.40 + t / 100, [NEW]) for t in range(0, 60)]    # 400ms: kết quả xuất hiện
        r, t, sm = run(seq, stable_s=0.25)
        self.assertEqual(r, SettleState.SETTLED)
        self.assertGreaterEqual(t, 0.40 + 0.25 - 1e-9)             # phải chờ đủ ổn định SAU khi đổi
        self.assertAlmostEqual(sm.t_first_change, 0.40, places=2)

    def test_no_change_reports_no_response(self):
        seq = [(t / 100, [OLD]) for t in range(1, 400)]
        r, t, _ = run(seq, first_change_timeout_s=1.5)
        self.assertEqual(r, SettleState.NO_RESPONSE)
        self.assertGreaterEqual(t, 1.5)

    def test_continuous_animation_times_out(self):
        seq = [(t / 100, [NEW if t % 2 else MID]) for t in range(1, 800)]
        r, t, _ = run(seq, max_wait_s=3.0)
        self.assertEqual(r, SettleState.TIMEOUT)
        self.assertGreaterEqual(t, 3.0)

    def test_short_pause_mid_animation_is_not_settled(self):
        """Dừng giữa chừng 150ms (< stable_s=250ms) rồi hiện kết quả: chưa được coi là xong."""
        seq = [(0.05, [MID])]
        seq += [(0.05 + i / 100, [MID]) for i in range(1, 16)]      # đứng yên 150ms
        seq += [(0.25 + i / 100, [NEW]) for i in range(0, 50)]      # rồi đổi sang kết quả
        r, t, _ = run(seq, stable_s=0.25)
        self.assertEqual(r, SettleState.SETTLED)
        self.assertGreater(t, 0.25)                                 # không settle ở khung MID

    def test_all_slots_are_observed(self):
        """Slot thứ 2 đổi muộn: phải chờ cả hai, không chỉ regions[0]."""
        sm = TwoPhaseSettle([OLD, OLD], 0.0, stable_s=0.1)
        res = None
        for i in range(1, 100):
            t = i / 100
            f1 = NEW
            f2 = OLD if t < 0.5 else NEW                            # slot 2 phản hồi lúc 500ms
            res = sm.feed([f1, f2], t)
            if res:
                break
        self.assertEqual(res, SettleState.SETTLED)
        self.assertGreaterEqual(t, 0.5 + 0.1 - 1e-9)

    def test_change_percent_shape_mismatch_is_full_change(self):
        self.assertEqual(change_percent(OLD, OLD[:10]), 100.0)


if __name__ == "__main__":
    unittest.main()
