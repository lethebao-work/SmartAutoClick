@echo off
title Visual Conditional Auto Clicker
chcp 65001 >nul
cd /d "%~dp0"
echo Dang khoi dong Auto Clicker...
python main.py
if errorlevel 1 (
    echo.
    echo [LOI] Khong the khoi dong. Vui long kiem tra Python va thu vien.
    pause
)
