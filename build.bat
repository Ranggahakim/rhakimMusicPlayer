@echo off
title rhakim Music Player Builder
echo ==========================================
echo    rhakim Music Player - Safe Build
echo ==========================================

echo [0/3] Memastikan aplikasi sudah tertutup...
:: /f artinya force (paksa), /im artinya image name (nama file)
:: 2>nul itu biar gak muncul pesan error kalau aplikasinya emang lagi gak jalan
taskkill /f /im "rhakim Music Player.exe" 2>nul

echo [1/3] Menghapus folder build lama...
if exist build rd /s /q build

echo [2/3] Memulai proses PyInstaller...
:: Kita tetap jalankan build seperti biasa
py -m PyInstaller --noconsole --onefile --name "rhakim Music Player" --icon=app.ico --add-data "ui_components.py;." --add-data "app.ico;." main.py

echo [3/3] Sinkronisasi file pendukung...
:: Hanya copy .env jika ada, tanpa menghapus settings.json yang sudah ada di dist
if exist .env (
    copy .env dist\
)

echo ==========================================
echo Build Selesai! Pengaturan folder kamu aman.
echo ==========================================
pause