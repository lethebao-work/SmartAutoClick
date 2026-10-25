# 🎯 Smart Auto Click v2.0 — Conditional Visual Auto Clicker

Ứng dụng Desktop tự động bấm nút kết hợp nhận diện hình ảnh màu sắc (Computer Vision / OpenCV + HSV). Tự động dừng khi phát hiện vật phẩm hoặc đồ hiếm theo màu sắc cấu hình. **Không can thiệp mã nguồn hay bộ nhớ game.**

---

## 🌟 Tính năng nổi bật (v2.0 Redesign)

### 1. Đóng gói EXE độc lập (`SmartAutoClick.exe`)
- Chạy trực tiếp từ file `.exe` duy nhất, không cần cài đặt Python.
- Có thể **Ghim vào Taskbar (Pin to Taskbar)** hoặc tạo Desktop Shortcut để mở nhanh bất cứ khi nào chơi game.
- Đi kèm icon ứng dụng sắc nét chuẩn Windows.

### 2. Thu nhỏ vào Khay hệ thống (System Tray)
- Khi bấm nút `X` đóng cửa sổ, ứng dụng sẽ **tự động ẩn vào khay Taskbar** (cạnh đồng hồ) và tiếp tục chạy ngầm mà không làm vướng màn hình.
- Menu chuột phải tại khay hệ thống hỗ trợ thao tác nhanh:
  - ⛶ Mở lại cửa sổ chính
  - 📐 Mở Chế độ thu gọn (Mini Widget)
  - ▶ Bắt đầu (F6) / ⏸ Tạm dừng (F6) / 🛑 Dừng (F7)
  - ❌ Thoát hoàn toàn
- Icon khay đổi màu theo trạng thái (Xanh lá = Nghỉ, Đỏ = Đang Auto Roll).

### 3. Chế độ thu gọn (Compact Window / Mini Widget)
- Cửa sổ nhỏ gọn (330x220px) thiết kế hiện đại, có tính năng **Always-on-Top (Luôn nổi trên cùng)**.
- Cho phép vừa chơi game vừa theo dõi số lượt Roll và tình trạng nhận diện đồ hiếm mà không che màn hình game.
- Dễ dàng chuyển đổi qua lại giữa Giao diện đầy đủ và Giao diện thu gọn chỉ với 1 click.

### 4. Độ lệch thời gian ngẫu nhiên (Random Delay Offset Jitter)
- Tự động cộng/trừ ngẫu nhiên một khoảng thời gian (± ms) giữa các lần click.
- Giả lập hành vi người thật, ngăn chặn hoàn toàn hệ thống chống auto-click / anti-macro của game.

### 5. Ghi & Phát lại Macro thao tác chuột (Record & Playback Macro)
- Tab riêng cho phép người dùng **Ghi lại các thao tác click chuột thực tế** (tọa độ, nút bấm trái/phải, thời gian chờ giữa các lần bấm).
- Phát lại chuỗi thao tác với nhiều tùy chọn:
  - Tốc độ phát: `0.5x`, `1.0x (Chuẩn)`, `2.0x`, `5.0x (Siêu tốc)`
  - Số lần lặp lại hoặc **Lặp vô hạn**
  - Lưu và Nạp danh sách macro từ file `.json` để chia sẻ cho người khác.

---

## 🎮 Tính năng lõi & Trí tuệ nhận diện

### Nhận diện màu sắc theo thời gian thực (OpenCV HSV)
- Tự động phân tích từng ô vật phẩm theo dải màu HSV (Tím Epic, Đỏ Mythic, Vàng Legendary, Xanh Rare, Xanh Uncommon...).
- **Color Sampler (Hút màu)**: Kính lúp phóng to 8x, click trực tiếp vào ảnh game để lấy màu chính xác pixel.

### Logic đa điều kiện & Multi-Slot
- **Hành động theo màu**:
  - `stop`: Dừng ngay khi phát hiện đồ hiếm (kèm âm thanh chuông báo và chụp ảnh lưu lại).
  - `lock`: Khóa giữ ô đồ hiếm đó và tiếp tục roll các ô còn lại.
- **Theo dõi nhiều ô vật phẩm**: Hỗ trợ không giới hạn số slot quan sát độc lập.
- **Region Picker Overlay**: Kéo thả chuột trực quan trên màn hình để chọn vùng soi kết quả.
- **Animation Detection**: Tự động nhận biết khi nào vòng xoay roll kết thúc để bấm tiếp ngay.
- **Budget Guard**: Tự động dừng an toàn khi nút Roll bị mờ (hết tiền).
- **Profile System**: Lưu và chuyển đổi nhiều cấu hình game khác nhau.

---

## 🚀 Hướng dẫn khởi chạy

### Cách 1: Chạy file EXE độc lập (Khuyên dùng)
1. Mở thư mục `dist/`
2. Nhấp đúp vào `SmartAutoClick.exe`
3. *(Tùy chọn)* Chuột phải vào `SmartAutoClick.exe` → **Pin to taskbar** để bấm nhanh từ thanh tác vụ Windows.

### Cách 2: Chạy từ mã nguồn Python
```bash
python main.py
# Hoặc nhấp đúp vào file run.bat
```

### Cách 3: Tự đóng gói lại file EXE
```bash
python build.py
```

---

## ⌨️ Phím tắt toàn cục (Global Hotkeys)

| Phím | Chức năng | Ghi chú |
|:---:|:---|:---|
| **F6** | **Bắt đầu / Tạm dừng** | Hoạt động ngay cả khi đang trong cửa sổ game |
| **F7** | **Dừng khẩn cấp** | Lập tức ngắt toàn bộ tiến trình click |
| **ESC** | **Hủy chọn vùng** | Thoát chế độ chọn vùng Region Picker |

---

## 📁 Cấu trúc thư mục

```text
Autoclick/
├── dist/
│   └── SmartAutoClick.exe   # File ứng dụng độc lập đóng gói sẵn
├── assets/                  # Icons và hình ảnh khay hệ thống
├── core/
│   ├── capture.py           # Chụp màn hình (mss / PIL fallback)
│   ├── detector.py          # Phân tích dải màu HSV
│   ├── clicker.py           # Mô phỏng chuột & human jitter
│   ├── engine.py            # Vòng lặp tự động, anim detect, budget guard
│   ├── config_manager.py    # Quản lý file cấu hình & profile
│   └── macro_recorder.py    # Ghi và phát lại macro chuột
├── gui/
│   ├── main_window.py       # Cửa sổ chính 5 tab & System tray
│   ├── compact_window.py    # Mini widget nổi Always-on-Top
│   ├── region_picker.py     # Overlay kéo thả chọn vùng
│   └── color_sampler.py     # Cửa sổ hút màu & kính lúp 8x
├── main.py                  # Điểm khởi chạy ứng dụng
├── build.py                 # Script đóng gói EXE tự động
├── config.json              # File cấu hình JSON
└── requirements.txt         # Danh sách thư viện Python
```
