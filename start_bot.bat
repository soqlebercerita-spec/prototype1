@echo off
echo ========================================
echo  MENJALANKAN BOT TRADING - bobot2.py
echo  Created by Pras
echo ========================================
echo.

:: Cek apakah Python tersedia
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo Python tidak ditemukan! Harap install Python terlebih dahulu.
    pause
    exit /b
)

:: Jalankan file bobot2.py
echo 🚀 Menjalankan bot...
python bobot2.py

:: Tunggu agar jendela tidak langsung tertutup jika terjadi error
echo.
echo 📍 Bot dihentikan atau error terjadi.
pause
