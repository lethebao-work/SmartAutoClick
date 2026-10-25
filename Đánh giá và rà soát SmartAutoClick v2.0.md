# Đánh giá và rà soát SmartAutoClick v2.0

*Báo cáo kỹ thuật · 25/10/2026 · Phạm vi: README, config.json, DESIGN.md và mã nguồn trong Autoclick.zip (khoảng 5.300 dòng Python)*

## 1. Tóm tắt điều hành

SmartAutoClick là công cụ roll tự động dùng thị giác máy tính: click nút Roll, chờ, chụp vùng kết quả, so màu HSV, rồi dừng hoặc khóa khi thấy màu hiếm. Phần giao diện và tính năng xung quanh khá đầy đủ (khay hệ thống, mini widget, macro, profile, phím tắt toàn cục). Vấn đề nằm ở **lõi điều khiển**: nó chạy theo kiểu vòng hở, thiếu cơ chế fail-safe, và một số tính năng được mô tả nhiều hơn những gì code thực sự làm.

### Kết luận chính

- Có **7 lỗi P0**, trong đó 4 lỗi đã **tái hiện bằng chạy thử** (engine thật, camera và chuột giả). Chúng khiến bot bỏ sót hoặc phá đồ hiếm mà không báo gì.
- Ba lỗi nặng nhất về nghiệp vụ: roll cuối cùng không bao giờ được kiểm tra (E-01), chụp màn hình hỏng thì thành ảnh đen im lặng (E-04), và `lock` không khóa gì trong game (E-05).
- Nguyên nhân gốc chung: hệ thống **hành động theo thời gian, quan sát bằng chỉ số yếu và mặc định fail-open**, trong khi chi phí lỗi là bất đối xứng (bỏ sót đồ hiếm là mất vĩnh viễn, dừng nhầm chỉ tốn vài giây).
- Khuyến nghị: **Phương án B** (refactor có kiểm soát), bắt đầu bằng việc đưa bộ harness giả lập vào repo làm bộ test đầu tiên.
- Độ tin cậy: cao (khoảng 90%) với các mục \[CHẠY THỬ\] và \[CODE\]; trung bình (khoảng 60%) với các mục \[GIẢ THUYẾT\], phụ thuộc game và cấu hình máy.

### Bảy việc nên làm trước

| # | Việc | Lỗi liên quan | Công sức (ước lượng thô) |
| --- | --- | --- | --- |
| 1 | Đưa harness giả lập vào repo làm test đầu tiên | E-01 đến E-04 | 0,5 ngày |
| 2 | Quét kết quả trước, kiểm tra giới hạn sau; tính lại `all_locked` | E-01, E-02 | 0,5 ngày |
| 3 | Capture ném lỗi thay vì trả ảnh đen; dừng khi mất thị giác | E-04 | 0,5 ngày |
| 4 | Bọc vòng lặp bằng try/except/finally, join thread khi dừng | E-08, E-09 | 0,5 ngày |
| 5 | Một hàm `validate_and_start()` dùng chung cho nút Start và F6 | E-07 | 0,5 ngày |
| 6 | Quyết định số phận của `lock`: khóa thật hoặc đổi tên cho đúng | E-05 | 1 đến 2 ngày |
| 7 | Phát hiện animation hai pha (thấy thay đổi, rồi mới tĩnh) | E-03 | 1 đến 2 ngày |

## 2. Phạm vi, phương pháp và nhãn độ tin cậy

Phương pháp: (1) đọc README, config.json, DESIGN.md và cây thư mục trên GitHub; (2) giải nén Autoclick.zip và đọc code; (3) chạy `AutoClickEngine` thật với `ScreenCapture` và `InputSimulator` được thay bằng bản giả để kiểm chứng logic vòng lặp; (4) xếp hạng bằng FMEA (Failure Mode and Effects Analysis).

| Nhãn | Ý nghĩa |
| --- | --- |
| CHẠY THỬ | Tái hiện bằng harness: engine thật, camera và chuột giả |
| CODE | Đọc trực tiếp từ mã nguồn, có số dòng, chưa chạy |
| FILE | Dựa trên README, config.json, DESIGN.md, danh sách file |
| GIẢ THUYẾT | Lỗi phổ biến của kiểu kiến trúc này, chưa kiểm chứng |

**Giới hạn của đánh giá**

- Môi trường chạy thử là Linux không có màn hình. Không chạy GUI, không chạy trên Windows, không có game thật.
- Đã đọc kỹ toàn bộ `core/`, `main.py`, `build.py`, `test_core.py`. `main_window.py` chỉ đọc các đoạn liên quan (khoảng một phần tư). `color_sampler.py`, `compact_window.py`, `scenario_builder.py`, `test_inspector.py` chỉ khảo sát bằng tìm kiếm.
- Repo chỉ có 1 commit nên không có lịch sử để xét xu hướng lỗi.
- Mọi điểm liên quan DPI, exclusive fullscreen, quyền admin và anti-cheat đều chưa kiểm thử trên máy thật.

## 3. Kiến trúc hiện tại

Công nghệ: Python 3.12, PySide6 (GUI), OpenCV (màu HSV), mss và Pillow (chụp màn hình), pyautogui (chuột), keyboard (phím tắt toàn cục), pynput (ghi macro), PyInstaller (đóng gói).

| File | Dòng | Vai trò | Nhận xét |
| --- | --- | --- | --- |
| core/engine.py | 572 | Vòng lặp chính, AnimationDetector, BudgetGuard, RuleEngine | Bốn trách nhiệm trong một file, không có điểm cắm để test |
| core/detector.py | 187 | Mặt nạ màu HSV | `border_only` có nhưng không ai gọi |
| core/capture.py | 126 | mss và PIL | Fallback ảnh đen |
| core/clicker.py | 49 | pyautogui | Lệch ±2px |
| core/config\_manager.py | 187 | Đọc và ghi JSON | Merge nông, ghi không atomic |
| core/macro\_recorder.py | 185 | pynput và pyautogui | Nuốt FailSafe |
| gui/main\_window.py | 1.854 | Giao diện 5 tab, tray, profile | God Object |
| gui/scenario\_builder.py | 571 | Tab kịch bản | Chỉ ghi vào cùng bộ ô số |
| gui/test\_inspector.py, color\_sampler.py, region\_picker.py, compact\_window.py | 362, 487, 227, 239 | Công cụ hỗ trợ | Dùng tọa độ logic của Qt ở một số nơi |
| main.py | 84 | Khởi chạy, phím F6 và F7 | F6 đi đường tắt vào engine |

Luồng chạy hiện tại:

```
Start hoặc F6 -> engine.start() -> thread _run_loop
  lặp:
    pause.wait()
    kiểm tra budget, kiểm tra max_rolls      <- chạy TRƯỚC khi xem kết quả
    quét từng slot -> detect -> rule (stop hoặc lock)
    click Roll
    chờ: delay cố định cộng jitter, hoặc animation-detect
```

Kết quả của lần click này chỉ được xem ở vòng kế tiếp, sau hai bước kiểm tra giới hạn. Đây là gốc của E-01.

## 4. Nguyên nhân gốc

| Mã | Nguyên nhân | Biểu hiện |
| --- | --- | --- |
| RC-1 | Vòng hở: hành động theo thời gian, quan sát bằng một chỉ số yếu, quyết định không có trạng thái | E-01, E-02, E-03, E-10 |
| RC-2 | Bỏ qua chi phí bất đối xứng: mặc định fail-open dù bỏ sót đồ hiếm tệ hơn dừng nhầm | E-04, E-11 |
| RC-3 | Nhiều nguồn sự thật cho cùng một thứ (màu, rule, profile) | C-01 đến C-05 |
| RC-4 | God Object và không có điểm cắm (seam) nên không test được | C-09, R-05 |
| RC-5 | Lỗi bị nuốt: 43 `except Exception`, 27 khối kết thúc bằng `pass` | E-04, E-08, C-08 |
| RC-6 | Giao diện và tài liệu hứa nhiều hơn code làm | E-05, C-05, C-06, R-07 |

## 5. Sổ đăng ký lỗi

Mức độ: **P0** mất hoặc phá đồ hiếm, hành vi sai nghiêm trọng; **P1** độ tin cậy và an toàn vận hành; **P2** dữ liệu, cấu hình, giao diện; **P3** repo, đóng gói, tài liệu.

### 5.1 P0: mất hoặc phá đồ hiếm

| ID | Lỗi và hậu quả | Vị trí | Nhãn | Hướng sửa |
| --- | --- | --- | --- | --- |
| E-01 | **Roll cuối không được kiểm tra.** Kiểm tra `max_rolls` và `budget` nằm trước bước quét. Roll cuối (hoặc roll làm hết tiền) bị bỏ qua; bot dừng với `max_rolls_reached` hoặc `out_of_budget` dù màn hình đang có đồ hiếm | engine.py:458-468 so với 470+ | CHẠY THỬ (A) | Quét trước, kiểm tra giới hạn sau |
| E-02 | **Roll thừa sau khi khóa slot cuối.** `all_locked` đặt False trước khi quét (dòng 482) và không tính lại, nên bot click thêm một lần rồi mới dừng (3 click thay vì 2) | engine.py:472, 482, 536-541 | CHẠY THỬ (B) | Tính lại `all_locked` ngay sau vòng quét, dừng trước khi click |
| E-03 | **Nhận diện animation xong sai.** Vùng còn tĩnh lúc game xử lý bị coi là xong sau khoảng 0,25s (3 frame). Hết `anim_max_wait` vẫn đi tiếp. Chỉ theo dõi `regions[0]`. Tính năng này tắt mặc định, nên mặc định chỉ có delay cố định 1,5s ± 100ms | engine.py:31-86, 333-357; config.json | CHẠY THỬ (C) | Hai pha: thấy thay đổi rồi mới tĩnh; kết hợp nút Roll sẵn sàng; hợp nhất mọi slot; timeout thì dừng ở trạng thái không chắc |
| E-04 | **Chụp hỏng thành ảnh đen im lặng.** Khi mss và PIL đều lỗi, trả `np.zeros` và mọi lỗi bị `except: pass`. Ảnh đen không có màu nào nên bot roll tiếp mà không biết mình mù. Khóa màn hình, ngủ máy, exclusive fullscreen đều dẫn tới kịch bản này | capture.py:301-316, 328-341; engine.py:353-354 | CHẠY THỬ (D) | `CaptureError`; dừng sau N lần lỗi liên tiếp; kiểm tra ảnh đen thuần (mean gần 0, std bằng 0) |
| E-05 | **`lock` chỉ là cờ nội bộ.** Slot được thêm vào `_locked_slots` rồi bị bỏ qua khi quét; không có click khóa, config không có tọa độ nút khóa. Roll tiếp sẽ ghi đè món đã khóa nếu game roll mọi slot. UI lại mô tả là khóa slot | engine.py:514-531; main\_window.py:855, 1628 | CODE | Thêm `lock_click` theo slot và xác nhận khóa thành công; hoặc đổi tên thành bỏ qua slot phía bot kèm cảnh báo |
| E-06 | **Nhận diện màu yếu.** Ngưỡng 1% trên cả vùng, không lọc nhiễu; `border_only` không được gọi ở đâu; chọn màu theo diện tích lớn nhất thay vì độ hiếm; S/V tối thiểu thấp (50 đến 100) dễ khớp nền UI; dải hue chạm nhau (35 giữa gold và green, 125 giữa blue và purple), hở 85-95; hue 180 không hợp lệ trong OpenCV (0-179) | detector.py:6-12, 57-116, 148-156; config.json | CODE (tần suất dương tính giả: GIẢ THUYẾT) | Vòng viền hoặc khung rarity; connected components với diện tích tối thiểu; ngưỡng riêng theo màu và slot; ưu tiên theo độ hiếm; điểm tin cậy |
| E-07 | **F6 bỏ qua xác thực.** Nút Start gọi `save_ui_to_config` và kiểm tra dữ liệu; F6 gọi thẳng `engine.toggle_pause()`. Thay đổi chưa lưu bị bỏ qua; danh sách màu rỗng thì bot roll mù đến hết `max_rolls` | main.py (on\_f6); main\_window.py:1527-1537; engine.py:274-292 | CODE | Một hàm `validate_and_start()` dùng chung; engine tự kiểm tra cấu hình đã resolve |

### 5.2 P1: độ tin cậy và an toàn vận hành

| ID | Lỗi | Vị trí | Nhãn | Hướng sửa |
| --- | --- | --- | --- | --- |
| E-08 | Thread engine chết âm thầm. `_run_loop` không có try/except/finally; thiếu key trong region (dòng 484) hoặc roll\_btn (435) làm thread thoát, UI vẫn hiện RUNNING, không gọi `on_finished` | engine.py:425-572 | CODE | try/except/finally; đặt STOPPED và báo lỗi lên GUI |
| E-09 | Không join thread nên có thể có hai vòng lặp song song: `start()` gọi `_stop_event.clear()` khi thread cũ chưa thoát (F7 rồi F6 nhanh). `MacroPlayer.stop()` đặt `is_playing=False` ngay nên `play()` lại được khi thread cũ còn chạy | engine.py:274-292, 314-323; macro\_recorder.py:160-163 | CODE (cửa sổ race hẹp) | join có timeout; mỗi lần chạy một Event mới |
| E-10 | Không ràng buộc cửa sổ game: không kiểm tra foreground, không phát hiện người dùng đang di chuột. Alt-tab thì bot click vào ứng dụng khác. Macro và engine có thể chạy đồng thời | toàn bộ core/; main\_window.py:1783-1791 | CODE | Foreground guard (GetForegroundWindow và tên process), tọa độ theo cửa sổ, phát hiện chuột bị di, khóa loại trừ lẫn nhau |
| E-11 | BudgetGuard fail-open và log sai: calibrate lỗi vẫn log đã ghi nhận độ sáng; mọi except trả False; baseline là độ sáng lúc bắt đầu nên nút đã mờ sẵn thì không bao giờ kích hoạt; `reload_config()` tạo guard mới với baseline None nên âm thầm tắt. Mặc định tắt | engine.py:93-143, 261-272, 441-444 | CODE | So với template nút Roll sẵn sàng; lỗi thì dừng; bật mặc định khi đã cấu hình |
| E-12 | Macro: FailSafe bị nuốt (`except Exception: pass` quanh `pyautogui.click`); không jitter, tọa độ và thời gian y hệt mỗi vòng; delay bước đầu (từ lúc bấm Record đến click đầu) bị lặp mỗi vòng; chỉ ghi nhấn chuột, không nhả, kéo, cuộn, phím; `import pyautogui` không được bảo vệ | macro\_recorder.py:11, 34, 118, 136-139 | CODE | Cho FailSafeException thoát vòng; chuẩn hóa delay bước đầu; mở rộng loại sự kiện |
| E-13 | Tọa độ logic và vật lý (DPI). Region picker trả tọa độ logic của Qt và chỉ chụp màn hình chính dù overlay phủ cả virtual desktop; preview chính dùng Qt, còn engine và Test Inspector dùng mss (pixel vật lý). Ở scale 125 đến 150% vùng có thể lệch | region\_picker.py:76-79, 185-222; main\_window.py:449-451; capture.py | CODE (tác động thật cần kiểm thử) | `SetProcessDpiAwarenessContext` PER\_MONITOR\_AWARE\_V2; quy đổi bằng devicePixelRatio đúng màn hình; lưu tọa độ tương đối |
| E-14 | Ảnh bằng chứng: đường dẫn tương đối `screenshots/` phụ thuộc thư mục làm việc; lỗi ghi chỉ WARN; chụp toàn màn hình chính (`monitors[1]`) nên sai nếu game ở màn hình khác; không xoay vòng nên đầy ổ | engine.py:370-382; capture.py:318-324 | CODE | Lưu vào `%APPDATA%`, chụp đúng vùng cửa sổ game, giới hạn số lượng |
| E-15 | Giả lập thời gian yếu: delay đều ± uniform (khoảng ±6,7% với 1,5s ± 100ms), click lệch ±2px, macro không có gì. README tuyên bố ngăn chặn hoàn toàn anti-macro là phóng đại | clicker.py:226-228; engine.py:554-569; README | CODE, FILE | Bỏ tuyên bố; ghi rõ rủi ro ToS (mục 12) |
| E-16 | Quyền và hook: `keyboard` (hook mức thấp) và pyautogui (SendInput) không gửi được input vào cửa sổ chạy quyền admin (UIPI); main.py chỉ in cảnh báo ra console | main.py (setup\_global\_hotkeys) | GIẢ THUYẾT | Phát hiện và cảnh báo khi khởi động; tùy chọn chạy elevated; thay bằng RegisterHotKey |
| E-17 | Đóng cửa sổ (X) chỉ ẩn vào khay và engine tiếp tục chạy. Là thiết kế chủ ý nhưng là rủi ro an toàn khi bot vẫn click lúc cửa sổ không hiện | main\_window.py:1837-1850 | CODE | Chỉ báo rõ trạng thái, giới hạn thời gian chạy, hỏi lại khi đóng lúc đang chạy |

### 5.3 P2: dữ liệu, cấu hình, giao diện

| ID | Lỗi | Vị trí | Nhãn | Hướng sửa |
| --- | --- | --- | --- | --- |
| C-01 | Ba nơi định nghĩa màu, giá trị lệch nhau: `BUILTIN_COLORS`, `DEFAULT_CONFIG`, `config.json` (ví dụ gold h\_min 18 so với 20, purple s\_min 50 so với 60) | detector.py:6-12; config\_manager.py:33-81 | CODE | Một nguồn duy nhất; preset màu thuộc về profile |
| C-02 | Hai cổng `target_colors` và `action_rules` cho cùng một quyết định. Màu có rule nhưng không tick thì bị bỏ qua; tick mà không có rule thì mặc định STOP. `config.json` mẫu có 5 rule stop nhưng chỉ 2 màu mục tiêu | engine.py:166-177; config.json | CODE | Gộp thành một bảng rule có thứ tự ưu tiên |
| C-03 | Quản lý config yếu: merge nông; ghi trực tiếp không atomic; lỗi parse thì dùng default trong bộ nhớ rồi bị ghi đè ở lần lưu kế tiếp; không validation hay migration; đơn vị lẫn (delay giây, jitter ms); `DEFAULT_CONFIG` thiếu key (`budget_guard`, `use_animation_detection`, `anim_*`, `profiles`); `get()` trả tham chiếu mutable dùng chung giữa GUI và engine, không khóa | config\_manager.py:104-149 | CODE | pydantic; ghi atomic (file tạm rồi os.replace); version và migration; snapshot bất biến khi bắt đầu chạy |
| C-04 | `reload_config()` gọi được khi đang chạy: thay đối tượng giữa vòng lặp. `save_ui_to_config` cắt hoặc sửa `watch_regions` trong khi engine đang duyệt cùng list | engine.py:261-272; main\_window.py (save\_ui\_to\_config) | CODE | Engine chỉ đọc snapshot cố định cho mỗi lần chạy |
| C-05 | Profile chỉ lưu `roll_button` và `target_colors`; chuyển profile chỉ đổi widget, không đổi region, delay, rule, budget; không ràng buộc game | main\_window.py:1410-1452 | CODE | Profile là toàn bộ cấu hình cộng khóa cửa sổ game, lưu thành file riêng |
| C-06 | Scenario Builder chỉ là vỏ: các bước chỉ ghi vào cùng bộ ô số, engine không đọc kịch bản (không có scenario trong core/); bước click `slot_N` ghi đè nút Roll; khối xử lý bọc `except: pass` | main\_window.py:1155-1185; scenario\_builder.py | CODE | Xây executor kịch bản thật, hoặc bỏ tab để khỏi gây hiểu nhầm |
| C-07 | Tọa độ tuyệt đối trong config (roll\_button, regions, budget\_guard) không gắn cửa sổ, monitor, DPI | config.json | FILE | Tọa độ tương đối (0 đến 1) theo client rect của cửa sổ game |
| C-08 | Lỗi bị nuốt hàng loạt: 43 `except Exception` (engine 13, capture 8, main\_window 9, macro 7, main 3, config 2, clicker 1), 27 khối kết thúc bằng `pass` | toàn mã nguồn | CODE | Dùng `logging`; chỉ bắt exception cụ thể; lỗi nghiệp vụ phải đổi trạng thái |
| C-09 | `main_window.py` dài 1.854 dòng, ôm UI, đọc ghi config, điều phối engine, macro, tray, profile, scenario; không test được | gui/main\_window.py | CODE | Tách presenter hoặc viewmodel; GUI chỉ phát sự kiện |
| C-10 | Ảnh minh họa không khớp quyết định: `get_annotated_result` dùng morphology và diện tích tối thiểu 20, còn quyết định thì không | detector.py:168-187 | CODE | Một pipeline dùng chung cho cả hai |
| C-11 | Dùng `time.time()` cho timeout và sleep, chịu ảnh hưởng khi đồng hồ hệ thống đổi | engine.py:326-343 | CODE | `time.monotonic()` |
| C-12 | GUI tạo `ScreenCapture()` mới ở nhiều nơi (mỗi lần một instance mss), chưa thấy đóng; `engine.test_single_check` là code chết | main\_window.py:471, 1361; test\_inspector.py:291 | CODE, GIẢ THUYẾT | Dùng chung một nguồn khung hình; xóa code chết |

### 5.4 P3: repo, đóng gói, tài liệu

| ID | Vấn đề | Nhãn | Hướng sửa |
| --- | --- | --- | --- |
| R-01 | README bước 1 hướng dẫn mở `dist/`, nhưng `.gitignore` loại `dist/` và `*.exe`, mục Releases trống. Người clone repo không làm theo được | FILE | Đăng bản build lên GitHub Releases, sửa README |
| R-02 | Một file EXE duy nhất là không đúng: dùng `--onefile` nhưng `build.py` vẫn copy `assets/` và `config.json` cạnh exe vì `main.py` tìm assets theo thư mục exe, không theo `sys._MEIPASS`. Chỉ chép exe thì mất icon (tray có kiểm tra tồn tại nên không sập) | CODE | `sys._MEIPASS` cho tài nguyên, `%APPDATA%` cho dữ liệu người dùng |
| R-03 | Quy trình build lẫn lộn: zip có cả onefile (spec, build.py) và onedir (`dist/SmartAutoClick/_internal`). Spec bật `upx=True`, làm tăng khả năng antivirus báo nhầm | CODE | Chốt một kiểu, tắt UPX |
| R-04 | `DESIGN.md` mang tên ClickCraft, chứa hai bảng màu khác nhau trong cùng file (front-matter `#0b1326` và `#c0c1ff`, phần thân `#0F172A` và `#6366F1`), có bản trùng `DESIGN (1).md`; Geist, Hanken Grotesk, squircle, box-shadow, `tabular-nums` là khái niệm CSS, khó áp thẳng cho Qt Widgets và không có font đi kèm | FILE | Một file thiết kế, một bảng màu, hiện thực bằng QSS và token trong code |
| R-05 | `test_core.py` là smoke test: test chụp màn hình vẫn pass với ảnh đen fallback; mở và có thể ghi `config.json` thật; không test vòng lặp, lock, animation | CODE | Test bằng khung hình ghi sẵn và game giả (mục 10) |
| R-06 | Không license, mô tả, CI, release; chỉ 1 commit; `requirements.txt` dùng `>=` không khóa phiên bản; ba thư viện input chồng chéo (pyautogui, pynput, keyboard) | FILE | Lock file (uv hoặc pip-tools), CI, gom về một lớp input |
| R-07 | README vượt thực tế: chống hoàn toàn anti-macro; Profile System; khóa giữ ô; Budget Guard và Animation Detection đều tắt mặc định | FILE, CODE | Viết lại theo đúng hành vi |
| R-08 | Kích thước: `cv2.pyd` 86 MB và `opencv_videoio_ffmpeg` 30 MB trong bản dist dù ứng dụng không dùng video; file `.pkg` khoảng 113 MB | FILE | `opencv-python-headless`, loại module Qt không dùng |

### 5.5 Lỗi tiềm ẩn chưa kiểm chứng

| ID | Rủi ro | Cách giảm |
| --- | --- | --- |
| L-01 | Exclusive fullscreen hoặc overlay GPU: mss và BitBlt trả ảnh đen hoặc ảnh cũ; kết hợp với E-04 thành mù âm thầm | dxcam hoặc Windows Graphics Capture; kiểm tra ảnh đen; hướng dẫn dùng borderless |
| L-02 | HDR, Night Light, hồ sơ màu ICC, f.lux làm đổi màu nên dải HSV bị lệch | Hiệu chuẩn bằng mẫu tham chiếu mỗi phiên; dùng khoảng cách ΔE trong không gian Lab |
| L-03 | Anti-cheat và ToS: input giả lập mang cờ injected, nhịp hành vi đều đặn | Không hứa chống phát hiện; cảnh báo rõ; chỉ dùng ở game cho phép |
| L-04 | UIPI khi game chạy quyền admin (xem E-16) | Phát hiện và cảnh báo khi khởi động |
| L-05 | Antivirus báo nhầm: PyInstaller, hook bàn phím, SendInput, UPX, chưa ký số | Tắt UPX, ký số, onedir kèm installer, gửi mẫu false-positive |
| L-06 | Nhiều màn hình: `capture_fullscreen` chỉ lấy `monitors[1]` | Chọn monitor theo cửa sổ game |
| L-07 | Khóa màn hình, ngủ máy, ngắt RDP làm capture lỗi hoặc ra ảnh đen | Phát hiện trạng thái phiên và dừng |
| L-08 | Game cập nhật đổi layout, ngôn ngữ, độ phân giải làm tọa độ cố định sai | Template neo (anchor) và tọa độ tương đối |
| L-09 | Ảnh bằng chứng chứa thông tin cá nhân (thông báo, chat) lưu vô thời hạn | Chụp đúng vùng, xoay vòng, cho phép tắt |

### 5.6 Xếp hạng FMEA cho nhóm P0

Thang 1 đến 10, chấm chủ quan: S là mức nghiêm trọng, O là khả năng xảy ra, D là độ khó phát hiện (10 nghĩa là gần như không thể phát hiện). RPN = S × O × D. Mục đích là sắp thứ tự sửa, không phải số đo thực nghiệm.

| Hạng | ID | S | O | D | RPN |
| --- | --- | --- | --- | --- | --- |
| 1 | E-01 Roll cuối không được kiểm tra | 9 | 6 | 9 | 486 |
| 2 | E-04 Ảnh đen im lặng | 10 | 4 | 10 | 400 |
| 3 | E-02 Roll thừa sau lock | 7 | 8 | 7 | 392 |
| 4 | E-05 Lock không khóa | 9 | 7 | 6 | 378 |
| 5 | E-03 Animation xong sai | 8 | 6 | 7 | 336 |
| 5 | E-06 Nhận diện màu yếu | 8 | 7 | 6 | 336 |
| 7 | E-07 F6 bỏ qua xác thực | 6 | 5 | 5 | 150 |

## 6. Phương án giải quyết

### 6.1 Vòng lặp đúng

Nguyên tắc: **quét trước, giới hạn sau; không chắc thì dừng; sau khi lock thì tính lại ngay.**

```
loop:
  pause.wait()
  click_roll()
  wait_settled()          # pha 1: thấy thay đổi hoặc nút Roll về trạng thái sẵn sàng
                          # pha 2: tĩnh liên tiếp N frame; hết thời gian thì dừng 'không chắc'
  result = scan_all()     # LUÔN quét trước mọi kiểm tra khác
  if capture_failed or result.uncertain:
      stop('uncertain')   # fail-safe: thà dừng nhầm còn hơn bỏ sót
  apply_rules(result)     # stop, hoặc lock (click nút khóa thật rồi xác nhận)
  if stopped or all_locked_now: break      # tính ngay sau khi lock, không roll thêm
  if budget_low or count >= max_rolls: break   # kiểm tra giới hạn SAU khi đã quét
```

### 6.2 Giải pháp và tiêu chí hoàn thành theo lỗi

| Lỗi | Giải pháp | Tiêu chí hoàn thành |
| --- | --- | --- |
| E-01, E-02 | Đổi thứ tự như 6.1; tính `all_locked` sau vòng quét | Test A và B chuyển xanh |
| E-03 | Settle hai pha, kết hợp template nút Roll, theo dõi mọi slot | Test C: đúng 1 click trong lúc game trễ |
| E-04 | `CaptureError`, ngưỡng lỗi liên tiếp, kiểm tra ảnh đen thuần | Test D: dừng với lý do `capture_failed` |
| E-05 | Chọn L1 hoặc L2 (6.4) | UI không còn mô tả sai; nếu L1 thì khóa được xác nhận |
| E-06 | Pipeline mới (6.3) | Đạt ngưỡng precision và recall đã đặt trước trên bộ khung hình ghi sẵn |
| E-07 | `validate_and_start()` dùng chung | F6 và nút Start cho cùng kết quả khi cấu hình sai |
| E-08, E-09 | Supervisor bọc vòng lặp, join khi dừng, Event mới cho mỗi lần chạy | Ném exception giả: UI báo lỗi và STOPPED; start và stop liên tiếp chỉ có một thread |
| E-10 | Foreground guard, phát hiện chuột bị di | Alt-tab thì bot tự tạm dừng |
| E-13 | Bật DPI-aware, quy đổi theo màn hình, tọa độ tương đối | Cùng vùng trên máy 100% và 150% cho cùng ảnh |

### 6.3 Pipeline nhận diện đề xuất

1. Cắt ROI theo slot và chuẩn hóa kích thước.
2. Lấy vòng viền (khung rarity) bằng mặt nạ hoặc template, loại phần nền và hình minh họa bên trong.
3. Chuyển sang không gian Lab; tính khoảng cách ΔE tới màu tham chiếu của từng rarity. Màu tham chiếu được hiệu chuẩn từ mẫu người dùng chọn bằng k-means hoặc percentile.
4. Tạo mặt nạ rồi dùng `connectedComponentsWithStats`, chỉ giữ thành phần có diện tích tối thiểu; tính tỷ lệ phủ trên viền.
5. Cho điểm tin cậy 0 đến 1 và bỏ phiếu k trong n khung liên tiếp để chống nhấp nháy.
6. Phân ba vùng: chắc chắn có, chắc chắn không, không chắc. Vùng không chắc thì dừng và báo.
7. Khi nhiều màu cùng khớp, chọn theo độ hiếm, không theo diện tích.

### 6.4 Hai lựa chọn cho `lock`

| Lựa chọn | Nội dung | Được | Mất |
| --- | --- | --- | --- |
| L1: khóa thật | Thêm `lock_click` theo slot, click rồi xác nhận khóa bằng template hoặc màu icon | Đúng như hứa; dùng được mô hình roll từng phần | Cần biết game cụ thể; thêm cấu hình và test |
| L2: đổi tên | Đổi thành bỏ qua slot (phía bot), hiện cảnh báo rằng game có thể ghi đè | Nhanh (khoảng 0,5 ngày), trung thực | Mất tính năng lock như tên gọi |

Đề xuất: làm L2 ngay để hết gây hiểu nhầm, làm L1 khi đã chốt game mục tiêu.

## 7. Kiến trúc đề xuất

Áp dụng Ports and Adapters (hexagonal): phần lõi chỉ biết các giao diện, không biết mss, pyautogui hay Qt. Nhờ vậy lõi chạy được headless với game giả.

```
Adapters   FrameSource (mss | dxcam)   InputSink (SendInput)   WindowInfo (win32)   Clock
              |                              |                      |                |
Core       Settle -> Perception -> RuleEngine -> StateMachine <- Watchdog / Guards
              |
Bus        sự kiện: StateChanged, RollDone, TargetFound, Locked, Error  (queue)
              |
UI         Presenter -> PySide6 (Signals)   Tray   Hotkeys (RegisterHotKey)   Logger
```

**Các giao diện chính**

```python
class FrameSource(Protocol):
    def grab(self, rect: Rect) -> Frame: ...      # ném CaptureError khi hỏng

class InputSink(Protocol):
    def click(self, point: Point) -> None: ...

class Clock(Protocol):
    def now(self) -> float: ...                   # monotonic
    def wait(self, seconds: float, stop: Event) -> bool: ...
```

**Máy trạng thái**

| Trạng thái | Việc làm | Chuyển tiếp |
| --- | --- | --- |
| IDLE | Chờ lệnh | Sang ARMED khi người dùng bắt đầu |
| ARMED | Kiểm tra cấu hình, cửa sổ game, DPI, quyền | Sang CLICK nếu hợp lệ; ngược lại về IDLE kèm lỗi |
| CLICK | Click Roll, ghi mốc thời gian | Sang SETTLE |
| SETTLE | Chờ hai pha | Sang SCAN khi tĩnh; hết thời gian thì UNCERTAIN |
| SCAN | Chụp và nhận diện mọi slot | Sang DECIDE; lỗi chụp thì ERROR |
| DECIDE | Áp rule theo độ hiếm | Sang CLICK, LOCKING, DONE hoặc UNCERTAIN |
| LOCKING | Click khóa và xác nhận | Sang CLICK hoặc DONE |
| UNCERTAIN, ERROR, DONE | Cảnh báo, lưu khung hình, dừng | Về IDLE |

Từ bất kỳ trạng thái nào có thể sang STOPPED khi người dùng dừng, watchdog hết hạn, mất foreground hoặc chạm giới hạn.

**Cấu hình có kiểu (phác thảo)**

```python
class Slot(BaseModel):
    id: str
    rect: RelRect                 # 0..1 theo client rect của cửa sổ game
    lock_click: RelPoint | None = None

class Rule(BaseModel):
    color: str
    action: Literal['stop', 'lock', 'ignore']
    priority: int                 # số nhỏ = hiếm hơn

class Profile(BaseModel):
    version: int = 3
    game: GameBinding             # tiêu đề cửa sổ, tên process
    roll_click: RelPoint
    slots: list[Slot]
    rules: list[Rule]
    timing: Timing                # một đơn vị (giây), một nơi duy nhất
    detection: Detection          # ngưỡng theo màu, vòng viền, số khung bỏ phiếu
    guards: Guards                # budget, max_rolls, max_runtime, foreground
```

Engine nhận một bản snapshot bất biến của `Profile` lúc bắt đầu chạy. Thay đổi từ GUI chỉ có hiệu lực ở lần chạy sau.
