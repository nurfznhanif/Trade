@echo off
REM KIRIM DATA PC -> SERVER: trade.db + analysis.json + kunci LLM (.env). Kunci akses server gak ketimpa.
REM AWAS: data di server DITIMPA versi PC (termasuk jurnal). Normalnya cuma sekali, pas pindahan.
cd /d "%~dp0\.."
call deploy\_conf.bat || exit /b 1

echo Siapin salinan DB (aman walau dashboard lagi kebuka) ...
".venv\Scripts\python.exe" -c "import sqlite3; s=sqlite3.connect('data/trade.db'); d=sqlite3.connect('data/trade_kirim.db'); s.backup(d); d.close()" || goto gagal

echo Kirim ke server (sekitar 500 MB, sabar) ...
scp -C %SSHOPT% data\trade_kirim.db data\analysis.json %SERVER%:/tmp/ || goto gagal
if exist ".env" scp %SSHOPT% .env %SERVER%:/tmp/pc.env || goto gagal
ssh %SSHOPT% %SERVER% "bash /opt/trade/deploy/terima_data.sh" || goto gagal
del data\trade_kirim.db

echo Data terkirim.
if not "%1"=="nopause" pause
exit /b 0

:gagal
echo [!] GAGAL kirim data. Cek pesan di atas.
if exist data\trade_kirim.db del data\trade_kirim.db
if not "%1"=="nopause" pause
exit /b 1
