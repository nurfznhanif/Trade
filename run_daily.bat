@echo off
REM Launcher pipeline harian Trade — dipanggil Windows Task Scheduler.
cd /d "%~dp0"
".venv\Scripts\python.exe" "scripts\daily.py" >> "data\daily_log.txt" 2>&1
