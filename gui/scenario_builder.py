"""
Scenario Builder — Trình tạo kịch bản tự động hóa trực quan:
- Xoay quanh các Slot làm đơn vị tương tác
- Cho phép chọn mục tiêu bấm, điều kiện soi màu, thời gian chờ qua các Dropdown
- Tự động sinh bản tóm tắt kịch bản dễ đọc
- Không cần biết code
"""
from typing import List, Dict, Any, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QDoubleSpinBox, QGroupBox, QFrame,
    QScrollArea, QMessageBox, QGridLayout, QCheckBox
)


COLOR_OPTIONS = [
    ("purple", "🟣 Tím (Epic)", "#c084fc"),
    ("red", "🔴 Đỏ (Mythic)", "#f87171"),
    ("gold", "🟡 Vàng (Legendary)", "#facc15"),
    ("blue", "🔵 Xanh dương (Rare)", "#60a5fa"),
    ("green", "🟢 Xanh lá (Uncommon)", "#4ade80"),
]


class StepCard(QFrame):
    """Một thẻ đại diện cho một bước trong kịch bản."""
    delete_requested = Signal(object)
    move_up_requested = Signal(object)
    move_down_requested = Signal(object)
    changed = Signal()

    def __init__(self, step_idx: int, slots: List[Dict[str, Any]],
                 roll_coord: Dict[str, int], step_data: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.step_idx = step_idx
        self._slots = slots
        self._roll_coord = roll_coord
        self._data = step_data or {}

        self.setStyleSheet("""
            StepCard {
                background-color: #171c26;
                border: 1px solid #283347;
                border-radius: 8px;
            }
        """)
        self._build_ui()

    def update_slots(self, slots: List[Dict[str, Any]], roll_coord: Dict[str, int]):
        self._slots = slots
        self._roll_coord = roll_coord
        self._refresh_target_combos()

    def _build_ui(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(12, 10, 12, 10)
        main_lay.setSpacing(8)

        # Header bar: Tên bước + Dropdown loại bước + nút điều khiển
        header = QHBoxLayout()
        header.setSpacing(8)

        self.lbl_step_num = QLabel(f"Bước {self.step_idx + 1}")
        self.lbl_step_num.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.lbl_step_num.setStyleSheet("color: #38bdf8;")
        header.addWidget(self.lbl_step_num)

        header.addWidget(QLabel("Loại hành động:"))
        self.cmb_type = QComboBox()
        self.cmb_type.addItem("🖱️ Bấm chuột (Click)", "click")
        self.cmb_type.addItem("⏳ Chờ đợi (Wait Delay / Animation)", "wait")
        self.cmb_type.addItem("👁️ Kiểm tra nhận diện màu (Check Color)", "check_color")
        self.cmb_type.addItem("🔁 Vòng lặp kịch bản (Loop)", "loop")

        step_type = self._data.get("type", "click")
        idx = self.cmb_type.findData(step_type)
        if idx >= 0:
            self.cmb_type.setCurrentIndex(idx)
        self.cmb_type.currentIndexChanged.connect(self._on_type_changed)
        header.addWidget(self.cmb_type, 1)

        # Reorder / Delete buttons
        btn_up = QPushButton("▲")
        btn_up.setFixedSize(26, 26)
        btn_up.clicked.connect(lambda: self.move_up_requested.emit(self))
        header.addWidget(btn_up)

        btn_down = QPushButton("▼")
        btn_down.setFixedSize(26, 26)
        btn_down.clicked.connect(lambda: self.move_down_requested.emit(self))
        header.addWidget(btn_down)

        btn_del = QPushButton("✕")
        btn_del.setFixedSize(26, 26)
        btn_del.setStyleSheet("QPushButton { color: #f87171; font-weight: bold; } QPushButton:hover { background-color: #7f1d1d; }")
        btn_del.clicked.connect(lambda: self.delete_requested.emit(self))
        header.addWidget(btn_del)

        main_lay.addLayout(header)

        # Container cho các trường phụ động theo loại bước
        self.content_container = QWidget()
        self.content_lay = QVBoxLayout(self.content_container)
        self.content_lay.setContentsMargins(0, 4, 0, 0)
        main_lay.addWidget(self.content_container)

        self._render_body()

    def _on_type_changed(self):
        self._render_body()
        self.changed.emit()

    def _render_body(self):
        # Clear old widgets
        while self.content_lay.count():
            item = self.content_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        stype = self.cmb_type.currentData()
        if stype == "click":
            self._render_click_body()
        elif stype == "wait":
            self._render_wait_body()
        elif stype == "check_color":
            self._render_check_body()
        elif stype == "loop":
            self._render_loop_body()

    def _render_click_body(self):
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(QLabel("Mục tiêu bấm:"))

        self.cmb_click_target = QComboBox()
        self._fill_target_combo()
        self.cmb_click_target.currentIndexChanged.connect(self.changed.emit)
        row.addWidget(self.cmb_click_target, 2)

        row.addWidget(QLabel("Kiểu bấm:"))
        self.cmb_click_button = QComboBox()
        self.cmb_click_button.addItem("Chuột trái (Left Click)", "left")
        self.cmb_click_button.addItem("Nhấp đúp (Double Click)", "double")
        self.cmb_click_button.addItem("Chuột phải (Right Click)", "right")
        btn_data = self._data.get("button", "left")
        idx = self.cmb_click_button.findData(btn_data)
        if idx >= 0:
            self.cmb_click_button.setCurrentIndex(idx)
        self.cmb_click_button.currentIndexChanged.connect(self.changed.emit)
        row.addWidget(self.cmb_click_button, 1)

        self.content_lay.addLayout(row)

    def _fill_target_combo(self):
        cur_target = self.cmb_click_target.currentData() if self.cmb_click_target.count() > 0 else self._data.get("target", "roll")
        self.cmb_click_target.blockSignals(True)
        self.cmb_click_target.clear()
        rx, ry = self._roll_coord.get("x", 960), self._roll_coord.get("y", 540)
        self.cmb_click_target.addItem(f"🎯 Nút ROLL chính ({rx}, {ry})", "roll")

        for i, s in enumerate(self._slots):
            s_name = s.get("name", f"Slot {i+1}")
            sx, sy = s.get("x", 0), s.get("y", 0)
            sw, sh = s.get("w", 100), s.get("h", 100)
            cx, cy = sx + sw // 2, sy + sh // 2
            self.cmb_click_target.addItem(f"📦 Tâm {s_name} ({cx}, {cy})", f"slot_{i}")

        idx = self.cmb_click_target.findData(cur_target)
        if idx >= 0:
            self.cmb_click_target.setCurrentIndex(idx)
        self.cmb_click_target.blockSignals(False)

    def _render_wait_body(self):
        row = QHBoxLayout()
        row.setSpacing(8)

        row.addWidget(QLabel("Kiểu chờ:"))
        self.cmb_wait_mode = QComboBox()
        self.cmb_wait_mode.addItem("⏱️ Chờ thời gian cố định", "fixed")
        self.cmb_wait_mode.addItem("🎬 Chờ hiệu ứng animation kết thúc", "animation")
        wait_mode = self._data.get("mode", "fixed")
        idx = self.cmb_wait_mode.findData(wait_mode)
        if idx >= 0:
            self.cmb_wait_mode.setCurrentIndex(idx)
        self.cmb_wait_mode.currentIndexChanged.connect(self.changed.emit)
        row.addWidget(self.cmb_wait_mode)

        row.addWidget(QLabel("Thời gian (giây):"))
        self.spin_delay = QDoubleSpinBox()
        self.spin_delay.setRange(0.05, 30.0)
        self.spin_delay.setSingleStep(0.1)
        self.spin_delay.setValue(float(self._data.get("delay", 1.5)))
        self.spin_delay.valueChanged.connect(self.changed.emit)
        row.addWidget(self.spin_delay)

        row.addWidget(QLabel("Ngẫu nhiên ± (ms):"))
        self.spin_jitter = QSpinBox()
        self.spin_jitter.setRange(0, 2000)
        self.spin_jitter.setSingleStep(50)
        self.spin_jitter.setValue(int(self._data.get("jitter", 100)))
        self.spin_jitter.valueChanged.connect(self.changed.emit)
        row.addWidget(self.spin_jitter)

        row.addStretch()
        self.content_lay.addLayout(row)

    def _render_check_body(self):
        v = QVBoxLayout()
        v.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Vùng quan sát cần soi:"))
        self.cmb_watch_slot = QComboBox()
        self.cmb_watch_slot.addItem("🔍 Tất cả các Slot đang có", "all")
        for i, s in enumerate(self._slots):
            s_name = s.get("name", f"Slot {i+1}")
            self.cmb_watch_slot.addItem(f"📦 Chỉ soi {s_name}", f"slot_{i}")
        wslot = self._data.get("watch_slot", "all")
        idx = self.cmb_watch_slot.findData(wslot)
        if idx >= 0:
            self.cmb_watch_slot.setCurrentIndex(idx)
        self.cmb_watch_slot.currentIndexChanged.connect(self.changed.emit)
        top_row.addWidget(self.cmb_watch_slot, 2)

        top_row.addWidget(QLabel("Ngưỡng nhận diện diện tích (%):"))
        self.spin_thresh = QDoubleSpinBox()
        self.spin_thresh.setRange(0.1, 100.0)
        self.spin_thresh.setSingleStep(0.5)
        self.spin_thresh.setValue(float(self._data.get("threshold", 1.0)))
        self.spin_thresh.valueChanged.connect(self.changed.emit)
        top_row.addWidget(self.spin_thresh, 1)
        v.addLayout(top_row)

        # Rules table for each color
        grp_rules = QGroupBox("Quy tắc xử lý khi phát hiện từng màu:")
        grp_rules.setStyleSheet("QGroupBox { font-size: 11px; margin-top: 6px; padding-top: 8px; }")
        grid = QGridLayout(grp_rules)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(4)

        self._color_action_combos: Dict[str, QComboBox] = {}
        saved_rules = self._data.get("rules", {
            "purple": "stop",
            "red": "stop",
            "gold": "lock",
            "blue": "ignore",
            "green": "ignore",
        })

        for row_i, (c_key, c_label, c_hex) in enumerate(COLOR_OPTIONS):
            lbl = QLabel(f"● {c_label}")
            lbl.setStyleSheet(f"color: {c_hex}; font-weight: bold; font-size: 11px;")
            grid.addWidget(lbl, row_i, 0)

            cmb = QComboBox()
            cmb.addItem("🛑 DỪNG ngay lập tức (Stop)", "stop")
            cmb.addItem("🔒 Khóa slot này và tiếp tục roll (Lock)", "lock")
            cmb.addItem("⏭ Bỏ qua (Ignore)", "ignore")
            cur_act = saved_rules.get(c_key, "ignore")
            c_idx = cmb.findData(cur_act)
            if c_idx >= 0:
                cmb.setCurrentIndex(c_idx)
            cmb.currentIndexChanged.connect(self.changed.emit)
            self._color_action_combos[c_key] = cmb
            grid.addWidget(cmb, row_i, 1)

        v.addWidget(grp_rules)
        self.content_lay.addLayout(v)

    def _render_loop_body(self):
        row = QHBoxLayout()
        row.setSpacing(8)

        row.addWidget(QLabel("Nếu chưa thỏa mãn điều kiện dừng: Lặp lại từ"))
        self.cmb_loop_target = QComboBox()
        self.cmb_loop_target.addItem("Bước 1 (Đầu kịch bản)", 0)
        row.addWidget(self.cmb_loop_target)

        row.addWidget(QLabel("Số lần tối đa:"))
        self.spin_max_loop = QSpinBox()
        self.spin_max_loop.setRange(1, 99999)
        self.spin_max_loop.setValue(int(self._data.get("max_loop", 100)))
        self.spin_max_loop.valueChanged.connect(self.changed.emit)
        row.addWidget(self.spin_max_loop)

        self.chk_bg = QCheckBox("Bật Budget Guard (Dừng khi hết tiền / nút mờ)")
        self.chk_bg.setChecked(bool(self._data.get("budget_guard", True)))
        self.chk_bg.toggled.connect(self.changed.emit)
        row.addWidget(self.chk_bg)

        row.addStretch()
        self.content_lay.addLayout(row)

    def _refresh_target_combos(self):
        if hasattr(self, "cmb_click_target"):
            self._fill_target_combo()
        if hasattr(self, "cmb_watch_slot"):
            cur_slot = self.cmb_watch_slot.currentData()
            self.cmb_watch_slot.blockSignals(True)
            self.cmb_watch_slot.clear()
            self.cmb_watch_slot.addItem("🔍 Tất cả các Slot đang có", "all")
            for i, s in enumerate(self._slots):
                s_name = s.get("name", f"Slot {i+1}")
                self.cmb_watch_slot.addItem(f"📦 Chỉ soi {s_name}", f"slot_{i}")
            idx = self.cmb_watch_slot.findData(cur_slot)
            if idx >= 0:
                self.cmb_watch_slot.setCurrentIndex(idx)
            self.cmb_watch_slot.blockSignals(False)

    def set_index(self, idx: int):
        self.step_idx = idx
        self.lbl_step_num.setText(f"Bước {idx + 1}")

    def get_data(self) -> Dict[str, Any]:
        stype = self.cmb_type.currentData()
        res = {"type": stype}
        if stype == "click":
            res["target"] = self.cmb_click_target.currentData() if hasattr(self, "cmb_click_target") else "roll"
            res["button"] = self.cmb_click_button.currentData() if hasattr(self, "cmb_click_button") else "left"
        elif stype == "wait":
            res["mode"] = self.cmb_wait_mode.currentData() if hasattr(self, "cmb_wait_mode") else "fixed"
            res["delay"] = self.spin_delay.value() if hasattr(self, "spin_delay") else 1.5
            res["jitter"] = self.spin_jitter.value() if hasattr(self, "spin_jitter") else 100
        elif stype == "check_color":
            res["watch_slot"] = self.cmb_watch_slot.currentData() if hasattr(self, "cmb_watch_slot") else "all"
            res["threshold"] = self.spin_thresh.value() if hasattr(self, "spin_thresh") else 1.0
            rules = {}
            for k, cmb in getattr(self, "_color_action_combos", {}).items():
                rules[k] = cmb.currentData()
            res["rules"] = rules
        elif stype == "loop":
            res["max_loop"] = self.spin_max_loop.value() if hasattr(self, "spin_max_loop") else 100
            res["budget_guard"] = self.chk_bg.isChecked() if hasattr(self, "chk_bg") else True
        return res


class ScenarioBuilderWidget(QWidget):
    """Toàn bộ giao diện Scenario Builder."""
    scenario_changed = Signal()
    request_test = Signal()
    request_start = Signal()

    def __init__(self, slots: List[Dict[str, Any]], roll_coord: Dict[str, int], parent=None):
        super().__init__(parent)
        self._slots = slots
        self._roll_coord = roll_coord
        self._steps: List[StepCard] = []
        self._build_ui()
        self.load_default_gacha_template()

    def update_slots(self, slots: List[Dict[str, Any]], roll_coord: Dict[str, int]):
        self._slots = slots
        self._roll_coord = roll_coord
        for s in self._steps:
            s.update_slots(slots, roll_coord)
        self.update_summary()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        # Thông báo trực quan về luồng hoạt động
        lbl_info = QLabel("ℹ️ <b>Mô Hình Kịch Bản Trực Quan:</b> Các bước dưới đây mô phỏng trực quan chu trình vận hành của Bot (Bấm Roll ➔ Chờ trễ / Animation ➔ Soi màu HSV ➔ Khóa / Dừng). Mọi thay đổi đều được đồng bộ trực tiếp sang bộ máy thực thi của Auto Clicker.")
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-size: 12px;")
        lay.addWidget(lbl_info)

        # Toolbar: Nút thêm bước, nạp mẫu chuẩn
        bar = QHBoxLayout()
        self.btn_add_step = QPushButton("➕ Thêm Bước")
        self.btn_add_step.setStyleSheet("background-color: #0284c7; border-color: #0ea5e9; color: white;")
        self.btn_add_step.clicked.connect(self._add_step)
        bar.addWidget(self.btn_add_step)

        btn_template = QPushButton("⭐ Nạp Kịch Bản Mẫu Chuẩn (Auto-Roll Gacha)")
        btn_template.clicked.connect(self.load_default_gacha_template)
        bar.addWidget(btn_template)

        btn_clear = QPushButton("🗑 Xóa Hết")
        btn_clear.clicked.connect(self._clear_steps)
        bar.addWidget(btn_clear)

        bar.addStretch()
        lay.addLayout(bar)

        # Scroll area chứa danh sách StepCard
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.steps_container = QWidget()
        self.steps_lay = QVBoxLayout(self.steps_container)
        self.steps_lay.setSpacing(10)
        self.steps_lay.setContentsMargins(4, 4, 4, 4)
        self.scroll.setWidget(self.steps_container)
        lay.addWidget(self.scroll, 1)

        # Bottom: Summary Box + Action Buttons
        summary_box = QGroupBox("📋 Tóm Tắt Luồng Kịch Bản")
        summary_box.setStyleSheet("""
            QGroupBox {
                background-color: #171c26;
                border: 1px solid #283347;
                border-radius: 8px;
                font-weight: bold;
                color: #38bdf8;
                padding-top: 14px;
            }
        """)
        vs = QVBoxLayout(summary_box)
        self.lbl_summary = QLabel("Chưa có bước nào trong kịch bản.")
        self.lbl_summary.setWordWrap(True)
        self.lbl_summary.setStyleSheet("color: #e2e8f0; font-size: 12px; line-height: 1.4;")
        vs.addWidget(self.lbl_summary)

        # Bottom action bar
        btn_bar = QHBoxLayout()
        self.btn_test = QPushButton("🔍 Test Nhận Diện Thử (Không Roll)")
        self.btn_test.setFixedHeight(38)
        self.btn_test.setStyleSheet("background-color: #1e293b; border: 1px solid #475569; font-weight: bold;")
        self.btn_test.clicked.connect(self.request_test.emit)
        btn_bar.addWidget(self.btn_test, 1)

        self.btn_start = QPushButton("▶ BẮT ĐẦU CHẠY KỊCH BẢN (F6)")
        self.btn_start.setFixedHeight(38)
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                border: 1px solid #10b981;
                font-weight: bold;
                font-size: 13px;
                color: white;
            }
            QPushButton:hover { background-color: #10b981; }
        """)
        self.btn_start.clicked.connect(self.request_start.emit)
        btn_bar.addWidget(self.btn_start, 2)

        vs.addLayout(btn_bar)
        lay.addWidget(summary_box)

    def _add_step(self, step_data: Optional[Dict[str, Any]] = None):
        idx = len(self._steps)
        card = StepCard(idx, self._slots, self._roll_coord, step_data=step_data, parent=self.steps_container)
        card.delete_requested.connect(self._delete_step)
        card.move_up_requested.connect(self._move_up_step)
        card.move_down_requested.connect(self._move_down_step)
        card.changed.connect(self._on_step_changed)
        self._steps.append(card)
        self.steps_lay.addWidget(card)
        self.update_summary()
        self.scenario_changed.emit()

    def _delete_step(self, card: StepCard):
        if len(self._steps) <= 1:
            QMessageBox.warning(self, "Cảnh báo", "Kịch bản cần có ít nhất 1 bước!")
            return
        idx = self._steps.index(card)
        self._steps.pop(idx)
        card.setParent(None)
        card.deleteLater()
        self._reindex()
        self.update_summary()
        self.scenario_changed.emit()

    def _move_up_step(self, card: StepCard):
        idx = self._steps.index(card)
        if idx > 0:
            self._steps.pop(idx)
            self._steps.insert(idx - 1, card)
            self._reorder_ui()

    def _move_down_step(self, card: StepCard):
        idx = self._steps.index(card)
        if idx < len(self._steps) - 1:
            self._steps.pop(idx)
            self._steps.insert(idx + 1, card)
            self._reorder_ui()

    def _reorder_ui(self):
        for card in self._steps:
            self.steps_lay.removeWidget(card)
        for card in self._steps:
            self.steps_lay.addWidget(card)
        self._reindex()
        self.update_summary()
        self.scenario_changed.emit()

    def _reindex(self):
        for i, card in enumerate(self._steps):
            card.set_index(i)

    def _clear_steps(self):
        for card in self._steps:
            card.setParent(None)
            card.deleteLater()
        self._steps.clear()
        self.update_summary()
        self.scenario_changed.emit()

    def _on_step_changed(self):
        self.update_summary()
        self.scenario_changed.emit()

    def load_default_gacha_template(self):
        """Khởi tạo kịch bản chuẩn cho Auto Roll."""
        self._clear_steps()
        # Bước 1: Bấm Roll
        self._add_step({"type": "click", "target": "roll", "button": "left"})
        # Bước 2: Chờ đợi 1.5s
        self._add_step({"type": "wait", "mode": "fixed", "delay": 1.5, "jitter": 100})
        # Bước 3: Soi màu
        self._add_step({
            "type": "check_color",
            "watch_slot": "all",
            "threshold": 1.0,
            "rules": {"purple": "stop", "red": "stop", "gold": "lock", "blue": "ignore", "green": "ignore"}
        })
        # Bước 4: Lặp lại
        self._add_step({"type": "loop", "max_loop": 100, "budget_guard": True})

    def update_summary(self):
        if not self._steps:
            self.lbl_summary.setText("Chưa có bước nào trong kịch bản. Hãy bấm '➕ Thêm Bước' hoặc 'Nạp Kịch Bản Mẫu Chuẩn'.")
            return

        summary_parts = []
        for i, card in enumerate(self._steps):
            data = card.get_data()
            stype = data.get("type")
            prefix = f"<b>{i+1}.</b>"

            if stype == "click":
                target = data.get("target", "roll")
                if target == "roll":
                    rx, ry = self._roll_coord.get("x", 960), self._roll_coord.get("y", 540)
                    t_str = f"nút Roll chính ({rx}, {ry})"
                elif target.startswith("slot_"):
                    s_idx = int(target.replace("slot_", ""))
                    s_name = self._slots[s_idx].get("name", f"Slot {s_idx+1}") if s_idx < len(self._slots) else target
                    t_str = f"tâm {s_name}"
                else:
                    t_str = str(target)
                summary_parts.append(f"{prefix} Bấm chuột trái vào <b>{t_str}</b>")

            elif stype == "wait":
                mode = data.get("mode", "fixed")
                if mode == "animation":
                    summary_parts.append(f"{prefix} Chờ hiệu ứng animation kết thúc")
                else:
                    d = data.get("delay", 1.5)
                    j = data.get("jitter", 100)
                    summary_parts.append(f"{prefix} Chờ {d:.1f}s (±{j}ms)")

            elif stype == "check_color":
                rules = data.get("rules", {})
                stops = [COLOR_OPTIONS[idx][1].split()[1] for idx, (k, _, _) in enumerate(COLOR_OPTIONS) if rules.get(k) == "stop"]
                locks = [COLOR_OPTIONS[idx][1].split()[1] for idx, (k, _, _) in enumerate(COLOR_OPTIONS) if rules.get(k) == "lock"]
                desc_items = []
                if stops:
                    desc_items.append(f"DỪNG khi thấy {', '.join(stops)}")
                if locks:
                    desc_items.append(f"KHÓA khi thấy {', '.join(locks)}")
                desc = " & ".join(desc_items) if desc_items else "soi kết quả"
                summary_parts.append(f"{prefix} Soi màu ({desc})")

            elif stype == "loop":
                max_l = data.get("max_loop", 100)
                summary_parts.append(f"{prefix} Lặp lại từ Bước 1 (tối đa {max_l} lần)")

        full_text = " ➔ ".join(summary_parts)
        self.lbl_summary.setText(full_text)

    def get_scenario_data(self) -> List[Dict[str, Any]]:
        return [card.get_data() for card in self._steps]
