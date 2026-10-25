"""
Tạo icon cho ứng dụng:
- assets/icon.png & assets/icon.ico (App Icon)
- assets/tray_idle.png (Khay hệ thống - Trạng thái nghỉ)
- assets/tray_running.png (Khay hệ thống - Đang chạy)
"""
import os
from PIL import Image, ImageDraw

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

def create_app_icon(size=256):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Bo góc nền bo tròn (squircle)
    margin = int(size * 0.06)
    radius = int(size * 0.22)
    bg_box = [margin, margin, size - margin, size - margin]
    
    # Nền gradient giả lập bằng các lớp
    draw.rounded_rectangle(bg_box, radius=radius, fill=(24, 28, 36, 255), outline=(0, 210, 255, 200), width=int(size * 0.03))
    
    # Vòng tròn radar / target ở tâm
    center = size // 2
    r_outer = int(size * 0.28)
    r_inner = int(size * 0.16)
    
    # Vòng ngoài
    draw.ellipse([center - r_outer, center - r_outer, center + r_outer, center + r_outer], outline=(155, 89, 182, 220), width=int(size * 0.025))
    # Vòng trong
    draw.ellipse([center - r_inner, center - r_inner, center + r_inner, center + r_inner], outline=(0, 229, 255, 240), width=int(size * 0.025))
    
    # Dấu thập ngắm
    cross_len = int(size * 0.34)
    w_line = max(2, int(size * 0.025))
    draw.line([center - cross_len, center, center - int(size * 0.08), center], fill=(0, 229, 255, 240), width=w_line)
    draw.line([center + int(size * 0.08), center, center + cross_len, center], fill=(0, 229, 255, 240), width=w_line)
    draw.line([center, center - cross_len, center, center - int(size * 0.08)], fill=(0, 229, 255, 240), width=w_line)
    draw.line([center, center + int(size * 0.08), center, center + cross_len], fill=(0, 229, 255, 240), width=w_line)
    
    # Con trỏ chuột sắc nét chỉ vào tâm
    # Vẽ con trỏ chuột dạng vector polygon (mũi tên nghiêng)
    p_tip = (center + int(size * 0.04), center + int(size * 0.04))
    p_bottom = (p_tip[0] + int(size * 0.24), p_tip[1] + int(size * 0.32))
    p_mid = (p_tip[0] + int(size * 0.16), p_tip[1] + int(size * 0.22))
    p_tail_1 = (p_mid[0] + int(size * 0.08), p_mid[1] + int(size * 0.14))
    p_tail_2 = (p_mid[0] + int(size * 0.04), p_mid[1] + int(size * 0.18))
    p_left = (p_tip[0], p_tip[1] + int(size * 0.28))
    
    cursor_poly = [
        p_tip,
        (p_tip[0] + int(size * 0.22), p_tip[1] + int(size * 0.22)),
        (p_tip[0] + int(size * 0.14), p_tip[1] + int(size * 0.22)),
        (p_tip[0] + int(size * 0.22), p_tip[1] + int(size * 0.36)),
        (p_tip[0] + int(size * 0.16), p_tip[1] + int(size * 0.38)),
        (p_tip[0] + int(size * 0.08), p_tip[1] + int(size * 0.24)),
        (p_tip[0], p_tip[1] + int(size * 0.26))
    ]
    draw.polygon(cursor_poly, fill=(255, 255, 255, 255), outline=(0, 0, 0, 255))
    
    # Điểm sáng ở tâm
    draw.ellipse([center - 4, center - 4, center + 4, center + 4], fill=(255, 46, 99, 255))
    
    return img

def create_tray_icon(is_running=False, size=64):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    center = size // 2
    r = int(size * 0.42)
    
    if is_running:
        # Màu đỏ / cam rực rỡ khi đang chạy
        bg_col = (255, 46, 99, 255)
        border_col = (255, 200, 210, 255)
        draw.ellipse([center - r, center - r, center + r, center + r], fill=bg_col, outline=border_col, width=3)
        # Biểu tượng tia chớp hoặc 2 vạch song song / nút pause / mũi tên
        # Vẽ tam giác play / vuông
        pad = int(size * 0.22)
        draw.rectangle([center - int(r*0.4), center - int(r*0.4), center + int(r*0.4), center + int(r*0.4)], fill=(255, 255, 255, 255))
    else:
        # Màu xanh ngọc / lá cây dịu khi đang nghỉ
        bg_col = (0, 200, 115, 255)
        border_col = (200, 255, 230, 255)
        draw.ellipse([center - r, center - r, center + r, center + r], fill=bg_col, outline=border_col, width=3)
        # Biểu tượng Play tam giác trắng
        poly = [
            (center - int(r*0.25), center - int(r*0.45)),
            (center - int(r*0.25), center + int(r*0.45)),
            (center + int(r*0.45), center)
        ]
        draw.polygon(poly, fill=(255, 255, 255, 255))
        
    return img

if __name__ == "__main__":
    app_img = create_app_icon(256)
    app_png_path = os.path.join(ASSETS_DIR, "icon.png")
    app_ico_path = os.path.join(ASSETS_DIR, "icon.ico")
    app_img.save(app_png_path, format="PNG")
    
    # Lưu .ico với nhiều kích thước tiêu chuẩn Windows
    icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    app_img.save(app_ico_path, format="ICO", sizes=icon_sizes)
    
    # Tray icons
    tray_idle = create_tray_icon(is_running=False, size=64)
    tray_idle.save(os.path.join(ASSETS_DIR, "tray_idle.png"), format="PNG")
    
    tray_running = create_tray_icon(is_running=True, size=64)
    tray_running.save(os.path.join(ASSETS_DIR, "tray_running.png"), format="PNG")
    
    print("Assets generated successfully:")
    print(" -", app_png_path)
    print(" -", app_ico_path)
    print(" -", os.path.join(ASSETS_DIR, "tray_idle.png"))
    print(" -", os.path.join(ASSETS_DIR, "tray_running.png"))
