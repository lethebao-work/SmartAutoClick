# SmartAutoClick v3.1 — Kế hoạch Visual Automation Engine

> Ngày cập nhật: 25/10/2026  
> Kế thừa: SmartAutoClick v3.0 và nền tảng refactor v2.0 (Phase 0–5 đã hoàn thành).  
> Chiến lược: Refactor tăng dần, giữ tương thích API, profile, GUI và các tính năng đang hoạt động.

---

## 1. Định hướng sản phẩm

SmartAutoClick không chỉ là phần mềm click theo màu hoặc tọa độ, mà hướng tới một nền tảng **Visual Automation** dành cho những tác vụ tự động hóa lặp lại.

Ví dụ:
- Auto Roll đến khi xuất hiện vật phẩm đạt điều kiện.
- Quan sát trạng thái giao diện rồi tự động thực hiện hành động.
- Thu thập tài nguyên theo chu trình.
- Tự động chạy các tác vụ lặp lại trong thời gian dài.
- Dừng khi hoàn thành mục tiêu, gặp lỗi hoặc vượt giới hạn cấu hình.

### Nguyên tắc thiết kế

**Observe → Understand → Decide → Act → Verify**

Phần mềm phải quan sát, xác định trạng thái, quyết định hành động, thực hiện và kiểm chứng kết quả.

Không mặc định rằng click thành công đồng nghĩa game đã tiếp nhận click. Không mặc định rằng nhận được khung hình mới đồng nghĩa giao diện game đã thay đổi. Không thực hiện hành động khi dữ liệu đầu vào chưa đáng tin cậy.

---

## 2. Những vấn đề cần giải quyết

Giữ nguyên các vấn đề đã xác định trong kế hoạch v3.0:
- Lệch tọa độ do DPI và màn hình.
- Ảnh cũ, ảnh đen.
- Capture phụ thuộc desktop.
- Nhận diện HSV tại vùng cố định.
- Engine phụ thuộc chu trình click → sleep → capture.
- Phần chụp, nhận diện và điều khiển có sự phụ thuộc lẫn nhau.

Bổ sung các vấn đề mới:

| Vấn đề | Hướng giải quyết |
|---|---|
| Ảnh mới nhưng game chưa phản hồi | Kiểm tra thay đổi tại ROI |
| Hiệu ứng chuyển động gây nhận diện nhầm | Temporal Confirmation |
| Click được gửi nhưng game không tiếp nhận | Action Verification |
| Capture thành công nhưng ảnh không hợp lệ | Frame Validation |
| Backend tự chuyển gây sai hệ tọa độ | Chuẩn hóa Frame Contract |
| Game thay đổi giao diện hoặc popup bất ngờ | Unknown State Detection |
| Bot chạy lâu, phát sinh lỗi không thể phục hồi | Recovery Policy |
| Logic nhận diện gắn cứng với Auto Roll | Observation Layer độc lập |

---

## 3. Kiến trúc tổng thể

```text
               GAME WINDOW
                    |
                    v
          [CAPTURE ADAPTER]
            WGC / DXGI / MSS
                    |
                    v
          [FRAME VALIDATION]
       Freshness / Geometry / Health
                    |
                    v
           [VISUAL ENGINE]
       Anchor / ROI / Color / Motion
                    |
                    v
          [OBSERVATION LAYER]
       Trạng thái + Confidence + Evidence
                    |
                    v
           [DECISION ENGINE]
        FSM / Rules / Temporal Check
                    |
                    v
            [ACTION ENGINE]
          Mouse / Keyboard / Macro
                    |
                    v
          [ACTION VERIFICATION]
          Quan sát kết quả hành động
                    |
                    +------> Lặp chu trình
                    |
                    v
           [RECOVERY / STOP]

          Qt GUI / Profile / Logs
          (nằm ngoài đường xử lý nóng)
```

### Quy tắc kiến trúc

Các module giao tiếp qua interface và cấu trúc dữ liệu thống nhất. Capture không quyết định click. Detector không trực tiếp điều khiển chuột. Action Engine không tự diễn giải hình ảnh. GUI không trực tiếp truy cập hoặc khóa luồng capture. Engine chịu trách nhiệm điều phối toàn bộ chu trình.

---

## 4. Kế hoạch triển khai

### PHASE 0 — Baseline, Interface và Test Harness

**Mục tiêu:** Có cơ sở đo lường và kiến trúc chuyển đổi an toàn trước khi thay backend.

Giữ nguyên các task V0-T1 đến V0-T5 của v3.0:

- [ ] **V0-T1** — Chạy `tools/benchmark_capture.py` trên máy thật, ghi lại FPS, độ trễ, tỉ lệ ảnh đen của `dxcam`, `mss`, PIL (baseline).
- [ ] **V0-T2** — Kiểm tra môi trường: Windows 10 bản 1903 trở lên, có viền vàng khi WGC chụp hay không, game đang chạy windowed, borderless hay exclusive fullscreen.
- [ ] **V0-T3** — Định nghĩa giao diện `FrameSource` (`start()`, `stop()`, `latest() -> Frame`).
- [ ] **V0-T4** — Cho `ScreenCapture` hiện tại và `FakeFrameSource` trong `tests/fakes.py` cùng tuân theo giao diện này.
- [ ] **V0-T5** — Đảm bảo 11 test hiện có vẫn pass sau khi bọc giao diện.

Bổ sung:
- [ ] **V0-T6** — Định nghĩa `Frame Contract` thống nhất giữa tất cả capture backend.
- [ ] **V0-T7** — Xây dựng bộ dữ liệu ảnh kiểm thử gồm ảnh bình thường, ảnh đen, ảnh cũ, ảnh chuyển động, ảnh sai kích thước.
- [ ] **V0-T8** — Thiết lập các chỉ số baseline: FPS, độ trễ, CPU, RAM, capture failure rate, false detection.
- [ ] **V0-T9** — Tạo benchmark cho một chu trình Auto Roll hoàn chỉnh, không chỉ benchmark tốc độ capture.
- [ ] **V0-T10** — Xác định các API hiện có phải được giữ tương thích.

#### Frame Contract đề xuất

```python
Frame:
    image
    frame_id
    timestamp
    source_timestamp
    window_id
    client_size
    geometry_version
    backend
    status
```

`timestamp` sử dụng đồng hồ monotonic. `frame_id` tăng theo khung thực sự tiếp nhận từ backend. ID không được dùng làm bằng chứng duy nhất để xác định game đã phản hồi. `geometry_version` thay đổi khi kích thước hoặc hệ tọa độ nguồn thay đổi. `status` phân biệt khung hợp lệ, nguồn bị mất, capture lỗi và các trường hợp không đáng tin cậy.

**Điều kiện hoàn thành:** Có thể thay backend mà không sửa logic nghiệp vụ.

### PHASE 1 — Capture Engine + Frame Validation

**Mục tiêu:** Xây dựng lớp chụp ảnh đáng tin cậy, độc lập với engine.

Giữ nguyên các task V1-T1 đến V1-T8:

- [ ] **V1-T1** — Chọn thư viện WGC cho Python, thử nghiệm riêng script chụp 60 giây (rò rỉ bộ nhớ và độ ổn định).
- [ ] **V1-T2** — Tạo `core/capture_wgc.py`: `WgcSource` gắn HWND, callback ghi khung vào bộ đệm một ô.
- [ ] **V1-T3** — Gắn `frame_id` tăng dần và `timestamp` (`time.monotonic()`) cho mỗi khung.
- [ ] **V1-T4** — Tìm cửa sổ game theo tiêu đề hoặc tiến trình, xử lý cửa sổ đóng, thu nhỏ, đổi kích thước.
- [ ] **V1-T5** — Giữ fail-safe v2.0: lỗi liên tiếp hoặc khung quá cũ → `CaptureError` → dừng an toàn `capture_failed`.
- [ ] **V1-T6** — Chuỗi hạ cấp `WGC → DXGI → mss`, luôn log backend và lý do hạ cấp.
- [ ] **V1-T7** — Phát hiện ảnh đen và khung có dấu hiệu đóng băng.
- [ ] **V1-T8** — Test: khung cũ không được coi là khung mới; cửa sổ biến mất thì dừng an toàn.

#### Capture Adapter

Backend ưu tiên: Windows Graphics Capture (WGC), DXGI Desktop Duplication, MSS (dự phòng cuối). Mỗi backend tuân theo cùng interface. WGC hoạt động theo callback, chỉ giữ khung mới nhất trong bộ đệm một ô.

#### Bổ sung Frame Validator

- [ ] **V1-T9** — Tạo `core/frame_validator.py`.
- [ ] **V1-T10** — Kiểm tra độ mới của khung theo timestamp và frame_id.
- [ ] **V1-T11** — Phát hiện kích thước ảnh hoặc geometry bất thường.
- [ ] **V1-T12** — Phát hiện ảnh đen, ảnh rỗng hoặc capture lỗi.
- [ ] **V1-T13** — Phân biệt ảnh tĩnh hợp lệ với capture có dấu hiệu đóng băng, dựa trên kỳ vọng thay đổi của trạng thái hiện tại.
- [ ] **V1-T14** — Khi chuyển backend, vô hiệu hóa cache hình ảnh, neo và geometry cũ.
- [ ] **V1-T15** — Chỉ cho phép hạ cấp backend nếu backend mới có thể cung cấp ảnh và hệ tọa độ hợp lệ.

**Nguyên tắc quan trọng:** Fallback không có nghĩa là WGC lỗi thì lập tức dùng DXGI và tiếp tục click. DXGI có thể chụp cả desktop thay vì chỉ cửa sổ; nếu cửa sổ bị che, kết quả không còn tương đương WGC.

Khi chuyển backend: tạm dừng hành động → khởi tạo backend mới → xác minh cửa sổ và hệ tọa độ → tìm lại anchor → chỉ tiếp tục nếu trạng thái được xác nhận. Không mặc định cửa sổ đã thu nhỏ vẫn capture và tương tác bình thường.

**Điều kiện hoàn thành:** Mọi frame chuyển sang detector đều đã qua kiểm tra hợp lệ.

### PHASE 2 — Window Coordinate System

**Mục tiêu:** Loại bỏ phụ thuộc vào tọa độ tuyệt đối của desktop.

Giữ nguyên V2-T1 đến V2-T6:
- [ ] **V2-T1** — Lưu mọi vùng soi và điểm click theo tỉ lệ 0.0–1.0 hoặc offset cửa sổ/neo.
- [ ] **V2-T2** — Tập trung `window_to_screen()` và `screen_to_window()` trong luồng chuyển đổi tọa độ cho `clicker.py`.
- [ ] **V2-T3** — Nâng `schema_version`, di trú profile tuyệt đối cũ sang tương đối.
- [ ] **V2-T4** — Cập nhật `region_picker.py` để chọn vùng trên ảnh cửa sổ game.
- [ ] **V2-T5** — Giữ ghi atomic và snapshot bất biến của `ConfigManager`.
- [ ] **V2-T6** — Test di chuyển/đổi kích thước cửa sổ giả lập vẫn ra đúng điểm click.

Bổ sung:
- [ ] **V2-T7** — Chuẩn hóa không gian tọa độ theo client area của cửa sổ.
- [ ] **V2-T8** — Phân biệt tọa độ ảnh capture, tọa độ client và tọa độ desktop.
- [ ] **V2-T9** — Kiểm tra lại geometry ngay trước khi gửi hành động.
- [ ] **V2-T10** — Phát hiện thay đổi DPI, kích thước client area và display scaling.
- [ ] **V2-T11** — Chặn click khi geometry của kết quả nhận diện không còn khớp geometry hiện tại.

**Nguyên tắc:** Điểm click và vùng quan sát lưu theo hệ tọa độ logic hoặc tương đối. Chỉ Action Engine mới chuyển tọa độ logic thành tọa độ thao tác thực tế. Không rải rác chuyển đổi tọa độ trong các module.

### PHASE 3 — Visual Recognition Engine

**Mục tiêu:** Tách khả năng nhìn và nhận diện khỏi nghiệp vụ Auto Roll.

Giữ nguyên V3-T1 đến V3-T7:
- [ ] **V3-T1** — Tạo `core/anchor.py`, `AnchorMatcher.find(frame) -> (vị trí, độ tin cậy)`.
- [ ] **V3-T2** — Công cụ chụp ảnh mẫu neo từ GUI, lưu vào `profiles/<name>/anchors/`.
- [ ] **V3-T3** — Cache neo: lần đầu tìm toàn khung, sau đó tìm quanh vị trí cũ.
- [ ] **V3-T4** — Dưới ngưỡng tin cậy thì báo mất neo, không đoán.
- [ ] **V3-T5** — Tính vùng slot và điểm click theo offset neo.
- [ ] **V3-T6** — Giữ `ColorDetector`, morphology, `confidence`, `COLOR_PRIORITY` làm xác nhận cuối trên ROI.
- [ ] **V3-T7** — Bộ ảnh test nhiều kích thước, độ sáng và `tests/test_anchor.py`.

```text
Frame
  |
  v
Anchor Detection
  |
  v
Region Localization
  |
  v
Feature Extraction
  |
  +-- Template Matching
  +-- Color Detection
  +-- Motion Detection
  +-- OCR (Optional)
  |
  v
Observation
```

#### Bổ sung Observation Layer

- [ ] **V3-T8** — Tạo `core/observation.py`.
- [ ] **V3-T9** — Chuẩn hóa kết quả nhận diện thành Observation, không trả trực tiếp quyết định click.
- [ ] **V3-T10** — Mỗi Observation liên kết với frame_id và geometry_version.
- [ ] **V3-T11** — Thêm confidence và evidence phục vụ kiểm tra kết quả.
- [ ] **V3-T12** — Hỗ trợ nhiều detector xử lý những vùng khác nhau trên cùng một frame.
- [ ] **V3-T13** — Tạo tập ảnh kiểm thử có nhãn để đo false positive và false negative.

```python
Observation:
    frame_id
    geometry_version
    anchor
    regions
    detected_objects
    confidence
    evidence
    status
```

Detector chỉ báo đặc điểm quan sát và mức tin cậy. Decision Engine mới xác định kết quả đó có thỏa điều kiện dừng Auto Roll hay không.

**Hiệu năng:** Tìm anchor trong ROI cache trước; tìm toàn khung khi mất neo; chỉ kiểm tra vùng cần thiết; chạy detector nhẹ trước, detector nặng khi cần. ORB/AKAZE không phải đường mặc định, chỉ dùng khi template matching không giải quyết được biến đổi hình học. OCR dành cho nhu cầu đọc chữ/số trên ROI nhỏ.

### PHASE 4 — Event-driven Decision Engine

**Mục tiêu:** Chuyển từ macro click theo thời gian cố định thành chu trình điều khiển có kiểm chứng.

Giữ nguyên V4-T1 đến V4-T8:
- [ ] **V4-T1** — Tạo `core/state_machine.py` cùng bảng chuyển trạng thái.
- [ ] **V4-T2** — Xác định game phản hồi bằng frame sau action và vùng kết quả thay đổi thật.
- [ ] **V4-T3** — Chờ ổn định theo N khung với timeout, tái dùng ý tưởng `TwoPhaseSettle`.
- [ ] **V4-T4** — Popup, mất neo, mất kết nối, timeout → dừng và báo, không đoán.
- [ ] **V4-T5** — Giữ thứ tự quét slot → tính lại `all_locked` → kiểm tra ngân sách → click Roll.
- [ ] **V4-T6** — Tích hợp `WindowGuard`, can thiệp chuột, `BudgetGuard`.
- [ ] **V4-T7** — Biến `engine.py` thành lớp điều phối mỏng, tách module thích hợp.
- [ ] **V4-T8** — Mở rộng `test_engine_loop.py`, `test_frame_gating.py` bằng `FakeFrameSource`.

```text
READY
  |
  v
PRECHECK
  |
  v
ACTION_SENT
  |
  v
WAIT_RESPONSE
  |
  v
WAIT_SETTLE
  |
  v
OBSERVE
  |
  v
CONFIRM
  |
  v
DECIDE
  |
  +------> READY
  +------> COMPLETED
  +------> RECOVERY
  +------> STOPPED
```

#### Temporal Confirmation

- [ ] **V4-T9** — Xác nhận kết quả qua nhiều frame hợp lệ.
- [ ] **V4-T10** — Frame dùng xác nhận phải mới, không đếm lại một ảnh nhiều lần.
- [ ] **V4-T11** — Kết quả quan trọng đạt ngưỡng tin cậy và số lần xác nhận theo profile.
- [ ] **V4-T12** — Xử lý frame liên tiếp có kết quả mâu thuẫn.
- [ ] **V4-T13** — Chưa đủ bằng chứng thì tiếp tục quan sát, không tự click.
- [ ] **V4-T14** — Timeout riêng cho từng trạng thái.

Ví dụ Auto Roll: phát hiện đỏ → kiểm tra confidence → xác nhận trên frame mới → nếu không khớp thì quan sát lại, nếu khớp thì dừng. Ngưỡng confidence và số khung xác nhận cấu hình theo profile, không hardcode chung mọi game.

#### Action Verification

- [ ] **V4-T15** — Ghi lại Observation trước hành động.
- [ ] **V4-T16** — Gắn mã riêng cho từng action.
- [ ] **V4-T17** — Sau action, đợi bằng chứng game đã phản hồi.
- [ ] **V4-T18** — Phân biệt gửi input thành công và game thực sự thực hiện hành động.
- [ ] **V4-T19** — Không lặp lại action không an toàn khi chưa xác định kết quả lần trước.

**Nguyên tắc:** Không dùng `sleep` cố định để đoán game đã xử lý xong. Chờ điều kiện hình ảnh với timeout và giới hạn tần suất xử lý phù hợp.

### PHASE 5 — Performance, Reliability & Recovery

**Mục tiêu:** Bot chạy dài hạn với tài nguyên hợp lý, không phát sinh hành động ngoài kiểm soát.

Giữ nguyên V5-T1 đến V5-T7:
- [ ] **V5-T1** — Luồng chụp riêng, chỉ giữ frame mới nhất.
- [ ] **V5-T2** — Luồng quyết định đọc frame mới nhất, không giữ lock lâu.
- [ ] **V5-T3** — GUI chỉ nhận trạng thái/số roll/confidence/FPS/backend qua signal.
- [ ] **V5-T4** — Ưu tiên ảnh thu nhỏ hoặc ROI thay vì toàn khung.
- [ ] **V5-T5** — Đo độ trễ frame, tìm neo, quyết định.
- [ ] **V5-T6** — Giữ `join` luồng cũ, `Event` mới mỗi `start()`, `finally` ép `STOPPED`.
- [ ] **V5-T7** — Chỉ viết đường nóng Rust/C++ qua binding nếu benchmark chứng minh Python chưa đủ.

#### 5.1 Performance

- [ ] **V5-T8** — Latest-frame, không tạo hàng đợi ảnh tăng vô hạn.
- [ ] **V5-T9** — Tách tốc độ capture khỏi tốc độ detector.
- [ ] **V5-T10** — Worker được đánh thức khi có frame mới, tránh busy-wait.
- [ ] **V5-T11** — Theo dõi CPU, RAM, FPS, thời gian nhận diện và độ trễ quyết định.
- [ ] **V5-T12** — Tối ưu ROI/cache, tránh sao chép ảnh không cần thiết.

Không mặc định cần xử lý 60 FPS khi workflow chỉ cần kiểm tra vài lần mỗi giây.

#### 5.2 Recovery Policy

Tạo `core/recovery.py`:
- [ ] **V5-T13** — Phân loại lỗi: tạm thời, có thể phục hồi, bắt buộc dừng.
- [ ] **V5-T14** — Retry limit và backoff giới hạn.
- [ ] **V5-T15** — Dừng action khi mất cửa sổ, mất neo/geometry hoặc dữ liệu không đáng tin.
- [ ] **V5-T16** — Khởi tạo lại capture khi backend có lỗi phục hồi được.
- [ ] **V5-T17** — Sau recovery, quan sát lại trạng thái game rồi mới tiếp tục.
- [ ] **V5-T18** — Không tự gửi lại thao tác có thể tiêu hao tài nguyên hoặc gây hậu quả không mong muốn.

#### 5.3 Window & Input Safety

- [ ] **V5-T19** — Tái sử dụng `WindowGuard` và phát hiện người dùng can thiệp.
- [ ] **V5-T20** — Kiểm tra cửa sổ đích ngay trước khi gửi input.
- [ ] **V5-T21** — Nếu phương thức input cần foreground, chỉ làm khi foreground hợp lệ.
- [ ] **V5-T22** — Giới hạn ngân sách, số lượt, thời gian chạy.
- [ ] **V5-T23** — Khi stop hoàn tất, action cũ trong hàng đợi không còn được thực hiện.

**Điều kiện hoàn thành:** Lỗi Capture/Detector không dẫn đến click ngoài ý muốn.

### PHASE 6 — Integration, Testing & Release

**Mục tiêu:** Chuyển đổi an toàn từ kiến trúc cũ sang mới.

Giữ nguyên V6-T1 đến V6-T6:
- [ ] **V6-T1** — OCR tùy chọn trên ROI chữ/số, mặc định tắt.
- [ ] **V6-T2** — Cập nhật `requirements.txt`, `requirements.lock` cho WGC; cân nhắc bỏ `pyautogui` nếu không cần.
- [ ] **V6-T3** — Cập nhật `SmartAutoClick.spec`, đóng gói WGC và anchor (`sys._MEIPASS`), giữ `upx=False`.
- [ ] **V6-T4** — CI headless dùng FakeFrameSource; WGC thật kiểm thử thủ công trên Windows.
- [ ] **V6-T5** — Cập nhật README/DESIGN: yêu cầu hệ thống, borderless, ảnh neo, mất neo.
- [ ] **V6-T6** — Chạy dài 4–8 giờ: RAM, click sai, dừng an toàn.

#### Shadow Mode

- [ ] **V6-T7** — Engine mới quan sát và quyết định song song nhưng không click.
- [ ] **V6-T8** — So sánh engine cũ/mới trên cùng dữ liệu đầu vào.
- [ ] **V6-T9** — Log trường hợp khác quyết định để phân tích.
- [ ] **V6-T10** — Cho phép rollback về backend/engine cũ nếu tọa độ và điều kiện an toàn vẫn hợp lệ.

#### Test Matrix

| Kịch bản | Kết quả mong muốn |
|---|---|
| Cửa sổ thay đổi vị trí | Click vẫn chính xác |
| DPI thay đổi | Không lệch tọa độ |
| Frame bị lặp | Không coi là phản hồi mới |
| Game đứng hình | Timeout có kiểm soát |
| Hiệu ứng chuyển động | Không nhận nhầm kết quả cuối |
| Popup bất ngờ | Dừng hoặc xử lý theo rule đã cấu hình |
| Mất anchor | Không click |
| Capture backend lỗi | Recovery hoặc dừng an toàn |
| Game phản hồi chậm | Không click chồng |
| Người dùng can thiệp | Giữ hành vi WindowGuard |
| Stop khi worker đang xử lý | Không có action mới sau khi stop hoàn tất |
| Treo máy nhiều giờ | Không tăng bộ nhớ bất thường |

#### Definition of Done

- [ ] Toàn bộ test cũ và test mới pass.
- [ ] Các module mới có unit test độc lập.
- [ ] Không click dựa trên frame không hợp lệ.
- [ ] Không dùng tọa độ desktop cố định trong logic nghiệp vụ mới.
- [ ] Thay backend capture mà không sửa detector.
- [ ] Thay detector mà không sửa Action Engine.
- [ ] Có bằng chứng hiệu năng so với baseline.
- [ ] Chạy dài ít nhất 4 giờ, mở rộng 8 giờ nếu điều kiện cho phép.
- [ ] Log đủ truy nguyên mỗi quyết định và lần click.
- [ ] Profile cũ được di trú hoặc giữ tương thích có kiểm thử.

---

## 5. Cấu trúc module mục tiêu

*Định hướng, không bắt buộc tạo tất cả file ngay từ đầu.*

```text
core/
│
├── capture/
│   ├── base.py
│   ├── wgc.py
│   ├── dxgi.py
│   └── validator.py
│
├── vision/
│   ├── anchor.py
│   ├── detector.py
│   ├── observation.py
│   ├── motion.py
│   └── temporal.py
│
├── decision/
│   ├── state_machine.py
│   ├── rules.py
│   └── recovery.py
│
├── action/
│   ├── executor.py
│   └── verification.py
│
├── engine.py
├── config.py
└── ...
```

Chỉ di chuyển/thay thế module hiện có khi Phase tương ứng kiểm thử thành công. Không tách module máy móc nếu chỉ tăng phức tạp.

---

## 6. Nguyên tắc phát triển lâu dài

### Engine dùng chung, workflow riêng

Auto Roll là workflow đầu tiên trên nền Visual Automation Engine.

```text
Visual Automation Engine
          |
          +-- Auto Roll
          +-- Resource Farming
          +-- Repetitive Tasks
          +-- Custom Workflow
```

Mỗi workflow định nghĩa đối tượng quan sát, điều kiện nhận diện, điều kiện hành động, cách kiểm chứng kết quả, điều kiện hoàn thành/dừng và giới hạn an toàn. Không viết Capture Engine hoặc Click Engine riêng cho từng workflow.

---

## 7. Thứ tự triển khai cuối cùng

| Thứ tự | Giai đoạn | Ưu tiên |
|---|---|---|
| 1 | Phase 0 — Baseline & Contract | Bắt buộc |
| 2 | Phase 1 — Capture & Validation | Rất cao |
| 3 | Phase 2 — Coordinate System | Rất cao |
| 4 | Phase 3 — Visual Engine & Observation | Rất cao |
| 5 | Phase 4 — Decision & Verification | Rất cao |
| 6 | Phase 5 — Performance & Recovery | Cao |
| 7 | Phase 6 — Testing & Release | Bắt buộc trước phát hành |

**Nguyên tắc triển khai:** Không thay thế hoàn toàn thành phần cũ chỉ vì thành phần mới đã chạy được. Thành phần mới phải chứng minh tính chính xác, ổn định và tương thích bằng test và benchmark.

Mục tiêu v3.1 là một nền tảng tự động hóa thị giác đáng tin cậy, có thể mở rộng nhiều loại bot mà không phải liên tục sửa phần lõi khi thêm tính năng.

> Dùng tài liệu này làm kiến trúc đích và từng task V0–V6 làm phạm vi thực thi. Không triển khai tất cả phase trong một lần hoặc tự ý thay thế phần đang hoạt động tốt.
