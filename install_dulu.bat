@echo off
echo ========================================
echo  AUTO INSTALLER - BOT TRADING PYTHON
echo  Created by Pras
echo ========================================
echo.

:: Upgrade pip
echo 🔁 Updating pip...
python -m pip install --upgrade pip

:: Install semua module
echo 🔧 Installing required Python modules...

pip install MetaTrader5
pip install pandas
pip install numpy
pip install requests
pip install pytz

:: tkinter biasanya sudah ada, tapi bisa dipastikan via:
echo 📦 Pastikan tkinter sudah ada (bawaan Python)...
python -m tkinter || echo Jika gagal, pastikan Python dipasang dengan opsi TCL/Tk.

:: Untuk GUI
pip install ttkthemes
pip install matplotlib

:: Jika kamu pakai telegram
pip install python-telegram-bot

echo ✅ Semua module berhasil diinstall!
pause
