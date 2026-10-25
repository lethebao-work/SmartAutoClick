# Single source of truth cho phiên bản SmartAutoClick.
# Import từ đây để dùng ở mọi nơi: main.py, GUI, build script.

APP_VERSION = "3.6.1"
APP_NAME = "Smart Auto Click"
APP_BUILD_DATE = "2026-10-26"

# Lịch sử phiên bản (Quy ước: <Đại phiên bản>.<Phase/Tính năng lớn>.<Fix nhỏ>)
# 3.6.1 - Phase 7A Hotfix: Sửa lỗi màn hình trắng RegionPicker & ColorSampler qua WDA_EXCLUDEFROMCAPTURE, thêm QImage import, ghép multi-monitor, chặn ảnh đơn sắc và loại bỏ nuốt lỗi.
# 3.6.0 - Phase 6: Integration, Testing & Release (Full Test Matrix 12 kịch bản, Shadow Mode Evaluator, đóng gói PyInstaller WGC).
# 3.5.0 - Phase 5: Performance & Recovery Policy (RecoveryManager, ErrorSeverity, Exponential Backoff, SafetyBudget, PerformanceMonitor).
# 3.4.0 - Phase 4: Event-driven Decision Engine (FSM, Temporal Confirmation, Action Verification).
# 3.3.0 - Phase 3: Visual Recognition Engine (AnchorMatcher với ROI Caching, Observation Contract).
# 3.2.0 - Phase 2: Window Coordinate System (RelativePoint, RelativeRect, CoordinateTransformer, GeometryGuard, schema v3).
# 3.1.0 - Phase 1: WgcSource adapter (windows-capture), chuỗi hạ cấp WGC -> DXGI -> MSS -> PIL, FrameValidator độc lập.
# 3.0.0 - Phase 0: Baseline capture, Frame Contract & FrameSource interface, autoroll cycle benchmark.
# 2.4.1 - Fix DPI scaling: đồng bộ tọa độ pixel vật lý RegionPicker & ScreenCapture, sửa hiển thị preview PNG không bị trắng/lệch
# 2.4 - Capture overhaul: DXGI/mss/pil chain, frame-sync settle, confirm detection, SendInput click
# 2.0 - Multi-slot, profile, region picker, test inspector, animation detection
# 1.0 - Phiên bản đầu tiên
