@echo off
echo ========================================
echo Створення EXE файлу Version Checker
echo ========================================
echo.

REM Перевірка наявності Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не знайдено!
    echo Встановіть Python 3.8+ з python.org
    pause
    exit /b 1
)

REM Встановлення залежностей
echo 📦 Встановлення залежностей...
pip install -r requirements.txt

REM Створення EXE
echo 🔨 Створення EXE файлу...
pyinstaller --onefile ^
            --windowed ^
            --name "VersionChecker" ^
            --add-data "config.json;." ^
            --add-data "README.txt;." ^
            --hidden-import PyQt5.QtWidgets ^
            --hidden-import PyQt5.QtCore ^
            --hidden-import PyQt5.QtGui ^
            --hidden-import sqlite3 ^
            --hidden-import requests ^
            --hidden-import bs4 ^
            --clean ^
            --noconfirm ^
            launcher.py

echo.
echo ========================================
echo ✅ EXE файл успішно створено!
echo 📍 Розташування: dist\VersionChecker.exe
echo.
echo 💡 Поради:
echo 1. Скопіюйте config.json поряд з EXE
echo 2. Перший запуск може тривати 10-20 секунд
echo ========================================
pause