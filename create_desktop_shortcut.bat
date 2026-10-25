@echo off
chcp 65001 > nul
echo ======================================================
echo    Tạo Shortcut Smart Auto Click ra màn hình Desktop
echo ======================================================

set "TARGET=%~dp0dist\SmartAutoClick.exe"
set "ICON=%~dp0assets\icon.ico"
set "SHORTCUT=%USERPROFILE%\Desktop\Smart Auto Click.lnk"

if not exist "%TARGET%" (
    echo [!] Chưa tìm thấy dist\SmartAutoClick.exe. Hãy chạy python build.py trước!
    pause
    exit /b
)

powershell -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT%'); $s.TargetPath = '%TARGET%'; $s.WorkingDirectory = '%~dp0dist'; $s.IconLocation = '%ICON%'; $s.Save()"

if exist "%SHORTCUT%" (
    echo [OK] Đã tạo Shortcut thành công trên Desktop của bạn!
    echo Bạn có thể nhấp đúp vào icon trên Desktop hoặc chuột phải ghim vào Taskbar.
) else (
    echo [!] Không thể tạo shortcut. Vui lòng kiểm tra quyền truy cập.
)

pause
